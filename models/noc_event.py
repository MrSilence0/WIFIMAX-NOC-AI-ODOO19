from odoo import models, fields


class NocEvent(models.Model):
    _name = 'wifimax.noc.event'
    _description = 'NOC Event'

    # =========================
    # ORIGEN
    # =========================
    source = fields.Selection([
        ('zabbix', 'Zabbix'),
        ('librenms', 'LibreNMS'),
        ('manual', 'Manual'),
    ], string='Fuente', required=True)

    host = fields.Char(required=True)
    device_ip = fields.Char()

    # =========================
    # TIMING
    # =========================
    event_date = fields.Datetime()
    received_date = fields.Datetime(default=fields.Datetime.now)

    # =========================
    # TIPO DE EVENTO
    # =========================
    event_type = fields.Char(required=True)

    severity = fields.Selection([
        ('urgent', 'Urgente'),
        ('attention', 'Revisar'),
        ('normal', 'Normal'),
    ], default='normal')

    event_status = fields.Selection([
        ('problem', 'Problem'),
        ('recovery', 'Recovery'),
    ], default='problem')

    # =========================
    # CORRELACIÓN ZABBIX (CLAVE)
    # =========================

    # ID del evento en Zabbix
    external_event_id = fields.Char(index=True)

    # ID del evento problem asociado (para recovery)
    problem_event_id = fields.Char(index=True)

    # trigger lógico
    trigger_id = fields.Char(index=True)

    # =========================
    # AUDITORÍA
    # =========================
    raw_payload = fields.Text()

    processed = fields.Boolean(default=False)

    # =========================
    # RELACIÓN INTERNA
    # =========================
    incident_id = fields.Many2one('wifimax.noc.incident')
    
    # =========================
    # WEBHOOK ZABBIX Y LIBRENMS
    # =========================
    source = fields.Selection([
        ('zabbix', 'Zabbix'),
        ('librenms', 'LibreNMS'),
        ('manual', 'Manual'),
    ], string='Fuente')