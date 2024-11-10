import frappe
from frappe.model.document import Document

class Tolls(Document):
    def validate(self):
        # Additional validation can be added here if needed
        pass