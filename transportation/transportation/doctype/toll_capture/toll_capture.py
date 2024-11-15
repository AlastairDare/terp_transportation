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
        self.header_image = None
        
    def set_header_image(self, header_base64):
        """Process and store the header image at the correct width"""
        try:
            # Decode base64 to image
            header_bytes = base64.b64decode(header_base64)
            header_image = Image.open(io.BytesIO(header_bytes))
            
            # Calculate new height maintaining aspect ratio
            target_width = 595
            aspect_ratio = header_image.height / header_image.width
            new_height = int(target_width * aspect_ratio)
            
            # Resize image
            resized_header = header_image.resize((target_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert back to base64
            buffer = io.BytesIO()
            resized_header.save(buffer, format='JPEG', quality=85)
            buffer.seek(0)
            self.header_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
        except Exception as e:
            frappe.log_error(f"Error processing header image: {str(e)}")
            raise e
        
    def format_final_image(self, combined_image):
        """Apply white space and cropping to the combined image"""
        try:
            # Get original dimensions for all calculations
            original_width = combined_image.width
            original_height = combined_image.height
            
            # Calculate white space boundaries (vertical strip)
            white_start_x = int(original_width * 0.55)  # 55% from left
            white_end_x = int(original_width * 0.78)    # 78% from left
            
            # Calculate final crop boundaries
            crop_left = int(original_width * 0.10)      # 10% from left
            crop_right = int(original_width * 0.88)     # 88% from left
            
            # Create a drawing object for white space
            draw = ImageDraw.Draw(combined_image)
            
            # Fill white space region
            draw.rectangle(
                [
                    (white_start_x, 0),           # top-left of white space
                    (white_end_x, original_height) # bottom-right of white space
                ],
                fill='white'
            )
            
            # Perform the crop operation
            cropped_image = combined_image.crop(
                (
                    crop_left,        # left
                    0,                # top
                    crop_right,       # right
                    original_height   # bottom
                )
            )
            
            return cropped_image
            
        except Exception as e:
            frappe.log_error(f"Error formatting final image: {str(e)}")
            raise e

    def combine_header_with_section(self, section_base64):
        """Combine the stored header with a section image and apply formatting"""
        try:
            # Convert both images from base64
            header_bytes = base64.b64decode(self.header_image)
            header_img = Image.open(io.BytesIO(header_bytes))
            
            section_bytes = base64.b64decode(section_base64)
            section_img = Image.open(io.BytesIO(section_bytes))
            
            # Create new image with combined height
            combined_height = header_img.height + section_img.height
            combined_img = Image.new('RGB', (595, combined_height))
            
            # Paste header and section
            combined_img.paste(header_img, (0, 0))
            combined_img.paste(section_img, (0, header_img.height))
            
            # Apply white space and cropping
            final_img = self.format_final_image(combined_img)
            
            # Convert back to base64
            buffer = io.BytesIO()
            final_img.save(buffer, format='JPEG', quality=85)
            buffer.seek(0)
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
            
        except Exception as e:
            frappe.log_error(f"Error combining images: {str(e)}")
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
            # Set your header image here - replace this string with your actual base64 header
            self.set_header_image("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")
            
            file_path = frappe.get_site_path('public', self.toll_document.lstrip('/'))
            pdf_document = fitz.open(file_path)
            
            current_page_number = 1
            
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
            for valid_page_num in valid_pages:
                page = pdf_document[valid_page_num]
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                height = img.height
                crops = [
                    (0, 0, img.width, int(height * 0.25)),              # 0-25%
                    (0, int(height * 0.20), img.width, int(height * 0.45)),  # 20-45%
                    (0, int(height * 0.40), img.width, int(height * 0.65)),  # 40-65%
                    (0, int(height * 0.60), img.width, int(height * 0.85)),  # 60-85%
                    (0, int(height * 0.80), img.width, height)          # 80-100%
                ]

                for crop_box in crops:
                    section_img = img.crop(crop_box)
                    img_buffer = io.BytesIO()
                    section_img.save(img_buffer, format='JPEG', quality=85)
                    img_buffer.seek(0)
                    section_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
                    
                    # Combine header with section
                    combined_base64 = self.combine_header_with_section(section_base64)
                    
                    frappe.get_doc({
                        "doctype": "Toll Page Result",
                        "parent_document": self.name,
                        "page_number": current_page_number,
                        "base64_image": combined_base64,
                        "status": "Unprocessed"
                    }).insert()
                    
                    current_page_number += 1
            
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