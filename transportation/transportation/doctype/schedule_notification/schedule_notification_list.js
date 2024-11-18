frappe.listview_settings['Schedule Notification'] = {
    get_indicator: function(doc) {
        // Check for distance-based schedule notifications with missing data
        if (doc.threshold_type === 'Distance' && 
            (!doc.current_odometer_reading || !doc.last_service_date || !doc.last_service_odometer_reading)) {
            return [doc.notification_type, 'purple', 'data_missing,=,1'];
        }
        
        // Regular severity-based coloring
        switch (doc.current_severity_level) {
            case 'Level 1':
                return [doc.notification_type, 'yellow', 'current_severity_level,=,Level 1'];
            case 'Level 2':
                return [doc.notification_type, 'orange', 'current_severity_level,=,Level 2'];
            case 'Level 3':
                return [doc.notification_type, 'red', 'current_severity_level,=,Level 3'];
            default:
                return [doc.notification_type, 'blue', ''];
        }
    }
};