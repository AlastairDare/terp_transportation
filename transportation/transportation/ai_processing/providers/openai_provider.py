# transportation/ai_processing/providers/openai_provider.py

import json
import requests
from typing import Dict
from .base_provider import BaseAIProvider
from ..utils.exceptions import ProviderError

class OpenAIProvider(BaseAIProvider):
    def get_headers(self) -> Dict:
        return {
            "Authorization": f"Bearer {self.settings.get_password('api_key')}",
            "Content-Type": "application/json"
        }

    def process_document(self, base64_image: str, prompt: str) -> Dict:
        try:
            headers = self.get_headers()
            base_url = self.settings.base_url.rstrip('/')
            
            data = {
                "model": self.settings.default_model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
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
                "temperature": float(self.settings.temperature)
            }

            response = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )

            if response.status_code != 200:
                raise ProviderError(f"OpenAI API error: {response.text}")

            result = response.json()
            response_text = result['choices'][0]['message']['content']
            
            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ProviderError("No valid JSON found in OpenAI response")
                
            json_str = response_text[json_start:json_end]
            return json.loads(json_str)

        except Exception as e:
            if self.retry_count < self.max_retries:
                self.retry_count += 1
                return self.process_document(base64_image, prompt)
            raise ProviderError(f"OpenAI processing failed: {str(e)}")