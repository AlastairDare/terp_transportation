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

    def is_valid_transaction_row(self, row):
        """Check if this row represents a valid transaction"""
        try:
            # Log the row data for debugging
            frappe.log_error(f"Checking row: {row.to_dict()}", "Row Validation")
            
            # Skip empty rows
            if pd.isna(row).all():
                frappe.log_error("Row is empty", "Row Validation")
                return False
                
            # Check if this is a total row
            if any(str(val).strip().lower().startswith('total') for val in row.values):
                frappe.log_error("Row is a total row", "Row Validation")
                return False
            
            # Log column names
            frappe.log_error(f"Column names: {row.index.tolist()}", "Row Validation")
                
            # Check required columns exist
            required_columns = ['Transaction Date & Time', 'TA/Tolling Point', 'e-tag ID', 'Net Amount']
            for col in required_columns:
                if col not in row.index:
                    frappe.log_error(f"Missing column: {col}", "Row Validation")
                    return False
            
            # Validate date format
            date_str = str(row['Transaction Date & Time']).strip()
            if not date_str:
                frappe.log_error("Empty date string", "Row Validation")
                return False
            pd.to_datetime(date_str, format='%Y/%m/%d %I:%M:%S %p')
            
            # Validate e-tag ID format
            etag_id = str(row['e-tag ID']).strip()
            if not etag_id or not etag_id.replace(' ', '').isdigit():
                frappe.log_error(f"Invalid e-tag ID: {etag_id}", "Row Validation")
                return False
                
            # Validate amount
            amount_str = str(row['Net Amount']).strip()
            if not amount_str.startswith('R '):
                frappe.log_error(f"Invalid amount format: {amount_str}", "Row Validation")
                return False
            float(amount_str.replace('R ', '').replace(',', ''))
            
            frappe.log_error("Row is valid", "Row Validation")
            return True
            
        except Exception as e:
            frappe.log_error(f"Validation error: {str(e)}", "Row Validation Error")
            return False

    def process_document(self):
        """Process the uploaded PDF document and create toll records"""
        try:
            # Get file path and update status
            file_path = get_file_path(self.toll_document)
            self.db_set('processing_status', 'Processing')
            
            # Log the start of processing
            frappe.log_error("Starting PDF processing", "Toll Processing")
            
            # Try reading with default settings first
            tables = tabula.read_pdf(
                file_path,
                pages='all',
                guess=False,
                area=[120, 0, 750, 1000],
                multiple_tables=True
            )
            
            if not tables:
                raise Exception("No tables found in PDF document")
            
            # Log table data
            frappe.log_error(f"Found {len(tables)} tables", "Toll Processing")
            
            # Combine all tables
            df = pd.concat(tables)
            
            # Log initial data
            frappe.log_error(f"Initial columns: {df.columns.tolist()}", "Toll Processing")
            frappe.log_error(f"Initial row count: {len(df)}", "Toll Processing")
            
            # Filter valid transaction rows
            valid_rows = []
            for index, row in df.iterrows():
                if self.is_valid_transaction_row(row):
                    valid_rows.append(row)
            
            # Log validation results
            frappe.log_error(f"Valid rows found: {len(valid_rows)}", "Toll Processing")
            
            if not valid_rows:
                raise Exception("No valid transactions found in the document")
            
            df_filtered = pd.DataFrame(valid_rows)
            
            total_records = len(df_filtered)
            self.db_set('total_records', total_records)
            
            duplicates = []
            new_records = []
            processed_count = 0
            
            for index, row in df_filtered.iterrows():
                processed_count += 1
                self.db_set('progress_count', f"Processing record {processed_count} of {total_records}")
                
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
                        frappe.log_error(f"Duplicate found: {etag_id} at {tolling_point}", "Toll Processing")
                    else:
                        new_toll = frappe.get_doc({
                            "doctype": "Tolls",
                            "transaction_date": transaction_date.strftime('%Y-%m-%d %H:%M:%S'),
                            "tolling_point": tolling_point,
                            "etag_id": etag_id,
                            "net_amount": net_amount,
                            "process_status": "Unprocessed",
                            "source_capture": self.name
                        })
                        
                        new_toll.insert()
                        frappe.db.commit()
                        new_records.append(new_toll.name)
                        frappe.log_error(f"Created new toll record: {new_toll.name}", "Toll Processing")
                        
                except Exception as e:
                    frappe.log_error(
                        f"Error processing record {processed_count}:\n"
                        f"Data: {row.to_dict()}\n"
                        f"Error: {str(e)}",
                        "Toll Record Processing Error"
                    )
                    continue
            
            # Update final counts and status
            self.db_set('duplicate_records', len(duplicates))
            self.db_set('new_records', len(new_records))
            self.db_set('processing_status', 'Completed')
            
            # Log final results
            frappe.log_error(
                f"Processing completed.\n"
                f"New records: {len(new_records)}\n"
                f"Duplicates: {len(duplicates)}",
                "Toll Processing Complete"
            )
            
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
        frappe.throw(str(e))