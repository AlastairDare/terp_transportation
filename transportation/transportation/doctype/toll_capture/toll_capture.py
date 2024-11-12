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
        # First, log original columns
        print("Original columns:", df.columns.tolist())
        
        # Clean up column names
        df.columns = [col.replace('\r', ' ').replace('\n', ' ').strip() for col in df.columns]
        
        # Log cleaned columns
        print("Cleaned columns:", df.columns.tolist())
        
        return df

    def is_valid_transaction_row(self, row):
        """Check if this row represents a valid transaction"""
        try:
            # Print row data for debugging
            print("\nChecking row:", row.to_dict())
            
            # Skip empty rows
            if pd.isna(row).all():
                print("Row is all empty")
                return False
            
            # Check if any column contains 'Total'
            if any('Total' in str(val) for val in row.values):
                print("Row contains Total")
                return False
            
            # Check if we have the required columns
            required_cols = ['Transaction Date & Time', 'e-tag ID', 'Net Amount', 'TA/Tolling Point']
            missing_cols = [col for col in required_cols if col not in row.index]
            if missing_cols:
                print(f"Missing columns: {missing_cols}")
                return False
            
            # Check if required fields have values
            if any(pd.isna(row[col]) for col in required_cols):
                print("Required fields have NaN values")
                return False
            
            # Print specific field values for debugging
            print("Date:", str(row['Transaction Date & Time']).strip())
            print("e-tag ID:", str(row['e-tag ID']).strip())
            print("Net Amount:", str(row['Net Amount']).strip())
            
            return True
            
        except Exception as e:
            print(f"Validation error: {str(e)}")
            return False

    def process_document(self):
        """Process the uploaded PDF document and create toll records"""
        try:
            file_path = get_file_path(self.toll_document)
            self.db_set('processing_status', 'Processing')
            
            print("\nStarting PDF processing...")
            
            # Read PDF
            tables = tabula.read_pdf(
                file_path,
                pages='all',
                area=[120, 0, 750, 1000],
                multiple_tables=True,
                guess=False,
                lattice=True
            )
            
            print(f"\nFound {len(tables)} tables")
            
            if not tables:
                raise Exception("No tables found in PDF document")
            
            # Print first table sample
            if tables:
                print("\nFirst table sample:")
                print(tables[0].head())
            
            # Combine tables and clean column names
            df = pd.concat(tables)
            df = self.clean_column_names(df)
            
            print(f"\nTotal rows before filtering: {len(df)}")
            
            # Filter valid rows
            valid_rows = []
            for idx, row in df.iterrows():
                print(f"\nChecking row {idx}")
                if self.is_valid_transaction_row(row):
                    valid_rows.append(row)
                    print("Row is valid")
            
            print(f"\nValid rows found: {len(valid_rows)}")
            
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
                    print(f"Error processing row {index}: {str(e)}")
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