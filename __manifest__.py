{
    'name': 'Wifimax NOC AI',
    'version': '19.0.1.0.0',
    'license': 'LGPL-3',
    'summary': 'Sistema NOC con IA para monitoreo y tickets',
    'author': 'Wifimax',
    'category': 'Operations',

    'depends': [
        'base',
        'mail',
        'web',
        'contacts',
        'base',
    ],

    'data': [

        # SECURITY
        'security/noc_security.xml',
        'security/ir.model.access.csv',
        'security/noc_record_rules.xml',

        # MENUS
        'data/menu.xml',

        # DATA CORE
        'data/noc_sequence.xml',
        'data/noc_report_sequence.xml',
        'data/cron.xml',
        'data/mail_template.xml',
        'data/mail_report_template.xml',
        'views/noc_bonification_views.xml',
        'data/noc_bonification_data.xml',

        # VIEWS
        'views/home_menu_views.xml',
        'views/noc_zone_views.xml',
        'views/noc_business_client_views.xml',
        'views/res_partner_noc_views.xml',
        'views/noc_ticket_views.xml',
        'views/noc_ticket_graph_views.xml',
        'views/noc_ticket_pivot_views.xml',
        'views/noc_report_wizard_views.xml',
        'views/noc_report_history_views.xml',
        'views/whatsapp_settings_views.xml',
                
        # REPORT 
        'report/noc_report_template.xml',
        'report/noc_report.xml',
    ],

    'assets': {
        'web.assets_backend': [

            # 'wifimax_noc_ai/static/src/webclient/home_menu/home_menu.scss',

            'wifimax_noc_ai/static/src/webclient/home_menu/home_menu.js',
            'wifimax_noc_ai/static/src/webclient/home_menu/home_menu.xml',
            'wifimax_noc_ai/static/src/webclient/home_menu/home_menu_action.js',

            'wifimax_noc_ai/static/src/webclient/navbar/navbar.js',
            'wifimax_noc_ai/static/src/webclient/navbar/navbar.xml',
        ],
    },

    'installable': True,
    'application': True,
}