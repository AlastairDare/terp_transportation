import frappe
import tabula
import pandas as pd
from frappe.utils.file_manager import get_file_path
from frappe.model.document import Document

def validate(doc, method):
    if not doc.toll_document:
        frappe.throw("Toll document is required")
        
    file_path = get_file_path(doc.toll_document)
    if not file_path.lower().endswith('.pdf'):
        frappe.throw("Only PDF files are supported")

def process_toll_records(doc):
    try:
        file_path = get_file_path(doc.toll_document)
        doc.db_set('processing_status', 'Processing')
        
        # Basic tabula read first
        tables = tabula.read_pdf(
            file_path,
            pages='1',  # Just first page
            multiple_tables=True
        )
        
        # Immediate feedback
        frappe.msgprint("Step 1: Reading PDF")
        frappe.db.commit()  # Make sure message shows
        
        if not tables:
            frappe.msgprint("No tables found")
            return
            
        frappe.msgprint(f"Found {len(tables)} tables")
        frappe.db.commit()
        
        # Look at first table
        first_table = tables[0]
        frappe.msgprint("Step 2: First Table Details")
        frappe.db.commit()
        
        # Look at columns
        col_str = str(first_table.columns.tolist())[:100]  # Truncate to avoid length issues
        frappe.msgprint(f"Columns (truncated): {col_str}")
        frappe.db.commit()
        
        # Look at shape
        frappe.msgprint(f"Table shape: {first_table.shape}")
        frappe.db.commit()
        
        # Look at first row
        if len(first_table) > 0:
            row_str = str(first_table.iloc[0].tolist())[:100]
            frappe.msgprint(f"First row (truncated): {row_str}")
            frappe.db.commit()
        
        raise Exception("Debug complete - check messages above")
            
    except Exception as e:
        doc.db_set('processing_status', 'Failed')
        raise

class TollCapture(Document):
    def validate(self):
        if not self.name:
            self.processing_status = "Pending"
            self.progress_count = ""
            self.total_records = 0
            self.new_records = 0
            self.duplicate_records = 0

    def process_document(self):
        process_toll_records(self)

@frappe.whitelist()
def process_toll_document(doc_name):
    try:
        doc = frappe.get_doc("Toll Capture", doc_name)
        doc.process_document()
        return "Processing Complete"
    except Exception as e:
        frappe.throw(str(e))