frappe.views.TripPlannerView = class TripPlannerView extends frappe.views.ListView {
    setup_defaults() {
        super.setup_defaults();
        this.filters = [
            ["Trip", "docstatus", "<", "2"],
            ["Trip", "status", "=", "Planned"]
        ];
    }

    setup_page() {
        super.setup_page();
        
        // Add Plan Trip button
        this.page.add_button('Plan Trip', () => {
            frappe.new_doc('Trip');
        }, 'primary');

        // Add Truck filter
        this.page.add_field({
            fieldtype: 'Link',
            fieldname: 'truck',
            label: 'Truck',
            options: 'Transportation Asset',
            onchange: () => {
                const value = this.page.fields_dict.truck.get_value();
                const filters = [
                    ["Trip", "docstatus", "<", "2"],
                    ["Trip", "status", "=", "Planned"]
                ];
                if (value) {
                    filters.push(["Trip", "truck", "=", value]);
                }
                this.filter_area.clear();
                filters.forEach(filter => this.filter_area.add(filter));
            }
        });

        // Invoice status filter
        this.page.add_field({
            fieldtype: 'Select',
            fieldname: 'sales_invoice_status',
            label: 'Invoice Status',
            options: '\nNot Invoiced\nInvoiced',
            onchange: () => {
                const value = this.page.fields_dict.sales_invoice_status.get_value();
                const filters = [
                    ["Trip", "docstatus", "<", "2"],
                    ["Trip", "status", "=", "Planned"]
                ];
                if (value) {
                    filters.push(["Trip", "sales_invoice_status", "=", value]);
                }
                this.filter_area.clear();
                filters.forEach(filter => this.filter_area.add(filter));
            }
        });

        // Billing customer filter
        this.page.add_field({
            fieldtype: 'Link',
            fieldname: 'billing_customer',
            label: 'Billing Customer',
            options: 'Customer',
            onchange: () => {
                const value = this.page.fields_dict.billing_customer.get_value();
                const filters = [
                    ["Trip", "docstatus", "<", "2"],
                    ["Trip", "status", "=", "Planned"]
                ];
                if (value) {
                    filters.push(["Trip", "billing_customer", "=", value]);
                }
                this.filter_area.clear();
                filters.forEach(filter => this.filter_area.add(filter));
            }
        });

        // Date range filter
        this.page.add_field({
            fieldtype: 'DateRange',
            fieldname: 'date',
            label: 'Trip Date',
            onchange: () => {
                const dateRange = this.page.fields_dict.date.get_value();
                const filters = [
                    ["Trip", "docstatus", "<", "2"],
                    ["Trip", "status", "=", "Planned"]
                ];
                
                if (dateRange && dateRange.length === 2 && dateRange[0] && dateRange[1]) {
                    filters.push(["Trip", "date", "between", [dateRange[0], dateRange[1]]]);
                }
                this.filter_area.clear();
                filters.forEach(filter => this.filter_area.add(filter));
            }
        });

        // Clear filters button
        this.page.add_inner_button('Clear Filters', () => {
            Object.values(this.page.fields_dict).forEach(field => {
                field.set_value('');
            });
            this.filter_area.clear();
            this.filter_area.add(["Trip", "docstatus", "<", "2"]);
            this.filter_area.add(["Trip", "status", "=", "Planned"]);
        });
    }
};

// Register the custom view
frappe.views.view_registry['Trip Planner'] = 'TripPlannerView';