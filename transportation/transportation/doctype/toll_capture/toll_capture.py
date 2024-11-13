import frappe
from frappe.model.document import Document  # Correct import for Document class
import fitz  # PyMuPDF
from datetime import datetime
from frappe.utils import get_site_path, get_files_path
from frappe.utils.file_manager import get_file_path
import re
import os
from typing import List, Dict, Optional, Tuple

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
            blocks = page.get_text("blocks")
            blocks.sort(key=lambda b: b[1])  # Sort by y0 coordinate
            
            current_transaction = {}
            
            for block in blocks:
                text = block[4].strip()
                
                if self._is_transaction_row(text):
                    if current_transaction:
                        all_transactions.append(current_transaction)
                    current_transaction = self._parse_transaction_row(text)
        
        if current_transaction:
            all_transactions.append(current_transaction)
            
        return all_transactions
    
    def _is_transaction_row(self, text: str) -> bool:
        """Check if text block contains a transaction row"""
        date_pattern = r'\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}'
        return bool(re.search(date_pattern, text))
    
    def _parse_transaction_row(self, text: str) -> Dict:
        """Parse a transaction row into structured data"""
        try:
            fields = text.split()
            
            date_time_str = f"{fields[0]} {fields[1]}"
            date_time = datetime.strptime(date_time_str, '%Y/%m/%d %H:%M:%S')
            
            return {
                'transaction_date': date_time.strftime('%Y-%m-%d %H:%M:%S'),
                'tolling_point': ' '.join(fields[2:4]),
                'etag_id': fields[-4],
                'net_amount': float(fields[-2])
            }
            
        except (IndexError, ValueError) as e:
            frappe.log_error(
                f"Error parsing transaction row: {text}\nError: {str(e)}", 
                "Toll Capture Parser Error"
            )
            return {}

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
                existing = frappe.get_all(
                    "Tolls",
                    filters={
                        "transaction_date": transaction['transaction_date'],
                        "etag_id": transaction['etag_id']
                    }
                )
                
                if not existing:
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