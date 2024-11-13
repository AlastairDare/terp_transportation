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
                
                // Confirm before processing
                frappe.confirm(
                    __('Are you sure you want to process this document?'),
                    function() {
                        // Show progress dialog
                        let d = new frappe.ui.Dialog({
                            title: __('Processing Toll Document'),
                            fields: [
                                {
                                    fieldname: 'status_html',
                                    fieldtype: 'HTML',
                                    options: `<div class="progress">
                                        <div class="progress-bar progress-bar-striped active"
                                            role="progressbar" style="width: 100%">
                                        </div>
                                    </div>
                                    <p class="text-muted text-center">Processing document, please wait...</p>`
                                }
                            ]
                        });
                        d.show();
                        
                        frappe.call({
                            method: 'transportation.transportation.doctype.toll_capture.toll_capture.process_toll_document',
                            args: {
                                doc_name: frm.doc.name
                            },
                            callback: function(r) {
                                d.hide();
                                frm.reload_doc();
                                
                                // Show results
                                let message = `Processing complete<br>
                                    Total Records: ${frm.doc.total_records || 0}<br>
                                    New Records: ${frm.doc.new_records || 0}<br>
                                    Duplicates: ${frm.doc.duplicate_records || 0}`;
                                
                                frappe.msgprint({
                                    title: __('Processing Complete'),
                                    message: message,
                                    indicator: 'green'
                                });
                            },
                            error: function(r) {
                                d.hide();
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