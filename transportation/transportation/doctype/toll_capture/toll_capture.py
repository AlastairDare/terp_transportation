import frappe
import fitz  # PyMuPDF
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
        
        # Open PDF
        pdf_doc = fitz.open(file_path)
        
        # Expected columns
        expected_columns = [
            "Transaction Date & Time",
            "TA/ Tolling Point",
            "Vehicle Licence Plate Number",
            "e-tag ID",
            "Detected TA Class",
            "Nominal Amount",
            "Discount",
            "Net Amount",
            "VAT"
        ]
        
        all_data = []
        
        # Process each page
        for page in pdf_doc:
            # Get text blocks
            blocks = page.get_text("blocks")
            
            # Look for blocks that contain transaction data
            for block in blocks:
                text = block[4]  # block[4] contains the text
                
                # If we find a date pattern (2024/), process the block
                if "2024/" in text:
                    # Split into lines and process
                    lines = text.split('\n')
                    for line in lines:
                        if "2024/" in line:
                            # Clean and split the line
                            data = line.strip().split()
                            if len(data) > 8:  # Make sure we have enough data
                                all_data.append(line)
        
        # Convert to DataFrame
        if all_data:
            frappe.msgprint("Found transaction data. Sample records:")
            
            # Show first two records
            if len(all_data) > 0:
                frappe.msgprint("\nFirst record:")
                frappe.msgprint(all_data[0])
            if len(all_data) > 1:
                frappe.msgprint("\nSecond record:")
                frappe.msgprint(all_data[1])
            
            # Show last two records
            if len(all_data) > 2:
                frappe.msgprint("\nSecond to last record:")
                frappe.msgprint(all_data[-2])
                frappe.msgprint("\nLast record:")
                frappe.msgprint(all_data[-1])
            
            frappe.msgprint(f"\nTotal records found: {len(all_data)}")
        else:
            frappe.msgprint("No transaction data found")
        
        doc.db_set('processing_status', 'Completed')
        return "Debug mode - check sample records"
            
    except Exception as e:
        doc.db_set('processing_status', 'Failed')
        frappe.msgprint(f"Error: {str(e)}")
        return
    finally:
        if 'pdf_doc' in locals():
            pdf_doc.close()

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