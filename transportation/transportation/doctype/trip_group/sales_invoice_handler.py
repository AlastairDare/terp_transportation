import frappe
from frappe import _

def on_submit(doc, method):
    """Handle Trip Group updates when Sales Invoice is submitted"""
    update_trip_groups(doc)

def update_trip_groups(invoice):
    """Update Trip Groups and their trips when invoice is submitted"""
    for item in invoice.items:
        if item.item_code.startswith('GRP-'):
            # Find associated Trip Group
            trip_groups = frappe.get_all(
                "Trip Group",
                filters={"service_item": item.item_code}
            )
            
            for group in trip_groups:
                trip_group = frappe.get_doc("Trip Group", group.name)
                
                # Update Trip Group
                trip_group.sales_invoice = invoice.name
                trip_group.sales_invoice_status = "Invoiced"
                trip_group.save(ignore_permissions=True)
                
                # Update all associated trips
                for trip_detail in trip_group.trips:
                    trip = frappe.get_doc("Trip", trip_detail.trip)
                    trip.sales_invoice_status = "Invoiced"
                    trip.save(ignore_permissions=True)

def validate(doc, method):
    """Prevent modifications to invoiced Trip Groups"""
    for item in doc.items:
        if item.item_code.startswith('GRP-'):
            trip_groups = frappe.get_all(
                "Trip Group",
                filters={"service_item": item.item_code}
            )
            
            for group in trip_groups:
                trip_group = frappe.get_doc("Trip Group", group.name)
                if trip_group.sales_invoice_status == "Invoiced":
                    frappe.throw(
                        _("Cannot modify Trip Group {0} as it is already invoiced")
                        .format(trip_group.name)
                    )