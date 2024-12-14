import frappe
from frappe import _
from frappe.model.document import Document

class TripGroup(Document):
    def validate(self):
        try:
            self.validate_trips()
            self.calculate_total_amount()
            frappe.log_error(f"Total amount calculated: {self.total_amount}", "Trip Group Validation")
        except Exception as e:
            frappe.log_error(f"Error in validate: {str(e)}", "Trip Group Error")
        
    def validate_trips(self):
        """Ensure trips are not already in another group"""
        for trip_row in self.trips:
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
        try:
            self.total_amount = sum((trip.rate * trip.quantity) for trip in self.trips)
            frappe.log_error(f"Trips count: {len(self.trips)}, Total: {self.total_amount}", "Trip Group Amount Calc")
        except Exception as e:
            frappe.log_error(f"Error calculating total: {str(e)}", "Trip Group Error")

    def after_insert(self):
        try:
            frappe.log_error("Attempting after_insert", "Trip Group")
            self.create_service_item()
        except Exception as e:
            frappe.log_error(f"Error in after_insert: {str(e)}", "Trip Group Error")

    def on_update(self):
        """Update service item when Trip Group is modified"""
        try:
            if self.service_item:
                self.update_service_item()
            else:
                self.create_service_item()
        except Exception as e:
            frappe.log_error(f"Error in on_update: {str(e)}", "Trip Group Error")

    def create_service_item(self):
        try:
            item_code = f"GRP-{self.name}"
            frappe.log_error(f"Creating service item with code: {item_code}", "Trip Group")
            
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
                self.service_item = item_code
                self.save()
                frappe.log_error(f"Service item created: {item_code}", "Trip Group")
        except Exception as e:
            frappe.log_error(f"Error creating service item: {str(e)}", "Trip Group Error")
    
    def update_service_item(self):
        """Update service item details"""
        if self.service_item:
            item = frappe.get_doc("Item", self.service_item)
            item.standard_rate = self.total_amount
            item.save(ignore_permissions=True)

    def on_trash(self):
        """Handle deletion of Trip Group"""
        if self.sales_invoice_status == "Invoiced":
            frappe.throw(_("Cannot delete an invoiced Trip Group"))

    def handle_sales_invoice_submit(self, invoice_name):
        """Update Trip Group and associated trips when invoice is submitted"""
        self.sales_invoice = invoice_name
        self.sales_invoice_status = "Invoiced"
        self.save(ignore_permissions=True)
        
        # Update all associated trips
        for trip_detail in self.trips:
            trip = frappe.get_doc("Trip", trip_detail.trip)
            trip.sales_invoice_status = "Invoiced"
            trip.save(ignore_permissions=True)

def get_available_trips(doctype, txt, searchfield, start, page_len, filters):
    """Get list of trips not already in groups"""
    return frappe.db.sql("""
        SELECT t.name, t.date, t.license_plate
        FROM `tabTrip` t
        WHERE NOT EXISTS (
            SELECT 1 
            FROM `tabTrip Group Detail` tgd
            WHERE tgd.trip = t.name
        )
        AND t.name LIKE %(txt)s
        ORDER BY t.date DESC
        LIMIT %(start)s, %(page_len)s
    """, {
        'txt': f"%{txt}%",
        'start': start,
        'page_len': page_len
    })