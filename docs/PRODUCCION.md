# 🚀 GyverLabs — Guía para pasar a Producción Real

> Documento de planeación. **Nada aquí está activo en la demo** (que es 100% simulada y local). Esto es la hoja de ruta para cuando David dé la orden de "pasar a real".

La visión: **un solo dashboard** desde donde se agregan instituciones y secretarías; cada una opera con **su propio dominio y su marca** (ej. `ietac.edu.co`, `ietli.edu.co`) **sin ningún rastro visible de GyverLabs**; todo interconectado por dentro; servidor robusto y difícil de vulnerar; y costos de mantenimiento medibles.

---

## 1. Arquitectura multi-tenant (un código, N instituciones)

- **Una sola base de código** (la actual). Cada institución/secretaría es un **tenant** en la tabla `Tenant` (ya existe en la demo) con: nombre, dominio, color, módulos activos y estado.
- **Aislamiento de datos por tenant.** En producción se migra de SQLite a **PostgreSQL** con aislamiento por **schema** (un schema por institución) o por **fila con `tenant_id` + Row-Level Security**. Recomendado para colegios: **schema por tenant** (aislamiento fuerte, backups selectivos, y si un colegio se va, se exporta/elimina su schema sin tocar a los demás).
- **Resolución por dominio.** Un middleware lee el `Host:` de cada request (`ietac.edu.co` → tenant IETAC) y fija el schema/filtro de esa petición. El usuario nunca ve otro tenant.

## 2. Marca blanca y dominios propios (sin rastro de GyverLabs)

Cada institución con **su dominio .edu.co**, viéndose como su propio sistema:

1. **Registro del dominio `.edu.co`.** En Colombia los `.edu.co` los administra **.CO Internet S.A.S.** vía registradores autorizados. Requiere soporte de que es una institución educativa. (Alternativa rápida para pruebas: `.com`/`.co` normal.)
2. **DNS en Cloudflare** con **WHOIS privacy** activado → el "quién es el dueño" queda oculto. Un registro `CNAME`/`A` apunta el dominio del colegio al servidor.
3. **Sin marca en el producto.** El sistema toma logo, nombre y colores del tenant. **No se sirve ningún string "GyverLabs", ni en la UI, ni en los metadatos, ni en el `<title>`, ni en los correos** (los correos salen de `@ietac.edu.co`, no de un dominio de la plataforma). El código del cliente ya está preparado para esto (branding por tenant).
4. **Certificado TLS por dominio** automático (Cloudflare / Let's Encrypt) → candado verde `https://ietac.edu.co`.
5. **No rastreable:** sin analítica de terceros, sin CDNs que delaten origen común, cabeceras `Server` genéricas, y cada tenant con su subdominio de correo. Para el mundo exterior, `ietac.edu.co` e `ietli.edu.co` parecen sistemas independientes.

> En la demo esto ya se ve: en **Súper Admin → Tenants** creas una institución y le pones su dominio propio (campo "marca blanca"); el sistema muestra `ietac.edu.co` sin exponer la plataforma.

## 3. Seguridad — servidor difícil de vulnerar

Checklist mínimo de endurecimiento (defensa en capas):

- **Servidor / red**
  - VPS dedicado (ver costos abajo) con **firewall UFW**: solo 80/443 abiertos; **SSH por llave** (sin password) en puerto no estándar.
  - **Cloudflare como WAF + anti-DDoS** delante de todo: filtra ataques antes de llegar al servidor, oculta la IP real.
  - **fail2ban** para bloquear IPs con intentos de fuerza bruta.
  - Actualizaciones automáticas de seguridad del SO (`unattended-upgrades`).
- **Aplicación**
  - **2FA obligatorio** para rectores, secretarías y súper admin.
  - Contraseñas con **hash bcrypt/argon2** (nunca en texto plano); tokens de sesión con expiración.
  - Rate limiting por IP y por usuario en endpoints sensibles (login, firma).
  - Validación estricta de entradas (ya se usa Pydantic) → mitiga inyección.
  - **Aislamiento por tenant** (schema PostgreSQL) → un colegio jamás puede leer datos de otro, ni con un bug.
  - Todo el sistema sobre **HTTPS**; cookies `Secure` + `HttpOnly` + `SameSite`.
- **Datos y respaldo**
  - **Backups 3-2-1**: 3 copias, 2 medios, 1 fuera de sitio. Backup diario automático de PostgreSQL, cifrado, a almacenamiento externo (ej. Backblaze B2 / S3).
  - **Secretos en variables de entorno** (`.env` fuera del repo, ya está en `.gitignore`), nunca en el código.
  - Registro de auditoría inmutable (el **log de metadatos** ya captura cada acción con actor y fecha → sirve para forense).
- **Operación**
  - Monitoreo de disponibilidad (UptimeRobot) y de errores (Sentry).
  - Plan de respuesta a incidentes y política de acceso mínimo (cada quién ve solo su tenant y su rol).

> Ninguna medida individual hace un sistema "imposible de hackear", pero estas capas juntas lo vuelven un blanco caro y poco atractivo, que es el objetivo real.

## 4. Costos de mantenimiento (estimación mensual)

Cifras **aproximadas** para dimensionar; varían por proveedor, uso y negociación. En **USD/mes**.

| Concepto | Rango estimado | Notas |
|---|---:|---|
| **VPS** (Hostinger KVM / Hetzner / DigitalOcean) | $8 – $40 | Arranca chico (2–4 GB RAM) y escala. Un VPS soporta decenas de colegios pequeños. |
| **PostgreSQL gestionado** (opcional) | $0 – $25 | $0 si corre en el mismo VPS; gestionado da backups y alta disponibilidad. |
| **Cloudflare** (WAF, DNS, CDN) | $0 – $20 | El plan gratis ya da WAF básico + anti-DDoS + TLS. Pro para reglas avanzadas. |
| **Dominios** | ~$1 – $3 por dominio | `.edu.co`/`.co` anual prorrateado. Uno por institución. |
| **Backups externos** (B2/S3) | $1 – $5 | Cifrados, fuera de sitio. |
| **WhatsApp (Meta Cloud API)** | Variable | Se cobra **por conversación**; las de "servicio" iniciadas por el usuario suelen ser gratis dentro de la ventana de 24 h. Presupuestar según volumen de alertas a acudientes. |
| **Correo transaccional** (opcional, Resend/SES) | $0 – $10 | Para correos desde el dominio del colegio. |
| **Monitoreo** (UptimeRobot/Sentry) | $0 – $26 | Planes gratuitos suficientes al inicio. |

**Escalado por tamaño:**
- **Piloto (1–5 colegios):** 1 VPS pequeño + Cloudflare free + PostgreSQL local. **~$15–40/mes total** + dominios + WhatsApp por uso.
- **Municipio (10–30 colegios):** VPS mediano (8 GB) o 2 nodos + PostgreSQL gestionado + Cloudflare Pro. **~$80–200/mes** + dominios + WhatsApp.
- **Departamental (100+ colegios):** varios nodos con balanceador, réplica de BD, backups gestionados. Se dimensiona por carga real; el costo por colegio **baja** con escala.

> Regla práctica: el costo de infraestructura por colegio pequeño tiende a ser de **pocos dólares al mes**; el grueso del costo real es soporte, WhatsApp (si hay mucho volumen) y el tiempo de operación.

## 5. Ruta sugerida hacia real (cuando se dé la orden)

1. **Migrar de SQLite a PostgreSQL** con schema por tenant (el modelo de datos ya está listo).
2. **Middleware de dominio → tenant** y branding 100% por tenant (marca blanca).
3. **Autenticación real**: JWT + 2FA + roles (la base de auth ya existe en la demo).
4. **Integraciones reales** (reemplazar los simuladores): WhatsApp (Meta Cloud API), SECOP II, datos.gov.co (API SODA), correo del dominio.
5. **Despliegue** en VPS con Docker + Cloudflare + backups + monitoreo (el `Dockerfile` y `docker-compose.yml` ya están en el repo).
6. **Piloto con 1 colegio real** → medir, ajustar, y luego escalar a la secretaría completa.

---

*Todo el ecosistema de producto ya está construido y probado en la demo. Este documento es el puente hacia la operación real; se ejecuta paso a paso cuando el negocio lo requiera.*

---

# 🔌 Anexo v4 — Migración a producción: "solo conectar cables"

Todo el ecosistema ya está construido. Esta es la lista exacta de cables por conectar, en orden.

## Cable 1 · Base de datos: SQLite → PostgreSQL (pgAdmin)

El código usa SQLAlchemy, así que **el cambio es de una línea**: la cadena de conexión.

```bash
# .env de producción
DATABASE_URL=postgresql+psycopg2://gyver:CLAVE@db:5432/gyverlabs
```

`backend/database.py` ya lee `DATABASE_URL` del entorno; si no existe, cae a SQLite (modo demo). Pasos:

1. Levantar PostgreSQL (ver Cable 2) y crear la base desde **pgAdmin**: clic derecho en *Databases → Create → Database* → nombre `gyverlabs`.
2. Crear el rol de aplicación con permisos mínimos (no usar `postgres` para la app):
   ```sql
   CREATE ROLE gyver LOGIN PASSWORD 'CLAVE_FUERTE';
   GRANT CONNECT ON DATABASE gyverlabs TO gyver;
   ```
3. Crear las tablas: `python -c "from database import Base, engine; import models; Base.metadata.create_all(engine)"`.
4. Cargar datos reales (o `seed_data.py` para un piloto de demostración).
5. **Aislamiento por institución:** un schema por tenant.
   ```sql
   CREATE SCHEMA ietac AUTHORIZATION gyver;
   CREATE SCHEMA ietli AUTHORIZATION gyver;
   ```
   El middleware de dominio (Cable 4) hace `SET search_path TO <schema>` en cada petición. Un colegio nunca puede leer datos de otro, aunque hubiera un bug en el código.

> Migraciones: se recomienda añadir **Alembic** (`alembic init migrations`) antes del primer despliegue real, para versionar los cambios de modelo sin perder datos.

## Cable 2 · Docker

El repo ya trae `Dockerfile` y `docker-compose.yml`. Para producción el compose queda así (servicios: base de datos, pgAdmin, API y proxy):

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: gyverlabs
      POSTGRES_USER: gyver
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes: [pgdata:/var/lib/postgresql/data]
    restart: always

  pgadmin:
    image: dpage/pgadmin4
    environment:
      PGADMIN_DEFAULT_EMAIL: ${ADMIN_EMAIL}
      PGADMIN_DEFAULT_PASSWORD: ${ADMIN_PASSWORD}
    ports: ["127.0.0.1:5050:80"]   # solo accesible por túnel SSH, nunca público
    depends_on: [db]

  api:
    build: ./backend
    environment:
      DATABASE_URL: postgresql+psycopg2://gyver:${DB_PASSWORD}@db:5432/gyverlabs
      SECRET_KEY: ${SECRET_KEY}
    depends_on: [db]
    restart: always

  proxy:
    image: caddy:2          # TLS automático por dominio
    ports: ["80:80", "443:443"]
    volumes: [./Caddyfile:/etc/caddy/Caddyfile, caddydata:/data]
    depends_on: [api]

volumes: { pgdata: {}, caddydata: {} }
```

Comandos: `docker compose up -d` para levantar, `docker compose logs -f api` para ver la API, `docker compose exec db pg_dump -U gyver gyverlabs > backup.sql` para respaldo.

**pgAdmin nunca se expone a internet**: se publica solo en `127.0.0.1` y se accede por túnel SSH (`ssh -L 5050:localhost:5050 usuario@servidor`).

## Cable 3 · Dominios por institución (marca blanca)

`Caddyfile` — cada colegio con su dominio, TLS automático, sin rastro de la plataforma:

```
ietac.edu.co, www.ietac.edu.co {
    reverse_proxy api:8000
    header -Server
    header -X-Powered-By
}
ietli.edu.co, www.ietli.edu.co {
    reverse_proxy api:8000
    header -Server
}
```

En el DNS de cada dominio: un registro `A` apuntando a la IP del servidor (o a Cloudflare en modo proxy). El campo **dominio** del tenant ya existe en el sistema y se llena al crear la institución.

## Cable 4 · Middleware dominio → tenant

Una función en `main.py` que lee el `Host` y fija el schema de la petición:

```python
@app.middleware("http")
async def tenant_por_dominio(request, call_next):
    host = request.headers.get("host", "").split(":")[0]
    tenant = resolver_tenant(host)          # consulta tabla tenants (cacheada)
    request.state.tenant = tenant
    # la sesión de BD hace: SET search_path TO {tenant.schema}
    return await call_next(request)
```

Con esto, el mismo contenedor sirve a todas las instituciones y cada una ve solo lo suyo, con **su logo y sus colores** (el branding por tenant ya está implementado: `Tenant.logo`, `Tenant.color`).

## Cable 5 · Autenticación real

La demo entra por selector de perfiles. En producción:

- Login con usuario/contraseña, hash **argon2** o **bcrypt** (`passlib` ya está en requirements).
- **JWT** con expiración corta + refresh token (`python-jose` ya está en requirements).
- **2FA obligatorio** para rector, secretaría y súper admin (TOTP con `pyotp`).
- Los alumnos entran con su **código de acceso** (ya implementado: campo `codigo_acceso`) más contraseña propia.
- Middleware que valide rol y tenant en cada endpoint (los roles ya existen en el modelo).

## Cable 6 · Integraciones reales (reemplazar simuladores)

| Simulado hoy | Conectar a |
|---|---|
| `MensajeWhatsApp` (estado "ENVIADO (simulado)") | **WhatsApp Cloud API** de Meta: token permanente, plantillas aprobadas para alertas de ausencia, notas y firmas |
| Firma OTP simulada | Proveedor de **firma electrónica certificada** (Certicámara, Andes SCD) + biometría si se requiere |
| SECOP 2 simulado | **SECOP II** — publicación y consulta de procesos |
| `datos.gov.co` simulado | API **SODA** de datos abiertos |
| Guías en HTML imprimible | Se mantiene (funciona) o WeasyPrint para PDF nativo |
| Correo | SES / Resend desde el dominio del colegio (`@ietac.edu.co`) |

## Cable 7 · Respaldo y monitoreo

```bash
# backup diario cifrado, fuera del servidor (cron 2 a.m.)
0 2 * * * docker compose exec -T db pg_dump -U gyver gyverlabs | gzip | \
  gpg -c --passphrase-file /root/.bkey > /backups/gyver_$(date +\%F).sql.gz.gpg
```
Enviar a almacenamiento externo (Backblaze B2 / S3) y probar la **restauración** una vez al mes — un backup sin probar no es un backup. Monitoreo: UptimeRobot (disponibilidad) + Sentry (errores).

## Checklist de corte a producción

- [ ] `DATABASE_URL` apuntando a PostgreSQL y tablas creadas
- [ ] Schema por tenant + middleware de dominio activo
- [ ] `SECRET_KEY` y contraseñas en `.env` (nunca en el repo)
- [ ] Alembic inicializado para migraciones futuras
- [ ] Dominios `.edu.co` registrados y apuntando al servidor
- [ ] TLS activo en todos los dominios (Caddy/Cloudflare)
- [ ] Login real + 2FA para directivos
- [ ] WhatsApp Cloud API con plantillas aprobadas
- [ ] Backups automáticos probados (restauración verificada)
- [ ] UFW + fail2ban + Cloudflare WAF activos
- [ ] pgAdmin accesible solo por túnel SSH
- [ ] Logo y dominio cargados por institución (marca blanca verificada)

Con estos cables conectados, el sistema pasa de demostración a operación real sin reescribir la lógica: **el ecosistema completo ya está construido y probado.**
