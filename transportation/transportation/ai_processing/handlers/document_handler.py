import os
import base64
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
from PIL import Image
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
import frappe
from frappe.utils import get_files_path
from .base_handler import BaseHandler
from ..utils.request import DocumentRequest
from ..utils.exceptions import DocumentProcessingError

class DocumentPreparationHandler(BaseHandler):
    def handle(self, request: DocumentRequest) -> DocumentRequest:
        """Required implementation of abstract handle method"""
        try:
            if request.method == "process_toll":
                self._prepare_toll_document(request)
            else:
                self._prepare_delivery_note(request)
            
            return super().handle(request)
        
        except Exception as e:
            request.set_error(e)
            raise DocumentProcessingError(f"Document preparation failed: {str(e)}")

    def _optimize_image(self, image_path: str) -> str:
        """Optimize image size while maintaining readability"""
        try:
            with Image.open(image_path) as img:
                max_dimension = 1200
                ratio = min(max_dimension / float(img.size[0]), 
                          max_dimension / float(img.size[1]))
                new_size = tuple(int(dim * ratio) for dim in img.size)
                
                optimized = img.resize(new_size, Image.Resampling.LANCZOS)
                temp_path = image_path.replace('.jpg', '_optimized.jpg')
                optimized.save(temp_path, 'JPEG', quality=50, optimize=True)
                return temp_path
        except Exception as e:
            frappe.log_error(f"Image optimization failed: {str(e)}", "Image Optimization Error")
            return image_path

    def _process_single_page(self, image_path: str, page_number: int, total_pages: int) -> Optional[Dict]:
        """Process a single page in parallel"""
        try:
            # Log start of page processing
            frappe.logger("toll_capture").info(f"Starting processing of page {page_number}/{total_pages}")
            
            # Optimize the image
            optimized_path = self._optimize_image(image_path)
            
            # Convert to base64
            with open(optimized_path, "rb") as img_file:
                base64_image = base64.b64encode(img_file.read()).decode('utf-8')
                
                return {
                    'page_number': page_number,
                    'base64_image': base64_image
                }
                
        except Exception as e:
            frappe.log_error(
                f"Failed to process page {page_number}: {str(e)}", 
                f"Page {page_number} Processing Error"
            )
            return None

    def _prepare_toll_document(self, request: DocumentRequest) -> DocumentRequest:
        """Handle toll PDF document preparation with parallel processing"""
        if not request.doc.toll_document:
            raise DocumentProcessingError("Toll Document is required")
        
        pdf_path = get_files_path() + '/' + request.doc.toll_document.lstrip('/files/')
        if not os.path.exists(pdf_path):
            raise DocumentProcessingError("Toll Document file not found")
        
        try:
            # Initial serial phase - PDF preparation
            frappe.logger("toll_capture").info("Starting PDF processing")
            
            # Get total pages
            pdf = PdfReader(pdf_path)
            total_pages = len(pdf.pages)
            
            request.doc.total_records = total_pages
            request.doc.save(ignore_permissions=True)
            
            # Convert PDF to images
            with tempfile.TemporaryDirectory() as temp_dir:
                frappe.logger("toll_capture").info("Converting PDF to images")
                
                images = convert_from_path(
                    pdf_path,
                    dpi=150,
                    output_folder=temp_dir,
                    fmt="jpeg",
                    output_file="page",
                    paths_only=True,
                    poppler_path="/usr/bin"
                )
                
                # Parallel processing phase
                request.pages = []
                successful_pages = 0
                
                with ThreadPoolExecutor(max_workers=3) as executor:
                    # Create futures for all pages
                    future_to_page = {
                        executor.submit(
                            self._process_single_page, 
                            image_path, 
                            i, 
                            total_pages
                        ): (i, image_path) 
                        for i, image_path in enumerate(images, 1)
                    }
                    
                    # Process completed futures as they finish
                    for future in as_completed(future_to_page):
                        page_num, _ = future_to_page[future]
                        try:
                            result = future.result()
                            if result:
                                request.pages.append(result)
                                successful_pages += 1
                                
                                # Update progress
                                request.doc.progress_count = (
                                    f"Processed {successful_pages} of {total_pages} pages"
                                )
                                request.doc.save(ignore_permissions=True)
                                
                        except Exception as e:
                            frappe.log_error(
                                f"Error processing future for page {page_num}: {str(e)}",
                                "Page Processing Error"
                            )
                
                if not request.pages:
                    raise DocumentProcessingError("No valid pages were extracted from the PDF")
                
                frappe.logger("toll_capture").info(
                    f"Successfully processed {successful_pages} of {total_pages} pages"
                )
                return request
                
        except Exception as e:
            frappe.log_error(str(e), "PDF Processing Error")
            raise DocumentProcessingError(f"Failed to process PDF document: {str(e)}")

    def _prepare_delivery_note(self, request: DocumentRequest) -> DocumentRequest:
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