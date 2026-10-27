import logging
import re
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

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

    def _sanitize_string(self, text):
        """Normaliza el texto removiendo espacios, minúsculas, tildes y caracteres especiales."""
        if not text:
            return ''
        text = text.lower().strip()
        replacements = {'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'ñ': 'n', 'ü': 'u'}
        for orig, repl in replacements.items():
            text = text.replace(orig, repl)
        text = re.sub(r'[^a-z0-9]', '', text)
        return text

    def _normalize_slug(self, text):
        """Genera un slug estandarizado separado por guiones (ej. hoja-de-vida)."""
        if not text:
            return ''
        text = text.lower().strip()
        replacements = {'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'ñ': 'n', 'ü': 'u'}
        for orig, repl in replacements.items():
            text = text.replace(orig, repl)
        text = re.sub(r'[^a-z0-9\-]', '-', text)
        return re.sub(r'-+', '-', text).strip('-')

    @api.onchange('name')
    def _onchange_name_set_code(self):
        if self.name and not self.code:
            self.code = self._normalize_slug(self.name)

    @api.constrains('name', 'code')
    def _check_duplicate_sanitized(self):
        all_records = self.search([])
        for rec in self:
            if not rec.name:
                continue
            clean_name = rec._sanitize_string(rec.name)
            clean_code = rec._normalize_slug(rec.code or rec.name)
            for other in all_records:
                if other.id == rec.id:
                    continue
                other_clean_name = rec._sanitize_string(other.name)
                other_clean_code = rec._normalize_slug(other.code or other.name)

                # 1. Validar que no exista un Nombre equivalente
                if clean_name and clean_name == other_clean_name:
                    raise ValidationError(_(
                        "Ya existe un Tipo de Documento registrado con un nombre equivalente a '%s' (coincide con '%s')."
                    ) % (rec.name, other.name))

                # 2. Validar que no exista un Código / Slug equivalente
                if clean_code and clean_code == other_clean_code:
                    raise ValidationError(_(
                        "Ya existe un Tipo de Documento con un Código / Slug equivalente a '%s' (coincide con '%s')."
                    ) % (rec.code or clean_code, other.code or other_clean_code))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'name' in vals and not vals.get('code'):
                vals['code'] = self._normalize_slug(vals['name'])
            elif 'code' in vals and vals.get('code'):
                vals['code'] = self._normalize_slug(vals['code'])
        return super().create(vals_list)

    def write(self, vals):
        if 'code' in vals and vals.get('code'):
            vals['code'] = self._normalize_slug(vals['code'])
        elif 'name' in vals and 'code' not in vals:
            for rec in self:
                if not rec.code:
                    vals['code'] = self._normalize_slug(vals['name'])
        return super().write(vals)