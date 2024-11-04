frappe.ui.form.on('Issues', {
    refresh: function(frm) {
        // Refresh triggers when form is loaded or refreshed
        frm.set_query('asset', function() {
            return {
                filters: {
                    'docstatus': 1  // Only show submitted Transportation Assets
                }
            };
        });
    },

    validate: function(frm) {
        // Validate if resolution details are filled when status is Resolved
        if (frm.doc.issue_status === 'Resolved') {
            if (!frm.doc.issue_resolution_date) {
                frappe.throw(__('Please fill in the Resolution Date'));
            }
            if (!frm.doc.issue_resolution_notes) {
                frappe.throw(__('Please fill in the Resolution Notes'));
            }
            if (!frm.doc.issue_resolution_verified_by) {
                frappe.throw(__('Please select who verified the resolution'));
            }
        }
    },

    issue_status: function(frm) {
        // Clear resolution fields if status is changed from Resolved
        if (frm.doc.issue_status !== 'Resolved') {
            frm.set_value('issue_resolution_date', '');
            frm.set_value('issue_resolution_notes', '');
            frm.set_value('issue_resolution_verified_by', '');
        }
    }
});