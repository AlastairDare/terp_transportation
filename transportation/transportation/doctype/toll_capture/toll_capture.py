import frappe
from frappe.model.document import Document
import fitz  # PyMuPDF
from frappe.utils.file_manager import get_file_path
from datetime import datetime
import re
from typing import List, Dict

def validate(doc, method):
    if not doc.toll_document:
        frappe.throw("Toll document is required")
            
    file_path = get_file_path(doc.toll_document)
    if not file_path.lower().endswith('.pdf'):
        frappe.throw("Only PDF files are supported")

def extract_transactions(text: str) -> List[Dict]:
    """Extract transaction data using the exact pattern"""
    transactions = []
    
    # Find start of transactions
    start_index = text.find("Toll Transactions")
    if start_index == -1:
        return []
        
    # Get text after "Toll Transactions"
    text = text[start_index:]
    
    # Split into lines and remove empty lines
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Skip header rows (everything until we find a date)
    for i, line in enumerate(lines):
        if re.match(r'202[0-9]/\d{2}/\d{2}', line):
            lines = lines[i:]
            break
    
    # Process lines in groups of 8 (the pattern we identified)
    i = 0
    while i < len(lines):
        try:
            # Check if we've hit a line that indicates end of transactions
            if "Total Amount" in lines[i] or "Page" in lines[i]:
                break
                
            # Only process if line starts with a date
            if not re.match(r'202[0-9]/\d{2}/\d{2}', lines[i]):
                i += 1
                continue
                
            # Make sure we have enough lines for a complete transaction
            if i + 8 > len(lines):
                break
                
            try:
                # Parse date and time (first two lines)
                date_str = lines[i]
                time_str = lines[i + 1]
                date_time = datetime.strptime(f"{date_str} {time_str}", '%Y/%m/%d %I:%M:%S %p')
                
                # Parse class (third line)
                ta_class = lines[i + 2]  # Should be "Class 1" etc.
                
                # Parse amounts (fourth line - contains all amounts)
                amounts = lines[i + 3].split()
                nominal_amount = float(amounts[1])  # Skip 'R'
                discount = float(amounts[3])        # Skip 'R'
                net_amount = float(amounts[5])      # Skip 'R'
                vat = float(amounts[7])            # Skip 'R'
                
                # Parse tolling point (fifth and sixth lines)
                tolling_point = f"{lines[i + 4]} {lines[i + 5]}".strip()
                
                # Parse etag (seventh and eighth lines)
                etag_id = f"{lines[i + 6]} {lines[i + 7]}".strip()
                
                # Create transaction dictionary
                transaction = {
                    'transaction_date': date_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'ta_class': ta_class,
                    'nominal_amount': nominal_amount,
                    'discount': discount,
                    'net_amount': net_amount,
                    'vat': vat,
                    'tolling_point': tolling_point,
                    'etag_id': etag_id
                }
                
                # Add to transactions list if we have all required fields
                if all(key in transaction for key in ['transaction_date', 'etag_id', 'net_amount', 'tolling_point']):
                    transactions.append(transaction)
                    
                # Log for debugging
                frappe.log_error(
                    f"Successfully parsed transaction:\n{transaction}",
                    "Transaction Parse Success"
                )
                
                # Move to next transaction block (8 lines per transaction)
                i += 8
                
            except (IndexError, ValueError) as e:
                frappe.log_error(
                    f"Error parsing transaction starting at line {i}: {str(e)}\nLines: {lines[i:i+8]}", 
                    "Transaction Parse Error"
                )
                i += 1
                
        except Exception as e:
            frappe.log_error(
                f"Error in transaction processing: {str(e)}", 
                "General Processing Error"
            )
            i += 1
            
    return transactions

def analyze_pdf_structure(doc) -> str:
    """Process the PDF and extract transactions"""
    try:
        file_path = get_file_path(doc.toll_document)
        pdf_doc = fitz.open(file_path)
        
        # Get all text from PDF
        full_text = ""
        for page in pdf_doc:
            full_text += page.get_text()
        
        # Extract transactions
        transactions = extract_transactions(full_text)
        
        if not transactions:
            frappe.throw("No valid transaction data found in the document")
        
        # Process transactions
        new_count = 0
        duplicate_count = 0
        
        for transaction in transactions:
            try:
                # Check for existing record
                existing = frappe.get_all(
                    "Tolls",
                    filters={
                        "transaction_date": transaction['transaction_date'],
                        "etag_id": transaction['etag_id']
                    }
                )
                
                if not existing:
                    # Create new toll record
                    toll = frappe.get_doc({
                        "doctype": "Tolls",
                        "transaction_date": transaction['transaction_date'],
                        "tolling_point": transaction['tolling_point'],
                        "etag_id": transaction['etag_id'],
                        "net_amount": transaction['net_amount'],
                        "source_capture": doc.name,
                        "process_status": "Unprocessed"
                    })
                    toll.insert()
                    new_count += 1
                else:
                    duplicate_count += 1
                    
            except Exception as e:
                frappe.log_error(
                    f"Error processing transaction: {transaction}\nError: {str(e)}", 
                    "Transaction Processing Error"
                )
        
        # Update document status
        doc.db_set('processing_status', 'Completed')
        doc.db_set('total_records', len(transactions))
        doc.db_set('new_records', new_count)
        doc.db_set('duplicate_records', duplicate_count)
        
        return "Processing Complete"
        
    except Exception as e:
        doc.db_set('processing_status', 'Failed')
        frappe.log_error(f"PDF Processing Error: {str(e)}", "PDF Processing Error")
        frappe.throw(f"Error processing document: {str(e)}")
    finally:
        if 'pdf_doc' in locals():
            pdf_doc.close()

class TollCapture(Document):
    def process_document(self) -> str:
        """Process the uploaded toll document"""
        self.db_set('processing_status', 'Processing')
        return analyze_pdf_structure(self)

@frappe.whitelist()
def process_toll_document(doc_name: str) -> str:
    """Whitelist method to process toll document"""
    doc = frappe.get_doc("Toll Capture", doc_name)
    return doc.process_document()