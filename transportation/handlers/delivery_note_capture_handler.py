import frappe
import json
import base64
import requests
import os
from PIL import Image
import io
import cv2
import numpy as np
from datetime import datetime
from frappe import _
from frappe.utils import now, get_files_path, get_site_path, cint, cstr
from frappe.utils.background_jobs import enqueue

class ImageOptimizer:
    def __init__(self, doc):
        self.doc = doc
        self.max_dimension = 1024
        self.jpeg_quality = 60
        self.optimized_image_path = None
        self.max_file_size = 1024 * 1024  # 1MB target size
        
    def process_image(self):
        """Main function to process and optimize the image"""
        try:
            original_image_path = get_files_path() + '/' + self.doc.delivery_note_image.lstrip('/files/')
            original_size = os.path.getsize(original_image_path)
            
            if original_size <= self.max_file_size:
                self.optimized_image_path = original_image_path
                return self.doc.delivery_note_image
            
            with Image.open(original_image_path) as img:
                width, height = img.size
                
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                if width > self.max_dimension or height > self.max_dimension:
                    img = self._resize_image(img)
                
                optimized_filename = f"ocr_ready_{os.path.basename(original_image_path)}"
                self.optimized_image_path = os.path.join(get_files_path(), optimized_filename)
                
                img.save(
                    self.optimized_image_path,
                    'JPEG',
                    quality=self.jpeg_quality,
                    optimize=True
                )
                
                optimized_size = os.path.getsize(self.optimized_image_path)
                
                if optimized_size > original_size:
                    if os.path.exists(self.optimized_image_path):
                        os.remove(self.optimized_image_path)
                    self.optimized_image_path = original_image_path
                    return self.doc.delivery_note_image
                
                relative_path = os.path.join('files', optimized_filename)
                self.doc.ocr_ready_image = relative_path
                self.doc.save(ignore_permissions=True)
                
                return relative_path
                
        except Exception as e:
            frappe.log_error(f"Image optimization failed: {str(e)}", "Image Processing Error")
            raise
            
    def _resize_image(self, img):
        width, height = img.size
        if width > self.max_dimension or height > self.max_dimension:
            if width > height:
                new_width = self.max_dimension
                new_height = int(height * (self.max_dimension / width))
            else:
                new_height = self.max_dimension
                new_width = int(width * (self.max_dimension / height))
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        return img

    def get_base64_image(self):
        """Convert image to base64 string"""
        if not self.optimized_image_path or not os.path.exists(self.optimized_image_path):
            raise ValueError("Image not found")
            
        with open(self.optimized_image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')


class DeliveryNoteCaptureHandler:
    def __init__(self, doc, method):
        self.doc = doc
        self.method = method
        self.ocr_settings = None
        self.chatgpt_settings = None
        self.retry_count = 0
        self.max_retries = 3

    def process_new_capture(self):
        try:
            self._validate_required_fields()
            self._fetch_settings()
            trip_doc = self._create_initial_trip()
            self._enqueue_processing(trip_doc.name)
            return trip_doc.name
        except Exception as e:
            raise

    def _validate_required_fields(self):
        if not self.doc.employee:
            frappe.throw(_("Employee is required"))
        if not self.doc.delivery_note_image:
            frappe.throw(_("Delivery Note Image is required"))
        image_path = get_files_path() + '/' + self.doc.delivery_note_image.lstrip('/files/')
        if not os.path.exists(image_path):
            frappe.throw(_("Delivery Note Image file not found"))

    def _fetch_settings(self):
        try:
            self.ocr_settings = frappe.get_cached_doc("OCR Settings", {
                "function": "Delivery Note Capture Config"
            })
            
            if not self.ocr_settings:
                frappe.throw(_("OCR Settings not found for Delivery Note Capture Config"))

            self.chatgpt_settings = frappe.get_single("ChatGPT Settings")
            
            if not self.chatgpt_settings or not self.chatgpt_settings.api_key:
                frappe.throw(_("ChatGPT Settings not properly configured"))

        except Exception as e:
            raise

    def _create_initial_trip(self):
        try:
            employee_name = frappe.get_value("Employee", self.doc.employee, "employee_name")
            trip_doc = frappe.get_doc({
                "doctype": "Trip",
                "date": frappe.utils.today(),
                "status": "Draft",
                "employee": self.doc.employee,
                "employee_name": employee_name
            })
            trip_doc.insert(ignore_permissions=True)
            trip_doc.status = "Processing"
            trip_doc.save(ignore_permissions=True)
            return trip_doc
        except Exception as e:
            raise

    def _enqueue_processing(self, trip_id):
        try:
            frappe.msgprint(_("Processing delivery note capture..."))
            trip_doc = frappe.get_doc("Trip", trip_id)
            trip_doc.status = "Processing"
            trip_doc.save(ignore_permissions=True)
            frappe.db.commit()
            
            try:
                self.process_image_with_chatgpt(trip_id)
                frappe.msgprint(_("Processing completed successfully"))
            except Exception as e:
                trip_doc.status = "Error"
                trip_doc.save(ignore_permissions=True)
                frappe.db.commit()
                raise
                
        except Exception as e:
            raise

    def process_image_with_chatgpt(self, trip_id):
        try:
            trip_doc = frappe.get_doc("Trip", trip_id)
            if trip_doc.status != "Processing":
                frappe.throw(_("Invalid Trip status for processing"))

            optimizer = ImageOptimizer(self.doc)
            optimizer.process_image()
            encoded_image = optimizer.get_base64_image()

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
                "model": self.chatgpt_settings.default_model,
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
                raise

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
                        'odometer_reading': cint(odo_reading),
                        'parent_trip': trip_doc.name
                    })
            trip_doc.status = 'Awaiting Approval'
            trip_doc.save(ignore_permissions=True)
            if 'delivery_note_number' in chatgpt_data:
                self.doc.delivery_note_number = chatgpt_data['delivery_note_number']
                self.doc.save(ignore_permissions=True)
            frappe.db.commit()
        except Exception as e:
            self._handle_processing_error(e, trip_id)

    def _handle_processing_error(self, error, trip_id):
        try:
            error_msg = f"Trip Processing Error: {str(error)}"
            frappe.log_error(error_msg, "Trip Processing Error")
            
            trip_doc = frappe.get_doc("Trip", trip_id)
            trip_doc.status = "Error"
            trip_doc.save(ignore_permissions=True)
        
        except Exception as e:
            frappe.log_error(f"Error Handler Failed: {str(e)}", "Error Handler Failure")

def on_delivery_note_capture_save(doc, method):
    try:
        handler = DeliveryNoteCaptureHandler(doc, method)
        handler._validate_required_fields()
        handler._fetch_settings()
        trip_doc = handler._create_initial_trip()
        handler._enqueue_processing(trip_doc.name)
        return trip_doc.name
    except Exception as e:
        raise