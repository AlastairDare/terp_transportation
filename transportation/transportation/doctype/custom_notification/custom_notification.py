import frappe
from frappe.model.document import Document
from frappe.utils import get_week_days

class CustomNotification(Document):
    def validate(self):
        """Validate the custom notification settings"""
        self.validate_time_remaining_values()
    
    def validate_time_remaining_values(self):
        """Ensure that time remaining values are positive and level 1 > level 2 > level 3"""
        # Convert week strings to days for comparison
        values = [
            get_week_days(self.level_1_threshold),
            get_week_days(self.level_2_threshold),
            get_week_days(self.level_3_threshold)
        ]
        
        # Validate level hierarchy (level1 > level2 > level3)
        field_pairs = [
            ('level_1_threshold', 'level_2_threshold'),
            ('level_2_threshold', 'level_3_threshold')
        ]
        
        for i, (field1, field2) in enumerate(field_pairs):
            if values[i] <= values[i + 1]:
                frappe.throw(
                    f"{field1} must be greater than {field2}"
                )