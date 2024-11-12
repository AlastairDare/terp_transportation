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
            # Check if this is a total row
            if any(str(val).strip().lower().startswith('total') for val in row.values):
                return False
                
            # Validate date format
            date_str = str(row['Transaction Date & Time']).strip()
            pd.to_datetime(date_str, format='%Y/%m/%d %I:%M:%S %p')
            
            # Validate e-tag ID format (should be numeric and certain length)
            etag_id = str(row['e-tag ID']).strip()
            if not etag_id.replace(' ', '').isdigit():
                return False
                
            # Validate amount (should be convertible to float and have 'R' prefix)
            amount_str = str(row['Net Amount']).strip()
            if not amount_str.startswith('R '):
                return False
            float(amount_str.replace('R ', '').replace(',', ''))
            
            return True
            
        except (ValueError, KeyError, TypeError):
            return False

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
                guess=False,
                area=[120, 0, 750, 1000],
                multiple_tables=True
            )
            
            if not tables:
                raise Exception("No tables found in PDF document")
            
            # Combine all tables
            df = pd.concat(tables)
            
            # Filter valid transaction rows
            valid_rows = []
            for index, row in df.iterrows():
                if self.is_valid_transaction_row(row):
                    valid_rows.append(row)
            
            df_filtered = pd.DataFrame(valid_rows)
            
            total_records = len(df_filtered)
            self.db_set('total_records', total_records)
            
            if total_records == 0:
                raise Exception("No valid transactions found in the document")
            
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
            
            # Log success
            frappe.log_error(
                f"Successfully processed {len(new_records)} records.\n"
                f"Duplicates found: {len(duplicates)}",
                "Toll Processing Success"
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