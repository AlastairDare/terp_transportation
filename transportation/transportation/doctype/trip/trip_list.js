frappe.listview_settings['Trip'] = {
    add_fields: ["truck", "date", "sales_invoice_status"],
    
    filters: [
        ['Trip', 'docstatus', '<', '2']
    ],

    onload: function(listview) {
        // Create a filter group div
        const filterGroup = $('<div class="filter-group d-flex"></div>').appendTo(listview.page.page_form);

        // Add truck filter
        if (!listview.page.fields_dict.truck) {
            listview.page.add_field({
                fieldtype: 'Link',
                fieldname: 'truck',
                label: __('Truck'),
                options: 'Transportation Asset',
                onchange: function() {
                    listview.refresh();
                }
            });
        }

        // Add sales invoice status filter
        if (!listview.page.fields_dict.sales_invoice_status) {
            listview.page.add_field({
                fieldtype: 'Select',
                fieldname: 'sales_invoice_status',
                label: __('Invoice Status'),
                options: '\nNot Invoiced\nInvoiced',
                onchange: function() {
                    listview.refresh();
                }
            });
        }

        // Add date filters to the filter group
        if (!listview.page.fields_dict.from_date) {
            const fromDateField = listview.page.add_field({
                fieldtype: 'Date',
                fieldname: 'from_date',
                label: __('From Date'),
                onchange: function() {
                    validateAndSetDateFilter(listview);
                }
            });
            $(fromDateField.wrapper).appendTo(filterGroup);
        }

        if (!listview.page.fields_dict.to_date) {
            const toDateField = listview.page.add_field({
                fieldtype: 'Date',
                fieldname: 'to_date',
                label: __('To Date'),
                onchange: function() {
                    validateAndSetDateFilter(listview);
                }
            });
            $(toDateField.wrapper).appendTo(filterGroup);
        }

        // Add some margin between date fields
        filterGroup.find('.frappe-control').css('margin-right', '10px');
    }
};

// Function to validate and set date filter
function validateAndSetDateFilter(listview) {
    const fromDate = listview.page.fields_dict.from_date.get_value();
    const toDate = listview.page.fields_dict.to_date.get_value();

    // Clear any existing error messages
    frappe.show_alert('', 0);

    // Only validate if both dates are selected
    if (fromDate && toDate) {
        if (fromDate > toDate) {
            frappe.show_alert({
                message: __('From Date cannot be after To Date'),
                indicator: 'red'
            }, 5);
            // Clear the To Date field
            listview.page.fields_dict.to_date.set_value('');
            return;
        }
        
        // Set the date filter on the actual date field
        listview.filter_area.add([[
            'Trip',
            'date',
            'Between',
            [fromDate, toDate]
        ]]);
    } else {
        // Clear the date filter if either date is empty
        listview.filter_area.remove('date');
    }
}