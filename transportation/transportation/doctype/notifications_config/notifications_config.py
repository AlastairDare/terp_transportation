import frappe
from frappe.model.document import Document
from frappe.utils import getdate, nowdate, add_days, date_diff

def get_week_days(week_option):
    """Convert week option to days"""
    week_map = {
        'One Week': 7,
        'Two Weeks': 14,
        'Three Weeks': 21,
        'Four Weeks': 28,
        'Five Weeks': 35,
        'Six Weeks': 42,
        'Seven Weeks': 49,
        'Eight Weeks': 56,
        'Nine Weeks': 63,
        'Ten Weeks': 70,
        'Eleven Weeks': 77,
        'Twelve Weeks': 84
    }
    return week_map.get(week_option, 0)

@frappe.whitelist()
def process_notifications():
    """Process notifications based on current configuration"""
    config = frappe.get_single('Notifications Config')
    return config.process_notifications()

class NotificationsConfig(Document):
    def validate(self):
        """Validate the notification settings"""
        self.validate_time_remaining_values()
    
    def validate_time_remaining_values(self):
        """Ensure that time remaining values are positive and level 1 > level 2 > level 3"""
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
            }
        ]

        for section in sections:
            if self.get(section['check_field']):
                self._validate_section_values(section['fields'])

    def _validate_section_values(self, fields):
        """Validate individual section's time remaining values"""
        # Convert week strings to days for comparison
        values = [get_week_days(self.get(field)) for field in fields]
        
        # Validate level hierarchy (level1 > level2 > level3)
        for i in range(len(values) - 1):
            if values[i] <= values[i + 1]:
                frappe.throw(
                    f"{fields[i]} must be greater than {fields[i + 1]}"
                )
    
    def process_notifications(self):
        """Main function to process notifications based on current configuration"""
        # Track which notification types were previously configured
        previous_types = set(frappe.get_all('Notification', 
                                          fields=['notification_type'], 
                                          distinct=True, 
                                          pluck='notification_type'))
        
        # Get current enabled types
        current_types = set()
        if self.track_driver_license_expiry_date:
            current_types.add('Driver License')
        if self.track_driver_prdp_expiry_date:
            current_types.add('Driver PrDP')
        if self.track_transportation_assets_registration_expiry_date:
            current_types.add('Transportation Asset Registration')
        if self.track_transportation_assets_warranty_expiry_date:
            current_types.add('Transportation Asset Warranty')
        if self.track_transportation_assets_crw_expiry_date:
            current_types.add('Transportation Asset CRW')
        if self.track_transportation_assets_cbrta_expiry_date:
            current_types.add('Transportation Asset C-BRTA')
        if self.track_vehicles_upcoming_service_by_time:
            current_types.add('Transportation Asset Service Time')
        if self.track_vehicles_upcoming_service_by_kilometres:
            current_types.add('Transportation Asset Service Distance')
        
        # Remove notifications for disabled types
        types_to_remove = previous_types - current_types
        if types_to_remove:
            frappe.db.sql("""
                DELETE FROM `tabNotification` 
                WHERE notification_type IN %(types)s
            """, {'types': tuple(types_to_remove)})
        
        # Process notifications
        asset_count = 0
        driver_count = 0
        
        if self.track_driver_license_expiry_date or self.track_driver_prdp_expiry_date:
            driver_count = self._process_driver_notifications()
        
        if (self.track_transportation_assets_registration_expiry_date or
            self.track_transportation_assets_warranty_expiry_date or
            self.track_transportation_assets_crw_expiry_date or
            self.track_transportation_assets_cbrta_expiry_date or
            self.track_vehicles_upcoming_service_by_time or
            self.track_vehicles_upcoming_service_by_kilometres):
            asset_count = self._process_asset_notifications()
        
        frappe.db.commit()
        
        return {
            "assets": asset_count,
            "drivers": driver_count
        }

    def _process_driver_notifications(self):
        """Process all driver-related notifications"""
        drivers = frappe.get_all('Driver', fields=['name', 'license_expiry_date', 'prdp_expiration_date'])
        driver_count = 0

        for driver in drivers:
            notifications_created = False
            
            # Process driver's license notifications
            if self.track_driver_license_expiry_date and driver.license_expiry_date:
                self._create_time_based_notification(
                    driver=driver.name,
                    notification_type='Driver License',
                    expiry_date=driver.license_expiry_date,
                    level_1_threshold=self.driver_license_level_1_time_remaining,
                    level_2_threshold=self.driver_license_level_2_time_remaining,
                    level_3_threshold=self.driver_license_level_3_time_remaining
                )
                notifications_created = True
            
            # Process PrDP notifications
            if self.track_driver_prdp_expiry_date and driver.prdp_expiration_date:
                self._create_time_based_notification(
                    driver=driver.name,
                    notification_type='Driver PrDP',
                    expiry_date=driver.prdp_expiration_date,
                    level_1_threshold=self.prdp_level_1_time_remaining,
                    level_2_threshold=self.prdp_level_2_time_remaining,
                    level_3_threshold=self.prdp_level_3_time_remaining
                )
                notifications_created = True
            
            if notifications_created:
                driver_count += 1
        
        return driver_count

    def _process_asset_notifications(self):
        """Process all asset-related notifications"""
        assets = frappe.get_all(
            'Transportation Asset',
            fields=[
                'name', 'registration_expiry', 'warranty_expiration',
                'certificate_of_roadworthiness_expiration',
                'cross_border_road_transport_permit_expiration',
                'most_recent_service', 'current_mileage'
            ]
        )
        asset_count = 0

        for asset in assets:
            notifications_created = False
            
            # Process registration notifications
            if self.track_transportation_assets_registration_expiry_date and asset.registration_expiry:
                self._create_time_based_notification(
                    transportation_asset=asset.name,
                    notification_type='Transportation Asset Registration',
                    expiry_date=asset.registration_expiry,
                    level_1_threshold=self.transportation_asset_registration_level_1_time_remaining,
                    level_2_threshold=self.transportation_asset_registration_level_2_time_remaining,
                    level_3_threshold=self.transportation_asset_registration_level_3_time_remaining
                )
                notifications_created = True

            # Process warranty notifications
            if self.track_transportation_assets_warranty_expiry_date and asset.warranty_expiration:
                self._create_time_based_notification(
                    transportation_asset=asset.name,
                    notification_type='Transportation Asset Warranty',
                    expiry_date=asset.warranty_expiration,
                    level_1_threshold=self.transportation_asset_warranty_level_1_time_remaining,
                    level_2_threshold=self.transportation_asset_warranty_level_2_time_remaining,
                    level_3_threshold=self.transportation_asset_warranty_level_3_time_remaining
                )
                notifications_created = True

            # Process CRW notifications
            if self.track_transportation_assets_crw_expiry_date and asset.certificate_of_roadworthiness_expiration:
                self._create_time_based_notification(
                    transportation_asset=asset.name,
                    notification_type='Transportation Asset CRW',
                    expiry_date=asset.certificate_of_roadworthiness_expiration,
                    level_1_threshold=self.transportation_asset_crw_level_1_time_remaining,
                    level_2_threshold=self.transportation_asset_crw_level_2_time_remaining,
                    level_3_threshold=self.transportation_asset_crw_level_3_time_remaining
                )
                notifications_created = True

            # Process C-BRTA notifications
            if self.track_transportation_assets_cbrta_expiry_date and asset.cross_border_road_transport_permit_expiration:
                self._create_time_based_notification(
                    transportation_asset=asset.name,
                    notification_type='Transportation Asset C-BRTA',
                    expiry_date=asset.cross_border_road_transport_permit_expiration,
                    level_1_threshold=self.transportation_asset_cbrta_level_1_time_remaining,
                    level_2_threshold=self.transportation_asset_cbrta_level_2_time_remaining,
                    level_3_threshold=self.transportation_asset_cbrta_level_3_time_remaining
                )
                notifications_created = True

            # Process service notifications
            if asset.most_recent_service:
                service_doc = frappe.get_doc('Asset Unified Maintenance', asset.most_recent_service)
                
                # Time-based service notifications
                if self.track_vehicles_upcoming_service_by_time and service_doc.complete_date:
                    self._create_time_based_notification(
                        transportation_asset=asset.name,
                        notification_type='Transportation Asset Service Time',
                        expiry_date=service_doc.complete_date,
                        level_1_threshold=self.track_vehicles_service_by_time_level_1_time_remaining,
                        level_2_threshold=self.track_vehicles_service_by_time_level_2_time_remaining,
                        level_3_threshold=self.track_vehicles_service_by_time_level_3_time_remaining,
                        asset_unified_maintenance=asset.most_recent_service
                    )
                    notifications_created = True

                # Distance-based service notifications
                if self.track_vehicles_upcoming_service_by_kilometres and service_doc.odometer_reading is not None and asset.current_mileage is not None:
                    self._create_distance_based_notification(
                        transportation_asset=asset.name,
                        notification_type='Transportation Asset Service Distance',
                        current_odometer=asset.current_mileage,
                        last_service_odometer=service_doc.odometer_reading,
                        level_1_threshold=self.track_vehicles_service_by_kilometres_level_1_distance_remaining,
                        level_2_threshold=self.track_vehicles_service_by_kilometres_level_2_distance_remaining,
                        level_3_threshold=self.track_vehicles_service_by_kilometres_level_3_distance_remaining,
                        asset_unified_maintenance=asset.most_recent_service
                    )
                    notifications_created = True

            if notifications_created:
                asset_count += 1

        return asset_count

    def _create_time_based_notification(self, notification_type, expiry_date, 
                                      level_1_threshold, level_2_threshold, level_3_threshold,
                                      transportation_asset=None, driver=None, 
                                      asset_unified_maintenance=None):
        """Create a time-based notification"""
        remaining_days = date_diff(expiry_date, nowdate())
        
        # Convert week thresholds to days
        level_1_days = get_week_days(level_1_threshold)
        level_2_days = get_week_days(level_2_threshold)
        level_3_days = get_week_days(level_3_threshold)
        
        # Determine severity level
        if remaining_days <= level_3_days:
            severity = 'Level 3'
        elif remaining_days <= level_2_days:
            severity = 'Level 2'
        elif remaining_days <= level_1_days:
            severity = 'Level 1'
        else:
            return  # No notification needed
        
        # Delete existing notification if any
        existing = frappe.db.exists('Notification', {
            'notification_type': notification_type,
            'transportation_asset': transportation_asset,
            'driver': driver
        })
        if existing:
            frappe.delete_doc('Notification', existing)
            
        notification = frappe.get_doc({
            'doctype': 'Notification',
            'notification_type': notification_type,
            'threshold_type': 'Time',
            'transportation_asset': transportation_asset,
            'driver': driver,
            'asset_unified_maintenance': asset_unified_maintenance,
            'expiry_date': expiry_date,
            'level_1_time_threshold': level_1_threshold,
            'level_2_time_threshold': level_2_threshold,
            'level_3_time_threshold': level_3_threshold,
            'remaining_time': remaining_days,
            'current_severity_level': severity,
            'last_processed': frappe.utils.now()
        })
        
        notification.insert()
    
    def _create_distance_based_notification(self, notification_type, current_odometer, 
                                         last_service_odometer, level_1_threshold, 
                                         level_2_threshold, level_3_threshold,
                                         transportation_asset, asset_unified_maintenance):
        """Create a distance-based notification"""
        distance_since_service = current_odometer - last_service_odometer
        
        # Determine severity level based on kilometers traveled since last service
        if distance_since_service >= level_3_threshold:
            severity = 'Level 3'
        elif distance_since_service >= level_2_threshold:
            severity = 'Level 2'
        elif distance_since_service >= level_1_threshold:
            severity = 'Level 1'
        else:
            return  # No notification needed
        
        # Delete existing notification if any
        existing = frappe.db.exists('Notification', {
            'notification_type': notification_type,
            'transportation_asset': transportation_asset
        })
        if existing:
            frappe.delete_doc('Notification', existing)
        
        notification = frappe.get_doc({
            'doctype': 'Notification',
            'notification_type': notification_type,
            'threshold_type': 'Distance',
            'transportation_asset': transportation_asset,
            'asset_unified_maintenance': asset_unified_maintenance,
            'current_odometer_reading': current_odometer,
            'last_service_odometer_reading': last_service_odometer,
            'level_1_distance_threshold': level_1_threshold,
            'level_2_distance_threshold': level_2_threshold,
            'level_3_distance_threshold': level_3_threshold,
            'remaining_distance': distance_since_service,
            'current_severity_level': severity,
            'last_processed': frappe.utils.now()
        })
        
        notification.insert()
    
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