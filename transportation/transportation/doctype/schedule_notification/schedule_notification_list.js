frappe.listview_settings['Schedule Notification'] = {
    add_fields: ['current_severity_level', 'status'],  // Add fields we want to fetch
    
    onload: function(listview) {
        // Set up columns that should appear in the list view
        listview.page.add_inner_button(__('Refresh'), function() {
            listview.refresh();
        });
    },
    
    refresh: function(listview) {
        // Configure which fields should appear in the list view
        if (!listview.fields_dict.current_severity_level) {
            listview.settings.add_fields.push('current_severity_level');
        }
    },
    
    get_indicator: function(doc) {
        // Define color coding based on severity level
        if (!doc.current_severity_level) return [__('Unknown'), 'gray', 'current_severity_level,=,""'];
        
        let colors = {
            'Level 1': 'yellow',
            'Level 2': 'orange',
            'Level 3': 'red'
        };
        
        let color = colors[doc.current_severity_level] || 'blue';
        return [__(doc.current_severity_level), color, `current_severity_level,=,${doc.current_severity_level}`];
    },

    formatters: {
        current_severity_level: function(value) {
            return value || '';
        }
    }
};