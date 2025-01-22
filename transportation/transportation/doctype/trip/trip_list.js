frappe.listview_settings['Trip'] = {
    hide_name_column: true,
    hide_name_filter: false,

    add_fields: [
        "name",
        "asset_number",
        "billing_customer",
        "amount",
        "date",
        "sales_invoice_status",
        "billing_supplier",
        "purchase_invoice_status"
    ],
    
    filters: [
        ["Trip", "docstatus", "<", "2"]
    ],

    onload(listview) {
        // Initial setup of filters and buttons
        this.setup_page(listview);
    },

    refresh(listview) {
        // Clear and re-hide elements that might have reappeared
        this.hide_page_elements();
    },

    setup_page(listview) {
        // Hide unwanted elements
        this.hide_page_elements();
        
        // Remove any existing custom buttons and filters
        listview.page.clear_primary_action();
        $('.page-actions .custom-btn-group').remove();
        
        // Clear any existing custom fields
        listview.page.clear_fields();

        // Add Create Sales Invoice Trip Group button
        listview.page.add_button('Create Sales Invoice Trip Group', () => {
            const selected = listview.get_checked_items();
            createTripGroup(listview, 'Sales Invoice Group');
        }, 'primary');

        // Add Create Purchase Invoice Trip Group button
        listview.page.add_button('Create Purchase Invoice Trip Group', () => {
            const selected = listview.get_checked_items();
            createTripGroup(listview, 'Purchase Invoice Group');
        }, 'primary');

        // Truck filter
        listview.page.add_field({
            fieldtype: 'Link',
            fieldname: 'truck',
            label: 'Truck',
            options: 'Transportation Asset',
            onchange: () => {
                const value = listview.page.fields_dict.truck.get_value();
                const filters = [["Trip", "docstatus", "<", "2"]];
                if (value) {
                    filters.push(["Trip", "truck", "=", value]);
                }
                refreshList(listview, filters);
            }
        });

        // Invoice status filter
        listview.page.add_field({
            fieldtype: 'Select',
            fieldname: 'sales_invoice_status',
            label: 'Invoice Status',
            options: '\nNot Invoiced\nInvoiced',
            onchange: () => {
                const value = listview.page.fields_dict.sales_invoice_status.get_value();
                const filters = [["Trip", "docstatus", "<", "2"]];
                if (value) {
                    filters.push(["Trip", "sales_invoice_status", "=", value]);
                }
                refreshList(listview, filters);
            }
        });

        // Billing customer filter
        listview.page.add_field({
            fieldtype: 'Link',
            fieldname: 'billing_customer',
            label: 'Billing Customer',
            options: 'Customer',
            onchange: () => {
                const value = listview.page.fields_dict.billing_customer.get_value();
                const filters = [["Trip", "docstatus", "<", "2"]];
                if (value) {
                    filters.push(["Trip", "billing_customer", "=", value]);
                }
                refreshList(listview, filters);
            }
        });

        // Date range filter
        listview.page.add_field({
            fieldtype: 'DateRange',
            fieldname: 'date',
            label: 'Trip Date',
            onchange: () => {
                const dateRange = listview.page.fields_dict.date.get_value();
                const filters = [["Trip", "docstatus", "<", "2"]];
                
                if (dateRange && dateRange.length === 2 && dateRange[0] && dateRange[1]) {
                    filters.push(["Trip", "date", "between", [dateRange[0], dateRange[1]]]);
                }
                refreshList(listview, filters);
            }
        });
    },

    hide_page_elements() {
        // Hide sidebar for this list view only
        $('.layout-side-section').hide();
        $('.layout-main-section').css('width', '100%');
        
        // Hide standard filter sections and other unwanted elements
        $('.standard-filter-section, .filter-section').hide();
        $('.sort-selector').hide();
        $('.filter-selector').hide();
        $('.filter-button').hide();
        $('.tag-filters-area').hide();
        $('.filter-list').hide();
        $('.result').hide();
    }
};

function refreshList(listview, filters) {
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Trip",
            filters: filters,
            fields: [
                "name",
                "asset_number",
                "billing_customer",
                "amount",
                "date",
                "sales_invoice_status",
                "billing_supplier",
                "purchase_invoice_status"
            ],
            order_by: "modified desc"
        },
        callback: function(r) {
            if (r.message) {
                listview.data = r.message;
                listview.render_list();
            }
        }
    });
}

function createTripGroup(listview, groupType) {
    const selected = listview.get_checked_items();
    
    if (selected.length < 2) {
        frappe.throw('Please select at least 2 trips to group');
        return;
    }

    if (groupType === 'Sales Invoice Group') {
        if (selected.some(trip => trip.sales_invoice_status !== 'Not Invoiced')) {
            frappe.throw('Some selected trips are already in a Sales Invoice Group');
            return;
        }

        const customers = [...new Set(selected.map(trip => trip.billing_customer))];
        if (customers.length > 1) {
            frappe.throw('All selected trips must have the same billing customer');
            return;
        }
        if (!customers[0]) {
            frappe.throw('Selected trips must have a billing customer');
            return;
        }
    } else {
        if (selected.some(trip => trip.purchase_invoice_status !== 'Not Invoiced')) {
            frappe.throw('Some selected trips are already in a Purchase Invoice Group');
            return;
        }

        const suppliers = [...new Set(selected.map(trip => trip.billing_supplier))];
        if (suppliers.length > 1) {
            frappe.throw('All selected trips must have the same billing supplier');
            return;
        }
        if (!suppliers[0]) {
            frappe.throw('Selected trips must have a billing supplier');
            return;
        }
    }

    frappe.call({
        method: 'transportation.transportation.doctype.trip_group.trip_group.create_trip_group',
        args: {
            trips: selected.map(trip => trip.name),
            group_type: groupType,
            summarize_lines: 1
        },
        freeze: true,
        freeze_message: __('Creating Trip Group...'),
        callback: function(r) {
            if (r.message) {
                const billingParty = groupType === 'Sales Invoice Group' 
                    ? selected[0].billing_customer 
                    : selected[0].billing_supplier;
                
                frappe.msgprint({
                    title: __('Trip Group Created'),
                    indicator: 'green',
                    message: __(
                        `{0} Trip Group <a href="/app/trip-group/{1}">{1}</a> created with {2} trips for {3}`,
                        [groupType === 'Sales Invoice Group' ? 'Sales Invoice' : 'Purchase Invoice',
                         r.message,
                         selected.length,
                         billingParty]
                    )
                });
                
                listview.refresh();
            }
        }
    });
}