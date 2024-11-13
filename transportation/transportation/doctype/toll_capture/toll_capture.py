import frappe
from frappe import _
from frappe.model.document import Document
from transportation.transportation.ai_processing.chain_builder import process_toll_document

class TollCapture(Document):
    def validate(self):
        if not self.toll_document:
            frappe.throw(_("Please attach a Toll document"))
            
    def before_save(self):
        # Reset counters if new document is attached
        if self.has_value_changed('toll_document'):
            self.processing_status = 'Pending'
            self.progress_count = ''
            self.total_records = 0
            self.new_records = 0
            self.duplicate_records = 0

@frappe.whitelist()
def process_toll_document_handler(doc_name):
    """Handler for the process button click"""
    return process_toll_document(doc_name)