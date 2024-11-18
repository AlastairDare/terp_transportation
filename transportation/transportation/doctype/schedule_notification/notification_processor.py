import frappe
from datetime import datetime
from frappe.utils import now_datetime, date_diff

def process_schedule_notifications():
    """
    Background job to process all Schedule Notification records and update their status
    """
    try:
        # Get all active Schedule Notification records
        notifications = frappe.get_all(
            "Schedule Notification",
            fields=["name", "expiry_date", "level_1_time_threshold", 
                   "level_2_time_threshold", "level_3_time_threshold"]
        )
        
        for notification in notifications:
            try:
                update_notification_status(notification)
            except Exception as e:
                frappe.log_error(
                    f"Error processing notification {notification.name}: {str(e)}",
                    "Schedule Notification Processing Error"
                )
                
    except Exception as e:
        frappe.log_error(
            f"Error in schedule notification processing: {str(e)}",
            "Schedule Notification Processing Error"
        )

def update_notification_status(notification):
    """
    Update a single notification record with current status
    """
    current_time = now_datetime()
    
    # Calculate remaining time in days
    remaining_time = date_diff(notification.expiry_date, current_time)
    
    # Convert threshold strings to days
    thresholds = {
        "level_1": convert_weeks_to_days(notification.level_1_time_threshold),
        "level_2": convert_weeks_to_days(notification.level_2_time_threshold),
        "level_3": convert_weeks_to_days(notification.level_3_time_threshold)
    }
    
    # Determine current severity level
    current_severity_level = determine_severity_level(remaining_time, thresholds)
    
    # Update the notification record
    frappe.db.set_value(
        "Schedule Notification",
        notification.name,
        {
            "last_processed": current_time,
            "remaining_time": remaining_time,
            "current_severity_level": current_severity_level
        },
        update_modified=False
    )
    frappe.db.commit()

def convert_weeks_to_days(weeks_string):
    """
    Convert string like 'One Week', 'Two Weeks' etc. to number of days
    """
    if not weeks_string:
        return 0
        
    weeks_map = {
        "One Week": 7,
        "Two Weeks": 14,
        "Three Weeks": 21,
        "Four Weeks": 28,
        "Five Weeks": 35,
        "Six Weeks": 42,
        "Seven Weeks": 49,
        "Eight Weeks": 56,
        "Nine Weeks": 63,
        "Ten Weeks": 70,
        "Eleven Weeks": 77,
        "Twelve Weeks": 84
    }
    
    return weeks_map.get(weeks_string, 0)

def determine_severity_level(remaining_time, thresholds):
    """
    Determine the current severity level based on remaining time and thresholds
    Level 0 means normal state (most time remaining)
    Level 1 has the second most time remaining (lowest severity)
    Level 2 is medium severity with less time
    Level 3 has the least time remaining (highest severity)
    """
    if remaining_time > thresholds["level_1"]:
        return "Level 0"
    elif remaining_time > thresholds["level_2"]:
        return "Level 1"
    elif remaining_time > thresholds["level_3"]:
        return "Level 2"
    else:
        return "Level 3"