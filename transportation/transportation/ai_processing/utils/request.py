import frappe
from typing import Optional, Any, Dict

class DocumentRequest:
    def __init__(self, doc: Any, method: str):
        self.doc = doc                    # Original document
        self.method = method              # Method being called
        self.config: Optional[Dict] = None  # AI Config settings
        self.provider_settings = None      # ChatGPT or Claude settings
        self.ocr_settings = None          # Document-specific OCR settings
        self.base64_image: Optional[str] = None  # Base64 encoded image
        self.base64_document: Optional[str] = None  # Base64 encoded PDF
        self.document_type: Optional[str] = None  # 'image' or 'pdf'
        self.ai_response = None           # Response from AI provider
        self.processed_data = None        # Final processed data
        self.error = None                 # Any error information
        self.trip_id = None               # Created trip document ID

    def set_error(self, error: Exception) -> None:
        self.error = str(error)
        frappe.log_error(
            message=f"Document Processing Error: {str(error)}", 
            title="AI Processing Error"
        )
