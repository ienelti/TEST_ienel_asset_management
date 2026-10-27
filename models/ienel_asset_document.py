import os
import re
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class IenelAssetDocument(models.Model):
    _name = 'ienel.asset.document'
    _description = 'Documento de Activo Fijo'
    _order = 'doc_type asc, id desc'

    asset_id = fields.Many2one(
        'ienel.asset',
        string='Activo Fijo',
        required=True,
        ondelete='cascade'
    )
    doc_type = fields.Selection([
        ('hoja_de_vida', 'Hoja de Vida'),
        ('ficha_tecnica', 'Ficha Técnica'),
        ('manual', 'Manual'),
    ], string='Tipo de Documento', required=True)
    name = fields.Char(
        string='Nombre del Archivo (Estandarizado)',
        readonly=True,
        store=True
    )
    # Campo temporal para la carga de archivo binario (no se almacena pesado en Odoo)
    file_binary = fields.Binary(
        string='Seleccionar Archivo',
        attachment=False
    )
    file_filename = fields.Char(string='Nombre Original')
    # Metadatos de OneDrive
    onedrive_item_id = fields.Char(string='ID OneDrive', readonly=True)
    onedrive_url = fields.Char(string='Enlace OneDrive', readonly=True)
    # Auditoría
    upload_user_id = fields.Many2one(
        'res.users',
        string='Cargado por',
        default=lambda self: self.env.user,
        readonly=True
    )
    upload_datetime = fields.Datetime(
        string='Fecha y Hora de Carga',
        default=fields.Datetime.now,
        readonly=True
    )

    def _normalize_slug(self, text):
        if not text:
            return ''
        text = text.lower().strip()
        replacements = {'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'ñ': 'n', 'ü': 'u'}
        for orig, repl in replacements.items():
            text = text.replace(orig, repl)
        text = re.sub(r'[^a-z0-9\-]', '-', text)
        return re.sub(r'-+', '-', text).strip('-')

    def _compute_standardized_filename(self, doc_type, asset_code, original_filename):
        type_map = {
            'hoja_de_vida': 'hoja-de-vida',
            'ficha_tecnica': 'ficha-tecnica',
            'manual': 'manual',
        }
        type_slug = type_map.get(doc_type, 'documento')
        code_slug = self._normalize_slug(asset_code or 'activo')
        ext = os.path.splitext(original_filename or '')[1].lower() or '.pdf'
        return f"{type_slug}-{code_slug}{ext}"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.file_binary:
                rec._process_onedrive_upload()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'file_binary' in vals and vals['file_binary']:
            for rec in self:
                rec._process_onedrive_upload()
        return res

    def _process_onedrive_upload(self):
        self.ensure_one()
        if not self.asset_id.code:
            raise UserError(_("El activo fijo debe tener un 'Código Único' asignado antes de subir documentos."))

        # 1. Generar nombre estandarizado
        std_filename = self._compute_standardized_filename(
            self.doc_type,
            self.asset_id.code,
            self.file_filename
        )

        # 2. Definir ruta en OneDrive: Activos Fijos/[CODIGO]
        folder_path = f"Activos Fijos/{self.asset_id.code.upper()}"

        # 3. Subir a OneDrive vía Servicio
        onedrive_service = self.env['onedrive.service']
        res_upload = onedrive_service.upload_file_to_onedrive(
            folder_path=folder_path,
            filename=std_filename,
            binary_content=self.file_binary
        )

        # 4. Actualizar metadatos y registrar en Chatter
        doc_type_label = dict(self._fields['doc_type'].selection).get(self.doc_type)
        self.write({
            'name': std_filename,
            'onedrive_item_id': res_upload.get('item_id'),
            'onedrive_url': res_upload.get('web_url'),
            'upload_user_id': self.env.user.id,
            'upload_datetime': fields.Datetime.now(),
            'file_binary': False,  # Limpiar binario de Odoo para ahorrar espacio en servidor
        })
        self.asset_id.message_post(
            body=_(
                "<b>Documento Actualizado:</b> Se cargó el archivo <b>%s</b> (%s) en OneDrive por %s."
            ) % (doc_type_label, std_filename, self.env.user.name)
        )

    def action_open_onedrive_url(self):
        self.ensure_one()
        if not self.onedrive_url:
            raise UserError(_("El documento no tiene un enlace de OneDrive asociado."))
        return {
            'type': 'ir.actions.act_url',
            'url': self.onedrive_url,
            'target': 'new',
        }
