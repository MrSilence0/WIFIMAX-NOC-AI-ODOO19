import logging
import re

_logger = logging.getLogger(__name__)

# Palabras clave que indican que la ACCIÓN PRINCIPAL es de Zona Roja
RED_ACTION_KEYWORDS = [
    r'\bclear\s+ip\s+bgp\b',
    r'\bno\s+router\s+bgp\b',
    r'\bno\s+router\s+ospf\b',
    r'\bno\s+network\b',
    r'\bno\s+neighbor\b',
    r'\bshutdown\s+bgp\b',
    r'\breinicia[r]?\s+sesion\s+bgp\b',
    r'\breset\s+bgp\b',
    r'\bmodifica[r]?\s+.*bgp\b',
    r'\bcambia[r]?\s+.*bgp\b',
    r'\bmodifica[r]?\s+.*ospf\b',
    r'\bcambia[r]?\s+.*ospf\b',
    r'\bvlan\s+trunk\b',
    r'\bswitchport\s+trunk\b',
    r'\bip\s+access-list\b',
    r'\baccess-list\b',
    r'\bno\s+ip\s+nat\b',
    r'\bip\s+nat\s+inside\b',
    r'\bmpls\s+label\b',
    r'\bno\s+mpls\b',
]

# Palabras clave de Zona Amarilla
YELLOW_PATTERNS = [
    r'\bruta\s+est[aá]tica\b',
    r'\bip\s+route\s+\d',
    r'\bstatic\s+route\b',
    r'\bfailover\b',
    r'\breinicio\s+de\s+servicio',
    r'\breinicia[r]?\s+servicio',
    r'\brestart\s+service',
    r'\bshutdown\b',
    r'\bno\s+shutdown\b',
    r'\bhabilitar\s+interfaz\b',
    r'\bdeshabilitar\s+interfaz\b',
    r'\binterface.*\bup\b',
    r'\binterface.*\bdown\b',
]

# Palabras clave de Zona Verde — diagnóstico y solo lectura
GREEN_PATTERNS = [
    r'\bping\b',
    r'\btraceroute\b',
    r'\btracert\b',
    r'\bshow\b',
    r'\bverifica[r]?\b',
    r'\bmonitor\b',
    r'\brecolect\b',
    r'\bdiagnos\b',
    r'\bconsult\b',
    r'\bcontacta[r]?\b',
    r'\brevisa[r]?\b',
    r'\bvalida[r]?\b',
    r'\bidentifica[r]?\b',
    r'\bdetecta[r]?\b',
    r'\banaliza[r]?\b',
    r'\bobserva[r]?\b',
]


class ActionClassifierService:

    @staticmethod
    def classify(text):
        """
        Clasifica un texto/acción en zona verde, amarilla o roja.
        La zona roja solo aplica si el COMANDO PRINCIPAL es rojo,
        no si aparece como contexto.
        """
        text_lower = text.lower()

        # Zona Roja — solo si la acción principal es peligrosa
        for pattern in RED_ACTION_KEYWORDS:
            if re.search(pattern, text_lower):
                _logger.info('Acción clasificada ROJA: %s', text[:80])
                return 'red'

        # Zona Amarilla
        for pattern in YELLOW_PATTERNS:
            if re.search(pattern, text_lower):
                _logger.info('Acción clasificada AMARILLA: %s', text[:80])
                return 'yellow'

        # Zona Verde por defecto
        _logger.info('Acción clasificada VERDE: %s', text[:80])
        return 'green'

    @staticmethod
    def extract_actions(diagnosis_text):
        """
        Extrae las acciones recomendadas del diagnóstico de Claude
        y las clasifica por zona.
        """
        actions = []
        in_actions = False

        for line in diagnosis_text.split('\n'):
            line = line.strip()

            if 'ACCIONES RECOMENDADAS' in line.upper():
                in_actions = True
                continue

            if in_actions and line.startswith('-'):
                action_text = line.lstrip('- ').strip()
                if action_text:
                    zone = ActionClassifierService.classify(action_text)
                    actions.append({
                        'text': action_text,
                        'zone': zone,
                    })

        return actions