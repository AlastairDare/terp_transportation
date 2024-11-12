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
            
        # Prevent processing while in progress
        if self.processing_status == "Processing" and not self.is_new():
            frappe.throw("Document is already being processed")
            
        # Validate mandatory fields
        mandatory_fields = ['toll_document', 'company']
        for field in mandatory_fields:
            if not self.get(field):
                frappe.throw(f"{field.replace('_', ' ').title()} is mandatory")
                
        # Prevent duplicate uploads
        if frappe.db.exists("Toll Capture", {
            "toll_document": self.toll_document,
            "name": ("!=", self.name)
        }):
            frappe.throw("This toll document has already been uploaded")

    def on_trash(self):
        """Handle deletion of toll records when the capture document is deleted"""
        try:
            # Delete associated toll records
            frappe.db.sql("""
                DELETE FROM `tabTolls` 
                WHERE source_capture = %s
            """, self.name)
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(str(e), "Toll Capture Delete Error")
            frappe.throw(f"Failed to delete associated toll records: {str(e)}")

    def process_document(self):
        """Process the uploaded PDF document and create toll records"""
        try:
            # Get file path and update status
            file_path = get_file_path(self.toll_document)
            self.db_set('processing_status', 'Processing')
            
            # Extract tables from PDF
            tables = tabula.read_pdf(file_path, pages='all')
            if not tables:
                raise Exception("No tables found in PDF document")
            
            # Combine all tables and clean data
            df = pd.concat(tables)
            df = df.dropna(subset=['Transaction Date & Time', 'e-tag ID'])
            
            total_records = len(df)
            self.db_set('total_records', total_records)
            
            # Process records in batches to improve performance
            batch_size = 100
            duplicates = []
            new_records = []
            
            for i in range(0, total_records, batch_size):
                batch = df.iloc[i:i+batch_size]
                
                for _, row in batch.iterrows():
                    # Update progress
                    progress = f"Processing records: {i + len(new_records)}/{total_records}"
                    self.db_set('progress_count', progress)
                    
                    # Check for duplicate records
                    exists = frappe.db.exists("Tolls", {
                        "transaction_date": pd.to_datetime(row['Transaction Date & Time']).strftime('%Y-%m-%d %H:%M:%S'),
                        "etag_id": row['e-tag ID'],
                        "tolling_point": row['TA/Tolling Point']
                    })
                    
                    if exists:
                        duplicates.append(row)
                    else:
                        new_records.append({
                            "doctype": "Tolls",
                            "transaction_date": pd.to_datetime(row['Transaction Date & Time']).strftime('%Y-%m-%d %H:%M:%S'),
                            "tolling_point": row['TA/Tolling Point'],
                            "etag_id": row['e-tag ID'],
                            "net_amount": row['Net Amount'],
                            "process_status": "Unprocessed",
                            "source_capture": self.name,
                            "company": self.company
                        })
                
                # Insert batch of new records
                if new_records:
                    frappe.db.bulk_insert("Tolls", new_records)
                    new_records = []  # Clear the batch
            
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