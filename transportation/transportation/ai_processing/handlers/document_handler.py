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
        frappe.log_error(f"DEBUG: Starting image optimization for {image_path}", "Toll Debug")
        with Image.open(image_path) as img:
            max_dimension = 1200
            ratio = min(max_dimension / float(img.size[0]), 
                      max_dimension / float(img.size[1]))
            new_size = tuple(int(dim * ratio) for dim in img.size)
            
            frappe.log_error(f"DEBUG: Resizing image to {new_size}", "Toll Debug")
            optimized = img.resize(new_size, Image.Resampling.LANCZOS)
            temp_path = image_path.replace('.jpg', '_optimized.jpg')
            optimized.save(temp_path, 'JPEG', quality=50, optimize=True)
            
            frappe.log_error(f"DEBUG: Saved optimized image to {temp_path}", "Toll Debug")
            return temp_path
    except Exception as e:
        frappe.log_error(f"DEBUG: Image optimization failed: {str(e)}", "Toll Debug")
        return image_path

@frappe.whitelist()
def update_toll_progress(doc_name: str, total_pages: int, retry_count=0):
    """Update toll document progress with concurrency handling"""
    frappe.log_error(f"DEBUG: Updating progress for {doc_name}, retry {retry_count}", "Toll Debug")
    
    if retry_count > 3:
        frappe.log_error(f"DEBUG: Max retries reached for {doc_name}", "Toll Debug")
        return
        
    try:
        doc = frappe.get_doc("Toll Capture", doc_name)
        completed_pages = frappe.db.count(
            "Toll Page Result",
            {"parent_document": doc_name, "status": "Completed"}
        )
        
        frappe.log_error(f"DEBUG: Found {completed_pages} completed pages", "Toll Debug")
        
        doc.progress_count = f"Processed {completed_pages} of {total_pages} pages"
        
        if completed_pages == total_pages:
            frappe.log_error("DEBUG: All pages completed, updating final status", "Toll Debug")
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
        doc.save(ignore_permissions=True, ignore_version=True)
        frappe.log_error(f"DEBUG: Successfully updated document progress", "Toll Debug")
        
    except frappe.TimestampMismatchError:
        frappe.log_error(f"DEBUG: Timestamp mismatch, retrying after delay", "Toll Debug")
        import time
        time.sleep(1)
        update_toll_progress(doc_name, total_pages, retry_count + 1)
    except Exception as e:
        frappe.log_error(f"DEBUG: Error updating progress: {str(e)}", "Toll Debug")

@frappe.whitelist()
def process_toll_page(doc_name: str, page_num: int, total_pages: int, pdf_path: str):
    """Process a single toll document page with debug logging"""
    frappe.log_error(f"DEBUG: Starting process_toll_page for page {page_num}", "Toll Debug")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            frappe.log_error(f"DEBUG: Created temp directory for page {page_num}", "Toll Debug")
            
            frappe.log_error(f"DEBUG: Converting page {page_num} to image", "Toll Debug")
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
                frappe.log_error(f"DEBUG: No images generated for page {page_num}", "Toll Debug")
                raise Exception(f"Failed to convert page {page_num}")
            
            frappe.log_error(f"DEBUG: Successfully converted page {page_num}, optimizing...", "Toll Debug")
            optimized_path = optimize_image(images[0])
            
            frappe.log_error(f"DEBUG: Converting page {page_num} to base64", "Toll Debug")
            with open(optimized_path, "rb") as img_file:
                base64_image = base64.b64encode(img_file.read()).decode('utf-8')
            
            frappe.log_error(f"DEBUG: Creating Toll Page Result for page {page_num}", "Toll Debug")
            frappe.get_doc({
                "doctype": "Toll Page Result",
                "parent_document": doc_name,
                "page_number": page_num,
                "base64_image": base64_image,
                "status": "Completed"
            }).insert(ignore_permissions=True)
            
            frappe.log_error(f"DEBUG: Updating toll progress for page {page_num}", "Toll Debug")
            update_toll_progress(doc_name, total_pages)
            
            frappe.log_error(f"DEBUG: Completed processing page {page_num}", "Toll Debug")
            
    except Exception as e:
        frappe.log_error(f"DEBUG: Error processing page {page_num}: {str(e)}", "Toll Debug")
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
        """Main handler with extensive debug logging"""
        try:
            if request.method == "process_toll":
                frappe.log_error("DEBUG: Starting toll document processing", "Toll Debug")
                
                pdf_path = get_files_path() + '/' + request.doc.toll_document.lstrip('/files/')
                frappe.log_error(f"DEBUG: PDF Path: {pdf_path}", "Toll Debug")
                
                pdf = PdfReader(pdf_path)
                total_pages = len(pdf.pages)
                frappe.log_error(f"DEBUG: Total pages: {total_pages}", "Toll Debug")
                
                request.doc.total_records = total_pages
                request.doc.status = "Processing"
                request.doc.progress_count = "0"
                request.doc.save(ignore_permissions=True)
                
                # Check redis connection
                try:
                    from rq import Queue
                    from frappe.utils.background_jobs import get_redis_conn
                    redis_conn = get_redis_conn()
                    frappe.log_error("DEBUG: Successfully connected to Redis", "Toll Debug")
                except Exception as e:
                    frappe.log_error(f"DEBUG: Redis connection error: {str(e)}", "Toll Debug")
                    raise
                
                # Queue jobs with explicit debug info
                for page_num in range(1, total_pages + 1):
                    job_name = f'toll_processing_{request.doc.name}_page_{page_num}'
                    frappe.log_error(f"DEBUG: About to queue job: {job_name}", "Toll Debug")
                    
                    try:
                        frappe.log_error(f"DEBUG: Inside enqueue try block for page {page_num}", "Toll Debug")
                        
                        # Force asynchronous execution
                        enqueue(
                            method=process_toll_page,
                            queue='long',
                            timeout=180,
                            job_name=job_name,
                            doc_name=request.doc.name,
                            page_num=page_num,
                            total_pages=total_pages,
                            pdf_path=pdf_path,
                            is_async=True,
                            now=False
                        )
                        
                        frappe.log_error(f"DEBUG: Successfully queued job: {job_name}", "Toll Debug")
                        
                        # Verify job was queued
                        q = Queue('long', connection=redis_conn)
                        job = q.fetch_job(job_name)
                        
                        if job:
                            frappe.log_error(f"DEBUG: Verified job in queue: {job_name}, Status: {job.get_status()}", "Toll Debug")
                        else:
                            frappe.log_error(f"DEBUG: Job not found in queue after enqueue: {job_name}", "Toll Debug")
                            
                    except Exception as e:
                        frappe.log_error(f"DEBUG: Failed to queue job {job_name}: {str(e)}", "Toll Debug")
                        raise
                
                frappe.log_error(f"DEBUG: Completed queueing {total_pages} jobs", "Toll Debug")
                return request
                
            else:
                return super().handle(request)
                
        except Exception as e:
            frappe.log_error(f"DEBUG: Error in handle method: {str(e)}", "Toll Debug")
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