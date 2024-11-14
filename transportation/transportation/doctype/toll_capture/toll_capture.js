frappe.ui.form.on('Toll Capture', {
    refresh: function(frm) {
        if (frm.doc.docstatus < 2) {
            frm.add_custom_button(__('Process Toll Document'), function() {
                frappe.call({
                    method: 'transportation.transportation.doctype.toll_page_result.process_toll_page.process_toll_pages',
                    args: {
                        toll_capture_id: frm.doc.name
                    },
                    freeze: true,
                    freeze_message: __('Processing Toll Document...'),
                    callback: function(r) {
                        frappe.show_alert({
                            message: __('Toll document processed'),
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    }
                });
            });
        }
    }
});