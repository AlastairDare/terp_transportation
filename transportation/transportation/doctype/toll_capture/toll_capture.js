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
    
    // Show a message that processing is starting
    frappe.show_alert({
        message: __('Starting document processing...'),
        indicator: 'blue'
    });
    
    frappe.call({
        method: 'transportation.transportation.doctype.toll_capture.toll_capture.process_toll_document',
        args: {
            doc_name: frm.doc.name
        },
        callback: function(r) {
            if (r.exc) {
                // If there's an error, show it
                frappe.msgprint({
                    title: __('Processing Error'),
                    message: r.exc,
                    indicator: 'red'
                });
            } else {
                // Success message
                frappe.show_alert({
                    message: __('Processing complete!'),
                    indicator: 'green'
                });
                frm.reload_doc();
            }
        }
    });
}