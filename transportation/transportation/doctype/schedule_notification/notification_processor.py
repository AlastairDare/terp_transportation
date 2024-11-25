import frappe

def process_schedule_notifications():
    """
    Background job to process all Schedule Notification records
    """
    try:
        config = frappe.get_single('Notifications Config')
        config.process_schedule_notifications()
    except Exception as e:
        frappe.log_error(
            f"Error in schedule notification processing: {str(e)}",
            "Schedule Notification Processing Error"
        )