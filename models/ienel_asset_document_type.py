import logging
from odoo import models, fields

_logger = logging.getLogger(__name__)

class IenelAssetDocumentType(models.Model):
    _name = 'ienel.asset.document.type'
    _description = 'Tipo de Documento de Activo Fijo'
    _order = 'name asc'
    
    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(
        string='Código / Slug',
        help='Identificador en minúsculas para la nomenclatura de archivos (ej. hoja-de-vida)'
    )
    active = fields.Boolean(default=True)
    
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'El nombre del tipo de documento debe ser único.'),
    ]
    