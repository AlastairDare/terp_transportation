from __future__ import unicode_literals
import frappe
import json
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

@frappe.whitelist()
def create_sales_invoice_for_trip(trip_name):
    """Create sales invoice for a trip"""
    if not trip_name:
        frappe.throw(_("Trip name is required"))
        
    doc = frappe.get_doc("Trip", trip_name)
    
    # Validate required fields
    if not doc.billing_customer:
        frappe.throw(_("Billing Customer is required for sales invoice creation"))
    if not doc.quantity or doc.quantity <= 0:
        frappe.throw(_("Quantity must be greater than 0"))
    if not doc.rate or doc.rate <= 0:
        frappe.throw(_("Rate must be greater than 0"))
    if not doc.taxes_and_charges:
        frappe.throw(_("Taxes and Charges is required"))
        
    try:
        # First ensure the service item exists
        if not frappe.db.exists("Item", doc.name):
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
            
        # Create or update sales invoice
        if doc.linked_sales_invoice:
            sales_invoice = frappe.get_doc("Sales Invoice", doc.linked_sales_invoice)
            update_sales_invoice(sales_invoice, doc)
            sales_invoice.save()
        else:
            sales_invoice = create_new_sales_invoice(doc)
            doc.linked_sales_invoice = sales_invoice.name
            
        # Update the sales invoice status
        doc.sales_invoice_status = "Invoice Created"
        doc.save(ignore_permissions=True)
            
        frappe.msgprint(
            msg=f"""
                <div>
                    <p>{_("Sales Invoice created/updated successfully: ")} 
                    <a href='/app/sales-invoice/{sales_invoice.name}'>{sales_invoice.name}</a>
                    </p>
                </div>
            """,
            title=_("Sales Invoice Created/Updated"),
            indicator="green"
        )
        
        return sales_invoice.name
            
    except Exception as e:
        frappe.log_error(
            message=f"Error creating sales invoice for trip {doc.name}: {str(e)}\nFull error: {frappe.get_traceback()}",
            title="Sales Invoice Creation Error"
        )
        frappe.throw(_("Failed to create sales invoice. Error: {0}").format(str(e)))

@frappe.whitelist()
def create_purchase_invoice_for_trip(trip_name):
    """Create purchase invoice for a trip"""
    if not trip_name:
        frappe.throw(_("Trip name is required"))
        
    doc = frappe.get_doc("Trip", trip_name)
    
    # Validate required fields
    if not doc.billing_supplier:
        frappe.throw(_("Billing Supplier is required for purchase invoice creation"))
    if not doc.purchase_quantity or doc.purchase_quantity <= 0:
        frappe.throw(_("Purchase Quantity must be greater than 0"))
    if not doc.purchase_rate or doc.purchase_rate <= 0:
        frappe.throw(_("Purchase Rate must be greater than 0"))
    if not doc.purchase_taxes_and_charges:
        frappe.throw(_("Purchase Taxes and Charges is required"))
        
    try:
        # Create the purchase item if it doesn't exist
        item_code = f"PURCH-{doc.name}"
        if not frappe.db.exists("Item", item_code):
            item = frappe.get_doc({
                "doctype": "Item",
                "item_code": item_code,
                "item_name": f"Purchase Item for {doc.name}",
                "item_group": "Services",
                "stock_uom": "Each",
                "is_stock_item": 0,
                "is_fixed_asset": 0,
                "description": f"Purchase Service Item for Trip {doc.name}"
            })
            item.insert(ignore_permissions=True)
            
        # Create or update purchase invoice
        if doc.linked_purchase_invoice:
            purchase_invoice = frappe.get_doc("Purchase Invoice", doc.linked_purchase_invoice)
            update_purchase_invoice(purchase_invoice, doc)
            purchase_invoice.save()
        else:
            purchase_invoice = create_new_purchase_invoice(doc)
            doc.linked_purchase_invoice = purchase_invoice.name
            
        # Update the purchase invoice status
        doc.purchase_invoice_status = "Invoice Created"
        doc.save(ignore_permissions=True)
            
        frappe.msgprint(
            msg=f"""
                <div>
                    <p>{_("Purchase Invoice created/updated successfully: ")} 
                    <a href='/app/purchase-invoice/{purchase_invoice.name}'>{purchase_invoice.name}</a>
                    </p>
                </div>
            """,
            title=_("Purchase Invoice Created/Updated"),
            indicator="green"
        )
        
        return purchase_invoice.name
            
    except Exception as e:
        frappe.log_error(
            message=f"Error creating purchase invoice for trip {doc.name}: {str(e)}\nFull error: {frappe.get_traceback()}",
            title="Purchase Invoice Creation Error"
        )
        frappe.throw(_("Failed to create purchase invoice. Error: {0}").format(str(e)))

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
        
def create_or_update_purchase_invoice(doc):
    """Create or update purchase invoice based on trip data"""
    try:
        if doc.linked_purchase_invoice:
            # Update existing invoice
            purchase_invoice = frappe.get_doc("Purchase Invoice", doc.linked_purchase_invoice)
            update_purchase_invoice(purchase_invoice, doc)
            purchase_invoice.save()
            return purchase_invoice
        else:
            # Create new invoice
            purchase_invoice = create_new_purchase_invoice(doc)
            doc.linked_purchase_invoice = purchase_invoice.name
            return purchase_invoice
            
    except Exception as e:
        frappe.log_error(
            message=f"Error creating/updating purchase invoice for trip {doc.name}: {str(e)}",
            title="Purchase Invoice Creation Error"
        )
        frappe.throw(_("Failed to create/update purchase invoice. Error: {0}").format(str(e)))

def create_new_purchase_invoice(doc):
    """Create a new purchase invoice from trip data"""
    # Create the purchase item first
    item_code = f"PURCH-{doc.name}"
    if not frappe.db.exists("Item", item_code):
        item = frappe.get_doc({
            "doctype": "Item",
            "item_code": item_code,
            "item_name": f"Purchase Item for {doc.name}",
            "item_group": "Services",
            "stock_uom": "Each",
            "is_stock_item": 0,
            "is_fixed_asset": 0,
            "description": f"Purchase Service Item for Trip {doc.name}"
        })
        item.insert(ignore_permissions=True)

    purchase_invoice = frappe.get_doc({
        "doctype": "Purchase Invoice",
        "supplier": doc.billing_supplier,
        "taxes_and_charges": doc.purchase_taxes_and_charges,
        "items": [{
            "item_code": item_code,
            "qty": doc.purchase_quantity,
            "rate": doc.purchase_rate,
            "amount": doc.purchase_amount
        }]
    })
    
    purchase_invoice.insert(ignore_permissions=True)
    return purchase_invoice

def update_purchase_invoice(purchase_invoice, doc):
    """Update existing purchase invoice with new trip data"""
    try:
        frappe.log_error(
            message=f"Starting purchase invoice update for trip {doc.name}, invoice {purchase_invoice.name}",
            title="Purchase Invoice Update Started"
        )
        
        purchase_invoice.supplier = doc.billing_supplier
        purchase_invoice.taxes_and_charges = doc.purchase_taxes_and_charges
        
        frappe.log_error(
            message=f"Header fields updated. Supplier: {doc.billing_supplier}, Taxes: {doc.purchase_taxes_and_charges}",
            title="Purchase Invoice Header Update"
        )
        
        item_code = f"PURCH-{doc.name}"
        item_found = False
        for item in purchase_invoice.items:
            if item.item_code == item_code:
                frappe.log_error(
                    message=f"Updating existing item {item.item_code}. Old values - Qty: {item.qty}, Rate: {item.rate}, Amount: {item.amount}",
                    title="Purchase Invoice Item Update"
                )
                
                item.qty = doc.purchase_quantity
                item.rate = doc.purchase_rate
                item.amount = doc.purchase_quantity * doc.purchase_rate
                
                frappe.log_error(
                    message=f"Item updated. New values - Qty: {item.qty}, Rate: {item.rate}, Amount: {item.amount}",
                    title="Purchase Invoice Item Updated"
                )
                
                item_found = True
                break
        
        if not item_found:
            frappe.log_error(
                message=f"Item {item_code} not found in invoice. Adding new item.",
                title="Purchase Invoice New Item"
            )
            
            purchase_invoice.append("items", {
                "item_code": item_code,
                "qty": doc.purchase_quantity,
                "rate": doc.purchase_rate,
                "amount": doc.purchase_quantity * doc.purchase_rate
            })
        
        # Save with flags to handle permissions
        purchase_invoice.flags.ignore_permissions = True
        purchase_invoice.calculate_taxes_and_totals()
        purchase_invoice.save()
        
        frappe.log_error(
            message=f"Purchase invoice {purchase_invoice.name} successfully updated",
            title="Purchase Invoice Update Complete"
        )
        
    except Exception as e:
        frappe.log_error(
            message=f"Error updating purchase invoice {purchase_invoice.name} for trip {doc.name}. Error: {str(e)}\nFull error: {frappe.get_traceback()}",
            title="Purchase Invoice Update Error"
        )
        raise

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
    try:
        frappe.log_error(
            message=f"Starting sales invoice update for trip {doc.name}, invoice {sales_invoice.name}",
            title="Sales Invoice Update Started"
        )
        
        # Update header level fields
        sales_invoice.customer = doc.billing_customer
        sales_invoice.taxes_and_charges = doc.taxes_and_charges
        
        frappe.log_error(
            message=f"Header fields updated. Customer: {doc.billing_customer}, Taxes: {doc.taxes_and_charges}",
            title="Sales Invoice Header Update"
        )
        
        # Update or add item
        item_found = False
        for item in sales_invoice.items:
            if item.item_code == doc.name:
                frappe.log_error(
                    message=f"Updating existing item {item.item_code}. Old values - Qty: {item.qty}, Rate: {item.rate}, Amount: {item.amount}",
                    title="Sales Invoice Item Update"
                )
                
                item.qty = doc.quantity
                item.rate = doc.rate
                item.amount = doc.quantity * doc.rate
                
                frappe.log_error(
                    message=f"Item updated. New values - Qty: {item.qty}, Rate: {item.rate}, Amount: {item.amount}",
                    title="Sales Invoice Item Updated"
                )
                
                item_found = True
                break
        
        if not item_found:
            frappe.log_error(
                message=f"Item {doc.name} not found in invoice. Adding new item.",
                title="Sales Invoice New Item"
            )
            
            sales_invoice.append("items", {
                "item_code": f"SALES-{doc.name}",
                "qty": doc.quantity,
                "rate": doc.rate,
                "amount": doc.quantity * doc.rate
            })
        
        # Save with flags to handle permissions
        sales_invoice.flags.ignore_permissions = True
        sales_invoice.calculate_taxes_and_totals()
        sales_invoice.save()
        
        frappe.log_error(
            message=f"Sales invoice {sales_invoice.name} successfully updated",
            title="Sales Invoice Update Complete"
        )
        
    except Exception as e:
        frappe.log_error(
            message=f"Error updating sales invoice {sales_invoice.name} for trip {doc.name}. Error: {str(e)}\nFull error: {frappe.get_traceback()}",
            title="Sales Invoice Update Error"
        )
        raise

        
@frappe.whitelist()
def create_group_service_item(trip_names):
    """Create a Trip Group from multiple trips"""
    if not trip_names:
        return
        
    # Convert string to list if needed
    if isinstance(trip_names, str):
        trip_names = json.loads(trip_names)
    
    # Get first trip for license plate
    first_trip = frappe.get_doc("Trip", trip_names[0])
    
    # Create Trip Group
    trip_group = frappe.get_doc({
        "doctype": "Trip Group",
        "license_plate": first_trip.license_plate,
        "trips": [{"trip": trip_name} for trip_name in trip_names]
    })
    
    trip_group.insert(ignore_permissions=True)
    
    return trip_group.name