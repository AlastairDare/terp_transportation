frappe.ui.form.on('Vehicle', {
    refresh: function(frm) {
        console.log('Vehicle form refreshed');
        // Set up initial state for all dependent fields
        updateFieldVisibility(frm, 'certificate_of_roadworthiness', 'certificate_of_roadworthiness_expiration');
        updateFieldVisibility(frm, 'cross_border_road_transport_permit', 'cross_border_road_transport_permit_expiration');
        updateFieldVisibility(frm, 'warranty', 'warranty_expiration');
        updateLicensePlateFields(frm);
    },
    
    setup: function(frm) {
        console.log('Vehicle form setup');
        frm.set_query('primary_trailer', function() {
            return {
                filters: {
                    'status': 'Active'
                }
            };
        });
    },
    
    primary_trailer: function(frm) {
        console.log('Primary trailer changed:', frm.doc.primary_trailer);
        
        if (!frm.doc.primary_trailer) {
            console.log('Clearing secondary trailer');
            frm.set_value('secondary_trailer', '');
            frm.refresh_field('secondary_trailer');
            return;
        }
        
        console.log('Fetching trailer details');
        frappe.call({
            method: 'frappe.client.get',
            args: {
                doctype: 'Trailer',
                name: frm.doc.primary_trailer
            },
            callback: function(response) {
                console.log('Trailer response:', response);
                if (response.message && response.message.paired_trailer) {
                    console.log('Setting secondary trailer to:', response.message.paired_trailer);
                    frm.set_value('secondary_trailer', response.message.paired_trailer);
                } else {
                    console.log('No paired trailer found');
                    frm.set_value('secondary_trailer', '');
                }
                frm.refresh_field('secondary_trailer');
            }
        });
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