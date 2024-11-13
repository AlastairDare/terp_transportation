import json
import time
import requests
from typing import Dict, List
from .base_provider import BaseAIProvider
from ..utils.exceptions import ProviderError

class OpenAIProvider(BaseAIProvider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timeout = getattr(self.settings, 'request_timeout', 120)
        self.base_retry_delay = 1  # Start with 1 second delay
        self.max_retries = getattr(self.settings, 'max_retries', 3)

    def get_headers(self) -> Dict:
        return {
            "Authorization": f"Bearer {self.settings.get_password('api_key')}",
            "Content-Type": "application/json"
        }

    def _make_request_with_backoff(self, url: str, headers: Dict, data: Dict) -> Dict:
        """Make request with exponential backoff retry logic"""
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=data,
                    timeout=(self.timeout/4, self.timeout)
                )
                
                if response.status_code == 200:
                    return response.json()
                    
                if response.status_code >= 500:  # Server errors should be retried
                    raise ProviderError(f"Server error: {response.status_code}")
                    
                # Client errors should fail fast
                if response.status_code >= 400:
                    raise ProviderError(f"API error {response.status_code}: {response.text}")
                    
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt == self.max_retries:
                    raise ProviderError(f"Failed after {self.max_retries} retries: {str(e)}")
                    
            # Calculate exponential backoff delay
            delay = min(300, (2 ** attempt) * self.base_retry_delay)  # Cap at 5 minutes
            time.sleep(delay)
            
        raise ProviderError("Max retries exceeded")

    def process_document(self, base64_image: str, prompt: str) -> Dict:
        try:
            headers = self.get_headers()
            base_url = self.settings.base_url.rstrip('/')
            
            # Structure the messages to force JSON response
            data = {
                "model": self.settings.default_model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a JSON-only response bot. Always respond with valid JSON "
                            "objects only, no additional text or explanations. Each response "
                            "should be a single, valid JSON object."
                        )
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"Analyze the following image and respond only with JSON: {prompt}"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 500,
                "temperature": float(self.settings.temperature),
                "response_format": { "type": "json_object" }  # Force JSON response
            }

            result = self._make_request_with_backoff(
                f"{base_url}/chat/completions",
                headers,
                data
            )

            # Extract the JSON response - should be clean JSON now
            response_content = result['choices'][0]['message']['content']
            
            try:
                return json.loads(response_content)
            except json.JSONDecodeError as e:
                raise ProviderError(f"Invalid JSON in response: {str(e)}\nResponse: {response_content}")

        except Exception as e:
            raise ProviderError(f"OpenAI processing failed: {str(e)}")