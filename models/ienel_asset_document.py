import base64
import logging
import os
import re
from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class IenelAssetDocument(models.Model):
    _name = 'ienel.asset.document'
    _description = 'Documento de Activo Fijo'
    _order = 'id desc'

    asset_id = fields.Many2one(
        'ienel.asset',
        string='Activo Fijo',
        required=True,
        ondelete='cascade'
    )
    doc_type_id = fields.Many2one(
        'ienel.asset.document.type',
        string='Tipo de Documento',
        required=True,
        ondelete='restrict'
    )
    # Campo técnico para filtrar dinámicamente los tipos no registrados aún en este activo
    available_doc_type_ids = fields.Many2many(
        'ienel.asset.document.type',
        compute='_compute_available_doc_type_ids',
        string='Tipos Disponibles'
    )
    name = fields.Char(
        string='Nombre del Archivo (Estandarizado)',
        readonly=True,
        store=True
    )
    file_binary = fields.Binary(
        string='Seleccionar Archivo',
        attachment=False
    )
    file_filename = fields.Char(string='Nombre Original')
    
    onedrive_item_id = fields.Char(string='ID OneDrive', readonly=True)
    onedrive_url = fields.Char(string='Enlace OneDrive', readonly=True)
    
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

    _sql_constraints = [
        ('asset_doc_type_uniq', 'unique(asset_id, doc_type_id)', 'Ya existe un documento de este tipo cargado para este activo fijo.'),
    ]

    @api.depends('asset_id', 'asset_id.document_ids.doc_type_id')
    def _compute_available_doc_type_ids(self):
        all_types = self.env['ienel.asset.document.type'].search([])
        for rec in self:
            if rec.asset_id:
                # Excluir los tipos que ya han sido asignados a otros documentos de este activo
                used_types = rec.asset_id.document_ids.filtered(lambda d: d.id != rec.id).mapped('doc_type_id')
                rec.available_doc_type_ids = all_types - used_types
            else:
                rec.available_doc_type_ids = all_types

    def _normalize_slug(self, text):
        if not text:
            return ''
        text = text.lower().strip()
        replacements = {'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'ñ': 'n', 'ü': 'u'}
        for orig, repl in replacements.items():
            text = text.replace(orig, repl)
        text = re.sub(r'[^a-z0-9\-]', '-', text)
        return re.sub(r'-+', '-', text).strip('-')

    def _compute_standardized_filename(self, doc_type_record, asset_code, original_filename):
        type_slug = self._normalize_slug(doc_type_record.code or doc_type_record.name) or 'documento'
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

    def unlink(self):
        onedrive_service = self.env['onedrive.service']
        for rec in self:
            folder_path = (
                f"Activos Fijos/{rec.asset_id.code.upper()}"
                if rec.asset_id and rec.asset_id.code
                else False
            )
            file_path = f"{folder_path}/{rec.name}" if folder_path and rec.name else False
            onedrive_service.delete_file_from_onedrive(
                item_id=rec.onedrive_item_id,
                file_path=file_path
            )
            if rec.asset_id:
                doc_type_label = rec.doc_type_id.name if rec.doc_type_id else 'Documento'
                rec.asset_id.message_post(
                    body=_(
                        "Documento Eliminado: Se eliminó el documento %s (%s) por %s."
                    ) % (doc_type_label, rec.name or '', self.env.user.name)
                )
        return super().unlink()

    def _process_onedrive_upload(self):
        self.ensure_one()
        if not self.asset_id.code:
            raise UserError(_("El activo fijo debe tener un 'Código Único' asignado antes de subir documentos."))

        std_filename = self._compute_standardized_filename(
            self.doc_type_id,
            self.asset_id.code,
            self.file_filename
        )
        folder_path = f"Activos Fijos/{self.asset_id.code.upper()}"
        raw_binary = base64.b64decode(self.file_binary) if self.file_binary else b''

        onedrive_service = self.env['onedrive.service']
        res_upload = onedrive_service.upload_file_to_onedrive(
            folder_path=folder_path,
            filename=std_filename,
            binary_content=raw_binary
        )

        doc_type_label = self.doc_type_id.name
        self.write({
            'name': std_filename,
            'onedrive_item_id': res_upload.get('item_id'),
            'onedrive_url': res_upload.get('web_url'),
            'upload_user_id': self.env.user.id,
            'upload_datetime': fields.Datetime.now(),
            'file_binary': False,
        })
        self.asset_id.message_post(
            body=_(
                "Documento Actualizado: Se cargó el archivo %s (%s) por %s."
            ) % (doc_type_label, std_filename, self.env.user.name)
        )

    def action_open_internal_preview(self):
        self.ensure_one()
        if not self.onedrive_item_id:
            raise UserError(_("El documento no se encuentra cargado en el almacenamiento."))
        return {
            'type': 'ir.actions.act_url',
            'url': f'/ienel_asset/document/{self.id}/preview',
            'target': 'new',
        }
        