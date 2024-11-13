import frappe
from frappe.utils.background_jobs import enqueue, get_jobs
from frappe.utils import get_files_path, now
import os
import base64
import tempfile
from PIL import Image
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
import json
import traceback
import psutil
import redis

def log_system_status():
    """Log system resource usage"""
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    status = {
        'memory_used_percent': memory.percent,
        'memory_available_gb': memory.available / (1024 ** 3),
        'disk_used_percent': disk.percent,
        'disk_free_gb': disk.free / (1024 ** 3)
    }
    frappe.logger("toll_capture").info(f"System Status: {json.dumps(status)}")

def check_redis_connection():
    """Verify Redis connection and log queue status"""
    try:
        redis_client = redis.from_url(frappe.conf.get("redis_queue") or "redis://localhost:6379")
        redis_info = redis_client.info()
        queue_keys = redis_client.keys('*toll_processing*')
        
        status = {
            'connected': True,
            'version': redis_info.get('redis_version'),
            'used_memory_human': redis_info.get('used_memory_human'),
            'connected_clients': redis_info.get('connected_clients'),
            'queue_keys': [key.decode('utf-8') for key in queue_keys]
        }
        frappe.logger("toll_capture").info(f"Redis Status: {json.dumps(status)}")
        return status
    except Exception as e:
        error = {'connected': False, 'error': str(e)}
        frappe.logger("toll_capture").error(f"Redis Connection Error: {json.dumps(error)}")
        return error

def verify_file_access(file_path: str) -> dict:
    """Verify file exists and is accessible"""
    status = {
        'exists': os.path.exists(file_path),
        'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
        'permissions': oct(os.stat(file_path).st_mode)[-3:] if os.path.exists(file_path) else None,
        'owner': os.stat(file_path).st_uid if os.path.exists(file_path) else None
    }
    frappe.logger("toll_capture").info(f"File Status for {file_path}: {json.dumps(status)}")
    return status

def optimize_image(image_path: str) -> str:
    """Optimize image size while maintaining readability"""
    frappe.logger("toll_capture").info(f"Starting image optimization for: {image_path}")
    try:
        with Image.open(image_path) as img:
            original_size = os.path.getsize(image_path)
            img_info = {
                'original_format': img.format,
                'original_mode': img.mode,
                'original_size': img.size,
                'file_size_mb': original_size / (1024 * 1024)
            }
            frappe.logger("toll_capture").info(f"Original image info: {json.dumps(img_info)}")

            max_dimension = 1200
            ratio = min(max_dimension / float(img.size[0]), max_dimension / float(img.size[1]))
            new_size = tuple(int(dim * ratio) for dim in img.size)
            
            optimized = img.resize(new_size, Image.Resampling.LANCZOS)
            temp_path = image_path.replace('.jpg', '_optimized.jpg')
            optimized.save(temp_path, 'JPEG', quality=50, optimize=True)
            
            final_size = os.path.getsize(temp_path)
            result = {
                'original_size_mb': original_size / (1024 * 1024),
                'final_size_mb': final_size / (1024 * 1024),
                'reduction_percent': ((original_size - final_size) / original_size) * 100
            }
            frappe.logger("toll_capture").info(f"Image optimization results: {json.dumps(result)}")
            return temp_path
    except Exception as e:
        error_info = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'image_path': image_path
        }
        frappe.logger("toll_capture").error(f"Image optimization failed: {json.dumps(error_info)}")
        return image_path

@frappe.whitelist()
def update_toll_progress(doc_name: str, total_pages: int, retry_count=0):
    """Update toll document progress with concurrency handling"""
    start_time = now()
    frappe.logger("toll_capture").info(f"Starting progress update for {doc_name} (retry: {retry_count})")
    
    if retry_count > 3:
        frappe.logger("toll_capture").error(f"Max retries reached for {doc_name}")
        return
        
    try:
        doc = frappe.get_doc("Toll Capture", doc_name)
        completed_pages = frappe.db.count(
            "Toll Page Result",
            {"parent_document": doc_name, "status": "Completed"}
        )
        
        status_info = {
            'doc_name': doc_name,
            'total_pages': total_pages,
            'completed_pages': completed_pages,
            'current_status': doc.status
        }
        frappe.logger("toll_capture").info(f"Progress status: {json.dumps(status_info)}")
        
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
        doc.save(ignore_permissions=True, ignore_version=True)
        
        end_time = now()
        duration = frappe.utils.time_diff_in_seconds(end_time, start_time)
        frappe.logger("toll_capture").info(f"Progress update completed in {duration}s")
        
    except frappe.TimestampMismatchError:
        frappe.logger("toll_capture").warning(f"Timestamp mismatch for {doc_name}, retrying...")
        import time
        time.sleep(1)
        update_toll_progress(doc_name, total_pages, retry_count + 1)
    except Exception as e:
        error_info = {
            'doc_name': doc_name,
            'error': str(e),
            'traceback': traceback.format_exc()
        }
        frappe.logger("toll_capture").error(f"Progress update error: {json.dumps(error_info)}")

@frappe.whitelist()
def process_toll_page(doc_name: str, page_num: int, total_pages: int, pdf_path: str):
    """Process a single toll document page"""
    start_time = now()
    frappe.logger("toll_capture").info(f"Starting page processing: Doc={doc_name}, Page={page_num}")
    log_system_status()
    
    try:
        # Verify PDF file access
        pdf_status = verify_file_access(pdf_path)
        if not pdf_status['exists']:
            raise Exception(f"PDF file not found or inaccessible: {pdf_path}")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_status = {
                'path': temp_dir,
                'free_space_gb': psutil.disk_usage(temp_dir).free / (1024 ** 3)
            }
            frappe.logger("toll_capture").info(f"Temporary directory created: {json.dumps(temp_dir_status)}")
            
            # Convert PDF to image
            frappe.logger("toll_capture").info(f"Converting PDF page {page_num} to image...")
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
                raise Exception(f"PDF conversion failed for page {page_num}")
            
            conversion_status = {
                'page': page_num,
                'output_files': images,
                'file_exists': all(os.path.exists(p) for p in images)
            }
            frappe.logger("toll_capture").info(f"PDF conversion status: {json.dumps(conversion_status)}")
            
            # Optimize image
            optimized_path = optimize_image(images[0])
            
            # Create base64 image
            with open(optimized_path, "rb") as img_file:
                base64_image = base64.b64encode(img_file.read()).decode('utf-8')
                image_info = {
                    'file_size_mb': os.path.getsize(optimized_path) / (1024 * 1024),
                    'base64_length': len(base64_image)
                }
                frappe.logger("toll_capture").info(f"Image processing complete: {json.dumps(image_info)}")
            
            # Save result
            result_doc = frappe.get_doc({
                "doctype": "Toll Page Result",
                "parent_document": doc_name,
                "page_number": page_num,
                "base64_image": base64_image,
                "status": "Completed"
            })
            result_doc.insert(ignore_permissions=True)
            
            update_toll_progress(doc_name, total_pages)
            
            end_time = now()
            duration = frappe.utils.time_diff_in_seconds(end_time, start_time)
            frappe.logger("toll_capture").info(f"Page {page_num} processing completed in {duration}s")
            
    except Exception as e:
        error_info = {
            'doc_name': doc_name,
            'page_num': page_num,
            'error': str(e),
            'traceback': traceback.format_exc()
        }
        frappe.logger("toll_capture").error(f"Page processing error: {json.dumps(error_info)}")
        
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
        """Main handler - using function reference for enqueue"""
        start_time = now()
        frappe.logger("toll_capture").info(f"Starting document preparation: {request.doc.name}")
        
        try:
            if request.method == "process_toll":
                # Check Redis connection
                redis_status = check_redis_connection()
                if not redis_status['connected']:
                    raise Exception(f"Redis connection failed: {redis_status['error']}")
                
                # Get PDF info
                pdf_path = get_files_path() + '/' + request.doc.toll_document.lstrip('/files/')
                pdf_status = verify_file_access(pdf_path)
                if not pdf_status['exists']:
                    raise Exception(f"PDF file not found: {pdf_path}")
                
                pdf = PdfReader(pdf_path)
                total_pages = len(pdf.pages)
                
                doc_info = {
                    'doc_name': request.doc.name,
                    'total_pages': total_pages,
                    'pdf_path': pdf_path,
                    'pdf_size_mb': pdf_status['size'] / (1024 * 1024)
                }
                frappe.logger("toll_capture").info(f"Document info: {json.dumps(doc_info)}")
                
                # Update document status
                request.doc.total_records = total_pages
                request.doc.status = "Processing"
                request.doc.progress_count = "0"
                request.doc.save(ignore_permissions=True)
                
                # Queue jobs
                queued_jobs = []
                for page_num in range(1, total_pages + 1):
                    job_name = f'toll_processing_{request.doc.name}_page_{page_num}'
                    
                    try:
                        job = enqueue(
                            process_toll_page,
                            queue='long',
                            timeout=180,
                            job_name=job_name,
                            doc_name=request.doc.name,
                            page_num=page_num,
                            total_pages=total_pages,
                            pdf_path=pdf_path
                        )
                        
                        job_info = {
                            'job_name': job_name,
                            'queue': 'long',
                            'status': 'queued' if job else 'failed'
                        }
                        queued_jobs.append(job_info)
                        frappe.logger("toll_capture").info(f"Job queued: {json.dumps(job_info)}")
                        
                    except Exception as e:
                        error_info = {
                            'job_name': job_name,
                            'error': str(e),
                            'traceback': traceback.format_exc()
                        }
                        frappe.logger("toll_capture").error(f"Job queueing failed: {json.dumps(error_info)}")
                        raise
                
                # Final status check
                end_time = now()
                duration = frappe.utils.time_diff_in_seconds(end_time, start_time)
                final_status = {
                    'total_jobs': len(queued_jobs),
                    'queue_status': check_redis_connection(),
                    'duration_seconds': duration
                }
                frappe.logger("toll_capture").info(f"Document preparation complete: {json.dumps(final_status)}")
                
                return request
                
            else:
                return super().handle(request)
            
        except Exception as e:
            error_info = {
                'doc_name': request.doc.name,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
            frappe.logger("toll_capture").error(f"Document preparation failed: {json.dumps(error_info)}")
            request.set_error(e)
            raise DocumentProcessingError(f"Document preparation failed: {str(e)}")