from datetime import timedelta
from odoo import fields
import logging

_logger = logging.getLogger(__name__)


class CorrelationEngine:

    @staticmethod
    def process_event(env, event):

        incident_model = env[
            'wifimax.noc.incident'
        ].sudo()

        # ==================================
        # BUSCAR INCIDENT ABIERTO
        # mismo host + mismo trigger, sin límite de tiempo
        # Un incident abierto absorbe todos los eventos
        # del mismo trigger hasta que se cierre
        # ==================================
        domain = [
            ('host', '=', event.host),
            ('status', '=', 'open'),
        ]

        if event.trigger_id:
            domain.append(
                ('trigger_id', '=', event.trigger_id)
            )
        else:
            domain.append(
                ('root_cause', '=', event.event_type)
            )

        incident = incident_model.search(
            domain,
            order='id desc',
            limit=1
        )

        if incident:

            _logger.info(
                "INCIDENT FOUND: %s",
                incident.id
            )

            vals = {}

            if not incident.trigger_id and event.trigger_id:
                vals['trigger_id'] = event.trigger_id

            if (
                not incident.external_event_id
                and event.external_event_id
            ):
                vals['external_event_id'] = event.external_event_id

            if vals:
                incident.sudo().write(vals)

                _logger.info(
                    "INCIDENT UPDATED trigger=%s event=%s",
                    incident.trigger_id,
                    incident.external_event_id
                )

            event.sudo().incident_id = incident.id

            return incident, False

        # ==================================
        # CREAR INCIDENT NUEVO
        # Solo si no existe uno abierto para este host+trigger
        # La ventana de 10 min ya no es necesaria porque
        # la búsqueda por status='open' evita duplicados
        # ==================================
        incident = incident_model.create({
            'name': f'INC-{event.host}',
            'host': event.host,
            'device_ip': event.device_ip,
            'root_cause': event.event_type,
            'severity': event.severity,
            'status': 'open',
            'trigger_id': event.trigger_id,
            'external_event_id': event.external_event_id,
        })

        _logger.info(
            "INCIDENT CREATED: %s",
            incident.id
        )

        event.sudo().incident_id = incident.id

        return incident, True