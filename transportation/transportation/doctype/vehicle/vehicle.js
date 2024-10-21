frappe.ui.form.on('Vehicle', {
    refresh: function(frm) {
        frm.add_custom_button(__('Schedule Maintenance'), function() {
            // Logic to schedule maintenance
            frappe.msgprint('Maintenance scheduling feature to be implemented');
        });

        frm.add_custom_button(__('Update Mileage'), function() {
            frappe.prompt([
                {'fieldname': 'new_mileage', 'fieldtype': 'Float', 'label': 'New Mileage', 'reqd': 1}
            ],
            function(values){
                frm.set_value('current_mileage', values.new_mileage);
                frm.save();
            },
            __('Update Mileage'),
            __('Update')
            )
        });
    },

    validate: function(frm) {
        if (frm.doc.year && frm.doc.year > new Date().getFullYear()) {
            frappe.msgprint(__("Year cannot be in the future"));
            frappe.validated = false;
        }
    }
});