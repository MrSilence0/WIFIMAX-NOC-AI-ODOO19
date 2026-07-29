# NOC WIFIMAX IA (`wifimax_noc_ai`) — Odoo 19

Módulo personalizado para **Odoo 19** que centraliza la gestión de eventos de red, el diagnóstico automático mediante inteligencia artificial, la administración de tickets de soporte y la comunicación bidireccional con clientes y técnicos a través de **WhatsApp Business**.

Desarrollado para el Centro de Operaciones de Red (NOC) de **Wifimax Connection**.

> **Rama principal:** versión para Odoo 19.  
> Para la versión Odoo 18 consulta el repositorio [WIFIMAX-NOC-AI-ODOO18](https://github.com/MrSilence0/WIFIMAX-NOC-AI-ODOO18).

---

## Descripción general

El sistema integra herramientas de monitoreo de red existentes (Zabbix 7.0 y LibreNMS) mediante webhooks HTTP autenticados, delega el diagnóstico automático de fallas a **Claude Sonnet 4.6** (Anthropic) vía API o a modelos locales mediante **Ollama**, y gestiona la comunicación de mensajería mediante **Evolution API** (servidor de WhatsApp Business propio). Todos los componentes convergen en la base de datos PostgreSQL administrada por Odoo 19, garantizando consistencia, trazabilidad y auditoría completa de las operaciones del NOC.

---

## Stack Tecnológico

| Componente | Versión |
|-----------|---------|
| Odoo | 19.0 |
| Python | 3.12 |
| PostgreSQL | 15+ |
| Ubuntu | 24.04 LTS (WSL2) |
| Zabbix | 7.0 |
| LibreNMS | Última estable |
| IA (nube) | Claude Sonnet 4.6 (Anthropic) |
| IA (local) | Ollama (Qwen 2.5 32B, DeepSeek R1 32B, Llama 3.1 70B) |
| WhatsApp | Evolution API |

---

## Cambios respecto a la versión Odoo 18

Los siguientes ajustes fueron necesarios para la compatibilidad con Odoo 19:

| Área | Cambio |
| --- | --- |
| Controllers | `@route(type='json')` reemplazado por `@route(type='jsonrpc')` |
| Seguridad | Campo `category_id` eliminado de `res.groups` |
| Seguridad | Modelo `ir.module.category` eliminado para grupos |
| Vistas XML | Elemento `<group>` eliminado de `<search>`; reemplazado por `<filter>` individuales |
| Vistas XML | Atributo `expand="0"` eliminado de `<group>` en vistas de búsqueda |
| Vistas XML | `filter_domain` con `self` eliminado de campos en vistas de búsqueda |
| Vistas XML | `invisible="1"` cambia a `invisible="True"` |
| Modelos | Campo `mobile` eliminado de `res.partner` |
| Modelos | `user.groups_id` reemplazado por `user.group_ids` en `res_partner.py` |
| Referencias XML | Todos los `action=` en menuitems requieren prefijo del módulo: `wifimax_noc_ai.action_xxx` |
| Manifest | Orden secuencial obligatorio de archivos `data` por dependencias de referencias |
| Configuración | `db_host = False` y `db_port = False` generan warnings; se recomienda omitirlos del `.conf` |

---

## Características principales

- **Recepción y correlación de eventos**: webhooks para Zabbix y LibreNMS con autenticación por clave secreta compartida. Agrupa eventos del mismo host/trigger en un único incidente, evitando tickets duplicados.
- **Diagnóstico automático con IA**: integración dual con la API de Claude (Anthropic) y modelos locales vía Ollama para generar diagnósticos estructurados (Resumen, Posible Causa, Impacto, Acciones Recomendadas).
- **Zonas de seguridad operativa**: clasificación de acciones recomendadas en Verde (bajo riesgo), Amarilla (requiere aprobación) y Roja (nunca se ejecuta automáticamente). El sistema opera en modo solo diagnóstico/recomendación.
- **Tickets de soporte automáticos**: creación y asignación por zona geográfica y carga de trabajo del técnico.
- **Asistente conversacional vía WhatsApp**: los técnicos visualizan una lista de sus tickets abiertos, seleccionan cuál atender, consultan a la IA y marcan tickets como resueltos directamente desde WhatsApp.
- **Notificaciones automáticas a clientes**: alerta de afectación, número de ticket, y notificación de restablecimiento con duración calculada.
- **Notificación por correo al técnico**: correo electrónico con datos del ticket, diagnóstico HTML formateado y botón "Ver Ticket en Odoo".
- **Soporte de múltiples IPs por cliente**: modelo `wifimax.noc.device` para clientes con varios equipos o sucursales.
- **Reportes mensuales automáticos en PDF**: generados con QWeb y distribuidos por email y WhatsApp el día 1 de cada mes.
- **Cron jobs nativos de Odoo**: sin dependencias de cron del sistema operativo.

---

## Arquitectura

```
┌──────────────┐     ┌──────────────┐
│   Zabbix 7   │────►│              │
└──────────────┘     │  Controllers │     ┌──────────────────┐
┌──────────────┐     │   (webhooks) │────►│  TicketService   │
│  LibreNMS    │────►│              │     │  ClaudeAnalysis  │
└──────────────┘     └──────┬───────┘     │  ActionClassifier│
                            │             └────────┬─────────┘
┌──────────────┐     ┌──────▼───────┐              │
│  Evolution   │◄───►│   Models     │◄─────────────┘
│  API (WA)    │     │  (ORM/PG15)  │
└──────────────┘     └──────────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Anthropic│ │  Ollama  │ │  QWeb    │
        │ Claude   │ │  Local   │ │  Reports │
        └──────────┘ └──────────┘ └──────────┘
```

| Componente | Rol |
| --- | --- |
| Zabbix 7.0 / LibreNMS | Monitoreo de red y disparo de alertas vía webhook |
| Odoo 19 (`wifimax_noc_ai`) | Núcleo del sistema: modelos, lógica de negocio, controladores, cron jobs |
| Claude Sonnet 4.6 (Anthropic API) | Diagnóstico automático y asistente conversacional (nube) |
| Ollama | Diagnóstico automático y asistente conversacional (local) |
| Evolution API | Puerta de enlace de WhatsApp Business |
| PostgreSQL | Persistencia y auditoría |

---

## Estructura del módulo

```
wifimax_noc_ai/
├── controllers/       # Endpoints HTTP (webhooks Zabbix, LibreNMS, WhatsApp)
├── models/            # Modelos de datos ORM
├── services/          # Lógica de negocio (correlación, diagnóstico IA, tickets, WhatsApp, severidad, recovery)
├── views/             # Vistas XML (backend Odoo)
├── data/              # Cron jobs, secuencias, plantillas de correo
├── report/            # Reportes QWeb (PDF)
├── security/          # Reglas de acceso y seguridad
└── static/            # Assets del cliente web (JS/SCSS/XML)
```

---

## Modelos de datos

| Modelo | Tabla en BD | Propósito |
| --- | --- | --- |
| `wifimax.noc.event` | `wifimax_noc_event` | Alerta individual recibida de Zabbix/LibreNMS |
| `wifimax.noc.incident` | `wifimax_noc_incident` | Agrupación de eventos del mismo trigger |
| `wifimax.noc.ticket` | `wifimax_noc_ticket` | Ticket de soporte con diagnóstico IA, SLA y técnico asignado |
| `wifimax.noc.zone` | `wifimax_noc_zone` | Zona geográfica con técnicos para enrutamiento |
| `wifimax.noc.device` | `wifimax_noc_device` | Equipos monitoreados por cliente (múltiples IPs) |
| `wifimax.noc.action.request` | `wifimax_noc_action_request` | Acciones recomendadas clasificadas por zona de seguridad |
| `wifimax.noc.whatsapp.session` | `wifimax_noc_whatsapp_session` | Sesión de chat WhatsApp con historial en JSON |
| `wifimax.noc.report.history` | `wifimax_noc_report_history` | Historial de reportes PDF enviados |
| `wifimax.whatsapp.settings` | `wifimax_whatsapp_settings` | Configuración de proveedores WhatsApp (Evolution API, Meta Cloud API, Twilio) |

También extiende `res.partner` con campos NOC: WhatsApp, IP monitoreada (legacy), zona asignada, ubicación en Maps, indicador de cliente empresarial y equipos monitoreados.

---

## Flujo operativo

```
Zabbix/LibreNMS detecta falla
        │
        ▼
Webhook → Evento → Correlación → Incidente
        │
        ▼  (cron 20 min)
Claude/Ollama genera diagnóstico
        │
        ▼
Ticket creado → Técnico asignado por zona
        │
        ├──► Correo al técnico (con botón "Ver Ticket en Odoo")
        ├──► WhatsApp al técnico (con menú interactivo + sesión)
        └──► WhatsApp al cliente (notificación de afectación)
        │
        ▼
Técnico interactúa vía WhatsApp:
  - Lista de tickets abiertos
  - Ver ticket en Odoo
  - Consultar IA
  - Marcar como resuelto
  - Cerrar conversación
        │
        ▼
Recovery → Cierra incidente → Notifica cliente (duración calculada)
```

1. **Recepción y correlación** — Zabbix/LibreNMS envían un POST al webhook correspondiente; se valida la clave secreta y se correlaciona con incidentes existentes.
2. **Diagnóstico con IA** — Un cron cada 20 minutos procesa incidentes sin ticket, invoca a Claude o al modelo local y clasifica las acciones recomendadas por zona de seguridad.
3. **Creación y asignación de tickets** — Se genera el ticket y se asigna al técnico con menor carga en la zona correspondiente.
4. **Comunicación con técnicos** — Correo electrónico con diagnóstico HTML y botón de acceso + mensaje WhatsApp con menú interactivo y sesión de chat.
5. **Notificaciones al cliente** — Aviso de afectación, número de ticket y notificación de restablecimiento con duración calculada.

---

## Asistente WhatsApp — Flujo de estados

| Estado | Descripción | Acciones disponibles |
|--------|-------------|----------------------|
| `lista_tickets` | Lista de tickets abiertos del técnico | Número: abrir ticket / Cerrar: cerrar conversación |
| `menu` | Resumen completo del ticket seleccionado | 1: Ver en Odoo / 2: Consultar IA / 3: Marcar resuelto / 4: Lista de tickets / 5: Cerrar |
| `chat_ia` | Chat libre con IA sobre el ticket activo | 0: Menú / 1: Seguir preguntando / 2: Ver ticket / 3: Resuelto / 4: Lista / 5: Cerrar |
| `tras_link` | Menú posterior a mostrar el link del ticket | 1: Menú / 2: IA / 3: Resuelto / 4: Lista / 5: Cerrar |
| `closed` | Sesión cerrada | Solo responde a "Reactivar"; cualquier otro mensaje es ignorado |

La sesión se crea automáticamente al enviar el ticket al técnico. Al cerrar por inactividad (2 horas), el sistema envía un mensaje recordando escribir "Reactivar". Al marcar un ticket como resuelto, se muestra automáticamente la lista de tickets restantes.

---

## Zonas de seguridad operativa

| Zona | Riesgo | Comportamiento |
|------|--------|----------------|
| 🟢 Verde | Bajo | Solo diagnóstico — sin ejecución |
| 🟡 Amarilla | Medio | Solo diagnóstico — sin ejecución |
| 🔴 Roja | Alto | Solo diagnóstico — sin ejecución |

> **Nota:** La ejecución automática de comandos está deshabilitada por decisión operativa del asesor técnico de Wifimax Connection. El sistema solo genera diagnósticos y recomendaciones; la decisión final queda en manos del técnico responsable.

---

## Cron jobs

| Nombre | Frecuencia | Función |
| --- | --- | --- |
| NOC SLA Warning | Cada 5 minutos | Alerta de SLA próximo a vencer |
| Crear tickets de incidents pendientes | Cada 20 minutos | Diagnóstico IA + creación de ticket + notificación |
| Envío automático de reportes mensuales | Día 1 de cada mes | Reportes PDF a clientes empresariales |
| Limpiar sesiones WhatsApp inactivas | Cada hora | Cierra sesiones sin actividad por +2 horas y notifica al técnico |

---

## Requisitos

- Odoo 19
- PostgreSQL 15+
- Python 3.12
- Zabbix 7.0 y/o LibreNMS
- Evolution API (servidor WhatsApp Business)
- API Key de Anthropic (Claude) y/o Ollama (modelos locales)

---

## Instalación

1. Clonar este repositorio dentro de la carpeta de módulos de tu instancia de Odoo 19:
   ```bash
   cd /opt/odoo19_dev/modules
   git clone https://github.com/MrSilence0/WIFIMAX-NOC-AI-ODOO19.git wifimax_noc_ai
   ```

2. Instalar la dependencia de Anthropic en el virtualenv de Odoo 19:
   ```bash
   source /opt/odoo19_dev/venv/bin/activate
   pip install anthropic
   ```

3. Configurar la variable de entorno `ANTHROPIC_API_KEY` en `~/.bashrc`:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-api03-..."
   source ~/.bashrc
   ```

4. Instalar el módulo:
   ```bash
   cd /opt/odoo19_dev
   ./odoo/odoo-bin -c odoo19.conf -d database_odoo19 --init=wifimax_noc_ai --logfile=""
   ```

5. Configurar los parámetros del sistema (ver sección siguiente).

6. Configurar el servidor de correo saliente (ver sección siguiente).

7. Configurar el Media Type de tipo Webhook en Zabbix apuntando a `/zabbix/webhook` en el servidor Odoo.

---

## Configuración de parámetros del sistema

Ir a **Ajustes → Técnico → Parámetros del sistema** y configurar los siguientes valores:

### `noc.zabbix.url`
URL base del servidor Zabbix, sin barra al final.  
**Cómo obtenerla:** es la misma URL que usas para acceder al panel web de Zabbix.  
**Ejemplo:** `http://localhost:8082`

---

### `noc.zabbix.api_token`
Token de autenticación para la API de Zabbix.  
**Cómo obtenerlo:**
1. Inicia sesión en Zabbix como administrador.
2. Ve a **User settings → API tokens → Create API token**.
3. Asigna un nombre, selecciona el usuario y haz clic en **Add**.
4. Copia el token generado — solo se muestra una vez.

**Ejemplo:** `74c18eaf22f8a52eb541f0e23253cc52fb2ac6f46a78611f9ad4d5c241c20a41`

---

### `noc.librenms.url`
URL base del servidor LibreNMS, sin barra al final.  
**Cómo obtenerla:** es la misma URL que usas para acceder al panel web de LibreNMS.  
**Ejemplo:** `http://localhost:8081`

---

### `noc.librenms.api_token`
Token de autenticación para la API de LibreNMS.  
**Cómo obtenerlo:**
1. Inicia sesión en LibreNMS como administrador.
2. Ve a **Preferences → API Tokens** (esquina superior derecha, menú de usuario).
3. Haz clic en **Create API Token**.
4. Copia el token generado.

**Ejemplo:** `2ce26757862b36a4cf87640c0356a042`

---

### `noc.webhook.secret`
Clave secreta compartida para validar que los webhooks entrantes provienen de Zabbix o LibreNMS.  
**Cómo obtenerla:** es una clave que tú defines libremente. Debe ser la misma que configures en el Media Type de Zabbix y en las alertas de LibreNMS.  
**Recomendación:** usa una cadena aleatoria de al menos 16 caracteres.  
**Ejemplo:** `123456`

---

### `noc.default_technician_id`
ID del usuario de Odoo que se asignará como técnico cuando el cliente afectado no tenga zona NOC configurada.  
**Cómo obtenerlo:**
1. Ve a **Ajustes → Usuarios y empresas → Usuarios**.
2. Abre el perfil del técnico por defecto.
3. El ID aparece en la URL del navegador: `.../odoo/users/`**2** — ese número es el ID.

**Ejemplo:** `2`

---

### `web.base.url`
URL pública del servidor Odoo que se usa para generar los links de tickets en los mensajes de WhatsApp y correos electrónicos.  
**Importante para Odoo 19:** si Evolution API está en una VM o servidor diferente, esta URL debe ser la IP accesible desde esa red, no `localhost`.  
**Ejemplo:** `http://192.168.1.2:8070`

---

### `noc.ai.provider`
Proveedor de inteligencia artificial para diagnósticos y chat. Valores: `anthropic` (nube) o `local` (Ollama).  
**Ejemplo:** `anthropic`

---

### `noc.ai.ollama_host`
URL del servidor Ollama. Solo aplica si `noc.ai.provider` es `local`.  
**Ejemplo:** `http://localhost:8090`

---

### `noc.ai.ollama_model`
Nombre del modelo de Ollama a utilizar. Solo aplica si `noc.ai.provider` es `local`.  
**Ejemplo:** `qwen2.5-coder:32b`

---

> La API Key de Anthropic Claude se configura como variable de entorno del sistema operativo (`ANTHROPIC_API_KEY`), **no** como parámetro del sistema de Odoo.

---

## Configuración de IA Local (Ollama)

El sistema soporta dos proveedores de IA: **Anthropic Claude** (nube) y **Ollama** (local). Para cambiar entre ellos solo es necesario modificar el parámetro `noc.ai.provider` — no requiere reiniciar Odoo.

### Instalación de Ollama

```bash
# Instalar Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Descargar los modelos
ollama pull qwen2.5-coder:32b
ollama pull deepseek-r1:32b
ollama pull llama3.1:70b
```

### Modelos probados

| Modelo | Parámetro `noc.ai.ollama_model` | RAM mínima | Descripción |
|--------|-------------------------------|------------|-------------|
| Qwen 2.5 32B | `qwen2.5-coder:32b` | 20 GB | Modelo generalista de alto rendimiento |
| DeepSeek R1 32B | `deepseek-r1:32b` | 20 GB | Modelo con razonamiento avanzado |
| Llama 3.1 70B | `llama3.1:70b` | 40 GB | Modelo de Meta cuantizado para uso local |

### Activar IA local

1. Cambiar `noc.ai.provider` a `local` en **Ajustes → Parámetros del sistema**
2. Configurar `noc.ai.ollama_host` (por defecto `http://localhost:8090`)
3. Configurar `noc.ai.ollama_model` con el nombre del modelo deseado

### Volver a Claude

Cambiar `noc.ai.provider` a `anthropic`. No requiere reiniciar Odoo.

---

## Configuración del servidor de correo saliente

El módulo envía notificaciones por correo al técnico asignado cuando se crea un ticket. El correo incluye los datos del ticket, el diagnóstico formateado en HTML y un botón "Ver Ticket en Odoo".

### Paso 1 — Configurar el servidor SMTP en Odoo

Ir a **Ajustes → Técnico → Correo electrónico → Servidores de correo saliente → Nuevo** y completar:

| Campo | Valor |
| --- | --- |
| Nombre | Gmail NOC (o el nombre que prefieras) |
| Servidor SMTP | `smtp.gmail.com` |
| Puerto | `587` |
| Cifrado | TLS (STARTTLS) |
| Usuario | tu correo de Gmail |
| Contraseña | contraseña de aplicación (ver Paso 2) |

Haz clic en **Probar conexión** para verificar.

---

### Paso 2 — Obtener la contraseña de aplicación de Gmail

> La contraseña de aplicación es diferente a tu contraseña normal de Gmail. Se genera específicamente para aplicaciones externas y **no expone tu contraseña real**.

1. Ve a [myaccount.google.com](https://myaccount.google.com).
2. En el menú izquierdo selecciona **Seguridad**.
3. Activa la **Verificación en dos pasos** si no la tienes activa (es requisito).
4. Una vez activa, en la misma sección de Seguridad busca **Contraseñas de aplicaciones**.
5. En el campo **Seleccionar aplicación** escribe `Odoo NOC` o cualquier nombre descriptivo.
6. Haz clic en **Crear**.
7. Google genera una contraseña de 16 caracteres — cópiala y úsala en el campo **Contraseña** del servidor SMTP de Odoo.

> **Nota:** esta contraseña solo se muestra una vez. Si la pierdes deberás generar una nueva.

---

## Configuración de WhatsApp (Evolution API)

### Instalación en VM con Docker

```bash
# Instalar Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Clonar Evolution API
git clone https://github.com/EvolutionAPI/evolution-api.git
cd evolution-api
cp .env.example .env
nano .env   # configurar API_KEY y otros parámetros

# Iniciar
docker compose up -d

# Verificar
docker ps | grep evolution
```

### Configurar webhook hacia Odoo

```bash
curl -X POST http://IP_VM:8080/webhook/set/wifimax_noc \
  -H "Content-Type: application/json" \
  -H "apikey: TU_API_KEY" \
  -d '{"webhook":{"enabled":true,"url":"http://192.168.1.2:8070/whatsapp/incoming","webhookByEvents":false,"events":["MESSAGES_UPSERT"]}}'
```

### Verificar webhook

```bash
curl -s http://IP_VM:8080/webhook/find/wifimax_noc \
  -H "apikey: TU_API_KEY" | python3 -m json.tool
```

### Configurar en Odoo

Ir a **Wifimax NOC → Configuración de WhatsApp → Nuevo**:
- **URL base:** `http://192.168.1.44:8080`
- **API Key:** tu API key de Evolution
- **Instancia:** `wifimax_noc`
- **Default para NOC:** ✓

### Mantenimiento de la sesión

WhatsApp puede desvincular dispositivos tras ~14 días de inactividad. Para prevenirlo, configurar en la VM un cron que verifique el estado cada 15 minutos y reconecte automáticamente:

```bash
#!/bin/bash
# ~/check_evolution.sh
STATE=$(curl -s http://localhost:8080/instance/connectionState/wifimax_noc \
  -H "apikey: TU_API_KEY" | python3 -c "import sys,json; print(json.load(sys.stdin)['instance']['state'])" 2>/dev/null)

if [ "$STATE" != "open" ]; then
    echo "$(date) - Desconectada: $STATE" >> ~/evolution_alerts.log
    curl -s http://localhost:8080/instance/connect/wifimax_noc \
      -H "apikey: TU_API_KEY" > /dev/null 2>&1
fi
```

```bash
chmod +x ~/check_evolution.sh
crontab -e
# Agregar:
*/15 * * * * /home/vboxuser/check_evolution.sh
```

Asegurar reinicio automático de Docker:
```bash
docker update --restart=always evolution_api
```

---

## Configuración de red (Windows + WSL)

Si Odoo 19 corre en WSL y Evolution API en una VM de VirtualBox, configurar portproxy en Windows (PowerShell como administrador):

```powershell
# Puerto 8070 — Odoo 19
netsh interface portproxy add v4tov4 listenport=8070 listenaddress=0.0.0.0 connectport=8070 connectaddress=IP_WSL

# Verificar
netsh interface portproxy show all

# Regla de firewall
netsh advfirewall firewall add rule name="Odoo19 NOC" dir=in action=allow protocol=TCP localport=8070
```

> **Nota:** La IP de WSL puede cambiar al reiniciar. Verificar con `hostname -I` dentro de WSL y actualizar el portproxy si es necesario.

---

## Comandos de operación

```bash
# Arrancar Odoo 19
cd /opt/odoo19_dev && source venv/bin/activate
./odoo/odoo-bin -c odoo19.conf -d database_odoo19 --logfile=""

# Actualizar módulo
./odoo/odoo-bin -c odoo19.conf -d database_odoo19 -u wifimax_noc_ai --logfile=""

# Shell de Odoo
./odoo/odoo-bin shell -c odoo19.conf -d database_odoo19

# Prueba de webhook Zabbix
curl -s -X POST http://localhost:8070/zabbix/webhook \
  -H "Content-Type: application/json" \
  -d '{"secret":"123456","host":"RTR-TEST","ip":"10.10.50.1","event_status":"problem","trigger":"Interface Down","trigger_id":"TRG-001","event_id":"EV-001","severity":"High","event_date":"2026-07-12 00:00:00"}'

# Logs de Evolution API
docker logs -f evolution_api
```

### URLs de acceso

| Servicio | URL |
|----------|-----|
| Odoo 19 | `http://localhost:8070` |
| Odoo 19 (debug) | `http://localhost:8070/odoo?debug=1` |
| Odoo 18 | `http://localhost:8069` |
| Zabbix | `http://localhost:8082` |
| LibreNMS | `http://localhost:8081` |
| Evolution API Manager | `http://IP_VM:8080/manager` |

---

## Estado del proyecto

Sistema funcional en ambiente de pruebas. Todas las acciones recomendadas por la IA se registran en estado **pendiente**; el sistema opera en modo solo diagnóstico/recomendación y ninguna acción modifica la infraestructura de red de forma automática.

### Próximas mejoras sugeridas

- Activar ejecución automática de acciones de Zona Verde (ping, traceroute, show interfaces) tras validar en producción.
- Flujo de aprobación de acciones de Zona Amarilla vía WhatsApp.
- Migrar la API Key de Anthropic a un gestor de secretos (ej. HashiCorp Vault).
- Portal web de autoservicio para clientes empresariales.
- Evaluación comparativa de modelos locales vs Claude para diagnósticos NOC.

---

## Repositorios

- **Odoo 19:** https://github.com/MrSilence0/WIFIMAX-NOC-AI-ODOO19
- **Odoo 18:** https://github.com/MrSilence0/WIFIMAX-NOC-AI-ODOO18

---

## Licencia

Uso interno — Wifimax Connection SAS de CV © 2026