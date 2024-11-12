frappe.ui.form.on('Toll Capture', {
    refresh: function(frm) {
        frm.add_custom_button(__('Process Toll Document'), function() {
            if (!frm.doc.toll_document) {
                frappe.throw(__('Please attach a Toll document first'));
                return;
            }
            
            let file_url = frm.doc.toll_document;
            if (!file_url.toLowerCase().endsWith('.pdf')) {
                frappe.throw(__('Please upload a PDF document'));
                return;
            }
            
            let dialog = frappe.show_progress('Processing Toll Document', 0, 100, 'Please wait...');
            
            frappe.call({
                method: 'transportation.transportation.doctype.toll_capture.toll_capture.process_toll_document',
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
    }
});