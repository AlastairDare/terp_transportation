import frappe
from frappe.utils import cint
from .base_handler import BaseHandler
from ..utils.request import DocumentRequest
from ..utils.exceptions import DocumentProcessingError

class ResponseProcessingHandler(BaseHandler):
    def handle(self, request: DocumentRequest) -> DocumentRequest:
        try:
            if request.method == "process_toll":
                self._process_toll_records(request)
            else:
                self._update_documents(request)
            return super().handle(request)
        except Exception as e:
            request.set_error(e)
            self._handle_error(request)
            raise DocumentProcessingError(f"Response processing failed: {str(e)}")

    def _find_matching_truck_by_plate(self, license_plate: str) -> dict:
        """Find a Transportation Asset matching the given license plate"""
        try:
            matching_truck = frappe.get_list(
                "Transportation Asset",
                filters={
                    "license_plate": license_plate,
                    "transportation_asset_type": "Truck"
                },
                fields=["name", "license_plate"],
                limit=1
            )
            return matching_truck[0] if matching_truck else None
        except Exception as e:
            frappe.log_error(
                f"Error finding matching truck for plate {license_plate}: {str(e)}", 
                "Truck Matching Error"
            )
            return None

    # Keeping existing methods unchanged
    def _find_matching_truck(self, truck_number: str) -> dict:
        """Find a Transportation Asset matching the given truck number."""
        try:
            matching_truck = frappe.get_list(
                "Transportation Asset",
                filters={
                    "asset_number": truck_number,
                    "transportation_asset_type": "Truck"
                },
                fields=["name", "license_plate"],
                limit=1
            )
            return matching_truck[0] if matching_truck else None
        except Exception as e:
            frappe.log_error(
                f"Error finding matching truck for number {truck_number}: {str(e)}", 
                "Truck Matching Error"
            )
            return None

    def _rename_trip_doc(self, doc_name: str, license_plate: str) -> str:
        """Rename the trip document to include the license plate"""
        try:
            counter = doc_name.split('--')[-1]
            new_name = f"TRIP-{license_plate}-{counter}"
            frappe.rename_doc("Trip", doc_name, new_name, force=True)
            return new_name
        except Exception as e:
            frappe.log_error(
                f"Error renaming trip document {doc_name}: {str(e)}",
                "Trip Rename Error"
            )
            return doc_name

    def _update_documents(self, request: DocumentRequest):
        """Update ERPNext documents with AI response for delivery notes"""
        try:
            frappe.log_error(
                message=f"Starting response handler with AI response: {request.ai_response}",
                title="Response Handler Debug"
            )

            # Get the first transaction from the response
            if 'transactions' in request.ai_response:
                transaction_data = request.ai_response['transactions'][0]
            else:
                transaction_data = request.ai_response  # fallback to original format

            # Get trip document
            trip_doc = frappe.get_doc("Trip", request.trip_id)
            
            # Update trip fields from AI response
            field_mappings = {
                'date': 'date',
                'delivery_note_number': 'delivery_note_number',
                'odo_start': ('odo_start', lambda x: cint(x)),
                'odo_end': ('odo_end', lambda x: cint(x)),
                'time_start': 'time_start',
                'time_end': 'time_end'
            }

            # Handle truck number and Transportation Asset linking first
            if 'truck_number' in transaction_data:
                truck_number = transaction_data['truck_number']
                matching_truck = self._find_matching_truck(truck_number)
                
                if matching_truck:
                    trip_doc.truck = matching_truck.get('name')
                    new_name = self._rename_trip_doc(
                        trip_doc.name, 
                        matching_truck.get('license_plate')
                    )
                    trip_doc.name = new_name
                    request.trip_id = new_name
                else:
                    trip_doc.truck = None
                    frappe.log_error(
                        f"No matching Transportation Asset found for truck number: {truck_number}",
                        "Missing Transportation Asset"
                    )

            # Handle other fields
            for api_field, mapping in field_mappings.items():
                if api_field in transaction_data:
                    value = transaction_data[api_field]
                    if isinstance(mapping, tuple):
                        doc_field, transform_func = mapping
                        value = transform_func(value)
                    else:
                        doc_field = mapping
                    trip_doc.set(doc_field, value)

            # Handle odometer readings
            trip_doc.drop_details_odo = []
            if 'drop_details_odo' in transaction_data:
                for odo_reading in transaction_data['drop_details_odo']:
                    trip_doc.append('drop_details_odo', {
                        'odometer_reading': cint(odo_reading),
                        'parent_trip': trip_doc.name
                    })

            # Update status and save
            trip_doc.status = 'Awaiting Approval'
            trip_doc.save(ignore_permissions=True)

            # Update source document if needed
            if 'delivery_note_number' in transaction_data:
                request.doc.delivery_note_number = transaction_data['delivery_note_number']
                request.doc.save(ignore_permissions=True)

            frappe.db.commit()

            frappe.log_error(
                message="Response handler completed successfully",
                title="Response Handler Debug"
            )

        except Exception as e:
            frappe.log_error(
                message=f"Failed to update documents: {str(e)}",
                title="Response Handler Error"
            )
            raise DocumentProcessingError(f"Failed to update documents: {str(e)}")

    def _handle_error(self, request: DocumentRequest):
        """Handle errors in document processing"""
        try:
            if hasattr(request, 'trip_id') and request.trip_id:
                trip_doc = frappe.get_doc("Trip", request.trip_id)
                trip_doc.status = "Error"
                trip_doc.save(ignore_permissions=True)
            elif request.method == "process_toll":
                request.doc.processing_status = "Failed"
                request.doc.save(ignore_permissions=True)
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(f"Error Handler Failed: {str(e)}", "Error Handler Failure")