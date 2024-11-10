import frappe
import tabula
import pandas as pd
from frappe.utils.file_manager import get_file_path

class ETollCapture:
    def __init__(self, doc):
        self.doc = doc
        self.processed_data = None
        
    def update_status(self, status, progress=None):
        """Update processing status and progress in the document"""
        self.doc.processing_status = status
        if progress:
            self.doc.progress_count = progress
        self.doc.save()
        frappe.db.commit()
        
    def process_document(self):
        try:
            # Get file path
            file_path = get_file_path(self.doc.toll_document)
            
            # Update status
            self.update_status("Extracting e-toll data...")
            
            # Read tables from PDF
            tables = tabula.read_pdf(file_path, pages='all')
            
            # Convert to single DataFrame and clean up
            df = pd.concat(tables)
            df = df[df['Transaction Date & Time'].notna()]  # Remove empty rows
            
            self.processed_data = df
            total_records = len(df)
            self.doc.total_records = total_records
            
            # Check for duplicates
            self.update_status("Checking for duplicates")
            duplicates = []
            new_records = []
            
            for index, row in df.iterrows():
                # Update progress
                progress = f"Checking for duplicates: {index + 1}/{total_records}"
                self.update_status("Checking for duplicates", progress)
                
                # Check if record exists
                exists = frappe.db.exists("Tolls", {
                    "transaction_date": pd.to_datetime(row['Transaction Date & Time']).strftime('%Y-%m-%d %H:%M:%S'),
                    "etag_id": row['e-tag ID']
                })
                
                if exists:
                    duplicates.append(row)
                else:
                    new_records.append(row)
            
            # Update counts
            self.doc.duplicate_records = len(duplicates)
            self.doc.new_records = len(new_records)
            
            # Create new toll records
            self.update_status(f"Saving {len(new_records)} new records...")
            
            for record in new_records:
                toll = frappe.get_doc({
                    "doctype": "Tolls",
                    "transaction_date": pd.to_datetime(record['Transaction Date & Time']).strftime('%Y-%m-%d %H:%M:%S'),
                    "tolling_point": record['TA/Tolling Point'],
                    "etag_id": record['e-tag ID'],
                    "net_amount": record['Net Amount'],
                    "process_status": "Unprocessed",
                    "source_capture": self.doc.name
                })
                toll.insert()
            
            self.update_status(f"{len(new_records)} New E-Toll Records Saved")
            
        except Exception as e:
            frappe.throw(f"Error processing document: {str(e)}")

@frappe.whitelist()
def process_etoll_document(doc_name):
    doc = frappe.get_doc("E-Toll Capture", doc_name)
    processor = ETollCapture(doc)
    processor.process_document()
    return "Processing Complete"