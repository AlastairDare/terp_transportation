frappe.ui.form.on('Issue', {
    refresh: function(frm) {
        // Set initial visibility of the maintenance job field
        updateMaintenanceJobVisibility(frm);
    },

    // Handle changes to the maintenance job field
    issue_assigned_to_maintenance_job: function(frm) {
        updateMaintenanceJobVisibility(frm);
    }
});

// Function to update the visibility of the maintenance job field
function updateMaintenanceJobVisibility(frm) {
    let maintenanceJobField = frm.doc.issue_assigned_to_maintenance_job;
    
    if (!maintenanceJobField) {
        // Hide the field if there's no value
        frm.set_df_property('issue_assigned_to_maintenance_job', 'hidden', 1);
    } else {
        // Show the field if there's a value
        frm.set_df_property('issue_assigned_to_maintenance_job', 'hidden', 0);
        // Ensure the field is read-only when visible
        frm.set_df_property('issue_assigned_to_maintenance_job', 'read_only', 1);
    }
    
    // Refresh the form to apply changes
    frm.refresh_field('issue_assigned_to_maintenance_job');
}