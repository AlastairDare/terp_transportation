import frappe
from frappe.model.document import Document

def validate(doc, method):
    """Module-level validation for tolls"""
    if not doc.transaction_date:
        frappe.throw("Transaction Date & Time is required")
        
    if not doc.tolling_point:
        frappe.throw("TA/Tolling Point is required")
        
    if not doc.etag_id:
        frappe.throw("e-tag ID is required")
        
    if not doc.net_amount:
        frappe.throw("Net Amount is required")

class Tolls(Document):
    pass  # All validation handled at module level