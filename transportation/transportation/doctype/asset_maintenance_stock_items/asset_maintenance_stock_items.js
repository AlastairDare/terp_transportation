frappe.ui.form.on('Asset Maintenance Stock Item', {
    qty: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        calculate_amount(row);
        frappe.model.set_value(cdt, cdn, 'amount', row.amount);
    },
    
    rate: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        calculate_amount(row);
        frappe.model.set_value(cdt, cdn, 'amount', row.amount);
    }
});

function calculate_amount(row) {
    row.amount = flt(row.qty) * flt(row.rate);
}