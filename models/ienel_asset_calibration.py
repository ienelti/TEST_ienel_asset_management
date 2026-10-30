import base64
import logging
import os
import re

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class IenelAssetCalibration(models.Model):
    _name = 'ienel.asset.calibration'
    _description = 'Calibración de Activo Fijo'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'asset_id'
    _order = 'calibration_date desc, id desc'

    asset_id = fields.Many2one(
        'ienel.asset',
        string='Activo Fijo',
        required=True,
        ondelete='restrict',
        tracking=True
    )
    calibration_date = fields.Date(
        string='Fecha de Calibración',
        required=True,
        help='Fecha en la cual se realizó la calibración.',
        tracking=True
    )
    next_calibration_date = fields.Date(
        string='Próxima Fecha de Calibración',
        required=True,
        help='Fecha programada para la siguiente calibración.',
        tracking=True
    )
    cost = fields.Float(
        string='Valor',
        required=True,
        digits=(16, 2),
        help='Costo total del servicio de calibración.',
        tracking=True
    )
    # Campos de soporte de documento en OneDrive
    certificate_file = fields.Binary(
        string='Cargar Soporte',
        attachment=False,
        tracking=True
    )
    certificate_filename = fields.Char(string='Nombre del Archivo')
    onedrive_item_id = fields.Char(string='ID OneDrive', readonly=True)
    onedrive_url = fields.Char(string='Enlace OneDrive', readonly=True)
    notes = fields.Text(string='Observaciones')

    @api.depends('asset_id', 'asset_id.code', 'asset_id.name', 'calibration_date')
    def _compute_display_name(self):
        for rec in self:
            asset_ref = rec.asset_id.code or rec.asset_id.name or ''
            if asset_ref and rec.calibration_date:
                date_str = rec.calibration_date.strftime('%d/%m/%Y')
                rec.display_name = f"Calibración - {asset_ref} ({date_str})"
            elif asset_ref:
                rec.display_name = f"Calibración - {asset_ref}"
            else:
                rec.display_name = "Calibración"

    def _normalize_slug(self, text):
        if not text:
            return ''
        text = text.lower().strip()
        replacements = {'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'ñ': 'n', 'ü': 'u'}
        for orig, repl in replacements.items():
            text = text.replace(orig, repl)
        text = re.sub(r'[^a-z0-9\-]', '-', text)
        return re.sub(r'-+', '-', text).strip('-')

    def _compute_standardized_filename(self, asset_code, calibration_date, original_filename):
        code_slug = self._normalize_slug(asset_code or 'activo')
        date_str = calibration_date.strftime('%d%m%y') if calibration_date else '000000'
        ext = os.path.splitext(original_filename or '')[1].lower() or '.pdf'
        return f"cal-{code_slug}-{date_str}{ext}"

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
                    f"Activos Fijos/{rec.asset_id.code.upper()}/Calibraciones"
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
                    _logger.warning("Error eliminando certificado de calibración en OneDrive: %s", str(e))

            if rec.asset_id:
                rec.asset_id.message_post(
                    body=_("Calibración Eliminada: Se eliminó un registro de calibración.")
                )
        return super().unlink()

    def _process_onedrive_upload(self):
        self.ensure_one()
        if not self.asset_id.code:
            raise UserError(_("El activo fijo debe tener un 'Código Único' asignado antes de subir certificados de calibración."))

        std_filename = self._compute_standardized_filename(
            self.asset_id.code,
            self.calibration_date,
            self.certificate_filename
        )
        folder_path = f"Activos Fijos/{self.asset_id.code.upper()}/Calibraciones"
        raw_binary = base64.b64decode(self.certificate_file) if self.certificate_file else b''

        onedrive_service = self.env['onedrive.service']
        res_upload = onedrive_service.upload_file_to_onedrive(
            folder_path=folder_path,
            filename=std_filename,
            binary_content=raw_binary
        )

        self.write({
            'certificate_filename': std_filename,
            'onedrive_item_id': res_upload.get('item_id'),
            'onedrive_url': res_upload.get('web_url'),
            'certificate_file': False,
        })
        self.asset_id.message_post(
            body=_("Certificado de Calibración Cargado: Se adjuntó el soporte %s.") % std_filename
        )

    def action_open_internal_preview(self):
        self.ensure_one()
        if not self.onedrive_item_id:
            raise UserError(_("El certificado no se encuentra cargado en el almacenamiento."))
        return {
            'type': 'ir.actions.act_url',
            'url': f'/ienel_asset/calibration/{self.id}/preview',
            'target': 'new',
        }