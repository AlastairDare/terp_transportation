import frappe
from frappe import _
from frappe.model.document import Document
import fitz
import io
import base64
from PIL import Image, ImageDraw
import json
import requests
import time

class TollCapture(Document):
    def __init__(self, *args, **kwargs):
        super(TollCapture, self).__init__(*args, **kwargs)
        
    def format_image(self, image, is_first_page=False):
        """Apply cropping excluding middle section in one operation"""
        try:
            original_width = image.width
            original_height = image.height
            
            # Calculate initial crop boundaries
            crop_left = int(original_width * 0.10)    
            crop_right = int(original_width * 0.87)   
            
            if is_first_page:
                crop_top = int(original_height * 0.605)   
                crop_bottom = int(original_height * 0.845)
            else:
                crop_top = int(original_height * 0.225)    
                crop_bottom = int(original_height * 0.87)
            
            # Initial crop to get working dimensions
            cropped_image = image.crop((crop_left, crop_top, crop_right, crop_bottom))
            
            # Calculate split point for middle section
            split_point = int(cropped_image.width * 0.585)
            join_point = int(cropped_image.width * 0.92)
            
            # Create final image excluding middle section
            final_width = split_point + (cropped_image.width - join_point)
            final_image = Image.new('RGB', (final_width, cropped_image.height))
            
            # Copy left and right sections in one operation
            final_image.paste(cropped_image.crop((0, 0, split_point, cropped_image.height)), (0, 0))
            final_image.paste(cropped_image.crop((join_point, 0, cropped_image.width, cropped_image.height)), (split_point, 0))
            
            return final_image
            
        except Exception as e:
            frappe.log_error(f"Error formatting image: {str(e)}")
            raise e

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
            
            # First pass: evaluate each page
            valid_pages = []
            for pdf_page_num in range(len(pdf_document)):
                page = pdf_document[pdf_page_num]
                pix = page.get_pixmap()
                
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='JPEG', quality=85)
                img_buffer.seek(0)
                base64_image = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
                
                if self._check_page_validity(base64_image, pdf_page_num + 1):
                    valid_pages.append(pdf_page_num)
            
            # Process valid pages
            for idx, valid_page_num in enumerate(valid_pages):
                page = pdf_document[valid_page_num]
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # Check if this is the first page of the PDF
                is_first_page = valid_page_num == 0
                
                # Apply formatting
                final_img = self.format_image(img, is_first_page)
                
                # Convert to base64
                buffer = io.BytesIO()
                final_img.save(buffer, format='JPEG', quality=85)
                buffer.seek(0)
                final_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                
                # Create Toll Page Result
                frappe.get_doc({
                    "doctype": "Toll Page Result",
                    "parent_document": self.name,
                    "page_number": idx + 1,
                    "base64_image": final_base64,
                    "status": "Unprocessed"
                }).insert()
            
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