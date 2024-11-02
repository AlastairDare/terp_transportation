frappe.ui.form.on('Vehicle', {
    refresh: function(frm) {
        console.log('Vehicle form refreshed');
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
    }
});