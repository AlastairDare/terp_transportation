import frappe
from frappe.utils.background_jobs import enqueue
from frappe.utils import get_files_path
import os
import base64
import tempfile
from PIL import Image
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
from .base_handler import BaseHandler
from ..utils.request import DocumentRequest
from ..utils.exceptions import DocumentProcessingError

def optimize_image(image_path: str) -> str:
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

@frappe.whitelist()
def update_toll_progress(doc_name: str, total_pages: int, retry_count=0):
    """Update toll document progress with concurrency handling"""
    if retry_count > 3:
        frappe.logger("toll_capture").error(f"Max retries reached for {doc_name}")
        return
        
    try:
        doc = frappe.get_doc("Toll Capture", doc_name)
        
        completed_pages = frappe.db.count(
            "Toll Page Result",
            {
                "parent_document": doc_name,
                "status": "Completed"
            }
        )
        
        doc.progress_count = f"Processed {completed_pages} of {total_pages} pages"
        
        if completed_pages == total_pages:
            doc.status = "Completed"
            pages = frappe.get_all(
                "Toll Page Result",
                filters={"parent_document": doc_name, "status": "Completed"},
                fields=["page_number", "base64_image"],
                order_by="page_number"
            )
            doc.processed_pages = frappe.as_json([{
                'page_number': page.page_number,
                'base64_image': page.base64_image
            } for page in pages])
        
        doc.flags.ignore_version = True
        doc.save(
            ignore_permissions=True,
            ignore_version=True,
            ignore_if_duplicate=True
        )
        
    except frappe.TimestampMismatchError:
        import time
        time.sleep(1)
        update_toll_progress(doc_name, total_pages, retry_count + 1)
    except Exception as e:
        frappe.logger("toll_capture").error(f"Error updating progress: {str(e)}")

@frappe.whitelist()
def process_toll_page(doc_name: str, page_num: int, total_pages: int, pdf_path: str):
    """Process a single toll document page"""
    frappe.logger("toll_capture").info(f"=== Starting background processing of page {page_num} for {doc_name} ===")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Convert single page
            images = convert_from_path(
                pdf_path,
                dpi=150,
                output_folder=temp_dir,
                fmt="jpeg",
                first_page=page_num,
                last_page=page_num,
                output_file=f"page_{page_num}",
                paths_only=True,
                poppler_path="/usr/bin"
            )
            
            if not images:
                raise Exception(f"Failed to convert page {page_num}")
            
            # Optimize the image
            optimized_path = optimize_image(images[0])
            
            # Convert to base64
            with open(optimized_path, "rb") as img_file:
                base64_image = base64.b64encode(img_file.read()).decode('utf-8')
            
            # Save the page result
            frappe.get_doc({
                "doctype": "Toll Page Result",
                "parent_document": doc_name,
                "page_number": page_num,
                "base64_image": base64_image,
                "status": "Completed"
            }).insert(ignore_permissions=True)
            
            # Update progress
            update_toll_progress(doc_name, total_pages)
            
            frappe.logger("toll_capture").info(f"=== Completed processing page {page_num} for {doc_name} ===")
            
    except Exception as e:
        frappe.logger("toll_capture").error(f"Error processing page {page_num}: {str(e)}")
        # Save error state
        frappe.get_doc({
            "doctype": "Toll Page Result",
            "parent_document": doc_name,
            "page_number": page_num,
            "status": "Failed",
            "error_message": str(e)
        }).insert(ignore_permissions=True)
        raise

class DocumentPreparationHandler(BaseHandler):
    def handle(self, request: DocumentRequest) -> DocumentRequest:
        """Main handler - now queuing to module-level functions"""
        try:
            if request.method == "process_toll":
                frappe.logger("toll_capture").info("Starting toll document processing")
                
                # Get total pages first
                pdf_path = get_files_path() + '/' + request.doc.toll_document.lstrip('/files/')
                pdf = PdfReader(pdf_path)
                total_pages = len(pdf.pages)
                
                frappe.logger("toll_capture").info(f"Found {total_pages} pages to process")
                
                # Initialize document state
                request.doc.total_records = total_pages
                request.doc.status = "Processing"
                request.doc.progress_count = "0"
                request.doc.save(ignore_permissions=True)
                
                # Queue jobs for each page
                for page_num in range(1, total_pages + 1):
                    frappe.logger("toll_capture").info(f"Queueing job for page {page_num}")
                    
                    job_name = f'toll_processing_{request.doc.name}_page_{page_num}'
                    
                    # Queue to the module-level function
                    enqueue(
                        process_toll_page,
                        queue='long',
                        timeout=180,
                        job_name=job_name,
                        doc_name=request.doc.name,
                        page_num=page_num,
                        total_pages=total_pages,
                        pdf_path=pdf_path
                    )
                    
                    frappe.logger("toll_capture").info(f"Queued job: {job_name}")
                
                return request
                
            else:
                return super().handle(request)
            
        except Exception as e:
            frappe.logger("toll_capture").error(f"Error in handle method: {str(e)}")
            request.set_error(e)
            raise DocumentProcessingError(f"Document preparation failed: {str(e)}")

    # Keep the original delivery note methods unchanged
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