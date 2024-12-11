import frappe
from frappe.model.document import Document

class DocTypeFieldLabel(Document):
    def validate(self):
        # If custom label is empty, make sure is_active is False
        if not self.custom_label and self.is_active:
            self.is_active = 0
            
        # If custom label is provided but inactive, set active
        elif self.custom_label and not self.is_active:
            self.is_active = 1