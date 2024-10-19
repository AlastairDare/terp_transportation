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