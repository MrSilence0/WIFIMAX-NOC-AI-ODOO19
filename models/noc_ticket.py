from datetime import timedelta
from odoo import models, fields, api
import logging
from string import Template
from ..services.whatsapp_alert_service import WhatsAppAlertService


_logger = logging.getLogger(__name__)


class NocTicket(models.Model):
    _name = 'wifimax.noc.ticket'
    _description = 'NOC Ticket'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # =========================
    # BASIC INFO
    # =========================

    name = fields.Char(
        string='Ticket',
        required=True,
        copy=False,
        readonly=True,
        default='Nuevo',
        tracking=True
    )

    description = fields.Text(
        string='Descripción'
    )

    status = fields.Selection(
        [
            ('1_new', 'Nuevo'),
            ('2_progress', 'En Progreso'),
            ('3_done', 'Resuelto')
        ],
        default='1_new',
        string='Estado',
        tracking=True
    )

    priority = fields.Selection(
        [
            ('low', 'Baja'),
            ('medium', 'Media'),
            ('high', 'Alta')
        ],
        default='medium',
        string='Prioridad',
        tracking=True
    )

    zabbix_severity = fields.Selection(
        [
            ('urgent', 'Urgente'),
            ('attention', 'Revisar'),
            ('normal', 'Normal')
        ],
        string='Severidad Zabbix',
        readonly=True
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Contacto',
        domain="[('parent_id','=',partner_id)]",
        tracking=True
    )

    assigned_user_id = fields.Many2one(
        'res.users',
        string='Técnico Asignado',
        tracking=True
    )

    device_ip = fields.Char(
        string='IP Equipo'
    )

    address = fields.Char(
        string='Dirección',
        help='Dirección física donde se ubica el equipo, copiada del cliente'
    )

    map_url = fields.Char(
        string='Ubicación (Maps)',
        help='Link de Google Maps copiado del cliente'
    )

    # =========================
    # DATES
    # =========================

    detection_date = fields.Datetime(
        string='Fecha Detección',
        default=fields.Datetime.now,
        tracking=True
    )

    close_date = fields.Datetime(
        string='Fecha Resolución',
        tracking=True
    )

    sla_deadline = fields.Datetime(
        string='Fecha Límite SLA',
        compute='_compute_sla_deadline',
        store=True,
        tracking=True
    )

    sla_hours = fields.Float(
        string='Horas Resolución',
        compute='_compute_sla_hours',
        store=True
    )

    # =========================
    # SLA
    # =========================

    sla_status = fields.Selection(
        [
            ('ok', 'Dentro SLA'),
            ('warning', 'Por vencer'),
            ('expired', 'Vencido')
        ],
        string='Estado SLA',
        compute='_compute_sla_status',
        store=True
    )

    # =========================
    # STATS
    # =========================

    ticket_count = fields.Integer(
        string='Tickets',
        default=1
    )

    # =========================
    # DATA FROM ZABBIX
    # ========================

    event_id = fields.Char(
        string='Event ID'
    )

    host_name = fields.Char(
        string='Host'
    )

    trigger_name = fields.Char(
        string='Trigger'
    )

    event_date = fields.Datetime(
        string='Fecha Evento'
    )

    # =========================
    # WHATSAPP NOTIFICATIONS
    # ========================
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

    whatsapp_notified = fields.Boolean(
        string='Notificado por WhatsApp',
        default=False
    )

    # =========================
    # Incidente
    # =========================

    incident_id = fields.Many2one(
        'wifimax.noc.incident',
        string='Incidente'
    )
    
    # =========================
    # Acciones IA
    # =========================
        
    action_request_ids = fields.One2many(
        'wifimax.noc.action.request',
        'ticket_id',
        string='Acciones IA',
    )

    # =========================
    # SLA DEADLINE
    # =========================

    @api.depends('priority', 'zabbix_severity', 'detection_date')
    def _compute_sla_deadline(self):
        for rec in self:
            base_date = rec.detection_date or fields.Datetime.now()

            hours_by_priority = {
                'high': 1,
                'medium': 4,
                'low': 8,
            }.get(rec.priority, 4)

            hours_by_severity = {
                'urgent': 2,
                'attention': 6,
                'normal': 24,
            }.get(rec.zabbix_severity, 24)

            # Regla más estricta — la que dé menos horas
            hours = min(hours_by_priority, hours_by_severity)

            rec.sla_deadline = base_date + timedelta(hours=hours)

    # =========================
    # SLA STATUS
    # =========================

    @api.depends('sla_deadline')
    def _compute_sla_status(self):
        now = fields.Datetime.now()

        for rec in self:
            if not rec.sla_deadline:
                rec.sla_status = 'ok'
                continue

            hours_left = (rec.sla_deadline - now).total_seconds() / 3600

            if hours_left <= 0:
                rec.sla_status = 'expired'
            elif hours_left <= 1:
                rec.sla_status = 'warning'
            else:
                rec.sla_status = 'ok'

    # =========================
    # ACTIONS
    # =========================

    def action_start_progress(self):

        self.status = '2_progress'

    def action_done(self):

        self.status = '3_done'

        self.close_date = fields.Datetime.now()

        template = self.env.ref(
            'wifimax_noc_ai.email_template_noc_ticket_done',
            raise_if_not_found=False
        )

        if template and self.partner_id.email:

            template.send_mail(
                self.id,
                force_send=True
            )

    def action_reset(self):

        self.status = '1_new'

    # =========================
    # CREATE
    # =========================

    @api.model_create_multi
    def create(self, vals_list):

        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = (
                    self.env['ir.sequence']
                    .next_by_code('wifimax.noc.ticket')
                    or 'NOC-0000'
                )

        records = super().create(vals_list)

        # EMAIL (seguro)
        template = self.env.ref(
            'wifimax_noc_ai.email_template_noc_ticket_created',
            raise_if_not_found=False
        )

        if template:
            for rec in records:
                if rec.partner_id.email:
                    try:
                        template.send_mail(rec.id, force_send=True)
                    except Exception:
                        _logger.exception('Error enviando email')

        # WHATSAPP (CORREGIDO - SOLO UNA VEZ)
        for rec in records:
            try:
                rec._send_ticket_to_technician_whatsapp()
            except Exception:
                _logger.exception("Error enviando WhatsApp en create")

        return records

    # =========================
    # WRITE
    # =========================

    def write(self, vals):

        old_technicians = {
            rec.id: rec.assigned_user_id.id
            for rec in self
        }

        closing = vals.get('status') == '3_done'
        to_notify = (
            self.filtered(lambda t: t.status != '3_done')
            if closing else self.browse()
        )

        result = super().write(vals)

        if 'assigned_user_id' in vals:
            for rec in self:
                old = old_technicians.get(rec.id)
                new = rec.assigned_user_id.id
                if old != new:
                    try:
                        rec.sudo().write({'whatsapp_notified': False})  # <- agregar
                        rec._send_ticket_to_technician_whatsapp()
                    except Exception:
                        _logger.exception(
                            'Error WhatsApp reassignment'
                        )

        if closing and to_notify:
            from ..services.whatsapp_alert_service import (
                WhatsAppAlertService
            )
            for ticket in to_notify:
                WhatsAppAlertService.send_client_recovery_notification(
                    self.env,
                    ticket=ticket,
                )

        return result

    # =========================
    # SLA WARNING CRON
    # =========================

    def check_sla_warning(self):
        tickets = self.search([
            ('status', '!=', '3_done')
        ])

        # Forzar recálculo de sla_status, depende del tiempo actual
        for rec in tickets:
            rec._compute_sla_status()

        warning_tickets = tickets.filtered(
            lambda t: t.sla_status == 'warning'
        )

        activity_type = self.env.ref('mail.mail_activity_data_todo')

        for rec in warning_tickets:
            if not rec.assigned_user_id:
                continue

            existing = self.env['mail.activity'].search([
                ('res_model', '=', self._name),
                ('res_id', '=', rec.id),
                ('activity_type_id', '=', activity_type.id),
                ('user_id', '=', rec.assigned_user_id.id),
                ('summary', '=', 'SLA Warning')
            ], limit=1)

            if existing:
                continue

            rec.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=rec.assigned_user_id.id,
                summary='SLA Warning',
                note='El ticket está próximo a vencer SLA.'
            )
        expired_tickets = tickets.filtered(lambda t: t.sla_status == 'expired')

        template = self.env.ref(
            'wifimax_noc_ai.email_template_noc_sla_expired',
            raise_if_not_found=False
        )

        for rec in expired_tickets:
            if template and rec.partner_id.email:
                try:
                    template.send_mail(rec.id, force_send=True)
                except Exception as e:
                    _logger.exception('Error SLA expired email: %s', e)

                _logger.warning('SLA vencido para ticket: %s', rec.name)

    # =========================
    # DASHBOARD STATS
    # =========================

    def get_open_tickets_count(self):

        return self.search_count([
            ('status', '!=', '3_done')
        ])

    def get_critical_tickets_count(self):

        return self.search_count([
            ('zabbix_severity', '=', 'urgent')
        ])

    def get_expired_sla_count(self):

        return self.search_count([
            ('sla_status', '=', 'expired')
        ])

    def get_resolved_tickets_count(self):

        return self.search_count([
            ('status', '=', '3_done')
        ])

    # =========================
    # SLA HOURS
    # =========================

    @api.depends('detection_date', 'close_date')
    def _compute_sla_hours(self):

        for rec in self:

            if rec.detection_date and rec.close_date:

                delta = (
                    rec.close_date - rec.detection_date
                )

                rec.sla_hours = (
                    delta.total_seconds() / 3600
                )

            else:

                rec.sla_hours = 0

    # ===================================
    # Formato del mensaje para el técnico
    # ===================================

    def _format_technician_whatsapp_message(self):
        self.ensure_one()

        status_label = dict(self._fields['status'].selection).get(self.status, self.status)
        priority_label = dict(self._fields['priority'].selection).get(self.priority, self.priority)
        zabbix_label = dict(self._fields['zabbix_severity'].selection).get(self.zabbix_severity, self.zabbix_severity)
        client_name = self.partner_id.name or "Sin cliente"
        sla_deadline = self.sla_deadline.strftime("%Y-%m-%d %H:%M") if self.sla_deadline else "Sin definir"

        map_line = f"🗺 *Mapa:* {self.map_url}\n" if self.map_url else ""

        return (
            f"*_Sistema NOC Wifimax_*\n\n"
            f"🚨 *NUEVO TICKET ASIGNADO*\n\n"

            f"🧾 *Ticket:* {self.name}\n"
            f"👤 *Cliente:* {client_name}\n\n"

            f"📊 *Estado:* {status_label}\n"
            f"⚡ *Prioridad:* {priority_label}\n"
            f"🔥 *Severidad:* {zabbix_label}\n\n"

            f"⏳ *SLA Límite:* {sla_deadline}\n\n"

            f"🖥 *Host:* {self.host_name or '-'}\n"
            f"🌐 *IP:* {self.device_ip or '-'}\n"
            f"📍 *Dirección:* {self.address or 'No disponible'}\n"
            f"{map_line}\n"

            f"📝 *Descripción:*\n"
            f"```{self.description or '-'}```\n\n"

            f"━━━━━━━━━━━━━━━━\n"
            f"*¿Qué deseas hacer?*\n\n"
            f"1️⃣ Ver ticket en Odoo\n"
            f"2️⃣ Consultar IA sobre este ticket\n\n"
            f"_Responde con 1 o 2_"
        )

    # =========================
    # Mensaje para el técnico
    # =========================

    def _send_ticket_to_technician_whatsapp(self):
        self.ensure_one()

        if self.whatsapp_notified:
            return False

        if not self.assigned_user_id:
            return False

        partner = self.assigned_user_id.partner_id
        if not partner:
            return False

        number = (
            getattr(partner, 'whatsapp_phone', False)
            or partner.mobile
            or partner.phone
        )

        if not number:
            _logger.warning("Técnico sin número WhatsApp")
            return False

        config = self.env['wifimax.whatsapp.settings'].search([
            ('active', '=', True),
            ('default_for_noc', '=', True),
            ('provider', '=', 'evolution'),
        ], limit=1)

        if not config:
            _logger.warning("No hay configuración Evolution activa")
            return False

        message = self._format_technician_whatsapp_message()

        try:
            result = config.send_message(
                number=number,
                text=message
            )
        except Exception:
            _logger.exception("Error Evolution API ticket notify")
            return False

        if result and result.get('success'):

            self.write({
                'whatsapp_notified': True,
                'whatsapp_sent': True,
                'whatsapp_sent_date': fields.Datetime.now(),
                'whatsapp_message_id': result.get('message_id'),
            })

            self.message_post(
                body=f"WhatsApp enviado a técnico {partner.name}"
            )
            
            # Crear sesión automáticamente para el nuevo ticket
            phone_digits = ''.join(filter(str.isdigit, number or ''))
            existing = self.env['wifimax.noc.whatsapp.session'].sudo().search([
                ('phone', '=', phone_digits),
                ('state', '!=', 'closed'),
            ], limit=1)
            if not existing:
                self.env['wifimax.noc.whatsapp.session'].sudo().create({
                    'phone': phone_digits,
                    'ticket_id': self.id,
                    'state': 'menu',
                })

        return result