import frappe
import json
import base64
import requests
from frappe import _
from frappe.utils import now, get_files_path, get_site_path
import os

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
            # Get OCR settings for Trip Capture
            self.ocr_settings = frappe.get_doc("OCR Settings", {
                "function": "Trip Capture Config"
            })
            
            # Get ChatGPT settings
            self.chatgpt_settings = frappe.get_single("ChatGPT Settings")
            
            if not self.ocr_settings:
                frappe.log_error(
                    _("OCR Settings not found for Trip Capture Config"),
                    "Trip Capture Processing Error"
                )
                return

            # Create a new Trip record with pending status
            trip_doc = frappe.get_doc({
                "doctype": "Trip",
                "date": frappe.utils.today(),
                "status": "Pending"  # You might need to add this field to Trip doctype
            })
            trip_doc.insert(ignore_permissions=True)

            # Enqueue the background job
            frappe.enqueue(
                method=self.process_image_with_chatgpt,
                queue='long',
                timeout=1500,
                job_name=f'process_trip_capture_{self.doc.name}',
                trip_id=trip_doc.name,
                now=True
            )

        except Exception as e:
            frappe.log_error(
                frappe.get_traceback(),
                f"Trip Capture Processing Error: {str(e)}"
            )
            raise

    def process_image_with_chatgpt(self, trip_id):
        try:
            # Get the image file
            image_path = get_files_path() + '/' + self.doc.delivery_note_image.lstrip('/files/')
            
            if not os.path.exists(image_path):
                raise Exception("Image file not found")

            # Read and encode image
            with open(image_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode('utf-8')

            # Prepare ChatGPT API request
            chatgpt_response = self.call_chatgpt_api(encoded_image)
            
            if not chatgpt_response:
                raise Exception("Failed to get response from ChatGPT")

            # Process the response and update documents
            self.update_documents(chatgpt_response, trip_id)

        except Exception as e:
            self.handle_processing_error(e, trip_id)

    def call_chatgpt_api(self, encoded_image):
        try:
            # Validate ChatGPT settings
            if not self.chatgpt_settings.api_key:
                raise Exception("OpenAI API key not configured")

            # Prepare the prompt
            prompt = self.ocr_settings.language_prompt.replace(
                "{image_data}", encoded_image
            )

            # Add JSON example to the prompt
            prompt += f"\n\nPlease format the response exactly like this example:\n{self.ocr_settings.json_example}"

            # Make API request to ChatGPT
            headers = {
                "Authorization": f"Bearer {self.chatgpt_settings.get_password('api_key')}",
                "Content-Type": "application/json"
            }
            
            # Use configured base URL
            base_url = self.chatgpt_settings.base_url.rstrip('/')
            
            data = {
                "model": "gpt-4-vision-preview",  # Vision model is required for image analysis
                "messages": [
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
                                    "url": f"data:image/jpeg;base64,{encoded_image}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 500,
                "temperature": self.chatgpt_settings.temperature
            }

            response = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=data
            )

            if response.status_code != 200:
                raise Exception(f"ChatGPT API error: {response.text}")

            # Extract and parse JSON from response
            result = response.json()
            response_text = result['choices'][0]['message']['content']
            
            # Find and parse the JSON portion of the response
            try:
                # Look for JSON structure in the response
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                json_str = response_text[json_start:json_end]
                return json.loads(json_str)
            except Exception as e:
                raise Exception(f"Failed to parse ChatGPT response: {str(e)}")

        except Exception as e:
            if self.retry_count < self.max_retries:
                self.retry_count += 1
                frappe.log_error(
                    f"ChatGPT API call failed (attempt {self.retry_count}): {str(e)}",
                    "ChatGPT API Error"
                )
                return self.call_chatgpt_api(encoded_image)
            else:
                raise Exception(f"Failed to process image after {self.max_retries} attempts")

    def update_documents(self, chatgpt_data, trip_id):
        try:
            # Update Trip document
            trip_doc = frappe.get_doc("Trip", trip_id)
            
            # Update fields from ChatGPT response
            trip_doc.date = chatgpt_data.get('date')
            trip_doc.truck_number = chatgpt_data.get('truck_number')
            trip_doc.odo_start = chatgpt_data.get('odo_start')
            trip_doc.odo_end = chatgpt_data.get('odo_end')
            trip_doc.time_start = chatgpt_data.get('time_start')
            trip_doc.time_end = chatgpt_data.get('time_end')
            
            # Clear existing drop details if any
            trip_doc.drop_details_odo = []
            
            # Add drop details
            for odo_reading in chatgpt_data.get('drop_details_odo', []):
                trip_doc.append('drop_details_odo', {
                    'odometer_reading': odo_reading
                })
            
            trip_doc.status = 'Completed'
            trip_doc.save()

            # Update Trip Capture with delivery note number
            self.doc.delivery_note_number = chatgpt_data.get('delivery_note_number')
            self.doc.save()

            frappe.db.commit()

        except Exception as e:
            frappe.log_error(
                frappe.get_traceback(),
                f"Document Update Error: {str(e)}"
            )
            self.handle_processing_error(e, trip_id)

    def handle_processing_error(self, error, trip_id):
        try:
            # Update Trip status to Error
            trip_doc = frappe.get_doc("Trip", trip_id)
            trip_doc.status = 'Error'
            trip_doc.save()

            # Log the error
            frappe.log_error(
                frappe.get_traceback(),
                f"Trip Processing Error: {str(error)}"
            )

            # Notify admin
            frappe.sendmail(
                recipients=[frappe.get_system_settings('admin_email_address')],
                subject=f"Trip Processing Error: {trip_id}",
                message=f"Error processing trip capture: {str(error)}\n\nPlease check the error log for details."
            )

        except Exception as e:
            frappe.log_error(
                frappe.get_traceback(),
                f"Error Handler Failed: {str(e)}"
            )