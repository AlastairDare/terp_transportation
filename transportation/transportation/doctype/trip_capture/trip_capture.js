frappe.ui.form.on('Trip Capture', {
    refresh: function(frm) {
        // Only show save button if status is Draft
        if(frm.doc.status === 'Draft') {
            frm.add_custom_button(__('Save Trip'), function() {
                validateAndSaveTrip(frm);
            }).addClass('btn-primary');
        }
    },
    
    before_save: function(frm) {
        // Validate required fields before saving
        if (!frm.doc.trip_sheet_image || !frm.doc.delivery_note_image) {
            frappe.throw(__('Both Trip Sheet and Delivery Note images are required'));
            return false;
        }
    }
});

function validateAndSaveTrip(frm) {
    // Check if both images are uploaded
    if (!frm.doc.trip_sheet_image || !frm.doc.delivery_note_image) {
        frappe.msgprint(__('Please upload both Trip Sheet and Delivery Note images before saving'));
        return;
    }

    // Set status to Submitted
    frm.set_value('status', 'Submitted');
    
    // Save the form
    frm.save()
        .then(() => {
            frappe.msgprint({
                title: __('Success'),
                indicator: 'green',
                message: __('Trip saved successfully! Images will be processed.')
            });
            
            // Here you would add the call to process images with ChatGPT API
            processImagesWithGPT(frm);
        })
        .catch((err) => {
            frappe.msgprint({
                title: __('Error'),
                indicator: 'red',
                message: __('Error saving trip: ') + err.message
            });
        });
}

function processImagesWithGPT(frm) {
    // This function will be implemented later to handle ChatGPT API integration
    console.log('Processing images with GPT:', frm.doc.trip_sheet_image, frm.doc.delivery_note_image);
}