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
                    freeze_message: __('Extracting and creating Tolls...'),
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

        // Listen for status updates
        frappe.realtime.on('toll_capture_status', function(data) {
            if (data.type === 'freeze') {
                frappe.freeze(data.message);
            } else if (data.type === 'alert') {
                frappe.show_alert({
                    message: data.message,
                    indicator: data.indicator
                }, 5);
            }
        });
    },
    
    onload: function(frm) {
        // Clean up realtime listeners when form is unloaded
        frm.on('unload', function() {
            frappe.realtime.off('toll_capture_status');
        });
    }
});