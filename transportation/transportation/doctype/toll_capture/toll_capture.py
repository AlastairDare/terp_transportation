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
        
        # Try with specific table settings
        tables = tabula.read_pdf(
            file_path,
            pages='all',
            multiple_tables=True,
            lattice=False,  # Change to False since it's not strictly a grid
            stream=True,    # Use stream mode for less structured tables
            guess=False,    # Don't guess the table structure
            area=[250, 0, 700, 1000],  # Adjust area to focus on data
            columns=[50, 150, 250, 350, 450, 550, 650, 750]  # Try to define column positions
        )
        
        if not tables:
            frappe.throw("No tables found in PDF")
            
        # Combine all tables
        df = pd.concat(tables)
        
        # Look for date-like columns
        date_col = None
        for col in df.columns:
            sample_value = str(df[col].iloc[0]) if len(df) > 0 else ""
            if '2024' in sample_value and ':' in sample_value:
                date_col = col
                break
                
        frappe.msgprint(f"Found these columns: {', '.join(df.columns.tolist())}")
        if date_col:
            frappe.msgprint(f"Found date column: {date_col}")
            frappe.msgprint(f"Sample date: {df[date_col].iloc[0] if len(df) > 0 else 'No data'}")
            
        # Show first row data
        if len(df) > 0:
            first_row = df.iloc[0]
            frappe.msgprint("First row data (sample):")
            for col in df.columns[:3]:  # Show first 3 columns
                frappe.msgprint(f"{col}: {first_row[col]}")
        
        # Continue with more detailed debugging info
        total_rows = len(df)
        frappe.msgprint(f"Total rows found: {total_rows}")
        
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