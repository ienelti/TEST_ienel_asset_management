{
    'name': 'Gestión de Activos Fijos IENEL',
    'version': '19.0.1.0.0',
    'category': 'Operations/Assets',
    'summary': 'Módulo base minimalista para Activos Fijos.',
    'author': 'IENEL',
    'license': 'LGPL-3',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/ienel_asset_views.xml',
        'views/ienel_asset_type_views.xml',
        'views/menu_views.xml',
        ],
    'installable': True,
    'application': True,
}