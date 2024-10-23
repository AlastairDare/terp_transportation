frappe.ui.form.on('Trip Capture', {
    setup: function(frm) {
        // Set the form title
        frm.page.set_title('Trip Capture Form');
    },
    
    refresh: function(frm) {
        // Add the submit button - primary class makes it blue
        frm.add_custom_button('Submit Trip', function() {
            if (!frm.doc.trip_sheet_image || !frm.doc.delivery_note_image) {
                frappe.msgprint('Please upload both images before submitting');
                return;
            }
            
            frm.save()
                .then(() => {
                    frappe.msgprint({
                        title: 'Success',
                        indicator: 'green',
                        message: 'Trip submitted successfully!'
                    });
                })
                .catch((err) => {
                    frappe.msgprint({
                        title: 'Error',
                        indicator: 'red',
                        message: 'Error submitting trip: ' + err.message
                    });
                });
        }).addClass('btn-primary');
    }
});