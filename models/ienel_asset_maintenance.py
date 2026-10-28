import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

class IenelAssetMaintenance(models.Model):
    _name = 'ienel.asset.maintenance'
    _description = 'Mantenimiento de Activo Fijo'
    _order = 'maintenance_date desc, id desc'
    _rec_name = 'maintenance_type'

    asset_id = fields.Many2one(
        'ienel.asset',
        string='Activo Fijo',
        required=True,
        ondelete='restrict'
    )
    maintenance_type = fields.Selection([
        ('preventive', 'Preventivo'),
        ('corrective', 'Correctivo'),
    ], string='Tipo de Mantenimiento', required=True, default='preventive')
    maintenance_date = fields.Date(
        string='Fecha de Mantenimiento',
        required=True,
        default=fields.Date.context_today,
        help='Fecha en la cual se realizó el mantenimiento.'
    )
    next_maintenance_date = fields.Date(
        string='Próxima Fecha de Mantenimiento',
        required=True,
        help='Fecha programada para el siguiente mantenimiento.'
    )
    cost = fields.Float(
        string='Valor',
        required=True,
        digits=(16, 2),
        help='Costo del servicio de mantenimiento.'
    )
    certificate_file = fields.Binary(
        string='Certificado / Documento Soporte',
        attachment=True,
    )
    certificate_filename = fields.Char(string='Nombre del Archivo')
    notes = fields.Text(string='Observaciones')