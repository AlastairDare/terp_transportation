import frappe
from frappe.model.document import Document

class SubscriptionSettings(Document):
    def validate(self):
        """Validate Subscription Settings"""
        pass