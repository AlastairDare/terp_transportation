frappe.ui.form.on('Trip Capture', {
    refresh: function(frm) {
        // You can add custom buttons or functionality here
        frm.add_custom_button(__('Save Trip'), function() {
            // Add your save logic here
            frappe.msgprint('Trip Saved!');
        });
    }
});