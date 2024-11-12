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
            
            # First try without specifying columns
            tables = tabula.read_pdf(
                file_path,
                pages='all',
                multiple_tables=True,
                lattice=True
            )
            
            if not tables:
                raise Exception("No tables found in PDF document")
            
            # Combine all tables
            df = pd.concat(tables)
            
            # Log the found columns for debugging
            frappe.log_error(f"Found columns: {df.columns.tolist()}", "PDF Processing")
            
            # Clean column names
            df.columns = [str(col).strip().replace('\n', ' ') for col in df.columns]
            
            # Map the columns we need
            column_mapping = {
                'Transaction Date & Time': 'transaction_date',
                'TA/Tolling Point': 'tolling_point',
                'e-tag ID': 'etag_id',
                'Net Amount': 'net_amount'
            }
            
            # Create a new DataFrame with just the columns we need
            processed_data = []
            
            for index, row in df.iterrows():
                try:
                    # Clean and parse the date
                    date_str = str(row['Transaction Date & Time']).strip()
                    transaction_date = pd.to_datetime(date_str, format='%Y/%m/%d %I:%M:%S %p')
                    
                    # Clean and parse the amount (remove 'R ' and convert to float)
                    amount_str = str(row['Net Amount']).replace('R ', '').replace(',', '').strip()
                    net_amount = float(amount_str) if amount_str else 0.0
                    
                    # Create cleaned record
                    processed_data.append({
                        'transaction_date': transaction_date.strftime('%Y-%m-%d %H:%M:%S'),
                        'tolling_point': str(row['TA/Tolling Point']).strip(),
                        'etag_id': str(row['e-tag ID']).strip(),
                        'net_amount': net_amount
                    })
                    
                except Exception as row_error:
                    frappe.log_error(f"Error processing row {index}: {str(row_error)}\nRow data: {row.to_dict()}", 
                                   "Row Processing Error")
                    continue
            
            total_records = len(processed_data)
            self.db_set('total_records', total_records)
            
            # Process records
            duplicates = []
            new_records = []
            
            for index, data in enumerate(processed_data):
                self.db_set('progress_count', f"Processing records: {index + 1}/{total_records}")
                
                # Check for duplicates
                exists = frappe.db.exists("Tolls", {
                    "transaction_date": data['transaction_date'],
                    "etag_id": data['etag_id'],
                    "tolling_point": data['tolling_point']
                })
                
                if exists:
                    duplicates.append(data)
                else:
                    new_records.append({
                        "doctype": "Tolls",
                        "transaction_date": data['transaction_date'],
                        "tolling_point": data['tolling_point'],
                        "etag_id": data['etag_id'],
                        "net_amount": data['net_amount'],
                        "process_status": "Unprocessed",
                        "source_capture": self.name
                    })
                
                # Insert in batches of 100
                if len(new_records) >= 100:
                    frappe.db.bulk_insert("Tolls", new_records)
                    new_records = []
            
            # Insert remaining records
            if new_records:
                frappe.db.bulk_insert("Tolls", new_records)
            
            # Update final counts and status
            self.db_set('duplicate_records', len(duplicates))
            self.db_set('new_records', total_records - len(duplicates))
            self.db_set('processing_status', 'Completed')
            
        except Exception as e:
            self.db_set('processing_status', 'Failed')
            frappe.log_error(str(e), "Toll Capture Processing Error")
            raise

@frappe.whitelist()
def process_toll_document(doc_name):
    """Whitelist method to process toll documents"""
    try:
        doc = frappe.get_doc("Toll Capture", doc_name)
        doc.process_document()
        return "Processing Complete"
    except Exception as e:
        frappe.log_error(str(e), "Toll Document Processing Error")
        frappe.throw(f"Failed to process toll document: {str(e)}")