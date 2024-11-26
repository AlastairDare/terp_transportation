from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from typing import Any, Dict, Optional

class Trip(Document):
    pass

def validate(doc, method):
    """Validate Trip document before saving."""
    # Handle approver setting based on whether it's a new doc or status change
    if doc.status == "Complete":
        if not doc.get("__islocal"):
            # Existing document
            if doc.has_value_changed('status') and doc._doc_before_save and doc._doc_before_save.status == "Awaiting Approval":
                doc.approver = frappe.session.user
        else:
            # New document
            doc.approver = frappe.session.user

    # Validate odometer readings
    if doc.odo_start and doc.odo_end:
        if doc.odo_end < doc.odo_start:
            frappe.throw(_("End odometer reading cannot be less than start reading"))
        doc.total_distance = doc.odo_end - doc.odo_start

    # Validate date
    if not doc.date:
        frappe.throw(_("Trip Date is required"))

    # Validate mass readings if provided
    if doc.second_mass and doc.first_mass:
        if doc.second_mass < doc.first_mass:
            frappe.throw(_("Second mass cannot be less than first mass"))
        doc.net_mass = doc.second_mass - doc.first_mass

def before_save(doc, method):
    """Before save hook to handle item and sales invoice creation"""
    if doc.status == "Complete":
        try:
            # First ensure the item exists regardless of sales invoice choice
            if not frappe.db.exists("Item", doc.name):
                item = frappe.get_doc({
                    "doctype": "Item",
                    "item_code": doc.name,
                    "item_name": f"{doc.name}",
                    "item_group": "Trips",
                    "stock_uom": "Each",
                    "is_stock_item": 0,
                    "is_fixed_asset": 0,
                    "description": f"Service Item for Trip {doc.name}"
                })
                
                item.insert(ignore_permissions=True)
                
                # Only show item creation message if we're not creating a sales invoice
                if not doc.auto_create_sales_invoice:
                    msg = f"""
                        <div>
                            <p>{_("Service Item created successfully: {0}").format(doc.name)}</p>
                            <div style="margin-top: 10px;">
                                <button class="btn btn-xs btn-default" 
                                        onclick="frappe.utils.copy_to_clipboard('{doc.name}').then(() => {{
                                            frappe.show_alert({{
                                                message: '{_("Item code copied to clipboard")}',
                                                indicator: 'green'
                                            }});
                                        }})">
                                    Copy Item Code
                                </button>
                            </div>
                        </div>
                    """
                    
                    frappe.msgprint(
                        msg=msg,
                        title=_("Service Item Created"),
                        indicator="green"
                    )

            # Handle sales invoice creation/update if auto-create is enabled
            if doc.auto_create_sales_invoice:
                create_or_update_sales_invoice(doc)
                
        except Exception as e:
            frappe.log_error(
                message=f"Error in before_save for trip {doc.name}: {str(e)}",
                title="Trip Save Error"
            )
            frappe.throw(_("Failed to process trip completion. Error: {0}").format(str(e)))

def handle_service_item(doc):
    """Create service item if it doesn't exist"""
    try:
        if frappe.db.exists("Item", doc.name):
            frappe.msgprint(
                msg=_("Service Item {0} already exists").format(doc.name),
                title=_("Service Item Status"),
                indicator="blue"
            )
            return

        item = frappe.get_doc({
            "doctype": "Item",
            "item_code": doc.name,
            "item_name": f"{doc.name}",
            "item_group": "Services",
            "stock_uom": "Each",
            "is_stock_item": 0,
            "is_fixed_asset": 0,
            "description": f"Service Item for Trip {doc.name}"
        })
        
        item.insert(ignore_permissions=True)
        
        frappe.msgprint(
            msg=f"""
                <div>
                    <p>{_("Service Item created successfully: {0}").format(doc.name)}</p>
                    <div style="margin-top: 10px;">
                        <button class="btn btn-xs btn-default" 
                                onclick="frappe.ui.form.handle_copy_to_clipboard('{doc.name}')">
                            Copy Item Code
                        </button>
                    </div>
                </div>
            """,
            title=_("Service Item Created"),
            indicator="green"
        )

    except Exception as e:
        frappe.log_error(
            message=f"Error creating service item for trip {doc.name}: {str(e)}",
            title="Service Item Creation Error"
        )
        frappe.throw(_("Failed to create service item. Error: {0}").format(str(e)))

def get_truck_query(doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict) -> list:
    """Filter Transportation Assets to show only Trucks."""
    return frappe.db.sql("""
        SELECT name 
        FROM `tabTransportation Asset`
        WHERE transportation_asset_type = 'Truck'
        AND ({key} LIKE %(txt)s
            OR name LIKE %(txt)s)
        ORDER BY
            IF(LOCATE(%(_txt)s, name), LOCATE(%(_txt)s, name), 99999),
            name
        LIMIT %(start)s, %(page_len)s
    """.format(**{
        'key': searchfield
    }), {
        'txt': "%%%s%%" % txt,
        '_txt': txt.replace("%", ""),
        'start': start,
        'page_len': page_len
    })

def get_trailer_query(doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict) -> list:
    """Filter Transportation Assets to show only Trailers."""
    return frappe.db.sql("""
        SELECT name 
        FROM `tabTransportation Asset`
        WHERE transportation_asset_type = 'Trailer'
        AND ({key} LIKE %(txt)s
            OR name LIKE %(txt)s)
        ORDER BY
            IF(LOCATE(%(_txt)s, name), LOCATE(%(_txt)s, name), 99999),
            name
        LIMIT %(start)s, %(page_len)s
    """.format(**{
        'key': searchfield
    }), {
        'txt': "%%%s%%" % txt,
        '_txt': txt.replace("%", ""),
        'start': start,
        'page_len': page_len
    })

@frappe.whitelist()
def get_last_odometer_reading(truck: str, current_doc: Optional[str] = None) -> Dict:
    """Get the last odometer reading for a truck."""
    if not truck:
        return {
            "odo_end": 0,
            "trip_name": None,
            "trip_date": None
        }

    filters = {
        "truck": truck,
        "docstatus": ["!=", 2],  # Include both draft (0) and submitted (1) documents
    }
    
    if current_doc:
        filters["name"] = ["!=", current_doc]
    
    last_trip = frappe.get_list(
        "Trip",
        filters=filters,
        fields=["odo_end", "date", "name"],
        order_by="date desc, creation desc",
        limit=1
    )
    
    if last_trip and last_trip[0].odo_end:
        return {
            "odo_end": last_trip[0].odo_end,
            "trip_name": last_trip[0].name,
            "trip_date": last_trip[0].date
        }
    
    return {
        "odo_end": 0,
        "trip_name": None,
        "trip_date": None
    }
    
def create_or_update_sales_invoice(doc):
    """Create or update sales invoice based on trip data"""
    try:
        if doc.linked_sales_invoice:
            # Update existing invoice
            sales_invoice = frappe.get_doc("Sales Invoice", doc.linked_sales_invoice)
            update_sales_invoice(sales_invoice, doc)
            sales_invoice.save()
            frappe.msgprint(
                msg=f"""
                    <div>
                        <p>{_("Sales Invoice updated successfully: ")} 
                        <a href='/app/sales-invoice/{sales_invoice.name}'>{sales_invoice.name}</a>
                        </p>
                    </div>
                """,
                title=_("Sales Invoice Updated"),
                indicator="green"
            )
        else:
            # Create new invoice
            sales_invoice = create_new_sales_invoice(doc)
            doc.linked_sales_invoice = sales_invoice.name
            frappe.msgprint(
                msg=f"""
                    <div>
                        <p>{_("Sales Invoice created successfully: ")} 
                        <a href='/app/sales-invoice/{sales_invoice.name}'>{sales_invoice.name}</a>
                        </p>
                    </div>
                """,
                title=_("Sales Invoice Created"),
                indicator="green"
            )
            
    except Exception as e:
        frappe.log_error(
            message=f"Error creating/updating sales invoice for trip {doc.name}: {str(e)}",
            title="Sales Invoice Creation Error"
        )
        frappe.throw(_("Failed to create/update sales invoice. Error: {0}").format(str(e)))

def create_new_sales_invoice(doc):
    """Create a new sales invoice from trip data"""
    sales_invoice = frappe.get_doc({
        "doctype": "Sales Invoice",
        "customer": doc.billing_customer,
        "taxes_and_charges": doc.taxes_and_charges,
        "items": [{
            "item_code": doc.name,
            "qty": doc.quantity,
            "rate": doc.rate,
            "amount": doc.amount
        }]
    })
    
    sales_invoice.insert(ignore_permissions=True)
    return sales_invoice

def update_sales_invoice(sales_invoice, doc):
    """Update existing sales invoice with new trip data"""
    # Update header level fields
    sales_invoice.customer = doc.billing_customer
    sales_invoice.taxes_and_charges = doc.taxes_and_charges
    
    # Update or add item
    item_found = False
    for item in sales_invoice.items:
        if item.item_code == doc.name:
            item.qty = doc.quantity
            item.rate = doc.rate
            item.amount = doc.amount
            item_found = True
            break
    
    if not item_found:
        sales_invoice.append("items", {
            "item_code": doc.name,
            "qty": doc.quantity,
            "rate": doc.rate,
            "amount": doc.amount
        })