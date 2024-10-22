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
        "name": "Fleet Manager",
        "icon": "fleet",
        "module": "Transportation",
        "type": "page",
        "link": "fleet_manager",
        "label": "Fleet Manager"
    },
    {
        "name": "Driver Manager",
        "icon": "users",
        "module": "Transportation",
        "type": "page",
        "link": "driver_manager",
        "label": "Driver Manager"
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

website_route_rules = [
    {"from_route": "/trip-capture", "to_route": "www/trip_capture"}
]


