frappe.listview_settings['Schedule Notification'] = {
    refresh: function(listview) {
        // Ensure our custom columns show up
        frappe.meta.get_docfield('Schedule Notification', 'current_severity_level', listview.doctype).in_list_view = 1;
    },

    // Ensure we have the data we need
    list_view_doc: "Schedule Notification",
    
    get_indicator: function(doc) {
        let color = 'blue';
        switch (doc.current_severity_level) {
            case 'Level 1':
                color = 'yellow';
                break;
            case 'Level 2':
                color = 'orange';
                break;
            case 'Level 3':
                color = 'red';
                break;
        }
        return [__(doc.current_severity_level), color, `current_severity_level,=,${doc.current_severity_level}`];
    }
};