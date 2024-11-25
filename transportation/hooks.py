app_name = "transportation"
app_title = "Transportation"
app_publisher = "Alastair Dare"
app_description = "Transportation management system for T-ERP"
app_email = "tech@t-erp.co.za"
app_license = "gpl-3.0"

workspaces = [
    {
        "name": "Transportation",
        "icon": "truck",
        "module": "Transportation",
        "type": "module",
        "link": "transportation",
        "label": "Transportation"
    },
    {
        "name": "Operations",
        "icon": "road",
        "module": "Transportation",
        "type": "page",
        "link": "operations",
        "label": "Operations"
    },
    {
        "name": "Fleet Manager",
        "icon": "fleet",
        "module": "Transportation",
        "type": "page",
        "link": "fleet_manager",
        "label": "Fleet Manager"
    },
    {
        "name": "T-ERP Super Admin",
        "icon": "gear",
        "module": "Transportation",
        "type": "page",
        "link": "t_erp_super_admin",
        "label": "T-ERP Super Admin"
    }
]

add_to_apps_screen = [
	{
		"name": "transportation",
		"logo": "/assets/transportation/images/frappe-transportation-logo.svg",
		"title": "Transportation",
		"route": "/app/transportation",
	}
]

app_include_js = "transportation.bundle.js"
app_include_css = "transportation.bundle.css"

doc_events = {
    "Delivery Note Capture": {
        "after_insert": "transportation.transportation.ai_processing.chain_builder.process_delivery_note_capture"
    },
    "Transportation Asset": {
        "validate": "transportation.transportation.doctype.transportation_asset.transportation_asset.validate"
    },
    "Trip": {
        "validate": "transportation.transportation.doctype.trip.trip.validate",
        "before_save": "transportation.transportation.doctype.trip.trip.before_save"
    },
    "Refuel": {
    "validate": "transportation.transportation.doctype.refuel.refuel.validate",
    "before_save": "transportation.transportation.doctype.refuel.refuel.before_save"
    },
    "Tolls": {
        "before_save": "transportation.transportation.doctype.tolls.tolls.validate",
        "after_insert": "transportation.transportation.doctype.tolls.tolls.after_insert"
    }

}

has_permission = {
	"Asset Unified Maintenance": "transportation.transportation.doctype.asset_unified_maintenance.asset_unified_maintenance.has_permission"
}

whitelisted_methods = {
	"transportation.transportation.doctype.asset_unified_maintenance.asset_unified_maintenance.get_last_maintenance_dates": True,
        "transportation.transportation.page.transportation_dashboard.transportation_dashboard.get_dashboard_data": True,
        "transportation.transportation.page.transportation_dashboard.transportation_dashboard.get_columns": True
}


dependencies = [
    {
        "package": "opencv-python-headless",
        "version": ">=4.8.0"
    },
    {
        "package": "Pillow",
        "version": ">=10.0.0"
    },
    {
        "package": "numpy",
        "version": ">=1.24.0"
    }
]

doctype_properties = {
    "Toll Capture": {
        "allow_copy": 1,
        "allow_rename": 0,
    }
}

scheduler_events = {
    "cron": {
        "0 0 * * *": [
            "transportation.transportation.doctype.schedule_notification.notification_processor.process_schedule_notifications"
        ]
    }
}

on_session_creation = [
    "transportation.api.set_home_page"
]