import frappe
import tabula
import pandas as pd
from frappe.utils.file_manager import get_file_path
from frappe.model.document import Document
from frappe.utils import get_datetime_str

def validate(doc, method):
    if not doc.toll_document:
        frappe.throw("Toll document is required")
        
    # Validate file format
    file_path = get_file_path(doc.toll_document)
    if not file_path.lower().endswith('.pdf'):
        frappe.throw("Only PDF files are supported")

def create_toll_record(transaction_date, tolling_point, etag_id, net_amount, source_capture):
    """Create individual toll record at module level"""
    try:
        # Log the incoming data for debugging
        frappe.log_error(
            f"Creating toll record with:\n"
            f"Date: {transaction_date}\n"
            f"Point: {tolling_point}\n"
            f"Tag: {etag_id}\n"
            f"Amount: {net_amount}",
            "Toll Data Debug"
        )
        
        # Check for existing record
        exists = frappe.db.exists("Tolls", {
            "transaction_date": transaction_date,
            "etag_id": etag_id
        })
        
        if exists:
            return False, "Duplicate record"
            
        # Create new toll record
        toll = frappe.get_doc({
            "doctype": "Tolls",
            "transaction_date": transaction_date,
            "tolling_point": tolling_point,
            "etag_id": etag_id,
            "net_amount": net_amount,
            "process_status": "Unprocessed",
            "source_capture": source_capture
        })
        
        toll.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return True, toll.name
        
    except Exception as e:
        frappe.log_error(f"Failed to create toll record: {str(e)}")
        return False, str(e)

def process_toll_records(doc):
    """Process PDF and create toll records at module level"""
    try:
        file_path = get_file_path(doc.toll_document)
        
        # Read tables from PDF
        tables = tabula.read_pdf(
            file_path,
            pages='all',
            multiple_tables=True,
            lattice=True
        )
        
        if not tables:
            raise Exception("No tables found in PDF document")
        
        # Combine all tables and remove header/footer
        df = pd.concat(tables)
        df = df.iloc[1:-1]  # Remove first and last row
        
        # Log column names for debugging
        frappe.log_error(f"Columns in DataFrame: {df.columns.tolist()}", "Column Debug")
        
        total_records = len(df)
        doc.db_set('total_records', total_records)
        
        successful_records = []
        duplicate_records = []
        failed_records = []
        
        for index, row in df.iterrows():
            try:
                # Update progress
                doc.db_set('progress_count', f"Processing record {index + 1}/{total_records}")
                
                # Log raw row data for debugging
                frappe.log_error(f"Processing row: {row.to_dict()}", "Row Data Debug")
                
                # Clean and format date - handle possible column name variations
                date_col = next((col for col in df.columns if 'Transaction Date' in col), None)
                if not date_col:
                    raise Exception(f"Date column not found. Available columns: {df.columns.tolist()}")
                
                raw_date = str(row[date_col]).strip()
                # Convert to datetime and then to string in ERPNext format
                transaction_date = pd.to_datetime(raw_date, format='%Y/%m/%d %I:%M:%S %p')
                date_str = get_datetime_str(transaction_date)
                
                # Clean other fields
                tolling_point = str(row['TA/Tolling Point']).strip() if 'TA/Tolling Point' in row else ''
                etag_id = str(row['e-tag ID']).strip() if 'e-tag ID' in row else ''
                
                # Clean amount
                amount_str = str(row['Net Amount']).strip() if 'Net Amount' in row else '0'
                net_amount = float(amount_str.replace('R ', '').replace(',', ''))
                
                # Create individual toll record
                success, result = create_toll_record(
                    date_str,
                    tolling_point,
                    etag_id,
                    net_amount,
                    doc.name
                )
                
                if success:
                    successful_records.append(result)
                elif result == "Duplicate record":
                    duplicate_records.append(etag_id)
                else:
                    failed_records.append(f"Row {index + 1}: {result}")
                    
            except Exception as e:
                failed_records.append(f"Row {index + 1}: {str(e)}")
                continue
        
        # Update final counts
        doc.db_set('new_records', len(successful_records))
        doc.db_set('duplicate_records', len(duplicate_records))
        doc.db_set('processing_status', 'Completed')
        
        # Show summary message
        message = f"""
        <div>
            <p>Toll processing completed:</p>
            <ul>
                <li>Successfully created: {len(successful_records)}</li>
                <li>Duplicates skipped: {len(duplicate_records)}</li>
                <li>Failed records: {len(failed_records)}</li>
            </ul>
        </div>
        """
        
        if failed_records:
            message += "<p>Failed records details have been logged.</p>"
            frappe.log_error("\n".join(failed_records), "Toll Processing Failures")
            
        frappe.msgprint(
            msg=message,
            title="Toll Processing Complete",
            indicator="green" if not failed_records else "orange"
        )
        
    except Exception as e:
        doc.db_set('processing_status', 'Failed')
        raise

class TollCapture(Document):
    def validate(self):
        if not self.name:
            self.processing_status = "Pending"
            self.progress_count = ""
            self.total_records = 0
            self.new_records = 0
            self.duplicate_records = 0

    def process_document(self):
        """Trigger the processing at module level"""
        process_toll_records(self)

@frappe.whitelist()
def process_toll_document(doc_name):
    """Whitelist method to process toll documents"""
    try:
        doc = frappe.get_doc("Toll Capture", doc_name)
        doc.process_document()
        return "Processing Complete"
    except Exception as e:
        frappe.throw(str(e))