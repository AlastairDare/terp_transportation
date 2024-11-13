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
    """Basic PDF structure analysis"""
    try:
        file_path = get_file_path(doc.toll_document)
        pdf_doc = fitz.open(file_path)
        
        debug_info = []
        for page_num in range(len(pdf_doc)):
            page = pdf_doc[page_num]
            debug_info.append(f"\n{'='*50}")
            debug_info.append(f"PAGE {page_num + 1} ANALYSIS")
            debug_info.append(f"{'='*50}")
            
            # 1. Basic page info
            debug_info.append(f"\nPage Size: {page.rect}")
            debug_info.append(f"Rotation: {page.rotation}")
            
            # 2. Raw text content
            debug_info.append("\nRAW TEXT CONTENT:")
            debug_info.append("-" * 30)
            debug_info.append(page.get_text())
            
            # 3. Text blocks with positions
            debug_info.append("\nTEXT BLOCKS WITH POSITIONS:")
            debug_info.append("-" * 30)
            text_dict = page.get_text("dict")
            
            for block_num, block in enumerate(text_dict["blocks"]):
                if "lines" in block:
                    debug_info.append(f"\nBlock {block_num + 1}:")
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"]
                            bbox = span["bbox"]
                            font = span["font"]
                            size = span["size"]
                            debug_info.append(
                                f"Text: {text}\n"
                                f"Position: {bbox}\n"
                                f"Font: {font}\n"
                                f"Size: {size}\n"
                                f"---"
                            )
        
        # Log the complete debug info
        debug_text = "\n".join(debug_info)
        frappe.log_error(debug_text, "Basic PDF Analysis")
        
        # Show summary to user
        frappe.msgprint(
            msg="PDF Analysis Complete. Check Error Log for full details.",
            title="PDF Analysis Results"
        )
        
        return "Analysis Complete"
        
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