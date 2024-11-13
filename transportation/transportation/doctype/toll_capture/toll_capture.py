import frappe
from frappe.model.document import Document
import fitz  # PyMuPDF
from datetime import datetime
from frappe.utils.file_manager import get_file_path
import re
from typing import List, Dict, Optional

class TollDataExtractor:
    """Handles PDF data extraction and processing for toll records"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.pdf_doc = None
        
    def __enter__(self):
        self.pdf_doc = fitz.open(self.file_path)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.pdf_doc:
            self.pdf_doc.close()
            
    def extract_table_data(self) -> List[Dict]:
        """
        Extracts toll transaction data from PDF tables
        Returns list of dictionaries containing transaction details
        """
        all_transactions = []
        
        for page_num in range(len(self.pdf_doc)):
            page = self.pdf_doc[page_num]
            # Get text with preserved formatting
            tables = page.find_tables()
            
            for table in tables:
                rows = table.extract()
                # Skip header row
                for row in rows[1:]:  # Skip header row
                    transaction = self._parse_table_row(row)
                    if transaction:
                        all_transactions.append(transaction)
        
        return all_transactions
    
    def _parse_table_row(self, row: List[str]) -> Optional[Dict]:
        """Parse a table row into transaction data"""
        try:
            # Check if row has enough columns
            if len(row) < 8:
                return None
                
            # Parse date and time
            date_str = row[0]
            if not date_str or 'Date' in date_str:  # Skip header or empty rows
                return None
                
            try:
                # Parse the date time string
                date_time = datetime.strptime(date_str.strip(), '%Y/%m/%d %I:%M:%S %p')
            except ValueError:
                try:
                    # Try alternative format if first fails
                    date_time = datetime.strptime(date_str.strip(), '%Y/%m/%d %H:%M:%S')
                except ValueError:
                    frappe.log_error(f"Invalid date format: {date_str}", "Toll Capture Date Error")
                    return None
            
            # Extract values from columns
            tolling_point = row[1].strip()  # TA/Tolling Point
            etag_id = row[3].strip()  # e-tag ID
            net_amount_str = row[7].strip()  # Net Amount
            
            # Clean the net amount string (remove 'R' and spaces)
            net_amount = float(net_amount_str.replace('R', '').replace(' ', ''))
            
            return {
                'transaction_date': date_time.strftime('%Y-%m-%d %H:%M:%S'),
                'tolling_point': tolling_point,
                'etag_id': etag_id,
                'net_amount': net_amount
            }
            
        except (IndexError, ValueError) as e:
            frappe.log_error(
                f"Error parsing table row: {row}\nError: {str(e)}", 
                "Toll Capture Parser Error"
            )
            return None

class TollCapture(Document):
    def validate(self):
        """Validate the uploaded document"""
        if not self.toll_document:
            frappe.throw("Toll document is required")
            
        file_path = get_file_path(self.toll_document)
        if not file_path.lower().endswith('.pdf'):
            frappe.throw("Only PDF files are supported")
    
    def process_document(self) -> str:
        """Process the uploaded toll document"""
        try:
            self.db_set('processing_status', 'Processing')
            
            file_path = get_file_path(self.toll_document)
            
            with TollDataExtractor(file_path) as extractor:
                transactions = extractor.extract_table_data()
            
            if not transactions:
                frappe.throw("No valid transaction data found in the document")
            
            self._process_transactions(transactions)
            
            self.db_set('processing_status', 'Completed')
            self.db_set('total_records', len(transactions))
            
            return "Processing Complete"
            
        except Exception as e:
            self.db_set('processing_status', 'Failed')
            frappe.log_error(f"Toll Capture Processing Error: {str(e)}", "Toll Capture Error")
            frappe.throw(f"Error processing document: {str(e)}")
    
    def _process_transactions(self, transactions: List[Dict]):
        """Process extracted transactions and create Tolls records"""
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
                        "source_capture": self.name,
                        "process_status": "Unprocessed"
                    })
                    toll.insert()
                    new_count += 1
                else:
                    duplicate_count += 1
                    
            except Exception as e:
                frappe.log_error(
                    f"Error processing transaction: {transaction}\nError: {str(e)}", 
                    "Toll Transaction Error"
                )
        
        self.db_set('new_records', new_count)
        self.db_set('duplicate_records', duplicate_count)

@frappe.whitelist()
def process_toll_document(doc_name: str) -> str:
    """Whitelist method to process toll document"""
    doc = frappe.get_doc("Toll Capture", doc_name)
    return doc.process_document()

def validate(doc, method):
    """Module-level validate hook"""
    if not doc.toll_document:
        frappe.throw("Toll document is required")
        
    file_path = get_file_path(doc.toll_document)
    if not file_path.lower().endswith('.pdf'):
        frappe.throw("Only PDF files are supported")