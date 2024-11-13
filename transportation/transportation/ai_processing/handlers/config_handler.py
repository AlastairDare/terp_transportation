import frappe
from .base_handler import BaseHandler
from ..utils.request import DocumentRequest
from ..utils.exceptions import ConfigurationError

class ConfigurationHandler(BaseHandler):
    def handle(self, request: DocumentRequest) -> DocumentRequest:
        try:
            # Load AI Config settings
            ai_config = frappe.get_single("AI Config")
            if not ai_config.active:
                raise ConfigurationError("AI processing is disabled in configuration")
            request.config = ai_config
            
            # Load provider settings based on selected provider
            if ai_config.llm_model_family == "ChatGPT by OpenAI":
                request.provider_settings = frappe.get_single("ChatGPT Settings")
            else:
                request.provider_settings = frappe.get_single("Claude Settings")
            
            # Load OCR settings based on document type
            if request.method == "process_toll":
                request.ocr_settings = frappe.get_doc("OCR Settings", {
                    "function": "Toll Capture Config"
                })
            else:
                request.ocr_settings = frappe.get_doc("OCR Settings", {
                    "function": "Delivery Note Capture Config"
                })
            
            if not request.provider_settings or not request.ocr_settings:
                raise ConfigurationError("Required settings not found")
            
            return super().handle(request)
        
        except Exception as e:
            request.set_error(e)
            raise ConfigurationError(f"Configuration loading failed: {str(e)}")