# transportation/ai_processing/handlers/document_handler.py

import os
import base64
import frappe
from frappe.utils import get_files_path
from .base_handler import BaseHandler
from ..utils.request import DocumentRequest
from ..utils.exceptions import DocumentProcessingError

class DocumentPreparationHandler(BaseHandler):
    def handle(self, request: DocumentRequest) -> DocumentRequest:
        try:
            # Validate image exists in the document
            if not request.doc.delivery_note_image:
                raise DocumentProcessingError("Delivery Note Image is required")

            # Get the original image path directly
            original_image_path = get_files_path() + '/' + request.doc.delivery_note_image.lstrip('/files/')
            if not os.path.exists(original_image_path):
                raise DocumentProcessingError("Delivery Note Image file not found")

            # Convert original image to base64 directly
            with open(original_image_path, "rb") as image_file:
                request.base64_image = base64.b64encode(image_file.read()).decode('utf-8')

            # Create initial trip document
            trip_doc = self._create_initial_trip(request.doc)
            request.trip_id = trip_doc.name

            return super().handle(request)

        except Exception as e:
            request.set_error(e)
            raise DocumentProcessingError(f"Document preparation failed: {str(e)}")

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