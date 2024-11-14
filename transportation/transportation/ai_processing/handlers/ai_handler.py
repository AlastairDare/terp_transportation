from .base_handler import BaseHandler
from ..utils.request import DocumentRequest
from ..utils.exceptions import ProviderError
from ..providers.provider_factory import AIProviderFactory
import frappe

class AIProcessingHandler(BaseHandler):
    def handle(self, request: DocumentRequest) -> DocumentRequest:
        try:
            # Create AI provider instance
            provider = AIProviderFactory.create_provider(
                request.config,
                request.provider_settings
            )
            
            # Process delivery note image
            if not request.base64_image:
                raise ProviderError("No image data found for processing")
                
            # Format prompt using OCR settings
            prompt = provider.format_prompt(
                request.ocr_settings.language_prompt,
                request.ocr_settings.json_example,
                request.base64_image
            )
            
            # Process the document and get AI response
            request.ai_response = provider.process_document(
                request.base64_image,
                prompt
            )
            
            if not request.ai_response:
                raise ProviderError("No response received from AI provider")
            
            return super().handle(request)
            
        except Exception as e:
            request.set_error(e)
            raise ProviderError(f"AI processing failed: {str(e)}")