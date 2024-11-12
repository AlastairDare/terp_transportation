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

    def clean_column_names(self, df):
        """Clean up column names and standardize them"""
        column_mapping = {
            'TA/\rTolling\rPoint': 'TA/Tolling Point',
            'Vehicle\rLicence Plate\rNumber': 'Vehicle Licence Plate Number',
            'e-tag\rID': 'e-tag ID',
            'Detected\rTA Class': 'Detected TA Class',
            'Nominal\rAmount': 'Nominal Amount',
            'Net\rAmount': 'Net Amount',
            'Transaction\rDate & Time': 'Transaction Date & Time'
        }
        
        # Replace column names if they exist
        new_columns = []
        for col in df.columns:
            if col in column_mapping:
                new_columns.append(column_mapping[col])
            else:
                new_columns.append(col.replace('\r', ' ').strip())
                
        df.columns = new_columns
        return df

    def is_valid_transaction_row(self, row):
        """Check if this row represents a valid transaction"""
        try:
            # Skip empty rows
            if pd.isna(row).all():
                return False
                
            # Check if this is a total row
            if 'Total' in str(row.values):
                return False
                
            # Check for required data
            if not all(pd.notna(row.get(col, '')) for col in ['Transaction Date & Time', 'e-tag ID', 'Net Amount']):
                return False
            
            # Validate e-tag ID (should be numbers with possible spaces)
            etag_id = str(row['e-tag ID']).strip()
            if not etag_id.replace(' ', '').isdigit():
                return False
                
            # Validate amount format
            amount_str = str(row['Net Amount']).strip()
            if not amount_str.startswith('R '):
                return False
                
            return True
            
        except Exception:
            return False

    def process_document(self):
        """Process the uploaded PDF document and create toll records"""
        try:
            file_path = get_file_path(self.toll_document)
            self.db_set('processing_status', 'Processing')
            
            # Read PDF
            tables = tabula.read_pdf(
                file_path,
                pages='all',
                area=[120, 0, 750, 1000],
                multiple_tables=True
            )
            
            if not tables:
                raise Exception("No tables found in PDF document")
            
            # Combine tables and clean column names
            df = pd.concat(tables)
            df = self.clean_column_names(df)
            
            # Filter valid rows
            valid_rows = [row for _, row in df.iterrows() if self.is_valid_transaction_row(row)]
            
            if not valid_rows:
                raise Exception("No valid transactions found in the document")
            
            df_filtered = pd.DataFrame(valid_rows)
            total_records = len(df_filtered)
            self.db_set('total_records', total_records)
            
            # Process records
            duplicates = []
            new_records = []
            
            for index, row in df_filtered.iterrows():
                self.db_set('progress_count', f"Processing record {index + 1} of {total_records}")
                
                try:
                    # Clean data
                    transaction_date = pd.to_datetime(str(row['Transaction Date & Time']).strip(), 
                                                    format='%Y/%m/%d %I:%M:%S %p')
                    tolling_point = str(row['TA/Tolling Point']).strip()
                    etag_id = str(row['e-tag ID']).strip()
                    net_amount = float(str(row['Net Amount']).replace('R ', '').replace(',', ''))
                    
                    # Check duplicates
                    exists = frappe.db.exists("Tolls", {
                        "transaction_date": transaction_date.strftime('%Y-%m-%d %H:%M:%S'),
                        "etag_id": etag_id,
                        "tolling_point": tolling_point
                    })
                    
                    if exists:
                        duplicates.append(etag_id)
                    else:
                        doc = frappe.get_doc({
                            "doctype": "Tolls",
                            "transaction_date": transaction_date.strftime('%Y-%m-%d %H:%M:%S'),
                            "tolling_point": tolling_point,
                            "etag_id": etag_id,
                            "net_amount": net_amount,
                            "process_status": "Unprocessed",
                            "source_capture": self.name
                        })
                        doc.insert(ignore_permissions=True)
                        frappe.db.commit()
                        new_records.append(doc.name)
                        
                except Exception as e:
                    frappe.log_error(f"Row processing error: {str(e)}", "Toll Processing")
                    continue
            
            # Update final counts
            self.db_set('duplicate_records', len(duplicates))
            self.db_set('new_records', len(new_records))
            self.db_set('processing_status', 'Completed')
            
        except Exception as e:
            self.db_set('processing_status', 'Failed')
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