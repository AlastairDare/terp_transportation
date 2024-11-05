from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class AssetMaintenanceStockItem(Document):
    def validate(self):
        self.validate_quantity()
        self.calculate_amount()
    
    def validate_quantity(self):
        if self.qty <= 0:
            frappe.throw("Quantity must be greater than 0")
    
    def calculate_amount(self):
        self.amount = self.qty * self.rate if self.qty and self.rate else 0