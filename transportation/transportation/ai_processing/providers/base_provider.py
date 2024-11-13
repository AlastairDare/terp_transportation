from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseAIProvider(ABC):
    def __init__(self, settings: Any):
        self.settings = settings
        self.max_retries = 3
        self.retry_count = 0
    
    @abstractmethod
    def process_document(self, base64_image: str, prompt: str) -> Dict:
        """Process document and return structured response"""
        pass
    
    def get_headers(self) -> Dict:
        """Get provider-specific headers"""
        pass
    
    def format_prompt(self, base_prompt: str, json_example: str, image_data: str) -> str:
        """Format the prompt with image data and example"""
        return (
            f"{base_prompt.replace('{image_data}', image_data)}\n\n"
            f"Please format the response exactly like this example:\n{json_example}"
        )