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
        
        frappe.msgprint("Starting PDF read...")
        
        # Try reading with more specific area
        tables = tabula.read_pdf(
            file_path,
            pages='all',
            multiple_tables=False,  # Just get one table
            area=[250, 0, 700, 1000],  # Adjusted to focus below "Toll Transactions"
            pandas_options={'header': 0}  # Use first row as header
        )
        
        if isinstance(tables, list):
            first_table = tables[0]
        else:
            first_table = tables
            
        frappe.msgprint(f"Table shape: {first_table.shape}")
        
        # Show all column names
        frappe.msgprint("All columns found:")
        for i, col in enumerate(first_table.columns):
            frappe.msgprint(f"Column {i}: {str(col)}")
            
        # Show first row of data
        if len(first_table) > 0:
            frappe.msgprint("First row data:")
            first_row = first_table.iloc[0]
            for col, val in first_row.items():
                frappe.msgprint(f"{col}: {val}")
        
        doc.db_set('processing_status', 'Completed')
        return "Debug mode - check messages"
            
    except Exception as e:
        doc.db_set('processing_status', 'Failed')
        frappe.msgprint(f"Error: {str(e)}")
        return

class TollCapture(Document):
    def validate(self):
        if not self.name:
            self.processing_status = "Pending"
            self.progress_count = ""
            self.total_records = 0
            self.new_records = 0
            self.duplicate_records = 0

    def process_document(self):
        return process_toll_records(self)

@frappe.whitelist()
def process_toll_document(doc_name):
    try:
        doc = frappe.get_doc("Toll Capture", doc_name)
        result = doc.process_document()
        return result or "Processing Complete"
    except Exception as e:
        frappe.msgprint(f"Error in processing: {str(e)}")
        return "Failed"