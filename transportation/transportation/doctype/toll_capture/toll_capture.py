import frappe
import tabula
import pandas as pd
from frappe.utils.file_manager import get_file_path
from frappe.utils import get_datetime_str
from frappe.model.document import Document

def validate(doc, method):
    if not doc.toll_document:
        frappe.throw("Toll document is required")
        
    file_path = get_file_path(doc.toll_document)
    if not file_path.lower().endswith('.pdf'):
        frappe.throw("Only PDF files are supported")

def create_toll_record(transaction_date, tolling_point, etag_id, net_amount, source_capture):
    try:
        exists = frappe.db.exists("Tolls", {
            "transaction_date": transaction_date,
            "etag_id": etag_id
        })
        
        if exists:
            return False, "Duplicate record"
            
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
        return False, str(e)

def process_toll_records(doc):
    try:
        file_path = get_file_path(doc.toll_document)
        
        # Read tables from PDF with specific options
        tables = tabula.read_pdf(
            file_path,
            pages='all',
            multiple_tables=True,
            lattice=True,  # Use lattice mode since the PDF has lines
            guess=False,   # Don't guess the structure
            pandas_options={'header': None}
        )
        
        if not tables:
            raise Exception("No tables found in PDF document")
        
        # Combine all tables
        df = pd.concat(tables)
        
        # Debug: Print the first few rows with their raw data
        frappe.log_error(f"First row raw data: {df.iloc[0].to_dict()}", "Data Debug")
        frappe.log_error(f"Second row raw data: {df.iloc[1].to_dict()}", "Data Debug")
        
        # Let's see what columns we actually have
        frappe.log_error(f"Number of columns: {len(df.columns)}", "Data Debug")
        
        total_records = len(df)
        doc.db_set('total_records', total_records)
        
        successful_records = []
        duplicate_records = []
        failed_records = []
        
        # Process rows (skipping header)
        for index, row in df.iterrows():
            try:
                # Debug: Print each field for this row
                row_data = {
                    'Col0': row[0] if 0 in row else 'Missing',
                    'Col1': row[1] if 1 in row else 'Missing',
                    'Col2': row[2] if 2 in row else 'Missing',
                    'Col3': row[3] if 3 in row else 'Missing',
                    'Col4': row[4] if 4 in row else 'Missing',
                    'Col5': row[5] if 5 in row else 'Missing'
                }
                frappe.log_error(f"Processing row {index}, data: {row_data}", "Row Debug")
                
                # Skip if this looks like a header or total row
                if any(['Total' in str(val) for val in row.values]):
                    continue
                
                if index == 0:  # Skip header row
                    continue
                
                # Try to find the date column by looking at the format
                date_val = None
                tolling_point = None
                etag_id = None
                net_amount = None
                
                # Look through each column to identify the correct data
                for col in row.index:
                    val = str(row[col]).strip()
                    if '/' in val and ':' in val:  # Likely a date
                        date_val = val
                    elif 'N4:' in val or 'N1:' in val:  # Likely tolling point
                        tolling_point = val
                    elif val.replace(' ', '').isdigit() and len(val.replace(' ', '')) > 8:  # Likely etag
                        etag_id = val
                    elif val.startswith('R '):  # Likely amount
                        net_amount = float(val.replace('R ', '').replace(',', ''))
                
                if not all([date_val, tolling_point, etag_id, net_amount]):
                    raise Exception(f"Missing required data: date={bool(date_val)}, point={bool(tolling_point)}, tag={bool(etag_id)}, amount={bool(net_amount)}")
                
                # Parse date
                transaction_date = pd.to_datetime(date_val, format='%Y/%m/%d %I:%M:%S %p')
                date_str = get_datetime_str(transaction_date)
                
                # Create record
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
            frappe.log_error("\n".join(failed_records[:5]), "Sample Failed Records")
            
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
        process_toll_records(self)

@frappe.whitelist()
def process_toll_document(doc_name):
    try:
        doc = frappe.get_doc("Toll Capture", doc_name)
        doc.process_document()
        return "Processing Complete"
    except Exception as e:
        frappe.throw(str(e))