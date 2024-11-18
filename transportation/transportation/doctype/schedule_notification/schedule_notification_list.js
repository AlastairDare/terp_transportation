frappe.listview_settings['Schedule Notification'] = {
    add_fields: ['current_severity_level', 'status'],
    
    onload: function(listview) {
        // Add custom CSS for row coloring
        const style = document.createElement('style');
        style.textContent = `
            .level-1-row { background-color: rgba(255, 255, 0, 0.1) !important; }
            .level-2-row { background-color: rgba(255, 165, 0, 0.1) !important; }
            .level-3-row { background-color: rgba(255, 0, 0, 0.1) !important; }
        `;
        document.head.appendChild(style);
        
        listview.page.add_inner_button(__('Refresh'), function() {
            listview.refresh();
        });
    },
    
    refresh: function(listview) {
        if (!listview.fields_dict.current_severity_level) {
            listview.settings.add_fields.push('current_severity_level');
        }
    },

    // Override the standard row rendering
    prepare_data: function(data) {
        // Remove any existing level classes
        const levelClasses = ['level-1-row', 'level-2-row', 'level-3-row'];
        data.$row.removeClass(levelClasses.join(' '));
        
        // Add appropriate class based on severity level
        if (data.current_severity_level) {
            const level = data.current_severity_level.split(' ')[1]; // Gets "1" from "Level 1"
            data.$row.addClass(`level-${level}-row`);
        }
    },

    formatters: {
        current_severity_level: function(value) {
            return value || '';
        }
    }
};