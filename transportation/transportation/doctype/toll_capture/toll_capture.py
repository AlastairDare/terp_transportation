import frappe
import tabula
import pandas as pd
import pdfplumber  # This should be installed with tabula-py
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
        
        # First try reading with pdfplumber
        with pdfplumber.open(file_path) as pdf:
            # Get first page
            first_page = pdf.pages[0]
            
            # Extract table
            table = first_page.extract_table()
            
            if table:
                # Show headers
                headers = table[0]
                frappe.msgprint("Headers found: " + ", ".join(str(h) for h in headers if h))
                
                # Show first row
                if len(table) > 1:
                    first_row = table[1]
                    frappe.msgprint("First data row: " + ", ".join(str(d) for d in first_row if d))
                    
                # Show second row
                if len(table) > 2:
                    second_row = table[2]
                    frappe.msgprint("Second data row: " + ", ".join(str(d) for d in second_row if d))
            else:
                frappe.msgprint("No table found with pdfplumber")
            
        # Now try with tabula with different options
        tables = tabula.read_pdf(
            file_path,
            pages='1',
            stream=True,
            guess=False,
            spreadsheet=True,
            multiple_tables=False
        )
        
        if tables and len(tables) > 0:
            first_table = tables[0]
            frappe.msgprint("Tabula columns: " + ", ".join(first_table.columns.tolist()))
            
            if len(first_table) > 0:
                first_row = first_table.iloc[0]
                frappe.msgprint("Tabula first row: " + ", ".join(str(v) for v in first_row.values))
        
        raise Exception("Debug pause - check all messages above")
            
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