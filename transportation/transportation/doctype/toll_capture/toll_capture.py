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
            
            # Read tables from PDF
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
            
            # Remove first and last row
            df = df.iloc[1:-1]
            
            total_records = len(df)
            self.db_set('total_records', total_records)
            
            duplicates = []
            new_records = []
            
            for index, row in df.iterrows():
                # Update progress
                self.db_set('progress_count', f"Processing record {index + 1}/{total_records}")
                
                try:
                    # Clean up date format and convert to datetime
                    transaction_date = pd.to_datetime(row['Transaction Date & Time'], format='%Y/%m/%d %I:%M:%S %p')
                    date_str = transaction_date.strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Clean up net amount (remove 'R ' and convert to float)
                    net_amount = float(str(row['Net Amount']).replace('R ', '').replace(',', '').strip())
                    
                    # Clean up other fields
                    tolling_point = str(row['TA/Tolling Point']).strip()
                    etag_id = str(row['e-tag ID']).strip()
                    
                    # Check for duplicates
                    exists = frappe.db.exists("Tolls", {
                        "transaction_date": date_str,
                        "etag_id": etag_id
                    })
                    
                    if exists:
                        duplicates.append(row)
                        frappe.log_error(f"Duplicate found: Date {date_str}, Tag {etag_id}", "Toll Processing")
                    else:
                        # Create new toll record
                        try:
                            new_toll = {
                                "doctype": "Tolls",
                                "transaction_date": date_str,
                                "tolling_point": tolling_point,
                                "etag_id": etag_id,
                                "net_amount": net_amount,
                                "process_status": "Unprocessed",
                                "source_capture": self.name
                            }
                            
                            # Log the data being inserted
                            frappe.log_error(f"Creating toll record: {new_toll}", "Toll Creation")
                            
                            doc = frappe.get_doc(new_toll)
                            doc.insert(ignore_permissions=True)
                            frappe.db.commit()
                            
                            new_records.append(doc.name)
                            frappe.log_error(f"Created toll record: {doc.name}", "Toll Creation Success")
                            
                        except Exception as e:
                            frappe.log_error(f"Failed to create toll: {str(e)}\nData: {new_toll}", "Toll Creation Error")
                            raise
                        
                except Exception as e:
                    frappe.log_error(f"Error processing row {index}: {str(e)}", "Row Processing Error")
                    continue
            
            # Update final counts and status
            self.db_set('duplicate_records', len(duplicates))
            self.db_set('new_records', len(new_records))
            self.db_set('processing_status', 'Completed')
            
            # Log final summary
            frappe.log_error(
                f"Processing completed:\n"
                f"Total records: {total_records}\n"
                f"New records: {len(new_records)}\n"
                f"Duplicates: {len(duplicates)}",
                "Toll Processing Summary"
            )
            
        except Exception as e:
            self.db_set('processing_status', 'Failed')
            frappe.log_error(str(e), "Toll Processing Failed")
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