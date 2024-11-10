import frappe
from frappe.model.document import Document

class NotificationsConfig(Document):
    def validate(self):
        """
        Validate the notification settings
        """
        self.validate_time_remaining_values()
    
    def validate_time_remaining_values(self):
        """
        Ensure that time remaining values are positive and level 1 > level 2 > level 3
        """
        sections = [
            {
                'check_field': 'track_driver_license_expiry_date',
                'fields': ['driver_license_level_1_time_remaining', 
                          'driver_license_level_2_time_remaining', 
                          'driver_license_level_3_time_remaining']
            },
            {
                'check_field': 'track_driver_prdp_expiry_date',
                'fields': ['prdp_level_1_time_remaining', 
                          'prdp_level_2_time_remaining', 
                          'prdp_level_3_time_remaining']
            },
            {
                'check_field': 'track_transportation_assets_registration_expiry_date',
                'fields': ['transportation_asset_registration_level_1_time_remaining',
                          'transportation_asset_registration_level_2_time_remaining',
                          'transportation_asset_registration_level_3_time_remaining']
            },
            {
                'check_field': 'track_transportation_assets_warranty_expiry_date',
                'fields': ['transportation_asset_warranty_level_1_time_remaining',
                          'transportation_asset_warranty_level_2_time_remaining',
                          'transportation_asset_warranty_level_3_time_remaining']
            },
            {
                'check_field': 'track_transportation_assets_crw_expiry_date',
                'fields': ['transportation_asset_crw_level_1_time_remaining',
                          'transportation_asset_crw_level_2_time_remaining',
                          'transportation_asset_crw_level_3_time_remaining']
            },
            {
                'check_field': 'track_transportation_assets_cbrta_expiry_date',
                'fields': ['transportation_asset_cbrta_level_1_time_remaining',
                          'transportation_asset_cbrta_level_2_time_remaining',
                          'transportation_asset_cbrta_level_3_time_remaining']
            },
            {
                'check_field': 'track_vehicles_upcoming_service_by_time',
                'fields': ['track_vehicles_service_by_time_level_1_time_remaining',
                          'track_vehicles_service_by_time_level_2_time_remaining',
                          'track_vehicles_service_by_time_level_3_time_remaining']
            },
            {
                'check_field': 'track_vehicles_upcoming_service_by_kilometres',
                'fields': ['track_vehicles_service_by_kilometres_level_1_time_remaining',
                          'track_vehicles_service_by_kilometres_level_2_time_remaining',
                          'track_vehicles_service_by_kilometres_level_3_time_remaining']
            }
        ]

        for section in sections:
            if self.get(section['check_field']):
                self._validate_section_values(section['fields'])
    
    def _validate_section_values(self, fields):
        """
        Validate individual section's time remaining values
        
        Args:
            fields (list): List of field names to validate in order [level1, level2, level3]
        """
        # Validate values are positive
        for field in fields:
            if self.get(field) is not None and self.get(field) < 0:
                frappe.throw(
                    f"Time remaining values must be positive. {field} has negative value."
                )
        
        # Validate level hierarchy (level1 > level2 > level3)
        for i in range(len(fields) - 1):
            current_field = fields[i]
            next_field = fields[i + 1]
            
            current_value = self.get(current_field)
            next_value = self.get(next_field)
            
            if (current_value is not None and next_value is not None and 
                current_value <= next_value):
                frappe.throw(
                    f"{current_field} must be greater than {next_field}"
                )

    def before_save(self):
        """
        Clear dependent fields when their section toggle is turned off
        """
        sections = [
            {
                'check_field': 'track_driver_license_expiry_date',
                'fields': ['driver_license_level_1_time_remaining', 
                          'driver_license_level_2_time_remaining', 
                          'driver_license_level_3_time_remaining']
            },
            {
                'check_field': 'track_driver_prdp_expiry_date',
                'fields': ['prdp_level_1_time_remaining', 
                          'prdp_level_2_time_remaining', 
                          'prdp_level_3_time_remaining']
            },
            {
                'check_field': 'track_transportation_assets_registration_expiry_date',
                'fields': ['transportation_asset_registration_level_1_time_remaining',
                          'transportation_asset_registration_level_2_time_remaining',
                          'transportation_asset_registration_level_3_time_remaining']
            },
            {
                'check_field': 'track_transportation_assets_warranty_expiry_date',
                'fields': ['transportation_asset_warranty_level_1_time_remaining',
                          'transportation_asset_warranty_level_2_time_remaining',
                          'transportation_asset_warranty_level_3_time_remaining']
            },
            {
                'check_field': 'track_transportation_assets_crw_expiry_date',
                'fields': ['transportation_asset_crw_level_1_time_remaining',
                          'transportation_asset_crw_level_2_time_remaining',
                          'transportation_asset_crw_level_3_time_remaining']
            },
            {
                'check_field': 'track_transportation_assets_cbrta_expiry_date',
                'fields': ['transportation_asset_cbrta_level_1_time_remaining',
                          'transportation_asset_cbrta_level_2_time_remaining',
                          'transportation_asset_cbrta_level_3_time_remaining']
            },
            {
                'check_field': 'track_vehicles_upcoming_service_by_time',
                'fields': ['track_vehicles_service_by_time_level_1_time_remaining',
                          'track_vehicles_service_by_time_level_2_time_remaining',
                          'track_vehicles_service_by_time_level_3_time_remaining']
            },
            {
                'check_field': 'track_vehicles_upcoming_service_by_kilometres',
                'fields': ['track_vehicles_service_by_kilometres_level_1_time_remaining',
                          'track_vehicles_service_by_kilometres_level_2_time_remaining',
                          'track_vehicles_service_by_kilometres_level_3_time_remaining']
            }
        ]

        for section in sections:
            if not self.get(section['check_field']):
                for field in section['fields']:
                    self.set(field, None)