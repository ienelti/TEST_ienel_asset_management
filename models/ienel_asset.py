from odoo import models, fields, api

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
        string='Compañía a la que pertenece',
        default=lambda self: self.env.company,
        required=True,
        tracking=True
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
    
    @api.depends('assignment_ids', 'assignment_ids.state', 'assignment_ids.partner_id')
    def _compute_person_in_charge(self):
        for record in self:
            active_assignment = record.assignment_ids.filtered(lambda a: a.state in ('draft', 'active', 'pending_clearance'))
            record.person_in_charge_id = active_assignment[0].partner_id if active_assignment else False
    
    @api.depends('assignment_ids')
    def _compute_assignment_count(self):
        for record in self:
            record.assignment_count = len(record.assignment_ids)
    
    def action_open_assignments(self):
        self.ensure_one()
        return {
            'name': f'Historial de Pertenencias: {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ienel.asset.assignment',
            'view_mode': 'list,form',
            'domain': [('asset_id', '=', self.id)],
            'context': {
                'default_asset_id': self.id,
            },
        }