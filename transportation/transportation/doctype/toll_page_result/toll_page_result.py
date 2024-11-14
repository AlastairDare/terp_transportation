import frappe
import json
import requests
import time
from frappe.model.document import Document

class TollPageResult(Document):
    def after_insert(self):
        try:
            self._process_toll_page()
        except Exception as e:
            self._handle_error(f"Toll processing failed: {str(e)}")

    def _process_toll_page(self):
        try:
            # Get configurations
            ai_config = frappe.get_single("AI Config")
            if not ai_config.active:
                raise Exception("AI processing is disabled")

            provider_settings = frappe.get_single("ChatGPT Settings")
            ocr_settings = frappe.get_doc("OCR Settings", "Toll Capture Config")

            # Format prompt
            prompt = (
                f"{ocr_settings.language_prompt}\n"
                "IMPORTANT: Ensure your response is a complete, valid JSON array. "
                "If no toll records are found, return {'transactions': []}."
            )

            # Make OpenAI request
            response = self._make_openai_request(
                prompt,
                provider_settings,
                ai_config
            )

            # Process response and create tolls
            self._create_toll_records(response)
            
            # Update status
            self.status = "Processed"
            self.save()

        except Exception as e:
            self._handle_error(str(e))
            raise

    def _make_openai_request(self, prompt, provider_settings, ai_config):
        headers = {
            "Authorization": f"Bearer {provider_settings.get_password('api_key')}",
            "Content-Type": "application/json"
        }

        data = {
            "model": ai_config.default_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a JSON-only response bot. Respond with transaction data "
                        "or empty transactions array if no data found."
                    )
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{self.base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 4096,
            "temperature": 0.3,
            "response_format": {"type": "json_object"}
        }

        for attempt in range(3):
            try:
                response = requests.post(
                    f"{provider_settings.base_url.rstrip('/')}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=300
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    return json.loads(content)
                
                if response.status_code >= 400:
                    raise Exception(f"API error {response.status_code}: {response.text}")
                    
            except Exception as e:
                if attempt == 2:
                    raise Exception(f"OpenAI request failed: {str(e)}")
                    
            time.sleep(2 ** attempt)

    def _create_toll_records(self, response):
        if not isinstance(response.get('transactions', []), list):
            frappe.log_error("Invalid response format", "Toll Processing Error")
            raise Exception("Invalid response format from AI")

        for transaction in response.get('transactions', []):
            if self._validate_transaction(transaction):
                toll = frappe.get_doc({
                    "doctype": "Tolls",
                    "transaction_date": transaction['transaction_date'],
                    "tolling_point": transaction['tolling_point'],
                    "etag_id": transaction['etag_id'],
                    "net_amount": transaction['net_amount'],
                    "process_status": "Unprocessed"
                })
                toll.insert()

    def _validate_transaction(self, transaction):
        required_fields = ['transaction_date', 'tolling_point', 'etag_id', 'net_amount']
        return all(transaction.get(field) for field in required_fields)

    def _handle_error(self, error_message):
        frappe.log_error(
            message=f"Toll Page {self.name} processing failed: {error_message}",
            title="Toll Processing Error"
        )
        self.status = "Error"
        self.save()