import frappe

@frappe.whitelist()
def process_schedule_notifications():
    """Process schedule notifications based on current configuration"""
    try:
        config = frappe.get_single('Notifications Config')
        result = config.process_schedule_notifications()
        frappe.db.commit()
        return result
    except Exception as e:
        frappe.log_error(f"Error in schedule notification processing: {str(e)}")
        raise