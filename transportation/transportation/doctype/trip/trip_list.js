frappe.listview_settings['Trip'] = {
    add_fields: ["truck", "date", "sales_invoice_status", "billing_customer"],
    
    get_filters_for_args() {
        // Get standard filters
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

        listview.page.add_field({
            fieldtype: 'Date',
            fieldname: 'from_date',
            label: 'From Date'
        });

        listview.page.add_field({
            fieldtype: 'Date',
            fieldname: 'to_date',
            label: 'To Date'
        });
    }
};