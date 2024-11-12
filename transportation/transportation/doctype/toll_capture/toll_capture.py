import frappe
import tabula
import pandas as pd
from frappe.utils.file_manager import get_file_path
from frappe.utils import get_datetime_str
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
        
        # Read tables from PDF with specific area
        tables = tabula.read_pdf(
            file_path,
            pages='all',
            stream=True,               # Use stream mode instead of lattice
            multiple_tables=True
        )
        
        # Debug first table structure
        if tables and len(tables) > 0:
            first_table = tables[0]
            frappe.msgprint(f"Found {len(tables)} tables")
            
            # Show columns in chunks
            columns = first_table.columns.tolist()
            for i in range(0, len(columns), 3):
                chunk = columns[i:i+3]
                frappe.msgprint(f"Columns {i}-{i+2}: {chunk}")
            
            # Show first row data in chunks
            first_row = first_table.iloc[0]
            for i, value in enumerate(first_row):
                frappe.msgprint(f"Column {i} value: {value}")
        else:
            frappe.msgprint("No tables found in PDF")
            
        raise Exception("Debug pause - check messages")
            
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