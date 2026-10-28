import base64
import logging
import os
import re

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class IenelAssetMaintenance(models.Model):
    _name = 'ienel.asset.maintenance'
    _description = 'Mantenimiento de Activo Fijo'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'maintenance_date desc, id desc'

    asset_id = fields.Many2one(
        'ienel.asset',
        string='Activo Fijo',
        required=True,
        ondelete='restrict',
        tracking=True
    )
    maintenance_type = fields.Selection([
        ('preventive', 'Preventivo'),
        ('corrective', 'Correctivo'),
    ], string='Tipo de Mantenimiento', required=True, default='preventive', tracking=True)
    maintenance_date = fields.Date(
        string='Fecha de Mantenimiento',
        required=True,
        help='Fecha en la cual se realizó el mantenimiento.',
        tracking=True
    )
    next_maintenance_date = fields.Date(
        string='Próxima Fecha de Mantenimiento',
        required=True,
        help='Fecha programada para el siguiente mantenimiento.',
        tracking=True
    )
    cost = fields.Float(
        string='Valor',
        required=True,
        digits=(16, 2),
        help='Costo total del servicio de mantenimiento.',
        tracking=True
    )
    # Campos de soporte de documento en OneDrive
    certificate_file = fields.Binary(
        string='Cargar Certificado / Soporte',
        attachment=False,
        tracking=True
    )
    certificate_filename = fields.Char(string='Nombre del Archivo')
    onedrive_item_id = fields.Char(string='ID OneDrive', readonly=True)
    onedrive_url = fields.Char(string='Enlace OneDrive', readonly=True)
    notes = fields.Text(string='Observaciones')

    @api.depends('maintenance_type', 'asset_id', 'asset_id.code', 'asset_id.name', 'maintenance_date')
    def _compute_display_name(self):
        type_dict = dict(self._fields['maintenance_type'].selection)
        for rec in self:
            m_type = type_dict.get(rec.maintenance_type, 'Mantenimiento')
            asset_ref = rec.asset_id.code or rec.asset_id.name or ''
            if asset_ref and rec.maintenance_date:
                date_str = rec.maintenance_date.strftime('%d/%m/%Y')
                rec.display_name = f"{m_type} - {asset_ref} ({date_str})"
            elif asset_ref:
                rec.display_name = f"{m_type} - {asset_ref}"
            else:
                rec.display_name = m_type

    def _normalize_slug(self, text):
        if not text:
            return ''
        text = text.lower().strip()
        replacements = {'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'ñ': 'n', 'ü': 'u'}
        for orig, repl in replacements.items():
            text = text.replace(orig, repl)
        text = re.sub(r'[^a-z0-9\-]', '-', text)
        return re.sub(r'-+', '-', text).strip('-')

    def _compute_standardized_filename(self, maintenance_type, asset_code, maintenance_date, original_filename):
        type_prefix = 'mp' if maintenance_type == 'preventive' else 'mc'
        code_slug = self._normalize_slug(asset_code or 'activo')
        date_str = maintenance_date.strftime('%d%m%y') if maintenance_date else '000000'
        ext = os.path.splitext(original_filename or '')[1].lower() or '.pdf'
        return f"{type_prefix}-{code_slug}-{date_str}{ext}"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.certificate_file:
                rec._process_onedrive_upload()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'certificate_file' in vals and vals['certificate_file']:
            for rec in self:
                rec._process_onedrive_upload()
        return res

    def unlink(self):
        onedrive_service = self.env['onedrive.service']
        for rec in self:
            if rec.onedrive_item_id or (rec.asset_id and rec.certificate_filename):
                folder_path = (
                    f"Activos Fijos/{rec.asset_id.code.upper()}/Mantenimientos"
                    if rec.asset_id and rec.asset_id.code
                    else False
                )
                file_path = f"{folder_path}/{rec.certificate_filename}" if folder_path and rec.certificate_filename else False
                try:
                    onedrive_service.delete_file_from_onedrive(
                        item_id=rec.onedrive_item_id,
                        file_path=file_path
                    )
                except Exception as e:
                    _logger.warning("Error eliminando certificado de mantenimiento en OneDrive: %s", str(e))

            if rec.asset_id:
                m_type_label = dict(self._fields['maintenance_type'].selection).get(rec.maintenance_type)
                rec.asset_id.message_post(
                    body=_("Mantenimiento Eliminado: Se eliminó un registro de mantenimiento de tipo '%s'.") % m_type_label
                )
        return super().unlink()

    def _process_onedrive_upload(self):
        self.ensure_one()
        if not self.asset_id.code:
            raise UserError(_("El activo fijo debe tener un 'Código Único' asignado antes de subir certificados de mantenimiento."))

        std_filename = self._compute_standardized_filename(
            self.maintenance_type,
            self.asset_id.code,
            self.maintenance_date,
            self.certificate_filename
        )
        folder_path = f"Activos Fijos/{self.asset_id.code.upper()}/Mantenimientos"
        raw_binary = base64.b64decode(self.certificate_file) if self.certificate_file else b''

        onedrive_service = self.env['onedrive.service']
        res_upload = onedrive_service.upload_file_to_onedrive(
            folder_path=folder_path,
            filename=std_filename,
            binary_content=raw_binary
        )

        m_type_label = dict(self._fields['maintenance_type'].selection).get(self.maintenance_type)
        self.write({
            'certificate_filename': std_filename,
            'onedrive_item_id': res_upload.get('item_id'),
            'onedrive_url': res_upload.get('web_url'),
            'certificate_file': False,
        })
        self.asset_id.message_post(
            body=_(
                "Certificado de Mantenimiento Cargado: Se adjuntó el soporte %s (%s) en OneDrive."
            ) % (m_type_label, std_filename)
        )

    def action_open_internal_preview(self):
        self.ensure_one()
        if not self.onedrive_item_id:
            raise UserError(_("El certificado no se encuentra cargado en el almacenamiento."))
        return {
            'type': 'ir.actions.act_url',
            'url': f'/ienel_asset/maintenance/{self.id}/preview',
            'target': 'new',
        }