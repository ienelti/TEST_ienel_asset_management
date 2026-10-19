from odoo import fields, models, api, _


class IenelAsset(models.Model):
    _name = 'ienel.asset'
    _description = 'Ficha Maestra de Activo Fijo (IENEL)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc, id desc'

    name = fields.Char(
        string="Código Único",
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('Nuevo'),
        help="Código único interno generado para el almacén."
    )
    image_1920 = fields.Image(
        string="Imagen del Activo",
        max_width=1920,
        max_height=1920
    )
    product_id = fields.Many2one(
        'product.product',
        string="Producto",
        required=True,
        tracking=True
    )
    brand_name = fields.Char(
        string="Marca",
        compute='_compute_product_info',
        store=True,
        readonly=False,
        tracking=True
    )
    product_ref = fields.Char(
        string="Referencia",
        compute='_compute_product_info',
        store=True,
        readonly=False,
        tracking=True
    )
    asset_type_id = fields.Many2one(
        'product.category',
        string="Tipo de Activo / Categoría",
        compute='_compute_product_info',
        store=True,
        readonly=False,
        tracking=True
    )
    list_price = fields.Float(
        string="Precio de Venta",
        compute='_compute_product_info',
        store=True,
        readonly=False
    )
    lot_id = fields.Many2one(
        'stock.lot',
        string="Número de Serie / Lote",
        domain="[('product_id', '=', product_id)]",
        tracking=True
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string="Centro de Costos / Cta. Analítica",
        tracking=True
    )
    analytic_assignment_date = fields.Date(
        string="Fecha Inicio Asignación C. Costo",
        default=fields.Date.context_today
    )
    company_id = fields.Many2one(
        'res.company',
        string="Compañía",
        required=True,
        readonly=True,
        default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string="Persona a Cargo (Empleado)",
        tracking=True
    )
    employee_assignment_date = fields.Date(
        string="Fecha Inicio Asignación Empleado",
        default=fields.Date.context_today
    )
    cost_value = fields.Monetary(
        string="Costo / Valor de Adquisición",
        currency_field='currency_id',
        tracking=True
    )
    location_id = fields.Many2one(
        'stock.location',
        string="Ubicación en Bodega",
        domain="[('usage', '=', 'internal')]",
        tracking=True
    )
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('in_use', 'En Uso / Asignado'),
        ('maintenance', 'En Mantenimiento'),
        ('written_off', 'Dado de Baja')
    ], string="Estado", default='draft', tracking=True)

    notes = fields.Text(string="Notas / Observaciones")
    active = fields.Boolean(string="Activo", default=True)

    uvt_threshold_amount = fields.Monetary(
        string="Monto Umbral UVT",
        compute='_compute_uvt_warning',
        currency_field='currency_id'
    )
    requires_accounting_asset = fields.Boolean(
        string="Requiere Activo Contable",
        compute='_compute_uvt_warning',
        store=True
    )
    uvt_warning_message = fields.Char(
        string="Mensaje de Alerta UVT",
        compute='_compute_uvt_warning'
    )

    @api.depends('product_id')
    def _compute_product_info(self):
        for record in self:
            if record.product_id:
                record.product_ref = record.product_id.default_code or ''
                record.asset_type_id = record.product_id.categ_id.id if record.product_id.categ_id else False
                record.list_price = record.product_id.list_price or 0.0
                brand_val = False
                if hasattr(record.product_id, 'product_brand_id') and record.product_id.product_brand_id:
                    brand_val = record.product_id.product_brand_id.name
                elif hasattr(record.product_id, 'brand_id') and record.product_id.brand_id:
                    brand_val = record.product_id.brand_id.name
                elif hasattr(record.product_id.product_tmpl_id, 'brand') and record.product_id.product_tmpl_id.brand:
                    brand_val = record.product_id.product_tmpl_id.brand
                record.brand_name = brand_val or record.brand_name or ''
            else:
                record.product_ref = False
                record.asset_type_id = False
                record.list_price = 0.0

    @api.depends('cost_value', 'company_id')
    def _compute_uvt_warning(self):
        uvt_val = float(self.env['ir.config_parameter'].sudo().get_param('ienel_asset_management.uvt_value', default=49799.0))
        uvt_qty = float(self.env['ir.config_parameter'].sudo().get_param('ienel_asset_management.uvt_threshold_quantity', default=50.0))
        threshold = uvt_val * uvt_qty

        for record in self:
            record.uvt_threshold_amount = threshold
            if record.cost_value and record.cost_value >= threshold and threshold > 0:
                record.requires_accounting_asset = True
                record.uvt_warning_message = f" El valor del activo ({record.cost_value:,.2f} COP) supera el umbral de {uvt_qty:.0f} UVT ({threshold:,.2f} COP). Se relacionará un activo contable al guardar el registro."
            else:
                record.requires_accounting_asset = False
                record.uvt_warning_message = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nuevo')) == _('Nuevo'):
                vals['name'] = self.env['ir.sequence'].next_by_code('ienel.asset.sequence') or _('Nuevo')
        return super(IenelAsset, self).create(vals_list)
