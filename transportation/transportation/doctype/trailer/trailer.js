frappe.ui.form.on('Trailer', {
    refresh: function(frm) {
        // Set up initial state for all dependent fields
        updateFieldVisibility(frm, 'certificate_of_roadworthiness', 'certificate_of_roadworthiness_expiration');
        updateFieldVisibility(frm, 'cross_border_road_transport_permit', 'cross_border_road_transport_permit_expiration');
        updateFieldVisibility(frm, 'warranty', 'warranty_expiration');
        updateLicensePlateFields(frm);
    },

    // Handle Certificate of Roadworthiness changes
    certificate_of_roadworthiness: function(frm) {
        updateFieldVisibility(frm, 'certificate_of_roadworthiness', 'certificate_of_roadworthiness_expiration');
    },

    // Handle Cross Border Permit changes
    cross_border_road_transport_permit: function(frm) {
        updateFieldVisibility(frm, 'cross_border_road_transport_permit', 'cross_border_road_transport_permit_expiration');
    },

    // Handle Warranty changes
    warranty: function(frm) {
        updateFieldVisibility(frm, 'warranty', 'warranty_expiration');
    },

    // Handle License Plate changes
    license_plate: function(frm) {
        updateLicensePlateFields(frm);
    }
});

// Helper function to update field visibility and read-only state
function updateFieldVisibility(frm, checkboxField, dateField) {
    if (!frm.doc[checkboxField]) {
        // If checkbox is unchecked, clear and disable the date field
        frm.set_value(dateField, '');
        frm.set_df_property(dateField, 'read_only', 1);
        frm.set_df_property(dateField, 'reqd', 0);
    } else {
        // If checkbox is checked, enable the date field
        frm.set_df_property(dateField, 'read_only', 0);
        frm.set_df_property(dateField, 'reqd', 1);
    }
    frm.refresh_field(dateField);
}

// Helper function specifically for license plate related fields
function updateLicensePlateFields(frm) {
    if (!frm.doc.license_plate) {
        // If license plate is empty, clear and disable registration expiry
        frm.set_value('registration_expiry', '');
        frm.set_df_property('registration_expiry', 'read_only', 1);
        frm.set_df_property('registration_expiry', 'reqd', 0);
    } else {
        // If license plate has a value, enable registration expiry
        frm.set_df_property('registration_expiry', 'read_only', 0);
        frm.set_df_property('registration_expiry', 'reqd', 1);
    }
    frm.refresh_field('registration_expiry');
}