# 🌐 Conectar el dominio de cada institución

Guía práctica para el súper admin. Explica cómo pasar de la demo local a que
cada colegio entre por **su propia dirección**, sin rastro de GyverLabs.

---

## El escenario real

Casi todos los colegios ya tienen su página web en **WordPress**
(`ietac.edu.co`). Esa página no se toca: el sistema se monta **al lado**, en un
subdominio. Es lo más seguro y lo más rápido.

```
ietac.edu.co            → sigue siendo la página en WordPress (noticias, fotos)
sistema.ietac.edu.co    → el sistema educativo
```

---

## Los 3 modos disponibles en el panel

| Modo | Cuándo usarlo | Queda como |
|---|---|---|
| **Subdominio** (recomendado) | El colegio ya tiene web y no la quiere tocar | `sistema.ietac.edu.co` |
| **Dominio completo** | El colegio no tiene web o la va a reemplazar | `ietac.edu.co` |
| **Subcarpeta** | Se quiere un solo dominio (requiere tocar el servidor de WP) | `ietac.edu.co/plataforma` |

---

## Paso a paso (lo que hace el panel por ti)

1. **El colegio compra su dominio** donde quiera: Hostinger, GoDaddy, Namecheap.
   Para un `.edu.co` se requiere soporte de que es institución educativa.
2. En el sistema: **Súper Admin → 🌐 Dominios y contratos → ⚙️ Configurar**.
3. Escoges el modo, escribes el dominio y el proveedor. El panel **genera los
   registros DNS exactos**.
4. Copias los registros y los pegas en el panel del proveedor:

   | Tipo | Nombre | Valor | TTL |
   |---|---|---|---|
   | A | `sistema` | IP del servidor | 3600 |
   | CNAME | `www.sistema` | `sistema.ietac.edu.co` | 3600 |
   | TXT | `_gyver-verify` | código de verificación | 3600 |

5. Presionas **🔍 Verificar**. La propagación tarda de 5 minutos a 24 horas.
6. Cuando queda en verde, **el certificado SSL se emite solo** (Caddy/Let's Encrypt).

---

## Conectar con el WordPress existente

El panel ofrece cuatro formas, en la pestaña **🔌 Sitio actual**:

- **🔗 Botón en el menú** (recomendado): en WordPress → *Apariencia → Menús →
  Enlace personalizado* → se pega `https://sistema.ietac.edu.co`. Cero riesgo.
- **🧩 Plugin de conexión**: muestra el acceso y el estado dentro de WordPress,
  con inicio de sesión unificado. Requiere desarrollar el plugin
  (`GyverLabs Connect`) usando la API de `/usuarios/login`.
- **🖼️ Incrustado (iframe)**: funciona, pero se pierde experiencia en celular.
- **🚫 Sin conexión**: el sistema vive aparte.

---

## Servidor: dónde se monta

Con Docker + Caddy (ya está en `docs/PRODUCCION.md`), el `Caddyfile` queda así:

```
sistema.ietac.edu.co {
    reverse_proxy api:8000
    header -Server
    header -X-Powered-By
}
sistema.ietli.edu.co {
    reverse_proxy api:8000
    header -Server
}
```

Caddy pide el certificado SSL automáticamente para cada dominio nuevo. **Agregar
un colegio nuevo es agregar tres líneas** y recargar.

El middleware `dominio → tenant` (Cable 4 en `PRODUCCION.md`) lee el `Host` de
cada petición y sirve los datos de esa institución con su logo y sus colores.

---

## Contrato comercial por institución

En la pestaña **💰 Contrato** se registra por tenant:

- Plan (piloto / institucional / municipal / departamental)
- Fecha de inicio y duración → el sistema calcula **cuántos días faltan**
- Valor anual y los **pagos recibidos**, con saldo pendiente
- Alertas automáticas de **por vencer** (45 días antes) y **vencido**

El panel principal muestra el consolidado: facturación anual, recaudado y por
cobrar de toda la red.

---

## Checklist para el primer colegio real

- [ ] Dominio comprado y con acceso al panel DNS
- [ ] Servidor con Docker corriendo y su IP fija
- [ ] Modo escogido (normalmente subdominio)
- [ ] Registros DNS pegados y verificados en verde
- [ ] SSL activo (candado en el navegador)
- [ ] Logo y colores del colegio cargados en el tenant
- [ ] Botón agregado en el menú de WordPress
- [ ] Contrato registrado con fechas y valor
- [ ] Usuarios del colegio creados y aprobados
