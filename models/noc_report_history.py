from odoo import models, fields, api
from odoo.exceptions import ValidationError
import base64
import logging
import requests

_logger = logging.getLogger(__name__)

class NocReportHistory(models.Model):
    _name = 'wifimax.noc.report.history'
    _description = 'Historial de Reportes NOC'
    _order = 'create_date desc'

    name = fields.Char(
        string='Reporte',
        required=True,
        readonly=True,
        default='Nuevo'
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente'
    )

    date_from = fields.Datetime(
        string='Desde'
    )

    date_to = fields.Datetime(
        string='Hasta'
    )

    total_tickets = fields.Integer(
        string='Total de Tickets'
    )

    notes = fields.Html(
        string='Observaciones'
    )

    ticket_ids = fields.Many2many(
        'wifimax.noc.ticket',
        string='Tickets Relacionados'
    )
    
    email_sent = fields.Boolean(
        string='Email Enviado',
        default=False
    )

    email_sent_date = fields.Datetime(
        string='Fecha de Envío'
    )
    
    whatsapp_sent = fields.Boolean(
        string='WhatsApp Enviado',
        default=False
    )

    whatsapp_sent_date = fields.Datetime(
        string='Fecha WhatsApp'
    )

    whatsapp_message_id = fields.Char(
        string='WhatsApp Message ID'
    )

    whatsapp_error = fields.Text(
        string='Error WhatsApp'
    )
    
    pdf_attachment_id = fields.Many2one(
        'ir.attachment',
        string='PDF Generado',
        readonly=True
    )

    @api.model_create_multi
    def create(self, vals_list):

        for vals in vals_list:

            if vals.get('name', 'Nuevo') == 'Nuevo':

                vals['name'] = (
                    self.env['ir.sequence']
                    .next_by_code(
                        'wifimax.noc.report.history'
                    )
                    or 'Nuevo'
                )

        records = super().create(vals_list)

        return records

    def action_export_pdf(self):
        self.ensure_one()

        return self.env.ref('wifimax_noc_ai.action_report_noc_history_pdf').report_action(self)
    
    def action_send_email(self):
        self.ensure_one()

        if not self.partner_id.email:
            raise ValidationError(
                'El cliente no tiene correo electrónico configurado.'
            )

        attachment = self._get_or_create_pdf_attachment()

        template = self.env.ref(
            'wifimax_noc_ai.mail_template_noc_report'
        )

        template.send_mail(
            self.id,
            force_send=True,
            email_values={
                'attachment_ids': [(4, attachment.id)]
            }
        )

        self.write({
            'email_sent': True,
            'email_sent_date': fields.Datetime.now(),
        })
        
    def _generate_pdf(self):
        self.ensure_one()

        report = self.env.ref(
            'wifimax_noc_ai.action_report_noc_history_pdf'
        )

        pdf_content, _ = report._render_qweb_pdf(
            report_ref='wifimax_noc_ai.action_report_noc_history_pdf',
            res_ids=self.ids
        )

        return pdf_content

    def _create_pdf_attachment(self, pdf_content):
        self.ensure_one()

        return self.env['ir.attachment'].create({
            'name': f'{self.name}.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'mimetype': 'application/pdf',
            'res_model': self._name,
            'res_id': self.id,
        })


    def _send_whatsapp_document(self, attachment):
        self.ensure_one()

        config = self.env[
            'wifimax.whatsapp.settings'
        ].search([
            ('active', '=', True),
            ('default_for_noc', '=', True),
        ], limit=1)

        if not config:
            raise ValidationError(
                'No existe una configuración '
                'predeterminada para NOC.'
            )

        if not self.partner_id:
            raise ValidationError(
                'El reporte no tiene cliente asociado.'
            )

        number = (
            self.partner_id.whatsapp_phone
            or self.partner_id.mobile
            or self.partner_id.phone
        )

        if not number:
            raise ValidationError(
                'El cliente no tiene teléfono '
                'o WhatsApp configurado.'
            )

        _logger.info(
            'Enviando reporte WhatsApp a %s',
            number
        )

        pdf_content = base64.b64decode(
            attachment.datas
        )

        result = config.send_document(
            number=number,
            pdf_content=pdf_content,
            file_name=attachment.name,
            caption=self._get_whatsapp_message(),
        )

        return result
        
    def _get_whatsapp_message(self):
        self.ensure_one()

        return (
            f"Estimado cliente,\n\n"
            f"Adjuntamos el reporte NOC {self.name}.\n\n"
            f"Cliente: {self.partner_id.name}\n"
            f"Tickets incluidos: {self.total_tickets}\n\n"
            f"Saludos,\n"
            f"Wifimax NOC"
        )

    def _process_whatsapp_result(self, result):
        if result.get('success'):

            self.write({
                'whatsapp_sent': True,
                'whatsapp_sent_date': fields.Datetime.now(),
                'whatsapp_message_id': result.get(
                    'message_id'
                ),
                'whatsapp_error': False,
            })

        else:

            self.write({
                'whatsapp_error': result.get(
                    'error'
                )
            })


    def action_send_whatsapp(self):
        self.ensure_one()

        attachment = self._get_or_create_pdf_attachment()

        try:
            result = self._send_whatsapp_document(attachment)
        except Exception as e:
            _logger.exception("Error enviando WhatsApp")
            self.write({
                'whatsapp_error': str(e)
            })
            return False

        self._process_whatsapp_result(result)
        
    def _get_or_create_pdf_attachment(self):
        self.ensure_one()

        if self.pdf_attachment_id:
            return self.pdf_attachment_id

        pdf_content = self._generate_pdf()

        attachment = self._create_pdf_attachment(
            pdf_content
        )

        self.write({
            'pdf_attachment_id': attachment.id
        })

        return attachment
    
    def create_pdf_attachment(self):
        self.ensure_one()

        attachment = self._get_or_create_pdf_attachment()

        return attachment
    
    def action_view_pdf(self):
        self.ensure_one()

        if not self.pdf_attachment_id:
            raise ValidationError(
                'Este reporte aún no tiene un PDF asociado.'
            )

        return {
            'type': 'ir.actions.act_url',
            'url': (
                f'/web/content/'
                f'{self.pdf_attachment_id.id}'
                f'?download=false'
            ),
            'target': 'new',
        }
        
    @api.model
    def cron_send_monthly_reports(self):
        """Envía reportes mensuales automáticos el día 1 de cada mes."""
        from datetime import datetime, timedelta
        from dateutil.relativedelta import relativedelta

        today = fields.Datetime.now()

        # Rango del mes anterior
        first_day_current = today.replace(day=1, hour=0, minute=0, second=0)
        first_day_previous = first_day_current - relativedelta(months=1)
        last_day_previous = first_day_current - timedelta(seconds=1)

        # Buscar todos los partners con email o whatsapp
        partners = self.env['res.partner'].sudo().search([
            ('is_business_client', '=', True),
            '|',
            ('email', '!=', False),
            ('whatsapp_phone', '!=', False),
        ])

        _logger.info(
            'CRON MONTHLY REPORT: %s partners',
            len(partners)
        )

        for partner in partners:
            try:
                # Verificar que tenga tickets en el período
                tickets = self.env['wifimax.noc.ticket'].sudo().search([
                    ('partner_id', '=', partner.id),
                    ('detection_date', '>=', first_day_previous),
                    ('detection_date', '<=', last_day_previous),
                ])

                if not tickets:
                    continue

                # Crear historial
                history = self.sudo().create({
                    'partner_id': partner.id,
                    'date_from': first_day_previous,
                    'date_to': last_day_previous,
                    'total_tickets': len(tickets),
                    'ticket_ids': [(6, 0, tickets.ids)],
                })

                # Enviar por email
                if partner.email:
                    try:
                        history.action_send_email()
                        _logger.info(
                            'Reporte email enviado a partner=%s',
                            partner.id,
                        )
                    except Exception:
                        _logger.exception(
                            'Error enviando reporte email a partner=%s',
                            partner.id,
                        )

                # Enviar por WhatsApp
                if partner.whatsapp_phone:
                    try:
                        history.action_send_whatsapp()
                        _logger.info(
                            'Reporte WhatsApp enviado a partner=%s',
                            partner.id,
                        )
                    except Exception:
                        _logger.exception(
                            'Error enviando reporte WhatsApp a partner=%s',
                            partner.id,
                        )

            except Exception:
                _logger.exception(
                    'Error generando reporte para partner=%s',
                    partner.id,
                )