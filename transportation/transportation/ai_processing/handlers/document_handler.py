import os
import base64
import tempfile
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

    def _optimize_image(self, image_path):
        """Optimize image size while maintaining readability"""
        try:
            with Image.open(image_path) as img:
                # Calculate new size while maintaining aspect ratio
                max_dimension = 1200  # Reduced maximum dimension
                ratio = min(max_dimension / float(img.size[0]), 
                          max_dimension / float(img.size[1]))
                new_size = tuple(int(dim * ratio) for dim in img.size)
                
                # Resize image
                optimized = img.resize(new_size, Image.Resampling.LANCZOS)
                
                # Save with reduced quality
                temp_path = image_path.replace('.jpg', '_optimized.jpg')
                optimized.save(temp_path, 'JPEG', quality=50, optimize=True)
                return temp_path
        except Exception as e:
            frappe.log_error(f"Image optimization failed: {str(e)}", "Image Optimization Error")
            return image_path

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
            total_pages = len(pdf.pages)
            
            # Update the document with total pages as total records
            request.doc.total_records = total_pages
            request.doc.save(ignore_permissions=True)
            
            from concurrent.futures import ThreadPoolExecutor, as_completed
            from functools import partial
            
            def process_page(image_path, page_num, total):
                try:
                    # Update progress
                    request.doc.progress_count = f"Processing page {page_num} of {total}"
                    request.doc.save(ignore_permissions=True)
                    
                    # Optimize the image
                    optimized_path = self._optimize_image(image_path)
                    
                    # Quick check for empty page (you'd need to implement this)
                    if self._is_empty_page(optimized_path):
                        return None
                    
                    # Convert image to base64
                    with open(optimized_path, "rb") as img_file:
                        base64_image = base64.b64encode(img_file.read()).decode('utf-8')
                        return {
                            'page_number': page_num,
                            'base64_image': base64_image
                        }
                except Exception as e:
                    frappe.log_error(f"Page processing failed: {str(e)}", f"Page {page_num} Processing Error")
                    return None

            def _is_empty_page(self, image_path):
                """Quick check if page is empty or contains only totals"""
                try:
                    with Image.open(image_path) as img:
                        # Convert to grayscale
                        gray = img.convert('L')
                        
                        # Get histogram
                        hist = gray.histogram()
                        
                        # If mostly white pixels, likely empty
                        white_pixels = sum(hist[250:])  # Count very light pixels
                        total_pixels = sum(hist)
                        
                        if white_pixels / total_pixels > 0.95:  # 95% white
                            return True
                        
                        return False
                except Exception:
                    return False

            # Create temp directory for image conversion
            with tempfile.TemporaryDirectory() as temp_dir:
                # Convert PDF to images
                images = convert_from_path(
                    pdf_path,
                    dpi=150,
                    output_folder=temp_dir,
                    fmt="jpeg",
                    output_file="page",
                    paths_only=True,
                    poppler_path="/usr/bin"
                )
                
                # Process pages in parallel
                request.pages = []
                with ThreadPoolExecutor(max_workers=3) as executor:
                    # Create list of futures
                    future_to_page = {
                        executor.submit(
                            process_page, 
                            image_path, 
                            i, 
                            total_pages
                        ): i 
                        for i, image_path in enumerate(images, 1)
                    }
                    
                    # Process as they complete
                    for future in as_completed(future_to_page):
                        result = future.result()
                        if result:  # Only add non-empty pages
                            request.pages.append(result)
            
            if not request.pages:
                raise DocumentProcessingError("No valid pages were extracted from the PDF")
            
            return request
            
        except Exception as e:
            raise DocumentProcessingError(f"Failed to process PDF document: {str(e)}")

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