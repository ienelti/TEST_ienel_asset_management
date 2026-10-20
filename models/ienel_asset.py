from odoo import models, fields

class IenelAsset(models.Model):
    _name = 'ienel.asset'
    _description = 'Activo Fijo'
    
    name = fields.Char(string='Nombre del Activo', required=True)
    code = fields.Char(string='Código Único', default='AF-00001')
    active = fields.Boolean(string='Activo', default=True)