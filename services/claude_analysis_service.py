import os
import logging
from anthropic import Anthropic

_logger = logging.getLogger(__name__)

# =========================
# CONSTANTES
# =========================
CLAUDE_MODEL = 'claude-sonnet-4-6'
CLAUDE_API_KEY = os.getenv('ANTHROPIC_API_KEY') or os.getenv('CLAUDE_API_KEY')


def _get_client():
    """Retorna un cliente Anthropic. Lanza error si no hay API key."""
    if not CLAUDE_API_KEY:
        raise ValueError(
            "No se encontró ANTHROPIC_API_KEY en las variables de entorno. "
            "Ejecuta: export ANTHROPIC_API_KEY='sk-ant-api03-...'"
        )
    return Anthropic(api_key=CLAUDE_API_KEY)


class ClaudeAnalysisService:

    @staticmethod
    def generate_diagnosis(incident):

        try:
            client = _get_client()

            prompt = f"""
                    Eres un ingeniero NOC Senior experto en ISP.

                    Analiza la siguiente alerta:

                    Host: {incident.host}
                    IP: {incident.device_ip}
                    Alarma: {incident.root_cause}
                    Severidad: {incident.severity}

                    Genera un diagnóstico operativo.

                    IMPORTANTE:
                    - Responde únicamente en TEXTO PLANO.
                    - No utilices Markdown.
                    - No uses #, ##, **, tablas ni listas numeradas.
                    - Utiliza únicamente el siguiente formato exacto:

                    RESUMEN:
                    <texto>

                    POSIBLE CAUSA:
                    <texto>

                    IMPACTO:
                    <texto>

                    ACCIONES RECOMENDADAS:
                    - acción 1
                    - acción 2
                    - acción 3

                    Mantén la respuesta corta y práctica para un técnico NOC.
                    Máximo 250 palabras.

                    Responde en español.
                    """

            response = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=800,
                messages=[{'role': 'user', 'content': prompt}]
            )

            return response.content[0].text

        except Exception:
            _logger.exception('Error consultando Claude')
            return 'No fue posible generar el diagnóstico automático.'

    @staticmethod
    def chat_with_technician(incident, ticket, history, question):
        try:
            client = _get_client()

            system_prompt = f"""Eres un ingeniero NOC Senior experto en ISP.
Estás asistiendo a un técnico de soporte con un ticket específico.

CONTEXTO DEL TICKET:
- Ticket: {ticket.name}
- Host: {incident.host if incident else ticket.host_name}
- IP: {incident.device_ip if incident else ticket.device_ip}
- Alarma: {incident.root_cause if incident else ticket.name}
- Severidad: {ticket.zabbix_severity}
- Diagnóstico inicial: {ticket.description or 'No disponible'}

REGLAS ESTRICTAS:
- Solo responde preguntas relacionadas con este ticket, este host o esta alarma.
- Si el técnico pregunta algo que no tiene relación con el ticket, responde:
  "Solo puedo ayudarte con temas relacionados al ticket {ticket.name}."
- Responde en texto plano, sin Markdown.
- Máximo 200 palabras por respuesta.
- Responde en español."""

            messages = history + [{'role': 'user', 'content': question}]

            response = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=500,
                system=system_prompt,
                messages=messages,
            )

            return response.content[0].text

        except Exception:
            _logger.exception('Error en chat con técnico')
            return 'No fue posible consultar la IA.'

    @staticmethod
    def generate_diagnosis_and_actions(env, incident, ticket):
        """
        Genera diagnóstico y registra las acciones recomendadas clasificadas
        por zona. Ninguna acción se ejecuta automáticamente — el técnico
        decide qué ejecutar manualmente desde Odoo.
        """
        from .action_classifier_service import ActionClassifierService

        diagnosis = ClaudeAnalysisService.generate_diagnosis(incident)

        actions = ActionClassifierService.extract_actions(diagnosis)

        source = 'zabbix'
        if incident.event_ids:
            last_event = incident.event_ids.sorted('id', reverse=True)[:1]
            if last_event and last_event[0].source == 'librenms':
                source = 'librenms'

        for action in actions:
            zone = action['zone']

            if zone == 'red':
                _logger.warning(
                    'Acción ZONA ROJA detectada — solo alerta: %s',
                    action['text']
                )

            env['wifimax.noc.action.request'].sudo().create({
                'name': action['text'][:100],
                'ticket_id': ticket.id,
                'zone': zone,
                'command': action['text'],
                'device_ip': incident.device_ip,
                'source': source,
                'state': 'pending',
            })

        return diagnosis