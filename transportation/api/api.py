import frappe
from frappe import _
import base64
import requests
import json
from PIL import Image
import io

CHATGPT_API_KEY = "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"  # Replace with your actual API key

@frappe.whitelist()
def create_trip_record():
    try:
        # Get the uploaded files
        trip_sheet = frappe.request.files.get('trip_sheet')
        delivery_note = frappe.request.files.get('delivery_note')
        
        if not trip_sheet or not delivery_note:
            frappe.throw(_("Both images are required"))

        # Create new Trip Image document
        doc = frappe.new_doc("Trip Image")
        
        # Save the images as attachments
        trip_sheet_file = frappe.get_doc({
            "doctype": "File",
            "file_name": f"trip_sheet_{frappe.generate_hash()}.jpg",
            "attached_to_doctype": "Trip Image",
            "content": trip_sheet.read()
        })
        trip_sheet_file.save()
        
        delivery_note_file = frappe.get_doc({
            "doctype": "File",
            "file_name": f"delivery_note_{frappe.generate_hash()}.jpg",
            "attached_to_doctype": "Trip Image",
            "content": delivery_note.read()
        })
        delivery_note_file.save()
        
        # Set initial values
        doc.update({
            "status": "Draft",
            "trip_sheet_image": trip_sheet_file.file_url,
            "delivery_note_image": delivery_note_file.file_url
        })
        
        doc.save()
        
        # Create a background job for ChatGPT processing
        frappe.enqueue(
            'transportation.api.process_images_with_chatgpt',
            queue='long',
            job_name=f'process_trip_images_{doc.name}',
            doc_name=doc.name,
            trip_sheet_url=trip_sheet_file.file_url,
            delivery_note_url=delivery_note_file.file_url
        )
        
        return {
            "success": True,
            "message": "Images uploaded successfully",
            "doc_name": doc.name
        }
        
    except Exception as e:
        frappe.log_error(f"Trip Image Upload Error: {str(e)}")
        return {
            "success": False,
            "message": "Failed to upload images"
        }

def process_images_with_chatgpt(doc_name, trip_sheet_url, delivery_note_url):
    """Background job to process images with ChatGPT"""
    try:
        doc = frappe.get_doc("Trip Image", doc_name)
        
        # Process Trip Sheet
        trip_sheet_data = process_trip_sheet(doc.trip_sheet_image)
        if trip_sheet_data:
            doc.update(trip_sheet_data)
        
        # Process Delivery Note
        delivery_note_data = process_delivery_note(doc.delivery_note_image)
        if delivery_note_data:
            doc.update(delivery_note_data)
        
        doc.status = "Completed"
        doc.save()
        frappe.db.commit()
        
    except Exception as e:
        frappe.log_error(f"ChatGPT Processing Error: {str(e)}")
        doc.status = "Error"
        doc.save()
        frappe.db.commit()

def process_trip_sheet(image_path):
    """Process trip sheet image with ChatGPT"""
    try:
        with open(frappe.get_site_path() + image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {CHATGPT_API_KEY}"
        }
        
        payload = {
            "model": "gpt-4-vision-preview",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Extract the following information from this trip sheet image and return as JSON:
                                {
                                    "driver_name": "exact name as written",
                                    "truck": "truck number",
                                    "cargo_mass": numeric value only,
                                    "date": "YYYY-MM-DD format"
                                }"""
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
            "max_tokens": 300
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return json.loads(result['choices'][0]['message']['content'])
        else:
            frappe.log_error(f"ChatGPT Trip Sheet API Error: {response.text}")
            return None
            
    except Exception as e:
        frappe.log_error(f"Trip Sheet Processing Error: {str(e)}")
        return None

def process_delivery_note(image_path):
    """Process delivery note image with ChatGPT"""
    try:
        with open(frappe.get_site_path() + image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {CHATGPT_API_KEY}"
        }
        
        payload = {
            "model": "gpt-4-vision-preview",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Extract the end kilometer reading from this delivery note and return as JSON:
                                {
                                    "end_km": numeric value only
                                }"""
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
            "max_tokens": 100
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return json.loads(result['choices'][0]['message']['content'])
        else:
            frappe.log_error(f"ChatGPT Delivery Note API Error: {response.text}")
            return None
            
    except Exception as e:
        frappe.log_error(f"Delivery Note Processing Error: {str(e)}")
        return None