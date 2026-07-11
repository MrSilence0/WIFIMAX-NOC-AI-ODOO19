# NOC WIFIMAX IA (`wifimax_noc_ai`) — Odoo 19

Módulo personalizado para **Odoo 19** que centraliza la gestión de eventos de red, el diagnóstico automático mediante inteligencia artificial, la administración de tickets de soporte y la comunicación bidireccional con clientes y técnicos a través de **WhatsApp Business**.

Desarrollado para el Centro de Operaciones de Red (NOC) de **Wifimax Connection**.

> **Rama principal:** versión para Odoo 19.  
> Para la versión Odoo 18 consulta el repositorio [WIFIMAX-NOC-AI-ODOO18](https://github.com/MrSilence0/WIFIMAX-NOC-AI-ODOO18).

---

## Descripción general

El sistema integra herramientas de monitoreo de red existentes (Zabbix 7.0 y LibreNMS) mediante webhooks HTTP autenticados, delega el diagnóstico automático de fallas a **Claude Sonnet 4.6** (Anthropic) vía API, y gestiona la comunicación de mensajería mediante **Evolution API** (servidor de WhatsApp Business propio). Todos los componentes convergen en la base de datos PostgreSQL administrada por Odoo 19, garantizando consistencia, trazabilidad y auditoría completa de las operaciones del NOC.

---

## Cambios respecto a la versión Odoo 18

Los siguientes ajustes fueron necesarios para la compatibilidad con Odoo 19:

| Área | Cambio |
| --- | --- |
| Controllers | `@route(type='json')` reemplazado por `@route(type='jsonrpc')` |
| Seguridad | Campo `category_id` eliminado de `res.groups` |
| Vistas XML | Elemento `<group>` eliminado de `<search>`; reemplazado por `<filter>` individuales |
| Vistas XML | Atributo `expand="0"` eliminado de `<group>` en vistas de búsqueda |
| Vistas XML | `filter_domain` con `self` eliminado de campos en vistas de búsqueda |
| Vistas XML | `invisible="1"` cambia a `invisible="True"` |
| Modelos | Campo `mobile` eliminado de `res.partner` |
| Modelos | `user.groups_id` reemplazado por `user.group_ids` en `res_partner.py` |
| Referencias XML | Todos los `action=` en menuitems requieren prefijo del módulo: `wifimax_noc_ai.action_xxx` |
| Configuración | `db_host = False` y `db_port = False` generan warnings; se recomienda omitirlos del `.conf` |

---

## Características principales

- **Recepción y correlación de eventos**: webhooks para Zabbix y LibreNMS con autenticación por clave secreta compartida. Agrupa eventos del mismo host/trigger en un único incidente, evitando tickets duplicados.
- **Diagnóstico automático con IA**: integración con la API de Claude (Anthropic) para generar diagnósticos estructurados (Resumen, Posible Causa, Impacto, Acciones Recomendadas).
- **Zonas de seguridad operativa**: clasificación de acciones recomendadas en Verde (bajo riesgo), Amarilla (requiere aprobación) y Roja (nunca se ejecuta automáticamente). El sistema opera en modo solo diagnóstico/recomendación.
- **Tickets de soporte automáticos**: creación y asignación por zona geográfica y carga de trabajo del técnico.
- **Asistente conversacional vía WhatsApp**: los técnicos interactúan con un menú y pueden consultar a la IA sobre el ticket activo directamente desde WhatsApp.
- **Notificaciones automáticas a clientes**: alerta de afectación, número de ticket, y notificación de restablecimiento con duración calculada.
- **Soporte de múltiples IPs por cliente**: modelo `wifimax.noc.device` para clientes con varios equipos o sucursales.
- **Reportes mensuales automáticos en PDF**: generados con QWeb y distribuidos por email y WhatsApp el día 1 de cada mes.
- **Cron jobs nativos de Odoo**: sin dependencias de cron del sistema operativo.

---

## Arquitectura

| Componente | Rol |
| --- | --- |
| Zabbix 7.0 / LibreNMS | Monitoreo de red y disparo de alertas vía webhook |
| Odoo 19 (`wifimax_noc_ai`) | Núcleo del sistema: modelos, lógica de negocio, controladores, cron jobs |
| Claude Sonnet 4.6 (Anthropic API) | Diagnóstico automático y asistente conversacional |
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

1. **Recepción y correlación** — Zabbix/LibreNMS envían un POST al webhook correspondiente; se valida la clave secreta y se correlaciona con incidentes existentes.
2. **Diagnóstico con IA** — Un cron cada 20 minutos procesa incidentes sin ticket, invoca a Claude y clasifica las acciones recomendadas por zona de seguridad.
3. **Creación y asignación de tickets** — Se genera el ticket y se asigna al técnico con menor carga en la zona correspondiente.
4. **Comunicación con técnicos por WhatsApp** — Mensaje automático con los datos del ticket y sesión de chat interactiva (menú / consulta a IA / cierre).
5. **Notificaciones al cliente** — Aviso de afectación, número de ticket y notificación de restablecimiento con duración calculada.

---

## Cron jobs

| Nombre | Frecuencia | Función |
| --- | --- | --- |
| NOC SLA Warning | Cada 5 minutos | Alerta de SLA próximo a vencer |
| Crear tickets de incidents pendientes | Cada 20 minutos | Diagnóstico IA + creación de ticket + notificación |
| Envío automático de reportes mensuales | Día 1 de cada mes | Reportes PDF a clientes empresariales |
| Limpiar sesiones WhatsApp inactivas | Cada hora | Cierra sesiones sin actividad por +2 horas |

---

## Requisitos

- Odoo 19
- PostgreSQL 15+
- Python 3.12
- Zabbix 7.0 y/o LibreNMS
- Evolution API (servidor WhatsApp Business)
- API Key de Anthropic (Claude)

---

## Instalación

1. Clonar este repositorio dentro de la carpeta de módulos de tu instancia de Odoo 19:
   ```bash
   git clone https://github.com/MrSilence0/WIFIMAX-NOC-AI-ODOO19.git wifimax_noc_ai
   ```

2. Instalar la dependencia de Anthropic en el virtualenv de Odoo 19:
   ```bash
   pip install anthropic
   ```

3. Configurar la variable de entorno `ANTHROPIC_API_KEY` en `~/.bashrc`:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   source ~/.bashrc
   ```

4. Instalar el módulo desde la interfaz de Apps de Odoo (con modo desarrollador activado):
   ```bash
   ./odoo-bin -c odoo19.conf -d tu_base_de_datos --init=wifimax_noc_ai
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

**Ejemplo:** `abc123def456...`

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

**Ejemplo:** `xyz789abc123...`

---

### `noc.webhook.secret`
Clave secreta compartida para validar que los webhooks entrantes provienen de Zabbix o LibreNMS.  
**Cómo obtenerla:** es una clave que tú defines libremente. Debe ser la misma que configures en el Media Type de Zabbix y en las alertas de LibreNMS.  
**Recomendación:** usa una cadena aleatoria de al menos 16 caracteres.  
**Ejemplo:** `mi_clave_secreta_2026`

---

### `noc.default_technician_id`
ID del usuario de Odoo que se asignará como técnico cuando el cliente afectado no tenga zona NOC configurada.  
**Cómo obtenerlo:**
1. Ve a **Ajustes → Usuarios y empresas → Usuarios**.
2. Abre el perfil del técnico por defecto.
3. El ID aparece en la URL del navegador: `.../odoo/users/`**6** — ese número es el ID.

**Ejemplo:** `6`

---

### `web.base.url`
URL pública del servidor Odoo que se usa para generar los links de tickets en los mensajes de WhatsApp.  
**Importante para Odoo 19:** si Evolution API está en una VM o servidor diferente, esta URL debe ser la IP accesible desde esa red, no `localhost`.  
**Ejemplo:** `http://192.168.1.2:8070`

---

## Configuración del servidor de correo saliente

El módulo envía notificaciones por correo al técnico asignado cuando se crea un ticket. Para activarlo:

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

## Estado del proyecto

Sistema funcional en ambiente de pruebas. Todas las acciones recomendadas por la IA se registran en estado **pendiente**; el sistema opera en modo solo diagnóstico/recomendación y ninguna acción modifica la infraestructura de red de forma automática.

### Próximas mejoras sugeridas

- Activar ejecución automática de acciones de Zona Verde (ping, traceroute, show interfaces) tras validar en producción.
- Flujo de aprobación de acciones de Zona Amarilla vía WhatsApp.
- Migrar la API Key de Anthropic a un gestor de secretos (ej. HashiCorp Vault).
- Portal web de autoservicio para clientes empresariales.

---

## Licencia

Uso interno — Wifimax Connection.