from odoo import models, fields, api

class IenelAsset(models.Model):
    _name = 'ienel.asset'
    _description = 'Activo Fijo'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'code desc, id desc'

    # Identificación y Relación con Inventario
    code = fields.Char(
        string='Código Único',
        required=True,
        tracking=True
    )
    lot_id = fields.Many2one(
        'stock.lot',
        string='Número de serie',
        required=True,
        ondelete='restrict',
        tracking=True
    )
    product_id = fields.Many2one(
        'product.product',
        related='lot_id.product_id',
        string='Producto',
        store=True,
        readonly=True
    )

    # Información del Producto (Relacionados dinámicamente desde el producto y lote)
    name = fields.Char(
        related='lot_id.product_id.name',
        string='Descripción',
        store=True,
        readonly=True
    )
    image = fields.Image(
        related='lot_id.product_id.image_1920',
        string='Imagen',
        tracking=True,
        readonly=True
    )
    brand = fields.Char(
        related='lot_id.product_id.l10n_co_edi_brand',
        string='Marca',
        store=True,
        readonly=True
    )
    reference = fields.Char(
        related='lot_id.product_id.l10n_co_edi_reference',
        string='Referencia',
        store=True,
        readonly=True
    )
    serial_number = fields.Char(
        related='lot_id.name',
        string='Número de Serial',
        store=True,
        readonly=True
    )
    asset_type_id = fields.Many2one(
        'ienel.asset.type',
        string='Tipo de Activo',
        required=True,
        tracking=True
    )
    active = fields.Boolean(
        string='Activo',
        default=True
    )

    # Valores Financieros (Heredados del Producto)
    purchase_value = fields.Float(
        related='lot_id.product_id.standard_price',
        string='Valor',
        store=True,
        readonly=True
    )
    sale_price = fields.Float(
        related='lot_id.product_id.list_price',
        string='Precio de Venta',
        store=True,
        readonly=True
    )

    # Asignación, Pertenencia y Centro de Costos
    analytic_account = fields.Char(
        string='Cuenta analítica',
        required=True,
        tracking=True
    )
    analytic_start_date = fields.Date(
        string='Fecha Inicio de Cuenta Analítica',
        tracking=True
    )
    company_id = fields.Many2one(
        'res.company',
        related='lot_id.company_id',
        string='Compañía a la que pertenece',
        store=True,
        readonly=True
    )
    assignment_ids = fields.One2many(
        'ienel.asset.assignment',
        'asset_id',
        string='Historial de Pertenencias'
    )
    assignment_count = fields.Integer(
        string='Cantidad de Pertenencias',
        compute='_compute_assignment_count'
    )
    person_in_charge_id = fields.Many2one(
        'res.partner',
        string='Persona a cargo',
        compute='_compute_person_in_charge',
        store=True,
        tracking=True
    )
    location_name = fields.Char(
        related='lot_id.location_id.display_name',
        string='Ubicación en Bodega',
        store=True,
        readonly=True
    )

    # Umbral Contable
    requires_accounting_asset = fields.Boolean(
        string='Requiere Activo Contable',
        compute='_compute_requires_accounting_asset',
        store=True
    )

    @api.depends('purchase_value')
    def _compute_requires_accounting_asset(self):
        threshold = 2489950.0
        for record in self:
            record.requires_accounting_asset = bool(
                record.purchase_value and record.purchase_value >= threshold
            )

    @api.depends('assignment_ids', 'assignment_ids.state', 'assignment_ids.partner_id')
    def _compute_person_in_charge(self):
        for record in self:
            active_assignment = record.assignment_ids.filtered(
                lambda a: a.state in ('active', 'pending_clearance')
            )
            record.person_in_charge_id = active_assignment.partner_id if active_assignment else False

    @api.depends('assignment_ids')
    def _compute_assignment_count(self):
        for record in self:
            record.assignment_count = len(record.assignment_ids)

    def action_open_assignments(self):
        self.ensure_one()
        return {
            'name': f'Pertenencias: {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ienel.asset.assignment',
            'view_mode': 'list,form',
            'domain': [('asset_id', '=', self.id)],
            'context': {
                'default_asset_id': self.id,
                'search_default_asset_id': self.id,
            },
        }

    @api.onchange('code')
    def _onchange_uppercase_fields(self):
        if self.code:
            self.code = self.code.upper()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code'):
                vals['code'] = vals['code'].upper()
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('code'):
            vals['code'] = vals['code'].upper()
        return super().write(vals)

    @api.depends('name', 'lot_id', 'lot_id.name')
    def _compute_display_name(self):
        for record in self:
            asset_name = record.name or ''
            serial = record.lot_id.name if record.lot_id else ''
            if serial:
                record.display_name = f"{asset_name} [{serial}]"
            else:
                record.display_name = asset_name
