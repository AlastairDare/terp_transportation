from .base_handler import BaseHandler
from ..utils.request import DocumentRequest
from ..utils.exceptions import ProviderError
from ..providers.provider_factory import AIProviderFactory
import frappe

class AIProcessingHandler(BaseHandler):
    def handle(self, request: DocumentRequest) -> DocumentRequest:
        try:
            frappe.log_error(
                message="1. Starting AI handler",
                title="AI Handler Debug"
            )
            
            # Create AI provider instance
            provider = AIProviderFactory.create_provider(
                request.config,
                request.provider_settings
            )
            
            frappe.log_error(
                message="2. Created AI provider",
                title="AI Handler Debug"
            )
            
            # Process delivery note image
            if not request.base64_image:
                raise ProviderError("No image data found for processing")
                
            frappe.log_error(
                message="3. Found base64 image",
                title="AI Handler Debug"
            )
                
            # Format prompt using OCR settings
            prompt = provider.format_prompt(
                request.ocr_settings.language_prompt,
                request.ocr_settings.json_example,
                request.base64_image
            )
            
            frappe.log_error(
                message="4. Formatted prompt",
                title="AI Handler Debug"
            )
            
            # Process the document and get AI response
            request.ai_response = provider.process_document(
                request.base64_image,
                prompt
            )
            
            frappe.log_error(
                message=f"5. Got AI response: {str(request.ai_response)}",
                title="AI Handler Debug"
            )
            
            if not request.ai_response:
                raise ProviderError("No response received from AI provider")
            
            return super().handle(request)
                
        except Exception as e:
            request.set_error(e)
            frappe.log_error(
                message=f"AI handler failed: {str(e)}",
                title="AI Handler Error"
            )
            raise ProviderError(f"AI processing failed: {str(e)}")