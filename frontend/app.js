/* ============================================================
   GyverLabs — Demo funcional con datos simulados
   Concurso Datos al Ecosistema 2026 — MinTIC
   Ningún estudiante, docente o proveedor es real.
   En producción estos datos vienen de la API FastAPI (/backend)
   y del motor SRD real (protegido, ver LICENSE).
   ============================================================ */

/* ---------------- SALONES ---------------- */
const salones = [
  {grado:'601', jornada:'Mañana', director:'Prof. Ana Gómez', estudiantes:38, riesgo:4, asistencia:94},
  {grado:'602', jornada:'Mañana', director:'Prof. Iván Salas', estudiantes:36, riesgo:6, asistencia:92},
  {grado:'701', jornada:'Mañana', director:'Prof. Carla Pinto', estudiantes:35, riesgo:9, asistencia:93},
  {grado:'702', jornada:'Tarde', director:'Prof. Mario Cepeda', estudiantes:33, riesgo:11, asistencia:89},
  {grado:'801', jornada:'Mañana', director:'Prof. Rosa Beltrán', estudiantes:32, riesgo:14, asistencia:90},
  {grado:'802', jornada:'Tarde', director:'Prof. Felipe Ortiz', estudiantes:31, riesgo:16, asistencia:87},
  {grado:'901', jornada:'Mañana', director:'Prof. Diana Ruiz', estudiantes:34, riesgo:27, asistencia:85},
  {grado:'902', jornada:'Tarde', director:'Prof. Hugo Navarro', estudiantes:33, riesgo:24, asistencia:86},
  {grado:'1001', jornada:'Mañana', director:'Prof. Marcela Soto', estudiantes:29, riesgo:31, asistencia:83},
  {grado:'1002', jornada:'Tarde', director:'Prof. Camilo Vega', estudiantes:28, riesgo:22, asistencia:88},
];

/* ---------------- ESTUDIANTES SRD (grado 901) ---------------- */
const estudiantesSRD = [
  {n:'Camila Herrera', g:'901', score:0.82, nivel:'CRÍTICO', faltas:11,
   factores:['Asistencia del 68% en las últimas 4 semanas','Caída de 1.4 puntos en el promedio académico','Sin intervención registrada en 45 días'],
   notifPadre:{enviado:false, fecha:null}, notifRectoria:{enviado:false, fecha:null},
   acudiente:'María Herrera · 300 456 7891',
   historial:['12 jun 2026 — Llamada de seguimiento del coordinador','02 may 2026 — Citación a acudiente (no asistió)']},
  {n:'Julián Rueda', g:'901', score:0.74, nivel:'CRÍTICO', faltas:9,
   factores:['Sin intervención registrada hace 70 días','Distancia geográfica alta al plantel','Reprobó 2 materias el período anterior'],
   notifPadre:{enviado:true, fecha:'10 jul 2026'}, notifRectoria:{enviado:false, fecha:null},
   acudiente:'Pedro Rueda · 301 220 9981',
   historial:['10 jul 2026 — Notificación enviada al acudiente vía WhatsApp']},
  {n:'Valentina Ríos', g:'901', score:0.58, nivel:'MODERADO', faltas:5,
   factores:['Asistencia irregular los días viernes','Tendencia a la baja en matemáticas'],
   notifPadre:{enviado:true, fecha:'05 jul 2026'}, notifRectoria:{enviado:true, fecha:'06 jul 2026'},
   acudiente:'Liliana Ríos · 300 998 1122',
   historial:['06 jul 2026 — Rectoría informada','05 jul 2026 — Notificación al acudiente']},
  {n:'Andrés Pardo', g:'901', score:0.44, nivel:'MODERADO', faltas:4,
   factores:['Bajó una materia este período'],
   notifPadre:{enviado:false, fecha:null}, notifRectoria:{enviado:false, fecha:null},
   acudiente:'Jorge Pardo · 315 667 2200',
   historial:[]},
  {n:'Sofía Martínez', g:'901', score:0.31, nivel:'LEVE', faltas:2,
   factores:['Variación leve en asistencia'],
   notifPadre:{enviado:false, fecha:null}, notifRectoria:{enviado:false, fecha:null},
   acudiente:'Claudia Martínez · 320 445 8871',
   historial:[]},
  {n:'Kevin Duarte', g:'901', score:0.12, nivel:'SIN RIESGO', faltas:0,
   factores:['Sin variables en alerta'],
   notifPadre:{enviado:false, fecha:null}, notifRectoria:{enviado:false, fecha:null},
   acudiente:'Marta Duarte · 300 112 4456',
   historial:[]},
];
const coloresNivel = {'CRÍTICO':'critico', 'MODERADO':'moderado', 'LEVE':'leve', 'SIN RIESGO':'sinriesgo'};
const coloresBarra = {'CRÍTICO':'var(--rojo)', 'MODERADO':'var(--amarillo)', 'LEVE':'var(--azul-claro)', 'SIN RIESGO':'var(--verde)'};

/* ---------------- ASISTENCIA (estado del día en memoria) ---------------- */
const estadosAsistenciaHoy = {};
estudiantesSRD.forEach((e,i)=>{ estadosAsistenciaHoy[i] = 'presente'; });
const historialSemana = [
  {dia:'Lun', pct:93}, {dia:'Mar', pct:91}, {dia:'Mié', pct:88}, {dia:'Jue', pct:85}, {dia:'Vie', pct:79}
];

/* ---------------- AULA VIRTUAL ---------------- */
let materiales = [
  {t:'Guía de fracciones — semana 12', tipo:'📄 PDF', fecha:'2026-07-17', completado:24, total:34, entregado:20, preguntas:[
    {u:'Camila Herrera', q:'¿La guía se entrega en físico o virtual?'},
  ]},
  {t:'Video: la fotosíntesis', tipo:'🎬 Video', fecha:'2026-07-16', completado:19, total:34, entregado:0, preguntas:[]},
  {t:'Taller de comprensión lectora', tipo:'📝 Evaluación', fecha:'2026-07-18', completado:12, total:34, entregado:9, preguntas:[
    {u:'Andrés Pardo', q:'¿Hasta qué hora puedo entregar el viernes?'},
  ]},
];

/* ---------------- NOTAS ---------------- */
const notasPorEstudiante = {
  'Camila Herrera': {materias:{'Matemáticas':[3.2,2.8,3.0,null],'Lengua Castellana':[3.8,3.5,3.6,null],'Ciencias Naturales':[3.0,2.9,3.1,null],'Sociales':[3.6,3.4,3.5,null],'Inglés':[3.3,3.0,3.2,null]}},
  'Julián Rueda': {materias:{'Matemáticas':[2.5,2.2,2.6,null],'Lengua Castellana':[3.1,2.9,3.0,null],'Ciencias Naturales':[2.8,2.6,2.7,null],'Sociales':[3.0,2.8,2.9,null],'Inglés':[2.4,2.3,2.5,null]}},
  'Valentina Ríos': {materias:{'Matemáticas':[3.9,3.7,3.8,null],'Lengua Castellana':[4.2,4.0,4.1,null],'Ciencias Naturales':[3.8,3.9,4.0,null],'Sociales':[4.0,3.8,3.9,null],'Inglés':[3.7,3.6,3.8,null]}},
  'Andrés Pardo': {materias:{'Matemáticas':[3.4,3.3,2.9,null],'Lengua Castellana':[3.6,3.5,3.4,null],'Ciencias Naturales':[3.5,3.4,3.3,null],'Sociales':[3.7,3.6,3.5,null],'Inglés':[3.2,3.1,3.0,null]}},
  'Sofía Martínez': {materias:{'Matemáticas':[4.1,4.0,4.2,null],'Lengua Castellana':[4.3,4.2,4.4,null],'Ciencias Naturales':[4.0,4.1,4.2,null],'Sociales':[4.2,4.1,4.3,null],'Inglés':[3.9,4.0,4.1,null]}},
  'Kevin Duarte': {materias:{'Matemáticas':[4.5,4.6,4.7,null],'Lengua Castellana':[4.4,4.5,4.6,null],'Ciencias Naturales':[4.6,4.7,4.8,null],'Sociales':[4.5,4.6,4.7,null],'Inglés':[4.3,4.4,4.5,null]}},
};

/* ---------------- CONTABILIDAD FSE ---------------- */
let movimientosFSE = [
  {f:'2026-07-10', c:'Transferencia MEN — recursos de gratuidad', proveedor:'Ministerio de Educación Nacional', cuenta:'1105 Caja', tipo:'ingreso', v:6200000},
  {f:'2026-07-08', c:'Pago servicios públicos', proveedor:'Electrificadora del Caribe', cuenta:'2401 Cuentas por pagar', tipo:'egreso', v:1450000},
  {f:'2026-07-05', c:'Compra material didáctico', proveedor:'Distribuidora Escolar SAS', cuenta:'1524 Materiales', tipo:'egreso', v:980000},
  {f:'2026-07-02', c:'Donación empresa local', proveedor:'Cooperativa Agrícola del Sur', cuenta:'1105 Caja', tipo:'ingreso', v:1200000},
];

let registrosRP = [
  {numero:'RP-2026-011', f:'2026-06-20', proveedor:'Distribuidora Escolar SAS', concepto:'Contrato 018-2026 — material didáctico', v:2400000, estado:'Pagado', secopMin:2100000, secopMax:2500000},
  {numero:'RP-2026-013', f:'2026-07-02', proveedor:'Ferretería San Pablo', concepto:'Contrato 021-2026 — mantenimiento locativo', v:3800000, estado:'Comprometido', secopMin:2600000, secopMax:3200000},
  {numero:'RP-2026-014', f:'2026-07-09', proveedor:'Tecnología Educativa Ltda', concepto:'Contrato 023-2026 — equipos de cómputo', v:9500000, estado:'Pagado', secopMin:8800000, secopMax:9700000},
];

let planCompras = [
  {mes:'Julio', item:'Sillas para aula 902', prioridad:'Alta', valor:1800000, comprado:false},
  {mes:'Julio', item:'Mantenimiento de baterías sanitarias', prioridad:'Alta', valor:2200000, comprado:false},
  {mes:'Agosto', item:'Material de laboratorio de química', prioridad:'Media', valor:1500000, comprado:false},
  {mes:'Junio', item:'Pintura fachada bloque B', prioridad:'Media', valor:2600000, comprado:true},
  {mes:'Septiembre', item:'Balones y material deportivo', prioridad:'Baja', valor:650000, comprado:false},
  {mes:'Mayo', item:'Kits de primeros auxilios', prioridad:'Alta', valor:480000, comprado:true},
];

/* ---------------- USUARIOS ---------------- */
let usuarios = [
  {nombre:'Diana Ruiz', rol:'Coordinador', correo:'diana.ruiz@iesanpablo.edu.co', estado:'Activo'},
  {nombre:'Marcela Soto', rol:'Docente', correo:'marcela.soto@iesanpablo.edu.co', estado:'Activo'},
  {nombre:'Hugo Navarro', rol:'Docente', correo:'hugo.navarro@iesanpablo.edu.co', estado:'Activo'},
  {nombre:'Rectoría — Ignacio Correa', rol:'Rector', correo:'rectoria@iesanpablo.edu.co', estado:'Activo'},
];

/* ============================================================
   AUTENTICACIÓN
   ============================================================ */
function iniciarSesion(){
  document.getElementById('vista-login').classList.add('oculto');
  document.getElementById('vista-app').classList.remove('oculto');
  document.getElementById('vista-app-chat').classList.remove('oculto');
  renderTodo();
  conectarBackend();
}
function cerrarSesion(){
  document.getElementById('vista-app').classList.add('oculto');
  document.getElementById('vista-app-chat').classList.add('oculto');
  document.getElementById('vista-login').classList.remove('oculto');
}
function mostrarSeccion(id){
  ['dashboard','desercion','asistencia','aula','notas','fse','usuarios'].forEach(s=>{
    document.getElementById('seccion-'+s).classList.toggle('oculto', s!==id);
    document.getElementById('nav-'+s).classList.toggle('activo', s===id);
  });
}

/* ============================================================
   RENDER GENERAL
   ============================================================ */
function renderTodo(){
  renderMapaCalor();
  renderSalones();
  renderAlertasDashboard();
  renderKpisSRD();
  renderListaSRD();
  renderAsistencia();
  renderResumenSemana();
  renderMateriales();
  renderSelectEstudiantesNotas();
  renderNotas();
  renderFSE();
  renderRP();
  renderPlanCompras();
  renderUsuarios();
}

/* ============================================================
   1. DASHBOARD — mapa de calor + salones
   ============================================================ */
function renderMapaCalor(){
  const mapa = document.getElementById('mapa-calor');
  mapa.innerHTML = salones.map(s=>{
    const pct = Math.round(s.riesgo);
    let color = pct<10 ? ['var(--verde-fondo)','var(--verde)'] : pct<20 ? ['var(--amarillo-fondo)','var(--amarillo)'] : ['var(--rojo-fondo)','var(--rojo)'];
    return `<div class="celda-grado" style="background:${color[0]}; color:${color[1]};" onclick="irADesercion()">${s.grado}<b>${pct}%</b></div>`;
  }).join('');
}
function irADesercion(){ mostrarSeccion('desercion'); }

function toggleSalones(){
  const p = document.getElementById('panel-salones');
  const abierto = p.classList.toggle('oculto');
  document.getElementById('btn-toggle-salones').textContent = abierto ? 'Ver todos los salones ▾' : 'Ocultar salones ▴';
}
function renderSalones(){
  const tbody = document.getElementById('tabla-salones');
  tbody.innerHTML = salones.map(s=>{
    const colorRiesgo = s.riesgo<10 ? 'sinriesgo' : s.riesgo<20 ? 'moderado' : 'critico';
    return `<tr>
      <td><b>${s.grado}</b></td>
      <td>${s.jornada}</td>
      <td>${s.director}</td>
      <td>${s.estudiantes}</td>
      <td><span class="badge ${colorRiesgo}">${s.riesgo}%</span></td>
      <td>${s.asistencia}%</td>
    </tr>`;
  }).join('');
  const total = salones.reduce((a,s)=>a+s.estudiantes,0);
  document.getElementById('total-estudiantes-salones').textContent = total;
  document.getElementById('total-salones').textContent = salones.length;
}

function renderAlertasDashboard(){
  const criticos = estudiantesSRD.filter(e=>e.nivel==='CRÍTICO');
  document.getElementById('dashboard-alertas-recientes').innerHTML = criticos.map(e=>`
    <div class="fila-estudiante" onclick="irADesercion()">
      <div><span class="nombre">${e.n}</span><span class="grado">grado ${e.g}</span></div>
      <span class="badge ${coloresNivel[e.nivel]}">${e.nivel} · ${Math.round(e.score*100)}%</span>
    </div>`).join('');
}

/* ============================================================
   2. DESERCIÓN SRD — detalle enriquecido
   ============================================================ */
function renderKpisSRD(){
  document.getElementById('kpi-criticos').textContent = estudiantesSRD.filter(e=>e.nivel==='CRÍTICO').length;
  document.getElementById('kpi-moderados').textContent = estudiantesSRD.filter(e=>e.nivel==='MODERADO').length;
  document.getElementById('kpi-sin-notif-padre').textContent = estudiantesSRD.filter(e=>!e.notifPadre.enviado && (e.nivel==='CRÍTICO'||e.nivel==='MODERADO')).length;
  document.getElementById('kpi-sin-notif-rect').textContent = estudiantesSRD.filter(e=>!e.notifRectoria.enviado && e.nivel==='CRÍTICO').length;
}

function renderListaSRD(){
  const lista = document.getElementById('lista-srd');
  lista.innerHTML = '';
  estudiantesSRD.forEach((e,i)=>{
    const fila = document.createElement('div');
    fila.className = 'fila-estudiante';
    fila.innerHTML = `<div><span class="nombre">${e.n}</span><span class="grado">grado ${e.g} · ${e.faltas} faltas acum.</span></div>
      <span class="badge ${coloresNivel[e.nivel]}">${e.nivel} · ${Math.round(e.score*100)}%</span>`;
    fila.onclick = () => mostrarDetalleSRD(i);
    lista.appendChild(fila);
  });
}

function mostrarDetalleSRD(i){
  const e = estudiantesSRD[i];
  const d = document.getElementById('detalle-srd');
  d.classList.remove('oculto');
  d.innerHTML = `
    <div class="detalle-srd">
      <b>${e.n}</b> — grado ${e.g} · Score: ${Math.round(e.score*100)}% (${e.nivel})
      <div class="barra-score"><div class="barra-score-fill" style="width:${e.score*100}%; background:${coloresBarra[e.nivel]};"></div></div>

      <div class="grid-detalle">
        <div class="mini-dato"><div class="lbl">Faltas acumuladas</div><div class="val">${e.faltas}</div></div>
        <div class="mini-dato"><div class="lbl">Acudiente</div><div class="val" style="font-size:12.5px;">${e.acudiente}</div></div>
        <div class="mini-dato"><div class="lbl">Notif. al padre</div><div class="val" style="font-size:13px; color:${e.notifPadre.enviado?'var(--verde)':'var(--rojo)'};">${e.notifPadre.enviado ? '✔ '+e.notifPadre.fecha : 'Pendiente'}</div></div>
        <div class="mini-dato"><div class="lbl">Notif. a rectoría</div><div class="val" style="font-size:13px; color:${e.notifRectoria.enviado?'var(--verde)':'var(--rojo)'};">${e.notifRectoria.enviado ? '✔ '+e.notifRectoria.fecha : 'Pendiente'}</div></div>
      </div>

      <p style="margin:10px 0 4px; font-weight:500;">Factores detectados por el modelo:</p>
      <ul>${e.factores.map(f=>`<li>${f}</li>`).join('')}</ul>

      <p style="margin:10px 0 4px; font-weight:500;">Historial de seguimiento:</p>
      ${e.historial.length ? e.historial.map(h=>`<div class="linea-notif" style="font-size:12.5px; color:#334155;">${h}</div>`).join('') : '<p style="font-size:12.5px; color:var(--gris);">Sin registros aún.</p>'}

      <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:12px;">
        <button class="btn-secundario ${e.notifPadre.enviado?'gris':''}" onclick="notificarPadre(${i})" ${e.notifPadre.enviado?'disabled':''}>📩 ${e.notifPadre.enviado?'Padre ya notificado':'Notificar al padre de familia'}</button>
        <button class="btn-secundario ${e.notifRectoria.enviado?'gris':''}" onclick="notificarRectoria(${i})" ${e.notifRectoria.enviado?'disabled':''}>🏫 ${e.notifRectoria.enviado?'Rectoría ya informada':'Notificar a rectoría'}</button>
        <button class="btn-secundario rojo" onclick="activarIntervencion(${i})">🚨 Activar protocolo de intervención</button>
      </div>
    </div>`;
}

function notificarPadre(i){
  const e = estudiantesSRD[i];
  const hoy = new Date().toLocaleDateString('es-CO', {day:'2-digit', month:'short', year:'numeric'});
  e.notifPadre = {enviado:true, fecha:hoy};
  e.historial.unshift(hoy + ' — Notificación enviada al acudiente vía WhatsApp/SMS');
  mostrarDetalleSRD(i);
  renderListaSRD();
  renderKpisSRD();
}
function notificarRectoria(i){
  const e = estudiantesSRD[i];
  const hoy = new Date().toLocaleDateString('es-CO', {day:'2-digit', month:'short', year:'numeric'});
  e.notifRectoria = {enviado:true, fecha:hoy};
  e.historial.unshift(hoy + ' — Caso escalado a rectoría');
  mostrarDetalleSRD(i);
  renderListaSRD();
  renderKpisSRD();
}
function activarIntervencion(i){
  const e = estudiantesSRD[i];
  alert('Protocolo de intervención activado para ' + e.n + '.\nSe notificó al coordinador y quedó registrado en el historial del caso.');
  const hoy = new Date().toLocaleDateString('es-CO', {day:'2-digit', month:'short', year:'numeric'});
  e.historial.unshift(hoy + ' — Protocolo de intervención institucional activado');
  mostrarDetalleSRD(i);
}

/* ============================================================
   3. ASISTENCIA — 4 estados + integración con faltas SRD
   ============================================================ */
function renderAsistencia(){
  const tbody = document.getElementById('tabla-asistencia');
  tbody.innerHTML = estudiantesSRD.map((e,i)=>{
    const estado = estadosAsistenciaHoy[i];
    const opciones = [['presente','Presente'],['tarde','Tarde'],['excusa','Excusa'],['ausente','Ausente']];
    const botones = opciones.map(([val,lbl])=>
      `<button class="btn-toggle sel-${val} ${estado===val?'on':''}" onclick="marcarEstado(${i},'${val}')">${lbl}</button>`
    ).join('');
    return `<tr>
      <td>${e.n}</td>
      <td id="faltas-${i}">${e.faltas}</td>
      <td><div class="toggle-btns" id="botones-asis-${i}">${botones}</div></td>
    </tr>`;
  }).join('');
}
function marcarEstado(i, estado){
  estadosAsistenciaHoy[i] = estado;
  renderAsistencia();
}
function guardarAsistencia(){
  let presentes=0, tarde=0, excusa=0, ausentes=0;
  Object.values(estadosAsistenciaHoy).forEach(v=>{
    if(v==='presente') presentes++;
    else if(v==='tarde') tarde++;
    else if(v==='excusa') excusa++;
    else if(v==='ausente') ausentes++;
  });
  // Integración: sumar falta acumulada a quienes quedaron en "ausente" (sin excusa)
  estudiantesSRD.forEach((e,i)=>{
    if(estadosAsistenciaHoy[i]==='ausente') e.faltas += 1;
  });
  const msg = document.getElementById('msg-asistencia-guardada');
  msg.textContent = `✔ Guardado — Presentes: ${presentes} · Tarde: ${tarde} · Excusas: ${excusa} · Ausentes: ${ausentes}. El motor SRD recalculará los scores afectados.`;
  setTimeout(()=>{ msg.textContent=''; }, 6000);
  renderAsistencia();
  renderListaSRD();
  renderKpisSRD();
}
function renderResumenSemana(){
  const cont = document.getElementById('resumen-semana');
  cont.innerHTML = historialSemana.map(d=>`
    <div class="col-dia">
      <div class="barra-dia" style="height:${d.pct}%;"></div>
      <span>${d.dia}<br><b>${d.pct}%</b></span>
    </div>`).join('');
}

/* ============================================================
   4. AULA VIRTUAL — materiales, tareas y preguntas
   ============================================================ */
function toggleFormMaterial(){ document.getElementById('form-material').classList.toggle('oculto'); }
function agregarMaterial(){
  const titulo = document.getElementById('mat-titulo').value.trim();
  if(!titulo){ alert('Escribe un título para el material.'); return; }
  const tipo = document.getElementById('mat-tipo').value;
  const fecha = document.getElementById('mat-fecha').value || '2026-07-20';
  materiales.unshift({t:titulo, tipo, fecha, completado:0, total:34, entregado:0, preguntas:[]});
  document.getElementById('mat-titulo').value = '';
  document.getElementById('form-material').classList.add('oculto');
  renderMateriales();
}
function renderMateriales(){
  document.getElementById('kpi-materiales').textContent = materiales.length;
  document.getElementById('kpi-entregadas').textContent = materiales.reduce((a,m)=>a+m.entregado,0);
  document.getElementById('kpi-pendientes').textContent = materiales.reduce((a,m)=>a + (m.total-m.entregado),0);

  document.getElementById('lista-materiales').innerHTML = materiales.map((m,i)=>`
    <div class="fila-estudiante" style="cursor:default; flex-direction:column; align-items:stretch;">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <div><span class="nombre">${m.t}</span><span class="grado">${m.tipo} · entrega ${m.fecha}</span>
          <div class="barra-progreso" style="width:220px;"><div class="barra-progreso-fill" style="width:${Math.round(m.completado/m.total*100)}%;"></div></div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:12.5px; color:var(--gris);">${m.completado}/${m.total} vieron</div>
          <div style="font-size:12.5px; color:var(--verde); font-weight:600;">${m.entregado}/${m.total} entregaron</div>
        </div>
      </div>
      <div class="hilo-pregunta">
        <b>Preguntas de estudiantes (${m.preguntas.length})</b>
        ${m.preguntas.map(p=>`<div style="margin-top:6px;">💬 <b>${p.u}:</b> ${p.q}</div>`).join('')}
        <div style="display:flex; gap:6px; margin-top:8px;">
          <input id="preg-${i}" placeholder="Responder o simular nueva pregunta..." style="flex:1; padding:6px 8px; border:1px solid var(--borde); border-radius:6px; font-size:12.5px;">
          <button class="btn-mini" onclick="responderPregunta(${i})">Enviar</button>
        </div>
      </div>
    </div>`).join('');
}
function responderPregunta(i){
  const input = document.getElementById('preg-'+i);
  const txt = input.value.trim();
  if(!txt) return;
  materiales[i].preguntas.push({u:'Coordinador', q:txt});
  input.value = '';
  renderMateriales();
}

/* ============================================================
   5. NOTAS
   ============================================================ */
function renderSelectEstudiantesNotas(){
  const sel = document.getElementById('select-estudiante-notas');
  sel.innerHTML = Object.keys(notasPorEstudiante).map(n=>`<option value="${n}">${n}</option>`).join('');
}
function renderNotas(){
  const nombre = document.getElementById('select-estudiante-notas').value || Object.keys(notasPorEstudiante)[0];
  const datos = notasPorEstudiante[nombre];
  if(!datos) return;
  const tbody = document.getElementById('tabla-notas');
  let sumaDefinitivas = 0, n = 0;
  tbody.innerHTML = Object.entries(datos.materias).map(([materia, notas])=>{
    const validas = notas.filter(x=>x!==null);
    const definitiva = (validas.reduce((a,b)=>a+b,0)/validas.length).toFixed(1);
    sumaDefinitivas += parseFloat(definitiva); n++;
    return `<tr>
      <td>${materia}</td>
      ${notas.map(x=>`<td>${x===null ? '<span style="color:var(--gris);">—</span>' : x.toFixed(1)}</td>`).join('')}
      <td><b style="color:${definitiva>=3?'var(--verde)':'var(--rojo)'};">${definitiva}</b></td>
    </tr>`;
  }).join('');
  document.getElementById('promedio-general').textContent = (sumaDefinitivas/n).toFixed(2);
}

/* ============================================================
   6. CONTABILIDAD FSE
   ============================================================ */
function mostrarSubtabFSE(tab){
  ['movimientos','rp','plan','informe'].forEach(t=>{
    document.getElementById('fse-'+t).classList.toggle('oculto', t!==tab);
  });
  document.querySelectorAll('.subtab').forEach(b=>b.classList.toggle('activo', b.dataset.fsetab===tab));
}

function toggleFormMovimiento(){ document.getElementById('form-movimiento').classList.toggle('oculto'); }
function agregarMovimiento(){
  const fecha = document.getElementById('mov-fecha').value || '2026-07-15';
  const tipo = document.getElementById('mov-tipo').value;
  const concepto = document.getElementById('mov-concepto').value.trim();
  const proveedor = document.getElementById('mov-proveedor').value.trim() || 'N/A';
  const cuenta = document.getElementById('mov-cuenta').value.trim() || 'Sin clasificar';
  const valor = parseFloat(document.getElementById('mov-valor').value);
  if(!concepto || !valor){ alert('Completa al menos el concepto y el valor.'); return; }
  movimientosFSE.unshift({f:fecha, c:concepto, proveedor, cuenta, tipo, v:valor});
  ['mov-concepto','mov-proveedor','mov-cuenta','mov-valor'].forEach(id=>document.getElementById(id).value='');
  document.getElementById('form-movimiento').classList.add('oculto');
  renderFSE();
}
function editarMovimiento(i){
  const m = movimientosFSE[i];
  const nuevoValor = prompt('Nuevo valor para "'+m.c+'":', m.v);
  if(nuevoValor===null) return;
  const nuevaFecha = prompt('Nueva fecha (AAAA-MM-DD):', m.f);
  if(nuevaFecha===null) return;
  m.v = parseFloat(nuevoValor) || m.v;
  m.f = nuevaFecha || m.f;
  renderFSE();
}
function eliminarMovimiento(i){
  if(confirm('¿Eliminar este movimiento?')){ movimientosFSE.splice(i,1); renderFSE(); }
}
function renderFSE(){
  const ingresos = movimientosFSE.filter(m=>m.tipo==='ingreso').reduce((a,m)=>a+m.v,0);
  const egresos = movimientosFSE.filter(m=>m.tipo==='egreso').reduce((a,m)=>a+m.v,0);
  document.getElementById('kpi-ingresos').textContent = '$'+ingresos.toLocaleString('es-CO');
  document.getElementById('kpi-egresos').textContent = '$'+egresos.toLocaleString('es-CO');
  document.getElementById('kpi-saldo').textContent = '$'+(ingresos-egresos).toLocaleString('es-CO');
  document.getElementById('kpi-ejecucion').textContent = ingresos>0 ? Math.round(egresos/ingresos*100)+'%' : '0%';

  document.getElementById('tabla-fse').innerHTML = movimientosFSE.map((m,i)=>`
    <tr>
      <td>${m.f}</td><td>${m.c}</td><td>${m.proveedor}</td><td>${m.cuenta}</td>
      <td style="text-align:right; color:${m.tipo==='ingreso'?'var(--verde)':'var(--rojo)'}; font-weight:600;">
        ${m.tipo==='ingreso'?'+':'-'}$${m.v.toLocaleString('es-CO')}
      </td>
      <td class="no-imprimir" style="white-space:nowrap;">
        <button class="btn-mini" onclick="editarMovimiento(${i})">✏️</button>
        <button class="btn-mini" onclick="eliminarMovimiento(${i})">🗑️</button>
      </td>
    </tr>`).join('');
}

function toggleFormRP(){ document.getElementById('form-rp').classList.toggle('oculto'); }
function agregarRP(){
  const numero = document.getElementById('rp-numero').value.trim();
  const fecha = document.getElementById('rp-fecha').value || '2026-07-15';
  const proveedor = document.getElementById('rp-proveedor').value.trim();
  const concepto = document.getElementById('rp-concepto').value.trim();
  const valor = parseFloat(document.getElementById('rp-valor').value);
  const estado = document.getElementById('rp-estado').value;
  if(!numero || !proveedor || !valor){ alert('Completa al menos el número de RP, el proveedor y el valor.'); return; }
  registrosRP.unshift({numero, f:fecha, proveedor, concepto, v:valor, estado, secopMin:valor*0.85, secopMax:valor*1.05});
  ['rp-numero','rp-proveedor','rp-concepto','rp-valor'].forEach(id=>document.getElementById(id).value='');
  document.getElementById('form-rp').classList.add('oculto');
  renderRP();
}
function editarRP(i){
  const r = registrosRP[i];
  const nuevoValor = prompt('Nuevo valor para "'+r.numero+'":', r.v);
  if(nuevoValor===null) return;
  const nuevaFecha = prompt('Nueva fecha (AAAA-MM-DD):', r.f);
  if(nuevaFecha===null) return;
  r.v = parseFloat(nuevoValor) || r.v;
  r.f = nuevaFecha || r.f;
  renderRP();
}
function cambiarEstadoRP(i){
  registrosRP[i].estado = registrosRP[i].estado==='Pagado' ? 'Comprometido' : 'Pagado';
  renderRP();
}
function renderRP(){
  document.getElementById('tabla-rp').innerHTML = registrosRP.map((r,i)=>`
    <tr>
      <td>${r.numero}</td><td>${r.f}</td><td>${r.proveedor}</td><td>${r.concepto}</td>
      <td style="text-align:right;">$${r.v.toLocaleString('es-CO')}</td>
      <td><span class="badge ${r.estado==='Pagado'?'sinriesgo':'moderado'}" style="cursor:pointer;" onclick="cambiarEstadoRP(${i})">${r.estado}</span></td>
      <td class="no-imprimir"><button class="btn-mini" onclick="editarRP(${i})">✏️</button></td>
    </tr>`).join('');
}

function toggleFormPlan(){ document.getElementById('form-plan').classList.toggle('oculto'); }
function agregarPlan(){
  const mes = document.getElementById('plan-mes').value;
  const item = document.getElementById('plan-item').value.trim();
  const prioridad = document.getElementById('plan-prioridad').value;
  const valor = parseFloat(document.getElementById('plan-valor').value) || 0;
  if(!item){ alert('Describe la necesidad a planear.'); return; }
  planCompras.push({mes, item, prioridad, valor, comprado:false});
  document.getElementById('plan-item').value = '';
  document.getElementById('form-plan').classList.add('oculto');
  renderPlanCompras();
}
function marcarComprado(i){
  planCompras[i].comprado = !planCompras[i].comprado;
  renderPlanCompras();
}
function renderPlanCompras(){
  const orden = {'Alta':0, 'Media':1, 'Baja':2};
  const ordenado = [...planCompras].sort((a,b)=>orden[a.prioridad]-orden[b.prioridad]);
  document.getElementById('tabla-plan').innerHTML = ordenado.map(p=>{
    const iOriginal = planCompras.indexOf(p);
    const colorP = p.prioridad==='Alta' ? 'critico' : p.prioridad==='Media' ? 'moderado' : 'gris';
    return `<tr>
      <td><span class="badge ${colorP}">${p.prioridad}</span></td>
      <td>${p.mes}</td>
      <td>${p.item}</td>
      <td style="text-align:right;">$${p.valor.toLocaleString('es-CO')}</td>
      <td><span class="badge ${p.comprado?'sinriesgo':'gris'}" style="cursor:pointer;" onclick="marcarComprado(${iOriginal})">${p.comprado?'Comprado ✔':'Pendiente'}</span></td>
      <td class="no-imprimir"></td>
    </tr>`;
  }).join('');
}

function generarInforme(){
  const filasRP = registrosRP.map(r=>{
    const dentroDeRango = r.v >= r.secopMin && r.v <= r.secopMax;
    const diferenciaPct = Math.round(((r.v - r.secopMax) / r.secopMax) * 100);
    const estadoTxt = dentroDeRango ? 'Dentro de rango SECOP' : (r.v > r.secopMax ? `${diferenciaPct}% sobre el máximo SECOP` : 'Por debajo del rango SECOP');
    const colorEstado = dentroDeRango ? 'var(--verde)' : 'var(--rojo)';
    return `<tr>
      <td>${r.f}</td><td>${r.proveedor}</td><td>${r.numero}</td><td>${r.concepto}</td>
      <td style="text-align:right;">$${r.v.toLocaleString('es-CO')}</td>
      <td style="text-align:right; color:var(--gris);">$${r.secopMin.toLocaleString('es-CO')} – $${r.secopMax.toLocaleString('es-CO')}</td>
      <td style="color:${colorEstado}; font-weight:600;">${estadoTxt}</td>
    </tr>`;
  }).join('');

  const ingresos = movimientosFSE.filter(m=>m.tipo==='ingreso').reduce((a,m)=>a+m.v,0);
  const egresos = movimientosFSE.filter(m=>m.tipo==='egreso').reduce((a,m)=>a+m.v,0);
  const totalRP = registrosRP.reduce((a,r)=>a+r.v,0);
  const fechaHoy = new Date().toLocaleDateString('es-CO', {day:'2-digit', month:'long', year:'numeric'});

  document.getElementById('informe-contenido').innerHTML = `
    <p style="font-size:12.5px; color:var(--gris);">Informe generado el ${fechaHoy} — I.E. San Pablo, Sur de Bolívar. Fuente: movimientos de caja y Registros Presupuestales (RP) frente a precios de referencia de SECOP II.</p>
    <div class="grid-detalle" style="grid-template-columns:repeat(3,1fr);">
      <div class="mini-dato"><div class="lbl">Total ingresos (año)</div><div class="val">$${ingresos.toLocaleString('es-CO')}</div></div>
      <div class="mini-dato"><div class="lbl">Total egresos (año)</div><div class="val">$${egresos.toLocaleString('es-CO')}</div></div>
      <div class="mini-dato"><div class="lbl">Total comprometido en RP</div><div class="val">$${totalRP.toLocaleString('es-CO')}</div></div>
    </div>
    <p style="margin:14px 0 6px; font-weight:600; font-size:14px;">Detalle de contratos frente a SECOP II</p>
    <table class="tabla-simple">
      <thead><tr><th>Fecha</th><th>Proveedor</th><th>N° RP</th><th>Concepto / Contrato</th><th style="text-align:right;">Valor pagado</th><th style="text-align:right;">Rango SECOP</th><th>Estado</th></tr></thead>
      <tbody>${filasRP}</tbody>
    </table>
    <p style="margin-top:14px; font-size:12px; color:var(--gris);">Este informe compila datos simulados con fines de demostración ante el jurado del concurso. En producción, el rango SECOP se obtiene por cruce automático con la API de datos abiertos de Colombia Compra Eficiente.</p>
  `;
}

/* ============================================================
   7. USUARIOS
   ============================================================ */
function toggleFormUsuario(){ document.getElementById('form-usuario').classList.toggle('oculto'); }
function agregarUsuario(){
  const nombre = document.getElementById('usr-nombre').value.trim();
  const rol = document.getElementById('usr-rol').value;
  const correo = document.getElementById('usr-correo').value.trim();
  if(!nombre || !correo){ alert('Completa el nombre y el correo.'); return; }
  usuarios.push({nombre, rol, correo, estado:'Activo'});
  document.getElementById('usr-nombre').value = '';
  document.getElementById('usr-correo').value = '';
  document.getElementById('form-usuario').classList.add('oculto');
  renderUsuarios();
}
function cambiarEstadoUsuario(i){
  usuarios[i].estado = usuarios[i].estado==='Activo' ? 'Inactivo' : 'Activo';
  renderUsuarios();
}
function renderUsuarios(){
  document.getElementById('tabla-usuarios').innerHTML = usuarios.map((u,i)=>`
    <tr>
      <td>${u.nombre}</td>
      <td><span class="badge morado">${u.rol}</span></td>
      <td>${u.correo}</td>
      <td><span class="badge ${u.estado==='Activo'?'sinriesgo':'gris'}" style="cursor:pointer;" onclick="cambiarEstadoUsuario(${i})">${u.estado}</span></td>
      <td class="no-imprimir"></td>
    </tr>`).join('');
}

/* ============================================================
   AGENTE IA — chat flotante
   ============================================================ */
const respuestasBot = [
  {q:['nota','notas','calificacion'], r:'Tus notas del período están al 3.9/5.0 en promedio. La última entrega registrada fue el taller de comprensión lectora.'},
  {q:['asistencia','falte','falta'], r:'Tu asistencia de esta semana es del 91%. Tuviste una inasistencia el jueves, ya justificada por el docente.'},
  {q:['entrega','tarea','taller'], r:'Tienes pendiente la entrega de "Guía de fracciones — semana 12" hasta el viernes 17 de julio.'},
  {q:['fse','pago','contabilidad'], r:'La información financiera del FSE la puede consultar directamente el rector o el contador desde el módulo de Contabilidad FSE.'},
];
function toggleChat(){ document.getElementById('chat-caja').classList.toggle('oculto'); }
function enviarChat(){
  const input = document.getElementById('chat-input-txt');
  const txt = input.value.trim();
  if(!txt) return;
  const cuerpo = document.getElementById('chat-cuerpo');
  cuerpo.innerHTML += `<div class="msg-user">${txt}</div>`;
  let respuesta = 'Gracias por tu mensaje. Un coordinador revisará tu caso si se trata de algo académico específico.';
  const bajo = txt.toLowerCase();
  for(const r of respuestasBot){ if(r.q.some(k=>bajo.includes(k))){ respuesta = r.r; break; } }
  setTimeout(()=>{ cuerpo.innerHTML += `<div class="msg-bot">${respuesta}</div>`; cuerpo.scrollTop = cuerpo.scrollHeight; }, 400);
  input.value = '';
  cuerpo.scrollTop = cuerpo.scrollHeight;
}

/* ============================================================
   CONEXIÓN OPCIONAL AL BACKEND REAL (FastAPI + LightGBM entrenado)
   Si el backend está corriendo (./ejecutar_backend.sh), la demo
   reemplaza los datos de respaldo por los scores calculados en
   vivo por el modelo real. Si no está disponible, no pasa nada:
   la demo sigue funcionando 100% con los datos simulados de arriba.
   ============================================================ */
const BACKEND_URL = 'http://localhost:8000';

function fetchConTimeout(url, ms=1200){
  const controller = new AbortController();
  const id = setTimeout(()=>controller.abort(), ms);
  return fetch(url, {signal: controller.signal}).finally(()=>clearTimeout(id));
}

async function conectarBackend(){
  try{
    const salud = await fetchConTimeout(BACKEND_URL + '/health');
    if(!salud.ok) throw new Error('backend no saludable');

    const [tablero, ranking, resumenFSE, movsFSE] = await Promise.all([
      fetchConTimeout(BACKEND_URL + '/srd/tablero').then(r=>r.json()),
      fetchConTimeout(BACKEND_URL + '/srd/ranking?limite=80').then(r=>r.json()),
      fetchConTimeout(BACKEND_URL + '/fse/resumen').then(r=>r.json()).catch(()=>null),
      fetchConTimeout(BACKEND_URL + '/fse/movimientos?limite=20').then(r=>r.json()).catch(()=>null),
    ]);

    // 1. Mapa de calor y salones reales (por grado)
    if(tablero && tablero.mapa_calor){
      tablero.mapa_calor.forEach(g=>{
        const s = salones.find(x=>x.grado===g.grado);
        if(s){ s.riesgo = g.pct_riesgo; s.estudiantes = g.total_estudiantes; }
      });
    }

    // 2. Estudiantes del grado 901 con el score REAL del modelo entrenado
    if(ranking && ranking.length){
      const del901 = ranking.filter(r=>r.grado==='901').slice(0,6);
      if(del901.length){
        estudiantesSRD.length = 0;
        del901.forEach((r,i)=>{
          estudiantesSRD.push({
            n: r.nombre, g: r.grado, score: r.score, nivel: r.nivel,
            faltas: Math.round(r.score*15),
            factores: r.factores,
            notifPadre: {enviado: i%2===0, fecha: i%2===0 ? '10 jul 2026' : null},
            notifRectoria: {enviado: false, fecha: null},
            acudiente: 'Acudiente registrado · consultar ficha institucional',
            historial: i%2===0 ? ['10 jul 2026 — Notificación enviada al acudiente'] : [],
          });
          estadosAsistenciaHoy[i] = 'presente';
        });
      }
    }

    // 3. Contabilidad FSE real (si el módulo respondió)
    if(resumenFSE) {
      // los KPI se recalculan solos desde movimientosFSE en renderFSE(),
      // así que si hay movimientos reales los usamos; si no, se deja el resumen simulado.
    }
    if(movsFSE && movsFSE.length){
      movimientosFSE = movsFSE.map(m=>({
        f:m.fecha, c:m.concepto, proveedor:'Registrado en el FSE institucional',
        cuenta:m.cuenta_cgn, tipo: m.valor>=0 ? 'ingreso':'egreso', v: Math.abs(m.valor),
      }));
    }

    document.getElementById('badge-conexion').innerHTML = '🟢 Conectado al backend en vivo (modelo real)';
    document.getElementById('badge-conexion').style.color = '#4ade80';
    renderTodo();
  }catch(err){
    // Backend no disponible: la demo sigue con los datos simulados embebidos, sin interrupciones.
    document.getElementById('badge-conexion').innerHTML = '⚪ Backend no conectado (datos de respaldo)';
  }
}
