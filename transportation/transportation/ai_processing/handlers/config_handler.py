import frappe
from .base_handler import BaseHandler
from ..utils.request import DocumentRequest
from ..utils.exceptions import ConfigurationError

class ConfigurationHandler(BaseHandler):
    def handle(self, request: DocumentRequest) -> DocumentRequest:
        try:
            frappe.log_error(
                message="1. Starting config handler",
                title="Config Handler Debug"
            )
            
            # Load AI Config settings
            ai_config = frappe.get_single("AI Config")
            if not ai_config.active:
                raise ConfigurationError("AI processing is disabled in configuration")
            request.config = ai_config
            
            frappe.log_error(
                message="2. Loaded AI config",
                title="Config Handler Debug"
            )
            
            # Load provider settings
            if ai_config.llm_model_family == "ChatGPT by OpenAI":
                request.provider_settings = frappe.get_single("ChatGPT Settings")
            else:
                request.provider_settings = frappe.get_single("Claude Settings")
            
            frappe.log_error(
                message=f"3. Loaded provider settings for {ai_config.llm_model_family}",
                title="Config Handler Debug"
            )
            
            # Load OCR settings
            request.ocr_settings = frappe.get_doc("OCR Settings", {
                "function": "Delivery Note Capture Config"
            })
            
            frappe.log_error(
                message="4. Loaded OCR settings",
                title="Config Handler Debug"
            )
            
            if not request.provider_settings or not request.ocr_settings:
                raise ConfigurationError("Required settings not found")
            
            return super().handle(request)
                
        except Exception as e:
            request.set_error(e)
            frappe.log_error(
                message=f"Config handler failed: {str(e)}",
                title="Config Handler Error"
            )
            raise ConfigurationError(f"Configuration loading failed: {str(e)}")