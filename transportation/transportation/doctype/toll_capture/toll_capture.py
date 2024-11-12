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
            
        # Validate document status
        if self.processing_status == "Processing":
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
        try:
            # Delete associated toll records
            frappe.db.delete("Tolls", {
                "source_capture": self.name
            })
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(f"Error deleting toll records: {str(e)}")
            frappe.throw(f"Failed to delete associated toll records: {str(e)}")

    def process_document(self):
        try:
            # Get file path
            file_path = get_file_path(self.toll_document)
            
            # Update status
            self.processing_status = "Processing"
            self.save()
            
            # Read tables from PDF
            tables = tabula.read_pdf(file_path, pages='all')
            
            # Convert to single DataFrame and clean up
            df = pd.concat(tables)
            df = df[df['Transaction Date & Time'].notna()]  # Remove empty rows
            
            total_records = len(df)
            self.total_records = total_records
            
            # Check for duplicates
            duplicates = []
            new_records = []
            
            for index, row in df.iterrows():
                # Update progress
                self.progress_count = f"Checking for duplicates: {index + 1}/{total_records}"
                self.save()
                
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
            self.duplicate_records = len(duplicates)
            self.new_records = len(new_records)
            
            # Create new toll records
            for record in new_records:
                toll = frappe.get_doc({
                    "doctype": "Tolls",
                    "transaction_date": pd.to_datetime(record['Transaction Date & Time']).strftime('%Y-%m-%d %H:%M:%S'),
                    "tolling_point": record['TA/Tolling Point'],
                    "etag_id": record['e-tag ID'],
                    "net_amount": record['Net Amount'],
                    "process_status": "Unprocessed",
                    "source_capture": self.name
                })
                toll.insert()
            
            self.processing_status = "Completed"
            self.save()
            
        except Exception as e:
            self.processing_status = "Failed"
            self.save()
            frappe.throw(f"Error processing document: {str(e)}")

@frappe.whitelist()
def process_toll_document(doc_name):
    try:
        doc = frappe.get_doc("Toll Capture", doc_name)
        doc.process_document()
        return "Processing Complete"
    except Exception as e:
        frappe.log_error(f"Error processing toll document: {str(e)}")
        frappe.throw(f"Failed to process toll document: {str(e)}")