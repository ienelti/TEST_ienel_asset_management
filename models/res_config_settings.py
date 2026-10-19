from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    uvt_value = fields.Monetary(
        string="Valor de 1 UVT (COP)",
        config_parameter='ienel_asset_management.uvt_value',
        default=49799.0,
        currency_field='currency_id'
    )

    uvt_threshold_qty = fields.Float(
        string="Cantidad de UVT para Umbral Contable",
        config_parameter='ienel_asset_management.uvt_threshold_quantity',
        default=50.0
    )

    uvt_threshold_amount = fields.Monetary(
        string="Monto Total Umbral (COP)",
        compute='_compute_uvt_threshold_amount',
        currency_field='currency_id'
    )

    @api.depends('uvt_value', 'uvt_threshold_qty')
    def _compute_uvt_threshold_amount(self):
        for record in self:
            record.uvt_threshold_amount = (record.uvt_value or 0.0) * (record.uvt_threshold_qty or 0.0)
