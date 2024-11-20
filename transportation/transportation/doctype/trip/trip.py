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
    """Before save hook to handle item creation"""
    if doc.status == "Complete":
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
                "item_group": "Trips",
                "stock_uom": "Each",
                "is_stock_item": 0,
                "is_fixed_asset": 0,
                "description": f"Service Item for Trip {doc.name}"
            })
            
            item.insert(ignore_permissions=True)
            
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

        except Exception as e:
            frappe.log_error(
                message=f"Error creating service item for trip {doc.name}: {str(e)}",
                title="Service Item Creation Error"
            )
            frappe.throw(_("Failed to create service item. Error: {0}").format(str(e)))

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