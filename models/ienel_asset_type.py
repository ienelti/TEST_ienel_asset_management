from odoo import models, fields, api

class IenelAssetType(models.Model):
    _name = 'ienel.asset.type'
    _description = 'Tipo de Activo'
    _order = 'name'
    
    name = fields.Char(
        string='Nombre del Tipo de Activo',
        required=True
    )
    asset_ids = fields.One2many(
        'ienel.asset',
        'asset_type_id',
        string='Activos Fijos'
    )
    asset_count = fields.Integer(
        string='Cantidad de Activos',
        compute='_compute_asset_count'
    )
    
    @api.depends('asset_ids')
    def _compute_asset_count(self):
        for record in self:
            record.asset_count = len(record.asset_ids)
    
    def action_open_assets(self):
        self.ensure_one()
        return {
            'name': f'Activos Fijos: {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ienel.asset',
            'view_mode': 'list,kanban,form',
            'domain': [('asset_type_id', '=', self.id)],
            'context': {'default_asset_type_id': self.id},
        }
