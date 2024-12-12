frappe.listview_settings['Trip'] = {
    add_fields: ["truck", "date"],
    
    // Add filters to the list view
    filters: [
        ['Trip', 'docstatus', '<', '2']
    ],

    onload: function(listview) {
        // Add the filter fields
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

        if (!listview.page.fields_dict.date) {
            listview.page.add_field({
                fieldtype: 'DateRange',
                fieldname: 'date',
                label: __('Trip Date'),
                onchange: function() {
                    listview.refresh();
                }
            });
        }

        // Check for dashboard filters
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.has('dashboard_filters')) {
            try {
                const dashboardFilters = JSON.parse(decodeURIComponent(urlParams.get('dashboard_filters')));
                console.log('Parsed dashboard filters:', dashboardFilters);

                // Try using frappe.route_options
                frappe.route_options = {
                    'truck': dashboardFilters.truck,
                    'date': ['between', [dashboardFilters.from_date, dashboardFilters.to_date]]
                };

                // Force refresh
                listview.refresh();
            } catch (e) {
                console.error('Error applying filters:', e);
            }
        }
    }
};