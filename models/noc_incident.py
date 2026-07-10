from odoo import models, fields, api


class NocIncident(models.Model):
    _name = 'wifimax.noc.incident'
    _description = 'NOC Incident'

    # =========================
    # IDENTIFICACIÓN
    # =========================
    name = fields.Char(required=True)

    host = fields.Char(required=True)
    device_ip = fields.Char(string='IP Equipo')

    # =========================
    # CLASIFICACIÓN
    # =========================
    root_cause = fields.Char()

    severity = fields.Selection([
        ('urgent', 'Urgente'),
        ('attention', 'Revisar'),
        ('normal', 'Normal'),
    ], default='normal')

    status = fields.Selection([
        ('open', 'Open'),
        ('closed', 'Closed')
    ], default='open')

    # =========================
    # TIMELINE
    # =========================
    opened_date = fields.Datetime(default=fields.Datetime.now)
    closed_date = fields.Datetime()

    resolution_minutes = fields.Float(string='Tiempo Resolución (min)')

    # =========================
    # RELACIONES
    # =========================
    event_ids = fields.One2many(
        'wifimax.noc.event',
        'incident_id'
    )

    event_count = fields.Integer(
        string='Total Eventos',
        compute='_compute_event_count',
        store=True,
    )
    ticket_id = fields.Many2one('wifimax.noc.ticket')

    # =========================
    # CORRELACIÓN ZABBIX (CLAVE)
    # =========================

    # Event problem original que generó el incidente
    external_event_id = fields.Char(index=True)

    # trigger lógico (BGP Down, CPU High, etc.)
    trigger_id = fields.Char(index=True)
    
    # ==================================
    # ALMACENAR EL DIAGNÓSTICO DE CLAUDE
    # ==================================
    
    diagnosis = fields.Html(
        string='AI Diagnosis',
        readonly=True,
        help='Diagnóstico inicial generado por IA'
    )
    

    def cron_process_pending_incidents(self):
        from odoo.addons.wifimax_noc_ai.services.ticket_service import TicketService
        TicketService.process_pending_incidents(self.env)

    EVENT_LIMIT_WARNING = 50

    @api.depends('event_ids')
    def _compute_event_count(self):
        for rec in self:
            count = len(rec.event_ids)
            rec.event_count = count
            if count >= self.EVENT_LIMIT_WARNING:
                _logger.warning(
                    'Incident %s tiene %s eventos — posible tormenta de alertas.',
                    rec.id,
                    count,
                )
