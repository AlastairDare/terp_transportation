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
            
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                pix = page.get_pixmap()
                
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='JPEG', quality=85)
                img_buffer.seek(0)
                
                base64_image = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
                
                frappe.get_doc({
                    "doctype": "Toll Page Result",
                    "parent_document": self.name,
                    "page_number": page_num + 1,
                    "base64_image": base64_image,
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