from odoo import models, fields, api, _


class IenelAsset(models.Model):
    _name = 'ienel.asset'
    _description = 'Activo Fijo'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    code = fields.Char(
        string='Código Único',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nuevo'),
        tracking=True
    )
    name = fields.Char(
        string='Nombre / Descripción',
        required=True,
        tracking=True
    )
    active = fields.Boolean(
        string='Activo',
        default=True
    )
    image = fields.Image(
        string='Imagen'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Producto',
        required=True,
        tracking=True
    )
    brand = fields.Char(
        string='Marca',
        compute='_compute_product_fields',
        store=True,
        readonly=False
    )
    reference = fields.Char(
        string='Referencia',
        compute='_compute_product_fields',
        store=True,
        readonly=False
    )
    product_category_id = fields.Many2one(
        'product.category',
        string='Categoría de Producto',
        related='product_id.categ_id',
        store=True,
        readonly=True
    )
    serial_id = fields.Many2one(
        'stock.lot',
        string='Número de Serie / Lote',
        tracking=True
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Persona a Cargo',
        tracking=True
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Centro de Costos / Cuenta Analítica',
        tracking=True
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Ubicación en Bodega',
        tracking=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        required=True
    )
    purchase_value = fields.Float(
        string='Costo / Valor de Adquisición (COP)',
        tracking=True
    )
    requires_accounting_asset = fields.Boolean(
        string='Requiere Activo Contable',
        compute='_compute_requires_accounting_asset',
        store=True
    )
    notes = fields.Text(
        string='Notas / Observaciones'
    )

    @api.depends('product_id')
    def _compute_product_fields(self):
        for record in self:
            if record.product_id:
                record.brand = getattr(record.product_id, 'product_brand', '') or ''
                record.reference = record.product_id.default_code or ''
            else:
                record.brand = ''
                record.reference = ''

    @api.depends('purchase_value')
    def _compute_requires_accounting_asset(self):
        uvt_value = float(self.env['ir.config_parameter'].sudo().get_param('ienel_asset.uvt_value', default=49799.0))
        uvt_limit = float(self.env['ir.config_parameter'].sudo().get_param('ienel_asset.uvt_limit', default=50.0))
        threshold = uvt_value * uvt_limit
        for record in self:
            record.requires_accounting_asset = bool(record.purchase_value and record.purchase_value >= threshold)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', _('Nuevo')) == _('Nuevo'):
                vals['code'] = self.env['ir.sequence'].next_by_code('ienel.asset.sequence') or _('Nuevo')
        return super().create(vals_list)