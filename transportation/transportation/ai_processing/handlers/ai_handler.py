from .base_handler import BaseHandler
from ..utils.request import DocumentRequest
from ..utils.exceptions import ProviderError
from ..providers.provider_factory import AIProviderFactory

class AIProcessingHandler(BaseHandler):
    def handle(self, request: DocumentRequest) -> DocumentRequest:
        try:
            # Create AI provider instance
            provider = AIProviderFactory.create_provider(
                request.config,
                request.provider_settings
            )
            
            if request.method == "process_toll" and hasattr(request, 'pages'):
                # Process each page and combine results
                all_responses = []
                total_pages = len(request.pages)
                
                for page in request.pages:
                    # Update progress
                    request.doc.progress_count = f"Processing page {page['page_number']} of {total_pages}"
                    request.doc.save(ignore_permissions=True)
                    
                    # Format prompt
                    prompt = provider.format_prompt(
                        request.ocr_settings.language_prompt,
                        request.ocr_settings.json_example,
                        page['base64_image']
                    )
                    
                    # Process page
                    page_response = provider.process_document(
                        page['base64_image'],
                        prompt
                    )
                    
                    # Add page responses to combined results
                    if isinstance(page_response, list):
                        all_responses.extend(page_response)
                    elif isinstance(page_response, dict):
                        all_responses.append(page_response)
                
                request.ai_response = all_responses
                
            else:
                # Original image processing logic
                prompt = provider.format_prompt(
                    request.ocr_settings.language_prompt,
                    request.ocr_settings.json_example,
                    request.base64_image
                )
                
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