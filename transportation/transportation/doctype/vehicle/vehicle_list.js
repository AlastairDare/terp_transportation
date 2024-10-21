frappe.listview_settings['Vehicle'] = {
    add_fields: ["vin", "license_plate", "make", "model", "year", "status"],
    columns: ["vin", "license_plate", "make", "model", "year", "status"],
    filters: [["status", "=", "Active"]],
    onload: function(listview) {
        listview.page.add_inner_button(__('Add Vehicle'), function() {
            frappe.new_doc("Vehicle");
        });
    },
    formatters: {
        status: function(value) {
            let status_color = {
                "Active": "green",
                "In Maintenance": "orange",
                "Retired": "red"
            };
            return `<span class="indicator ${status_color[value] || 'gray'}">${value}</span>`;
        }
    }
};