frappe.ui.form.on('Vehicle', {
    setup: function(frm) {
        frm.set_query('primary_trailer', function() {
            return {
                filters: {
                    'status': 'Active'
                }
            };
        });
    },
    
    primary_trailer: function(frm) {
        if (!frm.doc.primary_trailer) {
            frm.set_value('secondary_trailer', '');
            frm.refresh_field('secondary_trailer');
            return;
        }
        
        frappe.call({
            method: 'frappe.client.get',
            args: {
                doctype: 'Trailer',
                name: frm.doc.primary_trailer
            },
            callback: function(response) {
                if (response.message && response.message.paired_trailer) {
                    frm.set_value('secondary_trailer', response.message.paired_trailer);
                } else {
                    frm.set_value('secondary_trailer', '');
                }
                frm.refresh_field('secondary_trailer');
            }
        });
    }
});