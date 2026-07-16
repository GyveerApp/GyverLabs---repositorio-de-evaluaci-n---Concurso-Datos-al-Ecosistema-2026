# GyverLabs Frontend

Repositorio de evaluación. Ver [`LICENSE`](../LICENSE) en la raíz del proyecto.

## Demo funcional: `index.html` + `app.js`

**Abre `frontend/index.html` en tu navegador — no requiere instalación ni servidor.**
Es una demostración autocontenida (HTML/CSS en `index.html`, lógica en `app.js`, ambos
en la misma carpeta) con datos simulados que reproduce la experiencia completa del panel
institucional: login, dashboard con listado de salones, deserción (SRD) con notificaciones
a acudientes y rectoría, asistencia con 4 estados, aula virtual interactiva, notas,
contabilidad FSE completa (movimientos, RP, plan anual de compras, informe de auditoría
frente a SECOP II) y gestión de usuarios. Sirve para presentar la solución ante el jurado
sin depender de instalar Node, levantar builds, ni tener conexión a internet.

Si además tienes el backend corriendo (`./ejecutar_backend.sh`), la demo detecta la
conexión automáticamente y reemplaza el mapa de calor, el ranking SRD y los movimientos
FSE por los datos calculados en vivo por el modelo LightGBM real — verás el indicador
**🟢 Conectado al backend en vivo** en la barra lateral. Si el backend no está disponible,
la demo sigue funcionando igual con los datos de respaldo: nunca depende de un solo punto
de falla durante la presentación.

## Stack de producción real: Next.js 14 (App Router)

El frontend de producción (no incluido completo en este repositorio de evaluación,
ver `LICENSE`) se construye sobre la siguiente estructura

```
src/app/
├── (superadmin)/     ← Panel global: tenants, secretarías, planes
├── (secretaria)/      ← Panel departamental: mapa de riesgo, FSE consolidado
├── (colegio)/         ← Panel del colegio: asistencia, aula virtual, SRD, contabilidad
│   ├── asistencia/
│   ├── aula/
│   ├── contabilidad/
│   ├── desercion/     ← Tablero SRD (mapa de calor, ficha del estudiante)
│   └── certificados/
└── verificar/[codigo]/ ← Página pública de verificación de certificados QR
```

Cada grupo de rutas usa un layout distinto según el rol (Super Admin, Admin
Secretaría, Rector/Coordinador/Docente/Estudiante dentro del colegio), con
tema visual (logo y colores) cargado dinámicamente por tenant.

## Por qué no está el código completo aquí

Los componentes de visualización del tablero SRD (`SRDHeatmap`, `SRDGauge`,
`TendenciaChart`) consumen directamente los resultados del motor de IA
protegido descrito en `backend/services/srd_service.py`. Se incluye a
continuación un componente de ejemplo (`ExampleCard.tsx`) que muestra el
patrón de diseño y consumo de API usado en toda la aplicación real.

## Stack

Next.js 14 · TypeScript · TailwindCSS · Zustand · PWA (next-pwa) con soporte
offline-first para zonas rurales de baja conectividad.
