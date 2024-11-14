frappe.ui.form.on('Toll Capture', {
    refresh: function(frm) {
        if (frm.doc.processing_status !== 'Processing') {
            frm.add_custom_button(__('Process Toll Document'), function() {
                process_toll_document(frm);
            }).addClass('btn-primary');
        }
    }
});

function process_toll_document(frm) {
    if (!frm.doc.toll_document) {
        frappe.msgprint({
            title: __('Missing Document'),
            message: __('Please attach a Toll document first'),
            indicator: 'red'
        });
        return;
    }
    
    frappe.confirm(
        __('Are you sure you want to process this document?'),
        function() {
            frappe.call({
                method: 'transportation.transportation.doctype.toll_capture.toll_capture.process_toll_document_handler',
                args: {
                    doc_name: frm.doc.name
                },
                callback: function(r) {
                    if (r.exc) {
                        frappe.msgprint({
                            title: __('Processing Error'),
                            message: __('Error processing document: ') + r.exc,
                            indicator: 'red'
                        });
                    } else {
                        frm.reload_doc();
                        frappe.msgprint({
                            title: __('Processing Complete'),
                            message: __(`${r.message.page_count} pages optimized and saved to Toll Page Result`),
                            indicator: 'green'
                        });
                    }
                }
            });
        }
    );
}