import frappe
import tabula
import pandas as pd
from frappe.utils.file_manager import get_file_path
from frappe.model.document import Document

class TollCapture(Document):
    def validate(self):
        if not self.toll_document:
            frappe.throw("Toll document is required")
            
        # Validate file format
        file_path = get_file_path(self.toll_document)
        if not file_path.lower().endswith('.pdf'):
            frappe.throw("Only PDF files are supported")
            
        # Reset processing status for new documents
        if not self.name:
            self.processing_status = "Pending"
            self.progress_count = ""
            self.total_records = 0
            self.new_records = 0
            self.duplicate_records = 0

    def process_document(self):
        """Process the uploaded PDF document and create toll records"""
        try:
            # Get file path and update status
            file_path = get_file_path(self.toll_document)
            self.db_set('processing_status', 'Processing')
            
            # Try reading with default settings first
            tables = tabula.read_pdf(
                file_path,
                pages='all',
                guess=False,  # Don't guess the table structure
                area=[120, 0, 750, 1000],  # Approximate area where the table is
                multiple_tables=True
            )
            
            if not tables:
                raise Exception("No tables found in PDF document")
            
            # Combine all tables
            df = pd.concat(tables)
            
            # Process records
            total_records = len(df)
            self.db_set('total_records', total_records)
            
            duplicates = []
            new_records = []
            
            for index, row in df.iterrows():
                self.db_set('progress_count', f"Processing record {index + 1} of {total_records}")
                
                try:
                    # Extract and clean data
                    date_str = str(row['Transaction Date & Time']).strip()
                    transaction_date = pd.to_datetime(date_str, format='%Y/%m/%d %I:%M:%S %p')
                    tolling_point = str(row['TA/Tolling Point']).strip()
                    etag_id = str(row['e-tag ID']).strip()
                    net_amount = float(str(row['Net Amount']).replace('R ', '').replace(',', '').strip())
                    
                    # Check for duplicates
                    exists = frappe.db.exists("Tolls", {
                        "transaction_date": transaction_date.strftime('%Y-%m-%d %H:%M:%S'),
                        "etag_id": etag_id,
                        "tolling_point": tolling_point
                    })
                    
                    if exists:
                        duplicates.append(row)
                    else:
                        new_records.append({
                            "doctype": "Tolls",
                            "transaction_date": transaction_date.strftime('%Y-%m-%d %H:%M:%S'),
                            "tolling_point": tolling_point,
                            "etag_id": etag_id,
                            "net_amount": net_amount,
                            "process_status": "Unprocessed",
                            "source_capture": self.name
                        })
                        
                        # Insert in batches
                        if len(new_records) >= 100:
                            frappe.db.bulk_insert("Tolls", new_records)
                            new_records = []
                            
                except Exception as e:
                    continue
            
            # Insert remaining records
            if new_records:
                frappe.db.bulk_insert("Tolls", new_records)
            
            # Update final counts and status
            self.db_set('duplicate_records', len(duplicates))
            self.db_set('new_records', total_records - len(duplicates))
            self.db_set('processing_status', 'Completed')
            
        except Exception as e:
            self.db_set('processing_status', 'Failed')
            frappe.throw(str(e))

@frappe.whitelist()
def process_toll_document(doc_name):
    """Whitelist method to process toll documents"""
    try:
        doc = frappe.get_doc("Toll Capture", doc_name)
        doc.process_document()
        return "Processing Complete"
    except Exception as e:
        frappe.throw(str(e))