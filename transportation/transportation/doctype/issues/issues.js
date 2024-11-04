frappe.ui.form.on('Issues', {
    refresh: function(frm) {
        // Set query for asset field to include draft documents
        frm.set_query('asset', function() {
            return {
                doctype: 'Transportation Asset',  // Specify doctype here, not in filters
                filters: {
                    'docstatus': ['in', [0, 1]]  // Include both draft and submitted documents
                }
            };
        });
    },

    validate: function(frm) {
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
        if (frm.doc.issue_status !== 'Resolved') {
            frm.set_value('issue_resolution_date', '');
            frm.set_value('issue_resolution_notes', '');
            frm.set_value('issue_resolution_verified_by', '');
        }
    }
});