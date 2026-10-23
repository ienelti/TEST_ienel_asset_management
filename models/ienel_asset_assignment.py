from odoo import models, fields, api, _
from odoo.exceptions import UserError

class IenelAssetAssignment(models.Model):
    _name = 'ienel.asset.assignment'
    _description = 'Historial de Pertenencia / Asignación de Activo'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc, id desc'

    asset_id = fields.Many2one(
        'ienel.asset',
        string='Activo Fijo',
        required=True,
        ondelete='cascade',
        tracking=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Persona a cargo',
        required=True,
        tracking=True
    )
    start_date = fields.Date(
        string='Fecha Inicio Asignación',
        default=fields.Date.context_today,
        required=True,
        tracking=True
    )
    end_date = fields.Date(
        string='Fecha Fin / Devolución',
        tracking=True
    )
    state = fields.Selection([
        ('draft', 'Pendiente Comodato'),
        ('active', 'Activo'),
        ('pending_clearance', 'Pendiente Paz y Salvo'),
        ('closed', 'Terminado'),
    ], string='Estado', default='draft', required=True, tracking=True)
    notes = fields.Text(
        string='Observaciones Devolución'
    )

    @api.constrains('asset_id', 'state')
    def _check_single_active_assignment(self):
        for rec in self:
            if rec.state != 'closed':
                open_assignments = self.search([
                    ('asset_id', '=', rec.asset_id.id),
                    ('id', '!=', rec.id),
                    ('state', '!=', 'closed')
                ])
                if open_assignments:
                    raise UserError(_(
                        "No se puede registrar una nueva pertenencia para el activo '%s'. "
                        "Existe una asignación en proceso con '%s' que debe estar en estado 'Concluido'."
                    ) % (rec.asset_id.display_name, open_assignments[0].partner_id.name))

    def action_activate(self):
        for rec in self:
            rec.state = 'active'

    def action_request_clearance(self):
        for rec in self:
            if not rec.end_date:
                rec.end_date = fields.Date.context_today(self)
            rec.state = 'pending_clearance'

    def action_close(self):
        for rec in self:
            if not rec.end_date:
                rec.end_date = fields.Date.context_today(self)
            rec.state = 'closed'