import base64
import logging
import os
import re

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta

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
        string='Próxima fecha de Calibración',
        compute='_compute_next_calibration_date',
        store=True,
        readonly=True,
        help='Fecha programada automáticamente a 1 año para la siguiente calibración.',
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
    
    @api.depends('calibration_date')
    def _compute_next_calibration_date(self):
        for rec in self:
            if rec.calibration_date:
                rec.next_calibration_date = rec.calibration_date + relativedelta(years=1)
            else:
                rec.next_calibration_date = False
    
    # --- GESTIÓN DE ALERTAS ---
    def _get_default_alert_days(self, param_key, default_val):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        val = ICPSudo.get_param(f'TEST_ienel_asset_management.{param_key}')
        try:
            return int(val) if val is not None and val != '' else default_val
        except (ValueError, TypeError):
            return default_val

    custom_alerts = fields.Boolean(
        string='Personalizar Alertas',
        default=False,
        help='Si se activa, permite definir días de alerta específicos para este registro en lugar de los globales.'
    )
    alert_days_1 = fields.Integer(
        string='1.ª Alerta (Días antes)',
        default=lambda self: self._get_default_alert_days('alert_days_1', 30),
        help='Días de anticipación para la primera alerta.'
    )
    alert_days_2 = fields.Integer(
        string='2.ª Alerta (Días antes)',
        default=lambda self: self._get_default_alert_days('alert_days_2', 15),
        help='Días de anticipación para la segunda alerta.'
    )
    alert_days_3 = fields.Integer(
        string='3.ª Alerta (Días antes)',
        default=lambda self: self._get_default_alert_days('alert_days_3', 2),
        help='Días de anticipación para la tercera alerta (urgente).'
    )

    # Control de alertas emitidas
    alert_1_sent = fields.Boolean(string='Alerta 1 Enviada', default=False)
    alert_2_sent = fields.Boolean(string='Alerta 2 Enviada', default=False)
    alert_3_sent = fields.Boolean(string='Alerta 3 Enviada', default=False)

    @api.onchange('custom_alerts')
    def _onchange_custom_alerts(self):
        if not self.custom_alerts:
            self.alert_days_1 = self._get_default_alert_days('alert_days_1', 30)
            self.alert_days_2 = self._get_default_alert_days('alert_days_2', 15)
            self.alert_days_3 = self._get_default_alert_days('alert_days_3', 2)

    def write(self, vals):
        if 'next_calibration_date' in vals:
            vals.update({
                'alert_1_sent': False,
                'alert_2_sent': False,
                'alert_3_sent': False,
            })
        return super().write(vals)
    
    @api.model
    def _cron_check_alerts(self):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        enabled = ICPSudo.get_param('TEST_ienel_asset_management.enable_asset_alerts', 'True')
        if str(enabled).lower() not in ('true', '1', 't'):
            return

        today = fields.Date.today()
        records = self.search([('next_calibration_date', '!=', False)])

        group_manager = self.env.ref('TEST_ienel_asset_management.group_ienel_asset_manager', raise_if_not_found=False)
        group_admin = self.env.ref('TEST_ienel_asset_management.group_ienel_asset_admin', raise_if_not_found=False)

        group_ids = []
        if group_manager:
            group_ids.append(group_manager.id)
        if group_admin:
            group_ids.append(group_admin.id)

        if not group_ids:
            return

        recipients = self.env['res.users'].search([
            ('groups_id', 'in', group_ids),
            ('active', '=', True)
        ])
        if not recipients:
            return

        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        activity_type_id = activity_type.id if activity_type else False

        for rec in records:
            delta_days = (rec.next_calibration_date - today).days
            d1 = rec.alert_days_1 if rec.custom_alerts else int(ICPSudo.get_param('TEST_ienel_asset_management.alert_days_1', 30) or 30)
            d2 = rec.alert_days_2 if rec.custom_alerts else int(ICPSudo.get_param('TEST_ienel_asset_management.alert_days_2', 15) or 15)
            d3 = rec.alert_days_3 if rec.custom_alerts else int(ICPSudo.get_param('TEST_ienel_asset_management.alert_days_3', 2) or 2)

            alerts_to_trigger = []
            if delta_days <= d1 and not rec.alert_1_sent:
                alerts_to_trigger.append(('1_sent', d1, "1.ª Alerta"))
            if delta_days <= d2 and not rec.alert_2_sent:
                alerts_to_trigger.append(('2_sent', d2, "2.ª Alerta"))
            if delta_days <= d3 and not rec.alert_3_sent:
                alerts_to_trigger.append(('3_sent', d3, "3.ª Alerta (Urgente)"))

            for sent_attr, days_val, label in alerts_to_trigger:
                asset_name = rec.asset_id.name if rec.asset_id else ''
                summary = f"Calibración Próxima ({label}): {asset_name}"
                note = (
                    f"La calibración del activo {asset_name} "
                    f"está programada para el {rec.next_calibration_date} "
                    f"(faltan {delta_days} días)."
                )
                for user in recipients:
                    self.env['mail.activity'].create({
                        'activity_type_id': activity_type_id,
                        'summary': summary,
                        'note': note,
                        'res_id': rec.id,
                        'res_model_id': self.env['ir.model']._get_id('ienel.asset.calibration'),
                        'user_id': user.id,
                        'date_deadline': rec.next_calibration_date,
                    })
                rec.message_post(body=f"🔔 {label} enviada: {note}")
                setattr(rec, f'alert_{sent_attr}', True)
