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
            frm.set_df_property('total_fuel_cost', 'read_only',
                (frm.doc.fuel_amount && frm.doc.fuel_rate) ? 1 : 0
            );
        }
    },

    onload: function(frm) {
        // Set query for transportation asset - removed is_active filter
        frm.set_query('transportation_asset', function() {
            return {
                filters: {
                    'docstatus': 1  // Only show submitted transportation assets
                }
            };
        });
    },

    transportation_asset: function(frm) {
        if (frm.doc.transportation_asset) {
            frappe.call({
                method: 'frappe.client.get_value',
                args: {
                    doctype: 'Transportation Asset',
                    filters: { name: frm.doc.transportation_asset },
                    fieldname: 'fuel_type'
                },
                callback: function(r) {
                    if (r.message && r.message.fuel_type) {
                        frm.set_value('fuel_type', r.message.fuel_type);
                    }
                }
            });
        }
    },

    material_issue: function(frm) {
        if (frm.doc.material_issue) {
            frappe.call({
                method: 'transportation.transportation.doctype.refuel.refuel.get_material_issue_cost',
                args: {
                    'material_issue': frm.doc.material_issue
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('total_fuel_cost', r.message);
                    }
                }
            });
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

    before_save: function(frm) {
        if (frm.doc.refuel_status === "Draft") {
            frappe.show_alert({
                message: __("Change status to 'Complete' to create an Expense log for this Refuel Event"),
                indicator: 'blue'
            });
        }
    },

    after_save: function(frm) {
        if (frm.doc.refuel_status === "Complete" && frm.doc.expense_link) {
            let message = `
                <div>
                    <p>${__('Expense logged with ID: ')}${frm.doc.expense_link}</p>
                    <button class="btn btn-xs btn-default" 
                            onclick="frappe.utils.copy_to_clipboard('${frm.doc.expense_link}').then(() => {
                                frappe.show_alert({
                                    message: '${__('Expense ID copied to clipboard')}',
                                    indicator: 'green'
                                });
                            })">
                        ${__('Copy Expense ID')}
                    </button>
                </div>
            `;
            
            frappe.msgprint({
                message: message,
                title: __("Expense Created"),
                indicator: "green"
            });
        }
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