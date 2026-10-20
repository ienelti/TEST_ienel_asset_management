from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    uvt_value = fields.Float(
        string='Valor UVT (COP)',
        config_parameter='ienel_asset.uvt_value',
        default=49799.0
    )
    uvt_limit = fields.Float(
        string='Límite UVT para Activos Contables',
        config_parameter='ienel_asset.uvt_limit',
        default=50.0
    )
