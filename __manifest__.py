{
    "name": "Odoo Access Visualizer",
    "version": "19.0.1.0.0",
    "category": "Administration/Security",
    "summary": "Read-only visualization and analysis of Odoo security configuration",
    "description": """
Odoo Access Visualizer gives administrators an evidence-backed view of users,
groups, implied groups, access controls, record rules, privileges and menus.
It is read-only and uses background snapshots so large databases are not scanned
inside a web request.
    """,
    "author": "NicoOdooV19EE",
    "license": "Other OSI approved licence",
    "depends": ["base", "web"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "views/access_snapshot_views.xml",
        "views/menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "odoo_access_visualizer/static/lib/cytoscape.min.js",
            "odoo_access_visualizer/static/src/js/access_visualizer_api.js",
            "odoo_access_visualizer/static/src/js/graph_renderer.js",
            "odoo_access_visualizer/static/src/js/access_visualizer_action.js",
            "odoo_access_visualizer/static/src/xml/access_visualizer.xml",
            "odoo_access_visualizer/static/src/scss/access_visualizer.scss",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}
