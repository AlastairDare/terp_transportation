frappe.listview_settings['Schedule Notification'] = {
    add_fields: [
        "name",
        "current_severity_level"
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