from odoo import models, fields, api, _
from odoo.exceptions import UserError

class IenelAssetAssignment(models.Model):
    _name = 'ienel.asset.assignment'
    _description = 'Historial de Pertenencias'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'
    _order = 'start_date desc, id desc'

    asset_id = fields.Many2one(
        'ienel.asset',
        string='Activo Fijo',
        required=True,
        ondelete='restrict',
        tracking=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Persona a cargo',
        required=True,
        tracking=True
    )
    start_date = fields.Date(
        string='Fecha de inicio',
        required=True,
        default=False,
        tracking=True
    )
    end_date = fields.Date(
        string='Fecha fin',
        tracking=True
    )
    comodato_signed = fields.Boolean(
        string='Contrato de Comodato',
        default=False,
        tracking=True
    )
    paz_y_salvo_signed = fields.Boolean(
        string='Paz y Salvo',
        default=False,
        tracking=True
    )
    notes = fields.Text(
        string='Observaciones',
        tracking=True
    )
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('active', 'Activo'),
        ('pending_clearance', 'Pendiente Paz y Salvo'),
        ('closed', 'Terminado'),
    ], string='Estado', default='draft', required=True, tracking=True)

    @api.constrains('asset_id', 'state')
    def _check_single_active_assignment(self):
        for rec in self:
            if rec.state != 'closed':
                other_open = self.search([
                    ('asset_id', '=', rec.asset_id.id),
                    ('id', '!=', rec.id),
                    ('state', '!=', 'closed')
                ])
                if other_open:
                    raise UserError(_(
                        "No se puede registrar una nueva pertenencia para el activo '%s'. "
                        "Existe una pertenencia en proceso con '%s' que debe estar en estado 'Terminado'."
                    ) % (rec.asset_id.display_name, other_open[0].partner_id.name))

    def action_activate(self):
        for rec in self:
            if not rec.start_date:
                raise UserError(_("Debe ingresar la 'Fecha de inicio' para poder asignar la pertenencia."))
            if not rec.comodato_signed:
                raise UserError(_("Debe marcar la casilla 'Contrato de Comodato' como firmado para poder asignar la pertenencia."))
            rec.state = 'active'
            
    def action_request_clearance(self):
        for rec in self:
            rec.state = 'pending_clearance'
    
    def action_reset_draft(self):
        for rec in self:
            rec.state = 'draft'
    
    def action_cancel_clearance(self):
        for rec in self:
            rec.state = 'active'
    
    def action_close(self):
        for rec in self:
            if not rec.end_date:
                raise UserError(_("Debe ingresar la 'Fecha fin' para poder terminar la pertenencia."))
            if not rec.paz_y_salvo_signed:
                raise UserError(_("Debe marcar la casilla 'Paz y Salvo' como firmado para poder terminar la pertenencia."))
            rec.state = 'closed'

    def action_revert_clearance(self):
        for rec in self:
            rec.state = 'pending_clearance'
        
    @api.depends('asset_id', 'asset_id.name', 'asset_id.serial_number')
    def _compute_display_name(self):
        for record in self:
            if record.asset_id:
                asset_name = record.asset_id.name or ''
                if record.asset_id.serial_number:
                    record.display_name = f"{asset_name} [{record.asset_id.serial_number}]"
                else:
                    record.display_name = asset_name
            else: record.display_name = _("Pertenencia")
    
    @api.ondelete(at_uninstall=False)
    def _unlink_prevent_if_processed_or_signed(self):
        for rec in self:
            if rec.state != 'draft' or rec.comodato_signed or rec.paz_y_salvo_signed:
                raise UserError(_(
                    "No se puede eliminar la pertenencia del activo '%s' ya que se encuentra en estado '%s' "
                    "o cuenta con documentos firmados asociados. Para mantener la trazabilidad legal, este registro debe conservarse."
                ) % (rec.asset_id.display_name, dict(self._fields['state'].selection).get(rec.state)))
    