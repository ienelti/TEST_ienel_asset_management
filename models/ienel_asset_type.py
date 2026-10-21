from odoo import models, fields

class IenelAssetType(models.Model):
    _name = 'ienel.asset.type'
    _description = 'Tipo de Activo'
    _order = 'name'
    
    name = fields.Char(
        string='Nombre del Tipo de Activo',
        required=True
    )