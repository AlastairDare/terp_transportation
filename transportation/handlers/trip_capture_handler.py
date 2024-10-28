import frappe
import json
import base64
import requests
import os
from datetime import datetime
from frappe import _
from frappe.utils import now, get_files_path, get_site_path, cint, cstr
from frappe.utils.background_jobs import enqueue

class TripCaptureHandler:
    def __init__(self, doc, method):
        self.doc = doc
        self.method = method
        self.ocr_settings = None
        self.chatgpt_settings = None
        self.retry_count = 0
        self.max_retries = 3

    def process_new_capture(self):
        try:
            frappe.log_error(f"Starting process_new_capture for driver {self.doc.driver}", "Trip Processing Start")
            self._validate_required_fields()
            self._fetch_settings()
            trip_doc = self._create_initial_trip()
            self._enqueue_processing(trip_doc.name)
            return trip_doc.name
        except Exception as e:
            raise

    def _validate_required_fields(self):
        if not self.doc.driver:
            frappe.throw(_("Driver is required"))
        if not self.doc.delivery_note_image:
            frappe.throw(_("Delivery Note Image is required"))
        image_path = get_files_path() + '/' + self.doc.delivery_note_image.lstrip('/files/')
        if not os.path.exists(image_path):
            frappe.throw(_("Delivery Note Image file not found"))

    def _fetch_settings(self):
        try:
            frappe.log_error("Starting _fetch_settings", "Trip Debug")
            self.ocr_settings = frappe.get_cached_doc("OCR Settings", {
                "function": "Trip Capture Config"
            })
            frappe.log_error("Got OCR settings", "Trip Debug")
            
            if not self.ocr_settings:
                frappe.log_error("No OCR Settings found", "Trip Error")
                frappe.throw(_("OCR Settings not found for Trip Capture Config"))

            self.chatgpt_settings = frappe.get_single("ChatGPT Settings")
            frappe.log_error("Got ChatGPT settings", "Trip Debug")
            
            if not self.chatgpt_settings or not self.chatgpt_settings.api_key:
                frappe.log_error("ChatGPT Settings missing or no API key", "Trip Error")
                frappe.throw(_("ChatGPT Settings not properly configured"))

        except Exception as e:
            frappe.log_error(f"Settings Error: {str(e)}", "Trip Error")
            raise

    def _create_initial_trip(self):
        try:
            trip_doc = frappe.get_doc({
                "doctype": "Trip",
                "date": frappe.utils.today(),
                "status": "Draft",
                "driver_name": self.doc.driver
            })
            trip_doc.insert(ignore_permissions=True)
            trip_doc.status = "Processing"
            trip_doc.save(ignore_permissions=True)
            return trip_doc
        except Exception as e:
            raise

    def _enqueue_processing(self, trip_id):
        enqueue(
            method=self.process_image_with_chatgpt,
            queue='long',
            timeout=1500,
            job_name=f'process_trip_capture_{self.doc.name}',
            trip_id=trip_id,
            now=True
        )

    def process_image_with_chatgpt(self, trip_id):
        try:
            trip_doc = frappe.get_doc("Trip", trip_id)
            if trip_doc.status != "Processing":
                frappe.throw(_("Invalid Trip status for processing"))
            image_path = get_files_path() + '/' + self.doc.delivery_note_image.lstrip('/files/')
            with open(image_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
            chatgpt_response = self._call_chatgpt_api(encoded_image)
            if not chatgpt_response:
                raise Exception("Failed to get response from ChatGPT")
            self._update_documents(chatgpt_response, trip_id)
        except Exception as e:
            self._handle_processing_error(e, trip_id)

    def _call_chatgpt_api(self, encoded_image):
        try:
            headers = {
                "Authorization": f"Bearer {self.chatgpt_settings.get_password('api_key')}",
                "Content-Type": "application/json"
            }
            base_url = self.chatgpt_settings.base_url.rstrip('/')
            prompt = (
                f"{self.ocr_settings.language_prompt.replace('{image_data}', encoded_image)}\n\n"
                f"Please format the response exactly like this example:\n{self.ocr_settings.json_example}"
            )
            data = {
                "model": "gpt-4-vision-preview",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{encoded_image}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 500,
                "temperature": float(self.chatgpt_settings.temperature)
            }
            response = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            if response.status_code != 200:
                raise Exception(f"ChatGPT API error: {response.text}")
            result = response.json()
            response_text = result['choices'][0]['message']['content']
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start == -1 or json_end == 0:
                raise Exception("No valid JSON found in ChatGPT response")
            json_str = response_text[json_start:json_end]
            return json.loads(json_str)
        except Exception as e:
            if self.retry_count < self.max_retries:
                self.retry_count += 1
                return self._call_chatgpt_api(encoded_image)
            else:
                raise Exception(f"Failed to process image after {self.max_retries} attempts")

    def _update_documents(self, chatgpt_data, trip_id):
        try:
            trip_doc = frappe.get_doc("Trip", trip_id)
            field_mappings = {
                'date': 'date',
                'truck_number': 'truck_number',
                'delivery_note_number': 'delivery_note_number',
                'odo_start': 'odo_start',
                'odo_end': 'odo_end',
                'time_start': 'time_start',
                'time_end': 'time_end'
            }
            for api_field, doc_field in field_mappings.items():
                if api_field in chatgpt_data:
                    value = chatgpt_data[api_field]
                    if doc_field in ['odo_start', 'odo_end']:
                        value = cint(value)
                    trip_doc.set(doc_field, value)
            trip_doc.drop_details_odo = []
            if 'drop_details_odo' in chatgpt_data:
                for odo_reading in chatgpt_data['drop_details_odo']:
                    trip_doc.append('drop_details_odo', {
                        'odometer_reading': cint(odo_reading)
                    })
            trip_doc.status = 'Completed'
            trip_doc.save(ignore_permissions=True)
            if 'delivery_note_number' in chatgpt_data:
                self.doc.delivery_note_number = chatgpt_data['delivery_note_number']
                self.doc.save(ignore_permissions=True)
            frappe.db.commit()
        except Exception as e:
            self._handle_processing_error(e, trip_id)

    def _handle_processing_error(self, error, trip_id):
        try:
            error_msg = f"""
            Trip Processing Error Details:
            Error Type: {type(error).__name__}
            Error Message: {str(error)}
            Trip ID: {trip_id}
            Driver: {self.doc.driver}
            Image Path: {self.doc.delivery_note_image}
            """
            frappe.log_error(error_msg, "Detailed Trip Processing Error")
            
            trip_doc = frappe.get_doc("Trip", trip_id)
            trip_doc.status = "Error"
            trip_doc.save(ignore_permissions=True)
        
        except Exception as e:
            frappe.log_error(f"Error Handler Failed: {str(e)}", "Error Handler Failure")

def on_trip_capture_save(doc, method):
    try:
        print("STEP 1: Before handler creation")
        handler = TripCaptureHandler(doc, method)
        
        print("STEP 2: Before process_new_capture")
        result = handler.process_new_capture()
        
        print("STEP 3: After process_new_capture")
        return result
        
    except Exception as e:
        raise Exception(f"Error in handler: {str(e)}")