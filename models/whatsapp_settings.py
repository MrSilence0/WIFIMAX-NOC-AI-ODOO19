import base64
from odoo import models, fields, _, api
from odoo.exceptions import ValidationError
import requests

class WhatsappSettings(models.Model):
    _name = 'wifimax.whatsapp.settings'
    _description = 'Configuración WhatsApp'

    # =====================================================
    # GENERALES
    # =====================================================

    name = fields.Char(
        string='Nombre',
        required=True,
        default='WhatsApp Principal'
    )

    active = fields.Boolean(
        default=True
    )

    default_for_noc = fields.Boolean(
        string='Predeterminado para NOC'
    )

    default_for_tickets = fields.Boolean(
        string='Predeterminado para Tickets'
    )

    provider = fields.Selection(
        [
            ('meta', 'Meta Cloud API'),
            ('twilio', 'Twilio'),
            ('evolution', 'Evolution API'),
        ],
        string='Proveedor',
        required=True,
        default='meta'
    )

    # =====================================================
    # META CLOUD API
    # =====================================================

    access_token = fields.Text(
        string='Access Token'
    )

    phone_number_id = fields.Char(
        string='Phone Number ID'
    )

    whatsapp_business_account_id = fields.Char(
        string='WABA ID'
    )

    # =====================================================
    # EVOLUTION API
    # =====================================================

    evolution_url = fields.Char(
        string='Evolution URL'
    )

    evolution_instance = fields.Char(
        string='Instancia'
    )

    evolution_api_key = fields.Char(
        string='API Key',
        groups='base.group_system'
    )

    # =====================================================
    # ALERTAS GRUPO
    # =====================================================

    zabbix_group_id = fields.Char(
        string='Grupo WhatsApp Alertas Zabbix',
        help='Grupo donde se enviarán todas las alertas y recuperaciones provenientes de Zabbix.'
    )
    
    # =====================================================
    # NUMERO DE PRUEBA
    # =====================================================    
    
    test_phone = fields.Char(
        string='Número de prueba',
        help='Número para el botón Enviar Mensaje Prueba. Formato: 521XXXXXXXXXX'
    )
    # =====================================================
    # CONSTRAINTS
    # =====================================================

    @api.constrains(
        'default_for_noc',
        'default_for_tickets',
        'active'
    )

    def _check_defaults(self):
        for record in self:

            if record.default_for_noc:
                count = self.search_count([
                    ('id', '!=', record.id),
                    ('active', '=', True),
                    ('default_for_noc', '=', True),
                ])

                if count:
                    raise ValidationError(
                        _('Ya existe una configuración predeterminada para NOC.')
                    )

            if record.default_for_tickets:
                count = self.search_count([
                    ('id', '!=', record.id),
                    ('active', '=', True),
                    ('default_for_tickets', '=', True),
                ])

                if count:
                    raise ValidationError(
                        _('Ya existe una configuración predeterminada para Tickets.')
                    )

    # =====================================================
    # VALIDACIÓN
    # =====================================================
    
    def _validate_evolution_config(self):
        self.ensure_one()

        if not self.evolution_url:
            raise ValidationError(
                _('Debe capturar la URL de Evolution API.')
            )

        if not self.evolution_url.startswith(
            ('http://', 'https://')
        ):
            raise ValidationError(
                _('La URL debe iniciar con http:// o https://')
            )

        if not self.evolution_instance:
            raise ValidationError(
                _('Debe capturar la instancia.')
            )

        if not self.evolution_api_key:
            raise ValidationError(
                _('Debe capturar la API Key.')
            )

    # =====================================================
    # TEST DE CONEXIÓN
    # =====================================================

    def action_test_connection(self):
        self.ensure_one()
        if self.provider == 'meta':
            if not self.access_token:
                raise ValidationError(
                    _('Debe capturar el Access Token.')
                )

            if not self.phone_number_id:
                raise ValidationError(
                    _('Debe capturar el Phone Number ID.')

                )

        elif self.provider == 'evolution':
            self._validate_evolution_config()

            try:
                response = requests.get(
                    self.evolution_url,
                    headers={
                        'apikey': self.evolution_api_key,
                    },
                    timeout=30
                )

                if response.status_code not in (200, 201):
                    raise ValidationError(
                        _(
                            'Evolution API respondió con código %s'
                        ) % response.status_code
                    )

            except requests.exceptions.RequestException as e:
                
                raise ValidationError(
                    _(
                        'No fue posible conectar con Evolution API:\n%s'
                    ) % str(e)
                )

        elif self.provider == 'twilio':

            raise ValidationError(
                _('Twilio aún no está implementado.')
            )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('WhatsApp'),
                'message': _('Conexión exitosa.'),
                'type': 'success',
            }
        }

    # =====================================================
    # MÉTODO GENÉRICO
    # =====================================================

    def send_message(self, number, text):
        self.ensure_one()

        if self.provider == 'evolution':
            return self.send_evolution_message(
                number=number,
                text=text,
            )

        if self.provider == 'meta':
            return self.send_meta_message(
                number=number,
                text=text,
            )

        if self.provider == 'twilio':
            return self.send_twilio_message(
                number=number,
                text=text,
            )

        raise ValidationError(
            _('Proveedor no soportado.')
        ) 

    # =====================================================
    # DOCUMENTOS
    # =====================================================

    def send_document(
        self,
        number,
        pdf_content,
        file_name,
        caption=''
    ):
        self.ensure_one()
        
        if self.provider == 'evolution':
            return self.send_evolution_document(
                number=number,
                pdf_content=pdf_content,
                file_name=file_name,
                caption=caption,
            )

        if self.provider == 'meta':
            return self.send_meta_document(
                number=number,
                pdf_content=pdf_content,
                file_name=file_name,
                caption=caption,
            )

        if self.provider == 'twilio':
            return self.send_twilio_document(
                number=number,
                pdf_content=pdf_content,
                file_name=file_name,
                caption=caption,
            )

        raise ValidationError(
            _('Proveedor no soportado.')
        )

    # =====================================================
    # PROCESAMIENTO DE RESULTADOS
    # =====================================================

    def send_text(
        self,
        number,
        message,
    ):
        self.ensure_one()

        if self.provider == 'evolution':
            return self._evolution_send_text(
                number,
                message,
            )

        elif self.provider == 'meta':
            return self._meta_send_text(
                number,
                message,
            )
        elif self.provider == 'twilio':
            return self._twilio_send_text(
                number,
                message,
            )
        raise ValidationError(
            f'Proveedor no soportado: {self.provider}'
        )
        
    # =====================================================
    # EVOLUTION API
    # =====================================================

    def send_evolution_message(self, number, text):
        self.ensure_one()
        self._validate_evolution_config()
        url = (
            f"{self.evolution_url}"
            f"/message/sendText/"
            f"{self.evolution_instance}"
        )

        headers = {
            'apikey': self.evolution_api_key,
            'Content-Type': 'application/json',
        }
        payload = {
            'number': number,
            'text': text,
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=30,
            )
            
            if response.status_code >= 400:
                raise ValidationError(
                    _(
                        'Evolution API respondió:\n%s'
                    ) % response.text
                )
                
            data = response.json()
            return {
                'success': True,
                'message_id': data.get('key', {}).get('id'),
                'response': data,
            }

        except requests.exceptions.RequestException as e:
            raise ValidationError(
                _(

                    'Error al enviar mensaje:\n%s'
                ) % str(e)
            )

    # =====================================================
    # PLACEHOLDERS FUTUROS
    # =====================================================

    def send_meta_message(self, number, text):
        raise ValidationError(
            _('Meta Cloud API aún no implementado.')
        )
        
    def send_twilio_message(self, number, text):
        raise ValidationError(
            _('Twilio aún no implementado.')
        )

    def send_meta_document(
        self,
        number,
        pdf_content,
        file_name,
        caption=''
    ):
        raise ValidationError(
            _('Meta Cloud API aún no implementado.')
        )

    def send_twilio_document(
        self,
        number,
        pdf_content,
        file_name,
        caption=''
    ):
        raise ValidationError(
            _('Twilio aún no implementado.')
        )
        
    # =====================================================
    # BOTÓN DE PRUEBA 
    # =====================================================

    def action_send_test_message(self):
        self.ensure_one()
        if not self.test_phone:
            raise ValidationError(
                _('Configure un número de prueba en el formulario.')
            )
        self.send_message(
            number=self.test_phone,
            text='✅ Prueba enviada desde Odoo NOC Wifimax'
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('WhatsApp'),
                'message': _('Mensaje enviado correctamente.'),
                'type': 'success',
            }
        }

    # =====================================================
    # EVOLUTION DOCUMENT
    #-=====================================================

    def send_evolution_document(
        self,
        number,
        pdf_content,
        file_name,
        caption=''
    ):
        self.ensure_one()
        self._validate_evolution_config()

        url = (

            f"{self.evolution_url}"
            f"/message/sendMedia/"
            f"{self.evolution_instance}"
        )

        pdf_base64 = (
            base64.b64encode(pdf_content)
            .decode('utf-8')
        )

        headers = {
            'apikey': self.evolution_api_key,
            'Content-Type': 'application/json',
        }

        payload = {
            'number': number,
            'mediatype': 'document',
            'mimetype': 'application/pdf',
            'fileName': file_name,
            'caption': caption,
            'media': pdf_base64,
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=120,
            )

            if response.status_code >= 400:
                raise ValidationError(
                    _(
                        'Evolution API respondió:\n%s'
                    ) % response.text
                )
            data = response.json()

            return {
                'success': True,
                'message_id': (
                    data.get('key', {})
                    .get('id')
                ),
                'response': data,
            }
            
        except requests.exceptions.RequestException as e:
            raise ValidationError(
                _(
                    'Error enviando documento:\n%s'
                ) % str(e)
            )
            
    # =====================================================
    # OLLAMA - CONFIGURACIÓN DE IA
    # =====================================================

    ollama_host = fields.Char(
        string='Ollama Host',
        help='URL del servidor Ollama. Ej: http://148.224.32.130:8090'
    )

    ollama_model = fields.Char(
        string='Modelo Ollama',
        default='qwen2.5-coder:32b',
        help='Modelo a usar para diagnóstico. Ej: qwen2.5-coder:32b'
    )

    # =====================================================
    # TEST OLLAMA CONNECTION
    # =====================================================

    def action_test_ollama_connection(self):
        """Probar conexión a Ollama"""
        self.ensure_one()

        if not self.ollama_host:
            raise ValidationError(
                _('No hay configurado un host de Ollama')
            )

        try:
            # Test: Conectar a Ollama
            url = f"{self.ollama_host}/api/tags"
            response = requests.get(
                url,
                timeout=5
            )
            response.raise_for_status()

            data = response.json()
            models = data.get('models', [])
            model_names = [m['name'] for m in models]

            # Construir mensaje
            msg = f"CONEXIÓN EXITOSA\n\n"
            msg += f"Host: {self.ollama_host}\n"
            msg += f"Modelos instalados: {len(models)}\n\n"
            for name in model_names:
                msg += f"  • {name}\n"

            if self.ollama_model and self.ollama_model not in model_names:
                msg += f"\nModelo configurado '{self.ollama_model}' NO está instalado"

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Ollama Conectado',
                    'message': msg,
                    'type': 'success',
                    'sticky': True,
                }
            }

        except requests.exceptions.ConnectionError:
            raise ValidationError(
                _(
                    'NO SE PUEDE CONECTAR A OLLAMA\n\n'
                    'Host: %s\n\n'
                    'Soluciones:\n'
                    '1. Verificar Ollama: sudo systemctl status ollama\n'
                    '2. Reiniciar: sudo systemctl restart ollama\n'
                    '3. Ver logs: sudo journalctl -u ollama -n 20'
                ) % self.ollama_host
            )

        except requests.exceptions.Timeout:
            raise ValidationError(
                _('TIMEOUT: Ollama tardó más de 5 segundos en responder')
            )

        except Exception as e:
            raise ValidationError(
                _('ERROR: %s') % str(e)
            )