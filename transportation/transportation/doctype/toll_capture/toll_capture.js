frappe.ui.form.on('Toll Capture', {
    refresh: function(frm) {
        // Only show process button if document is not already processing
        if (frm.doc.processing_status !== 'Processing') {
            frm.add_custom_button(__('Process Toll Document'), function() {
                if (!frm.doc.toll_document) {
                    frappe.msgprint({
                        title: __('Missing Document'),
                        message: __('Please attach a Toll document first'),
                        indicator: 'red'
                    });
                    return;
                }
                
                if (!frm.doc.toll_document.toLowerCase().endsWith('.pdf')) {
                    frappe.msgprint({
                        title: __('Invalid Format'),
                        message: __('Please upload a PDF document'),
                        indicator: 'red'
                    });
                    return;
                }
                
                // Confirm before processing
                frappe.confirm(
                    __('Are you sure you want to process this document?'),
                    function() {
                        // Show progress dialog
                        let dialog = frappe.show_progress(__('Processing Toll Document'), 0, 100);
                        
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
                                frappe.msgprint({
                                    title: __('Processing Error'),
                                    message: __('Error processing document: ') + r.exc,
                                    indicator: 'red'
                                });
                            }
                        });
                    }
                );
            }).addClass('btn-primary');
        }
    }
});