import frappe
from frappe.model.document import Document
import fitz  # PyMuPDF
from frappe.utils.file_manager import get_file_path

def validate(doc, method):
    """Module-level validation method"""
    if not doc.toll_document:
        frappe.throw("Toll document is required")
            
    file_path = get_file_path(doc.toll_document)
    if not file_path.lower().endswith('.pdf'):
        frappe.throw("Only PDF files are supported")

def analyze_pdf_structure(doc) -> str:
    """Module-level diagnostic function"""
    try:
        file_path = get_file_path(doc.toll_document)
        pdf_doc = fitz.open(file_path)
        
        debug_info = []
        for page_num in range(len(pdf_doc)):
            page = pdf_doc[page_num]
            debug_info.append(f"\nPAGE {page_num + 1}:")
            
            # Get raw text with formatting info
            text_dict = page.get_text("dict")
            
            # Debug each text block
            debug_info.append("\nText Blocks Found:")
            for block_num, block in enumerate(text_dict["blocks"]):
                if "lines" in block:
                    debug_info.append(f"\nBlock {block_num + 1}:")
                    for line in block["lines"]:
                        text = " ".join(span["text"] for span in line["spans"])
                        bbox = line["bbox"]  # [x0, y0, x1, y1]
                        debug_info.append(f"Line at position {bbox}: {text}")
            
            # Try table detection
            debug_info.append("\nAttempting Table Detection:")
            finder = page.find_tables()
            tables = finder.extract()  # This gets the actual tables
            debug_info.append(f"Number of tables detected: {len(tables)}")
            
            for table_num, table in enumerate(tables):
                debug_info.append(f"\nTable {table_num + 1}:")
                debug_info.append(f"Table bbox: {table.bbox}")  # Show table boundaries
                rows = table  # table is already the extracted data
                debug_info.append(f"Rows detected: {len(rows)}")
                
                # Show first few rows for inspection
                for row_num, row in enumerate(rows[:5]):  # Show first 5 rows
                    debug_info.append(f"Row {row_num}: {row}")
            
            # Alternative text extraction for comparison
            debug_info.append("\nRaw Text Extraction:")
            raw_text = page.get_text()
            debug_info.append(raw_text[:500])  # First 500 chars for comparison
        
        # Log the complete debug info
        debug_text = "\n".join(debug_info)
        frappe.log_error(debug_text, "PDF Structure Analysis")
        
        # Show summary to user
        frappe.msgprint(
            msg=f"PDF Analysis Complete. Check Error Log for full details.",
            title="Table Detection Results"
        )
        
        return "Diagnostic Complete"
        
    except Exception as e:
        frappe.log_error(f"Error during analysis: {str(e)}", "PDF Analysis Error")
        frappe.throw(f"Error analyzing document: {str(e)}")
    finally:
        if 'pdf_doc' in locals():
            pdf_doc.close()

class TollCapture(Document):
    def process_document(self) -> str:
        """Class method that calls module-level function"""
        return analyze_pdf_structure(self)

@frappe.whitelist()
def process_toll_document(doc_name: str) -> str:
    """Whitelist method to process toll document"""
    doc = frappe.get_doc("Toll Capture", doc_name)
    return doc.process_document()