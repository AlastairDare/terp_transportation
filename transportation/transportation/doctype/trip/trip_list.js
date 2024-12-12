frappe.listview_settings['Trip'] = {
    add_fields: ["truck", "date"],
    get_indicator: function(doc) {
        // Optional: Add status indicators if needed
        return [__(doc.status), doc.status === "Draft" ? "red" : "green", "status,=," + doc.status];
    },
    onload: function(listview) {
        // Add your filters here
        listview.page.add_field({
            fieldtype: 'Link',
            fieldname: 'truck',
            label: __('Truck'),
            options: 'Transportation Asset',
            onchange: function() {
                listview.refresh();
            }
        });

        listview.page.add_field({
            fieldtype: 'Date',
            fieldname: 'date',
            label: __('Trip Date'),
            onchange: function() {
                listview.refresh();
            }
        });
    }
};