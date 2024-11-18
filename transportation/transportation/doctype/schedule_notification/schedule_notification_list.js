frappe.listview_settings['Schedule Notification'] = {
    add_fields: [
        "name",
        "current_severity_level",
        "notification_type",
        "remaining_time",
        "remaining_distance"
    ],

    columns: [
        {
            label: "ID",
            fieldname: "name",
            fieldtype: "Data"
        },
        {
            label: "Severity Level",
            fieldname: "current_severity_level",
            fieldtype: "Select"
        },
        {
            label: "Notification Type",
            fieldname: "notification_type",
            fieldtype: "Select"
        },
        {
            label: "Remaining Time",
            fieldname: "remaining_time",
            fieldtype: "Int"
        },
        {
            label: "Remaining Distance",
            fieldname: "remaining_distance",
            fieldtype: "Int"
        }
    ],

    formatters: {
        name: function(value, df, doc) {
            let bgcolor = '';
            switch (doc.current_severity_level) {
                case 'Level 1':
                    bgcolor = 'var(--yellow-100)';
                    break;
                case 'Level 2':
                    bgcolor = 'var(--orange-100)';
                    break;
                case 'Level 3':
                    bgcolor = 'var(--red-100)';
                    break;
                default:
                    bgcolor = 'var(--blue-100)';
            }
            $(cur_list.page.container).find(`[data-name="${doc.name}"]`).css('background-color', bgcolor);
            return value;
        }
    }
};