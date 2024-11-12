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

def clean_table_data(df):
    """Clean up table data by combining split rows"""
    try:
        # Show initial state
        frappe.msgprint(f"Initial columns: {df.columns.tolist()[:5]}...")  # Show first 5
        
        # Try to find date pattern in any column
        for col in df.columns:
            sample = str(df[col].iloc[0]) if len(df) > 0 else ""
            if '2024/' in sample:
                frappe.msgprint(f"Found date in column: {col}")
                frappe.msgprint(f"Sample value: {sample}")
        
        return df
    except Exception as e:
        frappe.msgprint(f"Error in cleaning: {str(e)}")
        return df

def process_toll_records(doc):
    try:
        file_path = get_file_path(doc.toll_document)
        doc.db_set('processing_status', 'Processing')
        
        # Try different table extraction settings
        tables = tabula.read_pdf(
            file_path,
            pages='all',
            multiple_tables=True,
            lattice=True,  # Try lattice mode first
            pandas_options={
                'header': None,  # Don't use first row as header
            },
            area=[300, 0, 700, 1000],  # Focus more on transaction area
            relative_area=True,  # Use relative coordinates
            guess=False  # Don't guess the structure
        )
        
        if not tables:
            frappe.throw("No tables found in PDF")
            
        frappe.msgprint(f"Found {len(tables)} tables")
        
        # Process each table
        for i, table in enumerate(tables):
            frappe.msgprint(f"\nTable {i+1}:")
            frappe.msgprint(f"Shape: {table.shape}")
            
            # Show first few cells of first row
            if len(table) > 0:
                first_row = table.iloc[0]
                sample_data = [str(val)[:30] for val in first_row.values[:3]]
                frappe.msgprint(f"Sample data: {', '.join(sample_data)}")
            
            # Clean and analyze table
            cleaned_table = clean_table_data(table)
            
            # If this table has our transaction data, process it
            if any('2024/' in str(val) for val in cleaned_table.values.flatten()):
                frappe.msgprint("Found transaction table!")
                return "Found potential transaction table - check the logs"
        
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