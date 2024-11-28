frappe.ui.form.on('Custom Workspace Configuration', {

    after_save: function(frm) {
        frappe.show_alert({
            message: 'Refreshing workspaces...',
            indicator: 'blue'
        });

        frm.call('refresh_workspaces')
            .then(r => {
                if (r.message && r.message.success) {
                    frappe.show_alert({
                        message: 'Workspaces refreshed successfully',
                        indicator: 'green'
                    });
                    
                    // Refresh the page after a short delay
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                } else {
                    frappe.throw({
                        title: 'Error',
                        message: r.message.message || 'Failed to refresh workspaces'
                    });
                }
            })
            .catch(err => {
                frappe.throw({
                    title: 'Error',
                    message: 'Failed to refresh workspaces: ' + err.message
                });
            });
    }
});

// Add client script for the child table to auto-set sequence numbers
frappe.ui.form.on('Workspace Content Item', {
    workspace_content_add: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        let items = frm.doc.workspace_content || [];
        row.sequence = items.length;  // 0-based indexing
        frm.refresh_field('workspace_content');
    }
});