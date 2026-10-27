import logging
import mimetypes
import requests

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class IenelAssetDocumentController(http.Controller):

    @http.route('/ienel_asset/document/<int:doc_id>/preview', type='http', auth='user')
    def preview_asset_document(self, doc_id, **kwargs):
        """Descarga el contenido del archivo desde OneDrive y lo sirve de forma interna

        para previsualización en el navegador.
        """
        doc = request.env['ienel.asset.document'].browse(doc_id)
        if not doc.exists() or not doc.onedrive_item_id:
            return request.not_found()

        try:
            # 1. Obtener token de acceso y correo de OneDrive
            onedrive_service = request.env['onedrive.service']
            token = onedrive_service._get_access_token()
            ICPSudo = request.env['ir.config_parameter'].sudo()
            user_email = ICPSudo.get_param('ienel_onedrive_store.drive_id')

            if not user_email:
                return request.not_found()

            # 2. Consultar el contenido del archivo directamente desde Microsoft Graph API
            url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/items/{doc.onedrive_item_id}/content"
            headers = {'Authorization': f'Bearer {token}'}

            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code != 200:
                _logger.error("Error al obtener archivo de OneDrive para previsualización: %s", response.text)
                return request.not_found()

            # 3. Detectar el tipo MIME correcto o usar por defecto application/pdf
            file_content = response.content
            mime_type, _ = mimetypes.guess_type(doc.name or '')
            if not mime_type:
                mime_type = 'application/pdf'

            # 4. Retornar la respuesta HTTP con el contenido binario para vista en línea (inline)
            return request.make_response(
                file_content,
                headers=[
                    ('Content-Type', mime_type),
                    ('Content-Disposition', f'inline; filename="{doc.name or "documento.pdf"}"')
                ]
            )
        except Exception as e:
            _logger.exception("Excepción inesperada al previsualizar documento de OneDrive: %s", str(e))
            return request.not_found()