frappe.ui.form.on('Toll Capture', {
    refresh: function(frm) {
        // Only show process button if document is not processing
        if (frm.doc.processing_status !== 'Processing') {
            frm.add_custom_button(__('Process Toll Document'), function() {
                process_toll_document(frm);
            }).addClass('btn-primary');
        }
    }
});

function process_toll_document(frm) {
    // Validate document attachment
    if (!frm.doc.toll_document) {
        frappe.msgprint({
            title: __('Missing Document'),
            message: __('Please attach a Toll document first'),
            indicator: 'red'
        });
        return;
    }
    
    // Confirm processing
    frappe.confirm(
        __('Are you sure you want to process this document?'),
        function() {
            // Show processing dialog
            let dialog = create_processing_dialog();
            
            // Call server method
            frappe.call({
                method: 'transportation.transportation.doctype.toll_capture.toll_capture.process_toll_document_handler',
                args: {
                    doc_name: frm.doc.name
                },
                callback: function(r) {
                    dialog.hide();
                    if (r.exc) {
                        // Error handling
                        show_error_message(r.exc);
                    } else {
                        // Refresh and show success message
                        frm.reload_doc();
                        show_success_message(r.message);
                    }
                },
                error: function(r) {
                    dialog.hide();
                    show_error_message(r.message);
                }
            });
        }
    );
}

function create_processing_dialog() {
    let dialog = new frappe.ui.Dialog({
        title: __('Processing Toll Document'),
        fields: [{
            fieldname: 'status_html',
            fieldtype: 'HTML',
            options: `
                <div class="progress">
                    <div class="progress-bar progress-bar-striped active" 
                        role="progressbar" style="width: 100%">
                    </div>
                </div>
                <p class="text-muted text-center">Processing document, please wait...</p>
            `
        }]
    });
    dialog.show();
    return dialog;
}

function show_success_message(result) {
    let message = `
        Processing complete<br>
        Total Records: ${result.total_records || 0}<br>
        New Records: ${result.new_records || 0}<br>
        Duplicates: ${result.duplicate_records || 0}
    `;
    
    frappe.msgprint({
        title: __('Processing Complete'),
        message: message,
        indicator: 'green'
    });
}

function show_error_message(error) {
    frappe.msgprint({
        title: __('Processing Error'),
        message: __('Error processing document: ') + error,
        indicator: 'red'
    });
}