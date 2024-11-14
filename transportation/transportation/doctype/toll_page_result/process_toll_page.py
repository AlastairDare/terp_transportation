import frappe
import json
import requests
import time

@frappe.whitelist()
def process_toll_pages(toll_capture_id):
    toll_pages = frappe.get_all(
        "Toll Page Result",
        filters={"parent_document": toll_capture_id, "status": "Unprocessed"},
        fields=["name"]
    )
    
    for page in toll_pages:
        try:
            doc = frappe.get_doc("Toll Page Result", page.name)
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

        response = _make_openai_request(doc, ocr_settings.language_prompt, provider_settings)
        frappe.log_error("Processing page: " + doc.name, "Toll Debug")
        
        _create_toll_records(response)
        doc.status = "Processed"
        doc.save()
        frappe.db.commit()

    except Exception as e:
        frappe.log_error(f"Error processing page {doc.name}: {str(e)}", "Toll Debug")
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
                "content": "You are an expert at analyzing toll transaction tables. Return data as a valid JSON array of transactions."
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
                parsed_content = json.loads(content)
                if isinstance(parsed_content, list):
                    return parsed_content
                elif isinstance(parsed_content, dict) and 'transactions' in parsed_content:
                    return parsed_content['transactions']
                else:
                    raise Exception("Unexpected response format")
            
            if response.status_code >= 400:
                raise Exception(f"API error {response.status_code}: {response.text}")
                
        except Exception as e:
            if attempt == 2:
                raise Exception(f"OpenAI request failed: {str(e)}")
                
        time.sleep(2 ** attempt)

def _create_toll_records(response):
    if not isinstance(response, list):
        raise Exception("Invalid response format from AI")

    for transaction in response:
        if _validate_transaction(transaction):
            toll = frappe.get_doc({
                "doctype": "Tolls",
                "transaction_date": transaction['transaction_date'],
                "tolling_point": transaction['tolling_point'],
                "etag_id": transaction['etag_id'].replace(" ", ""),
                "net_amount": transaction['net_amount'],
                "process_status": "Unprocessed"
            })
            toll.insert()

def _validate_transaction(transaction):
    required_fields = ['transaction_date', 'tolling_point', 'etag_id', 'net_amount']
    return all(transaction.get(field) for field in required_fields)

def _handle_error(doc, error_message):
    doc.status = "Error"
    doc.save()
    frappe.db.commit()
    frappe.log_error(message=error_message, title=f"Toll Page {doc.name} Error")