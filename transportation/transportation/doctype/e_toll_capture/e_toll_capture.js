frappe.ui.form.on('E-Toll Capture', {
    refresh: function(frm) {
        // Add Process Document button
        frm.add_custom_button(__('Process E-Toll Document'), function() {
            if (!frm.doc.toll_document) {
                frappe.throw(__('Please attach an E-Toll document first'));
                return;
            }
            
            // Validate file type
            let file_url = frm.doc.toll_document;
            if (!file_url.toLowerCase().endsWith('.pdf')) {
                frappe.throw(__('Please upload a PDF document'));
                return;
            }
            
            // Create progress dialog
            let dialog = frappe.show_progress('Processing E-Toll Document', 0, 100, 'Please wait...');
            
            // Call process method
            frappe.call({
                method: 'transportation.transportation.doctype.e_toll_capture.e_toll_capture.process_etoll_document',
                args: {
                    doc_name: frm.doc.name
                },
                callback: function(r) {
                    dialog.hide();
                    frm.reload_doc();
                    frappe.show_alert({
                        message: __('Document processing complete'),
                        indicator: 'green'
                    });
                },
                error: function(r) {
                    dialog.hide();
                    frappe.throw(__('Error processing document'));
                }
            });
        });
    },
    
    // Update form when processing status changes
    processing_status: function(frm) {
        frm.reload_doc();
    }
});