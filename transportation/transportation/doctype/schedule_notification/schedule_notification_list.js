frappe.listview_settings['Schedule Notification'] = {
    get_indicator: function(doc) {
        // Check for distance-based notifications with missing data
        if (doc.threshold_type === 'Distance' && 
            (!doc.current_odometer_reading || !doc.last_service_date || !doc.last_service_odometer_reading)) {
            return [doc.notification_type, 'purple', 'data_missing,=,1'];
        }
        
        // Regular severity-based coloring
        if (doc.current_severity_level === 'Level 1') {
            return [doc.notification_type, 'yellow', 'severity,=,1'];
        } else if (doc.current_severity_level === 'Level 2') {
            return [doc.notification_type, 'orange', 'severity,=,2'];
        } else if (doc.current_severity_level === 'Level 3') {
            return [doc.notification_type, 'red', 'severity,=,3'];
        }
        
        return [doc.notification_type, 'blue', ''];
    }
};