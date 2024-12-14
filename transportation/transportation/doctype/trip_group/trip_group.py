import frappe
from frappe import _
from frappe.model.document import Document

class TripGroup(Document):
    def validate(self):
        self.validate_trips()
        self.calculate_total_amount()
        
    def validate_trips(self):
        """Ensure trips are not already in another group"""
        for trip_row in self.trips:
            if not trip_row.trip:
                continue
                
            # Skip validation for this doc when updating
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
        total = 0
        for trip_row in self.trips:
            # Get the actual trip document to ensure we have current values
            if trip_row.trip:
                trip = frappe.get_doc("Trip", trip_row.trip)
                trip_amount = (trip.rate or 0) * (trip.quantity or 0)
                total += trip_amount
                
                # Update the child record amounts
                trip_row.rate = trip.rate
                trip_row.quantity = trip.quantity
                trip_row.amount = trip_amount
                
        self.total_amount = total
        
    def before_save(self):
        """Ensure service item exists before saving"""
        if not self.service_item:
            self.create_service_item()

    def create_service_item(self):
        """Create a service item for the Trip Group"""
        if not self.total_amount:
            self.calculate_total_amount()
            
        item_code = f"GRP-{self.name}"
        
        if not frappe.db.exists("Item", item_code):
            item = frappe.get_doc({
                "doctype": "Item",
                "item_code": item_code,
                "item_name": item_code,
                "item_group": "Services",
                "stock_uom": "Each",
                "is_stock_item": 0,
                "is_fixed_asset": 0,
                "description": f"Group Service Item for Trip Group: {self.name}",
                "standard_rate": self.total_amount
            })
            item.insert(ignore_permissions=True)
            
            # Update Trip Group with service item reference
            self.service_item = item_code
    
    def update_service_item(self):
        """Update service item details"""
        if self.service_item:
            item = frappe.get_doc("Item", self.service_item)
            item.standard_rate = self.total_amount
            item.save(ignore_permissions=True)

    def on_update(self):
        """Update service item when Trip Group is modified"""
        if self.service_item:
            self.update_service_item()
        else:
            self.create_service_item()

    def on_trash(self):
        """Handle deletion of Trip Group"""
        if self.sales_invoice_status == "Invoiced":
            frappe.throw(_("Cannot delete an invoiced Trip Group"))