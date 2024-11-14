import frappe
import json
import requests
import time

def process_toll_page(doc, method):
    try:
        frappe.log_error("Starting toll processing", "Toll Debug")
        _process_toll_page(doc)
    except Exception as e:
        _handle_error(doc, f"Toll processing failed: {str(e)}")

def _process_toll_page(doc):
    try:
        ai_config = frappe.get_single("AI Config")
        if not ai_config.active:
            raise Exception("AI processing is disabled")

        provider_settings = frappe.get_single("ChatGPT Settings")
        ocr_settings = frappe.get_doc("OCR Settings", "Toll Capture Config")

        prompt = ocr_settings.language_prompt
        frappe.log_error(f"Using prompt: {prompt}", "Toll Debug")

        response = _make_openai_request(doc, prompt, provider_settings)
        frappe.log_error(f"OpenAI Response: {response}", "Toll Debug")

        _create_toll_records(response)
        
        doc.status = "Processed"
        doc.save()

    except Exception as e:
        frappe.log_error(f"Error in _process_toll_page: {str(e)}", "Toll Debug")
        _handle_error(doc, str(e))
        raise

def _make_openai_request(doc, prompt, provider_settings):
    headers = {
        "Authorization": f"Bearer {provider_settings.get_password('api_key')}",
        "Content-Type": "application/json"
    }

    data = {
        "model": provider_settings.default_model,
        "messages": [
            {
                "role": "system",
                "content": "You are an expert at analyzing toll transaction tables. Return data as an array of transactions."
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
                            "url": f"data:image/jpeg;base64,{doc.base64_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 4096,
        "temperature": float(provider_settings.temperature),
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
            
            frappe.log_error(f"API Response: {response.status_code} - {response.text}", "Toll Debug")
            if response.status_code >= 400:
                raise Exception(f"API error {response.status_code}: {response.text}")
                
        except Exception as e:
            frappe.log_error(f"Request attempt {attempt + 1} failed: {str(e)}", "Toll Debug")
            if attempt == 2:
                raise Exception(f"OpenAI request failed: {str(e)}")
                
        time.sleep(2 ** attempt)

def _create_toll_records(response):
    if not isinstance(response, list):
        frappe.log_error(f"Invalid response format: {response}", "Toll Debug")
        raise Exception("Invalid response format from AI")

    for transaction in response:
        if _validate_transaction(transaction):
            frappe.log_error(f"Creating toll record: {transaction}", "Toll Debug")
            toll = frappe.get_doc({
                "doctype": "Tolls",
                "transaction_date": transaction['transaction_date'],
                "tolling_point": transaction['tolling_point'],
                "etag_id": transaction['etag_id'],
                "net_amount": transaction['net_amount'],
                "process_status": "Unprocessed"
            })
            toll.insert()

def _validate_transaction(transaction):
    required_fields = ['transaction_date', 'tolling_point', 'etag_id', 'net_amount']
    return all(transaction.get(field) for field in required_fields)

def _handle_error(doc, error_message):
    frappe.log_error(
        message=f"Toll Page {doc.name} processing failed: {error_message}",
        title="Toll Processing Error"
    )
    doc.status = "Error"
    doc.save()