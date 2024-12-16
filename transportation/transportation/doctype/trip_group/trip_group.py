from __future__ import unicode_literals
import frappe
import json
from frappe import _
from frappe.model.document import Document

class TripGroup(Document):
    def validate(self):
        """Validate Trip Group document before saving"""
        self.validate_trips()
        self.calculate_total_amount()
        
    def validate_trips(self):
        """Ensure trips are not already in another group"""
        for trip_row in self.trips:
            existing_groups = frappe.get_all(
                "Trip Group Detail",
                filters={
                    "trip": trip_row.trip,
                    "parent": ["!=", self.name],
                    "parenttype": "Trip Group"
                }
            )
            
            if existing_groups:
                frappe.throw(_(f"Trip {trip_row.trip} is already part of another group"))
    
    def calculate_total_amount(self):
        """Calculate total amount from all trips"""
        try:
            total = 0
            for trip in self.trips:
                if trip.rate and trip.quantity:
                    total += float(trip.rate) * float(trip.quantity)
            self.total_amount = total
        except Exception as e:
            frappe.log_error(f"Error calculating total: {str(e)}", "Trip Group Error")
            frappe.throw(_("Error calculating total amount"))
    
    def on_update(self):
        """Handle updates to service item when Trip Group is modified"""
        frappe.log_error("on_update triggered", "Trip Group Debug")
        
        if self.service_item:  # Check if service_item exists
            frappe.log_error(f"Service item found: {self.service_item}", "Trip Group Debug")
            if frappe.db.exists("Item", self.service_item):  # Check if Item exists
                try:
                    item = frappe.get_doc("Item", self.service_item)
                    frappe.log_error(f"Current item rate: {item.standard_rate}, New total: {self.total_amount}", "Trip Group Debug")
                    
                    if float(item.standard_rate) != float(self.total_amount):
                        item.standard_rate = self.total_amount
                        item.valuation_rate = self.total_amount
                        item.save(ignore_permissions=True)
                        frappe.log_error(f"Updated service item rates to: {self.total_amount}", "Trip Group Debug")
                except Exception as e:
                    frappe.log_error(f"Error updating service item: {str(e)}", "Trip Group Error")
                    
    def before_save(self):
        frappe.log_error("before_save triggered", "Trip Group Debug")

    def after_save(self):
        frappe.log_error("after_save triggered", "Trip Group Debug")

    def before_submit(self):
        frappe.log_error("before_submit triggered", "Trip Group Debug")

    def on_update(self):
        frappe.log_error("on_update triggered", "Trip Group Debug")

    def on_change(self):
        frappe.log_error("on_change triggered", "Trip Group Debug")

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
    """Create or update service item for Trip Group"""
    doc = frappe.get_doc("Trip Group", trip_group)
    item_code = f"GRP-{doc.name}"
    
    try:
        if not frappe.db.exists("Item", item_code):
            # Create new service item
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
                "valuation_rate": doc.total_amount
            })
            item.insert(ignore_permissions=True)
            doc.service_item = item_code
            doc.save(ignore_permissions=True)
            
            frappe.msgprint(
                msg=f"""<div><p>{_("Group Service Item created successfully: {0}").format(item_code)}</p></div>""",
                title=_("Service Item Created"),
                indicator="green"
            )
        else:
            # Update existing service item
            item = frappe.get_doc("Item", item_code)
            if item.standard_rate != doc.total_amount:
                item.standard_rate = doc.total_amount
                item.valuation_rate = doc.total_amount
                item.save(ignore_permissions=True)
        
        return item_code
        
    except Exception as e:
        frappe.log_error(f"Error handling service item: {str(e)}", "Trip Group Error")
        frappe.throw(_("Failed to process service item. Error: {0}").format(str(e)))