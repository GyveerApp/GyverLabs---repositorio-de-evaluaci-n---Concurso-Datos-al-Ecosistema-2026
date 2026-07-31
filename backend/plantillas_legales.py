"""Plantillas de los documentos legales, calcadas de los reales.

Cada documento sale con el membrete de la institucion (ordenanza, decreto,
licencia, NIT, DANE) y toma sus fechas de la REJILLA, que es el registro
maestro. Cambiando los datos de la rejilla cambian todos los documentos.
"""

MESES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def fecha_larga(d):
    if not d:
        return "____________"
    return f"{d.day} de {MESES[d.month]} de {d.year}"


def fecha_corta(d):
    return d.isoformat() if d else "__________"


def pesos(v):
    return f"${round(v or 0):,}".replace(",", ".")


UNI = ["", "UN", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE",
       "DIEZ", "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE", "DIECISÉIS", "DIECISIETE",
       "DIECIOCHO", "DIECINUEVE", "VEINTE", "VEINTIUNO", "VEINTIDÓS", "VEINTITRÉS",
       "VEINTICUATRO", "VEINTICINCO", "VEINTISÉIS", "VEINTISIETE", "VEINTIOCHO",
       "VEINTINUEVE", "TREINTA"]
DEC = ["", "", "VEINTE", "TREINTA", "CUARENTA", "CINCUENTA", "SESENTA", "SETENTA",
       "OCHENTA", "NOVENTA"]
CEN = ["", "CIENTO", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS", "QUINIENTOS",
       "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS"]


def _h999(x):
    if x == 0:
        return ""
    if x == 100:
        return "CIEN"
    c, r = divmod(x, 100)
    out = CEN[c]
    if r:
        if r <= 30:
            out += (" " if out else "") + UNI[r]
        else:
            d, u = divmod(r, 10)
            out += (" " if out else "") + DEC[d] + (" Y " + UNI[u] if u else "")
    return out.strip()


def numero_letras(n):
    """Valor en letras, como lo exige la minuta."""
    n = int(round(n or 0))
    if n == 0:
        return "CERO PESOS M/CTE"
    mill, resto = divmod(n, 1_000_000)
    miles, uni = divmod(resto, 1000)
    p = []
    if mill:
        p.append("UN MILLÓN" if mill == 1 else _h999(mill) + " MILLONES")
    if miles:
        p.append("MIL" if miles == 1 else _h999(miles) + " MIL")
    if uni:
        p.append(_h999(uni))
    return " ".join(p) + " PESOS M/CTE"


def dias_letras(n):
    n = int(n or 0)
    return f"{UNI[n] if n <= 30 else str(n)} ({n:02d}) DÍAS"


# ═══════════════ MEMBRETE COMÚN ═══════════════
def membrete(pl):
    """El encabezado que llevan TODOS los documentos de la institución."""
    logo_i = (f'<img src="{pl.logo_izq}" class="logo">' if pl.logo_izq else
              '<div class="logo-ph">🏫</div>')
    logo_d = (f'<img src="{pl.logo_der}" class="logo">' if pl.logo_der else
              '<div class="logo-ph">🇨🇴</div>')
    return f"""<div class="membrete">
  <div class="mb-l">{logo_i}</div>
  <div class="mb-c">
    <div class="mb-nom">{pl.nombre_oficial or 'INSTITUCIÓN EDUCATIVA'}</div>
    <div class="mb-sub">
      {f'Organizada Según Ordenanza {pl.ordenanza}<br>' if pl.ordenanza else ''}
      {f'Reglamentada Mediante Decreto N° {pl.decreto}<br>' if pl.decreto else ''}
      {f'Licencia de Funcionamiento {pl.licencia}<br>' if pl.licencia else ''}
      {(pl.municipio or '') + (' - ' + pl.departamento if pl.departamento else '')}<br>
      <b>NIT:</b> {pl.nit or '—'}{f' D.V: {pl.nit_dv}' if pl.nit_dv else ''}
      &nbsp;&nbsp;<b>DANE:</b> {pl.dane or '—'}
    </div>
  </div>
  <div class="mb-r">{logo_d}</div>
</div>"""


CSS_BASE = """
 @page{size:letter;margin:1.6cm}
 body{font-family:'Times New Roman',Georgia,serif;max-width:800px;margin:20px auto;
   padding:0 30px;color:#1B2530;line-height:1.55;font-size:.94rem;text-align:justify}
 .membrete{display:flex;align-items:center;gap:14px;border-bottom:2.5px solid #1B2530;
   padding-bottom:10px;margin-bottom:18px}
 .mb-l,.mb-r{width:78px;text-align:center;flex-shrink:0}
 .logo{max-width:74px;max-height:74px;object-fit:contain}
 .logo-ph{font-size:2.2rem;opacity:.35}
 .mb-c{flex:1;text-align:center}
 .mb-nom{font-weight:bold;font-size:1.02rem;line-height:1.25;text-transform:uppercase}
 .mb-sub{font-size:.68rem;line-height:1.4;color:#334155;margin-top:3px}
 h1{text-align:center;font-size:1.05rem;letter-spacing:.06em;margin:16px 0 4px;text-transform:uppercase}
 h2{font-size:.95rem;margin:18px 0 6px;text-transform:uppercase;border-bottom:1px solid #CBD5E1;padding-bottom:3px}
 .doc-num{text-align:center;font-size:.86rem;color:#475569;margin-bottom:14px}
 table{width:100%;border-collapse:collapse;margin:12px 0;font-size:.86rem}
 td,th{border:1px solid #64748B;padding:5px 8px;vertical-align:top}
 th{background:#E2E8F0;font-weight:bold;text-align:left}
 .tk{background:#F1F5F9;font-weight:bold;width:32%}
 .cl{margin-bottom:10px;text-align:justify}
 .firmas{display:flex;justify-content:space-between;gap:36px;margin-top:56px;page-break-inside:avoid}
 .firmas div{flex:1;border-top:1px solid #1B2530;padding-top:5px;text-align:center;font-size:.8rem}
 .firma-img{max-height:52px;margin-bottom:-4px}
 .pie{margin-top:26px;padding-top:8px;border-top:1px solid #CBD5E1;
   font-size:.66rem;color:#64748B;text-align:center}
 .noprint{background:#FEF3C7;border:1px solid #FCD34D;border-radius:8px;padding:9px 13px;
   margin-bottom:14px;font-family:system-ui;font-size:.83rem}
 ol{padding-left:20px} li{margin-bottom:5px}
 .sello{border:1.5px dashed #94A3B8;border-radius:6px;padding:8px 12px;font-size:.76rem;
   color:#475569;margin-top:14px}
 @media print{.noprint{display:none}body{margin:0;padding:0}}
"""


def envolver(titulo, pl, cuerpo, extra_css=""):
    return f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<title>{titulo}</title><style>{CSS_BASE}{extra_css}</style></head>
<body onload="setTimeout(()=>window.print(),450)">
<div class="noprint">💡 En el diálogo de impresión elige <b>«Guardar como PDF»</b> para descargarlo.
 <button onclick="window.print()" style="margin-left:8px">🖨️ Imprimir</button></div>
{membrete(pl)}
{cuerpo}
<div class="pie">
 {pl.direccion or ''} · {pl.municipio or ''}{', ' + pl.departamento if pl.departamento else ''}
 {' · Tel. ' + pl.telefono if pl.telefono else ''}{' · ' + pl.email if pl.email else ''}
 {'<br>' + pl.pie_pagina if pl.pie_pagina else ''}
</div></body></html>"""


# ═══════════════ 1. SOLICITUD DE COTIZACIÓN ═══════════════
def solicitud_cotizacion(pl, r, items, proveedor=None):
    filas = "".join(
        f"<tr><td style='text-align:center'>{i}</td><td>{it.get('descripcion','')}</td>"
        f"<td style='text-align:center'>{it.get('unidad','UND')}</td>"
        f"<td style='text-align:center'>{it.get('cantidad',1)}</td>"
        f"<td></td><td></td></tr>"
        for i, it in enumerate(items or [{"descripcion": r.descripcion or "", "cantidad": 1}], 1))
    cuerpo = f"""
<h1>SOLICITUD DE COTIZACIÓN</h1>
<div class="doc-num">{pl.municipio or ''}, {fecha_larga(r.cotizacion_fecha or r.cdp_fecha)}</div>
<p><b>Señores:</b><br>{(proveedor or 'PROVEEDORES INTERESADOS').upper()}<br>
La ciudad</p>
<p><b>Asunto:</b> Solicitud de cotización — {r.descripcion or ''}</p>
<p>Cordial saludo,</p>
<p>La <b>{pl.nombre_oficial}</b>, identificada con NIT {pl.nit or ''}{'-' + pl.nit_dv if pl.nit_dv else ''},
en cumplimiento del principio de selección objetiva y con el fin de establecer el
presupuesto oficial del proceso, se permite solicitar cotización para el siguiente objeto:</p>
<p style="text-align:center"><b>{(r.descripcion or '').upper()}</b></p>
<table>
 <thead><tr><th style="width:6%">ÍTEM</th><th>DESCRIPCIÓN</th><th style="width:10%">UND</th>
 <th style="width:10%">CANT.</th><th style="width:16%">VR. UNITARIO</th><th style="width:16%">VR. TOTAL</th></tr></thead>
 <tbody>{filas}
 <tr><td colspan="5" style="text-align:right"><b>SUBTOTAL</b></td><td></td></tr>
 <tr><td colspan="5" style="text-align:right"><b>IVA</b></td><td></td></tr>
 <tr><td colspan="5" style="text-align:right"><b>TOTAL</b></td><td></td></tr>
 </tbody></table>
<p>La cotización deberá incluir todos los costos directos e indirectos, impuestos,
transporte e instalación a que haya lugar, y tener una validez mínima de treinta (30) días.</p>
<p>Agradecemos remitir la propuesta a más tardar el
<b>{fecha_larga(r.invitacion_fecha or r.cotizacion_fecha)}</b>, junto con copia del RUT
y del documento de identidad o certificado de existencia y representación legal.</p>
<p>Atentamente,</p>
<div class="firmas">
 <div>{('<img class="firma-img" src="' + pl.rector_firma + '">') if pl.rector_firma else ''}
  <b>{pl.rector_nombre or 'RECTOR(A)'}</b><br>Rector(a) — Ordenador(a) del Gasto<br>
  C.C. {pl.rector_cc or ''}</div>
</div>"""
    return envolver("Solicitud de cotización", pl, cuerpo)


# ═══════════════ 2. ESTUDIOS PREVIOS / PROYECTO ═══════════════
def estudios_previos(pl, r, datos):
    d = datos or {}
    items = d.get("items", [])
    filas = "".join(
        f"<tr><td>{i}</td><td>{it.get('descripcion','')}</td>"
        f"<td style='text-align:center'>{it.get('cantidad',1)}</td>"
        f"<td style='text-align:right'>{pesos(it.get('valor_unitario',0))}</td>"
        f"<td style='text-align:right'>{pesos(it.get('cantidad',1)*it.get('valor_unitario',0))}</td></tr>"
        for i, it in enumerate(items, 1)) or \
        f"<tr><td>1</td><td>{r.descripcion or ''}</td><td style='text-align:center'>1</td>" \
        f"<td style='text-align:right'>{pesos(r.valor)}</td><td style='text-align:right'>{pesos(r.valor)}</td></tr>"
    cuerpo = f"""
<h1>ESTUDIOS PREVIOS Y ANÁLISIS DEL SECTOR</h1>
<div class="doc-num">Proceso de mínima cuantía · Vigencia {r.vigencia}</div>
<table>
 <tr><td class="tk">PROYECTO</td><td>{r.descripcion or ''}</td></tr>
 <tr><td class="tk">DEPENDENCIA SOLICITANTE</td><td>{d.get('dependencia','Rectoría')}</td></tr>
 <tr><td class="tk">FECHA</td><td>{fecha_larga(r.proyecto_fecha or r.cdp_fecha)}</td></tr>
 <tr><td class="tk">LOCALIZACIÓN</td><td>{pl.municipio or ''}, {pl.departamento or ''}</td></tr>
 <tr><td class="tk">RUBRO PRESUPUESTAL</td><td>{r.rubro_codigo or ''} — {r.rubro_nombre or ''}</td></tr>
 <tr><td class="tk">FUENTE DE FINANCIACIÓN</td><td>{r.fuente or 'Recursos de gratuidad'}</td></tr>
 <tr><td class="tk">CÓDIGO UNSPSC</td><td>{r.unspsc or '—'}</td></tr>
 <tr><td class="tk">VALOR ESTIMADO</td><td>{pesos(r.valor)} — {numero_letras(r.valor)}</td></tr>
</table>

<h2>1. Identificación de la necesidad</h2>
<p>{d.get('necesidad', f'La institución requiere {(r.descripcion or "").lower()} '
   'para garantizar la adecuada prestación del servicio educativo y el bienestar '
   'de la comunidad estudiantil.')}</p>

<h2>2. Población beneficiada</h2>
<p>{d.get('poblacion', f'Estudiantes, docentes y personal administrativo de la '
   f'{pl.nombre_oficial}, así como la comunidad educativa en general.')}</p>

<h2>3. Objetivo</h2>
<p>{d.get('objetivo', f'Contratar {(r.descripcion or "").lower()} conforme a las '
   'especificaciones técnicas requeridas por la institución.')}</p>

<h2>4. Justificación</h2>
<p>{d.get('justificacion', 'La contratación se justifica en la necesidad de mantener '
   'en condiciones óptimas los bienes y servicios que soportan la prestación del '
   'servicio educativo, en concordancia con el Proyecto Educativo Institucional (PEI) '
   'y el plan de compras aprobado por el Consejo Directivo.')}</p>

<h2>5. Fundamento jurídico</h2>
<p>El presente proceso se adelanta bajo el régimen especial de contratación de los
Fondos de Servicios Educativos, previsto en el Decreto 1075 de 2015 (que compiló el
Decreto 4791 de 2008), y en el Acuerdo del Consejo Directivo que reglamenta la
contratación de la institución. Por tratarse de una cuantía inferior a veinte (20)
salarios mínimos legales mensuales vigentes, se aplica el procedimiento simplificado
de invitación pública.</p>

<h2>6. Análisis del sector</h2>
<p><b>Análisis comercial:</b> Se consultó el Sistema Electrónico de Contratación Pública
(SECOP) y se solicitaron cotizaciones a proveedores del sector, con el fin de establecer
el valor de mercado del objeto a contratar.</p>
<p><b>Análisis de la demanda:</b> {d.get('demanda', 'Entidades del sector educativo del '
   'municipio han adelantado procesos similares en la presente vigencia.')}</p>
<p><b>Análisis de la oferta:</b> {d.get('oferta', 'Existen en el mercado local y regional '
   'proveedores con capacidad técnica y jurídica para atender el objeto contractual.')}</p>

<h2>7. Relación de costos</h2>
<table>
 <thead><tr><th style="width:7%">ÍTEM</th><th>DESCRIPCIÓN</th><th style="width:11%">CANT.</th>
 <th style="width:18%">VR. UNIT.</th><th style="width:18%">VR. TOTAL</th></tr></thead>
 <tbody>{filas}
 <tr><td colspan="4" style="text-align:right"><b>TOTAL PRESUPUESTO OFICIAL</b></td>
 <td style="text-align:right"><b>{pesos(r.valor)}</b></td></tr></tbody></table>

<h2>8. Análisis de riesgos</h2>
<table>
 <thead><tr><th>RIESGO</th><th>PROBABILIDAD</th><th>IMPACTO</th><th>MITIGACIÓN</th></tr></thead>
 <tbody>
  <tr><td>Incumplimiento en tiempos de entrega</td><td>Media</td><td>Alto</td>
   <td>Supervisión permanente y cláusula de multas</td></tr>
  <tr><td>Calidad inferior a la ofertada</td><td>Baja</td><td>Alto</td>
   <td>Recibo a satisfacción previo al pago</td></tr>
  <tr><td>Variación de precios</td><td>Baja</td><td>Medio</td>
   <td>Precios fijos durante el plazo del contrato</td></tr>
 </tbody></table>

<h2>9. Garantías</h2>
<p>{d.get('garantias', 'Dada la cuantía y naturaleza del contrato, y conforme al régimen '
   'especial aplicable, no se exige constitución de garantías. El pago se efectuará '
   'contra entrega a satisfacción certificada por el supervisor.')}</p>

<h2>10. Supervisión</h2>
<p>La supervisión estará a cargo de <b>{d.get('supervisor', pl.rector_nombre or 'el Rector')}</b>,
quien verificará el cumplimiento y suscribirá las actas correspondientes.</p>

<div class="firmas">
 <div>{('<img class="firma-img" src="' + pl.rector_firma + '">') if pl.rector_firma else ''}
  <b>{pl.rector_nombre or 'RECTOR(A)'}</b><br>Rector(a) — Ordenador(a) del Gasto</div>
</div>"""
    return envolver("Estudios previos", pl, cuerpo)


# ═══════════════ 3. INVITACIÓN PÚBLICA ═══════════════
def invitacion(pl, r, datos):
    d = datos or {}
    num_inv = r.invitacion_num or f"{r.consecutivo:02d}"
    cuerpo = f"""
<h1>INVITACIÓN PÚBLICA N° {num_inv}</h1>
<div class="doc-num">Proceso de selección de mínima cuantía · Inferior a 20 SMMLV<br>
Vigencia {r.vigencia}</div>

<h2>Capítulo I — Información general</h2>
<table>
 <tr><td class="tk">ENTIDAD CONTRATANTE</td><td>{pl.nombre_oficial}</td></tr>
 <tr><td class="tk">NIT</td><td>{pl.nit or ''}{'-' + pl.nit_dv if pl.nit_dv else ''}</td></tr>
 <tr><td class="tk">OBJETO</td><td>{(r.descripcion or '').upper()}</td></tr>
 <tr><td class="tk">PRESUPUESTO OFICIAL</td><td>{pesos(r.valor)} — {numero_letras(r.valor)}</td></tr>
 <tr><td class="tk">CDP</td><td>N° {r.cdp_num or ''} del {fecha_corta(r.cdp_fecha)}</td></tr>
 <tr><td class="tk">RUBRO</td><td>{r.rubro_codigo or ''} — {r.rubro_nombre or ''}</td></tr>
 <tr><td class="tk">PLAZO DE EJECUCIÓN</td><td>{dias_letras(r.plazo_dias)}</td></tr>
 <tr><td class="tk">MODALIDAD</td><td>Mínima cuantía — Régimen especial FSE</td></tr>
</table>

<h2>Capítulo II — Cronograma</h2>
<table>
 <thead><tr><th>ACTUACIÓN</th><th style="width:30%">FECHA</th><th style="width:26%">LUGAR</th></tr></thead>
 <tbody>
  <tr><td>Publicación de la invitación</td><td>{fecha_corta(r.invitacion_fecha)}</td>
   <td>Cartelera institucional y SECOP</td></tr>
  <tr><td>Presentación de ofertas</td>
   <td>Hasta el {fecha_corta(r.cierre_fecha)} a las 4:00 p.m.</td><td>Rectoría</td></tr>
  <tr><td>Evaluación de ofertas</td><td>{fecha_corta(r.evaluacion_fecha)}</td><td>Rectoría</td></tr>
  <tr><td>Aceptación de oferta</td><td>{fecha_corta(r.aceptacion_fecha)}</td><td>Rectoría</td></tr>
  <tr><td>Suscripción del contrato</td><td>{fecha_corta(r.contrato_fecha)}</td><td>Rectoría</td></tr>
  <tr><td>Acta de inicio</td><td>{fecha_corta(r.acta_inicio_fecha)}</td><td>Rectoría</td></tr>
 </tbody></table>

<h2>Capítulo III — Requisitos habilitantes</h2>
<p><b>Personas naturales:</b></p>
<ol>
 <li>Carta de presentación de la oferta debidamente suscrita (Anexo 1).</li>
 <li>Fotocopia de la cédula de ciudadanía.</li>
 <li>Registro Único Tributario (RUT) actualizado.</li>
 <li>Certificado de antecedentes disciplinarios (Procuraduría).</li>
 <li>Certificado de antecedentes fiscales (Contraloría).</li>
 <li>Certificado de antecedentes judiciales (Policía Nacional).</li>
 <li>Consulta del Registro Nacional de Medidas Correctivas.</li>
 <li>Certificación de afiliación y pago al Sistema de Seguridad Social.</li>
 <li>Certificación bancaria no mayor a treinta (30) días.</li>
 <li>Declaración juramentada de no encontrarse incurso en inhabilidades (Anexo 3).</li>
</ol>
<p><b>Personas jurídicas:</b> además de lo anterior, certificado de existencia y
representación legal expedido por la Cámara de Comercio con vigencia no superior a
treinta (30) días, y documento de identidad del representante legal.</p>

<h2>Capítulo IV — Criterios de selección</h2>
<p>La institución seleccionará la oferta que, cumpliendo la totalidad de los requisitos
habilitantes, presente el <b>menor precio</b> y cumpla las especificaciones técnicas.
En caso de empate se preferirá la oferta radicada en primer lugar.</p>

<h2>Capítulo V — Especificaciones técnicas</h2>
<p>{d.get('especificaciones', r.descripcion or '')}</p>

<h2>Anexos</h2>
<ol><li>Anexo 1 — Carta de presentación de la oferta.</li>
<li>Anexo 2 — Oferta económica.</li>
<li>Anexo 3 — Declaración juramentada de inhabilidades e incompatibilidades.</li></ol>

<div class="firmas">
 <div>{('<img class="firma-img" src="' + pl.rector_firma + '">') if pl.rector_firma else ''}
  <b>{pl.rector_nombre or 'RECTOR(A)'}</b><br>Rector(a) — Ordenador(a) del Gasto<br>
  C.C. {pl.rector_cc or ''}</div>
</div>"""
    return envolver(f"Invitación pública {r.invitacion_num or ''}", pl, cuerpo)


# ═══════════════ 4. CONTRATO ═══════════════
CLAUSULAS_ESTANDAR = [
    ("OBJETO", "El CONTRATISTA se obliga para con LA INSTITUCIÓN a {objeto}, "
     "de acuerdo con las especificaciones técnicas contenidas en los estudios previos "
     "y en la propuesta presentada, documentos que hacen parte integral del presente contrato."),
    ("VALOR", "El valor total del presente contrato es la suma de {valor_letras} "
     "({valor}), incluidos todos los impuestos, tasas, contribuciones y demás costos "
     "directos e indirectos a que haya lugar."),
    ("FORMA DE PAGO", "LA INSTITUCIÓN pagará al CONTRATISTA el valor pactado en un solo "
     "contado, una vez ejecutado el objeto contractual, previa presentación de: "
     "a) factura o cuenta de cobro; b) informe de ejecución; c) acta de recibo a "
     "satisfacción suscrita por el supervisor; d) certificación de pago de aportes al "
     "Sistema de Seguridad Social Integral."),
    ("PLAZO DE EJECUCIÓN", "El plazo de ejecución será de {plazo}, contados a partir de "
     "la suscripción del acta de inicio, sin que en ningún caso exceda el 31 de diciembre "
     "de la vigencia fiscal {vigencia}."),
    ("IMPUTACIÓN PRESUPUESTAL", "El valor del presente contrato se imputa al rubro "
     "{rubro_codigo} — {rubro_nombre}, respaldado con el Certificado de Disponibilidad "
     "Presupuestal N° {cdp} del {cdp_fecha} y el Registro Presupuestal N° {rp} "
     "del {rp_fecha}."),
    ("OBLIGACIONES DEL CONTRATISTA", "1) Ejecutar el objeto contractual con la calidad, "
     "cantidad y oportunidad pactadas. 2) Acatar las instrucciones del supervisor. "
     "3) Mantener vigente la afiliación al Sistema de Seguridad Social Integral y "
     "acreditar el pago de aportes. 4) Responder por la calidad de los bienes o servicios "
     "entregados. 5) Presentar los informes que le sean requeridos. 6) Las demás inherentes "
     "a la naturaleza del contrato."),
    ("OBLIGACIONES DE LA INSTITUCIÓN", "1) Pagar el valor del contrato en la forma pactada. "
     "2) Suministrar la información necesaria para la ejecución. 3) Ejercer la supervisión. "
     "4) Expedir el registro presupuestal correspondiente."),
    ("SUPERVISIÓN", "La supervisión del presente contrato será ejercida por "
     "{supervisor}, quien verificará el cumplimiento de las obligaciones, suscribirá las "
     "actas de inicio, recibo final y liquidación, y certificará el recibo a satisfacción."),
    ("INDEPENDENCIA DEL CONTRATISTA", "El CONTRATISTA actuará con plena autonomía técnica "
     "y administrativa. En consecuencia, el presente contrato no genera relación laboral "
     "alguna ni el pago de prestaciones sociales entre LA INSTITUCIÓN y el CONTRATISTA "
     "o el personal que este vincule."),
    ("INHABILIDADES E INCOMPATIBILIDADES", "El CONTRATISTA declara bajo la gravedad del "
     "juramento que no se encuentra incurso en ninguna de las causales de inhabilidad o "
     "incompatibilidad previstas en la Constitución Política y en la ley."),
    ("CESIÓN", "El CONTRATISTA no podrá ceder total ni parcialmente el presente contrato "
     "sin autorización previa, expresa y escrita de LA INSTITUCIÓN."),
    ("MULTAS", "En caso de mora o incumplimiento parcial de las obligaciones, LA INSTITUCIÓN "
     "podrá imponer multas sucesivas equivalentes al uno por ciento (1%) del valor del "
     "contrato por cada día de retraso, sin exceder el diez por ciento (10%) del valor total."),
    ("CLÁUSULA PENAL PECUNIARIA", "En caso de incumplimiento total o parcial definitivo, "
     "el CONTRATISTA pagará a LA INSTITUCIÓN, a título de cláusula penal, el diez por "
     "ciento (10%) del valor del contrato, sin perjuicio de la indemnización de perjuicios."),
    ("CADUCIDAD Y TERMINACIÓN", "LA INSTITUCIÓN podrá declarar la caducidad o dar por "
     "terminado el contrato en forma unilateral cuando se presenten hechos constitutivos "
     "de incumplimiento que afecten de manera grave y directa su ejecución."),
    ("SUSPENSIÓN", "De común acuerdo, las partes podrán suspender la ejecución del contrato "
     "mediante acta motivada, evento en el cual el plazo se reanudará mediante acta de reinicio."),
    ("LIQUIDACIÓN", "El presente contrato se liquidará de común acuerdo dentro de los cuatro "
     "(4) meses siguientes a su terminación, mediante acta suscrita por las partes, en la "
     "cual se dejará constancia del balance de ejecución y del paz y salvo mutuo."),
    ("PERFECCIONAMIENTO Y EJECUCIÓN", "El presente contrato se perfecciona con la firma de "
     "las partes. Para su ejecución se requiere la expedición del registro presupuestal y "
     "la suscripción del acta de inicio."),
    ("DOCUMENTOS DEL CONTRATO", "Hacen parte integral del presente contrato: los estudios "
     "previos, la invitación pública, la propuesta del CONTRATISTA, el CDP, el RP, las "
     "actas que se suscriban y los demás documentos que se generen durante su ejecución."),
    ("DOMICILIO CONTRACTUAL", "Para todos los efectos legales, el domicilio contractual "
     "será el municipio de {municipio}, {departamento}."),
    ("SOLUCIÓN DE CONTROVERSIAS", "Las diferencias que surjan con ocasión de la celebración, "
     "ejecución o liquidación del contrato se resolverán mediante arreglo directo entre "
     "las partes, dentro de los treinta (30) días siguientes a la fecha en que una de "
     "ellas comunique a la otra la existencia de la controversia."),
    ("RÉGIMEN LEGAL APLICABLE", "El presente contrato se rige por el régimen especial de "
     "contratación de los Fondos de Servicios Educativos, contenido en el Decreto 1075 de "
     "2015 y las normas que lo modifiquen, y en lo no previsto por las disposiciones del "
     "derecho privado, conforme a los artículos 13 y 32 de la Ley 80 de 1993."),
    ("PUBLICACIÓN", "El presente contrato será publicado en el Sistema Electrónico de "
     "Contratación Pública (SECOP), conforme a las disposiciones vigentes."),
]

ROMANOS = ["", "PRIMERA", "SEGUNDA", "TERCERA", "CUARTA", "QUINTA", "SEXTA", "SÉPTIMA",
           "OCTAVA", "NOVENA", "DÉCIMA", "DÉCIMA PRIMERA", "DÉCIMA SEGUNDA",
           "DÉCIMA TERCERA", "DÉCIMA CUARTA", "DÉCIMA QUINTA", "DÉCIMA SEXTA",
           "DÉCIMA SÉPTIMA", "DÉCIMA OCTAVA", "DÉCIMA NOVENA", "VIGÉSIMA",
           "VIGÉSIMA PRIMERA", "VIGÉSIMA SEGUNDA", "VIGÉSIMA TERCERA",
           "VIGÉSIMA CUARTA", "VIGÉSIMA QUINTA"]


def contrato(pl, r, datos, clausulas=None):
    d = datos or {}
    ctx = {
        "objeto": r.descripcion or "", "valor": pesos(r.valor),
        "valor_letras": numero_letras(r.valor), "plazo": dias_letras(r.plazo_dias),
        "vigencia": r.vigencia, "rubro_codigo": r.rubro_codigo or "",
        "rubro_nombre": r.rubro_nombre or "", "cdp": r.cdp_num or "",
        "cdp_fecha": fecha_corta(r.cdp_fecha), "rp": r.rp_num or "",
        "rp_fecha": fecha_corta(r.rp_fecha),
        "supervisor": d.get("supervisor", pl.rector_nombre or "el Rector"),
        "municipio": pl.municipio or "", "departamento": pl.departamento or "",
    }
    lista = clausulas or [{"titulo": t, "texto": x} for t, x in CLAUSULAS_ESTANDAR]
    cuerpo_cl = ""
    for i, c in enumerate(lista, 1):
        try:
            txt = c["texto"].format(**ctx)
        except (KeyError, IndexError):
            txt = c["texto"]
        rom = ROMANOS[i] if i < len(ROMANOS) else f"{i}ª"
        cuerpo_cl += f'<p class="cl"><b>CLÁUSULA {rom} — {c["titulo"]}:</b> {txt}</p>'
    cuerpo = f"""
<h1>CONTRATO N° {r.contrato_num or ''}</h1>
<table>
 <tr><td class="tk">CONTRATANTE</td><td>{pl.nombre_oficial}</td></tr>
 <tr><td class="tk">NIT</td><td>{pl.nit or ''}{'-' + pl.nit_dv if pl.nit_dv else ''}</td></tr>
 <tr><td class="tk">REPRESENTANTE LEGAL</td><td>{pl.rector_nombre or ''} — C.C. {pl.rector_cc or ''}</td></tr>
 <tr><td class="tk">CONTRATISTA</td><td>{r.contratista_nombre or ''}</td></tr>
 <tr><td class="tk">IDENTIFICACIÓN</td><td>{r.contratista_doc or ''}</td></tr>
 <tr><td class="tk">DOMICILIO</td><td>{d.get('domicilio_contratista','')}</td></tr>
 <tr><td class="tk">OBJETO</td><td>{(r.descripcion or '').upper()}</td></tr>
 <tr><td class="tk">VALOR</td><td>{pesos(r.valor)} — {numero_letras(r.valor)}</td></tr>
 <tr><td class="tk">PLAZO</td><td>{dias_letras(r.plazo_dias)}</td></tr>
 <tr><td class="tk">CDP N°</td><td>{r.cdp_num or ''} del {fecha_corta(r.cdp_fecha)}</td></tr>
 <tr><td class="tk">RP N°</td><td>{r.rp_num or ''} del {fecha_corta(r.rp_fecha)}</td></tr>
 <tr><td class="tk">RUBRO</td><td>{r.rubro_codigo or ''} — {r.rubro_nombre or ''}</td></tr>
 <tr><td class="tk">FECHA</td><td>{fecha_larga(r.contrato_fecha)}</td></tr>
</table>

<p>Entre los suscritos, <b>{(pl.rector_nombre or 'EL RECTOR').upper()}</b>, mayor de edad,
identificado(a) con cédula de ciudadanía N° {pl.rector_cc or ''} expedida en
{pl.rector_cc_lugar or ''}, quien obra en calidad de Rector(a) y Ordenador(a) del Gasto de la
<b>{pl.nombre_oficial}</b>, {f'posesionado(a) mediante acta N° {pl.rector_acta_posesion}' if pl.rector_acta_posesion else ''}
{f'de fecha {fecha_larga(pl.rector_fecha_posesion)}' if pl.rector_fecha_posesion else ''},
debidamente facultado(a) por el Decreto 1075 de 2015 y por el Acuerdo del Consejo Directivo,
quien en adelante se denominará <b>LA INSTITUCIÓN</b>; y por la otra
<b>{(r.contratista_nombre or 'EL CONTRATISTA').upper()}</b>, identificado(a) con
{r.contratista_doc or ''}, {f"con domicilio en {d.get('domicilio_contratista')}" if d.get('domicilio_contratista') else ''},
quien en adelante se denominará <b>EL CONTRATISTA</b>, hemos acordado celebrar el presente
contrato, previas las siguientes:</p>

<h2>Consideraciones</h2>
<ol>
 <li>Que la institución requiere {(r.descripcion or '').lower()} conforme a la necesidad
  identificada en los estudios previos de fecha {fecha_corta(r.proyecto_fecha)}.</li>
 <li>Que existe disponibilidad presupuestal según CDP N° {r.cdp_num or ''} del
  {fecha_corta(r.cdp_fecha)} por valor de {pesos(r.valor)}, con cargo al rubro
  {r.rubro_codigo or ''} — {r.rubro_nombre or ''}.</li>
 <li>Que se adelantó el proceso de invitación pública N° {r.invitacion_num or ''} del
  {fecha_corta(r.invitacion_fecha)}, dentro del cual el CONTRATISTA presentó la oferta
  más favorable para la institución.</li>
 <li>Que el CONTRATISTA cumple con los requisitos habilitantes exigidos y manifiesta
  no encontrarse incurso en causal de inhabilidad o incompatibilidad.</li>
 <li>Que por tratarse de una contratación de cuantía inferior a veinte (20) SMMLV, se
  aplica el procedimiento simplificado del régimen especial de los Fondos de Servicios
  Educativos.</li>
</ol>
<p>En razón de lo anterior, las partes acuerdan las siguientes:</p>
<h2>Cláusulas</h2>
{cuerpo_cl}

<p style="margin-top:20px">Para constancia se firma en {pl.municipio or ''},
a los {(r.contrato_fecha.day if r.contrato_fecha else 0)} días del mes de
{MESES[r.contrato_fecha.month] if r.contrato_fecha else ''} de
{r.contrato_fecha.year if r.contrato_fecha else r.vigencia}.</p>

<div class="firmas">
 <div>{('<img class="firma-img" src="' + pl.rector_firma + '">') if pl.rector_firma else ''}
  <b>{(pl.rector_nombre or '').upper()}</b><br>Rector(a) — LA INSTITUCIÓN<br>
  C.C. {pl.rector_cc or ''}</div>
 <div><b>{(r.contratista_nombre or '').upper()}</b><br>EL CONTRATISTA<br>
  {r.contratista_doc or ''}</div>
</div>"""
    return envolver(f"Contrato {r.contrato_num or ''}", pl, cuerpo)


# ═══════════════ 5. ACTA DE INICIO ═══════════════
def acta_inicio(pl, r, datos):
    d = datos or {}
    fin = r.acta_final_fecha
    cuerpo = f"""
<h1>ACTA DE INICIO</h1>
<div class="doc-num">Contrato N° {r.contrato_num or ''} · Vigencia {r.vigencia}</div>
<table>
 <tr><td class="tk">CONTRATANTE</td><td>{pl.nombre_oficial}</td></tr>
 <tr><td class="tk">CONTRATISTA</td><td>{r.contratista_nombre or ''} — {r.contratista_doc or ''}</td></tr>
 <tr><td class="tk">OBJETO</td><td>{(r.descripcion or '').upper()}</td></tr>
 <tr><td class="tk">VALOR</td><td>{pesos(r.valor)}</td></tr>
 <tr><td class="tk">PLAZO</td><td>{dias_letras(r.plazo_dias)}</td></tr>
 <tr><td class="tk">FECHA DE INICIO</td><td>{fecha_larga(r.acta_inicio_fecha)}</td></tr>
 <tr><td class="tk">FECHA DE TERMINACIÓN</td><td>{fecha_larga(fin)}</td></tr>
 <tr><td class="tk">CDP / RP</td><td>{r.cdp_num or ''} · {r.rp_num or ''}</td></tr>
</table>

<p>En el municipio de {pl.municipio or ''}, {pl.departamento or ''}, a los
{(r.acta_inicio_fecha.day if r.acta_inicio_fecha else 0)} días del mes de
{MESES[r.acta_inicio_fecha.month] if r.acta_inicio_fecha else ''} de
{r.acta_inicio_fecha.year if r.acta_inicio_fecha else r.vigencia}, se reunieron
<b>{pl.rector_nombre or ''}</b>, identificado(a) con C.C. {pl.rector_cc or ''}, en calidad
de Rector(a) y Ordenador(a) del Gasto de la <b>{pl.nombre_oficial}</b>;
<b>{d.get('supervisor', pl.rector_nombre or '')}</b> en calidad de supervisor(a) del contrato;
y <b>{r.contratista_nombre or ''}</b>, identificado(a) con {r.contratista_doc or ''},
en calidad de CONTRATISTA, con el fin de suscribir la presente acta de inicio, previas
las siguientes</p>

<h2>Consideraciones</h2>
<ol>
 <li>Que el {fecha_corta(r.contrato_fecha)} se suscribió el contrato N° {r.contrato_num or ''},
  cuyo objeto es {(r.descripcion or '').upper()}.</li>
 <li>Que se expidió el Registro Presupuestal N° {r.rp_num or ''} del
  {fecha_corta(r.rp_fecha)}, con lo cual se cumplen los requisitos de ejecución.</li>
 <li>Que el CONTRATISTA acreditó la afiliación y el pago de aportes al Sistema de
  Seguridad Social Integral.</li>
 <li>Que se encuentran satisfechos los requisitos de perfeccionamiento y ejecución
  previstos en el contrato.</li>
</ol>

<h2>Acuerdan</h2>
<p><b>PRIMERO:</b> Dar inicio a la ejecución del contrato N° {r.contrato_num or ''} a partir
del {fecha_larga(r.acta_inicio_fecha)}.</p>
<p><b>SEGUNDO:</b> El plazo de ejecución es de {dias_letras(r.plazo_dias)}, venciendo el
{fecha_larga(fin)}.</p>
<p><b>TERCERO:</b> El CONTRATISTA se compromete a ejecutar el objeto contractual conforme
a las especificaciones técnicas y a las obligaciones pactadas.</p>
<p><b>CUARTO:</b> La supervisión será ejercida por {d.get('supervisor', pl.rector_nombre or '')},
quien velará por el cumplimiento del contrato.</p>

<p>Para constancia se firma por quienes en ella intervinieron.</p>
<div class="firmas">
 <div>{('<img class="firma-img" src="' + pl.rector_firma + '">') if pl.rector_firma else ''}
  <b>{(pl.rector_nombre or '').upper()}</b><br>Rector(a) — Ordenador(a) del Gasto</div>
 <div><b>{(d.get('supervisor', pl.rector_nombre) or '').upper()}</b><br>Supervisor(a)</div>
 <div><b>{(r.contratista_nombre or '').upper()}</b><br>Contratista<br>{r.contratista_doc or ''}</div>
</div>"""
    return envolver("Acta de inicio", pl, cuerpo)


# ═══════════════ 6. ACTA FINAL ═══════════════
def acta_final(pl, r, datos):
    d = datos or {}
    ejec = d.get("valor_ejecutado", r.valor)
    cuerpo = f"""
<h1>ACTA DE RECIBO FINAL A SATISFACCIÓN</h1>
<div class="doc-num">Contrato N° {r.contrato_num or ''} · Vigencia {r.vigencia}</div>
<table>
 <tr><td class="tk">CONTRATANTE</td><td>{pl.nombre_oficial}</td></tr>
 <tr><td class="tk">CONTRATISTA</td><td>{r.contratista_nombre or ''} — {r.contratista_doc or ''}</td></tr>
 <tr><td class="tk">OBJETO</td><td>{(r.descripcion or '').upper()}</td></tr>
 <tr><td class="tk">VALOR DEL CONTRATO</td><td>{pesos(r.valor)}</td></tr>
 <tr><td class="tk">VALOR EJECUTADO</td><td>{pesos(ejec)}</td></tr>
 <tr><td class="tk">FECHA DE INICIO</td><td>{fecha_corta(r.acta_inicio_fecha)}</td></tr>
 <tr><td class="tk">FECHA DE TERMINACIÓN</td><td>{fecha_corta(r.acta_final_fecha)}</td></tr>
</table>

<p>En {pl.municipio or ''}, a los {(r.acta_final_fecha.day if r.acta_final_fecha else 0)} días
del mes de {MESES[r.acta_final_fecha.month] if r.acta_final_fecha else ''} de
{r.acta_final_fecha.year if r.acta_final_fecha else r.vigencia}, se reunieron
<b>{pl.rector_nombre or ''}</b>, Rector(a) de la <b>{pl.nombre_oficial}</b>;
<b>{d.get('supervisor', pl.rector_nombre or '')}</b>, supervisor(a) del contrato; y
<b>{r.contratista_nombre or ''}</b>, CONTRATISTA, con el fin de dejar constancia del
recibo final del objeto contractual.</p>

<h2>Constancias</h2>
<ol>
 <li>Que el CONTRATISTA ejecutó el objeto del contrato N° {r.contrato_num or ''} dentro
  del plazo establecido.</li>
 <li>Que el supervisor verificó el cumplimiento de las obligaciones y las especificaciones
  técnicas pactadas, encontrándolas conformes.</li>
 <li>Que el valor ejecutado asciende a {pesos(ejec)} — {numero_letras(ejec)}.</li>
 <li>Que el CONTRATISTA se encuentra a paz y salvo por concepto de aportes al Sistema
  de Seguridad Social Integral.</li>
 <li>{d.get('observaciones', 'Que no existen observaciones ni reclamaciones pendientes '
     'entre las partes.')}</li>
</ol>

<h2>Recibo a satisfacción</h2>
<p>En consecuencia, LA INSTITUCIÓN <b>RECIBE A SATISFACCIÓN</b> el objeto contratado y
autoriza el trámite del pago correspondiente, previa presentación de la factura o cuenta
de cobro y demás soportes exigidos.</p>

<div class="firmas">
 <div>{('<img class="firma-img" src="' + pl.rector_firma + '">') if pl.rector_firma else ''}
  <b>{(pl.rector_nombre or '').upper()}</b><br>Rector(a)</div>
 <div><b>{(d.get('supervisor', pl.rector_nombre) or '').upper()}</b><br>Supervisor(a)</div>
 <div><b>{(r.contratista_nombre or '').upper()}</b><br>Contratista</div>
</div>"""
    return envolver("Acta final", pl, cuerpo)


# ═══════════════ 7. ACTA DE LIQUIDACIÓN ═══════════════
def acta_liquidacion(pl, r, datos):
    d = datos or {}
    ejec = d.get("valor_ejecutado", r.valor)
    saldo = (r.valor or 0) - ejec
    cuerpo = f"""
<h1>ACTA DE LIQUIDACIÓN</h1>
<div class="doc-num">Contrato N° {r.contrato_num or ''} · Vigencia {r.vigencia}</div>

<h2>1. Información general</h2>
<table>
 <tr><td class="tk">CONTRATANTE</td><td>{pl.nombre_oficial} — NIT {pl.nit or ''}</td></tr>
 <tr><td class="tk">CONTRATISTA</td><td>{r.contratista_nombre or ''} — {r.contratista_doc or ''}</td></tr>
 <tr><td class="tk">OBJETO</td><td>{(r.descripcion or '').upper()}</td></tr>
 <tr><td class="tk">FECHA DEL CONTRATO</td><td>{fecha_corta(r.contrato_fecha)}</td></tr>
 <tr><td class="tk">ACTA DE INICIO</td><td>{fecha_corta(r.acta_inicio_fecha)}</td></tr>
 <tr><td class="tk">ACTA FINAL</td><td>{fecha_corta(r.acta_final_fecha)}</td></tr>
 <tr><td class="tk">PLAZO</td><td>{dias_letras(r.plazo_dias)}</td></tr>
 <tr><td class="tk">CDP / RP</td><td>{r.cdp_num or ''} · {r.rp_num or ''}</td></tr>
 <tr><td class="tk">RUBRO</td><td>{r.rubro_codigo or ''} — {r.rubro_nombre or ''}</td></tr>
</table>

<h2>2. Ejecución y cumplimiento</h2>
<p>El supervisor del contrato, <b>{d.get('supervisor', pl.rector_nombre or '')}</b>, certifica
que el CONTRATISTA cumplió con el objeto contractual y con las obligaciones pactadas,
dentro del plazo establecido y conforme a las especificaciones técnicas exigidas.</p>

<h2>3. Balance presupuestal y financiero</h2>
<table>
 <thead><tr><th>CONCEPTO</th><th style="width:26%">VALOR</th></tr></thead>
 <tbody>
  <tr><td>Valor inicial del contrato</td><td style="text-align:right">{pesos(r.valor)}</td></tr>
  <tr><td>Adiciones</td><td style="text-align:right">{pesos(d.get('adiciones', 0))}</td></tr>
  <tr><td>Valor total del contrato</td>
   <td style="text-align:right"><b>{pesos((r.valor or 0) + d.get('adiciones', 0))}</b></td></tr>
  <tr><td>Valor ejecutado y pagado</td><td style="text-align:right">{pesos(ejec)}</td></tr>
  <tr><td>Saldo a liberar</td><td style="text-align:right"><b>{pesos(saldo)}</b></td></tr>
 </tbody></table>
<p><b>Observaciones:</b> {d.get('observaciones', 'Ninguna. El contrato se ejecutó en su '
   'totalidad sin novedades.')}</p>

<h2>4. Pago de aportes al Sistema de Seguridad Social</h2>
<p>El CONTRATISTA acreditó el pago de los aportes al Sistema de Seguridad Social Integral
correspondientes al periodo de ejecución del contrato, conforme al artículo 50 de la
Ley 789 de 2002 y el artículo 23 de la Ley 1150 de 2007.</p>

<h2>5. Garantías y publicaciones</h2>
<p>{d.get('garantias', 'Dada la cuantía y naturaleza del contrato, no se exigió la '
   'constitución de garantías. El proceso fue publicado en el SECOP conforme a la ley.')}</p>

<h2>6. Paz y salvo</h2>
<p>Las partes declaran que se encuentran a <b>PAZ Y SALVO</b> por todo concepto derivado
del presente contrato y renuncian expresamente a formular reclamaciones futuras
relacionadas con su celebración, ejecución y liquidación.</p>

<p>Para constancia se firma en {pl.municipio or ''} el {fecha_larga(r.liquidacion_fecha)}.</p>
<div class="firmas">
 <div>{('<img class="firma-img" src="' + pl.rector_firma + '">') if pl.rector_firma else ''}
  <b>{(pl.rector_nombre or '').upper()}</b><br>Rector(a) — Ordenador(a) del Gasto</div>
 <div><b>{(d.get('supervisor', pl.rector_nombre) or '').upper()}</b><br>Supervisor(a)</div>
 <div><b>{(r.contratista_nombre or '').upper()}</b><br>Contratista</div>
</div>
{f'<div class="sello"><b>Contador(a):</b> {pl.contador_nombre} — T.P. {pl.contador_tp or ""}</div>' if pl.contador_nombre else ''}"""
    return envolver("Acta de liquidación", pl, cuerpo)


# ═══════════════ 8. CARTA / OFICIO / DERECHO DE PETICIÓN ═══════════════
def correspondencia(pl, c, datos=None):
    d = datos or {}
    TIT = {"carta": "", "oficio": "OFICIO", "derecho_peticion": "DERECHO DE PETICIÓN",
           "respuesta_dp": "RESPUESTA A DERECHO DE PETICIÓN",
           "circular": "CIRCULAR", "constancia": "CONSTANCIA"}
    fundamento = ""
    if c.tipo == "derecho_peticion":
        fundamento = """<p>El presente derecho de petición se formula con fundamento en el
artículo 23 de la Constitución Política y en la Ley 1755 de 2015, por lo cual solicito
respetuosamente que la respuesta sea remitida dentro de los quince (15) días hábiles
siguientes a su radicación.</p>"""
    elif c.tipo == "respuesta_dp":
        fundamento = f"""<p>La presente respuesta se emite dentro del término legal previsto
en la Ley 1755 de 2015, en atención a la petición radicada
{f'el {fecha_corta(d.get("fecha_peticion"))}' if d.get("fecha_peticion") else ''}.</p>"""
    anexos = ""
    if c.anexos:
        try:
            import json as _j
            lst = _j.loads(c.anexos) if isinstance(c.anexos, str) else c.anexos
            if lst:
                anexos = "<p><b>Anexos:</b></p><ol>" + "".join(
                    f"<li>{a}</li>" for a in lst) + "</ol>"
        except Exception:
            anexos = f"<p><b>Anexos:</b> {c.anexos}</p>"
    cuerpo = f"""
{f'<h1>{TIT.get(c.tipo, "")}</h1>' if TIT.get(c.tipo) else ''}
{f'<div class="doc-num">Radicado N° {c.radicado}</div>' if c.radicado else ''}
<p style="text-align:right">{pl.municipio or ''}, {fecha_larga(c.fecha)}</p>
<p><b>Señor(a):</b><br>
<b>{(c.destinatario or '').upper()}</b><br>
{c.destinatario_cargo or ''}{'<br>' if c.destinatario_cargo else ''}
{c.destinatario_entidad or ''}{'<br>' if c.destinatario_entidad else ''}
{d.get('ciudad_destino', 'La ciudad')}</p>
<p><b>Asunto:</b> {c.asunto}</p>
<p>Cordial saludo,</p>
<div style="white-space:pre-line;margin:14px 0">{c.cuerpo or ''}</div>
{fundamento}
{anexos}
<p>Atentamente,</p>
<div class="firmas">
 <div>{('<img class="firma-img" src="' + pl.rector_firma + '">') if pl.rector_firma else ''}
  <b>{(c.remitente or pl.rector_nombre or '').upper()}</b><br>
  {d.get('cargo_remitente', 'Rector(a)')} — {pl.nombre_oficial}<br>
  {f'C.C. {pl.rector_cc}' if not d.get('cargo_remitente') and pl.rector_cc else ''}</div>
</div>
{f'<div class="sello">📅 Término legal de respuesta: {fecha_larga(c.fecha_limite)} (15 días hábiles)</div>' if c.tipo == 'derecho_peticion' and c.fecha_limite else ''}"""
    return envolver(c.asunto[:50], pl, cuerpo)


PLANTILLAS = {
    "solicitud_cotizacion": ("📨 Solicitud de cotización", solicitud_cotizacion),
    "estudios_previos": ("📋 Estudios previos", estudios_previos),
    "invitacion": ("📢 Invitación pública", invitacion),
    "contrato": ("📜 Contrato", contrato),
    "acta_inicio": ("🚀 Acta de inicio", acta_inicio),
    "acta_final": ("✅ Acta final", acta_final),
    "acta_liquidacion": ("🏁 Acta de liquidación", acta_liquidacion),
}
