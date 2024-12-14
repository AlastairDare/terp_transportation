from __future__ import unicode_literals
import frappe
import json
from frappe import _
from frappe.model.document import Document

class TripGroup(Document):
    pass

def validate(doc, method):
    """Validate Trip Group document before saving."""
    try:
        # Validate trips aren't in other groups
        for trip_row in doc.trips:
            existing_groups = frappe.get_all(
                "Trip Group Detail",
                filters={
                    "trip": trip_row.trip,
                    "parent": ["!=", doc.name],
                    "parenttype": "Trip Group"
                }
            )
            if existing_groups:
                frappe.throw(_(f"Trip {trip_row.trip} is already part of another group"))

        # Calculate total amount
        total = 0
        for trip in doc.trips:
            if trip.rate and trip.quantity:
                total += float(trip.rate) * float(trip.quantity)
        doc.total_amount = total
        
        frappe.log_error(f"Total amount calculated: {total}", "Trip Group Validation")
        
    except Exception as e:
        frappe.log_error(f"Error in validate: {str(e)}", "Trip Group Error")
        frappe.throw(_("Validation failed. Error: {0}").format(str(e)))

def before_save(doc, method):
    """Before save hook to handle service item creation"""
    try:
        if not frappe.db.exists("Item", f"GRP-{doc.name}"):
            item = frappe.get_doc({
                "doctype": "Item",
                "item_code": f"GRP-{doc.name}",
                "item_name": f"GRP-{doc.name}",
                "item_group": "Services",
                "stock_uom": "Each",
                "is_stock_item": 0,
                "is_fixed_asset": 0,
                "description": f"Group Service Item for Trip Group: {doc.name}",
                "standard_rate": doc.total_amount
            })
            
            item.insert(ignore_permissions=True)
            doc.service_item = f"GRP-{doc.name}"
            
            frappe.msgprint(
                msg=f"""
                    <div>
                        <p>{_("Group Service Item created successfully: {0}").format(doc.service_item)}</p>
                    </div>
                """,
                title=_("Service Item Created"),
                indicator="green"
            )
            
        frappe.log_error(f"Service item handled for {doc.name}", "Trip Group")
            
    except Exception as e:
        frappe.log_error(f"Error in before_save: {str(e)}", "Trip Group Error")
        frappe.throw(_("Failed to process Trip Group. Error: {0}").format(str(e)))

def validate_trip_group(doc, method):
    validate_trips(doc)
    calculate_total_amount(doc)

def validate_trips(doc):
    """Ensure trips are not already in another group"""
    for trip_row in doc.trips:
        existing_groups = frappe.get_all(
            "Trip Group Detail",
            filters={
                "trip": trip_row.trip,
                "parent": ["!=", doc.name],
                "parenttype": "Trip Group"
            }
        )
        
        if existing_groups:
            frappe.throw(_(f"Trip {trip_row.trip} is already part of another group"))

def calculate_total_amount(doc):
    """Calculate total amount from all trips"""
    frappe.log_error("Starting total calculation", "Trip Group")
    try:
        total = 0
        for trip in doc.trips:
            trip_amount = (float(trip.rate) * float(trip.quantity)) if trip.rate and trip.quantity else 0
            total += trip_amount
            frappe.log_error(f"Trip {trip.trip}: Rate={trip.rate}, Qty={trip.quantity}, Amount={trip_amount}", "Trip Group")
        
        doc.total_amount = total
        frappe.log_error(f"Final total: {total}", "Trip Group")
    except Exception as e:
        frappe.log_error(f"Error calculating total: {str(e)}", "Trip Group Error")

def create_service_item(doc, method):
    """Create service item after Trip Group is created"""
    frappe.log_error("Starting service item creation", "Trip Group")
    try:
        item_code = f"GRP-{doc.name}"
        
        if not frappe.db.exists("Item", item_code):
            item = frappe.get_doc({
                "doctype": "Item",
                "item_code": item_code,
                "item_name": item_code,
                "item_group": "Services",
                "stock_uom": "Each",
                "is_stock_item": 0,
                "is_fixed_asset": 0,
                "description": f"Group Service Item for Trip Group: {doc.name}",
                "standard_rate": doc.total_amount
            })
            item.insert(ignore_permissions=True)
            doc.db_set('service_item', item_code)
            frappe.log_error(f"Created service item: {item_code}", "Trip Group")
    except Exception as e:
        frappe.log_error(f"Error creating service item: {str(e)}", "Trip Group Error")

def update_service_item(doc, method):
    """Update service item when Trip Group is modified"""
    if doc.service_item:
        try:
            item = frappe.get_doc("Item", doc.service_item)
            item.standard_rate = doc.total_amount
            item.save(ignore_permissions=True)
            frappe.log_error(f"Updated service item: {doc.service_item}", "Trip Group")
        except Exception as e:
            frappe.log_error(f"Error updating service item: {str(e)}", "Trip Group Error")

def prevent_deletion_if_invoiced(doc, method):
    """Prevent deletion if Trip Group is invoiced"""
    if doc.sales_invoice_status == "Invoiced":
        frappe.throw(_("Cannot delete an invoiced Trip Group"))

def handle_sales_invoice_submit(doc, method):
    """Update Trip Groups and their trips when invoice is submitted"""
    for item in doc.items:
        if item.item_code.startswith('GRP-'):
            trip_groups = frappe.get_all(
                "Trip Group",
                filters={"service_item": item.item_code}
            )
            
            for group in trip_groups:
                trip_group = frappe.get_doc("Trip Group", group.name)
                update_invoice_status(trip_group, doc.name)

def update_invoice_status(trip_group, invoice_name):
    """Update Trip Group and its trips with invoice status"""
    trip_group.sales_invoice = invoice_name
    trip_group.sales_invoice_status = "Invoiced"
    trip_group.save(ignore_permissions=True)
    
    for trip_detail in trip_group.trips:
        trip = frappe.get_doc("Trip", trip_detail.trip)
        trip.sales_invoice_status = "Invoiced"
        trip.save(ignore_permissions=True)

@frappe.whitelist()
def create_service_item(trip_group):
    doc = frappe.get_doc("Trip Group", trip_group)
    item_code = f"GRP-{doc.name}"
    
    if not frappe.db.exists("Item", item_code):
        item = frappe.get_doc({
            "doctype": "Item",
            "item_code": item_code,
            "item_name": item_code,
            "item_group": "Services",
            "stock_uom": "Each",
            "is_stock_item": 0,
            "is_fixed_asset": 0,
            "description": f"Group Service Item for Trip Group: {doc.name}",
            "standard_rate": doc.total_amount,
            "is_sales_item": 1,
            "has_variants": 0,
            "include_item_in_manufacturing": 0,
            "opening_stock": 0,
            "valuation_rate": doc.total_amount,
            "standard_rate": doc.total_amount
        })
        item.insert(ignore_permissions=True)
        doc.service_item = item_code
        doc.save(ignore_permissions=True)
        return item_code
    else:
        # Only update if total has changed
        item = frappe.get_doc("Item", item_code)
        if item.standard_rate != doc.total_amount:
            item.standard_rate = doc.total_amount
            item.valuation_rate = doc.total_amount
            item.save(ignore_permissions=True)
        return item_code