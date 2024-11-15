import frappe
from frappe import _
from frappe.model.document import Document
import fitz
import io
import base64
from PIL import Image

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
            
            for pdf_page_num in range(len(pdf_document)):
                page = pdf_document[pdf_page_num]
                pix = page.get_pixmap()
                
                # Convert pixmap to PIL Image
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
                
            self.status = "Processed"
            self.save()
            frappe.db.commit()
            
        except Exception as e:
            frappe.log_error(str(e))
            raise e
        finally:
            if 'pdf_document' in locals():
                pdf_document.close()