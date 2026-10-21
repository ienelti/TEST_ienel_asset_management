from odoo import models, fields, api, _

class IenelAsset(models.Model):
    _name = 'ienel.asset'
    _description = 'Activo Fijo'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'code desc, id desc'

    # Identificación
    code = fields.Char(
        string='Código Único',
        required=True,
        tracking=True
    )
    name = fields.Char(
        string='Descripción',
        required=True,
        tracking=True
    )
    image = fields.Image(
        string='Imagen'
    )
    active = fields.Boolean(
        string='Activo',
        default=True
    )

    # Información del Producto
    brand = fields.Char(
        string='Marca',
        required=True,
        tracking=True
    )
    reference = fields.Char(
        string='Referencia',
        required=True,
        tracking=True
    )
    asset_type_id = fields.Many2one(
        'ienel.asset.type',
        string='Tipo de Activo',
        required=True,
        tracking=True
    )
    sale_price = fields.Float(
        string='Precio de Venta',
        tracking=True
    )
    serial_number = fields.Char(
        string='Número de Serial',
        required=True,
        tracking=True
    )

    # Asignación, Custodia y Centro de Costos
    analytic_account = fields.Char(
        string='Cuenta analítica',
        required=True,
        tracking=True
    )
    analytic_start_date = fields.Date(
        string='Fecha Inicio de Cuenta Analítica',
        tracking=True
    )
    company_name = fields.Char(
        string='Compañía a la que pertenece',
        default='IENEL S.A.S.',
        required=True
    )
    person_in_charge = fields.Char(
        string='Persona a cargo',
        tracking=True
    )
    employee_start_date = fields.Date(
        string='Fecha Asignación de Persona',
        tracking=True
    )
    location_name = fields.Char(
        string='Ubicación en Bodega',
        tracking=True
    )

    # Valoración y Umbral Contable
    purchase_value = fields.Float(
        string='Costo / Valor',
        required=True,
        tracking=True
    )
    requires_accounting_asset = fields.Boolean(
        string='Requiere Activo Contable',
        compute='_compute_requires_accounting_asset',
        store=True
    )

    @api.depends('purchase_value')
    def _compute_requires_accounting_asset(self):
        # Umbral estático de prueba para la alerta visual (50 UVT ~ 2.489.950 COP)
        threshold = 2489950.0
        for record in self:
            record.requires_accounting_asset = bool(
                record.purchase_value and record.purchase_value >= threshold
            )