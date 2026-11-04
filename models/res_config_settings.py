from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_asset_alerts = fields.Boolean(
        string="Habilitar Alertas de Mantenimientos y Calibraciones",
        config_parameter='TEST_ienel_asset_management.enable_asset_alerts',
        default=True,
        help="Activa la evaluación diaria automática para generar actividades de alerta."
    )
    alert_days_1 = fields.Integer(
        string="Primera Alerta (Días antes)",
        config_parameter='TEST_ienel_asset_management.alert_days_1',
        default=30,
        help="Número de días de anticipación para la primera alerta."
    )
    alert_days_2 = fields.Integer(
        string="Segunda Alerta (Días antes)",
        config_parameter='TEST_ienel_asset_management.alert_days_2',
        default=15,
        help="Número de días de anticipación para la segunda alerta."
    )
    alert_days_3 = fields.Integer(
        string="Tercera Alerta (Días antes)",
        config_parameter='TEST_ienel_asset_management.alert_days_3',
        default=2,
        help="Número de días de anticipación para la tercera alerta (urgente)."
    )