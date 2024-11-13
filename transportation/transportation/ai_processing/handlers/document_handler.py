import os
import base64
import tempfile
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
import frappe
from frappe.utils import get_files_path
from .base_handler import BaseHandler
from ..utils.request import DocumentRequest
from ..utils.exceptions import DocumentProcessingError

class DocumentPreparationHandler(BaseHandler):
    def handle(self, request: DocumentRequest) -> DocumentRequest:
        try:
            if request.method == "process_toll":
                self._prepare_toll_document(request)
            else:
                self._prepare_delivery_note(request)
            
            return super().handle(request)
        
        except Exception as e:
            request.set_error(e)
            raise DocumentProcessingError(f"Document preparation failed: {str(e)}")
    
    def _prepare_delivery_note(self, request):
        """Handle delivery note image preparation"""
        if not request.doc.delivery_note_image:
            raise DocumentProcessingError("Delivery Note Image is required")
        
        original_image_path = get_files_path() + '/' + request.doc.delivery_note_image.lstrip('/files/')
        if not os.path.exists(original_image_path):
            raise DocumentProcessingError("Delivery Note Image file not found")
        
        with open(original_image_path, "rb") as image_file:
            request.base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        
        trip_doc = self._create_initial_trip(request.doc)
        request.trip_id = trip_doc.name
    
    def _prepare_toll_document(self, request):
        """Handle toll PDF document preparation"""
        if not request.doc.toll_document:
            raise DocumentProcessingError("Toll Document is required")
        
        pdf_path = get_files_path() + '/' + request.doc.toll_document.lstrip('/files/')
        if not os.path.exists(pdf_path):
            raise DocumentProcessingError("Toll Document file not found")
        
        try:
            # Get total number of pages
            pdf = PdfReader(pdf_path)
            total_pages = len(pdf)
            
            # Update the document with total pages as total records
            request.doc.total_records = total_pages
            request.doc.save(ignore_permissions=True)
            
            # Create temp directory for image conversion
            with tempfile.TemporaryDirectory() as temp_dir:
                # Convert PDF to images
                images = convert_from_path(
                    pdf_path,
                    dpi=300,
                    output_folder=temp_dir,
                    fmt="jpeg",
                    output_file="page",
                    paths_only=True
                )
                
                # Process each page
                request.pages = []
                for i, image_path in enumerate(images, 1):
                    # Update progress
                    request.doc.progress_count = f"Processing page {i} of {total_pages}"
                    request.doc.save(ignore_permissions=True)
                    
                    # Convert image to base64
                    with open(image_path, "rb") as img_file:
                        base64_image = base64.b64encode(img_file.read()).decode('utf-8')
                        request.pages.append({
                            'page_number': i,
                            'base64_image': base64_image
                        })
            
            if not request.pages:
                raise DocumentProcessingError("No pages were extracted from the PDF")
            
            return request
            
        except Exception as e:
            raise DocumentProcessingError(f"Failed to process PDF document: {str(e)}")
    
    def _create_initial_trip(self, source_doc):
        """Create initial trip document"""
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