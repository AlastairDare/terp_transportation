from frappe.utils import get_files_path
import frappe
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
import base64
from PIL import Image
import tempfile
import os
from typing import List
from ..utils.request import DocumentRequest
from ..utils.exceptions import DocumentProcessingError
from .base_handler import BaseHandler

class DocumentPreparationHandler(BaseHandler):
    def handle(self, request: DocumentRequest) -> DocumentRequest:
        """Handle document preparation synchronously"""
        try:
            if request.method == "process_toll":
                frappe.logger().debug("Starting toll document processing")
                
                # Get PDF path
                pdf_path = get_files_path() + '/' + request.doc.toll_document.lstrip('/files/')
                frappe.logger().debug(f"Processing PDF: {pdf_path}")
                
                if not os.path.exists(pdf_path):
                    frappe.throw(f"PDF file not found at path: {pdf_path}")
                
                # Process PDF and save pages
                page_records = self._process_pdf_pages(pdf_path, request.doc.name)
                
                # Log success
                frappe.logger().debug(f"Successfully processed {len(page_records)} pages")
                
                return super().handle(request)
            else:
                return self._prepare_delivery_note(request)
                
        except Exception as e:
            frappe.log_error("Document Processing Error", str(e))
            frappe.throw(str(e))

    def _process_pdf_pages(self, pdf_path: str, doc_name: str) -> List[str]:
        """Process PDF pages and return list of Toll Page Result IDs"""
        page_records = []
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                frappe.logger().debug(f"Created temp directory: {temp_dir}")
                
                # Convert PDF pages to images
                frappe.logger().debug("Converting PDF to images...")
                images = convert_from_path(
                    pdf_path,
                    dpi=150,
                    output_folder=temp_dir,
                    fmt="jpeg",
                    paths_only=True
                )
                
                frappe.logger().debug(f"Converted {len(images)} pages")
                
                # Process each image
                for idx, image_path in enumerate(images, 1):
                    frappe.logger().debug(f"Processing page {idx}")
                    
                    # Optimize image
                    optimized_path = self._optimize_image(image_path)
                    
                    # Convert to base64
                    with open(optimized_path, "rb") as img_file:
                        base64_image = base64.b64encode(img_file.read()).decode('utf-8')
                    
                    # Create Toll Page Result
                    page_doc = frappe.get_doc({
                        "doctype": "Toll Page Result",
                        "parent_document": doc_name,
                        "page_number": idx,
                        "base64_image": base64_image,
                        "status": "Completed"
                    }).insert(ignore_permissions=True)
                    
                    frappe.logger().debug(f"Saved page {idx} with ID {page_doc.name}")
                    page_records.append(page_doc.name)
                    
                    # Commit after each page to ensure it's saved
                    frappe.db.commit()
                
                return page_records
                
        except Exception as e:
            frappe.logger().error(f"Error processing PDF: {str(e)}")
            raise

    def _optimize_image(self, image_path: str) -> str:
        """Optimize image size while maintaining readability"""
        try:
            with Image.open(image_path) as img:
                max_dimension = 1200
                ratio = min(max_dimension / float(img.size[0]), 
                          max_dimension / float(img.size[1]))
                
                if ratio < 1:
                    new_size = tuple(int(dim * ratio) for dim in img.size)
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                
                optimized_path = image_path.replace('.jpg', '_optimized.jpg')
                img.save(optimized_path, 'JPEG', quality=50, optimize=True)
                return optimized_path
        except Exception as e:
            frappe.logger().error(f"Error optimizing image: {str(e)}")
            raise

    def _prepare_delivery_note(self, request: DocumentRequest) -> DocumentRequest:
        """Original delivery note method remains unchanged"""
        if not request.doc.delivery_note_image:
            raise DocumentProcessingError("Delivery Note Image is required")
        
        original_image_path = get_files_path() + '/' + request.doc.delivery_note_image.lstrip('/files/')
        if not os.path.exists(original_image_path):
            raise DocumentProcessingError("Delivery Note Image file not found")
        
        with open(original_image_path, "rb") as image_file:
            request.base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        
        trip_doc = self._create_initial_trip(request.doc)
        request.trip_id = trip_doc.name
        return request

    def _create_initial_trip(self, source_doc):
        """Original create_initial_trip method remains unchanged"""
        try:
            employee_name = frappe.get_value("Employee", source_doc.employee, "employee_name")
            trip_doc = frappe.get_doc({
                "doctype": "Trip",
                "date": frappe.utils.today(),
                "status": "Draft",
                "driver": source_doc.employee,
                "employee_name": employee_name
            })
            trip_doc.insert(ignore_permissions=True)
            trip_doc.status = "Processing"
            trip_doc.save(ignore_permissions=True)
            return trip_doc
        except Exception as e:
            raise DocumentProcessingError(f"Failed to create trip document: {str(e)}")