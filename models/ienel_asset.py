from odoo import models, fields, api, _

class IenelAsset(models.Model):
    _name = 'ienel.asset'
    _description = 'Activo Fijo'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'code desc, id desc'

    # Identificación
    code = fields.Char(
        string='Código Único',
        default='AF-00001',
        tracking=True
    )
    name = fields.Char(
        string='Nombre / Descripción del Activo',
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
    product_name = fields.Char(
        string='Producto',
        tracking=True
    )
    brand = fields.Char(
        string='Marca',
        tracking=True
    )
    reference = fields.Char(
        string='Referencia',
        tracking=True
    )
    asset_type = fields.Char(
        string='Tipo de Activo / Categoría',
        tracking=True
    )
    sale_price = fields.Float(
        string='Precio de Venta (COP)',
        tracking=True
    )
    serial_number = fields.Char(
        string='Número de Serial',
        tracking=True
    )

    # Asignación, Custodia y Centro de Costos
    analytic_account = fields.Char(
        string='Centro de Costos / Cuenta Analítica',
        tracking=True
    )
    analytic_start_date = fields.Date(
        string='Fecha Inicio Asignación (CC)',
        tracking=True
    )
    company_name = fields.Char(
        string='Compañía a la que Pertenece',
        default='IENEL S.A.S.',
        readonly=True
    )
    person_in_charge = fields.Char(
        string='Persona a Cargo (Empleado)',
        tracking=True
    )
    employee_start_date = fields.Date(
        string='Fecha Inicio Asignación (Persona)',
        tracking=True
    )
    location_name = fields.Char(
        string='Ubicación en Bodega',
        tracking=True
    )

    # Valoración y Leyenda de Umbral Contable
    purchase_value = fields.Float(
        string='Costo / Valor (COP)',
        tracking=True
    )
    requires_accounting_asset = fields.Boolean(
        string='Requiere Activo Contable',
        compute='_compute_requires_accounting_asset',
        store=True
    )

    @api.depends('purchase_value')
    def _compute_requires_accounting_asset(self):
        # Umbral estático de prueba para la alerta visual (ej. 50 UVT ~ 2.489.950 COP)
        threshold = 2489950.0
        for record in self:
            record.requires_accounting_asset = bool(
                record.purchase_value and record.purchase_value >= threshold
            )