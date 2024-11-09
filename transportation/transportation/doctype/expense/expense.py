import frappe
from frappe import _
from frappe.model.document import Document

class Expense(Document):
    def validate(self):
        self.validate_reference()
    
    def validate_reference(self):
        """Validate that the correct reference field is filled based on expense type"""
        if self.expense_type == "Toll" and not self.toll_reference:
            frappe.throw(_("Toll Reference is required for Toll expense type"))
        elif self.expense_type == "Refuel" and not self.refuel_reference:
            frappe.throw(_("Refuel Reference is required for Refuel expense type"))
        elif self.expense_type == "Unified Maintenance" and not self.maintenance_reference:
            frappe.throw(_("Maintenance Reference is required for Unified Maintenance expense type"))