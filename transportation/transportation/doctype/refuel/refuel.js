frappe.ui.form.on('Refuel', {
    refresh: function(frm) {
        // Update section label based on refuel type
        frm.set_df_property('external_internal_details_section', 'label',
            frm.doc.refuel_type === 'Internal Refuel' ? 'Internal Refuel Details' : 'External Refuel Details'
        );
        
        // Set read-only state for total_fuel_cost based on refuel type
        if (frm.doc.refuel_type === 'Internal Refuel') {
            frm.set_df_property('total_fuel_cost', 'read_only', 1);
        } else {
            // For external refuel, make read-only only if both fuel_amount and fuel_rate are set
            frm.set_df_property('total_fuel_cost', 'read_only',
                (frm.doc.fuel_amount && frm.doc.fuel_rate) ? 1 : 0
            );
        }
    },

    refuel_type: function(frm) {
        // Update section label when refuel type changes
        frm.set_df_property('external_internal_details_section', 'label',
            frm.doc.refuel_type === 'Internal Refuel' ? 'Internal Refuel Details' : 'External Refuel Details'
        );
        
        // Clear fields when switching between internal and external
        if (frm.doc.refuel_type === 'Internal Refuel') {
            frm.set_value('fuel_amount', '');
            frm.set_value('fuel_rate', '');
        } else {
            frm.set_value('material_issue', '');
        }
        
        // Reset total fuel cost
        frm.set_value('total_fuel_cost', '');
    },

    fuel_amount: function(frm) {
        calculate_total_fuel_cost(frm);
    },

    fuel_rate: function(frm) {
        calculate_total_fuel_cost(frm);
    }
});

function calculate_total_fuel_cost(frm) {
    if (frm.doc.refuel_type === 'External Refuel' && frm.doc.fuel_amount && frm.doc.fuel_rate) {
        frm.set_value('total_fuel_cost', frm.doc.fuel_amount * frm.doc.fuel_rate);
        frm.set_df_property('total_fuel_cost', 'read_only', 1);
    } else if (frm.doc.refuel_type === 'External Refuel') {
        frm.set_df_property('total_fuel_cost', 'read_only', 0);
    }
}