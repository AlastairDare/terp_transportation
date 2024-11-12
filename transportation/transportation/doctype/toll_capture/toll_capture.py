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
            
            # Define all columns in the exact order they appear in the PDF
            columns = [
                'Transaction Date & Time',
                'TA/Tolling Point',
                'Vehicle Licence Plate Number',
                'e-tag ID',
                'Detected TA Class',
                'Nominal Amount',
                'Discount',
                'Net Amount',
                'VAT'
            ]
            
            # Read tables from PDF with all columns in order
            tables = tabula.read_pdf(
                file_path,
                pages='all',
                multiple_tables=True,
                lattice=True,
                columns=columns
            )
            
            if not tables:
                raise Exception("No tables found in PDF document")
            
            # Combine all tables
            df = pd.concat(tables)
            
            # Filter only the columns we need
            needed_columns = ['Transaction Date & Time', 'TA/Tolling Point', 'e-tag ID', 'Net Amount']
            df = df[needed_columns]
            
            # Remove rows where all needed columns are empty
            df = df.dropna(subset=needed_columns, how='all')
            
            total_records = len(df)
            self.db_set('total_records', total_records)
            
            duplicates = []
            new_records = []
            
            for index, row in df.iterrows():
                # Update progress
                self.db_set('progress_count', f"Processing records: {index + 1}/{total_records}")
                
                try:
                    # Clean up date format and convert to datetime
                    transaction_date = pd.to_datetime(row['Transaction Date & Time'], format='%Y/%m/%d %I:%M:%S %p')
                    
                    # Clean up net amount (remove 'R ' and convert to float)
                    net_amount = float(str(row['Net Amount']).replace('R ', '').replace(',', '').strip())
                    
                    # Check for duplicates
                    exists = frappe.db.exists("Tolls", {
                        "transaction_date": transaction_date.strftime('%Y-%m-%d %H:%M:%S'),
                        "etag_id": str(row['e-tag ID']).strip(),
                        "tolling_point": str(row['TA/Tolling Point']).strip()
                    })
                    
                    if exists:
                        duplicates.append(row)
                    else:
                        new_records.append({
                            "doctype": "Tolls",
                            "transaction_date": transaction_date.strftime('%Y-%m-%d %H:%M:%S'),
                            "tolling_point": str(row['TA/Tolling Point']).strip(),
                            "etag_id": str(row['e-tag ID']).strip(),
                            "net_amount": net_amount,
                            "process_status": "Unprocessed",
                            "source_capture": self.name
                        })
                except Exception as row_error:
                    frappe.log_error(f"Error processing row {index}: {str(row_error)}")
                    continue
            
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