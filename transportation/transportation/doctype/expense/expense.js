frappe.ui.form.on('Expense', {
    refresh: function(frm) {
        // Make all fields read-only as this is system generated
        frm.set_read_only(true);
    },
    
    expense_type: function(frm) {
        // Clear other reference fields when expense type changes
        if (frm.doc.expense_type === 'Toll') {
            frm.set_value('refuel_reference', '');
            frm.set_value('maintenance_reference', '');
        } else if (frm.doc.expense_type === 'Refuel') {
            frm.set_value('toll_reference', '');
            frm.set_value('maintenance_reference', '');
        } else if (frm.doc.expense_type === 'Unified Maintenance') {
            frm.set_value('toll_reference', '');
            frm.set_value('refuel_reference', '');
        }
    }
});