frappe.listview_settings['Trip'] = {
    add_fields: ["truck", "date", "sales_invoice_status", "billing_customer"],
    
    get_filters_for_args() {
        return [["Trip", "docstatus", "<", "2"]];
    },

    onload(listview) {
        listview.page.add_field({
            fieldtype: 'Link',
            fieldname: 'truck',
            label: 'Truck',
            options: 'Transportation Asset'
        });

        listview.page.add_field({
            fieldtype: 'Select',
            fieldname: 'sales_invoice_status',
            label: 'Invoice Status',
            options: '\nNot Invoiced\nInvoiced'
        });

        listview.page.add_field({
            fieldtype: 'Link',
            fieldname: 'billing_customer',
            label: 'Billing Customer',
            options: 'Customer'
        });

        // Add from date with filtering logic
        listview.page.add_field({
            fieldtype: 'Date',
            fieldname: 'from_date',
            label: 'From Date',
            onchange: () => updateDateFilter(listview)
        });

        // Add to date with filtering logic
        listview.page.add_field({
            fieldtype: 'Date',
            fieldname: 'to_date',
            label: 'To Date',
            onchange: () => updateDateFilter(listview)
        });
    }
};

function updateDateFilter(listview) {
    const fromDate = listview.page.fields_dict.from_date.get_value();
    const toDate = listview.page.fields_dict.to_date.get_value();
    
    // Clear existing date filters
    listview.filter_area.clear();
    
    // Add back the default docstatus filter
    listview.filter_area.add([["Trip", "docstatus", "<", "2"]]);
    
    // If we have both dates, add the date range filter
    if (fromDate && toDate) {
        if (fromDate > toDate) {
            frappe.msgprint('From Date cannot be after To Date');
            listview.page.fields_dict.to_date.set_value('');
            return;
        }
        
        // Add filter for the "date" field in Trip DocType
        listview.filter_area.add([
            ["Trip", "date", ">=", fromDate],
            ["Trip", "date", "<=", toDate]
        ]);
    }
    
    listview.refresh();
}