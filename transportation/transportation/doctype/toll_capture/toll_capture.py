import frappe
from frappe import _
from frappe.model.document import Document
import fitz
import io
import base64
from PIL import Image
import json
import requests
import time

class TollCapture(Document):
    def validate(self):
        if self.status != "Unprocessed":
            return
            
        if not self.toll_document:
            frappe.throw(_("Toll document is required"))

    def after_insert(self):
        if self.status != "Unprocessed":
            return
            
        try:
            file_path = frappe.get_site_path('public', self.toll_document.lstrip('/'))
            pdf_document = fitz.open(file_path)
            
            current_page_number = 1  # This will track our sequential page numbers for sections
            
            frappe.publish_progress(
                0,
                "Evaluating pages...",
                doctype="Toll Capture",
                docname=self.name
            )
            
            # First pass: evaluate each page
            valid_pages = []
            for pdf_page_num in range(len(pdf_document)):
                page = pdf_document[pdf_page_num]
                pix = page.get_pixmap()
                
                # Convert pixmap to PIL Image for AI evaluation
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='JPEG', quality=85)
                img_buffer.seek(0)
                base64_image = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
                
                if self._check_page_validity(base64_image, pdf_page_num + 1):
                    valid_pages.append(pdf_page_num)
                
                frappe.publish_progress(
                    ((pdf_page_num + 1) / len(pdf_document)) * 50,
                    "Evaluating pages...",
                    doctype="Toll Capture",
                    docname=self.name
                )
            
            # Second pass: process valid pages
            frappe.publish_progress(
                50,
                "Saving formatted documents...",
                doctype="Toll Capture",
                docname=self.name
            )
            
            for idx, pdf_page_num in enumerate(valid_pages):
                page = pdf_document[pdf_page_num]
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # Calculate section boundaries
                height = img.height
                # Section 1: 0% to 25%
                first_crop = (0, 0, img.width, int(height * 0.25))
                # Section 2: 20% to 45%
                second_crop = (0, int(height * 0.20), img.width, int(height * 0.45))
                # Section 3: 40% to 65%
                third_crop = (0, int(height * 0.40), img.width, int(height * 0.65))
                # Section 4: 60% to 85%
                fourth_crop = (0, int(height * 0.60), img.width, int(height * 0.85))
                # Section 5: 80% to 100%
                fifth_crop = (0, int(height * 0.80), img.width, height)

                # Process each section
                for crop_box in [first_crop, second_crop, third_crop, fourth_crop, fifth_crop]:
                    # Crop the image to the current section
                    section_img = img.crop(crop_box)
                    
                    # Convert section to base64
                    img_buffer = io.BytesIO()
                    section_img.save(img_buffer, format='JPEG', quality=85)
                    img_buffer.seek(0)
                    base64_image = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
                    
                    # Create Toll Page Result record for this section
                    frappe.get_doc({
                        "doctype": "Toll Page Result",
                        "parent_document": self.name,
                        "page_number": current_page_number,
                        "base64_image": base64_image,
                        "status": "Unprocessed"
                    }).insert()
                    
                    current_page_number += 1
                
                frappe.publish_progress(
                    50 + ((idx + 1) / len(valid_pages)) * 50,
                    "Saving formatted documents...",
                    doctype="Toll Capture",
                    docname=self.name
                )
            
            self.status = "Processed"
            self.save()
            frappe.db.commit()
            
        except Exception as e:
            frappe.log_error(str(e))
            raise e
        finally:
            if 'pdf_document' in locals():
                pdf_document.close()

    def _check_page_validity(self, base64_image, page_number):
        """Check if a page contains valid toll transactions using OpenAI's vision API"""
        provider_settings = frappe.get_single("ChatGPT Settings")
        
        headers = {
            "Authorization": f"Bearer {provider_settings.get_password('api_key')}",
            "Content-Type": "application/json"
        }

        prompt = """Analyze this image and determine if it contains a table with toll transactions. 
                   A valid table must have at least one record with both a "Transaction Date & Time" column 
                   and an "e-tag ID" column with data in them. Respond with a JSON object containing a single 
                   key "contains_valid_toll_transactions" with value "yes" or "no"."""

        data = {
            "model": provider_settings.default_model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert at analyzing toll transaction tables."
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
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 4096,
            "temperature": 0,
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
                    
                    is_valid = parsed_content.get('contains_valid_toll_transactions') == 'yes'
                    frappe.log_error(
                        f"Page {page_number} validity check: {is_valid}",
                        "Toll Page Validation"
                    )
                    return is_valid
                
                if response.status_code >= 400:
                    raise Exception(f"API error {response.status_code}: {response.text}")
                    
            except Exception as e:
                if attempt == 2:
                    frappe.log_error(
                        f"Failed to check page {page_number} validity: {str(e)}",
                        "Toll Page Validation Error"
                    )
                    return False  # Assume invalid on error
                    
            time.sleep(2 ** attempt)
        
        return False  # Default to invalid if all attempts fail