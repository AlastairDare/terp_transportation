import frappe
import pdfplumber
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
        
        # Read with pdfplumber
        with pdfplumber.open(file_path) as pdf:
            # Get first page
            first_page = pdf.pages[0]
            
            # Extract table
            table = first_page.extract_table()
            
            if table:
                # Show first few rows
                for i, row in enumerate(table[:5]):  # Show first 5 rows
                    # Clean the row data (remove None and empty strings)
                    clean_row = [str(cell) for cell in row if cell and str(cell).strip()]
                    if clean_row:  # Only show rows that have data
                        frappe.msgprint(f"Row {i}: {' | '.join(clean_row)}")
            else:
                frappe.msgprint("No table found with pdfplumber")
                
            # Also try to get raw text to see structure
            text = first_page.extract_text()
            frappe.msgprint("Raw text sample (first 200 chars):")
            frappe.msgprint(text[:200] if text else "No text found")
            
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