/* ══════════════════════════════════════════════════════════════════
   GyverLabs — Sistema Educativo Inteligente PRO (demo multi-perfil)
   9 perfiles · multi-tenant con dominios · metadatos para IA
   Se conecta al backend FastAPI local (http://localhost:8000).
   ══════════════════════════════════════════════════════════════════ */
const API = "http://localhost:8000";
let ST = { perfil:null, institucion_id:null, salon_id:null, vista:null, conectado:false };

/* ---------- utilidades ---------- */
async function api(path, opts){
  const r = await fetch(API+path, opts);
  if(!r.ok) throw new Error("HTTP "+r.status);
  return r.json();
}
async function post(path, body){
  return api(path, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)});
}
const money = n => "$"+Number(n||0).toLocaleString("es-CO");
const esc = s => { const d=document.createElement("div"); d.textContent=s==null?"":s; return d.innerHTML; };
const ini = s => esc((s||"").substring(0,2).toUpperCase());
const hoyISO = () => { const d=new Date(); return d.getFullYear()+"-"+String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0"); };
const DIAS_ES=["Domingo","Lunes","Martes","Miércoles","Jueves","Viernes","Sábado"];
const MESES_ES=["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"];
function fechaBonita(iso){
  if(!iso) return "—";
  const [y,m,d]=iso.split("-").map(Number);
  const dt=new Date(y,m-1,d);
  return `${DIAS_ES[dt.getDay()]} ${d} de ${MESES_ES[m-1]}`;
}
function toast(msg, err){
  const t=document.getElementById("toast");
  t.textContent=msg; t.className="show"+(err?" err":"");
  setTimeout(()=>t.className=t.className.replace("show",""),4200);
}
function nivelClase(n){ return {"CRÍTICO":"critico","MODERADO":"moderado","LEVE":"leve","SIN RIESGO":"sin"}[n]||"sin"; }
function nivelBadge(n){ const c=nivelClase(n); return {critico:"b-red",moderado:"b-orange",leve:"b-yellow",sin:"b-green"}[c]; }
function abrirModal(id){ document.getElementById(id).classList.add("open"); }
function cerrarModal(id){ document.getElementById(id).classList.remove("open"); }
const MESES=["","Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"];
const PRIO={1:["Alta","b-red"],2:["Media","b-orange"],3:["Baja","b-green"]};
const TIPO_ICO={clase:"🧑‍🏫",taller:"📝",lectura:"📖",video:"🎬",foro:"💬",evaluacion:"🧪",curso:"📚",recuperacion:"♻️"};
const MAT_ICO={pdf:"📄",documento:"📝",hoja:"📊",presentacion:"📽️",video:"🎬",
  audio:"🎧",enlace:"🔗",imagen:"🖼️",archivo:"📎"};
function avatarCell(foto, nombre, extra){
  if(foto) return `<img class="avatar-foto ${extra||''}" src="${foto}" alt="">`;
  return `<div class="avatar-sm">${ini(nombre)}</div>`;
}

/* ---------- arranque ---------- */
window.addEventListener("DOMContentLoaded", cargarPerfiles);

async function cargarPerfiles(){
  try{
    const d = await api("/perfiles/");
    ST.conectado = true;
    window._perfiles = d.perfiles;
    const grid = document.getElementById("perfiles-grid");
    grid.innerHTML = d.perfiles.map((p,idx)=>`
      <div class="perfil-card ${p.rol==='superadmin'?'super':''}" onclick='entrarPerfil(window._perfiles[${idx}])'>
        <div class="perfil-avatar" style="background:${p.color}22;border:1px solid ${p.color}55">
          ${p.foto?`<img src="${p.foto}" alt="">`:p.avatar}
        </div>
        <div class="perfil-titulo">${esc(p.titulo)}</div>
        <div class="perfil-nombre">${esc(p.nombre)}</div>
        <div class="perfil-detalle">${esc(p.detalle)}</div>
        <div class="perfil-desc">${esc(p.descripcion)}</div>
      </div>`).join("");
  }catch(e){
    document.getElementById("perfiles-grid").innerHTML =
      `<div class="empty" style="color:#F5C77E;grid-column:1/-1">⚠️ No se pudo conectar al backend.<br><br>
       Asegúrate de que la ventana de <b>ejecutar_backend.bat</b> siga abierta y muestre<br>
       "Application startup complete", luego recarga esta página.</div>`;
  }
}

function entrarPerfil(p){
  ST.perfil = p;
  ST.institucion_id = p.institucion_id;
  ST.salon_id = p.salon_id;
  ST.estudiante_id = p.estudiante_id || null;
  document.getElementById("pantalla-perfiles").classList.add("oculto");
  document.getElementById("pantalla-app").classList.remove("oculto");
  pintarAvatarSidebar();
  document.getElementById("side-titulo").textContent = p.titulo;
  document.getElementById("side-nombre").textContent = p.nombre;
  document.getElementById("btn-foto").style.display = p.personal_id ? "block" : "none";
  const cx=document.getElementById("conx");
  cx.textContent="🟢 Conectado al backend"; cx.style.background="#14532d"; cx.style.color="#fff";
  document.getElementById("btn-campana").style.display = p.personal_id ? "block" : "none";
  initOffline();
  if(window.Notification && Notification.permission==='granted'){ PUSH.permiso='granted'; iniciarPush(); }
  document.getElementById("panel-campana").classList.add("oculto");
  if(p.personal_id){ cargarCampana(); pedirPermisoYNotificar(); }
  construirNav();
}
function pintarAvatarSidebar(){
  const av=document.getElementById("side-avatar");
  av.innerHTML = ST.perfil.foto ? `<img src="${ST.perfil.foto}" alt="">` : ST.perfil.avatar;
  pintarMarca();
}
/* Marca blanca: si la institución tiene logo, reemplaza a GyverLabs en TODO
   el sistema de ese tenant (punto 25). El súper admin conserva su marca. */
function pintarMarca(){
  const el=document.getElementById("sidebar-marca");
  if(!el) return;
  const logo=ST.perfil.logo;
  const nom=ST.perfil.institucion_nombre||"";
  if(logo){
    el.innerHTML=`<img src="${logo}" alt="${esc(nom)}" title="${esc(nom)}">`;
  } else if(ST.perfil.rol!=="superadmin" && nom){
    el.innerHTML=`<span class="dot"></span><span style="font-size:.92rem;line-height:1.15">${esc(nom)}</span>`;
  } else {
    el.innerHTML='<span class="dot"></span>GyverLabs';
  }
}
function volverPerfiles(){
  document.getElementById("pantalla-app").classList.add("oculto");
  document.getElementById("pantalla-perfiles").classList.remove("oculto");
  cargarPerfiles();
}

/* ---------- navegación por rol ---------- */
const NAV = {
  superadmin:[["adminresumen","🧠","Red GyverLabs"],["tenants","🌐","Tenants y dominios"]],
  docente:[["salones","🏫","Mis salones"],["asistencia","📋","Asistencia"],["aula","💻","Aula Virtual"],["calendario","🗓️","Mi calendario"],["notas","📗","Notas"],["riesgo","🎯","Riesgo"],["salas","🎥","Clases en vivo"],["planeacion","📋","Mi planeación"],["biblioteca","📼","Biblioteca"],["buzon","📬","Pedir recursos"],["miperfil","👤","Mi perfil y hoja de vida"]],
  coordinador:[["resumen","📊","Resumen"],["feed","📡","Qué está pasando"],["alertas","🔔","Alertas del día"],["salones","🏫","Salones"],["sedes","🏫","Sedes"],["horarios","🕐","Mapa de horarios"],["supervision","🔍","Supervisión"],["planeacion","📋","Planeaciones"],["solicitudes","📨","Solicitudes de salón"],["buzon","📬","Buzón de necesidades"],["docentes","👥","Docentes"],["riesgo","🎯","Riesgo"],["notas","📗","Notas"]],
  rector:[["resumen","📊","Resumen"],["feed","📡","Qué está pasando"],["salones","🏫","Salones"],["sedes","🏫","Sedes"],["horarios","🕐","Mapa de horarios"],["usuarios","👥","Control de usuarios"],["solicitudes","📨","Solicitudes"],["buzon","📬","Buzón de necesidades"],["personal","👥","Personal"],["comunicados","📢","Comunicados"],["riesgo","🎯","Riesgo"],["notas","📗","Notas"],["fse","💰","Fondo FSE"],["contratos","📜","Contratación"],["rejilla","📋","Rejilla y documentos"],["rejilla","📋","Rejilla y documentos"],["pagos","💸","Pagos"],["equipos","🤝","Equipos de trabajo"],["datos","🧠","Datos & IA"]],
  secretaria:[["secretaria","🏛️","Consolidado"],["instituciones","🏫","Instituciones"],["censo","👦","Censo juvenil"],["datos","🧠","Datos & IA"]],
  ministerio:[["ministerio","🇨🇴","Panorama nacional"],["datos","🧠","Datos & IA"]],
  alumno:[["altablero","🏠","Mi tablero"],["misalon","🏫","Mi salón"],["alclases","📚","Mis clases"],["alcalendario","🗓️","Mi calendario"],["alalertas","🔔","Mis alertas"],["alcertificados","📜","Mis certificados"],["altareas","📝","Tareas y talleres"],["alcurso","🎓","Mis cursos"],["alnotas","📗","Mis notas"],["alsalas","🎥","Clases en vivo"],["biblioteca","📼","Biblioteca"]],
};
const PANEL_NAV = { contratos:["contratos","📜","Contratación"], fse:["fse","💰","Fondo FSE"], datos:["datos","🧠","Datos & IA"] };

function construirNav(){
  let items;
  if(["auxiliar","contador","abogado"].includes(ST.perfil.rol)){
    const paneles=(ST.perfil.paneles||"contratos").split(",").filter(Boolean);
    items = paneles.map(p=>PANEL_NAV[p]).filter(Boolean);
    if(!items.length) items=[PANEL_NAV.contratos];
    if(ST.perfil.rol==="contador") items=[["contaduria","🧮","Mi tablero contable"]].concat(items);
    if(ST.perfil.rol==="abogado") items=[["juridica","⚖️","Mi bandeja jurídica"]].concat(items);
  } else {
    items = NAV[ST.perfil.rol]||[];
  }
  document.getElementById("sidebar-nav").innerHTML = items.map(([v,ico,lbl])=>
    `<button class="nav-btn" id="nav-${v}" onclick="irVista('${v}')"><span class="ico">${ico}</span>${lbl}<span class="nav-badge oculto" id="badge-${v}"></span></button>`).join("");
  if(ST.perfil.rol==="coordinador") actualizarBadgeAlertas();
  if(items.length) irVista(items[0][0]);
}
async function actualizarBadgeAlertas(){
  try{
    const c = await api(`/alertas/contador?institucion_id=${ST.institucion_id}`);
    const b = document.getElementById("badge-alertas");
    if(b){ if(c.abiertas>0){ b.textContent=c.abiertas; b.classList.remove("oculto"); } else b.classList.add("oculto"); }
  }catch(e){}
}
function irVista(v){
  cerrarMenuMovil();
  ST.vista=v;
  document.querySelectorAll(".nav-btn").forEach(b=>b.classList.remove("active"));
  const nb=document.getElementById("nav-"+v); if(nb) nb.classList.add("active");
  const render = VISTAS[v];
  if(render) render();
}

/* ---------- helpers de render ---------- */
function head(title, sub, btn){
  return `<div class="page-head"><div><div class="page-title">${title}</div>${sub?`<div class="page-sub">${sub}</div>`:""}</div><div style="display:flex;gap:8px;flex-wrap:wrap">${btn||""}</div></div>`;
}
function main(html){ document.getElementById("main").innerHTML = html; }
function loading(){ main(`<div class="empty">Cargando…</div>`); }

const VISTAS = {};

/* ---------- FOTO DE PERFIL ---------- */
function abrirModalFoto(pid, fotoActual){
  const propio = !pid || pid===ST.perfil.personal_id;
  if(propio && !ST.perfil.personal_id){ toast("Este perfil no tiene foto editable.",true); return; }
  window._fotoPid = propio ? ST.perfil.personal_id : pid;
  window._fotoPropia = propio;
  window._fotoData = null;
  document.getElementById("foto_prev").src = (propio ? ST.perfil.foto : fotoActual) || "";
  document.getElementById("foto_input").value = "";
  abrirModal("modal-foto");
}
function previsualizarFoto(){
  const f = document.getElementById("foto_input").files[0];
  if(!f) return;
  const img = new Image();
  const reader = new FileReader();
  reader.onload = e => {
    img.onload = () => {
      const c = document.createElement("canvas");
      const S = 220; c.width=S; c.height=S;
      const ctx = c.getContext("2d");
      const m = Math.min(img.width, img.height);
      ctx.drawImage(img, (img.width-m)/2, (img.height-m)/2, m, m, 0, 0, S, S);
      window._fotoData = c.toDataURL("image/jpeg", 0.82);
      document.getElementById("foto_prev").src = window._fotoData;
    };
    img.src = e.target.result;
  };
  reader.readAsDataURL(f);
}
async function guardarFoto(quitar){
  try{
    const foto = quitar ? null : (window._fotoData || null);
    if(!quitar && !foto){ toast("Selecciona una imagen primero.",true); return; }
    const r = await post("/perfiles/foto", {personal_id: window._fotoPid || ST.perfil.personal_id, foto});
    if(!r.ok){ toast(r.msg,true); return; }
    if(window._fotoPropia!==false){ ST.perfil.foto = foto; pintarAvatarSidebar(); }
    if(window._hv && window._hv.id===window._fotoPid){ window._hv.foto=foto; if(window.pintarHV) pintarHV(); }
    cerrarModal("modal-foto");
    toast(r.msg);
    if(ST.vista==="miperfil") VISTAS.miperfil();
  }catch(e){ toast("Error al guardar la foto",true); }
}

/* ═══════════ VISTA: SALONES (CRUD + Ver más) ═══════════ */
VISTAS.salones = async function(){
  loading();
  try{
    const salones = await api(`/academico/salones?institucion_id=${ST.institucion_id}`);
    window._salones = salones;
    const esDocente = ST.perfil.rol==="docente";
    // PUNTO 14: los salones los crea SOLO rectoría o coordinación.
    const puedeCrear = ["rector","coordinador"].includes(ST.perfil.rol);
    const titulo = esDocente ? "Mis salones" : "Salones de la institución";
    // FIX: se muestran TODOS los salones (antes un filtro ocultaba los recién creados).
    const mios = esDocente ? salones.filter(s=>s.director_id===ST.perfil.personal_id) : [];
    // PUNTO 1: el docente ve SOLO sus salones (nada de "otros salones").
    const filtrados = esDocente ? mios : salones;
    const fila = s=>`
      <tr>
        <td><div class="flex-cell"><div class="avatar-sm">${esc(s.nombre)}</div><div><b>Salón ${esc(s.nombre)}</b><div class="small muted">Grado ${esc(s.grado)} · ${esc(s.jornada)}</div></div></div></td>
        <td>${esc(s.director)}</td>
        <td><b>${s.n_estudiantes}</b> <span class="muted small">est.</span></td>
        <td>${s.en_riesgo>0?`<span class="badge b-red">${s.en_riesgo} en riesgo</span>`:`<span class="badge b-green">Sin alertas</span>`}</td>
        <td style="white-space:nowrap">
          <button class="btn btn-sm btn-primary" onclick="verSalon(${s.id})">🔍 Ver más</button>
          <button class="btn btn-sm" onclick="ST.salon_id=${s.id};irVista('asistencia')">📋</button>
          <button class="btn btn-sm" onclick="ST.salon_id=${s.id};irVista('notas')">📗</button>
          ${puedeCrear?`<button class="btn btn-sm" onclick="editarSalon(${s.id})">✎</button>
          <button class="btn btn-sm btn-danger" onclick="eliminarSalon(${s.id},'${esc(s.nombre)}')">🗑</button>`:""}
        </td>
      </tr>`;
    const rows = filtrados.map(fila).join("");
    const totEst = filtrados.reduce((a,s)=>a+s.n_estudiantes,0);
    const totRiesgo = filtrados.reduce((a,s)=>a+s.en_riesgo,0);
    const btn = puedeCrear
      ? `<button class="btn btn-primary" onclick="editarSalon(0)">➕ Nuevo salón</button>`
      : (esDocente ? `<button class="btn btn-primary" onclick="buscarSalonDocente()">🔎 Buscar mi salón</button>` : "");
    const sub = esDocente
      ? `${filtrados.length} salón(es) a tu cargo · toca "Ver más" para configurar horario, materias, cortes y temas`
      : `${filtrados.length} salones · ${totEst} estudiantes · clic en "Ver más" para horario y temas por corte`;
    main(head(titulo, sub, btn)+`
      ${esDocente?`<div class="legal-note">👋 <b>Aquí configuras todo lo tuyo:</b> entra a tu salón y define el <b>horario</b>, las <b>materias</b>, los <b>temas por corte</b> y tus clases. ¿No aparece tu salón? Usa <b>🔎 Buscar mi salón</b> y solicita la asignación: rectoría la aprueba y listo.</div>`:""}
      <div class="kpis">
        <div class="kpi"><div class="kpi-ico">🏫</div><div class="kpi-val">${filtrados.length}</div><div class="kpi-lbl">Salones</div></div>
        <div class="kpi green"><div class="kpi-ico">👨‍🎓</div><div class="kpi-val">${totEst}</div><div class="kpi-lbl">Estudiantes</div></div>
        <div class="kpi red"><div class="kpi-ico">⚠️</div><div class="kpi-val">${totRiesgo}</div><div class="kpi-lbl">En riesgo</div></div>
      </div>
      <div class="card"><div class="tbl-scroll"><table>
        <thead><tr><th>Salón</th><th>Director de grupo</th><th>Estudiantes</th><th>Riesgo</th><th>Acciones</th></tr></thead>
        <tbody>${rows||`<tr><td colspan="5" class="empty">${esDocente?"Todavía no tienes salones asignados. Usa 🔎 <b>Buscar mi salón</b> para solicitarlo.":"Sin salones. Crea el primero con ➕"}</td></tr>`}</tbody>
      </table></div></div>`);
  }catch(e){ main(`<div class="empty">Error cargando salones</div>`); }
};
const GRADOS_LISTA=[["Preescolar","Preescolar"],["1","1º Primaria"],["2","2º Primaria"],["3","3º Primaria"],["4","4º Primaria"],["5","5º Primaria"],["6","6º (Sexto)"],["7","7º (Séptimo)"],["8","8º (Octavo)"],["9","9º (Noveno)"],["10","10º (Décimo)"],["11","11º (Undécimo)"]];
const GRUPOS_LISTA=["","A","B","C","D","E","F","01","02","03","04"];
function salNombreAuto(){
  const g=document.getElementById("sal_grado").value;
  const gr=document.getElementById("sal_grupo").value;
  const base=(g==="Preescolar"?"Pre":g)+(gr||"");
  document.getElementById("sal_nombre").value=base;
}
async function editarSalon(id){
  const s = (window._salones||[]).find(x=>x.id===id);
  document.getElementById("modal-salon-title").textContent = id?`Editar salón ${s.nombre}`:"Nuevo salón";
  document.getElementById("sal_id").value = id||"";
  document.getElementById("sal_grado").innerHTML = GRADOS_LISTA.map(([v,l])=>`<option value="${v}" ${s&&s.grado===v?"selected":""}>${l}</option>`).join("");
  if(!s) document.getElementById("sal_grado").value="6";
  document.getElementById("sal_grupo").innerHTML = GRUPOS_LISTA.map(g=>`<option value="${g}">${g||"— sin grupo —"}</option>`).join("");
  if(s){ const m=s.nombre.match(/^(?:Pre|\d+)([A-F]|0\d)?$/); document.getElementById("sal_grupo").value=(m&&m[1])||""; }
  document.getElementById("sal_nombre").value = s?s.nombre:"";
  if(!s) salNombreAuto();
  document.getElementById("sal_jornada").value = s?s.jornada:"Mañana";
  const docentes = await api(`/academico/personal?institucion_id=${ST.institucion_id}&rol=docente`);
  document.getElementById("sal_director").innerHTML = `<option value="">— Sin asignar —</option>`+
    docentes.map(d=>`<option value="${d.id}" ${s&&s.director_id===d.id?"selected":""}>${esc(d.nombre)} (${esc(d.area||"")})</option>`).join("");
  abrirModal("modal-salon");
}
async function guardarSalon(){
  const body={ id:parseInt(document.getElementById("sal_id").value)||0, institucion_id:ST.institucion_id,
    nombre:document.getElementById("sal_nombre").value, grado:document.getElementById("sal_grado").value,
    jornada:document.getElementById("sal_jornada").value,
    director_id:parseInt(document.getElementById("sal_director").value)||null };
  try{ const r=await post("/academico/salones/guardar",body);
    if(!r.ok){toast(r.msg,true);return;}
    cerrarModal("modal-salon"); toast(r.msg); VISTAS.salones();
  }catch(e){ toast("Error al guardar",true); }
}
async function eliminarSalon(id,nombre){
  if(!confirm(`¿Eliminar el salón ${nombre}? (solo es posible si no tiene estudiantes)`)) return;
  try{ const r=await post("/academico/salones/eliminar",{id}); toast(r.msg, !r.ok); if(r.ok) VISTAS.salones(); }
  catch(e){ toast("Error",true); }
}
async function verSalon(id){
  try{
    const d = await api(`/academico/salones/detalle?salon_id=${id}`);
    window._detSalon = d;
    document.getElementById("detsalon-title").textContent = `Salón ${d.nombre} · Grado ${d.grado} · ${d.jornada}`;
    detSalonTab("info");
    abrirModal("modal-detsalon");
  }catch(e){ toast("Error al cargar el salón",true); }
}
function detSalonTab(t){
  const d = window._detSalon;
  const puedeGestion = ["docente","rector","coordinador"].includes(ST.perfil.rol);
  const tabs = `<div class="subtabs">
    ${[["info","ℹ️ Información"],["est","👨‍🎓 Estudiantes"],["cortes","📆 Cortes"],["horario","🕐 Horario"],["temas","📚 Temas por corte"]].map(([k,l])=>
      `<button class="subtab ${t===k?'active':''}" onclick="detSalonTab('${k}')">${l}</button>`).join("")}</div>`;
  let html="";
  if(t==="info"){
    html = `<div class="info-grid">
      <div class="info-it"><span class="k">Director de grupo</span><b>${esc(d.director)}</b></div>
      <div class="info-it"><span class="k">Estudiantes</span><b>${d.n_estudiantes}</b></div>
      <div class="info-it"><span class="k">Grado · Jornada</span><b>${esc(d.grado)} · ${esc(d.jornada)}</b></div>
      <div class="info-it"><span class="k">Franjas de horario</span><b>${d.horarios.length}</b></div>
    </div>
    <div class="legal-note">Gestiona los <b>estudiantes</b> del salón (agregar, mover, retirar), los <b>cortes</b> de cada período con sus fechas, el <b>horario</b> de clases (alimenta el calendario del docente) y los <b>temas por corte</b>.</div>`;
  }
  if(t==="est"){
    html = `<div style="display:flex;gap:8px;margin-bottom:10px;flex-wrap:wrap">
      <button class="btn btn-sm btn-primary" onclick="nuevoEstudiante()">➕ Nuevo estudiante</button>
      <button class="btn btn-sm" onclick="agregarSinSalon()">📥 Agregar estudiante sin salón</button>
    </div>
    <div id="detsalon-est"><div class="empty">Cargando estudiantes…</div></div>`;
  }
  if(t==="cortes"){
    const porP={};
    d.cortes.forEach(c=>{ (porP[c.periodo]=porP[c.periodo]||[]).push(c); });
    const esRector = ST.perfil.rol==="rector";
    html = `<div class="small muted" style="margin-bottom:10px">Cada período se divide en cortes con sus fechas. ${esRector?"Puedes <b>agregar cortes nuevos</b> o eliminar (con confirmación fuerte: se pierde la organización ligada al corte).":"Las fechas las administra rectoría."}</div>
      ${Object.keys(porP).sort().map(p=>`
        <div class="card"><div class="card-head"><h3>Período ${p}</h3>
          ${esRector?`<button class="btn btn-xs btn-primary" onclick="abrirModalCorte(${p})">➕ Agregar corte</button>`:""}</div>
        <div class="tbl-scroll"><table><thead><tr><th>Corte</th><th>Inicio</th><th>Fin</th>${esRector?'<th></th>':''}</tr></thead><tbody>
        ${porP[p].map(c=>`<tr><td><b>${esc(c.nombre)}</b></td>
          <td><input type="date" id="ci-${c.id}" value="${c.inicio||''}" class="nota-in" style="width:140px" ${!esRector?'disabled':''}></td>
          <td><input type="date" id="cf-${c.id}" value="${c.fin||''}" class="nota-in" style="width:140px" ${!esRector?'disabled':''}></td>
          ${esRector?`<td style="white-space:nowrap"><button class="btn btn-xs" onclick="guardarCorte(${c.id})">💾</button>
            <button class="btn btn-xs btn-danger" onclick="eliminarCorte(${c.id},'${esc(c.nombre)}')">🗑</button></td>`:''}</tr>`).join("")}
        </tbody></table></div></div>`).join("")}`;
  }
  if(t==="horario"){
    const dias=["Lunes","Martes","Miércoles","Jueves","Viernes"];
    const porDia={};
    d.horarios.forEach((h,i)=>{ (porDia[h.dia]=porDia[h.dia]||[]).push({...h,_i:i}); });
    html = `<div class="small muted" style="margin-bottom:10px">Edita la materia de cada franja y guarda. Estas clases alimentan automáticamente el <b>calendario del docente</b>.</div>
      <div class="tbl-scroll"><table><thead><tr><th>Día</th><th>Hora</th><th>Materia</th></tr></thead><tbody>
      ${dias.map(dia=>(porDia[dia]||[]).map((h,j)=>`
        <tr>${j===0?`<td rowspan="${porDia[dia].length}"><b>${dia}</b></td>`:""}
        <td class="small">${esc(h.hora)}</td>
        <td><input id="hm-${h._i}" value="${esc(h.materia)}" class="nota-in" style="width:170px;text-align:left" ${!puedeGestion?'disabled':''}></td></tr>`).join("")).join("")}
      </tbody></table></div>
      ${puedeGestion?`<div style="margin-top:12px;text-align:right"><button class="btn btn-primary" onclick="guardarHorario()">💾 Guardar horario</button></div>`:""}`;
  }
  if(t==="temas"){
    const porP={};
    d.temas.forEach(x=>{ const k=`P${x.periodo} · ${x.corte||"(sin corte)"}`; (porP[k]=porP[k]||[]).push(x); });
    const cortesOpts = d.cortes.map(c=>`<option>${esc(c.nombre)}</option>`).join("");
    html = `<div class="small muted" style="margin-bottom:10px">Los temas que manejas en cada período, divididos por corte según las fechas exactas de tu institución.</div>
      ${Object.entries(porP).map(([k,arr])=>`
        <div style="margin-bottom:12px"><b class="small">${k}</b>
        ${arr.map(x=>`<div class="obs-item obs-compromiso" style="display:flex;justify-content:space-between;align-items:center;gap:8px">
          <div><b>${esc(x.tema)}</b> <span class="badge b-blue">${esc(x.materia||"")}</span><div class="small muted">${esc(x.detalle||"")}</div></div>
          <button class="btn btn-xs btn-danger" onclick="eliminarTema(${x.id})">🗑</button></div>`).join("")}</div>`).join("")||'<div class="empty">Sin temas aún.</div>'}
      <div class="card"><div class="card-body">
        <b class="small">➕ Agregar tema</b>
        <div class="frow-3" style="margin-top:8px">
          <div><label class="small">Período</label><select id="tm_per"><option value="1">P1</option><option value="2">P2</option><option value="3" selected>P3</option><option value="4">P4</option></select></div>
          <div><label class="small">Corte</label><select id="tm_corte">${cortesOpts}</select></div>
          <div><label class="small">Materia</label><input id="tm_mat" placeholder="Matemáticas"></div>
        </div>
        <div class="frow"><label class="small">Tema *</label><input id="tm_tema" placeholder="Ecuaciones lineales"></div>
        <div style="text-align:right"><button class="btn btn-primary btn-sm" onclick="guardarTema()">💾 Agregar tema</button></div>
      </div></div>`;
  }
  document.getElementById("detsalon-body").innerHTML = tabs + html;
  if(t==="est") cargarEstudiantesSalon();
}
async function guardarCorte(id){
  try{ const r=await post("/academico/cortes/guardar",{id, inicio:document.getElementById("ci-"+id).value||null, fin:document.getElementById("cf-"+id).value||null});
    toast(r.msg,!r.ok);
  }catch(e){ toast("Error",true); }
}
async function guardarHorario(){
  const d=window._detSalon;
  const horarios=d.horarios.map((h,i)=>({dia:h.dia,hora:h.hora,materia:document.getElementById("hm-"+i).value}));
  try{ const r=await post("/academico/salones/horarios/guardar",{salon_id:d.id,horarios}); toast(r.msg,!r.ok);
    if(r.ok){ d.horarios=horarios; } }
  catch(e){ toast("Error",true); }
}
async function guardarTema(){
  const d=window._detSalon;
  const body={salon_id:d.id, periodo_numero:parseInt(document.getElementById("tm_per").value),
    corte:document.getElementById("tm_corte").value, materia:document.getElementById("tm_mat").value,
    tema:document.getElementById("tm_tema").value};
  if(!body.tema.trim()){toast("Escribe el tema",true);return;}
  try{ const r=await post("/academico/temas/guardar",body); toast(r.msg,!r.ok);
    if(r.ok){ verSalon(d.id); setTimeout(()=>detSalonTab("temas"),250); } }
  catch(e){ toast("Error",true); }
}
async function eliminarTema(id){
  try{ const r=await post("/academico/temas/eliminar",{id}); toast(r.msg,!r.ok);
    if(r.ok){ verSalon(window._detSalon.id); setTimeout(()=>detSalonTab("temas"),250); } }
  catch(e){ toast("Error",true); }
}

/* ═══════════ VISTA: ASISTENCIA PRO ═══════════ */
VISTAS.asistencia = async function(){
  loading();
  try{
    const salones = await api(`/academico/salones?institucion_id=${ST.institucion_id}`);
    if(!ST.salon_id && salones.length) ST.salon_id = salones[0].id;
    if(!salones.find(s=>s.id===ST.salon_id) && salones.length) ST.salon_id=salones[0].id;
    const hoy = hoyISO();
    const selSalon = `<select id="asis-salon" onchange="ST.salon_id=parseInt(this.value);VISTAS.asistencia()">
      ${salones.map(s=>`<option value="${s.id}" ${s.id===ST.salon_id?"selected":""}>Salón ${esc(s.nombre)} (${s.n_estudiantes})</option>`).join("")}</select>`;
    main(head("Registro de asistencia", "Toca el estado de cada estudiante — las ausencias avisan solas a coordinación y al acudiente",
      `<button class="btn" onclick="abrirHistorialAsistencia()">📋 Ver historial y score</button>`)+`
      <div class="card"><div class="card-body">
        <div style="display:flex;align-items:flex-end;gap:14px;flex-wrap:wrap;margin-bottom:10px">
          <div class="form-inline"><label>Salón</label>${selSalon}</div>
          <div class="form-inline"><label>Fecha</label><input type="date" id="asis-fecha" value="${hoy}" onchange="cargarAsistencia()"></div>
          <div class="fecha-hoy">📅 Hoy es ${fechaBonita(hoy)}</div>
          <div style="margin-left:auto;display:flex;gap:8px">
            <button class="btn btn-sm" onclick="marcarTodos('present')">✓ Todos presentes</button>
            <button class="btn btn-primary" onclick="guardarAsistencia()">💾 Guardar asistencia</button>
          </div>
        </div>
        <div class="att-chips" id="att-chips"></div>
      </div></div>
      <div class="card"><div class="tbl-scroll"><table>
        <thead><tr><th>Estudiante</th><th style="width:190px">Estado</th><th>Observación</th></tr></thead>
        <tbody id="asis-body"><tr><td colspan="3" class="empty">Cargando…</td></tr></tbody>
      </table></div></div>
      <div class="small muted">P = Presente · T = Tarde · E = Excusa · A = Ausente. Al guardar, cada <b>A</b> crea la alerta del coordinador 🔔 y el WhatsApp al acudiente 📱 (simulado), y recalcula el riesgo.</div>`);
    await cargarAsistencia();
  }catch(e){ main(`<div class="empty">Error</div>`); }
};
async function cargarAsistencia(){
  const fecha = document.getElementById("asis-fecha").value;
  const d = await api(`/asistencia/cargar?salon_id=${ST.salon_id}&fecha=${fecha}`);
  window._asis = d.filas;
  document.getElementById("asis-body").innerHTML = d.filas.map((f,i)=>`
    <tr id="fila-asis-${i}">
      <td><div class="flex-cell"><div class="avatar-sm">${ini(f.nombre)}</div>${esc(f.nombre)}</div></td>
      <td><div class="att-seg" id="seg-${i}">
        ${["present","late","excused","absent"].map(e=>{
          const L={present:"P",late:"T",excused:"E",absent:"A"}[e];
          const on=f.estado===e?`att-on att-${e}`:"";
          return `<button class="att-btn ${on}" data-i="${i}" data-e="${e}" onclick="setAsis(${i},'${e}')">${L}</button>`;
        }).join("")}
      </div></td>
      <td><input class="att-obs" id="obs-${i}" value="${esc(f.observacion)}" placeholder="—"></td>
    </tr>`).join("");
  pintarChips();
}
function pintarChips(){
  const c={present:0,late:0,excused:0,absent:0};
  (window._asis||[]).forEach(f=>c[f.estado]=(c[f.estado]||0)+1);
  document.getElementById("att-chips").innerHTML = `
    <div class="att-chip c-present">✅ Presentes <b>${c.present}</b></div>
    <div class="att-chip c-late">⏰ Tarde <b>${c.late}</b></div>
    <div class="att-chip c-excused">📝 Excusa <b>${c.excused}</b></div>
    <div class="att-chip c-absent">🚨 Ausentes <b>${c.absent}</b></div>`;
}
function setAsis(i,estado){
  window._asis[i].estado=estado;
  const seg=document.getElementById("seg-"+i);
  seg.querySelectorAll(".att-btn").forEach(b=>{
    const e=b.dataset.e;
    b.className="att-btn"+(e===estado?` att-on att-${e}`:"");
  });
  pintarChips();
}
function marcarTodos(estado){ (window._asis||[]).forEach((f,i)=>setAsis(i,estado)); }
async function guardarAsistencia(){
  const fecha=document.getElementById("asis-fecha").value;
  const filas=window._asis.map((f,i)=>({estudiante_id:f.estudiante_id,estado:f.estado,observacion:document.getElementById("obs-"+i).value}));
  try{
    toast("Guardando y recalculando riesgo…");
    const r=await post("/asistencia/guardar",{salon_id:ST.salon_id,fecha,filas});
    toast(r.msg);
  }catch(e){ toast("Error al guardar",true); }
}

/* ═══════════ VISTA: AULA VIRTUAL PRO ═══════════ */
VISTAS.aula = async function(tab){
  loading();
  try{
    const salonesTodos = await api(`/academico/salones?institucion_id=${ST.institucion_id}`);
    window._salones = salonesTodos;
    const mios = ST.perfil.rol==="docente" ? salonesTodos.filter(s=>s.director_id===ST.perfil.personal_id) : salonesTodos;
    const salones = mios.length?mios:salonesTodos;
    window._misSalones = salones;
    const salIds = new Set(salones.map(s=>s.id));
    const actsTodas = await api(`/aula/actividades?institucion_id=${ST.institucion_id}`);
    const acts = ST.perfil.rol==="docente" ? actsTodas.filter(a=>salIds.has(a.salon_id)) : actsTodas;
    window._acts = acts;
    if(!acts.length){
      main(head("Aula Virtual","Tu plataforma de clases en línea")+`
        <div class="big-wiz-invite">
          <h2>👋 ¡Hola! Vamos a preparar tu primera clase</h2>
          <p>No necesitas saber de tecnología: el asistente te guía paso a paso — eliges el salón, subes tus materiales (PDF, videos), la <b>IA te arma el plan de clase</b> y publicas. Tus estudiantes la ven al instante.</p>
          <button class="btn btn-gold" style="font-size:1rem;padding:12px 24px" onclick="abrirConstructor(0)">🚀 Crear mi primera clase</button>
        </div>`);
      return;
    }
    const t = tab||"clases";
    main(head("Aula Virtual", `${acts.length} contenidos publicados en tus salones`,
      `<button class="btn btn-primary" onclick="abrirConstructor(0)">➕ Crear clase</button>`)+`
      <div class="subtabs">
        <button class="subtab ${t==='clases'?'active':''}" onclick="VISTAS.aula('clases')">📚 Mis clases y contenidos</button>
        <button class="subtab ${t==='eval'?'active':''}" onclick="VISTAS.aula('eval')">🧪 Evaluaciones y recuperaciones</button>
      </div>
      <div id="aula-cont"></div>`);
    const filtradas = t==="eval" ? acts.filter(a=>["evaluacion","recuperacion"].includes(a.tipo)) : acts;
    pintarAulaCards(filtradas);
  }catch(e){ main(`<div class="empty">Error</div>`); }
};
function pintarAulaCards(acts){
  const principales = acts.filter(a=>!a.padre_id);
  document.getElementById("aula-cont").innerHTML = `<div class="grid-cards">
    ${principales.map(a=>`
      <div class="va-card">
        ${a.generado_ia?'<div class="ia-tag">🤖 IA</div>':''}
        <div class="va-top"><span class="va-tipo">${TIPO_ICO[a.tipo]||"📝"} ${esc(a.tipo)}</span><span class="small muted">Salón ${esc(a.salon)}</span></div>
        <h4 style="cursor:pointer" onclick="abrirClaseDocente(${a.id})">${esc(a.titulo)} ${a.n_sub?`<span class="badge b-purple">🔗 ${a.n_sub}</span>`:""}</h4>
        <div class="small muted" style="min-height:32px">${esc((a.descripcion||"").slice(0,90))}</div>
        <div>${(a.materiales||[]).map(m=>`<span class="mat-chip">${MAT_ICO[m.tipo]||"📎"} ${esc(m.nombre.slice(0,18))}</span>`).join("")}</div>
        ${a.tipo==='evaluacion'?`<div class="small" style="margin-top:6px">⏱️ ${a.tiempo_limite_min||45} min · ${a.permite_recuperacion?"♻️ con recuperación":"sin recuperación"}</div>`:""}
        <div class="va-meta">
          <span>${a.materia?esc(a.materia):"—"} · P${a.periodo||3}</span>
          <span>${a.fecha_limite?"📅 "+esc(a.fecha_limite):""}</span>
        </div>
        <div style="margin-top:9px"><div class="prog"><div class="prog-fill" style="width:${a.n_total?Math.round(100*a.n_entregas/a.n_total):0}%"></div></div>
        <div class="small muted" style="margin-top:4px">${a.n_entregas}/${a.n_total} entregas · ${a.n_revisadas} calificadas</div></div>
        <div style="margin-top:10px;display:flex;gap:5px;flex-wrap:wrap">
          <button class="btn btn-xs btn-primary" onclick="event.stopPropagation();verEntregasDe(${a.id})">📝 Ver entregas</button>
          <button class="btn btn-xs" onclick="event.stopPropagation();abrirConstructor(${a.id})">✎ Editar</button>
          <button class="btn btn-xs" onclick="event.stopPropagation();duplicarClase(${a.id})" title="Duplicar">📋</button>
          <button class="btn btn-xs btn-danger" onclick="event.stopPropagation();eliminarClase(${a.id},'${esc(a.titulo)}')">🗑</button>
        </div>
      </div>`).join("")||'<div class="empty">Nada por aquí todavía.</div>'}
  </div>`;
}
window._aulaCards = pintarAulaCards;
async function verActividad(id, tab){
  try{
    const a = (window._acts||[]).find(x=>x.id===id);
    window._actSel = a;
    document.getElementById("modal-srd-title").textContent = `${TIPO_ICO[a.tipo]||"📝"} ${a.titulo}`;
    actTab(tab||"contenido");
    abrirModal("modal-srd");
  }catch(e){ toast("Error",true); }
}
async function actTab(t){
  const a = window._actSel;
  const subs = (window._acts||[]).filter(x=>x.padre_id===a.id);
  const tabs = `<div class="subtabs">
    ${[["contenido","📖 Contenido"],["entregas",`📝 Entregas (${a.n_entregas}/${a.n_total})`],["ajustes","⚙️ Ajustes"]].map(([k,l])=>
      `<button class="subtab ${t===k?'active':''}" onclick="actTab('${k}')">${l}</button>`).join("")}</div>`;
  let body="";
  if(t==="contenido"){
    body=`
      <div class="info-grid">
        <div class="info-it"><span class="k">Salón</span><b>${esc(a.salon)}</b></div>
        <div class="info-it"><span class="k">Materia · Período</span><b>${esc(a.materia||"—")} · P${a.periodo||3}</b></div>
        <div class="info-it"><span class="k">Fecha límite</span><b>${a.fecha_limite||"—"}</b></div>
        ${a.tipo==='evaluacion'?`<div class="info-it"><span class="k">⏱️ Tiempo · Recuperación</span><b>${a.tiempo_limite_min||45} min · ${a.permite_recuperacion?"Sí":"No"}</b></div>`:""}
      </div>
      ${a.reglas?`<div class="legal-note">📏 <b>Reglas:</b> ${esc(a.reglas)}</div>`:""}
      <div class="card"><div class="card-head"><h3>📄 Vista previa para el estudiante</h3>
        <button class="btn btn-sm btn-gold" onclick="window.open(API+'/aula/actividades/guia?id=${a.id}')">⬇️ Descargar guía (PDF)</button></div>
      <div class="card-body">
        <p class="small" style="white-space:pre-line">${esc(a.descripcion||"Sin descripción.")}</p>
        <div style="margin-top:8px">${(a.materiales||[]).map(m=>`<span class="mat-chip">${MAT_ICO[m.tipo]||"📎"} ${esc(m.nombre)}</span>`).join("")||'<span class="small muted">Sin materiales.</span>'}</div>
      </div></div>
      ${subs.length?`<b class="small">🔗 Talleres y evaluaciones asociados a esta clase</b>
        ${subs.map(s=>`<div class="obs-item obs-compromiso" style="display:flex;justify-content:space-between;align-items:center;cursor:pointer" onclick="verActividad(${s.id})">
          <div><b>${TIPO_ICO[s.tipo]||"📝"} ${esc(s.titulo)}</b><div class="small muted">${s.fecha_limite?"Límite: "+esc(s.fecha_limite)+" · ":""}${s.n_entregas}/${s.n_total} entregas</div></div>
          <span class="btn btn-xs">Abrir ▸</span></div>`).join("")}`:""}
      <div style="margin-top:10px"><button class="btn btn-sm btn-primary" onclick="cerrarModal('modal-srd');abrirWizardSub(${a.id})">➕ Agregar taller / evaluación a esta clase</button></div>`;
  }
  if(t==="entregas"){
    const ents = await api(`/aula/entregas?actividad_id=${a.id}`);
    body=`<div class="tbl-scroll" style="max-height:340px;overflow-y:auto"><table>
      <thead><tr><th>Estudiante</th><th>Estado</th><th style="width:80px">Nota</th><th>Retroalimentación</th><th></th></tr></thead><tbody>
      ${ents.map(en=>`<tr>
        <td class="small">${esc(en.estudiante)}</td>
        <td>${en.estado==="revisado"?'<span class="badge b-green">Revisado</span>':en.estado==="entregado"?'<span class="badge b-blue">Entregado</span>':'<span class="badge b-gray">Pendiente</span>'}</td>
        <td><input class="nota-in" id="en-nota-${en.id}" type="number" min="0" max="5" step="0.1" value="${en.nota!=null?en.nota:""}"></td>
        <td><input class="att-obs" id="en-retro-${en.id}" value="${esc(en.retro||"")}" placeholder="Comentario…"></td>
        <td><button class="btn btn-xs btn-green" onclick="calificarEntrega(${en.id},${a.id})">💾</button></td>
      </tr>`).join("")}
    </tbody></table></div>`;
  }
  if(t==="ajustes"){
    body=`
      <div class="frow"><label>Título</label><input id="aj_titulo" value="${esc(a.titulo)}"></div>
      <div class="frow-3">
        <div><label>Fecha límite</label><input type="date" id="aj_fecha" value="${a.fecha_limite||''}"></div>
        <div><label>⏱️ Tiempo (min)</label><input type="number" id="aj_tiempo" value="${a.tiempo_limite_min||45}" min="5" max="240"></div>
        <div><label>Estado</label><select id="aj_estado"><option value="publicada" ${a.estado!=='cerrada'?'selected':''}>Publicada</option><option value="cerrada" ${a.estado==='cerrada'?'selected':''}>Cerrada (no recibe más entregas)</option></select></div>
      </div>
      <div class="frow"><label>📏 Reglas</label><input id="aj_reglas" value="${esc(a.reglas||'')}"></div>
      <div class="frow"><label>Descripción / instrucciones</label><textarea id="aj_desc" rows="5">${esc(a.descripcion||'')}</textarea></div>
      <div class="frow"><label>Materiales</label>
        <div id="aj_mats">${(a.materiales||[]).map((m,i)=>`<span class="mat-chip">${MAT_ICO[m.tipo]||"📎"} ${esc(m.nombre)} <a href="#" onclick="window._actSel.materiales.splice(${i},1);actTab('ajustes');return false">✕</a></span>`).join("")||'<span class="small muted">Sin materiales.</span>'}</div>
        <div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap">
          <select id="aj_mtipo" style="max-width:110px"><option value="pdf">📄 PDF</option><option value="video">🎬 Video</option><option value="enlace">🔗 Enlace</option><option value="imagen">🖼️ Img</option></select>
          <input id="aj_mnombre" placeholder="Nombre del archivo o enlace" style="flex:1;min-width:150px">
          <button class="btn btn-sm" onclick="if(document.getElementById('aj_mnombre').value.trim()){window._actSel.materiales.push({tipo:document.getElementById('aj_mtipo').value,nombre:document.getElementById('aj_mnombre').value});actTab('ajustes')}">➕</button>
        </div></div>
      <div style="text-align:right"><button class="btn btn-primary" onclick="guardarAjustesAct()">💾 Guardar cambios</button></div>`;
  }
  document.getElementById("modal-srd-body").innerHTML = tabs + body;
}
async function guardarAjustesAct(){
  const a=window._actSel;
  const body={id:a.id, titulo:document.getElementById("aj_titulo").value,
    descripcion:document.getElementById("aj_desc").value,
    fecha_limite:document.getElementById("aj_fecha").value||"",
    tiempo_limite_min:parseInt(document.getElementById("aj_tiempo").value)||45,
    reglas:document.getElementById("aj_reglas").value,
    materiales:a.materiales, estado:document.getElementById("aj_estado").value};
  try{ const r=await post("/aula/actividades/editar",body);
    toast(r.msg,!r.ok);
    if(r.ok){ cerrarModal("modal-srd"); VISTAS.aula(); }
  }catch(e){ toast("Error",true); }
}
async function calificarEntrega(id, actId){
  const nota=parseFloat(document.getElementById("en-nota-"+id).value);
  const retro=document.getElementById("en-retro-"+id).value;
  if(isNaN(nota)){ toast("Escribe la nota (0.0 a 5.0)",true); return; }
  try{ const r=await post("/aula/entregas/calificar",{id,nota,retro}); toast(r.msg,!r.ok); }
  catch(e){ toast("Error",true); }
}

/* ── Wizard de creación (4 pasos, con IA) ── */
let WIZ = {};
function abrirWizard(){
  WIZ = { paso:1, tipo:"clase", modo:"ia", padre_id:null,
    salon_id:(window._misSalones&&window._misSalones[0]?window._misSalones[0].id:ST.salon_id),
    materia:"", periodo:3, titulo:"", desc:"", materiales:[], fecha:"", tiempo:45, reglas:"", recup:true,
    ia_tema:"", ia_horas:2, ia_archivos:[], plan:null, generado_ia:false };
  pintarWizard();
  abrirModal("modal-clase");
}
function abrirWizardSub(padreId){
  const padre=(window._acts||[]).find(x=>x.id===padreId);
  abrirWizard();
  WIZ.padre_id=padreId; WIZ.tipo="taller"; WIZ.modo="manual";
  if(padre){ WIZ.salon_id=padre.salon_id; WIZ.materia=padre.materia||""; WIZ.titulo=""; }
  document.getElementById("clase-title").textContent="🔗 Agregar taller/evaluación a: "+(padre?padre.titulo:"la clase");
  pintarWizard();
}
function wizPasos(){
  const labels=["Lo básico","Contenido + IA","Reglas y fechas","Revisar y publicar"];
  return `<div class="wiz-steps">${[1,2,3,4].map(n=>`
    <div class="wiz-dot ${WIZ.paso===n?'active':WIZ.paso>n?'done':''}">${WIZ.paso>n?'✓':n}</div>
    ${n<4?`<div class="wiz-line ${WIZ.paso>n?'done':''}"></div>`:''}`).join("")}</div>
    <div class="wiz-lbl">Paso ${WIZ.paso} de 4 — <b>${labels[WIZ.paso-1]}</b></div>`;
}
function pintarWizard(){
  const c=document.getElementById("wiz-cont");
  let body="";
  if(WIZ.paso===1){
    body=`
      ${WIZ.padre_id?`<div class="legal-note">🔗 Este contenido quedará <b>asociado a la clase</b> que acabas de crear: el estudiante lo verá dentro de ella.</div>`:""}
      <div class="frow"><label>1️⃣ ¿Qué vas a crear?</label>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          ${[["clase","🧑‍🏫 Clase"],["taller","📝 Taller"],["evaluacion","🧪 Evaluación"],["curso","📚 Curso"],["recuperacion","♻️ Recuperación"],["video","🎬 Video"],["lectura","📖 Lectura"],["foro","💬 Foro"]].map(([k,l])=>
            `<button class="chip-filtro ${WIZ.tipo===k?'active':''}" onclick="WIZ.tipo='${k}';pintarWizard()">${l}</button>`).join("")}
        </div></div>
      <div class="frow"><label>2️⃣ ¿Cómo la quieres preparar?</label>
        <div class="wiz-modos">
          <div class="wiz-modo ${WIZ.modo==='ia'?'sel':''}" onclick="WIZ.modo='ia';pintarWizard()">
            <div class="ic">🤖</div><b>Con asistente IA</b>
            <div class="small">Subes tus archivos, dices el tema y la IA te arma el plan de clase completo.</div>
          </div>
          <div class="wiz-modo ${WIZ.modo==='manual'?'sel':''}" onclick="WIZ.modo='manual';pintarWizard()">
            <div class="ic">✍️</div><b>Manual (yo lo escribo)</b>
            <div class="small">Escribes la descripción y subes tus materiales tú mismo, sin IA.</div>
          </div>
        </div></div>
      <div class="frow-3">
        <div><label>Salón *</label><select id="wz_salon" onchange="WIZ.salon_id=parseInt(this.value)">
          ${(window._misSalones||[]).map(s=>`<option value="${s.id}" ${s.id===WIZ.salon_id?"selected":""}>Salón ${esc(s.nombre)}</option>`).join("")}</select></div>
        <div><label>Materia</label><input id="wz_materia" value="${esc(WIZ.materia)}" placeholder="Matemáticas" oninput="WIZ.materia=this.value"></div>
        <div><label>Período</label><select id="wz_per" onchange="WIZ.periodo=parseInt(this.value)"><option value="3" selected>P3 (activo)</option><option value="4">P4</option></select></div>
      </div>
      <div class="frow"><label>Título *</label><input id="wz_titulo" value="${esc(WIZ.titulo)}" placeholder="Ej: Fracciones en la vida real" oninput="WIZ.titulo=this.value"></div>`;
  }
  if(WIZ.paso===2 && WIZ.modo==="manual"){
    body=`
      <div class="frow"><label>✍️ Descripción / contenido para el estudiante *</label>
        <textarea id="wz_desc" rows="7" placeholder="Escribe aquí tu clase: objetivo, actividades, instrucciones de entrega…" oninput="WIZ.desc=this.value">${esc(WIZ.desc)}</textarea></div>
      <div class="frow"><label>📎 Sube tus materiales (PDF, videos, guías — simulado)</label>
        <div class="dropzone" onclick="document.getElementById('wz_files_man').click()">Toca aquí para agregar archivos<br><span class="small">${WIZ.materiales.length?"":"aún no has agregado archivos"}</span></div>
        <input type="file" id="wz_files_man" multiple style="display:none" onchange="manArchivos(this)">
        <div style="margin-top:8px">${WIZ.materiales.map((m,i)=>`<span class="mat-chip">${MAT_ICO[m.tipo]||"📎"} ${esc(m.nombre)}${m.tamano?` <span style="opacity:.6">${esc(m.tamano)}</span>`:""} <a href="#" onclick="WIZ.materiales.splice(${i},1);pintarWizard();return false">✕</a></span>`).join("")}</div>
        <div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap">
          <select id="wz_mtipo" style="max-width:120px"><option value="pdf">📄 PDF</option><option value="video">🎬 Video</option><option value="enlace">🔗 Enlace</option><option value="imagen">🖼️ Imagen</option></select>
          <input id="wz_mnombre" placeholder="…o escribe el nombre / enlace" style="flex:1;min-width:160px">
          <button class="btn btn-sm" onclick="agregarMaterial()">➕ Agregar</button>
        </div></div>`;
  }
  if(WIZ.paso===2 && WIZ.modo==="ia"){
    body=`
      <div class="ia-panel">
        <h4>🤖 Asistente IA GyverLabs — sube tus archivos y te preparo la clase</h4>
        <div class="frow-3">
          <div><label class="small">Tema de la clase</label><input id="ia_tema" value="${esc(WIZ.ia_tema||WIZ.titulo)}" placeholder="Ecuaciones lineales"></div>
          <div><label class="small">Grado</label><input id="ia_grado" value="${(window._misSalones||[]).find(s=>s.id===WIZ.salon_id)?.grado||''}"></div>
          <div><label class="small">Horas de clase</label><input id="ia_horas" type="number" min="1" max="8" value="${WIZ.ia_horas}"></div>
        </div>
        <div class="dropzone" onclick="document.getElementById('ia_files').click()">📎 Toca aquí para "subir" tus PDF, videos o guías (simulado)<br><span class="small">${WIZ.ia_archivos.length?WIZ.ia_archivos.map(a=>"«"+esc(a)+"»").join(" · "):"aún no has agregado archivos"}</span></div>
        <input type="file" id="ia_files" multiple style="display:none" onchange="iaArchivos(this)">
        <div style="text-align:center;margin-top:10px"><button class="btn btn-gold" onclick="iaPreparar()">✨ Preparar mi clase con IA</button></div>
        <div id="ia_plan">${WIZ.plan?pintarPlanIA(WIZ.plan):""}</div>
      </div>
      <div class="frow"><label>Descripción / instrucciones para el estudiante</label>
        <textarea id="wz_desc" rows="4" oninput="WIZ.desc=this.value">${esc(WIZ.desc)}</textarea></div>
      <div class="frow"><label>Materiales adjuntos</label>
        <div id="wz_mats">${WIZ.materiales.map((m,i)=>`<span class="mat-chip">${MAT_ICO[m.tipo]||"📎"} ${esc(m.nombre)} <a href="#" onclick="WIZ.materiales.splice(${i},1);pintarWizard();return false">✕</a></span>`).join("")||'<span class="small muted">Ninguno aún — usa la IA o agrega manual:</span>'}</div>
        <div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap">
          <select id="wz_mtipo" style="max-width:120px"><option value="pdf">📄 PDF</option><option value="video">🎬 Video</option><option value="enlace">🔗 Enlace</option><option value="imagen">🖼️ Imagen</option></select>
          <input id="wz_mnombre" placeholder="Nombre del archivo o enlace" style="flex:1;min-width:160px">
          <button class="btn btn-sm" onclick="agregarMaterial()">➕ Agregar</button>
        </div></div>`;
  }
  if(WIZ.paso===3){
    const esEval = ["evaluacion","recuperacion"].includes(WIZ.tipo);
    body=`
      <div class="frow-2">
        <div><label>Fecha límite de entrega</label><input type="date" id="wz_fecha" value="${WIZ.fecha}" onchange="WIZ.fecha=this.value"></div>
        ${esEval?`<div><label>⏱️ Tiempo límite (minutos)</label><input type="number" id="wz_tiempo" value="${WIZ.tiempo}" min="5" max="240" oninput="WIZ.tiempo=parseInt(this.value)||45"></div>`:"<div></div>"}
      </div>
      ${esEval?`<div class="frow"><label>📏 Reglas de la evaluación</label><input id="wz_reglas" value="${esc(WIZ.reglas||'Individual · Un solo intento · Sin materiales de apoyo')}" oninput="WIZ.reglas=this.value"></div>`:""}
      <div class="check-row"><input type="checkbox" id="wz_recup" ${WIZ.recup?"checked":""} onchange="WIZ.recup=this.checked">
        <label for="wz_recup" style="margin:0">♻️ Permitir <b>recuperación</b> para estudiantes con inasistencia justificada o nota &lt; 3.0</label></div>
      <div class="legal-note">💡 Al publicar: se crea la entrega pendiente para cada estudiante del salón, la fecha límite entra a tu <b>calendario</b> y todo queda en el <b>log de metadatos</b> para los modelos de IA.</div>`;
  }
  if(WIZ.paso===4){
    const sal=(window._misSalones||[]).find(s=>s.id===WIZ.salon_id);
    body=`
      <div class="card"><div class="card-body">
        <div class="va-top"><span class="va-tipo">${TIPO_ICO[WIZ.tipo]} ${WIZ.tipo}</span>${WIZ.generado_ia?'<span class="badge b-purple">🤖 plan con IA</span>':''}</div>
        <h3 style="margin:4px 0 8px">${esc(WIZ.titulo||"(sin título)")}</h3>
        <div class="info-grid">
          <div class="info-it"><span class="k">Salón</span><b>${sal?("Salón "+esc(sal.nombre)):"—"}</b></div>
          <div class="info-it"><span class="k">Materia · Período</span><b>${esc(WIZ.materia||"—")} · P${WIZ.periodo}</b></div>
          <div class="info-it"><span class="k">Fecha límite</span><b>${WIZ.fecha||"—"}</b></div>
          ${["evaluacion","recuperacion"].includes(WIZ.tipo)?`<div class="info-it"><span class="k">Tiempo · Recuperación</span><b>${WIZ.tiempo} min · ${WIZ.recup?"Sí":"No"}</b></div>`:""}
        </div>
        <div>${WIZ.materiales.map(m=>`<span class="mat-chip">${MAT_ICO[m.tipo]||"📎"} ${esc(m.nombre)}</span>`).join("")}</div>
        <p class="small" style="margin-top:8px;white-space:pre-line">${esc((WIZ.desc||"").slice(0,400))}</p>
      </div></div>`;
  }
  c.innerHTML = wizPasos()+body+`
    <div class="modal-foot" style="border:none;padding:14px 0 0">
      ${WIZ.paso>1?`<button class="btn" onclick="WIZ.paso--;pintarWizard()">← Atrás</button>`:`<button class="btn" onclick="cerrarModal('modal-clase')">Cancelar</button>`}
      ${WIZ.paso<4?`<button class="btn btn-primary" onclick="wizSiguiente()">Siguiente →</button>`
                  :`<button class="btn btn-green" onclick="publicarClase()">🚀 Publicar en el Aula Virtual</button>`}
    </div>`;
}
function wizSiguiente(){
  if(WIZ.paso===1){
    WIZ.titulo=document.getElementById("wz_titulo").value;
    WIZ.materia=document.getElementById("wz_materia").value;
    if(!WIZ.titulo.trim()){ toast("Ponle un título a tu clase ✍️",true); return; }
  }
  if(WIZ.paso===2){ WIZ.desc=document.getElementById("wz_desc").value;
    if(WIZ.modo==="manual" && !WIZ.desc.trim()){ toast("Escribe la descripción de tu clase ✍️",true); return; } }
  WIZ.paso++; pintarWizard();
}
/* Detecta el tipo por la EXTENSIÓN real del archivo (no por el nombre completo).
   Antes un PDF llamado "video_clase.pdf" se guardaba como video. */
const EXT_TIPO = {
  pdf:"pdf",
  doc:"documento", docx:"documento", odt:"documento", txt:"documento", rtf:"documento",
  xls:"hoja", xlsx:"hoja", csv:"hoja", ods:"hoja",
  ppt:"presentacion", pptx:"presentacion", odp:"presentacion",
  jpg:"imagen", jpeg:"imagen", png:"imagen", gif:"imagen", webp:"imagen", heic:"imagen",
  mp4:"video", mov:"video", avi:"video", mkv:"video", webm:"video",
  mp3:"audio", wav:"audio", m4a:"audio", ogg:"audio",
  zip:"archivo", rar:"archivo", "7z":"archivo",
};
function tipoDeArchivo(nombre){
  const ext=(nombre.split(".").pop()||"").toLowerCase();
  return EXT_TIPO[ext] || "archivo";
}
function tamanoLegible(bytes){
  if(!bytes && bytes!==0) return "";
  if(bytes < 1024) return bytes+" B";
  if(bytes < 1048576) return Math.round(bytes/1024)+" KB";
  return (bytes/1048576).toFixed(1)+" MB";
}
function manArchivos(inp){
  const nuevos=[];
  Array.from(inp.files).slice(0,10).forEach(f=>{
    if(WIZ.materiales.find(m=>m.nombre===f.name)){ return; }
    WIZ.materiales.push({tipo:tipoDeArchivo(f.name), nombre:f.name, tamano:tamanoLegible(f.size)});
    nuevos.push(f.name);
  });
  inp.value="";   // permite volver a escoger el mismo archivo si lo quitó
  pintarWizard();
  if(nuevos.length) toast(`📎 ${nuevos.length} archivo(s) adjuntado(s): ${nuevos.join(", ").slice(0,70)}`);
}
function iaArchivos(inp){
  WIZ.ia_archivos = Array.from(inp.files).slice(0,6).map(f=>f.name);
  // los archivos que subes con la IA también quedan como material de la clase,
  // con su tipo real — antes se perdían o se guardaban con el tipo equivocado
  Array.from(inp.files).slice(0,6).forEach(f=>{
    if(!WIZ.materiales.find(m=>m.nombre===f.name))
      WIZ.materiales.push({tipo:tipoDeArchivo(f.name), nombre:f.name, tamano:tamanoLegible(f.size)});
  });
  inp.value="";
  pintarWizard();
}
function agregarMaterial(){
  const nombre=document.getElementById("wz_mnombre").value.trim();
  if(!nombre){ toast("Escribe el nombre del material o el enlace",true); return; }
  const esEnlace = /^https?:\/\//i.test(nombre);
  const tipoSel = document.getElementById("wz_mtipo").value;
  const tipo = esEnlace ? "enlace" : (nombre.includes(".") ? tipoDeArchivo(nombre) : tipoSel);
  WIZ.materiales.push({tipo, nombre});
  document.getElementById("wz_mnombre").value="";
  pintarWizard();
}
async function iaPreparar(){
  WIZ.ia_tema=document.getElementById("ia_tema").value;
  WIZ.ia_horas=parseFloat(document.getElementById("ia_horas").value)||2;
  const grado=document.getElementById("ia_grado").value;
  if(!WIZ.ia_tema.trim()){ toast("Dime el tema y te preparo la clase 🙂",true); return; }
  document.getElementById("ia_plan").innerHTML='<div class="empty">🤖 Analizando tus materiales y armando el plan…</div>';
  try{
    const r=await post("/aula/ia_preparar",{tema:WIZ.ia_tema, materia:WIZ.materia, grado, horas:WIZ.ia_horas, archivos:WIZ.ia_archivos});
    WIZ.plan=r.plan;
    document.getElementById("ia_plan").innerHTML=pintarPlanIA(r.plan);
  }catch(e){ toast("Error del asistente",true); }
}
function pintarPlanIA(p){
  return `<div class="plan-ia">
    <b>${esc(p.titulo_sugerido)}</b>
    <h5>🎯 Objetivo</h5><div>${esc(p.objetivo_general)}</div>
    <h5>⏱️ Momentos de la clase (${esc(p.distribucion_horas)})</h5>
    <ul>${p.momentos.map(m=>`<li><b>${esc(m.nombre)}</b> — ${m.minutos} min. ${esc(m.detalle)}</li>`).join("")}</ul>
    <h5>📎 Uso de tus materiales</h5>
    <ul>${p.uso_de_materiales.map(u=>`<li>${esc(u)}</li>`).join("")}</ul>
    <h5>🧪 Evaluación sugerida</h5>
    <div>${esc(p.evaluacion_sugerida.tipo)} — ${p.evaluacion_sugerida.criterios.map(c=>esc(c)).join(" · ")}</div>
    <div class="small muted" style="margin-top:6px">${esc(p.nota)}</div>
    <div style="text-align:center;margin-top:10px"><button class="btn btn-primary btn-sm" onclick="usarPlanIA()">✅ Usar este plan en mi clase</button></div>
  </div>`;
}
function usarPlanIA(){
  const p=WIZ.plan; if(!p) return;
  if(!WIZ.titulo) WIZ.titulo=p.titulo_sugerido;
  WIZ.desc = `${p.objetivo_general}\n\nMOMENTOS DE LA CLASE:\n`+p.momentos.map(m=>`• ${m.nombre} (${m.minutos} min): ${m.detalle}`).join("\n")+`\n\nEVALUACIÓN: ${p.evaluacion_sugerida.tipo}.`;
  WIZ.ia_archivos.forEach(a=>{
    const low=a.toLowerCase();
    const tipo = low.includes(".mp4")||low.includes("video")?"video":low.includes(".jpg")||low.includes(".png")?"imagen":"pdf";
    if(!WIZ.materiales.find(m=>m.nombre===a)) WIZ.materiales.push({tipo, nombre:a});
  });
  WIZ.generado_ia=true;
  toast("🤖 Plan aplicado: descripción y materiales listos.");
  pintarWizard();
}
async function publicarClase(){
  const body={ salon_id:WIZ.salon_id, padre_id:WIZ.padre_id||null, titulo:WIZ.titulo, descripcion:WIZ.desc, tipo:WIZ.tipo,
    materia:WIZ.materia, periodo_numero:WIZ.periodo, fecha_limite:WIZ.fecha||null,
    tiempo_limite_min:WIZ.tiempo, reglas:WIZ.reglas, permite_recuperacion:WIZ.recup,
    materiales:WIZ.materiales, generado_ia:WIZ.generado_ia };
  try{ const r=await post("/aula/actividades/guardar",body);
    if(!r.ok){toast(r.msg,true);return;}
    cerrarModal("modal-clase"); toast(r.msg);
    const eraPadre=!WIZ.padre_id && ["clase","curso"].includes(WIZ.tipo);
    const nuevoId=r.id;
    await VISTAS.aula();
    if(eraPadre && nuevoId && confirm("✅ ¡Publicada! ¿Quieres agregar de una vez un TALLER o EVALUACIÓN asociado a esta clase?")){
      abrirWizardSub(nuevoId);
      abrirModal("modal-clase");
    }
  }catch(e){ toast("Error al publicar",true); }
}

/* ═══════════ VISTA: CALENDARIO DEL DOCENTE ═══════════ */
VISTAS.calendario = async function(filtro){
  loading();
  try{
    const f=filtro||"todos";
    const [d, rec] = await Promise.all([
      api(`/aula/calendario?personal_id=${ST.perfil.personal_id}&dias=14`),
      api(`/aula/recordatorios?personal_id=${ST.perfil.personal_id}`),
    ]);
    let evs=d.eventos;
    if(f==="pend") evs=evs.filter(e=>!e.done);
    if(f==="hechos") evs=evs.filter(e=>e.done);
    const porFecha={};
    evs.forEach(ev=>{ (porFecha[ev.fecha]=porFecha[ev.fecha]||[]).push(ev); });
    const hoy=hoyISO();
    const fechas=Object.keys(porFecha).sort();
    main(head("Mi calendario","Clases (según tu horario), obligaciones, pendientes y cierres del aula — próximos 14 días",
      `<button class="btn btn-primary" onclick="abrirModalEvento()">➕ Agregar evento</button>`)+`
      ${rec.length?`<div class="digest"><div style="font-size:1.8rem">⏰</div><div style="flex:1"><b>Próximos vencimientos (${rec.length}):</b>
        ${rec.slice(0,4).map(r=>`<div class="small">• <b>${r.cuando}</b>${r.hora?" "+esc(r.hora):""} — ${esc(r.titulo)}</div>`).join("")}
        <div class="small muted" style="margin-top:4px">🔔 También te llegan como notificación del navegador al entrar (si diste permiso) y un día antes.</div></div></div>`:""}
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:12px">
        ${[["todos","Todos"],["pend","☑️ Pendientes"],["hechos","✅ Hechos"]].map(([k,l])=>
          `<button class="chip-filtro ${f===k?'active':''}" onclick="VISTAS.calendario('${k}')">${l}</button>`).join("")}
        <span style="margin-left:auto"></span>
        <span class="badge b-teal">🧑‍🏫 Clase</span><span class="badge b-purple">📌 Obligación</span>
        <span class="badge b-orange">☑️ Pendiente</span><span class="badge b-red">🧪 Evaluación/cierre</span>
      </div>
      ${fechas.map(fch=>`
        <div class="cal-day">
          <div class="cal-fecha ${fch===hoy?'hoy':''}"><span>${fch===hoy?'⭐ HOY — ':''}${fechaBonita(fch)}</span><span class="small muted">${porFecha[fch].length} eventos</span></div>
          ${porFecha[fch].map(ev=>`
            <div class="cal-ev t-${ev.tipo} ${ev.done?'donee':''}">
              <span class="hora">${ev.hora?esc(ev.hora):"—"}</span>
              <span class="titulo" style="flex:1">${esc(ev.titulo)}</span>
              ${ev.fuente==="agenda"&&ev.id?`<label class="small muted" style="display:flex;align-items:center;gap:5px;cursor:pointer"><input type="checkbox" ${ev.done?"checked":""} onchange="marcarEvento(${ev.id},this.checked)">${ev.done?"hecho":"marcar hecho"}</label>`:`<span class="small muted">${ev.fuente==="horario"?"horario":"aula"}</span>`}
            </div>`).join("")}
        </div>`).join("")||'<div class="empty">Sin eventos con este filtro.</div>'}`);
  }catch(e){ main(`<div class="empty">Error</div>`); }
};
function abrirModalEvento(){
  document.getElementById("ev_titulo").value="";
  document.getElementById("ev_fecha").value=hoyISO();
  document.getElementById("ev_hora").value="";
  document.getElementById("ev_tipo").value="obligacion";
  document.getElementById("ev_detalle").value="";
  abrirModal("modal-evento");
}
async function guardarEvento(){
  const body={personal_id:ST.perfil.personal_id, fecha:document.getElementById("ev_fecha").value,
    hora:document.getElementById("ev_hora").value||null, titulo:document.getElementById("ev_titulo").value,
    tipo:document.getElementById("ev_tipo").value, detalle:document.getElementById("ev_detalle").value};
  if(!body.titulo.trim()){toast("El título es obligatorio",true);return;}
  try{ const r=await post("/aula/calendario/guardar",body);
    if(!r.ok){toast(r.msg,true);return;}
    cerrarModal("modal-evento"); toast(r.msg); VISTAS.calendario();
  }catch(e){ toast("Error",true); }
}
async function marcarEvento(id,done){
  try{ const r=await post("/aula/calendario/done",{id,done}); toast(r.msg,!r.ok);
    if(r.ok) VISTAS.calendario();
  }catch(e){ toast("Error",true); }
}

/* ═══════════ VISTA: NOTAS (editable por materia con candado) ═══════════ */
VISTAS.notas = async function(tab){
  if(tab==="riesgo"){ return vistaNotasRiesgo(); }
  loading();
  try{
    const salones = await api(`/academico/salones?institucion_id=${ST.institucion_id}`);
    if(!ST.salon_id && salones.length) ST.salon_id=salones[0].id;
    if(!salones.find(s=>s.id===ST.salon_id) && salones.length) ST.salon_id=salones[0].id;
    if(!window._materiaSel) window._materiaSel="Matemáticas";
    const d = await api(`/academico/notas?salon_id=${ST.salon_id}&materia=${encodeURIComponent(window._materiaSel)}`);
    const puedeEditar = ["docente","coordinador","rector"].includes(ST.perfil.rol);
    const selSalon=`<select onchange="ST.salon_id=parseInt(this.value);VISTAS.notas()">
      ${salones.map(s=>`<option value="${s.id}" ${s.id===ST.salon_id?"selected":""}>Salón ${esc(s.nombre)}</option>`).join("")}</select>`;
    const selMateria=`<select onchange="window._materiaSel=this.value;VISTAS.notas()">
      ${d.materias.map(m=>`<option ${m===window._materiaSel?"selected":""}>${m}</option>`).join("")}</select>`;
    const cols = d.periodos.map(p=>`<th style="text-align:center" title="Peso ${p.peso}%">P${p.numero} ${p.cerrado?'<span class="lock">🔒</span>':'<span title="abierto">🔓</span>'}</th>`).join("");
    let rows = d.filas.map(f=>{
      const celdas = d.periodos.map(p=>{
        const v=f.periodos[p.numero];
        if(p.cerrado || !puedeEditar){
          return `<td style="text-align:center">${v==null?'<span class="muted">—</span>':(v<3?`<b style="color:var(--red)">${v.toFixed(1)}</b>`:v.toFixed(1))}${p.cerrado?'':''}</td>`;
        }
        return `<td style="text-align:center"><input class="nota-in" type="number" min="0" max="5" step="0.1"
          value="${v!=null?v.toFixed(1):""}" placeholder="—"
          onchange="guardarNotaCelda(${f.estudiante_id},${p.numero},this)"></td>`;
      }).join("");
      const def=f.definitiva;
      return `<tr>
        <td><div class="flex-cell"><div class="avatar-sm">${ini(f.nombre)}</div>${esc(f.nombre)}</div></td>
        ${celdas}
        <td style="text-align:center">${def==null?'—':`<b style="color:${def<3?'var(--red)':'var(--green)'}">${def.toFixed(1)}</b>`}</td>
        <td>${f.estado==="En riesgo"?'<span class="badge b-red">En riesgo</span>':f.estado==="Aprobando"?'<span class="badge b-green">Aprobando</span>':'<span class="badge b-gray">Sin notas</span>'}</td>
      </tr>`;
    }).join("");
    main(head("Notas por período — "+esc(window._materiaSel), "Edita las celdas de los períodos ABIERTOS 🔓 · los cerrados 🔒 quedan sellados (los abre rectoría)")+`
      <div class="subtabs">
        <button class="subtab active" onclick="VISTAS.notas()">📗 Planilla de notas</button>
        <button class="subtab" onclick="VISTAS.notas('riesgo')">🚨 Riesgo académico y avisos</button>
      </div>
      <div class="card"><div class="card-body" style="display:flex;gap:14px;align-items:flex-end;flex-wrap:wrap">
        <div class="form-inline"><label>Salón</label>${selSalon}</div>
        <div class="form-inline"><label>Materia</label>${selMateria}</div>
        ${ST.perfil.rol==="rector"?`<div style="margin-left:auto;display:flex;gap:6px">${d.periodos.map(p=>
          `<button class="btn btn-sm ${p.cerrado?'':'btn-primary'}" onclick="togglePeriodo(${p.numero},${p.cerrado})">${p.cerrado?'🔓 Abrir P'+p.numero:'🔒 Cerrar P'+p.numero}</button>`).join("")}</div>`:""}
      </div></div>
      <div class="card"><div class="tbl-scroll"><table>
        <thead><tr><th>Estudiante</th>${cols}<th style="text-align:center">Definitiva</th><th>Estado</th></tr></thead>
        <tbody>${rows||'<tr><td colspan="8" class="empty">Sin estudiantes</td></tr>'}</tbody>
      </table></div></div>`);
  }catch(e){ main(`<div class="empty">Error cargando notas</div>`); }
};
async function guardarNotaCelda(estId, per, inp){
  const nota=parseFloat(inp.value);
  if(isNaN(nota)){ return; }
  try{
    const r=await post("/academico/notas/guardar",{estudiante_id:estId,periodo_numero:per,materia:window._materiaSel,nota});
    if(!r.ok){ toast(r.msg,true); inp.value=""; return; }
    inp.style.background="#ECFDF5";
    setTimeout(()=>inp.style.background="",800);
    toast(r.msg);
  }catch(e){ toast("Error al guardar",true); }
}
async function togglePeriodo(num, cerradoActual){
  try{ const r=await post("/academico/periodos/cerrar",{numero:num,cerrado:!cerradoActual});
    toast(r.msg,!r.ok); if(r.ok) VISTAS.notas();
  }catch(e){ toast("Error",true); }
}

/* ═══════════ VISTA: RIESGO (SRD) ═══════════ */
VISTAS.riesgo = async function(){
  loading();
  try{
    const scope = ST.perfil.rol==="docente" && ST.salon_id ? `salon_id=${ST.salon_id}` : `institucion_id=${ST.institucion_id}`;
    const [tab, rank] = await Promise.all([
      api(`/srd/tablero?institucion_id=${ST.institucion_id}`),
      api(`/srd/ranking?${scope}`),
    ]);
    const btn=`<button class="btn btn-sm" onclick="recalcRiesgo()">🔄 Recalcular</button>`;
    let rows = rank.map(r=>`
      <tr onclick='verFicha(${r.estudiante_id})' style="cursor:pointer">
        <td><div class="pill p-${nivelClase(r.nivel)}">${r.score}</div></td>
        <td><div class="flex-cell"><div class="avatar-sm">${ini(r.nombre)}</div><div><b>${esc(r.nombre)}</b><div class="small muted">Salón ${esc(r.salon)}</div></div></div></td>
        <td><span class="badge ${nivelBadge(r.nivel)}">${esc(r.nivel)}</span></td>
        <td style="text-align:center">${r.faltas_acumuladas}</td>
        <td style="text-align:center">${r.pct_asistencia}%</td>
        <td style="text-align:center">${r.promedio.toFixed(1)}</td>
        <td>${r.notificado_padre?'<span class="badge b-green">✓ Padre</span>':'<span class="badge b-gray">Sin avisar</span>'}
            ${r.notificado_rectoria?'<span class="badge b-blue">✓ Rectoría</span>':''}</td>
        <td><button class="btn btn-xs" onclick="event.stopPropagation();verFicha(${r.estudiante_id})">Ficha 360° ▸</button></td>
      </tr>`).join("");
    main(head("Score de Riesgo de Deserción", "Modelo LightGBM + indicadores · clic en un estudiante para su FICHA 360°", btn)+`
      <div class="kpis">
        <div class="kpi"><div class="kpi-ico">👨‍🎓</div><div class="kpi-val">${tab.total}</div><div class="kpi-lbl">Estudiantes evaluados</div></div>
        <div class="kpi red"><div class="kpi-ico">🔴</div><div class="kpi-val">${tab.criticos}</div><div class="kpi-lbl">Riesgo crítico</div></div>
        <div class="kpi orange"><div class="kpi-ico">🟠</div><div class="kpi-val">${tab.moderados}</div><div class="kpi-lbl">Riesgo moderado</div></div>
        <div class="kpi gold"><div class="kpi-ico">🟡</div><div class="kpi-val">${tab.leves}</div><div class="kpi-lbl">Riesgo leve</div></div>
      </div>
      <div class="card"><div class="card-head"><h3>Estudiantes priorizados por riesgo</h3><span class="small muted">${rank.length} mostrados</span></div>
      <div class="tbl-scroll"><table>
        <thead><tr><th>Score</th><th>Estudiante</th><th>Nivel</th><th>Faltas</th><th>Asist.</th><th>Prom.</th><th>Notificación</th><th></th></tr></thead>
        <tbody>${rows||'<tr><td colspan="8" class="empty">Sin datos de riesgo</td></tr>'}</tbody>
      </table></div></div>`);
  }catch(e){ main(`<div class="empty">Error cargando riesgo</div>`); }
};
async function recalcRiesgo(){
  try{ toast("Recalculando…"); const r=await post("/srd/recalcular",{}); toast(r.msg); if(ST.vista==="riesgo")VISTAS.riesgo(); }catch(e){ toast("Error",true); }
}

/* ── FICHA 360° del estudiante ── */
async function verFicha(id, tab){
  try{
    const f = await api(`/srd/ficha?estudiante_id=${id}`);
    window._ficha = f;
    document.getElementById("modal-srd-title").textContent = "Ficha 360° — "+f.nombre;
    fichaTab(tab||"riesgo");
    abrirModal("modal-srd");
  }catch(e){ toast("Error al cargar la ficha",true); }
}
function fichaTab(t){
  const f = window._ficha;
  const cls=nivelClase(f.srd.nivel);
  const antig = f.es_nuevo ? '<span class="badge b-gold">🌱 Estudiante NUEVO este año</span>'
    : (f.antiguedad_anios!=null?`<span class="badge b-teal">${f.antiguedad_anios} años en la institución</span>`:'');
  const cab = `
    <div class="srd-dhead srd-bg-${cls}">
      <div>
        <div class="srd-name">${esc(f.nombre)}</div>
        <div style="opacity:.9;font-size:.82rem">Salón ${esc(f.salon)} · Grado ${esc(f.grado)} · ${esc(f.institucion)}</div>
        <div style="margin-top:6px">${antig} ${f.alertas_abiertas?`<span class="badge b-red">🔔 ${f.alertas_abiertas} alerta(s) abierta(s)</span>`:""}</div>
      </div>
      <div><div class="srd-scoreval">${f.srd.score??"—"}</div><div style="text-align:center;font-size:.72rem;opacity:.9">${esc(f.srd.nivel)}</div></div>
    </div>
    <div class="info-grid">
      <div class="info-it"><span class="k">Acudiente</span><b>${esc(f.acudiente||"—")}</b> <span class="small muted">(${esc(f.parentesco||"acudiente")})</span></div>
      <div class="info-it"><span class="k">Teléfono</span><b>${esc(f.telefono||"—")}</b></div>
      <div class="info-it"><span class="k">Dirección</span><b>${esc(f.direccion||"—")}</b><div class="small muted">${esc(f.barrio_vereda||"")} · zona ${esc(f.zona)}</div></div>
      <div class="info-it"><span class="k">SISBEN · Ingreso</span><b>${esc(f.nivel_sisben)}</b> · ${f.fecha_ingreso||"—"}</div>
    </div>`;
  const tabs = `<div class="subtabs">
    ${[["riesgo","🎯 Riesgo"],["observador","🧾 Observador"],["pend","☑️ Pendientes"],["asis","📅 Asistencia"],["notas","📗 Notas"],["wa","📱 WhatsApp"],["log","📜 Auditoría"]].map(([k,l])=>
      `<button class="subtab ${t===k?'active':''}" onclick="fichaTab('${k}')">${l}</button>`).join("")}</div>`;
  let body="";
  if(t==="riesgo"){
    body=`
      <div class="srd-metrics">
        <div class="srd-metric"><span class="srd-mlbl">Faltas acum.</span><span class="srd-mval">${f.srd.faltas_acumuladas}</span></div>
        <div class="srd-metric"><span class="srd-mlbl">Faltas 4 sem</span><span class="srd-mval">${f.srd.faltas_recientes}</span></div>
        <div class="srd-metric"><span class="srd-mlbl">Asistencia</span><span class="srd-mval">${f.srd.pct_asistencia??"—"}%</span></div>
        <div class="srd-metric"><span class="srd-mlbl">Promedio</span><span class="srd-mval">${f.srd.promedio!=null?f.srd.promedio.toFixed(1):"—"}</span></div>
        <div class="srd-metric"><span class="srd-mlbl">Tendencia</span><span class="srd-mval" style="color:${f.srd.tendencia<0?'var(--red)':'var(--green)'}">${f.srd.tendencia>0?'+':''}${(f.srd.tendencia||0).toFixed(1)}</span></div>
      </div>
      <div class="srd-factors"><b>🔍 Factores que explican el riesgo</b><ul>${f.srd.factores.map(x=>`<li>${esc(x)}</li>`).join("")}</ul></div>
      <div class="srd-notif">
        <div class="srd-nx ${f.srd.notificado_padre?'done':''}">
          ${f.srd.notificado_padre?`✓ Acudiente notificado 📱<br><span class="small">${esc(f.srd.fecha_notif_padre||"")}</span>`:`<button class="btn btn-sm btn-primary" onclick="notificar(${f.id},'padre')">📱 Notificar al acudiente (WhatsApp)</button>`}
        </div>
        <div class="srd-nx ${f.srd.notificado_rectoria?'done':''}">
          ${f.srd.notificado_rectoria?`✓ Reportado a rectoría<br><span class="small">${esc(f.srd.fecha_notif_rectoria||"")}</span>`:`<button class="btn btn-sm" onclick="notificar(${f.id},'rectoria')">🏛️ Reportar a rectoría</button>`}
        </div>
      </div>
      <div class="srd-interv">
        <label style="font-size:.79rem;font-weight:700;color:#5B21B6">Estado de la intervención</label>
        <div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap">
          <select id="int-estado" style="padding:7px 10px;border:1px solid var(--border);border-radius:8px">
            <option value="pendiente" ${f.srd.intervencion_estado==="pendiente"?"selected":""}>Pendiente</option>
            <option value="en_proceso" ${f.srd.intervencion_estado==="en_proceso"?"selected":""}>En proceso</option>
            <option value="resuelto" ${f.srd.intervencion_estado==="resuelto"?"selected":""}>Resuelto</option>
          </select>
          <input id="int-nota" placeholder="Nota de seguimiento…" value="${esc(f.srd.intervencion_nota)}" style="flex:1;min-width:180px;padding:7px 10px;border:1px solid var(--border);border-radius:8px">
          <button class="btn btn-sm btn-green" onclick="guardarInterv(${f.id})">Guardar</button>
        </div>
      </div>`;
  }
  if(t==="observador"){
    const TIPO_OBS={comportamiento:["🚨 Comportamiento","b-red"],academico:["📚 Académico","b-orange"],felicitacion:["🌟 Felicitación","b-green"],compromiso:["🤝 Compromiso","b-purple"]};
    body=`
      ${f.observador.map(o=>{
        const [lbl,bg]=TIPO_OBS[o.tipo]||["📄 "+o.tipo,"b-gray"];
        return `<div class="obs-item obs-${o.tipo}">
          <div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap">
            <span class="badge ${bg}">${lbl}</span><span class="small muted">${esc(o.fecha)} · ${esc(o.registrado_por||"")}</span></div>
          <div style="margin-top:5px">${esc(o.descripcion)}</div>
          <div style="margin-top:6px">${o.firmado
            ?`<span class="badge b-green">✍️ Firmado por acudiente · ${esc(o.firma_metodo||"")} · ${esc(o.fecha_firma||"")}</span>`
            :`<button class="btn btn-xs btn-gold" onclick="firmarObs(${o.id})">✍️ Solicitar firma del acudiente (OTP)</button>`}</div>
        </div>`;}).join("")||'<div class="empty">Sin anotaciones en el observador.</div>'}
      <div class="card"><div class="card-body">
        <b class="small">➕ Nueva anotación</b>
        <div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap">
          <select id="obs_tipo" style="padding:8px;border:1px solid var(--border);border-radius:8px">
            <option value="academico">📚 Académico</option><option value="comportamiento">🚨 Comportamiento</option>
            <option value="compromiso">🤝 Compromiso</option><option value="felicitacion">🌟 Felicitación</option></select>
          <input id="obs_desc" placeholder="Describe la situación…" style="flex:1;min-width:200px;padding:8px;border:1px solid var(--border);border-radius:8px">
          <button class="btn btn-sm btn-primary" onclick="guardarObs(${f.id})">Registrar</button>
        </div></div></div>`;
  }
  if(t==="pend"){
    body=`
      ${f.pendientes.map(p=>`
        <div class="check-row"><input type="checkbox" ${p.done?"checked":""} onchange="donePend(${p.id},this.checked,${f.id})">
        <div style="flex:1"><span style="${p.done?'text-decoration:line-through;color:var(--muted)':''}">${esc(p.texto)}</span>
        <div class="small muted">${esc(p.fecha)} · ${esc(p.creado_por||"")}</div></div></div>`).join("")||'<div class="empty">Sin pendientes en la bitácora.</div>'}
      <div style="display:flex;gap:8px;margin-top:10px">
        <input id="pend_txt" placeholder="Nuevo pendiente (ej: citar acudiente el lunes)…" style="flex:1;padding:9px;border:1px solid var(--border);border-radius:8px">
        <button class="btn btn-primary btn-sm" onclick="guardarPend(${f.id})">➕ Agregar</button>
      </div>`;
  }
  if(t==="asis"){
    const L={present:"P",late:"T",excused:"E",absent:"A"};
    body=`<b class="small">Últimos ${f.asistencia_reciente.length} registros</b>
      <div class="asis-dots" style="margin-top:10px">
        ${f.asistencia_reciente.map(a=>`<div class="asis-dot d-${a.estado}" title="${a.fecha}: ${a.estado}">${L[a.estado]||"?"}</div>`).join("")}
      </div>
      <div class="small muted" style="margin-top:10px">Verde P = presente · Naranja T = tarde · Azul E = excusa · Rojo A = ausente. Cada A generó alerta al coordinador y WhatsApp al acudiente.</div>`;
  }
  if(t==="notas"){
    body=`<div class="tbl-scroll"><table><thead><tr><th>Período</th><th style="text-align:center">Promedio</th><th>Estado</th></tr></thead><tbody>
      ${f.notas.map(n=>`<tr><td>${esc(n.nombre)} ${n.cerrado?'🔒':'🔓'}</td>
        <td style="text-align:center"><b style="color:${n.promedio<3?'var(--red)':'var(--green)'}">${n.promedio.toFixed(1)}</b></td>
        <td>${n.promedio<3?'<span class="badge b-red">Bajo</span>':'<span class="badge b-green">OK</span>'}</td></tr>`).join("")||'<tr><td colspan="3" class="empty">Sin notas</td></tr>'}
    </tbody></table></div>`;
  }
  if(t==="wa"){
    body = pintarChatWA(f.whatsapp, f.acudiente, f.parentesco, f.telefono, f.id);
  }
  if(t==="log"){
    body=`${f.bitacora.map(l=>`<div class="srd-log-row"><div class="srd-log-dot"></div><div><b class="small">${esc(l.accion)}</b>${l.detalle?` — <span class="small">${esc(l.detalle)}</span>`:""}<div class="small muted">${esc(l.fecha)} · ${esc(l.actor)}</div></div></div>`).join("")||'<div class="small muted">Sin acciones registradas todavía.</div>'}`;
  }
  document.getElementById("modal-srd-body").innerHTML = cab + tabs + body;
}
function pintarChatWA(msgs, acudiente, parentesco, telefono, estId){
  return `<div class="wa-chat">
    <div class="wa-head"><div class="avatar-sm">${ini(acudiente||"AC")}</div>
      <div><b style="font-size:.9rem">${esc(acudiente||"Acudiente")}</b><div class="small" style="opacity:.85">${esc(parentesco||"")} · ${esc(telefono||"")}</div></div></div>
    <div class="wa-body">
      <div class="wa-note">🔒 Pasarela simulada — en producción: Meta Cloud API / Twilio con plantillas aprobadas</div>
      ${msgs.slice().reverse().map(m=>`<div class="wa-bubble">${esc(m.contenido)}<div class="wa-meta">${esc(m.fecha)} · ${esc(m.estado)} ✓✓</div></div>`).join("")||'<div class="small muted" style="text-align:center">Aún no hay mensajes.</div>'}
    </div>
    <div class="wa-send">
      <input id="wa_txt" placeholder="Escribe un mensaje al acudiente…">
      <button class="btn btn-green btn-sm" onclick="enviarWA(${estId})">Enviar ➤</button>
    </div>
  </div>`;
}
async function enviarWA(estId){
  const txt=document.getElementById("wa_txt").value;
  if(!txt.trim()){ toast("Escribe el mensaje",true); return; }
  try{ const r=await post("/alertas/whatsapp/enviar",{estudiante_id:estId,contenido:txt});
    toast(r.msg,!r.ok); if(r.ok) verFicha(estId,"wa");
  }catch(e){ toast("Error",true); }
}
async function notificar(id,tipo){
  try{ const r=await post("/srd/notificar",{estudiante_id:id,tipo}); toast(r.msg); verFicha(id,"riesgo"); }
  catch(e){ toast("Error",true); }
}
async function guardarInterv(id){
  const estado=document.getElementById("int-estado").value, nota=document.getElementById("int-nota").value;
  try{ const r=await post("/srd/intervencion",{estudiante_id:id,estado,nota}); toast(r.msg); verFicha(id,"riesgo"); }
  catch(e){ toast("Error",true); }
}
async function guardarObs(id){
  const tipo=document.getElementById("obs_tipo").value, descripcion=document.getElementById("obs_desc").value;
  if(!descripcion.trim()){toast("Describe la situación",true);return;}
  try{ const r=await post("/srd/observador/guardar",{estudiante_id:id,tipo,descripcion,registrado_por:ST.perfil.titulo});
    toast(r.msg,!r.ok); if(r.ok) verFicha(id,"observador");
  }catch(e){ toast("Error",true); }
}
async function firmarObs(obsId){
  if(!confirm("Se enviará un código OTP al WhatsApp del acudiente para validar su identidad y registrar la firma. ¿Continuar? (simulado)")) return;
  try{ const r=await post("/srd/observador/firmar",{id:obsId}); toast(r.msg,!r.ok);
    if(r.ok) verFicha(window._ficha.id,"observador");
  }catch(e){ toast("Error",true); }
}
async function guardarPend(id){
  const texto=document.getElementById("pend_txt").value;
  if(!texto.trim()){toast("Escribe el pendiente",true);return;}
  try{ const r=await post("/srd/pendientes/guardar",{estudiante_id:id,texto,creado_por:ST.perfil.titulo});
    toast(r.msg,!r.ok); if(r.ok) verFicha(id,"pend");
  }catch(e){ toast("Error",true); }
}
async function donePend(pid,done,estId){
  try{ const r=await post("/srd/pendientes/done",{id:pid,done}); toast(r.msg,!r.ok); }
  catch(e){ toast("Error",true); }
}

/* ═══════════ VISTA: RESUMEN (coordinador/rector) ═══════════ */
VISTAS.resumen = async function(){
  loading();
  try{
    const [tab, salones, personal, cont] = await Promise.all([
      api(`/srd/tablero?institucion_id=${ST.institucion_id}`),
      api(`/academico/salones?institucion_id=${ST.institucion_id}`),
      api(`/academico/personal?institucion_id=${ST.institucion_id}`),
      api(`/alertas/contador?institucion_id=${ST.institucion_id}`),
    ]);
    const nDoc = personal.filter(p=>p.rol==="docente").length;
    const totEst = salones.reduce((a,s)=>a+s.n_estudiantes,0);
    let mapa = tab.mapa.map(m=>{
      const cls = m.pct_riesgo>=20?"b-red":m.pct_riesgo>=10?"b-orange":m.pct_riesgo>0?"b-yellow":"b-green";
      return `<tr><td><b>Salón ${esc(m.salon)}</b> <span class="muted small">(${esc(m.grado)})</span></td>
        <td style="text-align:center">${m.total}</td>
        <td><div class="flex-cell"><div class="prog" style="flex:1"><div class="prog-fill" style="width:${m.pct_riesgo}%;background:${m.pct_riesgo>=20?'var(--red)':m.pct_riesgo>=10?'var(--orange)':'var(--gold)'}"></div></div><span class="badge ${cls}">${m.pct_riesgo}%</span></div></td></tr>`;
    }).join("");
    const esCoord = ST.perfil.rol==="coordinador";
    main(head("Resumen de la institución", ST.perfil.detalle)+`
      <div class="kpis">
        <div class="kpi green"><div class="kpi-ico">👨‍🎓</div><div class="kpi-val">${totEst}</div><div class="kpi-lbl">Estudiantes</div></div>
        <div class="kpi"><div class="kpi-ico">🏫</div><div class="kpi-val">${salones.length}</div><div class="kpi-lbl">Salones</div></div>
        <div class="kpi purple"><div class="kpi-ico">👥</div><div class="kpi-val">${nDoc}</div><div class="kpi-lbl">Docentes</div></div>
        <div class="kpi red"><div class="kpi-ico">🔔</div><div class="kpi-val">${cont.abiertas}</div><div class="kpi-lbl">Alertas abiertas</div></div>
      </div>
      <div class="digest"><div style="font-size:1.8rem">🔔</div>
        <div style="flex:1"><b>${cont.abiertas} alertas abiertas</b> — ausencias del día y casos de riesgo esperando gestión.
        <div class="small muted">Cada ausencia registrada por un docente llega aquí automáticamente y dispara el WhatsApp al acudiente.</div></div>
        ${esCoord?`<button class="btn btn-primary" onclick="irVista('alertas')">Gestionar →</button>`:`<button class="btn btn-primary" onclick="irVista('riesgo')">Ver riesgo →</button>`}
      </div>
      <div class="card"><div class="card-head"><h3>Mapa de riesgo por salón</h3><span class="small muted">🔴 ${tab.criticos} críticos · 🟠 ${tab.moderados} moderados</span></div>
      <div class="tbl-scroll"><table><thead><tr><th>Salón</th><th style="text-align:center">Estudiantes</th><th>% en riesgo</th></tr></thead>
      <tbody>${mapa||'<tr><td colspan="3" class="empty">Sin datos</td></tr>'}</tbody></table></div></div>`);
  }catch(e){ main(`<div class="empty">Error cargando resumen</div>`); }
};

/* ═══════════ VISTA: ALERTAS (coordinador) ═══════════ */
/* PUNTO 13: el centro de alertas se mantiene al día solo — refresca cada 25s
   mientras estás en la vista, y cada acción del sistema que genera alertas
   (asistencia, riesgo) actualiza el contador al instante. */
let _alertasTimer=null;
function iniciarAutoAlertas(){
  if(_alertasTimer) clearInterval(_alertasTimer);
  _alertasTimer=setInterval(()=>{
    if(ST.vista!=="alertas"){ clearInterval(_alertasTimer); _alertasTimer=null; return; }
    refrescarAlertas(true);
  }, 25000);
}
async function refrescarAlertas(silencioso){
  if(ST.vista!=="alertas") return;
  const f=ST._alertaFiltro||"abierta";
  await VISTAS.alertas(f);
  if(!silencioso) toast("🔄 Alertas actualizadas.");
}

VISTAS.alertas = async function(filtro){
  loading();
  try{
    const f = filtro||"abierta";
    ST._alertaFiltro = f;
    iniciarVivo('alertas');
    const alertas = await api(`/alertas/?institucion_id=${ST.institucion_id}${f!=="todas"?"&estado="+f:""}`);
    const hoyN = alertas.filter(a=>a.es_hoy&&a.estado==="abierta").length;
    actualizarBadgeAlertas();
    const TIPO={ausencia:["🚨 Ausencia","b-red"],riesgo:["🎯 Riesgo","b-orange"],comportamiento:["🧾 Comportamiento","b-purple"]};
    let rows = alertas.map(a=>{
      const [lbl,bg]=TIPO[a.tipo]||["📄","b-gray"];
      return `<tr>
        <td class="small">${esc(a.fecha)}${a.es_hoy?' <span class="badge b-gold">HOY</span>':''}</td>
        <td><span class="badge ${bg}">${lbl}</span></td>
        <td><b>${esc(a.estudiante)}</b> <span class="small muted">G${esc(a.grado)}</span><div class="small muted">${esc(a.detalle||"")}</div>
          ${a.resolucion?`<div class="small" style="color:var(--green);margin-top:3px">✅ <b>Resolución:</b> ${esc(a.resolucion)} <span class="muted">(${esc(a.fecha_cierre||"")})</span></div>`:""}</td>
        <td>${a.estado==="abierta"?'<span class="badge b-red">Abierta</span>':a.estado==="completada"?'<span class="badge b-green">Completada</span>':'<span class="badge b-gray">Archivada</span>'}</td>
        <td style="white-space:nowrap">
          <button class="btn btn-xs" onclick="verFicha(${a.estudiante_id})">👤 Ficha</button>
          ${a.estado==="abierta"?`<button class="btn btn-xs btn-green" onclick="abrirResol(${a.id})">✅ Completar</button>
          <button class="btn btn-xs" onclick="archivarCaso(${a.id})">🗄️</button>`:""}
        </td></tr>`;
    }).join("");
    main(head("Centro de alertas", "Ausencias del día en tiempo real + casos de riesgo · completa cada caso con su resolución para el historial",
      `<button class="btn" onclick="refrescarAlertas(false)">🔄 Actualizar ahora</button>`)+`
      <div id="vivo-bar" class="vivo-bar"></div>
      <div class="small muted" style="margin-bottom:10px">🔄 Esta vista se actualiza sola: cuando un docente marca una ausencia o el modelo detecta un caso, aparece aquí sin recargar la página.</div>
      ${hoyN?`<div class="digest"><div style="font-size:1.8rem">📅</div><div><b>${hoyN} ausencia(s) reportadas HOY</b> por los docentes al tomar asistencia — el acudiente ya recibió el WhatsApp automático (simulado). Verifica el motivo y cierra el caso.</div></div>`:""}
      <div style="margin-bottom:14px">
        ${[["abierta","🔔 Abiertas"],["completada","✅ Completadas"],["archivada","🗄️ Archivadas"],["todas","Todas"]].map(([k,l])=>
          `<button class="chip-filtro ${f===k?'active':''}" onclick="VISTAS.alertas('${k}')">${l}</button>`).join("")}
      </div>
      <div class="card"><div class="tbl-scroll"><table>
        <thead><tr><th>Fecha</th><th>Tipo</th><th>Caso</th><th>Estado</th><th>Acciones</th></tr></thead>
        <tbody>${rows||'<tr><td colspan="5" class="empty">Nada por aquí 🎉</td></tr>'}</tbody>
      </table></div></div>`);
  }catch(e){ main(`<div class="empty">Error</div>`); }
};
function abrirResol(id){
  document.getElementById("res_id").value=id;
  document.getElementById("res_texto").value="";
  abrirModal("modal-resol");
}
async function completarCaso(){
  const id=parseInt(document.getElementById("res_id").value);
  const resolucion=document.getElementById("res_texto").value;
  try{ const r=await post("/alertas/estado",{id,estado:"completada",resolucion});
    if(!r.ok){toast(r.msg,true);return;}
    cerrarModal("modal-resol"); toast(r.msg); VISTAS.alertas("abierta");
  }catch(e){ toast("Error",true); }
}
async function archivarCaso(id){
  if(!confirm("¿Archivar este caso sin resolución? (quedará en el historial)")) return;
  try{ const r=await post("/alertas/estado",{id,estado:"archivada",resolucion:"Archivado por coordinación."});
    toast(r.msg,!r.ok); VISTAS.alertas("abierta");
  }catch(e){ toast("Error",true); }
}

/* ═══════════ VISTA: DOCENTES (coordinador) ═══════════ */
VISTAS.docentes = async function(tab){
  loading();
  try{
    const t=tab||"gestion";
    main(head("Gestión de docentes","Planta docente: crear, editar, controlar su asistencia y ver el reporte de ausentismo",
      `<button class="btn btn-primary" onclick="editarPersona(0,'docente')">➕ Agregar docente</button>`)+`
      <div class="subtabs">
        ${[["gestion","👥 Planta docente"],["asistencia","📋 Asistencia de hoy"],["reporte","📊 Reporte de ausentismo"]].map(([k,l])=>
          `<button class="subtab ${t===k?'active':''}" onclick="VISTAS.docentes('${k}')">${l}</button>`).join("")}</div>
      <div id="doc-cont"><div class="empty">Cargando…</div></div>`);
    if(t==="gestion") docentesGestion();
    if(t==="asistencia") docentesAsistencia();
    if(t==="reporte") docentesReporte();
  }catch(e){ main(`<div class="empty">Error</div>`); }
};
async function docentesGestion(){
  const personal = await api(`/academico/personal?institucion_id=${ST.institucion_id}&rol=docente`);
  window._personal = personal;
  document.getElementById("doc-cont").innerHTML = `
    <div class="card"><div class="tbl-scroll"><table>
      <thead><tr><th>Docente</th><th>Área</th><th style="text-align:center">Salones</th><th style="text-align:center">Asistencia 4 sem</th><th>Contacto</th><th></th></tr></thead>
      <tbody>${personal.map(p=>`<tr>
        <td><div class="flex-cell">${avatarCell(p.foto,p.nombre)}<div><b>${esc(p.nombre)}</b><div class="small muted">${esc(p.profesion||"")}</div></div></div></td>
        <td>${esc(p.area||"—")}</td>
        <td style="text-align:center">${p.n_salones}</td>
        <td style="text-align:center">${p.asistencia_pct!=null?`<span class="badge ${p.asistencia_pct<85?'b-red':p.asistencia_pct<93?'b-orange':'b-green'}">${p.asistencia_pct}%</span>`:'—'}</td>
        <td class="small">${esc(p.telefono||"—")}</td>
        <td style="white-space:nowrap">
          <button class="btn btn-xs" onclick="verHV(${p.id})">📄 HV</button>
          <button class="btn btn-xs" onclick="editarPersona(${p.id})">✎</button>
          <button class="btn btn-xs btn-danger" onclick="eliminarPersona(${p.id},'${esc(p.nombre)}')">🗑</button>
        </td></tr>`).join("")||'<tr><td colspan="6" class="empty">Sin docentes</td></tr>'}
      </tbody></table></div></div>`;
}
async function docentesAsistencia(){
  const hoy=hoyISO();
  const d = await api(`/asistencia/docentes/cargar?institucion_id=${ST.institucion_id}&fecha=${hoy}`);
  window._asisDoc = d.filas;
  document.getElementById("doc-cont").innerHTML = `
    <div class="fecha-hoy" style="display:inline-block;margin-bottom:12px">📅 ${fechaBonita(hoy)}</div>
    <div class="card"><div class="tbl-scroll"><table>
      <thead><tr><th>Docente</th><th style="width:190px">Estado</th><th>Observación</th></tr></thead>
      <tbody>${d.filas.map((f,i)=>`<tr>
        <td><div class="flex-cell">${avatarCell(f.foto,f.nombre)}<div><b>${esc(f.nombre)}</b><div class="small muted">${esc(f.area||"")}</div></div></div></td>
        <td><div class="att-seg" id="dseg-${i}">
          ${["present","late","excused","absent"].map(e=>{
            const L={present:"P",late:"T",excused:"E",absent:"A"}[e];
            const on=f.estado===e?`att-on att-${e}`:"";
            return `<button class="att-btn ${on}" onclick="setAsisDoc(${i},'${e}')">${L}</button>`;
          }).join("")}
        </div></td>
        <td><input class="att-obs" id="dobs-${i}" value="${esc(f.observacion)}" placeholder="—"></td>
      </tr>`).join("")}
      </tbody></table></div></div>
    <div style="text-align:right"><button class="btn btn-primary" onclick="guardarAsisDoc('${hoy}')">💾 Guardar asistencia docente</button></div>`;
}
function setAsisDoc(i,estado){
  window._asisDoc[i].estado=estado;
  const seg=document.getElementById("dseg-"+i);
  seg.querySelectorAll(".att-btn").forEach((b,j)=>{
    const e=["present","late","excused","absent"][j];
    b.className="att-btn"+(e===estado?` att-on att-${e}`:"");
  });
}
async function guardarAsisDoc(fecha){
  const filas=window._asisDoc.map((f,i)=>({personal_id:f.personal_id,estado:f.estado,observacion:document.getElementById("dobs-"+i).value}));
  try{ const r=await post("/asistencia/docentes/guardar",{institucion_id:ST.institucion_id,fecha,filas}); toast(r.msg,!r.ok); }
  catch(e){ toast("Error",true); }
}
async function docentesReporte(){
  const rep = await api(`/asistencia/docentes/reporte?institucion_id=${ST.institucion_id}`);
  document.getElementById("doc-cont").innerHTML = `
    <div class="card"><div class="card-head"><h3>Ausentismo docente (últimas 4-5 semanas)</h3><button class="btn btn-sm" onclick="window.print()">🖨️ Imprimir reporte</button></div>
    <div class="tbl-scroll"><table>
      <thead><tr><th>Docente</th><th style="text-align:center">Días</th><th style="text-align:center">Ausencias</th><th style="text-align:center">Tardanzas</th><th>% Asistencia</th><th>Riesgo</th></tr></thead>
      <tbody>${rep.map(d=>`<tr>
        <td><div class="flex-cell">${avatarCell(d.foto,d.nombre)}<div><b>${esc(d.nombre)}</b><div class="small muted">${esc(d.area||"")}</div></div></div></td>
        <td style="text-align:center">${d.dias}</td>
        <td style="text-align:center"><b style="color:${d.ausencias>2?'var(--red)':'inherit'}">${d.ausencias}</b></td>
        <td style="text-align:center">${d.tardanzas}</td>
        <td><div class="flex-cell"><div class="prog" style="flex:1"><div class="prog-fill" style="width:${d.pct||0}%;background:${d.riesgo==='ALTO'?'var(--red)':d.riesgo==='MEDIO'?'var(--orange)':'var(--green)'}"></div></div><b class="small">${d.pct!=null?d.pct+"%":"—"}</b></div></td>
        <td>${d.riesgo==="ALTO"?'<span class="badge b-red">ALTO</span>':d.riesgo==="MEDIO"?'<span class="badge b-orange">MEDIO</span>':'<span class="badge b-green">OK</span>'}</td>
      </tr>`).join("")}
      </tbody></table></div></div>
    <div class="audit-note">📌 El ausentismo docente alimenta el <b>riesgo institucional</b>: un docente que falta genera pérdida de clases para 30+ estudiantes. Rectoría ve este mismo reporte en "Personal".</div>`;
}

/* ── Persona (CRUD compartido) ── */
async function editarPersona(id, rolDefault){
  const p = (window._personal||[]).find(x=>x.id===id);
  document.getElementById("persona-title").textContent = id?"Editar persona":"Agregar persona al plantel";
  document.getElementById("per_id").value=id||"";
  document.getElementById("per_nombre").value=p?p.nombre:"";
  document.getElementById("per_rol").value=p?p.rol:(rolDefault||"docente");
  document.getElementById("per_area").value=p?(p.area||""):"";
  document.getElementById("per_doc").value=p?(p.documento||""):"";
  document.getElementById("per_tel").value=p?(p.telefono||""):"";
  document.getElementById("per_prof").value=p?(p.profesion||""):"";
  document.getElementById("per_exp").value=p?(p.experiencia_anios||0):0;
  document.getElementById("per_email").value=p?(p.email||""):"";
  abrirModal("modal-persona");
}
async function guardarPersona(){
  const body={ id:parseInt(document.getElementById("per_id").value)||0, institucion_id:ST.institucion_id,
    nombre:document.getElementById("per_nombre").value, rol:document.getElementById("per_rol").value,
    area:document.getElementById("per_area").value, documento:document.getElementById("per_doc").value,
    telefono:document.getElementById("per_tel").value, profesion:document.getElementById("per_prof").value,
    experiencia_anios:parseInt(document.getElementById("per_exp").value)||0,
    email:document.getElementById("per_email").value };
  try{ const r=await post("/academico/personal/guardar",body);
    if(!r.ok){toast(r.msg,true);return;}
    cerrarModal("modal-persona"); toast(r.msg);
    const esNuevo = !body.id;
    if(esNuevo && window._equipoPaneles){
      const paneles = window._equipoPaneles.split(",");
      window._equipoPaneles = null;
      await post("/academico/autorizaciones/guardar",{institucion_id:ST.institucion_id,personal_id:r.id,paneles});
      toast("🔐 Paneles del rol autorizados automáticamente.");
    }
    if(ST.vista==="docentes") VISTAS.docentes("gestion");
    else if(ST.vista==="personal") VISTAS.personal();
    else if(ST.vista==="equipos") VISTAS.equipos();
    if(esNuevo && r.id && ["docente","coordinador"].includes(body.rol) &&
       confirm("✅ Guardado. ¿Completar de una vez su HOJA DE VIDA (estudios, certificados, experiencia y foto)?")){
      verHV(r.id);
    }
  }catch(e){ toast("Error",true); }
}
async function eliminarPersona(id,nombre){
  if(!confirm(`¿Retirar a ${nombre} del plantel? (el histórico se conserva)`)) return;
  try{ const r=await post("/academico/personal/eliminar",{id}); toast(r.msg,!r.ok);
    if(r.ok){ if(ST.vista==="docentes") VISTAS.docentes("gestion"); else VISTAS.personal(); }
  }catch(e){ toast("Error",true); }
}

/* ── Hoja de vida ── */
async function verHV(id){
  try{
    const hv = await api(`/academico/personal/hoja_vida?personal_id=${id}`);
    window._hv = hv;
    document.getElementById("hv-title").textContent = "Hoja de vida — "+hv.nombre;
    const lista=(arr,pid)=>arr.map((x,i)=>`<div class="check-row"><span style="flex:1">${esc(x)}</span><button class="btn btn-xs btn-danger" onclick="window._hv.${pid}.splice(${i},1);pintarHV()">✕</button></div>`).join("");
    window.pintarHV = function(){
      const h=window._hv;
      document.getElementById("hv-body").innerHTML=`
        <div style="display:flex;gap:16px;align-items:center;margin-bottom:14px;flex-wrap:wrap">
          <div style="position:relative">
            ${h.foto?`<img class="avatar-foto lg" src="${h.foto}">`:`<div class="avatar-sm" style="width:56px;height:56px;font-size:1rem">${ini(h.nombre)}</div>`}
            <button class="btn btn-xs" style="position:absolute;bottom:-6px;right:-6px" title="Cambiar foto" onclick="abrirModalFoto(${h.id}, window._hv.foto)">📷</button>
          </div>
          <div style="flex:1"><b>${esc(h.nombre)}</b><div class="small muted">${esc(h.profesion||"")} · ${h.experiencia_anios} años de experiencia · CC ${esc(h.documento||"—")}</div>
          <div class="small muted">Vinculación: ${h.fecha_vinculacion||"—"} · 📞 ${esc(h.telefono||"—")}</div></div>
          <div class="score-ring" style="--v:${h.hv_score}"><span>${h.hv_score}</span></div>
        </div>
        <div class="legal-note" style="margin-bottom:12px">🧮 <b>Score de hoja de vida ${h.hv_score}/100</b> = base 35 + 8×títulos + 2×años de experiencia (máx 30) + 5×certificaciones. La Secretaría lo usa para encontrar talento docente.</div>
        <b class="small">🎓 Estudios</b>${lista(h.estudios,"estudios")}
        <div style="display:flex;gap:8px;margin:6px 0 12px"><input id="hv_est" placeholder="Nuevo título…" style="flex:1;padding:8px;border:1px solid var(--border);border-radius:8px"><button class="btn btn-sm" onclick="if(document.getElementById('hv_est').value.trim()){window._hv.estudios.push(document.getElementById('hv_est').value);pintarHV()}">➕</button></div>
        <b class="small">💼 Experiencia</b>${lista(h.experiencia,"experiencia")}
        <div style="display:flex;gap:8px;margin:6px 0 12px"><input id="hv_exp" placeholder="Cargo — institución (años)…" style="flex:1;padding:8px;border:1px solid var(--border);border-radius:8px"><button class="btn btn-sm" onclick="if(document.getElementById('hv_exp').value.trim()){window._hv.experiencia.push(document.getElementById('hv_exp').value);pintarHV()}">➕</button></div>
        <b class="small">🏅 Certificados, capacitaciones y diplomados</b>${lista(h.certificaciones,"certificaciones")}
        <div class="dropzone" style="margin:6px 0" onclick="document.getElementById('hv_certs_files').click()">📎 Sube tus certificados en PDF/imagen (simulado) — se anexan a la hoja de vida</div>
        <input type="file" id="hv_certs_files" multiple style="display:none" onchange="Array.from(this.files).slice(0,10).forEach(f=>window._hv.certificaciones.push('📎 '+f.name));pintarHV()">
        <div style="display:flex;gap:8px;margin:6px 0 12px"><input id="hv_cert" placeholder="…o escribe el curso o diplomado" style="flex:1;padding:8px;border:1px solid var(--border);border-radius:8px"><button class="btn btn-sm" onclick="if(document.getElementById('hv_cert').value.trim()){window._hv.certificaciones.push(document.getElementById('hv_cert').value);pintarHV()}">➕</button></div>
        <div class="dropzone" onclick="document.getElementById('hv_file').click()">📎 ${h.archivo?("Archivo adjunto: «"+esc(h.archivo)+"» — toca para reemplazar"):"Subir hoja de vida en PDF (simulado)"}</div>
        <input type="file" id="hv_file" style="display:none" onchange="window._hv.archivo=this.files[0]?this.files[0].name:window._hv.archivo;pintarHV()">
        <div style="text-align:right;margin-top:14px"><button class="btn btn-primary" onclick="guardarHV()">💾 Guardar hoja de vida</button></div>`;
    };
    pintarHV();
    abrirModal("modal-hv");
  }catch(e){ toast("Error",true); }
}
async function guardarHV(){
  const h=window._hv;
  try{ const r=await post("/academico/personal/hoja_vida/guardar",{personal_id:h.id,estudios:h.estudios,experiencia:h.experiencia,certificaciones:h.certificaciones,archivo:h.archivo});
    toast(r.msg,!r.ok);
    if(r.ok){ cerrarModal("modal-hv"); if(ST.vista==="personal")VISTAS.personal(); if(ST.vista==="docentes")VISTAS.docentes("gestion"); }
  }catch(e){ toast("Error",true); }
}

/* ═══════════ VISTA: PERSONAL (rector) ═══════════ */
VISTAS.personal = async function(){
  loading();
  try{
    const personal = await api(`/academico/personal?institucion_id=${ST.institucion_id}`);
    window._personal = personal;
    const GRUPOS=[["Directivos y coordinación",["rector","coordinador"]],["Docentes",["docente"]],
      ["Equipo administrativo",["auxiliar","contador","abogado"]],["Apoyo y servicios",["psicoorientacion","vigilante","servicios"]]];
    const ROL_LBL={rector:"Rector(a)",coordinador:"Coordinador(a)",docente:"Docente",auxiliar:"Contratación",contador:"Contador(a)",abogado:"Abogado(a)",psicoorientacion:"Psicoorientación",vigilante:"Vigilante",servicios:"Servicios"};
    const seccion=(titulo,roles)=>{
      const arr=personal.filter(p=>roles.includes(p.rol));
      if(!arr.length) return "";
      return `<div class="card"><div class="card-head"><h3>${titulo}</h3><span class="small muted">${arr.length}</span></div>
        <div class="tbl-scroll"><table><thead><tr><th>Persona</th><th>Cargo</th><th style="text-align:center">Score HV</th><th style="text-align:center">Asistencia</th><th>Contacto</th><th></th></tr></thead><tbody>
        ${arr.map(p=>`<tr>
          <td><div class="flex-cell">${avatarCell(p.foto,p.nombre)}<div><b>${esc(p.nombre)}</b><div class="small muted">${esc(p.profesion||"")}</div></div></div></td>
          <td>${ROL_LBL[p.rol]||p.rol}<div class="small muted">${esc(p.area||"")}</div></td>
          <td style="text-align:center"><div class="score-ring" style="--v:${p.hv_score||0};width:42px;height:42px;font-size:.78rem;margin:0 auto"><span>${p.hv_score||0}</span></div></td>
          <td style="text-align:center">${p.asistencia_pct!=null?`<span class="badge ${p.asistencia_pct<85?'b-red':p.asistencia_pct<93?'b-orange':'b-green'}">${p.asistencia_pct}%</span>`:'—'}</td>
          <td class="small">${esc(p.telefono||"—")}<div class="muted">${esc(p.email||"")}</div></td>
          <td style="white-space:nowrap">
            <button class="btn btn-xs" onclick="verHV(${p.id})">📄 HV</button>
            <button class="btn btn-xs" onclick="editarPersona(${p.id})">✎</button>
            ${p.rol!=="rector"?`<button class="btn btn-xs btn-danger" onclick="eliminarPersona(${p.id},'${esc(p.nombre)}')">🗑</button>`:""}
          </td></tr>`).join("")}
        </tbody></table></div></div>`;
    };
    main(head("Personal de la institución", `${personal.length} personas — de rectoría a servicios generales, con hoja de vida y score`,
      `<button class="btn btn-primary" onclick="editarPersona(0)">➕ Agregar persona</button>`)+
      GRUPOS.map(([t,r])=>seccion(t,r)).join("")+
      `<div class="audit-note">📌 El <b>score de hoja de vida</b> y el <b>% de asistencia docente</b> son visibles para la Secretaría de Educación en su tablero de talento — así encuentran y contactan docentes para vacantes.</div>`);
  }catch(e){ main(`<div class="empty">Error</div>`); }
};

/* ═══════════ VISTA: EQUIPOS DE TRABAJO (rector) ═══════════ */
VISTAS.equipos = async function(){
  loading();
  try{
    const personal = await api(`/academico/personal?institucion_id=${ST.institucion_id}`);
    window._personal = personal;
    const ROLES_EQUIPO=[
      ["auxiliar","🗂️","Contratación","Recibe y sube los documentos de cada contratista (con fecha verificada), arma expedientes, genera el link de autogestión y mueve el pipeline hasta jurídica.","fse,contratos"],
      ["contador","🧮","Contaduría","Expide y edita CDP y RP, lleva el libro del FSE, registra cuentas de cobro y pagos, y responde por los reportes a Contraloría.","fse,contratos,datos"],
      ["abogado","⚖️","Jurídica","Revisa requisitos legales de cada contrato, emite el Vo.Bo. o lo devuelve con observaciones, y firma en línea.","contratos"],
    ];
    const cards = ROLES_EQUIPO.map(([rol,ico,titulo,desc,panelesDef])=>{
      const gente = personal.filter(p=>p.rol===rol);
      return `<div class="va-card" style="cursor:default">
        <div class="va-top"><b style="font-size:1rem">${ico} ${titulo}</b><span class="badge b-teal">${gente.length} persona(s)</span></div>
        <div class="small muted" style="min-height:58px">${desc}</div>
        <div style="margin:8px 0">${gente.map(p=>`<div class="flex-cell" style="margin-bottom:6px">${avatarCell(p.foto,p.nombre)}<div style="flex:1"><b class="small">${esc(p.nombre)}</b><div class="small muted">Paneles: ${(p.paneles||"—")||"—"}</div></div><button class="btn btn-xs" onclick="verHV(${p.id})">📄</button></div>`).join("")||'<div class="small muted">Sin asignar aún.</div>'}</div>
        <button class="btn btn-sm btn-primary" style="width:100%" onclick="agregarAlEquipo('${rol}','${panelesDef}')">➕ Agregar al equipo</button>
      </div>`;}).join("");
    const admin = personal.filter(p=>["auxiliar","contador","abogado","coordinador","psicoorientacion"].includes(p.rol));
    const ROL_LBL={auxiliar:"Contratación",contador:"Contador(a)",abogado:"Abogado(a)",coordinador:"Coordinador(a)",psicoorientacion:"Psicoorientación"};
    main(head("Equipos de trabajo","Arma tu equipo administrativo: cada rol tiene responsabilidades claras y solo ve los paneles que tú autorices")+`
      <div class="grid-cards" style="margin-bottom:18px">${cards}</div>
      <div class="card"><div class="card-head"><h3>🔐 Matriz de permisos (qué panel ve cada quién)</h3><span class="small muted">los cambios aplican al instante en su perfil</span></div>
      <div class="tbl-scroll"><table>
        <thead><tr><th>Persona</th><th>Cargo</th><th style="text-align:center">💰 FSE</th><th style="text-align:center">📜 Contratos</th><th style="text-align:center">🧠 Datos & IA</th><th></th></tr></thead>
        <tbody>${admin.map(p=>{
          const pan=(p.paneles||"").split(",");
          return `<tr>
            <td><div class="flex-cell">${avatarCell(p.foto,p.nombre)}<b>${esc(p.nombre)}</b></div></td>
            <td>${ROL_LBL[p.rol]||p.rol}</td>
            ${["fse","contratos","datos"].map(k=>`<td style="text-align:center"><input type="checkbox" id="aut-${p.id}-${k}" ${pan.includes(k)?"checked":""} style="width:18px;height:18px;accent-color:var(--teal)"></td>`).join("")}
            <td><button class="btn btn-xs btn-primary" onclick="guardarAutorizacion(${p.id})">💾 Guardar</button></td>
          </tr>`;}).join("")||'<tr><td colspan="6" class="empty">Agrega personal administrativo primero.</td></tr>'}
        </tbody></table></div></div>
      <div class="legal-note">🤝 Así delega la rectoría SIN perder control: cada acción del equipo queda en el log de metadatos con fecha y responsable. Cambia los perfiles arriba a Contratación, Contaduría o Jurídica para ver exactamente lo que ve cada uno.</div>`);
  }catch(e){ main(`<div class="empty">Error</div>`); }
};
function agregarAlEquipo(rol, panelesDef){
  window._equipoPaneles = panelesDef;
  editarPersona(0, rol);
  document.getElementById("per_hint").innerHTML = "🤝 Al guardar quedará en el equipo con los paneles <b>"+panelesDef+"</b> autorizados automáticamente (puedes ajustarlo en la matriz).";
}
async function guardarAutorizacion(pid){
  const paneles=["fse","contratos","datos"].filter(k=>document.getElementById(`aut-${pid}-${k}`).checked);
  try{ const r=await post("/academico/autorizaciones/guardar",{institucion_id:ST.institucion_id,personal_id:pid,paneles});
    toast(r.msg,!r.ok);
  }catch(e){ toast("Error",true); }
}

/* ═══════════ VISTA: FONDO FSE ═══════════ */
VISTAS.fse = async function(tab){
  loading();
  try{
    const t=tab||"plan";
    const res = await api(`/fse/resumen?institucion_id=${ST.institucion_id}`);
    main(head("Fondo de Servicios Educativos (FSE)", "Contabilidad del colegio conciliada con SECOP · régimen especial (Decreto 4791/2008)")+`
      <div class="kpis">
        <div class="kpi green"><div class="kpi-ico">📥</div><div class="kpi-val sm">${money(res.ingresos)}</div><div class="kpi-lbl">Ingresos</div></div>
        <div class="kpi red"><div class="kpi-ico">📤</div><div class="kpi-val sm">${money(res.egresos)}</div><div class="kpi-lbl">Egresos ejecutados</div></div>
        <div class="kpi"><div class="kpi-ico">💰</div><div class="kpi-val sm">${money(res.saldo)}</div><div class="kpi-lbl">Saldo disponible</div></div>
        <div class="kpi orange"><div class="kpi-ico">📋</div><div class="kpi-val sm">${money(res.plan_total)}</div><div class="kpi-lbl">Plan de compras</div></div>
      </div>
      <div class="subtabs">
        ${[["plan","📋 Plan de compras"],["presupuesto","🏛️ Presupuesto"],["rubros","🗂️ Rubros"],["rp","🧾 CDP / RP"],["mov","💸 Movimientos"],["audit","🔍 Auditoría + SECOP"]].map(([k,l])=>
          `<button class="subtab ${t===k?'active':''}" onclick="VISTAS.fse('${k}')">${l}</button>`).join("")}</div>
      <div id="fse-cont"><div class="empty">Cargando…</div></div>`);
    if(t==="plan") fsePlan();
    if(t==="presupuesto") fsePresupuesto();
    if(t==="rubros") fseRubros();
    if(t==="rp") fseRP();
    if(t==="mov") fseMov();
    if(t==="audit") fseAudit();
  }catch(e){ main(`<div class="empty">Error cargando FSE</div>`); }
};
async function fsePlan(){
  const [plan, cuentas] = await Promise.all([
    api(`/fse/plan?institucion_id=${ST.institucion_id}`),
    api(`/fse/cuentas?institucion_id=${ST.institucion_id}`),
  ]);
  window._cuentasFSE = cuentas;
  window._planFSE = plan;
  const puedeEditar = ["rector","contador","auxiliar"].includes(ST.perfil.rol);
  document.getElementById("fse-cont").innerHTML = `
    ${puedeEditar?`<div style="display:flex;gap:8px;justify-content:flex-end;margin-bottom:10px;flex-wrap:wrap">
      <button class="btn btn-gold btn-sm" onclick="importarPlanPDF()">📄 Importar plan desde PDF (IA)</button>
      <button class="btn btn-primary btn-sm" onclick="editarPlanItem(0)">➕ Agregar ítem manual</button>
    </div>`:""}
    <div id="plan-import"></div>
    <div class="card"><div class="tbl-scroll"><table>
      <thead><tr><th>Concepto</th><th>Cuenta</th><th>Prioridad</th><th>Mes</th><th style="text-align:right">Presupuesto</th><th>Estado</th>${puedeEditar?'<th></th>':''}</tr></thead>
      <tbody>${plan.map(p=>{
        const [pl,pb]=PRIO[p.prioridad]||["—","b-gray"];
        return `<tr><td><b>${esc(p.concepto)}</b></td><td class="small">${esc(p.cuenta||"—")}</td>
          <td><span class="badge ${pb}">${pl}</span></td><td>${MESES[p.mes]||"—"}</td>
          <td style="text-align:right"><b>${money(p.valor)}</b></td>
          <td>${puedeEditar?`<select onchange="planEstado(${p.id},this.value)" style="padding:5px 8px;border:1px solid var(--border);border-radius:7px;font-size:.78rem">
            <option value="pendiente" ${p.estado==='pendiente'?'selected':''}>Pendiente</option>
            <option value="parcial" ${p.estado==='parcial'?'selected':''}>Parcial</option>
            <option value="comprado" ${p.estado==='comprado'?'selected':''}>Comprado</option></select>`
            :`<span class="badge ${p.estado==='comprado'?'b-green':p.estado==='parcial'?'b-orange':'b-gray'}">${esc(p.estado)}</span>`}</td>
          ${puedeEditar?`<td style="white-space:nowrap"><button class="btn btn-xs" onclick="editarPlanItem(${p.id})">✎</button>
            <button class="btn btn-xs btn-danger" onclick="eliminarPlanItem(${p.id},'${esc(p.concepto)}')">🗑</button></td>`:''}</tr>`;}).join("")||'<tr><td colspan="7" class="empty">Plan vacío. Impórtalo desde el PDF o agrégalo manual.</td></tr>'}
      </tbody></table></div></div>
    <div class="legal-note">📌 El plan de compras es la hoja de ruta anual del FSE aprobada por el Consejo Directivo. Con el botón <b>📄 Importar</b> subes el PDF del plan y la IA extrae los ítems para que solo confirmes.</div>`;
}
async function fseRP(){
  const rps = await api(`/fse/rp?institucion_id=${ST.institucion_id}`);
  document.getElementById("fse-cont").innerHTML = `
    <div class="card"><div class="tbl-scroll"><table>
      <thead><tr><th>Consecutivo</th><th>Fecha</th><th>Objeto</th><th>Proveedor</th><th style="text-align:right">Valor</th><th>SECOP</th></tr></thead>
      <tbody>${rps.map(r=>`<tr>
        <td><b>${esc(r.consecutivo)}</b><div class="small muted">${(r.tipo||"").toUpperCase()}</div></td>
        <td class="small">${esc(r.fecha)}</td><td>${esc(r.objeto)}</td>
        <td class="small">${esc(r.proveedor||"—")}<div class="muted">${esc(r.nit||"")}</div></td>
        <td style="text-align:right"><b>${money(r.valor)}</b>${r.desviacion!=null?`<div class="desv ${r.desviacion>3?'desv-high':r.desviacion<-3?'desv-low':'desv-ok'}">${r.desviacion>0?'+':''}${r.desviacion}% vs SECOP</div>`:""}</td>
        <td><a href="${r.secop_url}" target="_blank" class="btn btn-xs">🔗 Ver</a></td></tr>`).join("")}
      </tbody></table></div></div>`;
}
async function fseMov(){
  const movs = await api(`/fse/movimientos?institucion_id=${ST.institucion_id}`);
  const cuentas = await api(`/fse/cuentas?institucion_id=${ST.institucion_id}`);
  window._cuentasFSE = cuentas;
  document.getElementById("fse-cont").innerHTML = `
    <div style="text-align:right;margin-bottom:10px">
      <button class="btn btn-green btn-sm" onclick="abrirModalMov('ingreso')">📥 Registrar ingreso</button>
      <button class="btn btn-primary btn-sm" onclick="abrirModalMov('egreso')">📤 Registrar egreso</button>
    </div>
    <div class="card"><div class="tbl-scroll"><table>
      <thead><tr><th>Fecha</th><th>Tipo</th><th>Concepto</th><th>Proveedor</th><th style="text-align:right">Valor</th><th>Estado</th></tr></thead>
      <tbody>${movs.map(m=>`<tr>
        <td class="small">${esc(m.fecha)}</td>
        <td>${m.tipo==="ingreso"?'<span class="badge b-green">Ingreso</span>':'<span class="badge b-red">Egreso</span>'}</td>
        <td><b>${esc(m.concepto)}</b><div class="small muted">${esc(m.cuenta||"")} · ${esc(m.comprobante||"")}</div></td>
        <td class="small">${esc(m.proveedor||"—")}</td>
        <td style="text-align:right"><b style="color:${m.tipo==='ingreso'?'var(--green)':'var(--red)'}">${m.tipo==='ingreso'?'+':'−'}${money(m.valor)}</b></td>
        <td><span class="badge ${m.estado==='pagado'?'b-green':m.estado==='anulado'?'b-gray':'b-blue'}">${esc(m.estado)}</span></td></tr>`).join("")}
      </tbody></table></div></div>`;
}
async function fseAudit(){
  const a = await api(`/fse/auditoria?institucion_id=${ST.institucion_id}`);
  document.getElementById("fse-cont").innerHTML = `
    <div class="card"><div class="card-head"><h3>Trazabilidad de egresos vs SECOP</h3><button class="btn btn-sm" onclick="window.print()">🖨️ Imprimir</button></div>
    <div class="tbl-scroll"><table>
      <thead><tr><th>Fecha</th><th>Concepto</th><th>Proveedor</th><th>Cuenta</th><th>Comp.</th><th style="text-align:right">FSE</th><th style="text-align:right">SECOP</th><th></th></tr></thead>
      <tbody>${a.filas.map(f=>{
        const dv = f.valor_secop&&f.valor?Math.round((f.valor-f.valor_secop)/f.valor_secop*1000)/10:null;
        return `<tr><td class="small">${esc(f.fecha)}</td><td>${esc(f.concepto)}</td>
          <td class="small">${esc(f.proveedor||"—")}<div class="muted">${esc(f.nit||"")}</div></td>
          <td class="small">${esc(f.cuenta||"")}</td><td class="small">${esc(f.comprobante||"")}</td>
          <td style="text-align:right">${money(f.valor)}</td>
          <td style="text-align:right">${f.valor_secop?money(f.valor_secop):"—"}${dv!=null?`<div class="desv ${dv>3?'desv-high':dv<-3?'desv-low':'desv-ok'}">${dv>0?'+':''}${dv}%</div>`:""}</td>
          <td>${f.secop_url?`<a href="${f.secop_url}" target="_blank" class="btn btn-xs">🔗</a>`:""}</td></tr>`;}).join("")}
      </tbody></table></div></div>
    <div class="audit-note">🔍 <b>Conciliación automática FSE ↔ SECOP.</b> El sistema marca en rojo las compras cuyo valor pagado se desvía del contrato publicado — así la Contraloría y la Secretaría detectan sobrecostos al instante. Todo con enlace directo a SECOP.</div>`;
}
function abrirModalMov(tipo){
  document.getElementById("modal-mov-title").textContent = tipo==="ingreso"?"📥 Registrar ingreso":"📤 Registrar egreso";
  document.getElementById("mov_tipo").value=tipo;
  document.getElementById("mov_id").value="";
  document.getElementById("mov_fecha").value=hoyISO();
  document.getElementById("mov_concepto").value="";
  document.getElementById("mov_prov").value="";
  document.getElementById("mov_nit").value="";
  document.getElementById("mov_valor").value="";
  document.getElementById("mov_comp").value="";
  document.getElementById("mov_metodo").value="Transferencia";
  document.getElementById("mov_estado").value=tipo==="ingreso"?"registrado":"pagado";
  document.getElementById("mov_cuenta").innerHTML = (window._cuentasFSE||[]).filter(c=>tipo==="ingreso"?c.tipo==="ingreso":c.tipo==="gasto")
    .map(c=>`<option value="${c.codigo}">${c.codigo} · ${esc(c.nombre)}</option>`).join("");
  abrirModal("modal-mov");
}
async function guardarMov(){
  const body={ institucion_id:ST.institucion_id, tipo:document.getElementById("mov_tipo").value,
    fecha:document.getElementById("mov_fecha").value, cuenta_codigo:document.getElementById("mov_cuenta").value,
    concepto:document.getElementById("mov_concepto").value, proveedor:document.getElementById("mov_prov").value,
    nit:document.getElementById("mov_nit").value, valor:parseFloat(document.getElementById("mov_valor").value)||0,
    metodo:document.getElementById("mov_metodo").value, comprobante:document.getElementById("mov_comp").value,
    estado:document.getElementById("mov_estado").value };
  if(!body.concepto.trim()||body.valor<=0){toast("Concepto y valor son obligatorios",true);return;}
  try{ const r=await post("/fse/movimientos/guardar",body);
    if(!r.ok){toast(r.msg,true);return;}
    cerrarModal("modal-mov"); toast(r.msg); VISTAS.fse("mov");
  }catch(e){ toast("Error",true); }
}

/* ═══════════ VISTA: CONTRATACIÓN SECOP 2 ═══════════ */
const DOCS_LABELS=[["cedula","Cédula/rep. legal"],["contraloria","Contraloría"],["procuraduria","Procuraduría"],["redam","REDAM"],["camara_comercio","Cámara de Comercio"],["rut","RUT"],["seguridad_social","Seguridad social"]];
VISTAS.contratos = async function(tab){
  loading();
  try{
    const t=tab||"pipeline";
    main(head("Contratación — Régimen especial FSE", "Pipeline SECOP 2 con firma en línea (OTP) · topes del Decreto 4791/2008 art. 17")+`
      <div class="subtabs">
        ${[["pipeline","📜 Contratos"],["contratistas","🏢 Contratistas y documentos"],["vencimientos","🗓️ Vencimientos"],["secop","📤 SECOP"],["propuestas","📨 Propuestas"],["cronologia","🕓 Cronología (auditoría)"],["topes","⚖️ Topes y control legal"]].map(([k,l])=>
          `<button class="subtab ${t===k?'active':''}" onclick="VISTAS.contratos('${k}')">${l}</button>`).join("")}</div>
      <div id="con-cont"><div class="empty">Cargando…</div></div>`);
    ST._conTab = t;
    if(t==="pipeline") contratosPipeline();
    if(t==="contratistas") contratistasView();
    if(t==="vencimientos") vencimientosView();
    if(t==="secop") secopView();
    if(t==="propuestas") propuestasView();
    if(t==="cronologia") cronologiaView();
    if(t==="topes") topesView();
  }catch(e){ main(`<div class="empty">Error</div>`); }
};
async function contratosPipeline(){
  const [contratos, contratistas, plan] = await Promise.all([
    api(`/contratos/?institucion_id=${ST.institucion_id}`),
    api(`/contratos/contratistas`),
    api(`/fse/plan?institucion_id=${ST.institucion_id}`),
  ]);
  window._contratistas = contratistas;
  window._planFSE = plan;
  window._contratosCache = contratos;
  const esAbogado = ST.perfil.rol==="abogado";
  const PASOS=["Borrador","Documentos","Jurídica","Firma","Firmado","Ejecución","Liquidado"];
  document.getElementById("con-cont").innerHTML = `
    <div style="text-align:right;margin-bottom:12px"><button class="btn btn-primary" onclick="abrirModalContrato()">➕ Nuevo contrato</button></div>
    ${contratos.map(c=>{
      const stepper=`<div class="pipe">${c.pipeline.map((p,i)=>`
        <div class="pipe-step ${i<c.paso?'done':i===c.paso?'current':''}">
          <div class="pipe-dot">${i<c.paso?'✓':i+1}</div><div class="pipe-lbl">${PASOS[i]}</div>
        </div>${i<c.pipeline.length-1?`<div class="pipe-con ${i<c.paso?'done':''}"></div>`:''}`).join("")}</div>`;
      const firmasHtml = (c.firmas||[]).map(f=>`
        <div class="firma-row"><span>${f.firmado?'✅':'⏳'} <b>${esc(f.rol)}</b> · ${esc(f.nombre)}</span>
        <span class="small muted">${f.firmado?esc(f.metodo)+" · "+esc(f.fecha||""):"pendiente"}</span></div>`).join("");
      const puedeFirmar = c.estado==="firma" && (c.firmas||[]).some(f=>!f.firmado);
      const puedeAvanzar = !["liquidado"].includes(c.estado);
      return `<div class="card"><div class="card-body">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;flex-wrap:wrap;margin-bottom:8px">
          <div><b>${esc(c.numero)}</b> · ${esc(c.objeto)} <span class="badge b-teal">${esc(c.tipo_label||"Suministro")}</span>
            <div class="small muted">${esc(c.contratista)} · ${money(c.valor)} <span class="badge b-blue">${c.valor_smmlv} SMMLV</span>${c.excede_tope?' <span class="badge b-red">⚠️ excede tope</span>':''}</div>
            <div class="small muted">CDP ${esc(c.cdp||"—")} · RP ${esc(c.rp||"—")}${c.plan?` · Plan: ${esc(c.plan)}`:""}</div>
            ${c.dias_en_etapa!=null&&c.plazo_etapa!=null?`<span class="badge ${c.atrasado?'plazo-mal':'plazo-ok'}" title="tiempo en la etapa actual vs plazo del tipo de contrato">⏱ ${c.dias_en_etapa} día(s) en esta etapa · plazo ${c.plazo_etapa}${c.atrasado?' — ¡ATRASADO!':''}</span>`:""}
          </div>
          <div style="text-align:right"><span class="badge ${{borrador:'b-gray',documentos:'b-orange',juridica:'b-purple',firma:'b-gold',firmado:'b-teal',ejecucion:'b-green',liquidado:'b-blue'}[c.estado]||'b-gray'}">${c.estado.toUpperCase()}</span>
          <div style="margin-top:6px"><a href="${c.secop_url}" target="_blank" class="btn btn-xs">🔗 SECOP</a></div></div>
        </div>
        ${stepper}
        ${!c.docs_ok?`<div style="margin-top:8px"><span class="small" style="color:var(--red)">⛔ Documentos faltantes del contratista:</span> ${c.docs_faltantes.map(x=>`<span class="doc-chip no">${esc(x)}</span>`).join("")}</div>`:""}
        <div style="margin-top:10px">${firmasHtml}</div>
        ${c.nota_juridica?`<div class="legal-note" style="margin-top:8px">⚖️ <b>Jurídica:</b> ${esc(c.nota_juridica)}</div>`:""}
        <div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap">
          <button class="btn btn-sm" onclick="abrirCoedit(${c.id})">✎ Editar</button>
          <button class="btn btn-sm" onclick="verPipelineDetalle(${c.id})">📜 Paso a paso</button>
          <button class="btn btn-sm" onclick="abrirChecklistDocs(${c.contratista_id},'${esc(c.numero)}')">📋 Checklist de documentos</button>
          <button class="btn btn-sm btn-purple" onclick="validarLogicaContrato(${c.id})">⚖️ Revisión jurídica</button>
          <button class="btn btn-sm" onclick="recordarFirmas(${c.id})">📱 Recordar firmas</button>
          ${puedeFirmar?`<button class="btn btn-sm btn-gold" onclick='abrirModalFirma(${c.id}, ${JSON.stringify(c.firmas)})'>✍️ Firmar en línea</button>`:""}
          ${esAbogado&&c.estado==="juridica"?`<button class="btn btn-sm btn-green" onclick="juridicaContrato(${c.id},true)">⚖️ Dar Vo.Bo. jurídico</button><button class="btn btn-sm btn-danger" onclick="juridicaContrato(${c.id},false)">↩️ Devolver</button>`:""}
          ${puedeAvanzar&&c.estado!=="juridica"?`<button class="btn btn-sm btn-primary" onclick="avanzarContrato(${c.id})">Avanzar etapa →</button>`:""}
        </div>
      </div></div>`;
    }).join("")||'<div class="empty">Sin contratos. Crea el primero con ➕</div>'}
    <div class="legal-note">📜 Flujo real SECOP 2: <b>Borrador → Documentos → Jurídica → Firma → Firmado → Ejecución → Liquidado</b>. Cada etapa valida requisitos; las firmas usan verificación de identidad por OTP (simulado). Nada avanza si faltan documentos del contratista.</div>`;
}
function abrirModalContrato(){
  const an=document.getElementById("co_analisis"); if(an) an.innerHTML="";
  document.getElementById("co_contratista").innerHTML = (window._contratistas||[]).map(c=>
    `<option value="${c.id}" data-cap="${c.disponible_cop}" data-conf="${c.confianza}" data-ok="${c.docs_completos}">${esc(c.nombre)} — confianza ${c.confianza}% ${c.docs_completos?"✅":"⚠️ docs incompletos"}</option>`).join("");
  document.getElementById("co_objeto").value="";
  document.getElementById("co_valor").value="";
  document.getElementById("co_plan").innerHTML = `<option value="">— Ninguno —</option>`+(window._planFSE||[]).map(p=>`<option value="${p.id}">${esc(p.concepto)} (${money(p.valor)})</option>`).join("");
  coInfo();
  abrirModal("modal-contrato");
}
function coInfo(){
  const sel=document.getElementById("co_contratista");
  const opt=sel.options[sel.selectedIndex];
  const valor=parseFloat(document.getElementById("co_valor").value)||0;
  const smmlv=1623500, tope=20;
  const smmlvVal=(valor/smmlv).toFixed(2);
  const excede=valor>tope*smmlv;
  const disp=opt?parseFloat(opt.dataset.cap):0;
  const docsOk=opt?opt.dataset.ok==="true":true;
  let html=`El CDP se expide automáticamente al crear el borrador. `;
  html+=`<br>Valor: <b>${valor?money(valor):"—"}</b> = <b>${valor?smmlvVal:"0"} SMMLV</b>. Tope régimen especial: 20 SMMLV (${money(tope*smmlv)}).`;
  if(excede) html=`<span style="color:var(--red)">⚠️ <b>Este valor SUPERA el tope</b> de 20 SMMLV. El sistema lo bloqueará: debe ir por Ley 80.</span>`;
  else if(valor>disp) html+=`<br><span style="color:var(--red)">⚠️ Supera la capacidad disponible del contratista (${money(disp)}).</span>`;
  if(!docsOk) html+=`<br><span style="color:var(--orange)">⚠️ El contratista tiene documentos pendientes; podrás crear el borrador pero no avanzará a jurídica.</span>`;
  document.getElementById("co_info").innerHTML=html;
}
async function guardarContrato(){
  const body={institucion_id:ST.institucion_id, contratista_id:parseInt(document.getElementById("co_contratista").value),
    objeto:document.getElementById("co_objeto").value, valor:parseFloat(document.getElementById("co_valor").value)||0,
    plan_id:parseInt(document.getElementById("co_plan").value)||null,
    tipo_contrato:document.getElementById("co_tipo").value };
  try{ const r=await post("/contratos/guardar",body);
    if(!r.ok){toast(r.msg,true);return;}
    cerrarModal("modal-contrato"); toast(r.msg); VISTAS.contratos("pipeline");
  }catch(e){ toast("Error",true); }
}
async function avanzarContrato(id){
  try{ const r=await post("/contratos/avanzar",{id}); toast(r.msg,!r.ok); if(r.ok) VISTAS.contratos("pipeline"); }
  catch(e){ toast("Error",true); }
}
async function juridicaContrato(id, aprobado){
  const nota = aprobado ? (prompt("Nota jurídica (Vo.Bo.):","Revisado. Cumple requisitos del régimen especial.")||"Aprobado.") 
                        : (prompt("Observación (por qué se devuelve):","Falta subsanar documentos del contratista.")||"Devuelto.");
  try{ const r=await post("/contratos/juridica",{id,nota,aprobado}); toast(r.msg,!r.ok); if(r.ok) VISTAS.contratos("pipeline"); }
  catch(e){ toast("Error",true); }
}
function abrirModalFirma(id, firmas){
  const pendientes=firmas.filter(f=>!f.firmado);
  document.getElementById("firma-body").innerHTML = `
    <p class="small" style="margin-bottom:12px">Selecciona quién firma. Se enviará un código OTP de 6 dígitos a su celular/correo para validar la identidad antes de firmar electrónicamente <span class="muted">(simulado — usa cualquier 6 dígitos)</span>.</p>
    <div class="frow"><label>Firmante</label><select id="firma_rol">${pendientes.map(f=>`<option value="${esc(f.rol)}">${esc(f.rol)} · ${esc(f.nombre)}</option>`).join("")}</select></div>
    <div class="otp-wrap">${[0,1,2,3,4,5].map(i=>`<input class="otp-in" id="otp-${i}" maxlength="1" inputmode="numeric" onkeyup="otpnext(${i})">`).join("")}</div>
    <input type="hidden" id="firma_cid" value="${id}">
    <div style="text-align:center"><button class="btn btn-gold" onclick="firmarContrato()">✍️ Validar OTP y firmar</button></div>`;
  abrirModal("modal-firma");
}
function otpnext(i){
  const el=document.getElementById("otp-"+i);
  if(el.value && i<5) document.getElementById("otp-"+(i+1)).focus();
}
async function firmarContrato(){
  const otp=[0,1,2,3,4,5].map(i=>document.getElementById("otp-"+i).value).join("");
  if(otp.length!==6 || !/^\d{6}$/.test(otp)){ toast("Ingresa los 6 dígitos del código OTP",true); return; }
  const id=parseInt(document.getElementById("firma_cid").value);
  const rol=document.getElementById("firma_rol").value;
  try{ const r=await post("/contratos/firmar",{id,rol,otp}); 
    if(!r.ok){toast(r.msg,true);return;}
    cerrarModal("modal-firma"); toast(r.msg); VISTAS.contratos("pipeline");
  }catch(e){ toast("Error",true); }
}
async function contratistasView(){
  const cts = await api(`/contratos/contratistas`);
  window._contratistas = cts;
  document.getElementById("con-cont").innerHTML = `
    <div style="text-align:right;margin-bottom:12px"><button class="btn btn-primary" onclick="editarContratista(0)">➕ Nuevo contratista</button></div>
    <div class="grid-cards">
    ${cts.map(c=>`
      <div class="va-card" style="cursor:default">
        <div class="va-top"><b>${esc(c.nombre)}</b>${c.docs_completos?'<span class="badge b-green">Expediente OK</span>':'<span class="badge b-red">Incompleto</span>'}</div>
        <div class="small muted">${esc(c.nit||"")} · ${c.tipo==="natural"?"Persona natural":"Persona jurídica"}</div>
        <div style="margin:8px 0">${c.documentos.map(d=>`<span class="doc-chip ${d.ok?'ok':'no'}" title="${d.archivo?esc(d.archivo)+' · '+esc(d.fecha||''):''}">${d.ok?'✓':'✕'} ${esc(d.label)}${d.ok&&d.fecha?` <span style="opacity:.7">${esc(d.fecha.slice(5))}</span>`:""}</span>`).join("")}</div>
        <div class="small"><b>Confianza:</b> <div class="prog" style="display:inline-block;width:100px;vertical-align:middle"><div class="prog-fill" style="width:${c.confianza}%;background:${c.confianza>=80?'var(--green)':c.confianza>=60?'var(--orange)':'var(--red)'}"></div></div> ${c.confianza}%</div>
        <div class="small" style="margin-top:5px"><b>Capacidad anual:</b> ${money(c.contratado_anio)} / ${money(c.capacidad_cop)} <span class="muted">(${c.pct_usado}% usado)</span></div>
        <div style="margin-top:10px;display:flex;gap:6px;flex-wrap:wrap">
          <button class="btn btn-xs" onclick="editarContratista(${c.id})">✎ Expediente</button>
          <button class="btn btn-xs btn-gold" onclick="portalLink(${c.id})">🔗 Enviar link</button>
          <button class="btn btn-xs" onclick="vistaPreviaPortal(${c.id})">👁️ Vista previa</button>
          ${!c.docs_completos?`<button class="btn btn-xs btn-green" onclick="portalCarga(${c.id})">📥 Simular carga del contratista</button>`:""}
        </div>
      </div>`).join("")}
    </div>`;
}
function editarContratista(id){
  const c=(window._contratistas||[]).find(x=>x.id===id);
  document.getElementById("ct-title").textContent = id?"Editar expediente":"Nuevo contratista";
  document.getElementById("ct_id").value=id||"";
  document.getElementById("ct_nombre").value=c?c.nombre:"";
  document.getElementById("ct_nit").value=c?(c.nit||""):"";
  document.getElementById("ct_tipo").value=c?c.tipo:"juridica";
  document.getElementById("ct_tel").value=c?(c.telefono||""):"";
  document.getElementById("ct_cap").value=c?c.capacidad_smmlv:20;
  document.getElementById("ct_email").value=c?(c.email||""):"";
  document.getElementById("ct_notas").value=c?(c.notas||""):"";
  const docsActuales={};
  if(c) c.documentos.forEach(d=>docsActuales[d.clave]={ok:d.ok,archivo:d.archivo,fecha:d.fecha});
  window._ctDocs = docsActuales;
  document.getElementById("ct_docs").innerHTML = DOCS_LABELS.map(([k,l])=>{
    const d=docsActuales[k]||{};
    return `<div class="check-row">
      <input type="checkbox" id="ctd-${k}" ${d.ok?"checked":""}>
      <label for="ctd-${k}" style="margin:0;flex:1">📄 ${l}
        <span class="small muted" id="ctd-info-${k}">${d.archivo?`· ${esc(d.archivo)} (${esc(d.fecha||"")})`:""}</span></label>
      <input type="date" id="ctd-fecha-${k}" value="${d.fecha||''}" class="nota-in" style="width:135px" title="fecha del documento (verifícala)">
      <button class="btn btn-xs" onclick="ctSubirDoc('${k}')" title="Subir archivo (simulado)">📎</button>
      <input type="file" id="ctd-file-${k}" style="display:none" onchange="ctArchivoSel('${k}',this)">
    </div>`;}).join("");
  abrirModal("modal-contratista");
}
function ctSubirDoc(k){ document.getElementById("ctd-file-"+k).click(); }
function ctArchivoSel(k, inp){
  const f=inp.files[0]; if(!f) return;
  window._ctDocs[k]={...(window._ctDocs[k]||{}), ok:true, archivo:f.name};
  document.getElementById("ctd-"+k).checked=true;
  if(!document.getElementById("ctd-fecha-"+k).value) document.getElementById("ctd-fecha-"+k).value=hoyISO();
  document.getElementById("ctd-info-"+k).textContent="· "+f.name+" (recién subido)";
}
async function guardarContratista(){
  const documentos={};
  DOCS_LABELS.forEach(([k])=>{
    const ok=document.getElementById("ctd-"+k).checked;
    const prev=(window._ctDocs||{})[k]||{};
    documentos[k]={ok, archivo: ok?(prev.archivo||k+".pdf"):null,
      fecha: ok?(document.getElementById("ctd-fecha-"+k).value||hoyISO()):null};
  });
  const body={ id:parseInt(document.getElementById("ct_id").value)||0,
    nombre:document.getElementById("ct_nombre").value, nit:document.getElementById("ct_nit").value,
    tipo:document.getElementById("ct_tipo").value, telefono:document.getElementById("ct_tel").value,
    email:document.getElementById("ct_email").value, capacidad_smmlv:parseFloat(document.getElementById("ct_cap").value)||20,
    documentos, notas:document.getElementById("ct_notas").value };
  try{ const r=await post("/contratos/contratistas/guardar",body);
    if(!r.ok){toast(r.msg,true);return;}
    cerrarModal("modal-contratista"); toast(r.msg); VISTAS.contratos("contratistas");
  }catch(e){ toast("Error",true); }
}
async function solicitarDocs(id){
  try{ const r=await post("/contratos/contratistas/solicitar_docs",{id}); toast(r.msg,!r.ok); }
  catch(e){ toast("Error",true); }
}
async function topesView(){
  const t = await api(`/contratos/topes?institucion_id=${ST.institucion_id}`);
  document.getElementById("con-cont").innerHTML = `
    <div class="kpis">
      <div class="kpi gold"><div class="kpi-ico">⚖️</div><div class="kpi-val sm">${money(t.tope_cop)}</div><div class="kpi-lbl">Tope régimen especial (20 SMMLV)</div></div>
      <div class="kpi"><div class="kpi-ico">💵</div><div class="kpi-val sm">${money(t.smmlv)}</div><div class="kpi-lbl">SMMLV vigente</div></div>
    </div>
    ${t.alertas.length?`<div class="digest"><div style="font-size:1.6rem">⚠️</div><div><b>Alertas de capacidad:</b><ul style="margin:4px 0 0;padding-left:18px">${t.alertas.map(a=>`<li class="small">${esc(a)}</li>`).join("")}</ul></div></div>`:""}
    <div class="card"><div class="card-head"><h3>Capacidad de contratación por proveedor</h3></div>
    <div class="tbl-scroll"><table>
      <thead><tr><th>Contratista</th><th style="text-align:right">Capacidad anual</th><th style="text-align:right">Contratado</th><th style="text-align:right">Disponible</th><th>% usado</th></tr></thead>
      <tbody>${t.contratistas.map(c=>`<tr>
        <td><b>${esc(c.nombre)}</b><div class="small muted">${c.capacidad_smmlv} SMMLV</div></td>
        <td style="text-align:right">${money(c.capacidad_cop)}</td><td style="text-align:right">${money(c.acumulado)}</td>
        <td style="text-align:right"><b style="color:${c.disponible>0?'var(--green)':'var(--red)'}">${money(c.disponible)}</b></td>
        <td><div class="prog" style="display:inline-block;width:100px;vertical-align:middle"><div class="prog-fill" style="width:${Math.min(100,c.pct)}%;background:${c.pct>=80?'var(--red)':c.pct>=50?'var(--orange)':'var(--green)'}"></div></div> ${c.pct}%</td></tr>`).join("")}
      </tbody></table></div></div>
    ${ST.perfil.rol==="rector"||ST.perfil.rol==="contador"?`<div class="card"><div class="card-body">
      <b class="small">Parametrizar SMMLV</b> <span class="small muted">(cuando cambia el salario mínimo anual)</span>
      <div style="display:flex;gap:8px;margin-top:8px;max-width:340px">
        <input type="number" id="smmlv_new" value="${t.smmlv}" style="flex:1;padding:8px;border:1px solid var(--border);border-radius:8px">
        <button class="btn btn-primary btn-sm" onclick="guardarSMMLV()">💾 Actualizar</button>
      </div></div></div>`:""}
    <div class="legal-note">⚖️ <b>Referencia legal:</b> ${esc(t.referencia)}. El sistema impide crear contratos por FSE que superen el tope o la capacidad del contratista — evitando el fraccionamiento indebido y las sanciones fiscales.</div>`;
}
async function guardarSMMLV(){
  const valor=parseFloat(document.getElementById("smmlv_new").value)||0;
  try{ const r=await post("/contratos/topes/smmlv",{valor}); toast(r.msg,!r.ok); if(r.ok) VISTAS.contratos("topes"); }
  catch(e){ toast("Error",true); }
}

/* ═══════════ VISTA: SECRETARÍA ═══════════ */
VISTAS.secretaria = async function(){
  loading();
  try{
    const muni = encodeURIComponent(ST.perfil.municipio||"San Pablo");
    const d = await api(`/territorio/secretaria?municipio=${muni}`);
    window._secData = d;
    let rows = d.colegios.map(c=>`
      <tr onclick="verInstitucion(${c.institucion_id})" style="cursor:pointer">
        <td><div class="flex-cell"><div class="avatar-sm">${ini(c.nombre.replace("I.E.",""))}</div><div><b>${esc(c.nombre)}</b><div class="small muted">${esc(c.sector||"")} · DANE ${esc(c.codigo_dane||"")}</div></div></div></td>
        <td style="text-align:center">${c.n_estudiantes}</td>
        <td style="text-align:center">${c.n_docentes||"—"}</td>
        <td><div class="flex-cell"><div class="prog" style="flex:1"><div class="prog-fill" style="width:${c.pct_riesgo||0}%;background:${c.pct_riesgo>=20?'var(--red)':c.pct_riesgo>=10?'var(--orange)':'var(--gold)'}"></div></div><span class="badge ${c.pct_riesgo>=20?'b-red':c.pct_riesgo>=10?'b-orange':'b-green'}">${c.pct_riesgo||0}%</span></div></td>
        <td><button class="btn btn-xs btn-primary" onclick="event.stopPropagation();verInstitucion(${c.institucion_id})">Entrar ▸</button></td></tr>`).join("");
    main(head(`Secretaría de Educación de ${d.municipio||ST.perfil.municipio}`, `${d.departamento||"Bolívar"} · vista consolidada de todas las instituciones del municipio`,
      `<button class="btn btn-sm" onclick="window.print()">🖨️ Imprimir</button>`)+`
      <div class="kpis">
        <div class="kpi"><div class="kpi-ico">🏫</div><div class="kpi-val">${d.kpis.n_colegios}</div><div class="kpi-lbl">Instituciones</div></div>
        <div class="kpi green"><div class="kpi-ico">👨‍🎓</div><div class="kpi-val">${d.kpis.n_estudiantes}</div><div class="kpi-lbl">Estudiantes</div></div>
        <div class="kpi red"><div class="kpi-ico">⚠️</div><div class="kpi-val">${d.kpis.en_riesgo||0}</div><div class="kpi-lbl">En riesgo</div></div>
        <div class="kpi purple"><div class="kpi-ico">👥</div><div class="kpi-val">${d.kpis.n_docentes||"—"}</div><div class="kpi-lbl">Docentes</div></div>
      </div>
      <div class="card"><div class="card-head"><h3>Instituciones del municipio</h3><span class="small muted">Clic en una para ver su personal completo, compras y contratos</span></div>
      <div class="tbl-scroll"><table><thead><tr><th>Institución</th><th style="text-align:center">Estudiantes</th><th style="text-align:center">Docentes</th><th>% en riesgo</th><th></th></tr></thead>
      <tbody>${rows||'<tr><td colspan="5" class="empty">Sin instituciones</td></tr>'}</tbody></table></div></div>
      ${d.censo?`<div class="digest"><div style="font-size:1.8rem">👦</div><div style="flex:1"><b>Censo juvenil:</b> ${d.censo.fuera_sistema||0} jóvenes fuera del sistema · ${d.censo.zonas_riesgo||0} en zonas de riesgo.
        <div class="small muted">Cruza tu población escolar con los jóvenes del territorio para cerrar la brecha de cobertura.</div></div>
        <button class="btn btn-primary" onclick="irVista('censo')">Ver censo →</button></div>`:""}`);
  }catch(e){ main(`<div class="empty">Error cargando la Secretaría</div>`); }
};

/* ═══════════ VISTA: INSTITUCIONES (drill-down Secretaría) ═══════════ */
VISTAS.instituciones = async function(){
  loading();
  try{
    const muni = encodeURIComponent(ST.perfil.municipio||"San Pablo");
    const d = await api(`/territorio/secretaria?municipio=${muni}`);
    main(head("Instituciones", "Cada colegio tiene su propio dominio · clic para ver todo su personal, hojas de vida, compras y contratos")+`
      <div class="grid-cards">
      ${d.colegios.map(c=>`
        <div class="ie-card" onclick="verInstitucion(${c.institucion_id})">
          <div class="ie-color" style="background:${c.color||'#0E7C86'}"></div>
          <div class="ie-body">
            <b>${esc(c.nombre)}</b>
            <div class="small muted" style="margin:4px 0">${esc(c.sector||"")}</div>
            ${c.dominio?`<div class="dominio">${esc(c.dominio)}</div>`:""}
            <div style="display:flex;gap:12px;margin-top:10px">
              <div><div style="font-size:1.2rem;font-weight:800">${c.n_estudiantes}</div><div class="small muted">estudiantes</div></div>
              <div><div style="font-size:1.2rem;font-weight:800;color:var(--red)">${c.pct_riesgo||0}%</div><div class="small muted">en riesgo</div></div>
            </div>
            <button class="btn btn-sm btn-primary" style="width:100%;margin-top:10px">🔍 Ver institución</button>
          </div>
        </div>`).join("")}
      </div>`);
  }catch(e){ main(`<div class="empty">Error</div>`); }
};
async function verInstitucion(id){
  loading();
  try{
    const d = await api(`/territorio/institucion_detalle?institucion_id=${id}`);
    window._ieDetalle = d;
    const ROL_LBL={rector:"Rector(a)",coordinador:"Coordinador(a)",docente:"Docente",psicoorientacion:"Psicoorientación",auxiliar:"Contratación",contador:"Contador(a)",abogado:"Abogado(a)",vigilante:"Vigilante",servicios:"Servicios"};
    const personalRows = d.personal.map(p=>`<tr>
      <td><div class="flex-cell">${avatarCell(p.foto,p.nombre)}<div><b>${esc(p.nombre)}</b><div class="small muted">${esc(p.profesion||"")}</div></div></div></td>
      <td>${ROL_LBL[p.rol]||p.rol}<div class="small muted">${esc(p.area||"")}</div></td>
      <td style="text-align:center">${p.hv_score?`<div class="score-ring" style="--v:${p.hv_score};width:38px;height:38px;font-size:.72rem;margin:0 auto"><span>${p.hv_score}</span></div>`:'—'}</td>
      <td class="small">${esc(p.telefono||"—")}</td>
      <td>${["docente","coordinador","rector"].includes(p.rol)?`<button class="btn btn-xs btn-green" onclick="contactarDocente(${p.id},'${esc(p.nombre)}')">📱 Contactar</button>`:""}</td>
    </tr>`).join("");
    main(head(d.nombre, `${esc(d.municipio)}, ${esc(d.departamento)} · Rector: ${esc(d.rector||"—")}`,
      `<button class="btn" onclick="irVista('instituciones')">← Volver</button>`)+`
      <div class="card"><div class="card-body" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
        <div><span class="tn-dot" style="background:${d.color}"></span><b>Dominio propio:</b> <span class="dominio">${esc(d.dominio||"—")}</span>
          <div class="small muted" style="margin-top:4px">Módulos activos: ${(d.modulos||[]).map(m=>`<span class="mat-chip">${esc(m)}</span>`).join("")}</div></div>
        <div class="small muted">DANE ${esc(d.dane)} · ${esc(d.sector)}<br>📍 ${esc(d.direccion||"—")} · 📞 ${esc(d.telefono||"—")}</div>
      </div></div>
      <div class="kpis">
        <div class="kpi green"><div class="kpi-ico">👨‍🎓</div><div class="kpi-val">${d.kpis.estudiantes}</div><div class="kpi-lbl">Estudiantes</div></div>
        <div class="kpi purple"><div class="kpi-ico">👥</div><div class="kpi-val">${d.kpis.personal}</div><div class="kpi-lbl">Personal total</div></div>
        <div class="kpi red"><div class="kpi-ico">⚠️</div><div class="kpi-val">${d.kpis.pct_riesgo}%</div><div class="kpi-lbl">En riesgo</div></div>
        <div class="kpi orange"><div class="kpi-ico">📤</div><div class="kpi-val sm">${money(d.kpis.fse_egresos)}</div><div class="kpi-lbl">FSE ejecutado</div></div>
      </div>
      ${d.top_hojas_vida.length?`<div class="card"><div class="card-head"><h3>⭐ Mejores hojas de vida (para vacantes)</h3></div><div class="card-body" style="display:flex;gap:10px;flex-wrap:wrap">
        ${d.top_hojas_vida.map(p=>`<div style="display:flex;align-items:center;gap:8px;background:#F8FAFC;border:1px solid var(--border);border-radius:10px;padding:8px 12px">
          ${avatarCell(p.foto,p.nombre)}<div><b class="small">${esc(p.nombre)}</b><div class="small muted">${esc(p.area||p.rol)}</div></div>
          <div class="score-ring" style="--v:${p.hv_score};width:40px;height:40px;font-size:.74rem"><span>${p.hv_score}</span></div></div>`).join("")}
      </div></div>`:""}
      <div class="card"><div class="card-head"><h3>Personal completo (de rectoría a vigilancia)</h3><span class="small muted">${d.personal.length} personas</span></div>
      <div class="tbl-scroll" style="max-height:420px;overflow-y:auto"><table><thead><tr><th>Persona</th><th>Cargo</th><th style="text-align:center">HV</th><th>Contacto</th><th></th></tr></thead>
      <tbody>${personalRows}</tbody></table></div></div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
        <div class="card"><div class="card-head"><h3>🛒 Compras recientes (FSE)</h3></div><div class="tbl-scroll"><table><thead><tr><th>Concepto</th><th style="text-align:right">Valor</th></tr></thead><tbody>
          ${d.compras.map(c=>`<tr><td class="small"><b>${esc(c.concepto)}</b><div class="muted">${esc(c.proveedor||"")} · ${esc(c.fecha)}</div></td><td style="text-align:right">${money(c.valor)}</td></tr>`).join("")||'<tr><td colspan="2" class="empty">Sin compras</td></tr>'}
        </tbody></table></div></div>
        <div class="card"><div class="card-head"><h3>📜 Contratos</h3></div><div class="tbl-scroll"><table><thead><tr><th>N°</th><th>Estado</th><th style="text-align:right">Valor</th></tr></thead><tbody>
          ${d.contratos.map(c=>`<tr><td class="small"><b>${esc(c.numero)}</b><div class="muted">${esc(c.contratista||"")}</div></td><td><span class="badge b-blue">${esc(c.estado)}</span></td><td style="text-align:right">${money(c.valor)}</td></tr>`).join("")||'<tr><td colspan="3" class="empty">Sin contratos</td></tr>'}
        </tbody></table></div></div>
      </div>
      <div class="legal-note">🏛️ Este es el poder de la Secretaría: <b>ver dentro de cada colegio</b> — su gente, sus hojas de vida, sus compras y contratos — sin salir de la plataforma. Cada institución opera con SU dominio, pero todo está interconectado.</div>`);
  }catch(e){ main(`<div class="empty">Error cargando la institución</div>`); }
};
function contactarDocente(pid, nombre){
  const asunto=prompt(`Asunto del mensaje a ${nombre}:`,"Invitación a formación docente");
  if(asunto===null) return;
  const contenido=prompt("Mensaje:","La Secretaría de Educación le extiende una invitación...");
  if(!contenido) return;
  post("/territorio/mensaje",{personal_id:pid,asunto,contenido}).then(r=>toast(r.msg,!r.ok)).catch(()=>toast("Error",true));
}

/* ═══════════ VISTA: CENSO ═══════════ */
VISTAS.censo = async function(tab){
  loading();
  try{
    const t=tab||"resumen";
    const muni = ST.perfil.municipio?`&municipio=${encodeURIComponent(ST.perfil.municipio)}`:"";
    const d = await api(`/censo/resumen?${muni.replace(/^&/,"")}`);
    main(head("Censo Juvenil Territorial", "Jóvenes 12-17 años DENTRO y FUERA del sistema · el poder de la Secretaría para cerrar la brecha")+`
      <div class="kpis">
        <div class="kpi"><div class="kpi-ico">👦</div><div class="kpi-val">${d.total||0}</div><div class="kpi-lbl">Jóvenes censados</div></div>
        <div class="kpi green"><div class="kpi-ico">🏫</div><div class="kpi-val">${d.estudian||0}</div><div class="kpi-lbl">Estudiando</div></div>
        <div class="kpi red"><div class="kpi-ico">🚸</div><div class="kpi-val">${d.fuera_sistema||0}</div><div class="kpi-lbl">Fuera del sistema</div></div>
        <div class="kpi orange"><div class="kpi-ico">🛡️</div><div class="kpi-val">${d.zonas_riesgo||0}</div><div class="kpi-lbl">En zonas de riesgo</div></div>
      </div>
      <div class="subtabs">
        ${[["resumen","📊 Motivos de deserción"],["zonas","📍 Zonas prioritarias"],["jovenes","👥 Jóvenes (gestión)"],["cruce","🔄 Cruce con instituciones"]].map(([k,l])=>
          `<button class="subtab ${t===k?'active':''}" onclick="VISTAS.censo('${k}')">${l}</button>`).join("")}</div>
      <div id="censo-cont"></div>`);
    if(t==="resumen") censoResumen(d);
    if(t==="zonas") censoZonas();
    if(t==="jovenes") censoJovenes();
    if(t==="cruce") censoCruce();
  }catch(e){ main(`<div class="empty">Error cargando el censo</div>`); }
};
function censoResumen(d){
  const motivos = d.motivos||{};
  const max = Math.max(1,...Object.values(motivos));
  document.getElementById("censo-cont").innerHTML = `
    <div class="card"><div class="card-head"><h3>¿Por qué los jóvenes no estudian?</h3></div><div class="card-body">
      ${Object.entries(motivos).sort((a,b)=>b[1]-a[1]).map(([m,n])=>`
        <div class="zona-bar"><div class="lbl">${esc(m)}</div><div class="bar"><div class="fill" style="width:${100*n/max}%"></div></div><b>${n}</b></div>`).join("")||'<div class="empty">Sin datos</div>'}
    </div></div>
    ${d.alertas_tipos?`<div class="card"><div class="card-head"><h3>🛡️ Alertas de protección (SAT)</h3></div><div class="card-body">
      ${Object.entries(d.alertas_tipos).sort((a,b)=>b[1]-a[1]).map(([a,n])=>`<span class="badge b-red" style="margin:3px">${esc(a)}: ${n}</span>`).join("")}
    </div></div>`:""}
    <div class="legal-note">👦 Este censo cruza el SIMAT con los jóvenes del territorio: identifica quién dejó de estudiar y por qué, para que la Secretaría actúe con estrategias focalizadas.</div>`;
}
async function censoZonas(){
  const muni = ST.perfil.municipio?`municipio=${encodeURIComponent(ST.perfil.municipio)}`:"";
  const zonas = await api(`/censo/zonas?${muni}`);
  const max=Math.max(1,...zonas.map(z=>z.fuera));
  document.getElementById("censo-cont").innerHTML = `
    <div class="card"><div class="card-head"><h3>Barrios/veredas con más jóvenes fuera del sistema</h3><span class="small muted">dónde priorizar cobertura</span></div><div class="card-body">
      ${zonas.map(z=>`<div class="zona-bar">
        <div class="lbl">${esc(z.barrio_vereda)} <span class="small muted">(${esc(z.zona)})</span></div>
        <div class="bar"><div class="fill" style="width:${100*z.fuera/max}%"></div></div>
        <b>${z.fuera}</b> <span class="small muted">de ${z.total} · ${z.pct_fuera}%</span>
        ${z.alertas?`<span class="badge b-red">🛡️ ${z.alertas}</span>`:""}
      </div>`).join("")||'<div class="empty">Sin datos</div>'}
    </div></div>
    <div class="legal-note">📍 Ranking de focalización: el barrio/vereda con la barra más larga es donde la Secretaría debe abrir cupos, transporte o jornadas — decisión basada en datos, no en intuición.</div>`;
}

/* ═══════════ VISTA: MINISTERIO ═══════════ */
VISTAS.ministerio = async function(){
  loading();
  try{
    const [d, tend] = await Promise.all([
      api(`/territorio/ministerio`),
      api(`/territorio/ministerio_tendencia`),
    ]);
    const maxT=Math.max(1,...tend.tendencia.map(x=>x.pct));
    const muniRows=(d.municipios||[]).map(m=>`<tr>
      <td><b>${esc(m.municipio)}</b><div class="small muted">${esc(m.departamento||"")}</div></td>
      <td style="text-align:center">${m.n_colegios||m.colegios||"—"}</td>
      <td style="text-align:center">${m.n_estudiantes||m.estudiantes||"—"}</td>
      <td><div class="flex-cell"><div class="prog" style="flex:1"><div class="prog-fill" style="width:${m.pct_riesgo||0}%;background:${m.pct_riesgo>=20?'var(--red)':'var(--orange)'}"></div></div><span class="badge ${m.pct_riesgo>=20?'b-red':'b-orange'}">${m.pct_riesgo||0}%</span></div></td></tr>`).join("");
    main(head("Panorama Nacional", "Ministerio de Educación · inteligencia territorial en tiempo real")+`
      <div class="kpis">
        <div class="kpi"><div class="kpi-ico">🗺️</div><div class="kpi-val">${d.kpis.n_municipios||d.kpis.municipios||"—"}</div><div class="kpi-lbl">Municipios</div></div>
        <div class="kpi"><div class="kpi-ico">🏫</div><div class="kpi-val">${d.kpis.n_colegios||d.kpis.colegios||"—"}</div><div class="kpi-lbl">Instituciones</div></div>
        <div class="kpi green"><div class="kpi-ico">👨‍🎓</div><div class="kpi-val">${d.kpis.n_estudiantes||d.kpis.estudiantes||"—"}</div><div class="kpi-lbl">Estudiantes</div></div>
        <div class="kpi red"><div class="kpi-ico">⚠️</div><div class="kpi-val">${d.kpis.en_riesgo||"—"}</div><div class="kpi-lbl">En riesgo</div></div>
      </div>
      <div class="card"><div class="card-head"><h3>📈 Tendencia nacional de asistencia (últimas 10 semanas)</h3></div><div class="card-body">
        <div class="mini-spark">${tend.tendencia.map(x=>`<div class="sp" style="height:${Math.max(8,100*x.pct/maxT)}%"><span>${x.pct}%</span></div>`).join("")}</div>
        <div class="small muted" style="margin-top:8px">Cada barra es una semana. La asistencia agregada es el mejor predictor temprano de deserción a nivel país.</div>
      </div></div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
        <div class="card"><div class="card-head"><h3>Por departamento</h3></div><div class="tbl-scroll"><table><thead><tr><th>Departamento</th><th>% asistencia</th></tr></thead><tbody>
          ${tend.departamentos.map(dd=>`<tr><td><b>${esc(dd.departamento)}</b></td><td><span class="badge ${dd.pct>=90?'b-green':dd.pct>=85?'b-orange':'b-red'}">${dd.pct}%</span> <span class="small muted">${dd.registros} regs</span></td></tr>`).join("")}
        </tbody></table></div></div>
        <div class="card"><div class="card-head"><h3>Por municipio</h3></div><div class="tbl-scroll"><table><thead><tr><th>Municipio</th><th style="text-align:center">Colegios</th><th style="text-align:center">Est.</th><th>Riesgo</th></tr></thead><tbody>
          ${muniRows||'<tr><td colspan="4" class="empty">Sin datos</td></tr>'}
        </tbody></table></div></div>
      </div>
      <div class="legal-note">🇨🇴 <b>Aporte al Plan Nacional de Desarrollo:</b> el Ministerio ve, municipio por municipio, dónde se está perdiendo la batalla contra la deserción — y puede dirigir recursos donde más se necesitan, con evidencia en tiempo real.</div>`);
  }catch(e){ main(`<div class="empty">Error cargando el panorama nacional</div>`); }
};

/* ═══════════ VISTA: DATOS & IA ═══════════ */
VISTAS.datos = async function(tab){
  if(tab==="cerebro" || tab==="datasets"){
    loading();
    main(head("Datos & IA — el cerebro de datos GyverLabs","Qué aprendió el modelo y cómo se comparten los datos")+`
      <div class="subtabs">
        ${[["resumen","📊 Log y modelo"],["cerebro","🧠 Qué aprendió"],["datasets","📦 Exportar datos"]].map(([k,l])=>
          `<button class="subtab ${tab===k?'active':''}" onclick="VISTAS.datos('${k}')">${l}</button>`).join("")}</div>
      <div id="datos-cont"><div class="empty">Cargando…</div></div>`);
    try{ if(tab==="cerebro") await cerebroView(); else await datasetsView(); }
    catch(e){ document.getElementById("datos-cont").innerHTML='<div class="empty">Error</div>'; }
    return;
  }
  loading();
  try{
    const res = await api(`/metadatos/resumen`);
    window._datosRes = res;
    const porEvento = Object.entries(res.log.por_evento).sort((a,b)=>b[1]-a[1]);
    const m = res.modelo;
    main(head("Datos & IA — el cerebro de datos GyverLabs", "El mismo motor de captura de metadatos del sistema de trading, aplicado a la educación")+`
      <div class="subtabs">
        <button class="subtab active" onclick="VISTAS.datos()">📊 Log y modelo</button>
        <button class="subtab" onclick="VISTAS.datos('cerebro')">🧠 Qué aprendió</button>
        <button class="subtab" onclick="VISTAS.datos('datasets')">📦 Exportar datos</button>
      </div>
      <div class="hero-datos">
        <h2>🧠 Un log unificado que aprende de cada acción</h2>
        <p>Cada asistencia, nota, alerta, contrato y firma genera un <b>evento</b> en el log <code>${esc(res.esquema.nombre)}</code>. Cada estudiante genera <b>snapshots semanales</b> con features y el score del modelo (el "brain"). ${esc(res.esquema.paralelo_trading)}</p>
        <div class="hero-stats">
          <div class="hero-stat"><b>${res.log.total_eventos.toLocaleString("es-CO")}</b><span>eventos capturados</span></div>
          <div class="hero-stat"><b>${res.dataset.filas.toLocaleString("es-CO")}</b><span>filas de entrenamiento</span></div>
          <div class="hero-stat"><b>${res.dataset.estudiantes}</b><span>estudiantes × ${res.dataset.semanas} semanas</span></div>
          <div class="hero-stat"><b>${res.dataset.con_target.toLocaleString("es-CO")}</b><span>con target verificable</span></div>
        </div>
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
        <div class="card"><div class="card-head"><h3>📡 Log de eventos (auditoría total)</h3></div><div class="card-body">
          ${porEvento.map(([ev,n])=>`<div class="imp-bar"><div class="lbl">${esc(ev)}</div><div class="bar"><div class="fill" style="width:${100*n/porEvento[0][1]}%"></div></div><b>${n}</b></div>`).join("")}
          <div class="small muted" style="margin-top:8px">Archivo: <code>${esc(res.log.archivo)}</code> · ${(res.log.bytes/1024).toFixed(1)} KB</div>
        </div></div>
        <div class="card"><div class="card-head"><h3>🎯 Dataset de entrenamiento</h3></div><div class="card-body">
          <p class="small">Serie <b>estudiante-semana</b> con ${res.dataset.features.length} variables predictoras y el target <span class="badge b-blue">target_ausencia_prox_sem</span> (¿faltará la próxima semana?) — etiqueta de <b>futuro observable</b>, igual que en la auditoría de trading.</p>
          <div style="margin:8px 0">${res.dataset.features.map(f=>`<span class="mat-chip">${esc(f)}</span>`).join("")}</div>
        </div></div>
      </div>

      <div class="card"><div class="card-head"><h3>📦 Exportar para tus modelos</h3></div><div class="card-body" style="display:flex;gap:10px;flex-wrap:wrap">
        <button class="btn" onclick="window.open('${API}/metadatos/exportar/eventos')">📄 Log de eventos (JSONL)</button>
        <button class="btn" onclick="window.open('${API}/metadatos/exportar/dataset')">📊 Dataset tabular — LightGBM (CSV)</button>
        <button class="btn" onclick="window.open('${API}/metadatos/exportar/secuencias')">🔁 Secuencias — LSTM/Transformer (JSONL)</button>
      </div></div>

      <div class="card"><div class="card-head"><h3>🧠 Modelo de riesgo (LightGBM real)</h3><button class="btn btn-sm btn-primary" onclick="entrenarModelo()">🔄 Re-entrenar con datos actuales</button></div>
      <div class="card-body" id="modelo-cont">${m?pintarModelo(m):'<div class="empty">Aún no entrenado. Pulsa "Re-entrenar".</div>'}</div></div>

      <div class="card"><div class="card-head"><h3>📤 Datos abiertos — datos.gov.co</h3></div><div class="card-body">
        <div id="datosgov-cont"><div class="empty">Cargando ficha…</div></div>
      </div></div>`);
    cargarDatosGov();
  }catch(e){ main(`<div class="empty">Error cargando Datos & IA</div>`); }
};
function pintarModelo(m){
  const imp = m.importancia_variables||{};
  const maxImp = Math.max(1,...Object.values(imp));
  return `<div class="kpis" style="margin-bottom:14px">
      <div class="kpi purple"><div class="kpi-ico">🎯</div><div class="kpi-val sm">${m.auc_roc}</div><div class="kpi-lbl">AUC-ROC</div></div>
      <div class="kpi"><div class="kpi-ico">✓</div><div class="kpi-val sm">${(m.accuracy*100).toFixed(0)}%</div><div class="kpi-lbl">Exactitud</div></div>
      <div class="kpi orange"><div class="kpi-ico">🔍</div><div class="kpi-val sm">${(m.precision*100).toFixed(0)}%</div><div class="kpi-lbl">Precisión</div></div>
      <div class="kpi green"><div class="kpi-ico">📥</div><div class="kpi-val sm">${(m.recall*100).toFixed(0)}%</div><div class="kpi-lbl">Recall</div></div>
    </div>
    <b class="small">Importancia de variables (qué mira el modelo)</b>
    <div style="margin-top:8px">${Object.entries(imp).sort((a,b)=>b[1]-a[1]).map(([k,v])=>`<div class="imp-bar"><div class="lbl">${esc(k)}</div><div class="bar"><div class="fill" style="width:${100*v/maxImp}%"></div></div><b>${v}</b></div>`).join("")}</div>
    <div class="small muted" style="margin-top:8px">Entrenado con ${m.n_train} filas · validado con ${m.n_test} · umbral de operación calibrado: ${m.umbral_operacion}. En producción: ~30 variables, calibración por institución y SHAP para explicar cada caso.</div>`;
}
async function entrenarModelo(){
  document.getElementById("modelo-cont").innerHTML='<div class="empty">🧠 Entrenando LightGBM con los datos actuales del sistema…</div>';
  try{ const r=await post("/metadatos/entrenar",{});
    if(!r.ok){ document.getElementById("modelo-cont").innerHTML=`<div class="empty">${esc(r.msg)}</div>`; return; }
    toast(r.msg);
    document.getElementById("modelo-cont").innerHTML=pintarModelo(r.metricas);
  }catch(e){ toast("Error al entrenar",true); }
}
async function cargarDatosGov(){
  const [ficha, pubs] = await Promise.all([ api(`/metadatos/datosgov`), api(`/metadatos/publicaciones`) ]);
  window._fichaDatos = ficha;
  document.getElementById("datosgov-cont").innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap">
      <div style="flex:1;min-width:280px">
        <b>${esc(ficha.titulo)}</b>
        <p class="small muted" style="margin:6px 0">${esc(ficha.descripcion)}</p>
        <div>${ficha.palabras_clave.map(k=>`<span class="mat-chip">🏷️ ${esc(k)}</span>`).join("")}</div>
        <div class="small muted" style="margin-top:8px">📊 ${ficha.registros.toLocaleString("es-CO")} registros · 📜 ${esc(ficha.licencia)} · 🔄 ${esc(ficha.frecuencia_actualizacion)} · 📍 ${esc(ficha.cobertura_geografica)}</div>
      </div>
      <button class="btn btn-gold" onclick="abrirModalPublicar()">📤 Publicar en datos.gov.co</button>
    </div>
    ${pubs.length?`<div style="margin-top:16px"><b class="small">Historial de publicaciones</b>
      <div class="tbl-scroll" style="margin-top:8px"><table><thead><tr><th>Dataset</th><th style="text-align:center">Registros</th><th>Fecha</th><th>URL</th></tr></thead><tbody>
        ${pubs.map(p=>`<tr><td class="small"><b>${esc(p.titulo)}</b><div class="muted">${esc(p.responsable||"")}</div></td>
          <td style="text-align:center">${p.registros.toLocaleString("es-CO")}</td><td class="small">${esc(p.fecha)}</td>
          <td><a href="${p.url}" target="_blank" class="btn btn-xs">🔗 Ver</a></td></tr>`).join("")}
      </tbody></table></div></div>`:""}
    <div class="legal-note" style="margin-top:12px">🔒 Solo se publica información <b>anonimizada</b> (códigos hash EST-xxxx irreversibles, Ley 1581 de 2012). Cero datos personales. Colombia obtiene datos abiertos de calidad para investigación y política pública.</div>`;
}
function abrirModalPublicar(){
  const f=window._fichaDatos;
  document.getElementById("pub_titulo").value=f.titulo;
  document.getElementById("pub_desc").value=f.descripcion;
  document.getElementById("pub_resp").value=f.responsable;
  abrirModal("modal-publicar");
}
async function publicarDatos(){
  const body={ titulo:document.getElementById("pub_titulo").value, descripcion:document.getElementById("pub_desc").value,
    responsable:document.getElementById("pub_resp").value };
  try{ const r=await post("/metadatos/publicar",body);
    if(!r.ok){toast(r.msg,true);return;}
    cerrarModal("modal-publicar"); toast(r.msg);
    if(r.url) setTimeout(()=>{ if(confirm("Dataset publicado (simulado). ¿Abrir la URL simulada de datos.gov.co?\n\n"+r.url)) window.open(r.url); },300);
    cargarDatosGov();
  }catch(e){ toast("Error al publicar",true); }
}

/* ═══════════ VISTA: SÚPER ADMIN — RESUMEN ═══════════ */
VISTAS.adminresumen = async function(){
  loading();
  try{
    const r = await api(`/admin/resumen`);
    main(head("Red GyverLabs", "Súper Administrador · el negocio completo en una pantalla")+`
      <div class="hero-datos">
        <h2>🌐 Un solo código · ${r.dominios} dominios</h2>
        <p>Cada secretaría y cada colegio ve <b>SU propio sistema</b> con su dominio, sus colores y su marca — percepción "a la medida". Pero internamente todo vive interconectado en una sola plataforma que tú administras. Así se escala a miles de instituciones sin reescribir nada.</p>
        <div class="hero-stats">
          <div class="hero-stat"><b>${r.colegios}</b><span>colegios</span></div>
          <div class="hero-stat"><b>${r.secretarias}</b><span>secretarías</span></div>
          <div class="hero-stat"><b>${r.dominios}</b><span>dominios activos</span></div>
          <div class="hero-stat"><b>${r.estudiantes.toLocaleString("es-CO")}</b><span>estudiantes</span></div>
        </div>
      </div>
      <div class="kpis">
        <div class="kpi"><div class="kpi-ico">🏫</div><div class="kpi-val">${r.colegios}</div><div class="kpi-lbl">Colegios (tenants)</div></div>
        <div class="kpi orange"><div class="kpi-ico">🏛️</div><div class="kpi-val">${r.secretarias}</div><div class="kpi-lbl">Secretarías</div></div>
        <div class="kpi purple"><div class="kpi-ico">👥</div><div class="kpi-val">${r.personal}</div><div class="kpi-lbl">Personal en la red</div></div>
        <div class="kpi red"><div class="kpi-ico">⚠️</div><div class="kpi-val">${r.en_riesgo}</div><div class="kpi-lbl">Estudiantes en riesgo</div></div>
      </div>
      <div class="card"><div class="card-body" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px">
        <div><h3 style="color:var(--navy)">Gestiona los tenants</h3><p class="small muted">Crea nuevas secretarías y colegios, asígnales dominio y módulos, suspéndelos o actívalos.</p></div>
        <button class="btn btn-primary" onclick="irVista('tenants')">🌐 Ir a Tenants y dominios →</button>
      </div></div>
      <div class="legal-note">💡 El modelo de negocio: interno (una secretaría con todos sus colegios interconectados) o externo (cada colegio contrata su propio dominio). El mismo código sirve a ambos — se activa por configuración del tenant.</div>`);
  }catch(e){ main(`<div class="empty">Error</div>`); }
};

/* ═══════════ VISTA: TENANTS (súper admin) ═══════════ */
VISTAS.tenants = async function(){
  loading();
  try{
    const tenants = await api(`/admin/tenants`);
    window._tenants = tenants;
    const cols = tenants.filter(t=>t.tipo==="colegio");
    const secs = tenants.filter(t=>t.tipo==="secretaria");
    const fila = t=>`<tr>
      <td><div class="flex-cell">
        ${t.logo?`<img src="${t.logo}" style="width:34px;height:34px;object-fit:contain;border-radius:7px;background:#fff;border:1px solid var(--border);padding:2px">`:`<span class="tn-dot" style="background:${t.color}"></span>`}
        <div>${t.tipo==="secretaria"?"🏛️":"🏫"} <b>${esc(t.nombre)}</b>${t.dane?`<div class="small muted">DANE ${esc(t.dane)}</div>`:""}</div></div></td>
      <td><span class="dominio">${esc(t.dominio)}</span></td>
      <td class="small">${esc(t.municipio||"")}<div class="muted">${esc(t.departamento||"")}</div></td>
      <td>${(t.modulos||[]).map(m=>`<span class="mat-chip">${esc(m)}</span>`).join("")}</td>
      <td style="text-align:center">${t.n_estudiantes!=null?t.n_estudiantes:"—"}</td>
      <td>${t.estado==="activo"?'<span class="badge b-green">Activo</span>':'<span class="badge b-gray">Suspendido</span>'}</td>
      <td style="white-space:nowrap">
        <button class="btn btn-xs btn-gold" onclick="abrirBranding(${t.id})" title="Logo y marca de la institución">🎨 Marca</button>
        ${t.estado==="activo"?`<button class="btn btn-xs btn-danger" onclick="cambiarEstadoTenant(${t.id},'suspendido')">⏸️</button>`:`<button class="btn btn-xs btn-green" onclick="cambiarEstadoTenant(${t.id},'activo')">▶️</button>`}</td>
    </tr>`;
    main(head("Tenants y dominios", `${tenants.length} tenants · cada uno con su dominio propio`,
      `<button class="btn btn-primary" onclick="abrirModalTenant('colegio')">➕ Nueva institución</button>
       <button class="btn btn-gold" onclick="abrirModalTenant('secretaria')">➕ Nueva secretaría</button>`)+`
      <div class="card"><div class="card-head"><h3>🏛️ Secretarías de Educación</h3><span class="small muted">${secs.length}</span></div>
      <div class="tbl-scroll"><table><thead><tr><th>Nombre</th><th>Dominio</th><th>Ubicación</th><th>Módulos</th><th style="text-align:center">Est.</th><th>Estado</th><th></th></tr></thead>
      <tbody>${secs.map(fila).join("")||'<tr><td colspan="7" class="empty">Sin secretarías</td></tr>'}</tbody></table></div></div>
      <div class="card"><div class="card-head"><h3>🏫 Colegios (instituciones)</h3><span class="small muted">${cols.length}</span></div>
      <div class="tbl-scroll"><table><thead><tr><th>Nombre</th><th>Dominio</th><th>Ubicación</th><th>Módulos</th><th style="text-align:center">Est.</th><th>Estado</th><th></th></tr></thead>
      <tbody>${cols.map(fila).join("")||'<tr><td colspan="7" class="empty">Sin colegios</td></tr>'}</tbody></table></div></div>
      <div class="legal-note">🌐 Cada fila es un <b>tenant</b> con su dominio. En producción, crear un tenant aprovisiona su subdominio (Cloudflare), su configuración de marca y su espacio de datos aislado — todo desde este panel, sin tocar código.</div>`);
  }catch(e){ main(`<div class="empty">Error</div>`); }
};
function abrirModalTenant(tipo){
  document.getElementById("tn_tipo").value=tipo;
  document.getElementById("tenant-title").textContent = tipo==="secretaria"?"➕ Nueva Secretaría de Educación":"➕ Nueva institución (colegio)";
  document.getElementById("tn_campos_colegio").style.display = tipo==="colegio"?"block":"none";
  document.getElementById("tn_extra_colegio").style.display = tipo==="colegio"?"grid":"none";
  document.getElementById("tn_nota").style.display = tipo==="colegio"?"block":"none";
  ["tn_nombre","tn_dane","tn_rector","tn_muni","tn_dominio"].forEach(id=>document.getElementById(id).value="");
  window._tnLogo=null;
  const lp=document.getElementById("tn_logo_prev"); if(lp) lp.innerHTML='<span class="small muted">—</span>';
  const lw=document.getElementById("tn_logo_wrap"); if(lw) lw.style.display = tipo==="colegio"?"block":"none";
  document.getElementById("tn_dom_wrap").style.display = tipo==="colegio"?"block":"none";
  document.getElementById("tn_depto").value="Bolívar";
  abrirModal("modal-tenant");
}
async function guardarTenant(){
  const tipo=document.getElementById("tn_tipo").value;
  try{
    let r;
    if(tipo==="secretaria"){
      r=await post("/admin/tenants/secretaria",{municipio:document.getElementById("tn_muni").value,departamento:document.getElementById("tn_depto").value});
    }else{
      r=await post("/admin/tenants/institucion",{
        nombre:document.getElementById("tn_nombre").value, dane:document.getElementById("tn_dane").value,
        municipio:document.getElementById("tn_muni").value, departamento:document.getElementById("tn_depto").value,
        sector:document.getElementById("tn_sector").value, rector:document.getElementById("tn_rector").value,
        color:document.getElementById("tn_color").value,
        logo: window._tnLogo||null,
        dominio:document.getElementById("tn_dominio").value.trim()||null });
    }
    if(!r.ok){toast(r.msg,true);return;}
    cerrarModal("modal-tenant"); toast(r.msg); VISTAS.tenants();
  }catch(e){ toast("Error al crear el tenant",true); }
}
async function cambiarEstadoTenant(id,estado){
  try{ const r=await post("/admin/tenants/estado",{tenant_id:id,estado}); toast(r.msg,!r.ok); if(r.ok) VISTAS.tenants(); }
  catch(e){ toast("Error",true); }
}

/* ═══════════════════════════════════════════════════════════════════
   V3 — FUNCIONES NUEVAS (campana, mi perfil, dashboards, comunicados,
   gestión de estudiantes, cortes, plan, contratos coedit, censo)
   ═══════════════════════════════════════════════════════════════════ */

/* ── CAMPANA DE NOTIFICACIONES (todos los perfiles con personal_id) ── */
async function cargarCampana(){
  if(!ST.perfil.personal_id) return;
  try{
    const b = await api(`/comunicados/bandeja?personal_id=${ST.perfil.personal_id}`);
    window._bandeja = b;
    const badge = document.getElementById("badge-campana");
    if(b.no_leidas>0){ badge.textContent=b.no_leidas; badge.classList.remove("oculto"); }
    else badge.classList.add("oculto");
  }catch(e){}
}
function toggleCampana(){
  const panel = document.getElementById("panel-campana");
  if(panel.classList.contains("oculto")){ pintarCampana(); panel.classList.remove("oculto"); }
  else panel.classList.add("oculto");
}
function pintarCampana(){
  const b = window._bandeja || {no_leidas:0, notificaciones:[]};
  document.getElementById("panel-campana").innerHTML = `
    <div class="campana-head"><span>🔔 Notificaciones ${b.no_leidas?`(${b.no_leidas} sin leer)`:""}</span>
      ${b.notificaciones.length?`<button class="btn btn-xs" onclick="marcarTodasNotif()">Marcar todas</button>`:""}</div>
    ${b.notificaciones.map(n=>`
      <div class="notif-item ${n.leida?'':'nueva'}" onclick="abrirNotif(${n.id})">
        <div class="nt">${esc(n.titulo)}</div>
        <div class="nm">${esc((n.mensaje||"").slice(0,110))}</div>
        <div class="nf">${esc(n.emisor)} · ${esc(n.fecha)}</div>
      </div>`).join("")||'<div class="empty" style="padding:20px">Sin notificaciones.</div>'}`;
}
async function abrirNotif(id){
  const n = (window._bandeja.notificaciones||[]).find(x=>x.id===id);
  try{ await post("/comunicados/leer",{id}); }catch(e){}
  if(n) alert("🔔 "+n.titulo+"\n\n"+n.mensaje+"\n\n— "+n.emisor+" · "+n.fecha);
  await cargarCampana(); pintarCampana();
}
async function marcarTodasNotif(){
  try{ await post("/comunicados/leer",{personal_id:ST.perfil.personal_id}); }catch(e){}
  await cargarCampana(); pintarCampana();
}
/* Notificaciones push del navegador + recordatorios del día */
async function pedirPermisoYNotificar(){
  if(!ST.perfil.personal_id) return;
  try{
    if("Notification" in window && Notification.permission==="default"){
      await Notification.requestPermission();
    }
    const rec = await api(`/aula/recordatorios?personal_id=${ST.perfil.personal_id}`);
    rec.slice(0,3).forEach((r,i)=>{
      const txt = `${r.cuando}${r.hora?" "+r.hora:""}: ${r.titulo}`;
      if("Notification" in window && Notification.permission==="granted"){
        setTimeout(()=>{ try{ new Notification("⏰ Recordatorio GyverLabs", {body:txt}); }catch(e){} }, 800*(i+1));
      }
    });
    if(rec.length){ setTimeout(()=>toast(`⏰ Tienes ${rec.length} vencimiento(s) próximo(s). Revisa tu calendario.`), 500); }
  }catch(e){}
}

/* ── VISTA: MI PERFIL (docente edita su propia hoja de vida) ── */
VISTAS.miperfil = async function(){
  loading();
  try{
    const hv = await api(`/academico/personal/hoja_vida?personal_id=${ST.perfil.personal_id}`);
    window._hv = hv;
    const lista=(arr,pid)=>arr.map((x,i)=>`<div class="check-row"><span style="flex:1">${esc(x)}</span><button class="btn btn-xs btn-danger" onclick="window._hv.${pid}.splice(${i},1);VISTAS.miperfil._repintar()">✕</button></div>`).join("");
    VISTAS.miperfil._repintar = function(){
      const h=window._hv;
      main(head("Mi perfil y hoja de vida", "Tú la construyes; rectoría la ve y también puede complementarla — queda sincronizada")+`
        <div class="card"><div class="card-body">
          <div style="display:flex;gap:16px;align-items:center;flex-wrap:wrap;margin-bottom:8px">
            <div style="position:relative">
              ${h.foto?`<img class="avatar-foto lg" src="${h.foto}">`:`<div class="avatar-sm" style="width:56px;height:56px;font-size:1rem">${ini(h.nombre)}</div>`}
              <button class="btn btn-xs" style="position:absolute;bottom:-6px;right:-6px" onclick="abrirModalFoto()">📷</button>
            </div>
            <div style="flex:1"><b style="font-size:1.05rem">${esc(h.nombre)}</b>
              <div class="small muted">${esc(h.profesion||"")} · ${h.experiencia_anios} años de experiencia · CC ${esc(h.documento||"—")}</div>
              <div class="small muted">📞 ${esc(h.telefono||"—")} · ✉️ ${esc(h.email||"—")} · Vinculación: ${h.fecha_vinculacion||"—"}</div></div>
            <div class="score-ring" style="--v:${h.hv_score}"><span>${h.hv_score}</span></div>
          </div>
          <div class="legal-note">🧮 <b>Score de hoja de vida ${h.hv_score}/100.</b> Mantén tus estudios y certificados al día: la Secretaría usa este puntaje para ubicar talento docente.</div>
        </div></div>
        <div class="card"><div class="card-body">
          <b class="small">🎓 Estudios y títulos</b>${lista(h.estudios,"estudios")}
          <div style="display:flex;gap:8px;margin:6px 0 14px"><input id="mp_est" placeholder="Nuevo título (ej: Especialización en...)" style="flex:1;padding:8px;border:1px solid var(--border);border-radius:8px"><button class="btn btn-sm" onclick="if(document.getElementById('mp_est').value.trim()){window._hv.estudios.push(document.getElementById('mp_est').value);VISTAS.miperfil._repintar()}">➕</button></div>
          <b class="small">💼 Experiencia laboral</b>${lista(h.experiencia,"experiencia")}
          <div style="display:flex;gap:8px;margin:6px 0 14px"><input id="mp_exp" placeholder="Cargo — institución (años)" style="flex:1;padding:8px;border:1px solid var(--border);border-radius:8px"><button class="btn btn-sm" onclick="if(document.getElementById('mp_exp').value.trim()){window._hv.experiencia.push(document.getElementById('mp_exp').value);VISTAS.miperfil._repintar()}">➕</button></div>
          <b class="small">🏅 Certificados, capacitaciones, diplomados y másteres</b>${lista(h.certificaciones,"certificaciones")}
          <div class="dropzone" style="margin:6px 0" onclick="document.getElementById('mp_certs').click()">📎 Sube tus certificados en PDF/imagen (simulado)</div>
          <input type="file" id="mp_certs" multiple style="display:none" onchange="Array.from(this.files).slice(0,10).forEach(f=>window._hv.certificaciones.push('📎 '+f.name));VISTAS.miperfil._repintar()">
          <div style="display:flex;gap:8px;margin:6px 0 8px"><input id="mp_cert" placeholder="…o escribe el curso/diplomado" style="flex:1;padding:8px;border:1px solid var(--border);border-radius:8px"><button class="btn btn-sm" onclick="if(document.getElementById('mp_cert').value.trim()){window._hv.certificaciones.push(document.getElementById('mp_cert').value);VISTAS.miperfil._repintar()}">➕</button></div>
          <div class="dropzone" onclick="document.getElementById('mp_hv_file').click()">📄 ${h.archivo?("HV adjunta: «"+esc(h.archivo)+"» — reemplazar"):"Sube tu hoja de vida completa en PDF (simulado)"}</div>
          <input type="file" id="mp_hv_file" style="display:none" onchange="window._hv.archivo=this.files[0]?this.files[0].name:window._hv.archivo;VISTAS.miperfil._repintar()">
          <div style="text-align:right;margin-top:14px"><button class="btn btn-primary" onclick="guardarMiHV()">💾 Guardar mi hoja de vida</button></div>
        </div></div>`);
    };
    VISTAS.miperfil._repintar();
  }catch(e){ main(`<div class="empty">Error cargando tu perfil</div>`); }
};
async function guardarMiHV(){
  const h=window._hv;
  try{ const r=await post("/academico/personal/hoja_vida/guardar",{personal_id:h.id,estudios:h.estudios,experiencia:h.experiencia,certificaciones:h.certificaciones,archivo:h.archivo});
    toast(r.msg,!r.ok);
    if(r.ok) VISTAS.miperfil();
  }catch(e){ toast("Error",true); }
}

/* ── VISTA: COMUNICADOS (rector) ── */
VISTAS.comunicados = async function(){
  loading();
  try{
    const [enviados, personal, salones] = await Promise.all([
      api(`/comunicados/enviados?institucion_id=${ST.institucion_id}`),
      api(`/academico/personal?institucion_id=${ST.institucion_id}`),
      api(`/academico/salones?institucion_id=${ST.institucion_id}`),
    ]);
    window._comPersonal = personal; window._comSalones = salones;
    main(head("Comunicados y notificaciones", "Envía avisos a toda la institución, a un grupo, a una persona o a los acudientes de un salón",
      `<button class="btn btn-primary" onclick="abrirComunicado()">📢 Nuevo comunicado</button>`)+`
      <div class="card"><div class="card-head"><h3>Historial de comunicados enviados</h3><span class="small muted">${enviados.length}</span></div>
      <div class="tbl-scroll"><table>
        <thead><tr><th>Fecha</th><th>Título</th><th>Dirigido a</th><th style="text-align:center">Destinatarios</th></tr></thead>
        <tbody>${enviados.map(c=>`<tr>
          <td class="small">${esc(c.fecha)}</td>
          <td><b>${esc(c.titulo)}</b><div class="small muted">${esc((c.mensaje||"").slice(0,80))}</div></td>
          <td>${esc(c.destinatario)}</td>
          <td style="text-align:center"><span class="badge b-teal">${c.n}</span></td></tr>`).join("")||'<tr><td colspan="4" class="empty">Aún no has enviado comunicados.</td></tr>'}
      </tbody></table></div></div>
      <div class="legal-note">📢 Cada comunicado llega a la campana 🔔 de los destinatarios al instante. Si tienen la página abierta, reciben también la notificación push del navegador. A los acudientes les llega por WhatsApp (simulado).</div>`);
  }catch(e){ main(`<div class="empty">Error</div>`); }
};
function abrirComunicado(){
  const per = window._comPersonal||[];
  const sal = window._comSalones||[];
  document.getElementById("com_tipo").value="institucion";
  document.getElementById("com_persona").innerHTML = per.map(p=>`<option value="${p.id}">${esc(p.nombre)} (${esc(p.rol)})</option>`).join("");
  document.getElementById("com_salon").innerHTML = sal.map(s=>`<option value="${s.id}">Salón ${esc(s.nombre)} (${s.n_estudiantes} est.)</option>`).join("");
  document.getElementById("com_titulo").value="";
  document.getElementById("com_msg").value="";
  comTipoCambio();
  abrirModal("modal-comunicado");
}
function comTipoCambio(){
  const t=document.getElementById("com_tipo").value;
  document.getElementById("com_persona_wrap").classList.toggle("oculto", t!=="persona");
  document.getElementById("com_salon_wrap").classList.toggle("oculto", t!=="salon_acudientes");
}
async function enviarComunicado(){
  const tipo=document.getElementById("com_tipo").value;
  const body={ institucion_id:ST.institucion_id, emisor:ST.perfil.titulo,
    destinatario_tipo:tipo,
    destinatario_id: tipo==="persona"?parseInt(document.getElementById("com_persona").value)
                    : tipo==="salon_acudientes"?parseInt(document.getElementById("com_salon").value):null,
    titulo:document.getElementById("com_titulo").value, mensaje:document.getElementById("com_msg").value };
  if(!body.titulo.trim()||!body.mensaje.trim()){ toast("Título y mensaje son obligatorios",true); return; }
  try{ const r=await post("/comunicados/enviar",body);
    if(!r.ok){toast(r.msg,true);return;}
    cerrarModal("modal-comunicado"); toast(r.msg); VISTAS.comunicados();
  }catch(e){ toast("Error al enviar",true); }
}

/* ── GESTIÓN DE ESTUDIANTES POR SALÓN (punto 5) ── */
async function cargarEstudiantesSalon(){
  const d = window._detSalon;
  try{
    const dd = await api(`/academico/salones/detalle?salon_id=${d.id}`);
    const ests = dd.estudiantes || [];
    window._estsSalon = ests;
    const otrosSalones = (window._salones||[]).filter(s=>s.id!==d.id);
    document.getElementById("detsalon-est").innerHTML = `
      <div class="small muted" style="margin-bottom:8px">${ests.length} estudiante(s) en el salón. Puedes moverlos a otro salón o retirarlos (su matrícula y notas se conservan).</div>
      <div class="tbl-scroll" style="max-height:340px;overflow-y:auto"><table>
        <thead><tr><th>Estudiante</th><th>SISBEN</th><th>Acudiente</th><th>Mover a</th><th></th></tr></thead>
        <tbody>${ests.map(e=>`<tr>
          <td><div class="flex-cell"><div class="avatar-sm">${ini(e.nombre)}</div>${esc(e.nombre)}</div></td>
          <td class="small">${esc(e.nivel_sisben||"—")}</td>
          <td class="small">${esc(e.acudiente||"—")}</td>
          <td><select id="mv-${e.id}" style="padding:5px 8px;border:1px solid var(--border);border-radius:7px;font-size:.78rem">
            <option value="">— elegir —</option>
            ${otrosSalones.map(s=>`<option value="${s.id}">Salón ${esc(s.nombre)}</option>`).join("")}
          </select><button class="btn btn-xs" onclick="moverEstudiante(${e.id})">↪️</button></td>
          <td><button class="btn btn-xs btn-danger" onclick="quitarEstudiante(${e.id},'${esc(e.nombre)}')">Retirar</button></td>
        </tr>`).join("")||'<tr><td colspan="5" class="empty">Salón sin estudiantes.</td></tr>'}
      </tbody></table></div>`;
  }catch(e){ document.getElementById("detsalon-est").innerHTML='<div class="empty">Error</div>'; }
}
async function moverEstudiante(eid){
  const dest=parseInt(document.getElementById("mv-"+eid).value);
  if(!dest){ toast("Elige el salón destino",true); return; }
  try{ const r=await post("/academico/estudiantes/mover",{estudiante_id:eid,salon_id:dest});
    toast(r.msg,!r.ok); if(r.ok){ verSalon(window._detSalon.id); setTimeout(()=>detSalonTab("est"),250); }
  }catch(e){ toast("Error",true); }
}
async function quitarEstudiante(eid,nombre){
  if(!confirm(`¿Retirar a ${nombre} de este salón? Quedará sin salón asignado (matrícula y notas se conservan).`)) return;
  try{ const r=await post("/academico/estudiantes/mover",{estudiante_id:eid,salon_id:null});
    toast(r.msg,!r.ok); if(r.ok){ verSalon(window._detSalon.id); setTimeout(()=>detSalonTab("est"),250); }
  }catch(e){ toast("Error",true); }
}
function nuevoEstudiante(){
  document.getElementById("est-title").textContent="➕ Nuevo estudiante — Salón "+window._detSalon.nombre;
  document.getElementById("est_id").value="";
  document.getElementById("est_salon").value=window._detSalon.id;
  ["est_nombre","est_barrio","est_acud","est_parent","est_tel","est_dir"].forEach(i=>document.getElementById(i).value="");
  document.getElementById("est_sisben").value="B4";
  document.getElementById("est_zona").value="urbana";
  abrirModal("modal-est");
}
async function guardarEstudiante(){
  const body={ id:parseInt(document.getElementById("est_id").value)||0, institucion_id:ST.institucion_id,
    salon_id:parseInt(document.getElementById("est_salon").value)||null,
    nombre:document.getElementById("est_nombre").value, nivel_sisben:document.getElementById("est_sisben").value,
    zona:document.getElementById("est_zona").value, barrio_vereda:document.getElementById("est_barrio").value,
    acudiente:document.getElementById("est_acud").value, parentesco:document.getElementById("est_parent").value,
    telefono:document.getElementById("est_tel").value, direccion:document.getElementById("est_dir").value };
  if(!body.nombre.trim()){ toast("El nombre es obligatorio",true); return; }
  try{ const r=await post("/academico/estudiantes/guardar",body);
    if(!r.ok){toast(r.msg,true);return;}
    cerrarModal("modal-est"); toast(r.msg);
    verSalon(window._detSalon.id); setTimeout(()=>detSalonTab("est"),250);
  }catch(e){ toast("Error",true); }
}
async function agregarSinSalon(){
  try{
    const sinSalon = await api(`/academico/estudiantes/sin_salon?institucion_id=${ST.institucion_id}`);
    if(!sinSalon.length){ toast("No hay estudiantes sin salón. Usa ➕ Nuevo estudiante.",true); return; }
    const opts = sinSalon.map(e=>`${e.id}: ${e.nombre} (grado ${e.grado})`).join("\n");
    const sel = prompt(`Estudiantes sin salón — escribe el ID del que quieres agregar a este salón:\n\n${opts}`);
    const id = parseInt(sel);
    if(!id) return;
    const r=await post("/academico/estudiantes/mover",{estudiante_id:id,salon_id:window._detSalon.id});
    toast(r.msg,!r.ok); if(r.ok){ verSalon(window._detSalon.id); setTimeout(()=>detSalonTab("est"),250); }
  }catch(e){ toast("Error",true); }
}

/* ── CORTES: crear / eliminar con protección (punto 6) ── */
function abrirModalCorte(periodo){
  document.getElementById("cor_per").value=periodo;
  document.getElementById("cor_nombre").value="";
  document.getElementById("cor_ini").value="";
  document.getElementById("cor_fin").value="";
  abrirModal("modal-corte");
}
async function crearCorte(){
  const body={ institucion_id:ST.institucion_id, periodo_numero:parseInt(document.getElementById("cor_per").value),
    nombre:document.getElementById("cor_nombre").value, inicio:document.getElementById("cor_ini").value||null,
    fin:document.getElementById("cor_fin").value||null };
  if(!body.nombre.trim()){ toast("El nombre del corte es obligatorio",true); return; }
  try{ const r=await post("/academico/cortes/crear",body);
    if(!r.ok){toast(r.msg,true);return;}
    cerrarModal("modal-corte"); toast(r.msg);
    verSalon(window._detSalon.id); setTimeout(()=>detSalonTab("cortes"),250);
  }catch(e){ toast("Error",true); }
}
async function eliminarCorte(id,nombre){
  const conf = prompt(`⚠️ ATENCIÓN: vas a eliminar «${nombre}».\n\nSe perderá la organización de temas ligada a este corte. Esta acción NO se puede deshacer.\n\nSi estás MUY seguro, escribe la palabra ELIMINAR:`);
  if(conf===null) return;
  try{ const r=await post("/academico/cortes/eliminar",{id,confirmacion:conf});
    toast(r.msg,!r.ok);
    if(r.ok){ verSalon(window._detSalon.id); setTimeout(()=>detSalonTab("cortes"),250); }
  }catch(e){ toast("Error",true); }
}

/* ── PLAN DE COMPRAS: CRUD + importación PDF (punto 9a) ── */
function editarPlanItem(id){
  const p=(window._planFSE||[]).find(x=>x.id===id);
  document.getElementById("plan-title").textContent = id?"Editar ítem del plan":"Nuevo ítem del plan";
  document.getElementById("pl_id").value=id||"";
  document.getElementById("pl_concepto").value=p?p.concepto:"";
  document.getElementById("pl_cuenta").innerHTML = (window._cuentasFSE||[]).filter(c=>c.tipo==="gasto").map(c=>`<option value="${c.codigo}" ${p&&p.cuenta===c.codigo?"selected":""}>${c.codigo} · ${esc(c.nombre)}</option>`).join("");
  document.getElementById("pl_prio").value=p?p.prioridad:2;
  document.getElementById("pl_mes").innerHTML = MESES.slice(1).map((m,i)=>`<option value="${i+1}" ${p&&p.mes===i+1?"selected":""}>${m}</option>`).join("");
  document.getElementById("pl_valor").value=p?p.valor:"";
  document.getElementById("pl_estado").value=p?p.estado:"pendiente";
  abrirModal("modal-plan");
}
async function guardarPlanItem(){
  const body={ id:parseInt(document.getElementById("pl_id").value)||0, institucion_id:ST.institucion_id,
    concepto:document.getElementById("pl_concepto").value, cuenta_codigo:document.getElementById("pl_cuenta").value,
    prioridad:parseInt(document.getElementById("pl_prio").value), mes_planeado:parseInt(document.getElementById("pl_mes").value),
    valor_presupuestado:parseFloat(document.getElementById("pl_valor").value)||0, estado:document.getElementById("pl_estado").value };
  if(!body.concepto.trim()){ toast("El concepto es obligatorio",true); return; }
  try{ const r=await post("/fse/plan/guardar",body);
    if(!r.ok){toast(r.msg,true);return;}
    cerrarModal("modal-plan"); toast(r.msg); VISTAS.fse("plan");
  }catch(e){ toast("Error",true); }
}
async function planEstado(id, estado){
  try{ const r=await post("/fse/plan/estado",{id,estado}); toast(r.msg,!r.ok); }
  catch(e){ toast("Error",true); }
}
async function eliminarPlanItem(id,concepto){
  if(!confirm(`¿Eliminar «${concepto}» del plan de compras?`)) return;
  try{ const r=await post("/fse/plan/eliminar",{id}); toast(r.msg,!r.ok); if(r.ok) VISTAS.fse("plan"); }
  catch(e){ toast("Error",true); }
}
function importarPlanPDF(){
  const inp=document.createElement("input");
  inp.type="file"; inp.accept=".pdf";
  inp.onchange=async ()=>{
    const nombre = inp.files[0]?inp.files[0].name:"plan_anual_2026.pdf";
    document.getElementById("plan-import").innerHTML='<div class="empty">🤖 Analizando el PDF con IA y extrayendo los ítems…</div>';
    try{
      const r=await post("/fse/plan/importar_pdf",{institucion_id:ST.institucion_id,archivo:nombre});
      if(!r.ok){ document.getElementById("plan-import").innerHTML=""; toast(r.msg,true); return; }
      window._planImport = r.items;
      document.getElementById("plan-import").innerHTML = `
        <div class="card" style="border:2px solid var(--gold)"><div class="card-head"><h3>🤖 ${r.items.length} ítems detectados en «${esc(nombre)}»</h3>
          <span class="small muted">Marca los que quieras agregar y confirma</span></div>
        <div class="card-body">
          <div class="tbl-scroll"><table><thead><tr><th style="width:40px"></th><th>Concepto</th><th>Cuenta</th><th>Prioridad</th><th>Mes</th><th style="text-align:right">Presupuesto</th></tr></thead><tbody>
            ${r.items.map((it,i)=>`<tr>
              <td style="text-align:center"><input type="checkbox" id="imp-${i}" checked style="width:17px;height:17px;accent-color:var(--teal)"></td>
              <td><b>${esc(it.concepto)}</b></td><td class="small">${esc(it.cuenta_codigo)}</td>
              <td>${(PRIO[it.prioridad]||["—"])[0]}</td><td>${MESES[it.mes_planeado]}</td>
              <td style="text-align:right">${money(it.valor_presupuestado)}</td></tr>`).join("")}
          </tbody></table></div>
          <div style="text-align:right;margin-top:10px">
            <button class="btn btn-sm" onclick="document.getElementById('plan-import').innerHTML=''">Cancelar</button>
            <button class="btn btn-sm btn-primary" onclick="confirmarImportPlan()">✅ Agregar seleccionados</button>
          </div>
        </div></div>`;
    }catch(e){ document.getElementById("plan-import").innerHTML=""; toast("Error al analizar",true); }
  };
  inp.click();
}
async function confirmarImportPlan(){
  const items = window._planImport||[];
  let n=0;
  for(let i=0;i<items.length;i++){
    if(!document.getElementById("imp-"+i).checked) continue;
    const it=items[i];
    try{ await post("/fse/plan/guardar",{institucion_id:ST.institucion_id,concepto:it.concepto,
      cuenta_codigo:it.cuenta_codigo,prioridad:it.prioridad,mes_planeado:it.mes_planeado,
      valor_presupuestado:it.valor_presupuestado,estado:"pendiente"}); n++; }catch(e){}
  }
  toast(`✅ ${n} ítem(s) agregados al plan desde el PDF.`);
  VISTAS.fse("plan");
}

/* ── CONTRATOS: coedit, portal, cronología (puntos 9b y 11) ── */
async function portalLink(id){
  try{ const r=await post("/contratos/contratistas/portal_link",{id});
    if(!r.ok){toast(r.msg,true);return;}
    toast(r.msg);
    setTimeout(()=>{ prompt("🔗 Link de autogestión del contratista (cópialo y compártelo):", r.url); },300);
  }catch(e){ toast("Error",true); }
}
async function portalCarga(id){
  if(!confirm("DEMO: simular que el contratista entró al link y subió sus documentos faltantes (con fecha de hoy). ¿Continuar?")) return;
  try{ const r=await post("/contratos/contratistas/portal_carga",{id});
    toast(r.msg,!r.ok); if(r.ok) VISTAS.contratos("contratistas");
  }catch(e){ toast("Error",true); }
}
function abrirCoedit(id){
  const c=(window._contratosCache||[]).find(x=>x.id===id);
  if(!c){ toast("Contrato no encontrado",true); return; }
  window._coedit=c;
  const esContador=["contador","rector"].includes(ST.perfil.rol);
  const editable = ["borrador","documentos"].includes(c.estado);
  const cc = c.cuenta_cobro||{};
  document.getElementById("coedit-title").textContent="✎ Editar contrato "+c.numero;
  document.getElementById("coedit-body").innerHTML=`
    <input type="hidden" id="ce_id" value="${c.id}">
    <div class="fsec">📄 Datos del contrato</div>
    <div class="frow"><label>Objeto</label><input id="ce_objeto" value="${esc(c.objeto)}" ${!editable?"disabled":""}></div>
    <div class="frow-3">
      <div><label>Valor (COP) ${!editable?"<span class='lock'>🔒 solo en borrador</span>":""}</label><input type="number" id="ce_valor" value="${c.valor}" ${!editable?"disabled":""}></div>
      <div><label>Tipo de contrato</label><select id="ce_tipo">
        ${[["suministro","Suministro"],["servicio","Servicio"],["obra","Obra menor"],["pae","PAE / alimentación"]].map(([v,l])=>`<option value="${v}" ${c.tipo_contrato===v?"selected":""}>${l}</option>`).join("")}
      </select></div>
      <div><label>Contratista ${c.estado!=="borrador"?"<span class='lock'>🔒</span>":""}</label>
        <select id="ce_contratista" ${c.estado!=="borrador"?"disabled":""}>
          ${(window._contratistas||[]).map(x=>`<option value="${x.id}" ${x.nombre===c.contratista?"selected":""}>${esc(x.nombre)}</option>`).join("")}
        </select></div>
    </div>
    <div class="fsec">🧾 CDP / RP ${esContador?"(editable por contaduría)":""}</div>
    <div class="frow-2">
      <div><label>CDP</label><input id="ce_cdp" value="${esc(c.cdp||"")}" ${!esContador?"disabled":""}></div>
      <div><label>RP</label><input id="ce_rp" value="${esc(c.rp||"")}" ${!esContador?"disabled":""}></div>
    </div>
    <div class="fsec">💬 Cotizaciones <button class="btn btn-xs" onclick="ceAddCotiz()">➕ Agregar</button></div>
    <div id="ce_cotiz"></div>
    <div class="fsec">🧾 Cuenta de cobro</div>
    <div class="frow-3">
      <div><label>Número</label><input id="ce_cc_num" value="${esc(cc.numero||"")}" placeholder="CC-001"></div>
      <div><label>Valor</label><input type="number" id="ce_cc_val" value="${cc.valor||c.valor}"></div>
      <div><label>Estado</label><select id="ce_cc_estado"><option value="pendiente" ${cc.estado!=="pagada"?"selected":""}>Pendiente</option><option value="pagada" ${cc.estado==="pagada"?"selected":""}>Pagada</option></select></div>
    </div>
    <div class="small muted">Al marcar la cuenta de cobro como <b>Pagada</b> se genera automáticamente el egreso en el libro FSE.</div>
    <div class="modal-foot" style="border:none;padding:14px 0 0">
      <button class="btn" onclick="cerrarModal('modal-coedit')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarCoedit()">💾 Guardar cambios</button>
    </div>`;
  window._ceCotiz = (c.cotizaciones||[]).slice();
  pintarCeCotiz();
  abrirModal("modal-coedit");
}
function pintarCeCotiz(){
  document.getElementById("ce_cotiz").innerHTML = (window._ceCotiz||[]).map((q,i)=>`
    <div style="display:flex;gap:6px;margin-bottom:6px;align-items:center">
      <input value="${esc(q.proveedor)}" onchange="window._ceCotiz[${i}].proveedor=this.value" placeholder="Proveedor" style="flex:2;padding:6px;border:1px solid var(--border);border-radius:7px;font-size:.8rem">
      <input type="number" value="${q.valor||0}" onchange="window._ceCotiz[${i}].valor=parseFloat(this.value)||0" placeholder="Valor" style="flex:1;padding:6px;border:1px solid var(--border);border-radius:7px;font-size:.8rem">
      <span class="small muted">${esc(q.archivo||"")}</span>
      <button class="btn btn-xs btn-danger" onclick="window._ceCotiz.splice(${i},1);pintarCeCotiz()">✕</button>
    </div>`).join("")||'<div class="small muted">Sin cotizaciones. Agrega al menos dos para comparar precios.</div>';
}
function ceAddCotiz(){
  (window._ceCotiz=window._ceCotiz||[]).push({proveedor:"",valor:0,fecha:hoyISO(),archivo:"cotizacion.pdf"});
  pintarCeCotiz();
}
async function guardarCoedit(){
  const c=window._coedit;
  const body={ id:c.id,
    objeto:document.getElementById("ce_objeto").value,
    tipo_contrato:document.getElementById("ce_tipo").value,
    cdp_num:document.getElementById("ce_cdp").value,
    rp_num:document.getElementById("ce_rp").value,
    cotizaciones:window._ceCotiz };
  const valEl=document.getElementById("ce_valor");
  if(!valEl.disabled) body.valor=parseFloat(valEl.value)||0;
  const ctEl=document.getElementById("ce_contratista");
  if(!ctEl.disabled) body.contratista_id=parseInt(ctEl.value);
  const ccNum=document.getElementById("ce_cc_num").value.trim();
  if(ccNum){
    body.cuenta_cobro={ numero:ccNum, valor:parseFloat(document.getElementById("ce_cc_val").value)||c.valor,
      estado:document.getElementById("ce_cc_estado").value };
  }
  try{ const r=await post("/contratos/editar",body);
    if(!r.ok){toast(r.msg,true);return;}
    cerrarModal("modal-coedit"); toast(r.msg); VISTAS.contratos("pipeline");
  }catch(e){ toast("Error",true); }
}
async function cronologiaView(){
  const cr = await api(`/contratos/cronologia?institucion_id=${ST.institucion_id}`);
  document.getElementById("con-cont").innerHTML = `
    <div class="card"><div class="card-head"><h3>🕓 Cronología completa de la contratación</h3>
      <button class="btn btn-sm" onclick="window.print()">🖨️ Imprimir para auditoría</button></div>
    <div class="tbl-scroll"><table>
      <thead><tr><th>Fecha</th><th>Contrato</th><th>Hito</th><th>Detalle / contratista</th><th style="text-align:right">Valor</th></tr></thead>
      <tbody>${cr.map(h=>`<tr>
        <td class="small"><b>${esc(h.fecha)}</b></td>
        <td class="small">${esc(h.contrato)}</td>
        <td>${esc(h.hito)}</td>
        <td class="small">${esc(h.detalle||"")}${h.contratista&&h.contratista!==h.detalle?`<div class="muted">${esc(h.contratista)}</div>`:""}</td>
        <td style="text-align:right">${h.valor!=null?money(h.valor):"—"}</td></tr>`).join("")||'<tr><td colspan="5" class="empty">Sin hitos registrados.</td></tr>'}
    </tbody></table></div></div>
    <div class="audit-note">🔍 Esta rejilla en <b>orden cronológico</b> es exactamente lo que pide una auditoría de la Contraloría: cada CDP, cotización, revisión jurídica, firma, cuenta de cobro y pago, con su fecha, en una sola línea de tiempo trazable.</div>`;
}

/* ── DASHBOARD CONTADOR (punto 11) ── */
VISTAS.contaduria = async function(){
  loading();
  try{
    const [res, contratos] = await Promise.all([
      api(`/fse/resumen?institucion_id=${ST.institucion_id}`),
      api(`/contratos/?institucion_id=${ST.institucion_id}`),
    ]);
    window._contratosCache = contratos;
    const cxp = contratos.filter(c=>c.cuenta_cobro && c.cuenta_cobro.estado==="pendiente");
    const sinRP = contratos.filter(c=>!c.rp && ["firma","firmado","ejecucion"].includes(c.estado));
    main(head("Mi tablero contable","Contaduría del FSE: saldos, cuentas de cobro por pagar, CDP/RP y cronología para auditorías")+`
      <div class="kpis">
        <div class="kpi green"><div class="kpi-ico">💰</div><div class="kpi-val sm">${money(res.saldo)}</div><div class="kpi-lbl">Saldo disponible FSE</div></div>
        <div class="kpi red"><div class="kpi-ico">🧾</div><div class="kpi-val">${cxp.length}</div><div class="kpi-lbl">Cuentas de cobro por pagar</div></div>
        <div class="kpi orange"><div class="kpi-ico">📤</div><div class="kpi-val sm">${money(res.egresos)}</div><div class="kpi-lbl">Egresos ejecutados</div></div>
        <div class="kpi"><div class="kpi-ico">📋</div><div class="kpi-val">${sinRP.length}</div><div class="kpi-lbl">Contratos sin RP</div></div>
      </div>
      <div class="card"><div class="card-head"><h3>🧾 Cuentas de cobro pendientes de pago</h3></div>
      <div class="tbl-scroll"><table><thead><tr><th>Contrato</th><th>Contratista</th><th>N° cuenta</th><th style="text-align:right">Valor</th><th></th></tr></thead>
      <tbody>${cxp.map(c=>`<tr>
        <td><b>${esc(c.numero)}</b><div class="small muted">${esc(c.objeto.slice(0,40))}</div></td>
        <td class="small">${esc(c.contratista)}</td>
        <td class="small">${esc(c.cuenta_cobro.numero||"—")}</td>
        <td style="text-align:right"><b>${money(c.cuenta_cobro.valor)}</b></td>
        <td><button class="btn btn-xs btn-green" onclick="marcarPagada(${c.id},${c.cuenta_cobro.valor},'${esc(c.cuenta_cobro.numero||"")}')">💸 Marcar pagada</button></td>
      </tr>`).join("")||'<tr><td colspan="5" class="empty">No hay cuentas de cobro pendientes 🎉</td></tr>'}
      </tbody></table></div></div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px">
        <button class="btn btn-primary" onclick="irVista('contratos')">📜 Ir a contratos (editar CDP/RP)</button>
        <button class="btn" onclick="irVista('fse')">💰 Libro FSE completo</button>
      </div>
      <div id="cont-crono"></div>`);
    // cronología embebida
    const cr = await api(`/contratos/cronologia?institucion_id=${ST.institucion_id}`);
    document.getElementById("cont-crono").innerHTML = `
      <div class="card"><div class="card-head"><h3>🕓 Cronología para auditoría</h3><button class="btn btn-sm" onclick="window.print()">🖨️</button></div>
      <div class="tbl-scroll" style="max-height:320px;overflow-y:auto"><table><thead><tr><th>Fecha</th><th>Contrato</th><th>Hito</th><th style="text-align:right">Valor</th></tr></thead>
      <tbody>${cr.map(h=>`<tr><td class="small"><b>${esc(h.fecha)}</b></td><td class="small">${esc(h.contrato)}</td><td>${esc(h.hito)}</td><td style="text-align:right">${h.valor!=null?money(h.valor):"—"}</td></tr>`).join("")}</tbody></table></div></div>`;
  }catch(e){ main(`<div class="empty">Error</div>`); }
};
async function marcarPagada(id, valor, numero){
  if(!confirm(`¿Marcar la cuenta de cobro ${numero} como PAGADA? Se registrará el egreso de ${money(valor)} en el FSE.`)) return;
  try{ const r=await post("/contratos/editar",{id,cuenta_cobro:{numero,valor,estado:"pagada"}});
    toast(r.msg,!r.ok); if(r.ok) VISTAS.contaduria();
  }catch(e){ toast("Error",true); }
}

/* ── DASHBOARD ABOGADO (punto 11) ── */
VISTAS.juridica = async function(){
  loading();
  try{
    const contratos = await api(`/contratos/?institucion_id=${ST.institucion_id}`);
    window._contratosCache = contratos;
    const enJuridica = contratos.filter(c=>c.estado==="juridica");
    const conConcepto = contratos.filter(c=>c.nota_juridica);
    main(head("Mi bandeja jurídica","Revisa requisitos, emite Vo.Bo. o devuelve, y consulta el historial de conceptos")+`
      <div class="kpis">
        <div class="kpi purple"><div class="kpi-ico">⚖️</div><div class="kpi-val">${enJuridica.length}</div><div class="kpi-lbl">Esperando tu revisión</div></div>
        <div class="kpi"><div class="kpi-ico">📝</div><div class="kpi-val">${conConcepto.length}</div><div class="kpi-lbl">Con concepto emitido</div></div>
        <div class="kpi red"><div class="kpi-ico">⏱</div><div class="kpi-val">${contratos.filter(c=>c.atrasado).length}</div><div class="kpi-lbl">Contratos atrasados</div></div>
      </div>
      <div class="card"><div class="card-head"><h3>⚖️ Contratos en revisión jurídica</h3></div><div class="card-body">
        ${enJuridica.map(c=>`<div class="obs-item obs-compromiso">
          <div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap">
            <div><b>${esc(c.numero)}</b> · ${esc(c.objeto)} <span class="badge b-teal">${esc(c.tipo_label)}</span>
              <div class="small muted">${esc(c.contratista)} · ${money(c.valor)} · CDP ${esc(c.cdp||"—")}</div></div>
            <div style="text-align:right">${c.docs_ok?'<span class="badge b-green">Docs completos</span>':'<span class="badge b-red">Faltan docs</span>'}</div>
          </div>
          ${!c.docs_ok?`<div class="small" style="color:var(--red);margin-top:5px">Faltantes: ${c.docs_faltantes.map(x=>esc(x)).join(", ")}</div>`:""}
          <div style="margin-top:8px;display:flex;gap:6px">
            <button class="btn btn-xs btn-green" onclick="juridicaContrato(${c.id},true)">⚖️ Dar Vo.Bo.</button>
            <button class="btn btn-xs btn-danger" onclick="juridicaContrato(${c.id},false)">↩️ Devolver</button>
            <button class="btn btn-xs" onclick="abrirCoedit(${c.id})">👁️ Ver detalle</button>
          </div>
        </div>`).join("")||'<div class="empty">No hay contratos esperando revisión jurídica 🎉</div>'}
      </div></div>
      <div class="card"><div class="card-head"><h3>📝 Historial de conceptos jurídicos</h3></div>
      <div class="tbl-scroll"><table><thead><tr><th>Contrato</th><th>Estado</th><th>Concepto emitido</th></tr></thead>
      <tbody>${conConcepto.map(c=>`<tr><td><b>${esc(c.numero)}</b></td>
        <td><span class="badge b-blue">${esc(c.estado)}</span></td>
        <td class="small">${esc(c.nota_juridica)}</td></tr>`).join("")||'<tr><td colspan="3" class="empty">Sin conceptos emitidos aún.</td></tr>'}
      </tbody></table></div></div>`);
  }catch(e){ main(`<div class="empty">Error</div>`); }
};

/* ── CENSO: jóvenes (gestión) + cruce (punto 13) ── */
let CENSO_FILTRO="fuera";
async function censoJovenes(){
  const muni = ST.perfil.municipio?`&municipio=${encodeURIComponent(ST.perfil.municipio)}`:"";
  const jov = await api(`/censo/jovenes?filtro=${CENSO_FILTRO}${muni}`);
  const insts = await api(`/territorio/secretaria${muni?"?municipio="+encodeURIComponent(ST.perfil.municipio):""}`);
  window._censoInsts = insts.colegios||[];
  document.getElementById("censo-cont").innerHTML = `
    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:12px">
      ${[["fuera","🚸 Fuera del sistema"],["riesgo","🛡️ Zona de riesgo"],["sin_contactar","📵 Sin contactar"],["todos","Todos"]].map(([k,l])=>
        `<button class="chip-filtro ${CENSO_FILTRO===k?'active':''}" onclick="CENSO_FILTRO='${k}';censoJovenes()">${l}</button>`).join("")}
      <button class="btn btn-sm btn-primary" style="margin-left:auto" onclick="nuevoJoven()">➕ Registrar joven</button>
    </div>
    <div class="card"><div class="tbl-scroll" style="max-height:460px;overflow-y:auto"><table>
      <thead><tr><th>Joven</th><th>Edad</th><th>Zona / barrio</th><th>Situación</th><th>Estado</th><th>Acciones</th></tr></thead>
      <tbody>${jov.map(j=>`<tr>
        <td><div class="flex-cell"><div class="avatar-sm">${ini(j.nombre)}</div><div><b>${esc(j.nombre)}</b>${j.zona_riesgo?' <span class="badge b-red">🛡️ riesgo</span>':''}</div></div></td>
        <td>${j.edad}</td>
        <td class="small">${esc(j.barrio_vereda||"—")}<div class="muted">${esc(j.zona)}</div></td>
        <td>${j.estudia?`<span class="badge b-green">Estudia</span><div class="small muted">${esc(j.colegio||"")}</div>`:`<span class="badge b-red">No estudia</span><div class="small muted">${esc(j.motivo||"")}</div>`}${j.tipo_alerta?`<div class="small" style="color:var(--red)">⚠️ ${esc(j.tipo_alerta)}</div>`:""}</td>
        <td>${j.estado==="Sin contactar"?'<span class="badge b-gray">Sin contactar</span>':j.estado==="En seguimiento"?'<span class="badge b-orange">En seguimiento</span>':'<span class="badge b-green">Cerrado</span>'}${j.ultimo_contacto?`<div class="small muted">${esc(j.ultimo_contacto)}</div>`:""}</td>
        <td style="white-space:nowrap">
          ${!j.estudia?`<button class="btn btn-xs btn-primary" onclick="contactarJoven(${j.id},'${esc(j.nombre)}')">📱</button>
          <button class="btn btn-xs btn-green" onclick="matricularJoven(${j.id},'${esc(j.nombre)}')">🎒</button>`:""}
          <button class="btn btn-xs" onclick="editarJoven(${j.id})">✎</button>
        </td></tr>`).join("")||'<tr><td colspan="6" class="empty">Sin jóvenes con este filtro.</td></tr>'}
    </tbody></table></div></div>
    <div class="legal-note">👥 Cada joven "fuera del sistema" es una oportunidad: <b>📱 Contactar</b> envía el mensaje a la familia (simulado), <b>🎒 Matricular</b> lo inscribe en una institución y cierra la brecha. Todo cruzado con el SIMAT.</div>`;
}
function nuevoJoven(){
  document.getElementById("joven-title").textContent="➕ Registrar joven en el censo";
  document.getElementById("jo_id").value="";
  ["jo_nombre","jo_barrio"].forEach(i=>document.getElementById(i).value="");
  document.getElementById("jo_edad").value=14;
  document.getElementById("jo_sexo").value="M";
  document.getElementById("jo_zona").value="urbana";
  document.getElementById("jo_estudia").value="false";
  document.getElementById("jo_motivo").value="Trabajo infantil";
  document.getElementById("jo_riesgo").checked=false;
  abrirModal("modal-joven");
}
function editarJoven(id){
  nuevoJoven();
  toast("Edición rápida: ajusta los campos y guarda (se creará/actualizará).");
  document.getElementById("jo_id").value=id;
  document.getElementById("joven-title").textContent="✎ Actualizar registro del censo";
}
async function guardarJoven(){
  const body={ id:parseInt(document.getElementById("jo_id").value)||0,
    nombre:document.getElementById("jo_nombre").value, edad:parseInt(document.getElementById("jo_edad").value)||14,
    sexo:document.getElementById("jo_sexo").value, municipio:ST.perfil.municipio||"San Pablo",
    zona:document.getElementById("jo_zona").value, barrio_vereda:document.getElementById("jo_barrio").value,
    estudia:document.getElementById("jo_estudia").value==="true",
    motivo_no_estudia:document.getElementById("jo_motivo").value,
    zona_riesgo:document.getElementById("jo_riesgo").checked };
  if(!body.nombre.trim()){ toast("El nombre es obligatorio",true); return; }
  try{ const r=await post("/censo/guardar",body);
    if(!r.ok){toast(r.msg,true);return;}
    cerrarModal("modal-joven"); toast(r.msg); censoJovenes();
  }catch(e){ toast("Error",true); }
}
async function contactarJoven(id,nombre){
  if(!confirm(`¿Enviar mensaje de acercamiento a la familia de ${nombre}? (WhatsApp simulado)`)) return;
  try{ const r=await post("/censo/contactar",{id}); toast(r.msg,!r.ok); if(r.ok) censoJovenes(); }
  catch(e){ toast("Error",true); }
}
async function matricularJoven(id,nombre){
  const insts=window._censoInsts||[];
  if(!insts.length){ toast("No hay instituciones para matricular",true); return; }
  const opts=insts.map(c=>`${c.institucion_id}: ${c.nombre}`).join("\n");
  const sel=prompt(`🎒 Matricular a ${nombre}. Escribe el ID de la institución:\n\n${opts}`);
  const iid=parseInt(sel); if(!iid) return;
  try{ const r=await post("/censo/matricular",{id,institucion_id:iid});
    toast(r.msg,!r.ok); if(r.ok) censoJovenes();
  }catch(e){ toast("Error",true); }
}
async function censoCruce(){
  const muni = ST.perfil.municipio?`?municipio=${encodeURIComponent(ST.perfil.municipio)}`:"";
  const cz = await api(`/censo/cruce${muni}`);
  document.getElementById("censo-cont").innerHTML = `
    <div class="kpis">
      <div class="kpi"><div class="kpi-ico">👦</div><div class="kpi-val">${cz.total_censados}</div><div class="kpi-lbl">Jóvenes censados</div></div>
      <div class="kpi red"><div class="kpi-ico">🚸</div><div class="kpi-val">${cz.fuera_sistema}</div><div class="kpi-lbl">Fuera del sistema</div></div>
      <div class="kpi green"><div class="kpi-ico">🎒</div><div class="kpi-val">${cz.matriculados_via_censo}</div><div class="kpi-lbl">Rescatados vía censo</div></div>
    </div>
    <div class="card"><div class="card-head"><h3>🔄 Cruce censo ↔ matrícula real por institución</h3></div>
    <div class="tbl-scroll"><table><thead><tr><th>Institución</th><th style="text-align:center">Matrícula real (SIMAT)</th><th style="text-align:center">Censo dice que estudian ahí</th><th>Cobertura del censo</th></tr></thead>
    <tbody>${cz.colegios.map(c=>`<tr>
      <td><b>${esc(c.institucion)}</b></td>
      <td style="text-align:center">${c.matricula_real}</td>
      <td style="text-align:center">${c.censados_dicen_estudiar}</td>
      <td><div class="flex-cell"><div class="prog" style="flex:1"><div class="prog-fill" style="width:${Math.min(100,c.cobertura_censo_pct)}%;background:${c.cobertura_censo_pct>=80?'var(--green)':'var(--orange)'}"></div></div><b class="small">${c.cobertura_censo_pct}%</b></div></td>
    </tr>`).join("")||'<tr><td colspan="4" class="empty">Sin datos</td></tr>'}
    </tbody></table></div></div>
    <div class="audit-note">🔄 Este cruce revela la <b>brecha de cobertura</b>: compara cuántos jóvenes están matriculados en el SIMAT contra cuántos el censo territorial dice que deberían estar estudiando. La diferencia es a quién hay que ir a buscar.</div>`;
}

/* ═══════════════════════════════════════════════════════════════════
   V4 · PORTAL DEL ALUMNO (puntos 4, 6, 9)
   ═══════════════════════════════════════════════════════════════════ */

VISTAS.altablero = async function(){
  loading();
  try{
    const d = await api(`/alumno/tablero?estudiante_id=${ST.estudiante_id}`);
    const pend = d.pendientes||[];
    main(`
      <div class="al-hero">
        <div style="font-size:3rem">🎒</div>
        <div><h2>¡Hola, ${esc((d.nombre||"").split(" ")[0])}!</h2>
          <div class="sub">Salón ${esc(d.salon)} · ${d.n_clases} clases publicadas${pend.length?` · <b>${pend.length} pendiente(s)</b>`:" · sin pendientes 🎉"}</div></div>
        <div class="prog-c"><div class="score-ring" style="--v:${d.curso_contabilidad.pct};--c:#fff"><span>${d.curso_contabilidad.pct}%</span></div>
          <div class="sub" style="margin-top:5px">Curso Contabilidad</div></div>
      </div>
      ${d.salas_vivo.filter(s=>s.estado==="en_vivo").length?`
        <div class="digest" style="border-color:var(--red);background:#FEF2F2">
          <div style="font-size:1.9rem">🔴</div>
          <div style="flex:1"><b>¡Tu clase está EN VIVO ahora!</b>
            ${d.salas_vivo.filter(s=>s.estado==="en_vivo").map(s=>`<div class="small">${esc(s.titulo)}</div>`).join("")}
            <div class="small muted">Aunque no puedas ir al colegio, entra y sigue la misma clase a la misma hora.</div></div>
          <button class="btn btn-danger" onclick="irVista('alsalas')">Entrar a la clase →</button>
        </div>`:""}
      <div class="card"><div class="card-head"><h3>📝 Lo que tienes pendiente</h3>
        <span class="small muted">ordenado por fecha de entrega</span></div><div class="card-body">
        ${pend.map(p=>`
          <div class="al-pend ${p.urgente?'urg':''}">
            <div><b>${TIPO_ICO[p.tipo]||"📝"} ${esc(p.titulo)}</b>
              <div class="small muted">${esc(p.materia||"")}${p.fecha_limite?` · entrega ${esc(p.fecha_limite)}`:""}</div></div>
            <div style="display:flex;gap:8px;align-items:center">
              ${p.dias!=null?`<span class="dias">${p.dias<0?"¡VENCIDA!":p.dias===0?"¡HOY!":p.dias===1?"Mañana":"En "+p.dias+" días"}</span>`:""}
              <button class="btn btn-sm btn-primary" onclick="alVerActividad(${p.actividad_id})">Ver y entregar</button>
            </div>
          </div>`).join("")||'<div class="empty">¡Estás al día! No tienes tareas pendientes 🎉</div>'}
      </div></div>
      <div class="grid-cards">
        <div class="va-card" onclick="irVista('alclases')" style="cursor:pointer">
          <div style="font-size:2.2rem">📚</div><h4>Mis clases</h4>
          <div class="small muted">Revisa el contenido, los materiales y descarga las guías en PDF.</div></div>
        <div class="va-card" onclick="irVista('alcurso')" style="cursor:pointer">
          <div style="font-size:2.2rem">🧮</div><h4>Curso de Contabilidad</h4>
          <div class="small muted">Aprende a manejar una empresa: inventarios, arqueos, facturas y DIAN. ${d.curso_contabilidad.completadas}/${d.curso_contabilidad.total} lecciones.</div></div>
        <div class="va-card" onclick="irVista('alnotas')" style="cursor:pointer">
          <div style="font-size:2.2rem">📗</div><h4>Mis notas</h4>
          <div class="small muted">Mira cómo vas en cada materia y qué necesitas mejorar.</div></div>
      </div>`);
  }catch(e){ main(`<div class="empty">Error cargando tu tablero</div>`); }
};

VISTAS.alclases = async function(){
  loading();
  try{
    const cl = await api(`/alumno/clases?estudiante_id=${ST.estudiante_id}`);
    window._alClases = cl;
    const ICO_FONDO = {clase:"🧑‍🏫",taller:"📝",evaluacion:"🧪",curso:"📚",video:"🎬",lectura:"📖",foro:"💬",recuperacion:"♻️"};
    main(head("Mis clases","Todo el contenido que tu docente ha publicado para tu salón")+`
      <div class="grid-cards">
        ${cl.map(c=>`
          <div class="clase-card" onclick="alVerActividad(${c.id})">
            <div class="clase-portada">${ICO_FONDO[c.tipo]||"📘"}
              <span class="est">${c.mi_estado==="revisado"?"✅ Calificado":c.mi_estado==="entregado"?"📤 Entregado":c.fecha_limite?"⏳ Pendiente":"📖 Material"}</span></div>
            <div class="clase-body">
              <h4>${esc(c.titulo)}</h4>
              <div class="small muted">${esc(c.materia||"")} · ${esc(c.docente)}</div>
              ${c.fecha_limite?`<div class="small" style="color:var(--orange);margin-top:4px">📅 Entrega: ${esc(c.fecha_limite)}</div>`:""}
              ${c.mi_nota!=null?`<div class="small" style="color:var(--green);margin-top:3px"><b>Nota: ${c.mi_nota}</b></div>`:""}
              ${c.n_sub?`<span class="badge b-purple" style="margin-top:5px">🔗 ${c.n_sub} actividad(es)</span>`:""}
            </div>
          </div>`).join("")||'<div class="empty">Tu docente aún no ha publicado clases.</div>'}
      </div>`);
  }catch(e){ main(`<div class="empty">Error</div>`); }
};

VISTAS.altareas = async function(){
  loading();
  try{
    const [tb, cl] = await Promise.all([
      api(`/alumno/tablero?estudiante_id=${ST.estudiante_id}`),
      api(`/alumno/clases?estudiante_id=${ST.estudiante_id}`),
    ]);
    window._alClases = cl;
    const conEntrega = cl.filter(c=>c.mi_estado!=="sin_entrega" || c.fecha_limite);
    main(head("Tareas y talleres","Lo que debes entregar, lo que ya entregaste y lo que te calificaron")+`
      <div class="kpis">
        <div class="kpi orange"><div class="kpi-ico">⏳</div><div class="kpi-val">${tb.pendientes.length}</div><div class="kpi-lbl">Pendientes</div></div>
        <div class="kpi"><div class="kpi-ico">📤</div><div class="kpi-val">${cl.filter(c=>c.mi_estado==="entregado").length}</div><div class="kpi-lbl">Entregadas (esperando nota)</div></div>
        <div class="kpi green"><div class="kpi-ico">✅</div><div class="kpi-val">${cl.filter(c=>c.mi_estado==="revisado").length}</div><div class="kpi-lbl">Calificadas</div></div>
      </div>
      <div class="card"><div class="tbl-scroll"><table>
        <thead><tr><th>Actividad</th><th>Materia</th><th>Entrega</th><th>Estado</th><th>Nota</th><th></th></tr></thead>
        <tbody>${conEntrega.map(c=>`<tr>
          <td><b>${TIPO_ICO[c.tipo]||"📝"} ${esc(c.titulo)}</b></td>
          <td class="small">${esc(c.materia||"—")}</td>
          <td class="small">${c.fecha_limite?esc(c.fecha_limite):"—"}</td>
          <td>${c.mi_estado==="revisado"?'<span class="badge b-green">Calificado</span>':c.mi_estado==="entregado"?'<span class="badge b-blue">Entregado</span>':'<span class="badge b-orange">Pendiente</span>'}</td>
          <td>${c.mi_nota!=null?`<b>${c.mi_nota}</b>`:"—"}</td>
          <td><button class="btn btn-xs btn-primary" onclick="alVerActividad(${c.id})">${c.mi_estado==="sin_entrega"?"Entregar":"Ver"}</button></td>
        </tr>`).join("")||'<tr><td colspan="6" class="empty">Sin tareas asignadas.</td></tr>'}
      </tbody></table></div></div>`);
  }catch(e){ main(`<div class="empty">Error</div>`); }
};

async function alVerActividad(id){
  try{
    const a = await api(`/alumno/actividad?actividad_id=${id}&estudiante_id=${ST.estudiante_id}`);
    if(!a.ok){ toast("No se pudo abrir",true); return; }
    window._alAct = a;
    const en = a.mi_entrega||{};
    const yaEntregado = en.estado==="entregado"||en.estado==="revisado";
    document.getElementById("modal-srd-title").textContent = `${TIPO_ICO[a.tipo]||"📝"} ${a.titulo}`;
    document.getElementById("modal-srd-body").innerHTML = `
      <div class="info-grid">
        <div class="info-it"><span class="k">Materia</span><b>${esc(a.materia||"—")}</b></div>
        <div class="info-it"><span class="k">Tipo</span><b>${esc(a.tipo)}</b></div>
        <div class="info-it"><span class="k">Fecha de entrega</span><b>${a.fecha_limite||"Sin fecha"}</b></div>
        ${a.tiempo_limite_min?`<div class="info-it"><span class="k">⏱️ Tiempo</span><b>${a.tiempo_limite_min} min</b></div>`:""}
      </div>
      ${a.reglas?`<div class="legal-note">📏 <b>Reglas:</b> ${esc(a.reglas)}</div>`:""}
      <div class="card"><div class="card-head"><h3>📖 Contenido de la clase</h3>
        <button class="btn btn-sm btn-gold" onclick="window.open(API+'/aula/actividades/guia?id=${a.id}')">⬇️ Descargar guía PDF</button></div>
      <div class="card-body">
        <p style="white-space:pre-line;line-height:1.65">${esc(a.descripcion||"Sin descripción.")}</p>
        <div style="margin-top:10px">${(a.materiales||[]).map(m=>`<span class="mat-chip">${MAT_ICO[m.tipo]||"📎"} ${esc(m.nombre)}</span>`).join("")||'<span class="small muted">Sin materiales adjuntos.</span>'}</div>
      </div></div>
      ${a.sub.length?`<b class="small">🔗 Actividades de esta clase</b>
        ${a.sub.map(s=>`<div class="obs-item obs-compromiso" style="display:flex;justify-content:space-between;align-items:center;cursor:pointer" onclick="alVerActividad(${s.id})">
          <div><b>${TIPO_ICO[s.tipo]||"📝"} ${esc(s.titulo)}</b>${s.fecha_limite?`<div class="small muted">Entrega: ${esc(s.fecha_limite)}</div>`:""}</div>
          <span class="btn btn-xs">Abrir ▸</span></div>`).join("")}`:""}
      <div class="card" style="border:2px solid ${yaEntregado?'var(--green)':'var(--teal)'}">
        <div class="card-head"><h3>${yaEntregado?"✅ Tu entrega":"📤 Entregar mi trabajo"}</h3>
          ${en.nota!=null?`<span class="badge b-green">Nota: ${en.nota}</span>`:""}</div>
        <div class="card-body">
          ${en.retro?`<div class="legal-note">💬 <b>Comentario de tu docente:</b> ${esc(en.retro)}</div>`:""}
          <div class="frow"><label>Tu respuesta</label>
            <textarea id="al_resp" rows="5" placeholder="Escribe aquí tu respuesta, el desarrollo del taller o tus conclusiones…">${esc(en.respuesta||"")}</textarea></div>
          <div class="frow"><label>Adjuntar archivo (foto, PDF, documento)</label>
            <div class="dropzone" onclick="document.getElementById('al_file').click()">
              ${en.archivo?`📎 ${esc(en.archivo)} — toca para cambiar`:"📎 Toca para adjuntar tu trabajo"}</div>
            <input type="file" id="al_file" style="display:none" onchange="window._alArchivo=this.files[0]?this.files[0].name:null;this.previousElementSibling.innerHTML='📎 '+(window._alArchivo||'')">
          </div>
          <div style="text-align:right"><button class="btn btn-primary" onclick="alEntregar(${a.id})">${yaEntregado?"🔄 Actualizar entrega":"📤 Enviar entrega"}</button></div>
        </div></div>`;
    window._alArchivo = en.archivo || null;
    abrirModal("modal-srd");
  }catch(e){ toast("Error",true); }
}
async function alEntregar(id){
  const resp=document.getElementById("al_resp").value;
  try{
    const r=await post("/alumno/entregar",{actividad_id:id,estudiante_id:ST.estudiante_id,
      respuesta:resp, archivo:window._alArchivo||null});
    if(!r.ok){toast(r.msg,true);return;}
    cerrarModal("modal-srd"); toast(r.msg);
    if(ST.vista==="altareas") VISTAS.altareas(); else if(ST.vista==="alclases") VISTAS.alclases(); else VISTAS.altablero();
  }catch(e){ toast("Error al entregar",true); }
}

VISTAS.alnotas = async function(){
  loading();
  try{
    const d = await api(`/alumno/notas?estudiante_id=${ST.estudiante_id}`);
    const enRiesgo = d.materias.filter(m=>m.riesgo);
    main(head("Mis notas","Cómo vas en cada materia, período por período")+`
      ${enRiesgo.length?`<div class="digest" style="border-color:var(--red);background:#FEF2F2">
        <div style="font-size:1.9rem">⚠️</div><div style="flex:1">
        <b>Atención: ${enRiesgo.length} materia(s) por debajo de 3.0</b>
        <div class="small">${enRiesgo.map(m=>esc(m.materia)).join(", ")}</div>
        <div class="small muted">Aún estás a tiempo. Habla con tu docente, entrega los pendientes y pide apoyo — el sistema ya avisó para que te ayuden.</div></div></div>`:
        `<div class="digest"><div style="font-size:1.9rem">🎉</div><div><b>¡Vas bien!</b><div class="small muted">Ninguna materia por debajo de 3.0. Sigue así.</div></div></div>`}
      <div class="card"><div class="tbl-scroll"><table>
        <thead><tr><th>Materia</th>${d.periodos.map(p=>`<th style="text-align:center">P${p.numero}</th>`).join("")}<th style="text-align:center">Promedio</th></tr></thead>
        <tbody>${d.materias.map(m=>`<tr>
          <td><b>${esc(m.materia)}</b></td>
          ${d.periodos.map(p=>{const v=m.periodos[p.numero];
            return `<td style="text-align:center">${v!=null?`<span class="${v<3?'nota-mala':v>=4?'nota-buena':''}">${v}</span>`:"—"}</td>`;}).join("")}
          <td style="text-align:center"><b class="${m.riesgo?'nota-mala':m.promedio>=4?'nota-buena':''}">${m.promedio!=null?m.promedio:"—"}</b></td>
        </tr>`).join("")||'<tr><td colspan="6" class="empty">Aún no tienes notas registradas.</td></tr>'}
      </tbody></table></div></div>`);
  }catch(e){ main(`<div class="empty">Error</div>`); }
};

VISTAS.alsalas = async function(){
  loading();
  try{
    const tb = await api(`/alumno/tablero?estudiante_id=${ST.estudiante_id}`);
    const salas = tb.salas_vivo||[];
    main(head("Clases en vivo","Si no puedes ir al colegio, sigue la misma clase a la misma hora desde aquí")+`
      ${salas.map(s=>`
        <div class="card"><div class="card-head">
          <h3>${esc(s.titulo)}</h3>
          ${s.estado==="en_vivo"?'<span class="vivo-badge">EN VIVO</span>':'<span class="badge b-gray">Programada</span>'}</div>
        <div class="card-body">
          ${s.estado==="en_vivo"?`
            <div class="legal-note">🎥 La clase está transmitiéndose ahora. Tus compañeros presenciales están en el salón; tú sigues la misma explicación desde casa y puedes preguntar por el chat.</div>
            <button class="btn btn-primary" onclick="entrarSalaVivo(${s.id})">🎥 Entrar con cámara →</button>
            <button class="btn btn-sm" onclick="alEntrarSala(${s.id},'${esc(s.titulo)}')">💬 Solo chat</button>`:
            `<div class="small muted">Esta sala aún no ha iniciado. Te avisaremos cuando tu docente la ponga en vivo.</div>`}
        </div></div>`).join("")||'<div class="empty">No hay clases en vivo programadas para tu salón.</div>'}`);
  }catch(e){ main(`<div class="empty">Error</div>`); }
};
async function alEntrarSala(id,titulo){
  window._salaId=id;
  document.getElementById("modal-srd-title").textContent="🎥 "+titulo;
  await pintarSalaChat(id,"alumno");
  abrirModal("modal-srd");
}
async function pintarSalaChat(id, comoTipo){
  try{
    const d = await api(`/alumno/sala?sala_id=${id}`);
    const nombre = comoTipo==="docente" ? ST.perfil.nombre : (ST.perfil.nombre||"Estudiante");
    document.getElementById("modal-srd-body").innerHTML = `
      ${d.estado==="en_vivo"?'<div style="margin-bottom:10px"><span class="vivo-badge">EN VIVO</span> <span class="small muted">La clase está en curso — el docente modera el chat.</span></div>':''}
      <div class="chat-box" id="chat-box">
        ${d.mensajes.map(m=>`<div class="chat-msg ${m.autor_tipo==='docente'?'doc':''}">
          <div class="bub"><div class="aut">${m.autor_tipo==='docente'?'🧑‍🏫 ':'🎒 '}${esc(m.autor)} · ${esc(m.fecha)}</div>${esc(m.texto)}</div></div>`).join("")
          ||'<div class="empty">Sé el primero en escribir 👋</div>'}
      </div>
      <div style="display:flex;gap:8px">
        <input id="chat-in" placeholder="Escribe tu mensaje…" style="flex:1;padding:10px;border:1px solid var(--border);border-radius:9px"
          onkeyup="if(event.key==='Enter')enviarMsgSala(${id},'${comoTipo}')">
        <button class="btn btn-primary" onclick="enviarMsgSala(${id},'${comoTipo}')">Enviar</button>
      </div>
      <div class="small muted" style="margin-top:8px">💡 En producción esta sala incluye video en vivo (WebRTC) y funciona con baja conectividad: si se cae el internet, los mensajes se guardan y se envían al reconectar.</div>`;
    const cb=document.getElementById("chat-box"); if(cb) cb.scrollTop=cb.scrollHeight;
  }catch(e){ toast("Error",true); }
}
async function enviarMsgSala(id, comoTipo){
  const inp=document.getElementById("chat-in");
  const txt=inp.value.trim(); if(!txt) return;
  inp.value="";
  try{
    await post("/alumno/sala/mensaje",{sala_id:id,autor_tipo:comoTipo,
      autor_id: comoTipo==="docente"?ST.perfil.personal_id:ST.estudiante_id,
      autor_nombre: ST.perfil.nombre, texto:txt});
    await pintarSalaChat(id, comoTipo);
  }catch(e){ toast("Error al enviar",true); }
}

/* (visor de cursos v5 reemplaza la versión anterior) */
function respQuiz(i,j){
  window._quizResp[i]=j;
  const l=window._lec;
  l.quiz[i].op.forEach((_,k)=>{
    const el=document.getElementById(`q${i}-${k}`);
    if(el) el.classList.toggle("sel", k===j);
  });
}
async function calificarQuiz(){
  const l=window._lec;
  let pts=0;
  l.quiz.forEach((q,i)=>{
    const r=window._quizResp[i];
    const ok = r===q.correcta;
    if(ok) pts++;
    q.op.forEach((_,k)=>{
      const el=document.getElementById(`q${i}-${k}`);
      if(!el) return;
      el.classList.remove("sel");
      if(k===q.correcta) el.classList.add("ok");
      else if(k===r) el.classList.add("mal");
    });
  });
  const pct = l.quiz.length ? Math.round(100*pts/l.quiz.length) : 100;
  const res=document.getElementById("quiz-res");
  if(res) res.innerHTML=`<div class="legal-note" style="background:${pct>=70?'#DCFCE7':'#FEF3C7'};border-color:${pct>=70?'var(--green)':'var(--gold)'}">
    ${pct>=70?"🎉":"💪"} <b>${pts} de ${l.quiz.length} correctas (${pct}%).</b> ${pct>=70?"¡Muy bien! Dominaste el tema.":"Repasa las secciones de arriba y vuelve a intentarlo — así se aprende."}</div>`;
  try{
    const r=await post("/alumno/leccion/completar",{leccion_id:l.id,estudiante_id:ST.estudiante_id,
      quiz_puntaje:pct, practica_data:window._prac||null});
    toast(r.msg,!r.ok);
    setTimeout(()=>{ cerrarModal("modal-srd"); VISTAS.alcurso(); }, 1600);
  }catch(e){ toast("Error",true); }
}

/* ── PRÁCTICAS INTERACTIVAS del curso ── */
function pintarPractica(tipo){
  if(tipo==="inventario") return practicaInventario();
  if(tipo==="arqueo") return practicaArqueo();
  if(tipo==="factura") return practicaFactura();
  if(tipo==="balance") return practicaBalance();
  if(tipo==="declaracion") return practicaDeclaracion();
  if(tipo==="flujo") return practicaFlujo();
  if(tipo==="nomina") return practicaNomina();
  return "";
}
function practicaInventario(){
  const p = window._prac || {productos:[]};
  window._prac = p;
  const total = (p.productos||[]).reduce((a,x)=>a+(x.cantidad*x.costo),0);
  const venta = (p.productos||[]).reduce((a,x)=>a+(x.cantidad*x.precio),0);
  return `<div class="prac-box">
    <b>🛠️ Práctica: arma tu inventario</b>
    <div class="small muted" style="margin-bottom:10px">Sube la foto de cada producto, su cantidad y sus precios. Igual que en un negocio real.</div>
    ${(p.productos||[]).map((x,i)=>`
      <div class="prod-item">
        <div class="prod-foto">${x.foto?`<img src="${x.foto}" style="width:100%;height:100%;object-fit:cover;border-radius:8px">`:"📦"}</div>
        <div style="flex:1"><b class="small">${esc(x.nombre)}</b>
          <div class="small muted">${x.cantidad} und · costo ${money(x.costo)} · venta ${money(x.precio)} · utilidad ${money((x.precio-x.costo)*x.cantidad)}</div></div>
        <button class="btn btn-xs btn-danger" onclick="window._prac.productos.splice(${i},1);document.getElementById('prac-cont').innerHTML=pintarPractica('inventario')">✕</button>
      </div>`).join("")}
    <div class="frow-3" style="margin-top:8px">
      <div><input id="pi_nom" placeholder="Producto"></div>
      <div><input id="pi_cant" type="number" placeholder="Cantidad" value="1"></div>
      <div><input id="pi_costo" type="number" placeholder="Costo"></div>
    </div>
    <div class="frow-2">
      <div><input id="pi_precio" type="number" placeholder="Precio de venta"></div>
      <div><button class="btn btn-sm" style="width:100%" onclick="document.getElementById('pi_foto').click()">📷 Foto del producto</button>
        <input type="file" id="pi_foto" accept="image/*" style="display:none" onchange="prodFoto(this)"></div>
    </div>
    <button class="btn btn-primary btn-sm" style="width:100%;margin-top:8px" onclick="addProducto()">➕ Agregar al inventario</button>
    ${(p.productos||[]).length?`<div class="legal-note" style="margin-top:10px">📊 <b>Tu inventario:</b> ${p.productos.length} producto(s) · Invertido: <b>${money(total)}</b> · Si vendes todo: <b>${money(venta)}</b> · Ganancia esperada: <b style="color:var(--green)">${money(venta-total)}</b></div>`:""}
  </div>`;
}
function prodFoto(inp){
  const f=inp.files[0]; if(!f) return;
  const rd=new FileReader();
  rd.onload=()=>{ window._prodFoto=rd.result; toast("Foto lista ✓"); };
  rd.readAsDataURL(f);
}
function addProducto(){
  const nom=document.getElementById("pi_nom").value.trim();
  if(!nom){ toast("Escribe el nombre del producto",true); return; }
  window._prac.productos = window._prac.productos||[];
  window._prac.productos.push({nombre:nom,
    cantidad:parseInt(document.getElementById("pi_cant").value)||1,
    costo:parseFloat(document.getElementById("pi_costo").value)||0,
    precio:parseFloat(document.getElementById("pi_precio").value)||0,
    foto:window._prodFoto||null});
  window._prodFoto=null;
  document.getElementById("prac-cont").innerHTML=pintarPractica("inventario");
}
function practicaArqueo(){
  const p=window._prac||{}; window._prac=p;
  return `<div class="prac-box">
    <b>🛠️ Práctica: haz un arqueo de caja</b>
    <div class="small muted" style="margin-bottom:10px">Cierra la caja del día y descubre si cuadra.</div>
    <div class="frow-3">
      <div><label class="small">Saldo inicial</label><input id="ar_ini" type="number" value="${p.inicial||100000}" oninput="calcArqueo()"></div>
      <div><label class="small">Ventas en efectivo</label><input id="ar_ventas" type="number" value="${p.ventas||0}" oninput="calcArqueo()"></div>
      <div><label class="small">Retiros / gastos</label><input id="ar_retiros" type="number" value="${p.retiros||0}" oninput="calcArqueo()"></div>
    </div>
    <div class="frow"><label class="small">💵 Efectivo que CONTASTE en la caja</label><input id="ar_contado" type="number" value="${p.contado||0}" oninput="calcArqueo()"></div>
    <div id="ar_res"></div>
  </div>`;
}
function calcArqueo(){
  const ini=parseFloat(document.getElementById("ar_ini").value)||0;
  const ven=parseFloat(document.getElementById("ar_ventas").value)||0;
  const ret=parseFloat(document.getElementById("ar_retiros").value)||0;
  const con=parseFloat(document.getElementById("ar_contado").value)||0;
  const esp=ini+ven-ret, dif=con-esp;
  window._prac={inicial:ini,ventas:ven,retiros:ret,contado:con,diferencia:dif};
  document.getElementById("ar_res").innerHTML=`
    <div class="legal-note" style="background:${dif===0?'#DCFCE7':'#FEE2E2'};border-color:${dif===0?'var(--green)':'var(--red)'}">
      <b>Efectivo esperado:</b> ${money(esp)} &nbsp;·&nbsp; <b>Contado:</b> ${money(con)}<br>
      <b style="font-size:1.05rem">${dif===0?"✅ ¡La caja CUADRA perfecto!":dif>0?`⚠️ SOBRANTE de ${money(dif)}`:`🚨 FALTANTE de ${money(Math.abs(dif))}`}</b>
      <div class="small">${dif===0?"Así debe quedar siempre: cada peso justificado.":dif>0?"Un sobrante también es un problema: significa que algo no se registró.":"Debes investigar: ¿faltó registrar una salida o hay un descuadre?"}</div>
    </div>`;
}
function practicaFactura(){
  const p=window._prac||{items:[]}; window._prac=p;
  const sub=(p.items||[]).reduce((a,x)=>a+x.cant*x.valor,0);
  const iva=Math.round(sub*0.19);
  return `<div class="prac-box">
    <b>🛠️ Práctica: arma una factura con IVA</b>
    <div class="small muted" style="margin-bottom:10px">Agrega los productos y mira cómo se calcula el IVA del 19%.</div>
    <div class="frow-2"><div><input id="fa_cli" placeholder="Cliente" value="${esc(p.cliente||"")}" oninput="window._prac.cliente=this.value"></div>
      <div><input id="fa_nit" placeholder="NIT / cédula" value="${esc(p.nit||"")}" oninput="window._prac.nit=this.value"></div></div>
    ${(p.items||[]).map((x,i)=>`<div class="prod-item"><div style="flex:1"><b class="small">${esc(x.desc)}</b>
      <div class="small muted">${x.cant} × ${money(x.valor)} = ${money(x.cant*x.valor)}</div></div>
      <button class="btn btn-xs btn-danger" onclick="window._prac.items.splice(${i},1);document.getElementById('prac-cont').innerHTML=pintarPractica('factura')">✕</button></div>`).join("")}
    <div class="frow-3">
      <div><input id="fa_desc" placeholder="Descripción"></div>
      <div><input id="fa_cant" type="number" placeholder="Cant" value="1"></div>
      <div><input id="fa_val" type="number" placeholder="Valor unit."></div>
    </div>
    <button class="btn btn-sm btn-primary" style="width:100%" onclick="addItemFactura()">➕ Agregar ítem</button>
    ${(p.items||[]).length?`<div class="legal-note" style="margin-top:10px;font-family:monospace">
      Subtotal: <b>${money(sub)}</b><br>IVA (19%): <b>${money(iva)}</b><br>
      <span style="font-size:1.1rem">TOTAL: <b>${money(sub+iva)}</b></span></div>`:""}
  </div>`;
}
function addItemFactura(){
  const d=document.getElementById("fa_desc").value.trim();
  if(!d){ toast("Escribe la descripción",true); return; }
  window._prac.items=window._prac.items||[];
  window._prac.items.push({desc:d,cant:parseInt(document.getElementById("fa_cant").value)||1,
    valor:parseFloat(document.getElementById("fa_val").value)||0});
  document.getElementById("prac-cont").innerHTML=pintarPractica("factura");
}
function practicaBalance(){
  const p=window._prac||{}; window._prac=p;
  return `<div class="prac-box">
    <b>🛠️ Práctica: cuadra un balance general</b>
    <div class="small muted" style="margin-bottom:10px">Recuerda la regla de oro: Activo = Pasivo + Patrimonio.</div>
    <div class="frow-3">
      <div><label class="small">Activos (lo que tienes)</label><input id="ba_act" type="number" value="${p.activo||0}" oninput="calcBalance()"></div>
      <div><label class="small">Pasivos (lo que debes)</label><input id="ba_pas" type="number" value="${p.pasivo||0}" oninput="calcBalance()"></div>
      <div><label class="small">Patrimonio (lo tuyo)</label><input id="ba_pat" type="number" value="${p.patrimonio||0}" oninput="calcBalance()"></div>
    </div>
    <div id="ba_res"></div>
  </div>`;
}
function calcBalance(){
  const a=parseFloat(document.getElementById("ba_act").value)||0;
  const pa=parseFloat(document.getElementById("ba_pas").value)||0;
  const pt=parseFloat(document.getElementById("ba_pat").value)||0;
  const dif=a-(pa+pt);
  window._prac={activo:a,pasivo:pa,patrimonio:pt};
  document.getElementById("ba_res").innerHTML=`
    <div class="legal-note" style="background:${dif===0?'#DCFCE7':'#FEF3C7'};border-color:${dif===0?'var(--green)':'var(--gold)'}">
      ${money(a)} = ${money(pa)} + ${money(pt)} → ${money(pa+pt)}<br>
      <b>${dif===0?"✅ ¡Balance CUADRADO! Así debe ser siempre.":`⚠️ Descuadre de ${money(Math.abs(dif))}. ${dif>0?"El patrimonio debería ser "+money(a-pa):"Revisa tus cifras."}`}</b></div>`;
}
function practicaDeclaracion(){
  const p=window._prac||{}; window._prac=p;
  return `<div class="prac-box">
    <b>🛠️ Práctica: calcula tu declaración de IVA</b>
    <div class="small muted" style="margin-bottom:10px">IVA a pagar = IVA cobrado en ventas − IVA pagado en compras.</div>
    <div class="frow-2">
      <div><label class="small">IVA cobrado (ventas)</label><input id="de_ven" type="number" value="${p.iva_ventas||0}" oninput="calcDeclaracion()"></div>
      <div><label class="small">IVA pagado (compras)</label><input id="de_com" type="number" value="${p.iva_compras||0}" oninput="calcDeclaracion()"></div>
    </div>
    <div id="de_res"></div>
  </div>`;
}
function calcDeclaracion(){
  const v=parseFloat(document.getElementById("de_ven").value)||0;
  const c=parseFloat(document.getElementById("de_com").value)||0;
  const saldo=v-c;
  window._prac={iva_ventas:v,iva_compras:c,saldo};
  document.getElementById("de_res").innerHTML=`
    <div class="legal-note" style="background:${saldo>=0?'#DBEAFE':'#DCFCE7'};border-color:var(--blue)">
      ${money(v)} − ${money(c)} = <b style="font-size:1.05rem">${money(Math.abs(saldo))}</b><br>
      <b>${saldo>0?`🏛️ Debes PAGARLE ${money(saldo)} a la DIAN.`:saldo<0?`💚 Tienes un saldo A FAVOR de ${money(Math.abs(saldo))}.`:"Ni pagas ni te devuelven: quedó en cero."}</b>
      <div class="small">Recuerda: declarar a tiempo evita sanciones. Guarda todas tus facturas como soporte.</div></div>`;
}

/* ═══ V4 · SOLICITUDES DE SALÓN (punto 14) ═══ */
VISTAS.solicitudes = async function(t){
  loading();
  try{
    t = t||"pendientes";
    const sols = await api(`/academico/solicitudes?institucion_id=${ST.institucion_id}`);
    const pend = sols.filter(s=>s.estado==="pendiente");
    const hist = sols.filter(s=>s.estado!=="pendiente");
    const lista = t==="pendientes"?pend:hist;
    main(head("Solicitudes de asignación a salón","Los docentes piden su salón; tú apruebas o rechazas — así nadie crea salones por su cuenta")+`
      <div class="subtabs">
        ${[["pendientes",`📨 Pendientes (${pend.length})`],["historial",`📚 Historial (${hist.length})`]].map(([k,l])=>
          `<button class="subtab ${t===k?'active':''}" onclick="VISTAS.solicitudes('${k}')">${l}</button>`).join("")}</div>
      ${lista.map(s=>`
        <div class="card"><div class="card-body">
          <div style="display:flex;gap:14px;align-items:center;flex-wrap:wrap">
            ${s.foto?`<img class="avatar-foto" src="${s.foto}">`:`<div class="avatar-sm">${ini(s.docente)}</div>`}
            <div style="flex:1;min-width:200px">
              <b>${esc(s.docente)}</b>
              <div class="small muted">${esc(s.profesion||"—")} · ${s.experiencia} años de experiencia</div>
              <div class="small">Solicita: <b>${s.rol_solicitado==="director"?"👑 Director(a) de grupo":"👨‍🏫 Docente de materia"}</b> en el <b>salón ${esc(s.salon)}</b>${s.materia?` · ${esc(s.materia)}`:""}</div>
              <div class="small muted">${esc(s.fecha)}</div>
            </div>
            <div>${s.estado==="pendiente"?`
              <button class="btn btn-sm btn-green" onclick="resolverSolicitud(${s.id},true)">✅ Aprobar</button>
              <button class="btn btn-sm btn-danger" onclick="resolverSolicitud(${s.id},false)">✕ Rechazar</button>`:
              s.estado==="aprobada"?'<span class="badge b-green">Aprobada</span>':'<span class="badge b-red">Rechazada</span>'}</div>
          </div>
          ${s.nota?`<div class="small muted" style="margin-top:6px">📝 ${esc(s.nota)}</div>`:""}
        </div></div>`).join("")||`<div class="empty">${t==="pendientes"?"No hay solicitudes pendientes 🎉":"Sin historial."}</div>`}
      <div class="legal-note">🔐 Los docentes <b>no pueden crear salones</b>: solo rectoría y coordinación. El docente busca su salón y solicita la asignación; aquí queda el registro de quién aprobó y cuándo.</div>`);
  }catch(e){ main(`<div class="empty">Error</div>`); }
};
async function resolverSolicitud(id, aprobar){
  const nota = aprobar ? "" : (prompt("Motivo del rechazo (el docente lo verá):")||"");
  if(!aprobar && nota===null) return;
  try{ const r=await post("/academico/solicitudes/resolver",{id,aprobar,nota});
    toast(r.msg,!r.ok); if(r.ok) VISTAS.solicitudes();
  }catch(e){ toast("Error",true); }
}

/* Docente: buscar salón y solicitar asignación */
async function buscarSalonDocente(){
  try{
    const salones = await api(`/academico/salones/buscar?institucion_id=${ST.institucion_id}`);
    const mias = await api(`/academico/solicitudes?institucion_id=${ST.institucion_id}&personal_id=${ST.perfil.personal_id}`);
    window._salBuscar = salones;
    document.getElementById("modal-srd-title").textContent="🔎 Buscar mi salón y solicitar asignación";
    document.getElementById("modal-srd-body").innerHTML=`
      <div class="legal-note">Los salones los crea rectoría o coordinación. Busca el tuyo y <b>solicita la asignación</b>: te avisamos apenas la aprueben.</div>
      ${mias.length?`<b class="small">Mis solicitudes</b>
        ${mias.map(s=>`<div class="obs-item ${s.estado==='aprobada'?'obs-compromiso':''}" style="display:flex;justify-content:space-between;align-items:center">
          <div><b>Salón ${esc(s.salon)}</b> · ${s.rol_solicitado==="director"?"Director de grupo":"Docente"} ${s.materia?"· "+esc(s.materia):""}</div>
          <span class="badge ${s.estado==='aprobada'?'b-green':s.estado==='rechazada'?'b-red':'b-orange'}">${esc(s.estado)}</span>
        </div>`).join("")}<hr style="margin:14px 0;border:none;border-top:1px solid var(--border)">`:""}
      <input id="bs_q" placeholder="Escribe el grado o el nombre del salón (ej: 6, 602)…" oninput="filtrarSalonesBuscar()" style="width:100%;padding:10px;border:1px solid var(--border);border-radius:9px;margin-bottom:10px">
      <div id="bs_lista"></div>`;
    filtrarSalonesBuscar();
    abrirModal("modal-srd");
  }catch(e){ toast("Error",true); }
}
function filtrarSalonesBuscar(){
  const q=(document.getElementById("bs_q").value||"").toLowerCase();
  const lista=(window._salBuscar||[]).filter(s=>!q||s.nombre.toLowerCase().includes(q)||String(s.grado).includes(q));
  document.getElementById("bs_lista").innerHTML=lista.map(s=>`
    <div class="obs-item" style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap">
      <div><b>Salón ${esc(s.nombre)}</b> <span class="badge b-blue">Grado ${esc(s.grado)}</span>
        <div class="small muted">${s.n_estudiantes} estudiantes · ${esc(s.jornada)} · Director: ${s.director?esc(s.director):"<b>sin asignar</b>"}</div></div>
      <div style="display:flex;gap:6px">
        ${s.libre?`<button class="btn btn-xs btn-primary" onclick="solicitarSalon(${s.id},'director')">👑 Ser director</button>`:""}
        <button class="btn btn-xs" onclick="solicitarSalon(${s.id},'docente')">👨‍🏫 Dar clase aquí</button>
      </div>
    </div>`).join("")||'<div class="empty">Sin resultados.</div>';
}
async function solicitarSalon(salon_id, rol){
  const materia = rol==="docente" ? (prompt("¿Qué materia dictas en ese salón?","Matemáticas")||"") : "";
  if(rol==="docente" && materia===null) return;
  try{
    const r=await post("/academico/solicitudes/crear",{institucion_id:ST.institucion_id,
      personal_id:ST.perfil.personal_id, salon_id, rol_solicitado:rol, materia});
    toast(r.msg,!r.ok);
    if(r.ok) cerrarModal("modal-srd");
  }catch(e){ toast("Error",true); }
}

/* ═══ V4 · SALAS EN VIVO DEL DOCENTE (puntos 4 y 12) ═══ */
VISTAS.salas = async function(){
  loading();
  try{
    const salas = await api(`/aula/salas?institucion_id=${ST.institucion_id}`);
    const mis = (window._misSalones||[]);
    main(head("Clases en vivo","Transmite tu clase presencial para los estudiantes que no pueden asistir — misma clase, misma hora",
      `<button class="btn btn-primary" onclick="nuevaSala()">🎥 Nueva clase en vivo</button>`)+`
      <div class="legal-note">🌐 <b>Clase híbrida:</b> mientras das la clase en el salón, los estudiantes en casa (o en veredas sin transporte) siguen la misma explicación y preguntan por el chat. Tú moderas.</div>
      ${salas.map(s=>`
        <div class="card"><div class="card-head">
          <h3>${esc(s.titulo)}</h3>
          ${s.estado==="en_vivo"?'<span class="vivo-badge">EN VIVO</span>':s.estado==="finalizada"?'<span class="badge b-gray">Finalizada</span>':'<span class="badge b-blue">Programada</span>'}</div>
        <div class="card-body">
          <div class="small muted">Salón ${esc(s.salon)} · ${s.n_mensajes} mensajes · ${esc(s.fecha)}</div>
          <div style="margin-top:10px;display:flex;gap:7px;flex-wrap:wrap">
            <button class="btn btn-sm btn-primary" onclick="entrarSalaVivo(${s.id})">🎥 Dictar con cámara</button>
            <button class="btn btn-sm" onclick="abrirSalaDocente(${s.id},'${esc(s.titulo)}')">💬 Chat</button>
            ${s.estado!=="en_vivo"?`<button class="btn btn-sm btn-danger" onclick="cambiarEstadoSala(${s.id},'en_vivo')">🔴 Poner EN VIVO</button>`:
              `<button class="btn btn-sm" onclick="cambiarEstadoSala(${s.id},'finalizada')">⏹️ Finalizar</button>`}
          </div>
        </div></div>`).join("")||'<div class="empty">Aún no has creado clases en vivo.</div>'}`);
  }catch(e){ main(`<div class="empty">Error</div>`); }
};
async function nuevaSala(){
  const mis=(window._misSalones||[]);
  let salonId = ST.salon_id;
  if(mis.length>1){
    const opts=mis.map(s=>`${s.id}: Salón ${s.nombre}`).join("\n");
    const sel=prompt(`¿Para cuál salón?\n\n${opts}`); if(!sel) return;
    salonId=parseInt(sel)||salonId;
  }
  const titulo=prompt("Título de la clase en vivo:","Clase de Matemáticas en vivo");
  if(!titulo) return;
  try{ const r=await post("/aula/salas/crear",{salon_id:salonId,titulo,docente_id:ST.perfil.personal_id});
    toast(r.msg,!r.ok); if(r.ok) VISTAS.salas();
  }catch(e){ toast("Error",true); }
}
async function cambiarEstadoSala(id,estado){
  try{ const r=await post("/aula/salas/estado",{id,estado}); toast(r.msg,!r.ok); if(r.ok) VISTAS.salas(); }
  catch(e){ toast("Error",true); }
}
async function abrirSalaDocente(id,titulo){
  document.getElementById("modal-srd-title").textContent="🎥 "+titulo+" (moderador)";
  await pintarSalaChat(id,"docente");
  abrirModal("modal-srd");
}

/* ═══ V4 · PAGOS CON EVIDENCIA (punto 27) ═══ */
VISTAS.pagos = async function(){
  loading();
  try{
    const d = await api(`/contratos/pagos?institucion_id=${ST.institucion_id}`);
    main(head("Pagos de contratos","Qué está pendiente por pagar y qué ya se pagó — cada pago con su evidencia")+`
      <div class="kpis">
        <div class="kpi red"><div class="kpi-ico">⏳</div><div class="kpi-val">${d.n_pendientes}</div><div class="kpi-lbl">Pagos pendientes</div></div>
        <div class="kpi orange"><div class="kpi-ico">💰</div><div class="kpi-val sm">${money(d.total_pendiente)}</div><div class="kpi-lbl">Por pagar</div></div>
        <div class="kpi green"><div class="kpi-ico">✅</div><div class="kpi-val sm">${money(d.total_pagado)}</div><div class="kpi-lbl">Pagado con evidencia</div></div>
      </div>
      <div class="card"><div class="tbl-scroll"><table>
        <thead><tr><th>Contrato</th><th>Concepto</th><th>Contratista</th><th style="text-align:right">Valor</th><th>Programado</th><th>Estado</th><th>Evidencia</th><th></th></tr></thead>
        <tbody>${d.pagos.map(p=>`<tr>
          <td><b>${esc(p.contrato)}</b></td>
          <td class="small">${esc(p.concepto)}</td>
          <td class="small">${esc(p.contratista)}</td>
          <td style="text-align:right"><b>${money(p.valor)}</b></td>
          <td class="small">${p.fecha_programada||"—"}</td>
          <td>${p.estado==="pagado"?'<span class="badge b-green">Pagado</span>':'<span class="badge b-orange">Pendiente</span>'}</td>
          <td class="small">${p.evidencia?`📎 ${esc(p.evidencia)}<div class="muted">${p.fecha_pago||""}</div>`:"—"}</td>
          <td>${p.estado==="pendiente"?`<button class="btn btn-xs btn-green" onclick="abrirMarcarPago(${p.id},'${esc(p.concepto)}',${p.valor})">💸 Marcar pagado</button>`:""}</td>
        </tr>`).join("")||'<tr><td colspan="8" class="empty">Sin pagos registrados.</td></tr>'}
      </tbody></table></div></div>
      <div class="audit-note">🧾 <b>Sin evidencia no hay pago:</b> el sistema exige adjuntar el comprobante antes de marcar como pagado, y genera automáticamente el egreso en el libro del FSE con su soporte. Eso es lo que revisa la Contraloría.</div>`);
  }catch(e){ main(`<div class="empty">Error</div>`); }
};
function abrirMarcarPago(id, concepto, valor){
  window._pagoId=id; window._pagoEvidencia=null;
  document.getElementById("modal-srd-title").textContent="💸 Registrar pago";
  document.getElementById("modal-srd-body").innerHTML=`
    <div class="info-grid">
      <div class="info-it"><span class="k">Concepto</span><b>${esc(concepto)}</b></div>
      <div class="info-it"><span class="k">Valor</span><b>${money(valor)}</b></div>
    </div>
    <div class="frow"><label>Método de pago</label><select id="pg_metodo">
      <option>Transferencia</option><option>Cheque</option><option>Efectivo</option></select></div>
    <div class="frow"><label>📎 Evidencia del pago (OBLIGATORIA)</label>
      <div class="dropzone" id="pg_drop" onclick="document.getElementById('pg_file').click()">Toca para adjuntar el comprobante de la transferencia o consignación</div>
      <input type="file" id="pg_file" style="display:none" onchange="window._pagoEvidencia=this.files[0]?this.files[0].name:null;document.getElementById('pg_drop').innerHTML='📎 '+(window._pagoEvidencia||'')">
    </div>
    <div class="frow"><label>Observación (opcional)</label><input id="pg_nota" placeholder="Ej: pago parcial acordado en acta"></div>
    <div class="legal-note">Al confirmar, el egreso queda registrado en el FSE con este soporte y aparece en la cronología de auditoría.</div>
    <div class="modal-foot" style="border:none;padding:14px 0 0">
      <button class="btn" onclick="cerrarModal('modal-srd')">Cancelar</button>
      <button class="btn btn-primary" onclick="confirmarPago()">💸 Confirmar pago</button></div>`;
  abrirModal("modal-srd");
}
async function confirmarPago(){
  if(!window._pagoEvidencia){ toast("Debes adjuntar la evidencia del pago 📎",true); return; }
  try{
    const r=await post("/contratos/pagos/marcar_pagado",{id:window._pagoId,
      metodo:document.getElementById("pg_metodo").value,
      evidencia:window._pagoEvidencia, nota:document.getElementById("pg_nota").value});
    if(!r.ok){toast(r.msg,true);return;}
    cerrarModal("modal-srd"); toast(r.msg); VISTAS.pagos();
  }catch(e){ toast("Error",true); }
}

/* ═══ V4 · RUBROS PRESUPUESTALES (punto 17) ═══ */
async function fseRubros(){
  const d = await api(`/fse/rubros?institucion_id=${ST.institucion_id}`);
  window._rubros = d.rubros;
  const puede = ["rector","contador"].includes(ST.perfil.rol);
  document.getElementById("fse-cont").innerHTML = `
    <div class="kpis">
      <div class="kpi"><div class="kpi-ico">📊</div><div class="kpi-val sm">${money(d.total_presupuesto)}</div><div class="kpi-lbl">Presupuestado</div></div>
      <div class="kpi orange"><div class="kpi-ico">📤</div><div class="kpi-val sm">${money(d.total_ejecutado)}</div><div class="kpi-lbl">Ejecutado</div></div>
      <div class="kpi green"><div class="kpi-ico">💰</div><div class="kpi-val sm">${money(d.total_disponible)}</div><div class="kpi-lbl">Disponible</div></div>
    </div>
    ${puede?`<div style="text-align:right;margin-bottom:10px"><button class="btn btn-primary btn-sm" onclick="editarRubro(0)">➕ Agregar rubro</button></div>`:""}
    <div class="card"><div class="tbl-scroll"><table>
      <thead><tr><th>Rubro</th><th>Código</th><th style="text-align:right">Presupuesto</th><th style="text-align:right">Ejecutado</th><th style="text-align:right">Disponible</th><th style="width:150px">Ejecución</th>${puede?'<th></th>':''}</tr></thead>
      <tbody>${d.rubros.map(r=>`<tr>
        <td><b>${esc(r.nombre)}</b></td>
        <td class="small">${esc(r.codigo||"—")}</td>
        <td style="text-align:right">${money(r.presupuesto)}</td>
        <td style="text-align:right">${money(r.ejecutado)}</td>
        <td style="text-align:right"><b style="color:${r.disponible<0?'var(--red)':'var(--green)'}">${money(r.disponible)}</b></td>
        <td><div class="flex-cell"><div class="prog" style="flex:1"><div class="prog-fill" style="width:${Math.min(100,r.pct_ejecutado)}%;background:${r.alerta?'var(--red)':r.pct_ejecutado>70?'var(--orange)':'var(--green)'}"></div></div><span class="small">${r.pct_ejecutado}%</span></div></td>
        ${puede?`<td style="white-space:nowrap"><button class="btn btn-xs" onclick="editarRubro(${r.id})">✎</button>
          <button class="btn btn-xs btn-danger" onclick="eliminarRubro(${r.id},'${esc(r.nombre)}')">🗑</button></td>`:''}
      </tr>`).join("")||'<tr><td colspan="7" class="empty">Sin rubros. Crea el primero.</td></tr>'}
      </tbody></table></div></div>
    ${d.egresos_sin_rubro?`<div class="legal-note" style="background:#FEF3C7;border-color:var(--gold)">⚠️ Hay <b>${money(d.egresos_sin_rubro)}</b> en egresos sin rubro asignado. Asígnalos para que la ejecución presupuestal quede completa.</div>`:""}
    <div class="legal-note">💡 Cada rubro muestra cuánto dinero queda realmente disponible. Cuando registras un ingreso o egreso puedes asignarlo a su rubro, y el sistema descuenta automáticamente — así el rector sabe siempre con cuánto cuenta en cada bolsillo.</div>`;
}
function editarRubro(id){
  const r=(window._rubros||[]).find(x=>x.id===id);
  const nombre=prompt("Nombre del rubro:", r?r.nombre:"");
  if(!nombre) return;
  const codigo=prompt("Código (opcional):", r?r.codigo:"")||"";
  const pres=parseFloat(prompt("Presupuesto asignado (COP):", r?r.presupuesto:"0"))||0;
  post("/fse/rubros/guardar",{id:id||0,institucion_id:ST.institucion_id,nombre,codigo,presupuesto:pres})
    .then(rr=>{ toast(rr.msg,!rr.ok); if(rr.ok) fseRubros(); })
    .catch(()=>toast("Error",true));
}
async function eliminarRubro(id,nombre){
  if(!confirm(`¿Eliminar el rubro «${nombre}»?`)) return;
  try{ const r=await post("/fse/rubros/eliminar",{id}); toast(r.msg,!r.ok); if(r.ok) fseRubros(); }
  catch(e){ toast("Error",true); }
}

/* ═══ V4 · CALENDARIO MENSUAL TIPO AFICHE (punto 10) ═══ */
let CAL_MES = null;
VISTAS.calendario = async function(modo){
  loading();
  try{
    const hoy=new Date();
    if(!CAL_MES) CAL_MES={y:hoy.getFullYear(), m:hoy.getMonth()};
    const [d, rec] = await Promise.all([
      api(`/aula/calendario?personal_id=${ST.perfil.personal_id}&dias=60`),
      api(`/aula/recordatorios?personal_id=${ST.perfil.personal_id}`),
    ]);
    window._calEventos = d.eventos;
    main(head("Mi calendario","Tus clases, obligaciones y cierres del aula — todo el mes de un vistazo",
      `<button class="btn btn-primary" onclick="abrirModalEvento()">➕ Agregar evento</button>`)+`
      ${rec.length?`<div class="digest"><div style="font-size:1.8rem">⏰</div><div style="flex:1">
        <b>Próximos vencimientos (${rec.length}):</b>
        ${rec.slice(0,4).map(r=>`<div class="small">• <b>${r.cuando}</b>${r.hora?" "+esc(r.hora):""} — ${esc(r.titulo)}</div>`).join("")}
        <div class="small muted" style="margin-top:4px">🔔 También te llegan como notificación del navegador y un día antes.</div></div></div>`:""}
      <div id="cal-cont"></div>`);
    pintarCalendarioMes();
  }catch(e){ main(`<div class="empty">Error</div>`); }
};
function pintarCalendarioMes(){
  const MES_N=["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
  const {y,m}=CAL_MES;
  const primero=new Date(y,m,1), ultimo=new Date(y,m+1,0);
  const inicioSem=(primero.getDay()+6)%7;   // lunes=0
  const hoyISOs=hoyISO();
  const porFecha={};
  (window._calEventos||[]).forEach(ev=>{ (porFecha[ev.fecha]=porFecha[ev.fecha]||[]).push(ev); });
  const COL={clase:"#CCFBF1|#0F766E",obligacion:"#EDE9FE|#6D28D9",pendiente:"#FFEDD5|#C2410C",evaluacion:"#FEE2E2|#B91C1C",reunion:"#DBEAFE|#1D4ED8"};
  let celdas="";
  for(let i=0;i<inicioSem;i++) celdas+=`<div class="cal-cell otro"></div>`;
  for(let dia=1;dia<=ultimo.getDate();dia++){
    const iso=`${y}-${String(m+1).padStart(2,"0")}-${String(dia).padStart(2,"0")}`;
    const evs=porFecha[iso]||[];
    const pend=evs.filter(e=>!e.done).length;
    celdas+=`<div class="cal-cell ${iso===hoyISOs?'hoy':''}" onclick="abrirDiaCal('${iso}')">
      <div class="cal-num">${dia}${pend?` <span class="badge b-red" style="font-size:.6rem;padding:1px 5px">${pend}</span>`:""}</div>
      ${evs.slice(0,3).map(e=>{const[bg,fg]=(COL[e.tipo]||"#F1F5F9|#334155").split("|");
        return `<span class="cal-chip" style="background:${bg};color:${fg};${e.done?'text-decoration:line-through;opacity:.6':''}">${esc((e.hora?e.hora.split("-")[0]+" ":"")+e.titulo)}</span>`;}).join("")}
      ${evs.length>3?`<div class="cal-mas">+${evs.length-3} más…</div>`:""}
    </div>`;
  }
  document.getElementById("cal-cont").innerHTML=`
    <div class="card"><div class="card-body">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;flex-wrap:wrap;gap:8px">
        <button class="btn btn-sm" onclick="moverMes(-1)">◂ Anterior</button>
        <b style="font-size:1.1rem">${MES_N[m]} ${y}</b>
        <button class="btn btn-sm" onclick="moverMes(1)">Siguiente ▸</button>
      </div>
      <div class="cal-grid">
        ${["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"].map(x=>`<div class="cal-hd">${x}</div>`).join("")}
        ${celdas}
      </div>
      <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">
        <span class="badge b-teal">🧑‍🏫 Clase</span><span class="badge b-purple">📌 Obligación</span>
        <span class="badge b-orange">☑️ Pendiente</span><span class="badge b-red">🧪 Evaluación</span>
        <span class="small muted" style="margin-left:auto">Toca cualquier día para ver el detalle, marcar hecho o agregar</span>
      </div>
    </div></div>`;
}
function moverMes(delta){
  let {y,m}=CAL_MES; m+=delta;
  if(m<0){m=11;y--;} if(m>11){m=0;y++;}
  CAL_MES={y,m}; pintarCalendarioMes();
}
function abrirDiaCal(iso){
  const evs=(window._calEventos||[]).filter(e=>e.fecha===iso);
  document.getElementById("modal-srd-title").textContent="🗓️ "+fechaBonita(iso);
  document.getElementById("modal-srd-body").innerHTML=`
    ${evs.map(ev=>`
      <div class="cal-ev t-${ev.tipo} ${ev.done?'donee':''}" style="margin-bottom:8px">
        <span class="hora">${ev.hora?esc(ev.hora):"—"}</span>
        <span class="titulo" style="flex:1">${esc(ev.titulo)}</span>
        ${ev.fuente==="agenda"&&ev.id?`
          <label class="small muted" style="display:flex;align-items:center;gap:5px;cursor:pointer">
            <input type="checkbox" ${ev.done?"checked":""} onchange="marcarEventoDia(${ev.id},this.checked,'${iso}')">${ev.done?"hecho":"marcar"}</label>
          <button class="btn btn-xs btn-danger" onclick="borrarEventoDia(${ev.id},'${iso}')">🗑</button>`:
          `<span class="small muted">${ev.fuente==="horario"?"horario":"aula"}</span>`}
      </div>`).join("")||'<div class="empty">Sin eventos este día.</div>'}
    <div style="text-align:right;margin-top:12px">
      <button class="btn btn-primary btn-sm" onclick="cerrarModal('modal-srd');abrirModalEvento('${iso}')">➕ Agregar evento este día</button></div>`;
  abrirModal("modal-srd");
}
async function marcarEventoDia(id,done,iso){
  try{ const r=await post("/aula/calendario/done",{id,done}); toast(r.msg,!r.ok);
    if(r.ok){ const ev=(window._calEventos||[]).find(x=>x.id===id&&x.fuente==="agenda"); if(ev) ev.done=done;
      pintarCalendarioMes(); abrirDiaCal(iso); }
  }catch(e){ toast("Error",true); }
}
async function borrarEventoDia(id,iso){
  if(!confirm("¿Eliminar este evento del calendario?")) return;
  try{ const r=await post("/aula/calendario/eliminar",{id}); toast(r.msg,!r.ok);
    if(r.ok){ window._calEventos=(window._calEventos||[]).filter(x=>!(x.id===id&&x.fuente==="agenda"));
      pintarCalendarioMes(); cerrarModal("modal-srd"); }
  }catch(e){ toast("Error",true); }
}

/* ═══ V4 · RIESGO ACADÉMICO → PADRES Y ALUMNOS (punto 11) ═══ */
async function vistaNotasRiesgo(){
  loading();
  main(head("Riesgo académico","Detección temprana del patrón «va a perder el año» — avisa a tiempo a acudientes y estudiantes")+`
    <div class="subtabs">
      <button class="subtab" onclick="VISTAS.notas()">📗 Planilla de notas</button>
      <button class="subtab active" onclick="VISTAS.notas('riesgo')">🚨 Riesgo académico y avisos</button>
    </div>
    <div id="notas-cont"><div class="empty">Analizando notas y tendencias…</div></div>`);
  try{ await notasRiesgo(); }
  catch(e){ document.getElementById("notas-cont").innerHTML='<div class="empty">Error</div>'; }
}

async function notasRiesgo(){
  const d = await api(`/academico/notas/riesgo_academico?institucion_id=${ST.institucion_id}`);
  document.getElementById("notas-cont").innerHTML = `
    <div class="kpis">
      <div class="kpi red"><div class="kpi-ico">🚨</div><div class="kpi-val">${d.filter(x=>x.nivel==="CRÍTICO").length}</div><div class="kpi-lbl">En riesgo de perder el año</div></div>
      <div class="kpi orange"><div class="kpi-ico">⚠️</div><div class="kpi-val">${d.filter(x=>x.nivel==="ALERTA").length}</div><div class="kpi-lbl">Con materias perdidas</div></div>
      <div class="kpi"><div class="kpi-ico">📉</div><div class="kpi-val">${d.filter(x=>x.tendencia<0).length}</div><div class="kpi-lbl">Bajando entre períodos</div></div>
    </div>
    <div class="card"><div class="card-head"><h3>Estudiantes que necesitan intervención</h3>
      <span class="small muted">el modelo cruza notas, tendencia y asistencia</span></div>
    <div class="tbl-scroll"><table>
      <thead><tr><th>Estudiante</th><th>Salón</th><th>Materias perdidas</th><th style="text-align:center">Promedio</th><th style="text-align:center">Tendencia</th><th style="text-align:center">Asistencia</th><th>Acciones</th></tr></thead>
      <tbody>${d.map(x=>`<tr>
        <td><div class="flex-cell"><div class="avatar-sm">${ini(x.nombre)}</div>
          <div><b>${esc(x.nombre)}</b>${x.nivel==="CRÍTICO"?' <span class="badge b-red">CRÍTICO</span>':''}
          <div class="small muted">👪 ${esc(x.acudiente||"—")}</div></div></div></td>
        <td class="small">${esc(x.salon)}</td>
        <td class="small">${x.materias_perdidas.map(m=>`<span class="badge b-red" style="margin:1px">${esc(m.materia)} ${m.promedio}</span>`).join("")}</td>
        <td style="text-align:center"><b class="nota-mala">${x.promedio_general}</b></td>
        <td style="text-align:center">${x.tendencia<0?`<span style="color:var(--red)">↓ ${x.tendencia}</span>`:`<span style="color:var(--green)">↑ ${x.tendencia}</span>`}</td>
        <td style="text-align:center">${x.pct_asistencia!=null?`${x.pct_asistencia}%`:"—"}</td>
        <td style="white-space:nowrap">
          <button class="btn btn-xs btn-primary" onclick="notificarPadre(${x.estudiante_id},'${esc(x.nombre)}')">📱 Avisar acudiente</button>
          <button class="btn btn-xs btn-gold" onclick="alertarAlumno(${x.estudiante_id},'${esc(x.nombre)}')">🔔 Alertar alumno</button>
        </td></tr>`).join("")||'<tr><td colspan="7" class="empty">🎉 Ningún estudiante con materias perdidas.</td></tr>'}
    </tbody></table></div></div>
    <div class="legal-note">🧠 <b>Detección temprana:</b> el sistema no espera a fin de año. Cruza las notas de cada período con la tendencia y la asistencia para identificar el patrón de "va a perder el año" mientras <b>todavía se puede hacer algo</b>. Cada aviso queda registrado como evidencia de que la institución actuó a tiempo.</div>`;
}
async function notificarPadre(id,nombre){
  if(!confirm(`¿Enviar mensaje al acudiente de ${nombre} sobre su situación académica?`)) return;
  try{ const r=await post("/academico/notas/notificar_padre",{estudiante_id:id}); toast(r.msg,!r.ok); }
  catch(e){ toast("Error",true); }
}
async function alertarAlumno(id,nombre){
  if(!confirm(`¿Enviar alerta temprana a ${nombre}? Le llegará a su portal y por WhatsApp.`)) return;
  try{ const r=await post("/academico/notas/alertar_alumno",{estudiante_id:id}); toast(r.msg,!r.ok); }
  catch(e){ toast("Error",true); }
}

/* ═══ V4 · HISTORIAL DE ASISTENCIA CON SCORE (punto 5) ═══ */
async function abrirHistorialAsistencia(){
  try{
    const d = await api(`/asistencia/historial_salon?salon_id=${ST.salon_id}&dias=30`);
    window._histAsist = d;
    const EST_ICO={present:"✅",absent:"❌",late:"🕐",excused:"📄","—":"·"};
    const EST_BG={present:"#DCFCE7",absent:"#FEE2E2",late:"#FEF3C7",excused:"#DBEAFE","—":"#F8FAFC"};
    document.getElementById("modal-srd-title").textContent="📋 Historial de asistencia · últimos 30 días";
    document.getElementById("modal-srd-body").innerHTML=`
      <div class="legal-note">Cada fila es un estudiante con su <b>score de faltas y pendientes</b>. Los que más faltan aparecen primero — así sabes a quién hay que buscar hoy.</div>
      <div class="tbl-scroll" style="max-height:420px;overflow:auto"><table>
        <thead><tr>
          <th style="position:sticky;left:0;background:#F8FAFC;z-index:2">Estudiante</th>
          <th style="text-align:center">Score</th>
          <th style="text-align:center">Faltas</th>
          <th style="text-align:center">Pendientes</th>
          ${d.fechas.map(f=>`<th style="text-align:center;font-size:.65rem;white-space:nowrap">${f.slice(5)}</th>`).join("")}
        </tr></thead>
        <tbody>${d.estudiantes.map(e=>`<tr>
          <td style="position:sticky;left:0;background:#fff;z-index:1">
            <div class="flex-cell"><div class="avatar-sm">${ini(e.nombre)}</div>
            <div><b class="small">${esc(e.nombre)}</b><div class="small muted">${e.pct_asistencia}% asistencia</div></div></div></td>
          <td style="text-align:center">${e.score_riesgo!=null?`<span class="badge ${e.nivel_riesgo==='CRÍTICO'?'b-red':e.nivel_riesgo==='MODERADO'?'b-orange':'b-green'}">${e.score_riesgo}</span>`:"—"}</td>
          <td style="text-align:center"><b style="color:${e.faltas>3?'var(--red)':'var(--ink)'}">${e.faltas}</b>${e.tardanzas?`<div class="small muted">${e.tardanzas} tarde</div>`:""}</td>
          <td style="text-align:center">${(e.pendientes_aula+e.pendientes_obs)?`<span class="badge b-orange">${e.pendientes_aula+e.pendientes_obs}</span><div class="small muted">${e.pendientes_aula} aula · ${e.pendientes_obs} obs</div>`:'<span class="small muted">al día</span>'}</td>
          ${e.historial.map(h=>`<td style="text-align:center;background:${EST_BG[h.estado]||'#F8FAFC'}" title="${h.fecha}: ${h.estado}">${EST_ICO[h.estado]||"·"}</td>`).join("")}
        </tr>`).join("")||'<tr><td colspan="8" class="empty">Sin registros.</td></tr>'}
      </tbody></table></div>
      <div style="margin-top:10px;display:flex;gap:10px;flex-wrap:wrap;font-size:.78rem">
        <span>✅ Presente</span><span>❌ Ausente</span><span>🕐 Tarde</span><span>📄 Excusa</span>
      </div>`;
    abrirModal("modal-srd");
  }catch(e){ toast("Error cargando el historial",true); }
}

/* ═══ V4 · BRANDING POR INSTITUCIÓN (punto 25) ═══ */
function abrirBranding(tenantId){
  const t=(window._tenants||[]).find(x=>x.id===tenantId);
  if(!t){ toast("Tenant no encontrado",true); return; }
  window._brandLogo = t.logo || null;
  document.getElementById("br_tenant").value=tenantId;
  document.getElementById("br_nombre").value=t.nombre||"";
  document.getElementById("br_color").value=t.color||"#0E7C86";
  document.getElementById("br_dominio").value=t.dominio||"";
  pintarPrevLogo();
  abrirModal("modal-brand");
}
function pintarPrevLogo(){
  const el=document.getElementById("br_prev");
  el.innerHTML = window._brandLogo
    ? `<img src="${window._brandLogo}" style="max-width:100%;max-height:100%;object-fit:contain">`
    : '<span class="small muted">sin logo</span>';
}
function logoSel(inp){
  const f=inp.files[0]; if(!f) return;
  if(f.size>800000){ toast("Imagen muy pesada. Usa uua imagen menor a 800 KB.",true); return; }
  const rd=new FileReader();
  rd.onload=()=>{ window._brandLogo=rd.result; pintarPrevLogo(); };
  rd.readAsDataURL(f);
}
function quitarLogoBrand(){ window._brandLogo=null; pintarPrevLogo(); }
async function guardarBranding(){
  const body={ tenant_id:parseInt(document.getElementById("br_tenant").value),
    logo: window._brandLogo, color:document.getElementById("br_color").value,
    nombre:document.getElementById("br_nombre").value,
    dominio:document.getElementById("br_dominio").value };
  try{ const r=await post("/admin/tenants/branding",body);
    if(!r.ok){toast(r.msg,true);return;}
    cerrarModal("modal-brand"); toast(r.msg); VISTAS.tenants();
  }catch(e){ toast("Error",true); }
}

function tnLogoSel(inp){
  const f=inp.files[0]; if(!f) return;
  if(f.size>800000){ toast("Imagen muy pesada (máx 800 KB).",true); return; }
  const rd=new FileReader();
  rd.onload=()=>{ window._tnLogo=rd.result;
    document.getElementById("tn_logo_prev").innerHTML=`<img src="${rd.result}" style="max-width:100%;max-height:100%;object-fit:contain">`; };
  rd.readAsDataURL(f);
}

/* ═══ V4 · CONTRATOS: checklist con anexos, validación jurídica, vencimientos ═══ */

/* Punto 20 y 26: en editar contrato, anexar los PDFs que faltan del expediente */
async function abrirChecklistDocs(contratistaId, contratoNum){
  try{
    const lst = window._contratistas || await api(`/contratos/contratistas`);
    const c = lst.find(x=>x.id===contratistaId);
    if(!c){ toast("Contratista no encontrado",true); return; }
    window._ckDocs = c;
    document.getElementById("modal-srd-title").textContent=`📋 Checklist documental · ${c.nombre}`;
    pintarChecklistDocs(contratoNum);
    abrirModal("modal-srd");
  }catch(e){ toast("Error",true); }
}
function pintarChecklistDocs(contratoNum){
  const c=window._ckDocs;
  const faltan=c.documentos.filter(d=>!d.ok);
  const venc=c.documentos.filter(d=>d.vencido);
  const porv=c.documentos.filter(d=>d.por_vencer);
  document.getElementById("modal-srd-body").innerHTML=`
    ${contratoNum?`<div class="small muted">Expediente exigido para el contrato <b>${esc(contratoNum)}</b></div>`:""}
    <div class="kpis" style="margin:10px 0">
      <div class="kpi ${faltan.length?'red':'green'}"><div class="kpi-ico">${faltan.length?"⛔":"✅"}</div>
        <div class="kpi-val">${c.documentos.length-faltan.length}/${c.documentos.length}</div><div class="kpi-lbl">Documentos válidos</div></div>
      <div class="kpi ${venc.length?'red':''}"><div class="kpi-ico">🗓️</div><div class="kpi-val">${venc.length}</div><div class="kpi-lbl">Vencidos</div></div>
      <div class="kpi ${porv.length?'orange':''}"><div class="kpi-ico">⏳</div><div class="kpi-val">${porv.length}</div><div class="kpi-lbl">Por vencer</div></div>
    </div>
    ${venc.length?`<div class="legal-note" style="background:#FEE2E2;border-color:var(--red)">🚨 <b>No se puede avanzar el contrato:</b> ${venc.map(d=>esc(d.label)).join(", ")} ${venc.length===1?"está vencido":"están vencidos"}. Solicita la renovación.</div>`:""}
    ${c.documentos.map(d=>`
      <div class="check-row" style="align-items:flex-start">
        <div style="flex:1">
          <b class="small">${d.ok?"✅":"⛔"} ${esc(d.label)}</b>
          <div class="small muted">
            ${d.archivo?`📎 ${esc(d.archivo)}`:"sin archivo"}
            ${d.fecha?` · expedido ${esc(d.fecha)}`:""}
            ${d.vigencia_dias?` · vigencia ${d.vigencia_dias} días`:" · sin vencimiento"}
            ${d.vencido?` · <b style="color:var(--red)">VENCIDO hace ${Math.abs(d.dias_restantes)} días</b>`:
              d.por_vencer?` · <b style="color:var(--orange)">vence en ${d.dias_restantes} días</b>`:
              (d.dias_restantes!=null?` · vence en ${d.dias_restantes} días`:"")}
          </div>
        </div>
        <button class="btn btn-xs ${d.ok&&!d.vencido?'':'btn-primary'}" onclick="anexarDocCheck('${d.clave}')">📎 ${d.ok?"Reemplazar":"Anexar"}</button>
        <input type="file" id="ck-file-${d.clave}" style="display:none" onchange="docCheckSel('${d.clave}',this)">
      </div>`).join("")}
    <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">
      <button class="btn btn-sm btn-gold" onclick="portalLink(${c.id})">🔗 Pedir al contratista por su portal</button>
      <button class="btn btn-sm" onclick="recordarDocs(${c.id})">📱 Recordar por WhatsApp</button>
      <button class="btn btn-sm btn-primary" style="margin-left:auto" onclick="guardarChecklist()">💾 Guardar expediente</button>
    </div>`;
}
function anexarDocCheck(clave){ document.getElementById("ck-file-"+clave).click(); }
function docCheckSel(clave, inp){
  const f=inp.files[0]; if(!f) return;
  const d=window._ckDocs.documentos.find(x=>x.clave===clave);
  if(d){ d.ok=true; d.archivo=f.name; d.fecha=hoyISO(); d.vencido=false; d.por_vencer=false;
    d.dias_restantes=d.vigencia_dias||null; }
  pintarChecklistDocs();
  toast(`📎 ${f.name} anexado. Recuerda guardar.`);
}
async function guardarChecklist(){
  const c=window._ckDocs;
  const documentos={};
  c.documentos.forEach(d=>{ documentos[d.clave]={ok:d.ok, archivo:d.archivo, fecha:d.fecha}; });
  try{
    const r=await post("/contratos/contratistas/guardar",{id:c.id, nombre:c.nombre, nit:c.nit,
      tipo:c.tipo, telefono:c.telefono, email:c.email, documentos});
    toast(r.msg,!r.ok);
    if(r.ok){ cerrarModal("modal-srd"); VISTAS.contratos(ST._conTab||"pipeline"); }
  }catch(e){ toast("Error",true); }
}
async function recordarDocs(id){
  try{ const r=await post("/contratos/documentos_alertas/recordar",{contratista_id:id}); toast(r.msg,!r.ok); }
  catch(e){ toast("Error",true); }
}

/* Punto 22: concepto jurídico automático */
async function validarLogicaContrato(id){
  try{
    const c=(window._contratosCache||[]).find(x=>x.id===id);
    const items = (c && c.objeto) ? [{descripcion:c.objeto}] : [];
    const r = await post("/contratos/validar_logica",{contrato_id:id, items});
    if(!r.ok){ toast(r.msg,true); return; }
    document.getElementById("modal-srd-title").textContent="⚖️ Revisión jurídica automática";
    document.getElementById("modal-srd-body").innerHTML=`
      <div class="legal-note" style="background:${r.criticos?'#FEE2E2':r.alertas?'#FEF3C7':'#DCFCE7'};border-color:${r.criticos?'var(--red)':r.alertas?'var(--gold)':'var(--green)'}">
        <b style="font-size:1.05rem">Concepto: ${esc(r.concepto)}</b><br>
        <span class="small">Contrato ${esc(r.contrato)} · ${r.criticos} hallazgo(s) crítico(s), ${r.alertas} observación(es)</span></div>
      ${r.hallazgos.map(h=>`
        <div class="obs-item ${h.tipo==='critico'?'obs-riesgo':h.tipo==='alerta'?'':'obs-compromiso'}" style="border-left:4px solid ${h.tipo==='critico'?'var(--red)':h.tipo==='alerta'?'var(--orange)':'var(--green)'}">
          <b class="small">${h.tipo==='critico'?"🚨 CRÍTICO":h.tipo==='alerta'?"⚠️ Observación":"✅ Correcto"}</b>
          <div class="small">${esc(h.texto)}</div></div>`).join("")}
      <div class="audit-note">🔍 <b>Qué revisa el sistema:</b> que lo que se compra corresponda al objeto contratado (no comprar veneno y anexarle papelería), que el <b>código CIIU</b> del contratista en Cámara de Comercio cubra esa actividad, que los documentos estén <b>vigentes</b> (REDAM y contraloría vencen a los 90 días) y que existan cotizaciones que soporten el precio. Todo queda registrado como evidencia exportable.</div>
      <div style="text-align:right;margin-top:12px">
        <button class="btn" onclick="cerrarModal('modal-srd')">Cerrar</button>
        <button class="btn btn-gold" onclick="window.print()">🖨️ Imprimir concepto</button></div>`;
    abrirModal("modal-srd");
  }catch(e){ toast("Error en la validación",true); }
}

/* Punto 21: tablero de vencimientos */
async function vencimientosView(){
  const d = await api(`/contratos/documentos_alertas`);
  document.getElementById("con-cont").innerHTML = `
    <div class="legal-note">🗓️ Los certificados de <b>Contraloría, Procuraduría, REDAM y Policía</b> tienen vigencia de 90 días; la planilla de seguridad social, 30. El sistema los vigila y avisa <b>antes</b> de que venzan, para que ningún contrato avance con papeles vencidos.</div>
    ${d.map(c=>`
      <div class="card"><div class="card-head"><h3>${esc(c.nombre)}</h3>
        <span class="small muted">NIT ${esc(c.nit||"—")}</span></div>
      <div class="card-body">
        ${c.vencidos.length?`<div style="margin-bottom:8px"><b class="small" style="color:var(--red)">🚨 Vencidos (${c.vencidos.length}):</b>
          ${c.vencidos.map(v=>`<span class="doc-chip no">${esc(v.label)} · ${esc(v.fecha||"")}</span>`).join("")}</div>`:""}
        ${c.por_vencer.length?`<div><b class="small" style="color:var(--orange)">⏳ Por vencer:</b>
          ${c.por_vencer.map(v=>`<span class="doc-chip" style="background:#FEF3C7;color:#92400E">${esc(v.label)} · ${v.dias} días</span>`).join("")}</div>`:""}
        <div style="margin-top:10px;display:flex;gap:7px;flex-wrap:wrap">
          <button class="btn btn-xs btn-primary" onclick="recordarDocs(${c.id})">📱 Pedir renovación</button>
          <button class="btn btn-xs" onclick="abrirChecklistDocs(${c.id})">📋 Ver checklist</button>
          <button class="btn btn-xs btn-gold" onclick="portalLink(${c.id})">🔗 Enviar link</button>
          <button class="btn btn-xs" onclick="vistaPreviaPortal(${c.id})">👁️ Vista previa</button>
        </div>
      </div></div>`).join("")||'<div class="empty">✅ Ningún documento vencido ni por vencer.</div>'}`;
}

/* Punto 16/18: análisis de precio antes de crear el contrato */
async function analizarPrecioContrato(){
  const valor=parseFloat(document.getElementById("co_valor").value)||0;
  const tipo=document.getElementById("co_tipo").value;
  const objeto=document.getElementById("co_objeto").value;
  if(!valor){ toast("Escribe primero el valor del contrato",true); return; }
  const cant=parseInt(prompt("¿Cuántas unidades / raciones / meses cubre este valor?","1"))||1;
  try{
    const r=await post("/contratos/analisis_precio",{institucion_id:ST.institucion_id,
      tipo_contrato:tipo, valor, cantidad:cant, objeto});
    const cont=document.getElementById("co_analisis");
    cont.innerHTML=`
      <div class="legal-note" style="background:${r.nivel==='critico'?'#FEE2E2':r.nivel==='alerta'?'#FEF3C7':'#DCFCE7'};border-color:${r.nivel==='critico'?'var(--red)':r.nivel==='alerta'?'var(--gold)':'var(--green)'}">
        <b>${r.nivel==='critico'?"🚨 RIESGO LEGAL":r.nivel==='alerta'?"⚠️ Revisar":"✅ Precio defendible"}</b>
        <div class="small">Unitario: ${money(r.unitario)} · Referencia máxima: ${money(r.referencia)} · ${r.valor_smmlv} SMMLV de ${r.tope_smmlv} permitidos</div>
        ${r.hallazgos.map(h=>`<div class="small" style="margin-top:5px">• ${esc(h.texto)}</div>`).join("")}
        <div class="small" style="margin-top:6px"><b>Recomendación:</b> ${esc(r.recomendacion)}</div>
      </div>`;
  }catch(e){ toast("Error en el análisis",true); }
}

/* Punto 23: recordar firmas por WhatsApp */
async function recordarFirmas(id){
  try{ const r=await post("/contratos/firmas/recordar",{id}); toast(r.msg,!r.ok); }
  catch(e){ toast("Error",true); }
}

/* Punto 19: bandeja de propuestas recibidas por el portal */
async function propuestasView(){
  const d = await api(`/contratos/propuestas`);
  document.getElementById("con-cont").innerHTML = `
    <div class="legal-note">📨 Aquí llegan las propuestas que los <b>contratistas suben por su propio portal</b>, sin que nadie de la institución tenga que digitarlas. Cada una con sus archivos adjuntos.</div>
    ${d.map(p=>`
      <div class="card"><div class="card-head">
        <h3>${esc(p.contratista)}</h3><span class="badge b-blue">${esc(p.estado||"recibida")}</span></div>
      <div class="card-body">
        <div style="display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap">
          <div><b style="font-size:1.05rem">${money(p.valor)}</b>
            <div class="small muted">NIT ${esc(p.nit||"—")} · recibida ${esc(p.fecha||"")}</div></div>
        </div>
        <p class="small" style="margin:8px 0">${esc(p.descripcion||"")}</p>
        <div>${(p.archivos||[]).map(a=>`<span class="mat-chip">📎 ${esc(a)}</span>`).join("")||'<span class="small muted">Sin archivos.</span>'}</div>
        <div style="margin-top:10px"><button class="btn btn-xs" onclick="abrirChecklistDocs(${p.contratista_id})">📋 Ver expediente</button></div>
      </div></div>`).join("")||'<div class="empty">Aún no se han recibido propuestas por el portal.</div>'}`;
}

/* ═══════════════════════════════════════════════════════════════════
   V5 · CURSOS: catálogo + visor paso a paso (estilo plataforma)
   ═══════════════════════════════════════════════════════════════════ */

VISTAS.alcurso = async function(){
  loading();
  try{
    const cursos = await api(`/cursos/?estudiante_id=${ST.estudiante_id}`);
    const prog = await api(`/cursos/mi_progreso?estudiante_id=${ST.estudiante_id}`);
    main(head("Mis cursos","Aprende a tu ritmo: cada curso avanza tema por tema y te va desbloqueando el siguiente")+`
      <div class="kpis">
        <div class="kpi teal"><div class="kpi-ico">📚</div><div class="kpi-val">${prog.completados}/${prog.total_temas}</div><div class="kpi-lbl">Temas completados</div></div>
        <div class="kpi green"><div class="kpi-ico">⏱️</div><div class="kpi-val">${Math.round(prog.minutos_estudiados/60*10)/10}h</div><div class="kpi-lbl">Tiempo estudiado</div></div>
        <div class="kpi"><div class="kpi-ico">🎯</div><div class="kpi-val">${prog.promedio_quiz!=null?prog.promedio_quiz+"%":"—"}</div><div class="kpi-lbl">Promedio en quices</div></div>
        <div class="kpi gold"><div class="kpi-ico">🎓</div><div class="kpi-val">${prog.certificados}</div><div class="kpi-lbl">Cursos terminados</div></div>
      </div>
      <div class="grid-cards">
        ${cursos.map(c=>`
          <div class="curso-card" onclick="abrirCurso(${c.id})">
            <div class="curso-top" style="background:linear-gradient(135deg,${c.color},${c.color}CC)">
              ${c.icono}
              <span class="pill">${c.terminado?"🎓 Terminado":c.pct>0?c.pct+"% avanzado":"Nuevo"}</span>
            </div>
            <div class="curso-body">
              <h4>${esc(c.titulo)}</h4>
              <div class="small muted" style="min-height:52px">${esc((c.descripcion||"").slice(0,120))}…</div>
              <div class="small muted" style="margin:8px 0 6px">📦 ${c.n_modulos} módulos · 📖 ${c.n_temas} temas · ⏱️ ${c.duracion_texto||Math.round(c.minutos/60)+"h"}</div>
              <div class="curso-prog-bar" style="background:#E2E8F0"><i style="width:${c.pct}%"></i></div>
              <div style="margin-top:10px">
                <button class="btn btn-sm btn-primary" style="width:100%">
                  ${c.terminado?"🔁 Repasar el curso":c.pct>0?"▶️ Continuar: "+esc((c.siguiente&&c.siguiente.titulo||"").slice(0,28)):"🚀 Empezar curso"}</button>
              </div>
            </div>
          </div>`).join("")}
      </div>
      <div class="legal-note">📚 Estos cursos vienen instalados para todos los estudiantes. Avanzas tema por tema: lees, practicas y presentas el quiz. Con <b>60% o más</b> se desbloquea el siguiente tema. Al terminar todo, recibes tu certificado.</div>`);
  }catch(e){ main(`<div class="empty">Error cargando los cursos</div>`); }
};

async function abrirCurso(cursoId, temaId){
  loading();
  try{
    const d = await api(`/cursos/detalle?curso_id=${cursoId}&estudiante_id=${ST.estudiante_id}`);
    if(!d.ok){ toast("Curso no encontrado",true); return; }
    window._curso = d;
    const tid = temaId || d.tema_actual || (d.modulos[0] && d.modulos[0].temas[0] && d.modulos[0].temas[0].id);
    main(`
      <div style="display:flex;gap:10px;align-items:center;margin-bottom:14px;flex-wrap:wrap">
        <button class="btn btn-sm" onclick="VISTAS.alcurso()">← Mis cursos</button>
        <h2 style="margin:0;font-size:1.2rem">${d.icono} ${esc(d.titulo)}</h2>
        <span class="badge b-teal" style="margin-left:auto">${d.completados}/${d.n_temas} temas · ${d.pct}%</span>
      </div>
      ${d.terminado?`<div class="cert-box">
        <div style="font-size:2.4rem">🎓</div>
        <h3 style="margin:6px 0">¡Terminaste «${esc(d.titulo)}»!</h3>
        <div class="small" style="opacity:.95">Completaste los ${d.n_temas} temas. Tu certificado está disponible.</div>
        <button class="btn" style="margin-top:12px;background:#fff;color:#B45309" onclick="window.open(API+'/contratos/certificado?estudiante_id='+ST.estudiante_id+'&curso_id=${d.id}')">📜 Ver mi certificado</button>
      </div>`:""}
      <div class="curso-layout">
        <div class="curso-side" id="curso-side"></div>
        <div class="curso-main" id="curso-main"></div>
      </div>`);
    pintarTemarioLateral(tid);
    if(tid) await abrirTema(tid);
  }catch(e){ main(`<div class="empty">Error</div>`); }
}

function pintarTemarioLateral(activoId){
  const d = window._curso;
  document.getElementById("curso-side").innerHTML = `
    <div class="curso-side-head">
      <h4>${d.icono} ${esc(d.titulo)}</h4>
      <div class="curso-prog-bar"><i style="width:${d.pct}%"></i></div>
      <div style="font-size:.73rem;color:#94A3B8;margin-top:6px">${d.completados} de ${d.n_temas} temas · ${d.pct}%</div>
    </div>
    ${d.modulos.map(m=>`
      <div class="mod-head"><span>${m.icono||"📘"} ${esc(m.titulo)}</span><span>${m.completados}/${m.n_temas}</span></div>
      ${m.temas.map(t=>`
        <div class="tema-li ${t.id===activoId?'activo':''} ${t.completado?'hecho':''} ${t.bloqueado?'bloq':''}"
             onclick="${t.bloqueado?`toast('🔒 Completa primero el tema anterior para desbloquear este.',true)`:`abrirTema(${t.id})`}">
          <span class="ic">${t.completado?"✅":t.bloqueado?"🔒":t.id===activoId?"▶️":"○"}</span>
          <span class="tit">${esc(t.titulo)}
            ${t.tipo_practica&&t.tipo_practica!=="none"?'<div style="font-size:.68rem;color:#38BDF8">🛠️ con práctica</div>':""}
            ${t.quiz_puntaje!=null?`<div style="font-size:.68rem;color:#4ADE80">quiz ${t.quiz_puntaje}%</div>`:""}</span>
          <span class="dur">${t.duracion_min}m</span>
        </div>`).join("")}`).join("")}`;
}

async function abrirTema(temaId){
  const cont=document.getElementById("curso-main");
  if(cont) cont.innerHTML='<div class="empty">Cargando tema…</div>';
  try{
    const t = await api(`/cursos/tema?tema_id=${temaId}&estudiante_id=${ST.estudiante_id}`);
    if(!t.ok){ toast("Tema no encontrado",true); return; }
    window._tema = t;
    window._quizResp = {};
    window._prac = t.practica_data || null;
    window._temaInicio = Date.now();
    pintarTema();
    pintarTemarioLateral(temaId);
  }catch(e){ toast("Error",true); }
}

function pintarTema(){
  const t = window._tema;
  document.getElementById("curso-main").innerHTML = `
    <div class="small muted">${t.modulo?esc(t.modulo.icono+" "+t.modulo.titulo):""} · Tema ${t.posicion} de ${t.total}</div>
    <h2>${esc(t.titulo)}</h2>
    <div class="tema-meta">
      <span>⏱️ ${t.duracion_min} min de lectura</span>
      ${t.quiz.length?`<span>📝 ${t.quiz.length} pregunta${t.quiz.length>1?"s":""}</span>`:""}
      ${t.tipo_practica&&t.tipo_practica!=="none"?'<span>🛠️ Práctica interactiva</span>':""}
      ${t.completado?'<span class="badge b-green">✅ Completado</span>':""}
    </div>
    ${t.resumen?`<div class="bloque"><p style="font-size:1.02rem;color:var(--muted)">${esc(t.resumen)}</p></div>`:""}
    ${t.contenido.map(b=>bloqueHTML(b)).join("")}
    ${t.tipo_practica&&t.tipo_practica!=="none"?`<div id="prac-cont">${pintarPractica(t.tipo_practica)}</div>`:""}
    ${t.quiz.length?`<div class="quiz-box" id="quiz-box">
      <b style="font-size:1rem">📝 Comprueba lo que aprendiste</b>
      <div class="small muted" style="margin-bottom:12px">Necesitas ${t.nota_minima}% para desbloquear el siguiente tema. Puedes intentarlo las veces que quieras.</div>
      ${t.quiz.map((q,i)=>`
        <div style="margin-bottom:16px" id="q-${i}">
          <b class="small">${i+1}. ${esc(q.q)}</b>
          ${q.op.map((o,j)=>`<button class="quiz-op" id="q${i}-${j}" onclick="respQuiz(${i},${j})">${esc(o)}</button>`).join("")}
          <div id="exp-${i}"></div>
        </div>`).join("")}
      <div id="quiz-res"></div>
      <button class="btn btn-primary" style="width:100%" onclick="calificarQuiz()">✅ Calificar y continuar</button>
    </div>`:`
      <div style="margin-top:20px"><button class="btn btn-primary btn-lg" onclick="calificarQuiz()">✅ Marcar como completado y seguir</button></div>`}
    <div class="tema-nav">
      ${t.anterior?`<button class="btn" onclick="abrirTema(${t.anterior})">← Tema anterior</button>`:"<span></span>"}
      ${t.siguiente?`<button class="btn" onclick="abrirTema(${t.siguiente})">Siguiente tema →</button>`:`<span class="small muted">Último tema del curso</span>`}
    </div>`;
  document.getElementById("curso-main").scrollTop=0;
}

function bloqueHTML(b){
  const h = b.h?`<h4>${esc(b.h)}</h4>`:"";
  if(b.t==="ejemplo")  return `<div class="bloque bl-ejemplo">${h?`<h4>💡 ${esc(b.h)}</h4>`:""}<p>${esc(b.p||"")}</p></div>`;
  if(b.t==="tip")      return `<div class="bloque bl-tip">${h?`<h4>✅ ${esc(b.h)}</h4>`:""}<p>${esc(b.p||"")}</p></div>`;
  if(b.t==="ojo")      return `<div class="bloque bl-ojo">${h?`<h4>⚠️ ${esc(b.h)}</h4>`:""}<p>${esc(b.p||"")}</p></div>`;
  if(b.t==="formula")  return `<div class="bloque bl-formula">${b.h?`<h4>${esc(b.h)}</h4>`:""}${esc(b.p||"").replace(/\\n/g,"<br>")}</div>`;
  if(b.t==="tabla")    return `<div class="bloque bl-tabla">${h}<table><tbody>${(b.filas||[]).map(f=>`<tr>${f.map(c=>`<td>${esc(c)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
  return `<div class="bloque">${h}<p>${esc(b.p||"")}</p></div>`;
}

function respQuiz(i,j){
  window._quizResp[i]=j;
  const t=window._tema;
  t.quiz[i].op.forEach((_,k)=>{
    const el=document.getElementById(`q${i}-${k}`);
    if(el) el.classList.toggle("sel", k===j);
  });
}

async function calificarQuiz(){
  const t=window._tema;
  let pts=0;
  const total=t.quiz.length;
  if(total){
    if(Object.keys(window._quizResp).length < total){
      toast("Responde todas las preguntas antes de calificar 🙂",true); return;
    }
    t.quiz.forEach((q,i)=>{
      const r=window._quizResp[i];
      if(r===q.correcta) pts++;
      q.op.forEach((_,k)=>{
        const el=document.getElementById(`q${i}-${k}`);
        if(!el) return;
        el.classList.remove("sel");
        if(k===q.correcta) el.classList.add("ok");
        else if(k===r) el.classList.add("mal");
      });
      const exp=document.getElementById(`exp-${i}`);
      if(exp && q.explica){
        const bien = r===q.correcta;
        exp.innerHTML=`<div class="small" style="margin-top:6px;padding:8px 12px;border-radius:8px;background:${bien?'#DCFCE7':'#FEF3C7'}">
          ${bien?"✅":"💡"} ${esc(q.explica)}</div>`;
      }
    });
  }
  const pct = total ? Math.round(100*pts/total) : 100;
  const minutos = Math.max(1, Math.round((Date.now()-(window._temaInicio||Date.now()))/60000));
  try{
    const r=await post("/cursos/tema/completar",{tema_id:t.id, estudiante_id:ST.estudiante_id,
      quiz_puntaje: total?pct:null, practica_data: window._prac||null, minutos});
    const res=document.getElementById("quiz-res");
    if(res){
      res.innerHTML=`<div class="legal-note" style="background:${r.aprobado?'#DCFCE7':'#FEF3C7'};border-color:${r.aprobado?'var(--green)':'var(--gold)'}">
        <b>${r.aprobado?"🎉":"💪"} ${total?`${pts} de ${total} correctas (${pct}%)`:"Tema completado"}.</b>
        <div class="small">${esc(r.msg)}</div></div>`;
    }
    toast(r.msg, !r.aprobado);
    if(r.aprobado){
      window._curso = await api(`/cursos/detalle?curso_id=${window._curso.id}&estudiante_id=${ST.estudiante_id}`);
      pintarTemarioLateral(t.id);
      if(r.termino_curso){ setTimeout(()=>abrirCurso(window._curso.id), 1400); }
      else if(r.siguiente){ setTimeout(()=>abrirTema(r.siguiente), 1500); }
    }
  }catch(e){ toast("Error al guardar tu avance",true); }
}

function verCertificado(cursoId){
  const d=window._curso;
  const w=window.open("","_blank");
  if(!w){ toast("Permite las ventanas emergentes para ver el certificado",true); return; }
  w.document.write(`<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><title>Certificado</title>
    <style>body{font-family:Georgia,serif;margin:0;padding:40px;background:#F8FAFC}
    .cert{max-width:780px;margin:0 auto;background:#fff;border:14px solid #0E7C86;padding:52px 44px;text-align:center}
    .cert h1{font-size:2rem;color:#0E7C86;margin:0 0 6px;letter-spacing:.04em}
    .cert .sub{color:#64748B;letter-spacing:.22em;font-size:.8rem;text-transform:uppercase}
    .cert .nom{font-size:1.9rem;margin:28px 0 6px;border-bottom:2px solid #E2E8F0;display:inline-block;padding:0 30px 8px}
    .cert .curso{font-size:1.25rem;color:#0F2138;margin:22px 0 6px;font-weight:bold}
    .firmas{display:flex;justify-content:space-around;margin-top:56px;gap:40px}
    .firmas div{flex:1;border-top:1px solid #94A3B8;padding-top:6px;font-size:.8rem;color:#64748B}
    @media print{body{background:#fff;padding:0}}</style></head>
    <body onload="setTimeout(()=>window.print(),500)"><div class="cert">
    <div class="sub">Constancia de formación</div>
    <h1>CERTIFICADO</h1>
    <div class="sub">Se certifica que</div>
    <div class="nom">${esc(ST.perfil.nombre||"Estudiante")}</div>
    <div style="color:#64748B;margin-top:14px">completó satisfactoriamente el curso</div>
    <div class="curso">${esc(d.titulo)}</div>
    <div style="color:#64748B;font-size:.9rem">${d.n_temas} temas · ${esc(d.duracion_texto||"")}</div>
    <div class="firmas"><div>Rectoría</div><div>Coordinación académica</div></div>
    <div style="margin-top:26px;font-size:.7rem;color:#94A3B8">Documento de demostración con datos simulados</div>
    </div></body></html>`);
  w.document.close();
}

/* Práctica de flujo de caja y nómina (nuevas del curso ampliado) */
function practicaFlujo(){
  const p=window._prac||{}; window._prac=p;
  return `<div class="prac-box">
    <b>🛠️ Práctica: ¿te alcanza la caja este mes?</b>
    <div class="small muted" style="margin-bottom:10px">Simula tus entradas y salidas reales de dinero.</div>
    <div class="frow-3">
      <div><label class="small">Cobros de contado</label><input id="fl_contado" type="number" value="${p.contado||0}" oninput="calcFlujo()"></div>
      <div><label class="small">Cobros de créditos anteriores</label><input id="fl_cxc" type="number" value="${p.cxc||0}" oninput="calcFlujo()"></div>
      <div><label class="small">Pagos del mes</label><input id="fl_pagos" type="number" value="${p.pagos||0}" oninput="calcFlujo()"></div>
    </div>
    <div class="frow"><label class="small">Ventas a crédito (entran después, NO este mes)</label><input id="fl_credito" type="number" value="${p.credito||0}" oninput="calcFlujo()"></div>
    <div id="fl_res"></div></div>`;
}
function calcFlujo(){
  const c=+document.getElementById("fl_contado").value||0;
  const x=+document.getElementById("fl_cxc").value||0;
  const pg=+document.getElementById("fl_pagos").value||0;
  const cr=+document.getElementById("fl_credito").value||0;
  const flujo=c+x-pg;
  window._prac={contado:c,cxc:x,pagos:pg,credito:cr,flujo};
  document.getElementById("fl_res").innerHTML=`
    <div class="legal-note" style="background:${flujo>=0?'#DCFCE7':'#FEE2E2'};border-color:${flujo>=0?'var(--green)':'var(--red)'}">
      Entradas reales: ${money(c+x)} − Salidas: ${money(pg)} = <b style="font-size:1.05rem">${money(flujo)}</b><br>
      <b>${flujo>=0?"✅ Te alcanza para cubrir el mes.":"🚨 ¡Te falta plata! Necesitas "+money(Math.abs(flujo))+" más."}</b>
      ${cr>0?`<div class="small" style="margin-top:5px">📌 Ojo: los ${money(cr)} de ventas a crédito NO entraron este mes. En tu estado de resultados aparecen como ingreso, pero en tu bolsillo todavía no están.</div>`:""}
    </div>`;
}
function practicaNomina(){
  const p=window._prac||{}; window._prac=p;
  return `<div class="prac-box">
    <b>🛠️ Práctica: ¿cuánto cuesta realmente un empleado?</b>
    <div class="small muted" style="margin-bottom:10px">Escribe el salario acordado y mira el costo real con prestaciones.</div>
    <div class="frow"><label class="small">Salario mensual acordado</label><input id="nm_sal" type="number" value="${p.salario||1300000}" oninput="calcNomina()"></div>
    <div id="nm_res"></div></div>`;
}
function calcNomina(){
  const s=+document.getElementById("nm_sal").value||0;
  const ces=s*0.0833, int=ces*0.12, pri=s*0.0833, vac=s*0.0417;
  const sal=s*0.085, pen=s*0.12, arl=s*0.00522, caja=s*0.04;
  const carga=ces+int+pri+vac+sal+pen+arl+caja;
  const total=s+carga;
  window._prac={salario:s,carga:Math.round(carga),total:Math.round(total)};
  document.getElementById("nm_res").innerHTML=`
    <div class="bl-tabla" style="margin-top:10px"><table><tbody>
      <tr><td>Salario</td><td style="text-align:right">${money(s)}</td></tr>
      <tr><td>Cesantías (8.33%)</td><td style="text-align:right">${money(ces)}</td></tr>
      <tr><td>Intereses cesantías</td><td style="text-align:right">${money(int)}</td></tr>
      <tr><td>Prima (8.33%)</td><td style="text-align:right">${money(pri)}</td></tr>
      <tr><td>Vacaciones (4.17%)</td><td style="text-align:right">${money(vac)}</td></tr>
      <tr><td>Salud empleador (8.5%)</td><td style="text-align:right">${money(sal)}</td></tr>
      <tr><td>Pensión empleador (12%)</td><td style="text-align:right">${money(pen)}</td></tr>
      <tr><td>ARL + Caja (4.5%)</td><td style="text-align:right">${money(arl+caja)}</td></tr>
    </tbody></table></div>
    <div class="legal-note" style="background:#FEF3C7;border-color:var(--gold);margin-top:8px">
      <b style="font-size:1.05rem">Costo real: ${money(total)} al mes</b><br>
      <span class="small">Son ${money(carga)} más que el salario (${Math.round(carga/s*100)}% adicional). Si cotizas un trabajo contando solo el salario, pierdes plata en cada contrato.</span></div>`;
}

/* ═══════════════════════════════════════════════════════════════════
   V5 · GESTIÓN DE USUARIOS (registro, roles, permisos, auditoría)
   ═══════════════════════════════════════════════════════════════════ */

let USR_FILTRO = {estado:"", rol:"", q:""};

VISTAS.usuarios = async function(tab){
  loading();
  try{
    const t = tab||"todos";
    ST._usrTab = t;
    const [cat, d] = await Promise.all([
      api(`/usuarios/roles`),
      api(`/usuarios/?institucion_id=${ST.institucion_id}${USR_FILTRO.estado?"&estado="+USR_FILTRO.estado:""}${USR_FILTRO.rol?"&rol="+USR_FILTRO.rol:""}${USR_FILTRO.q?"&q="+encodeURIComponent(USR_FILTRO.q):""}`),
    ]);
    window._rolesCat = cat;
    window._usuarios = d.usuarios;
    const r = d.resumen;
    main(head("Control de usuarios","Todas las cuentas de tu institución: quién entra, con qué rol y qué permisos tiene",
      `<button class="btn btn-primary" onclick="editarUsuario(0)">➕ Crear usuario</button>`)+`
      <div class="kpis">
        <div class="kpi green"><div class="kpi-ico">✅</div><div class="kpi-val">${r.activos}</div><div class="kpi-lbl">Cuentas activas</div></div>
        <div class="kpi ${r.pendientes?'orange':''}"><div class="kpi-ico">⏳</div><div class="kpi-val">${r.pendientes}</div><div class="kpi-lbl">Esperando aprobación</div></div>
        <div class="kpi ${r.suspendidos?'red':''}"><div class="kpi-ico">⏸️</div><div class="kpi-val">${r.suspendidos}</div><div class="kpi-lbl">Suspendidas</div></div>
        <div class="kpi"><div class="kpi-ico">💤</div><div class="kpi-val">${r.inactivos_30d}</div><div class="kpi-lbl">Sin entrar en 30 días</div></div>
      </div>
      <div class="subtabs">
        ${[["todos","👥 Todos los usuarios"],["pendientes",`⏳ Por aprobar${r.pendientes?" ("+r.pendientes+")":""}`],["roles","🔐 Roles y permisos"],["auditoria","📜 Auditoría de accesos"],["seguridad","🛡️ Seguridad"]].map(([k,l])=>
          `<button class="subtab ${t===k?'active':''}" onclick="VISTAS.usuarios('${k}')">${l}</button>`).join("")}</div>
      <div id="usr-cont"><div class="empty">Cargando…</div></div>`);
    if(t==="todos") usrLista(d);
    if(t==="pendientes") usrPendientes(d);
    if(t==="roles") usrRoles(cat, r);
    if(t==="auditoria") usrAuditoria();
    if(t==="seguridad") usrSeguridad();
  }catch(e){ main(`<div class="empty">Error cargando usuarios</div>`); }
};

function usrLista(d){
  const cat=window._rolesCat;
  document.getElementById("usr-cont").innerHTML = `
    <div class="card"><div class="card-body" style="display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end">
      <div style="flex:1;min-width:180px"><label class="small">Buscar</label>
        <input id="usr_q" value="${esc(USR_FILTRO.q)}" placeholder="Nombre, usuario o correo…" onkeyup="if(event.key==='Enter')aplicarFiltroUsr()"></div>
      <div><label class="small">Estado</label><select id="usr_estado" onchange="aplicarFiltroUsr()">
        <option value="">Todos</option>
        ${Object.entries(cat.estados).map(([k,v])=>`<option value="${k}" ${USR_FILTRO.estado===k?"selected":""}>${v}</option>`).join("")}
      </select></div>
      <div><label class="small">Rol</label><select id="usr_rol" onchange="aplicarFiltroUsr()">
        <option value="">Todos</option>
        ${cat.roles.map(x=>`<option value="${x.id}" ${USR_FILTRO.rol===x.id?"selected":""}>${x.icono} ${esc(x.label)}</option>`).join("")}
      </select></div>
      <button class="btn btn-sm" onclick="aplicarFiltroUsr()">🔎 Filtrar</button>
      <button class="btn btn-sm" onclick="USR_FILTRO={estado:'',rol:'',q:''};VISTAS.usuarios('todos')">Limpiar</button>
    </div></div>
    <div class="card"><div class="card-head"><h3>${d.usuarios.length} usuario(s)</h3>
      <span class="small muted">ordenados por estado</span></div>
    <div style="max-height:520px;overflow-y:auto">
      ${d.usuarios.map(u=>`
        <div class="usr-row">
          ${u.foto?`<img class="avatar-foto" src="${u.foto}">`:`<div class="avatar-sm">${ini(u.nombre)}</div>`}
          <div style="flex:1;min-width:170px">
            <b>${esc(u.nombre)}</b> <span class="usr-chip st-${u.estado}">${esc(u.estado_label)}</span>
            <div class="small muted">${u.rol_icono} ${esc(u.rol_label)} · @${esc(u.usuario)}${u.sede?" · "+esc(u.sede):""}</div>
            <div class="small muted">${u.email?esc(u.email)+" · ":""}${u.nunca_entro?'<span style="color:var(--orange)">nunca ha entrado</span>':u.dias_sin_entrar===0?"entró hoy":"hace "+u.dias_sin_entrar+" días"} · ${u.n_accesos} accesos</div>
            ${u.permisos_extra.length?`<div class="small" style="color:var(--teal)">🔐 ${u.permisos_extra.length} permiso(s) adicional(es)</div>`:""}
          </div>
          <div style="display:flex;gap:5px;flex-wrap:wrap">
            <button class="btn btn-xs" onclick="editarUsuario(${u.id})" title="Editar">✎</button>
            <button class="btn btn-xs" onclick="abrirPermisos(${u.id})" title="Permisos">🔐</button>
            ${u.personal_id?`<button class="btn btn-xs" onclick="verHV(${u.personal_id})" title="Hoja de vida">📄</button>`:""}
            <button class="btn btn-xs ${u.estado==='suspendido'?'btn-green':''}" onclick="suspenderUsuario(${u.id},'${esc(u.nombre)}',${u.estado==='suspendido'})">${u.estado==='suspendido'?"▶️":"⏸️"}</button>
            <button class="btn btn-xs btn-danger" onclick="eliminarUsuario(${u.id},'${esc(u.nombre)}')">🗑</button>
          </div>
        </div>`).join("")||'<div class="empty">Sin usuarios con estos filtros.</div>'}
    </div></div>`;
}
function aplicarFiltroUsr(){
  USR_FILTRO={q:document.getElementById("usr_q").value.trim(),
    estado:document.getElementById("usr_estado").value,
    rol:document.getElementById("usr_rol").value};
  VISTAS.usuarios("todos");
}

function usrPendientes(d){
  const pend=d.usuarios.filter(u=>u.estado==="pendiente");
  document.getElementById("usr-cont").innerHTML = `
    <div class="legal-note">🔐 Nadie entra al sistema sin tu aprobación. Cuando alguien se registra desde el portal, aparece aquí para que revises quién es antes de darle acceso.</div>
    ${pend.map(u=>`
      <div class="card"><div class="card-body">
        <div style="display:flex;gap:14px;align-items:center;flex-wrap:wrap">
          ${u.foto?`<img class="avatar-foto lg" src="${u.foto}">`:`<div class="avatar-sm" style="width:52px;height:52px">${ini(u.nombre)}</div>`}
          <div style="flex:1;min-width:210px">
            <b style="font-size:1.05rem">${esc(u.nombre)}</b>
            <div class="small muted">Solicita entrar como <b>${u.rol_icono} ${esc(u.rol_label)}</b> · @${esc(u.usuario)}</div>
            <div class="small muted">${u.email?"✉️ "+esc(u.email):""} ${u.telefono?" · 📱 "+esc(u.telefono):""} ${u.documento?" · CC "+esc(u.documento):""}</div>
            <div class="small muted">Se registró el ${esc(u.fecha_registro||"")}</div>
            ${u.nota_admin?`<div class="small" style="margin-top:5px;padding:7px 10px;background:#F8FAFC;border-radius:7px">📝 ${esc(u.nota_admin)}</div>`:""}
          </div>
          <div style="display:flex;gap:6px;flex-wrap:wrap">
            <button class="btn btn-sm btn-green" onclick="aprobarUsuario(${u.id})">✅ Aprobar</button>
            <button class="btn btn-sm btn-danger" onclick="rechazarUsuario(${u.id},'${esc(u.nombre)}')">✕ Rechazar</button>
            <button class="btn btn-sm" onclick="editarUsuario(${u.id})">✎ Revisar datos</button>
          </div>
        </div>
      </div></div>`).join("")||'<div class="empty">🎉 No hay registros pendientes por revisar.</div>'}`;
}

function usrRoles(cat, resumen){
  document.getElementById("usr-cont").innerHTML = `
    <div class="card"><div class="card-head"><h3>👥 Cuántos hay de cada rol</h3></div>
    <div class="card-body"><div style="display:flex;gap:8px;flex-wrap:wrap">
      ${resumen.por_rol.map(x=>`<span class="badge b-teal" style="font-size:.85rem;padding:6px 12px">${x.icono} ${esc(x.label)}: <b>${x.n}</b></span>`).join("")}
    </div></div></div>
    <div class="card"><div class="card-head"><h3>🔐 Qué puede hacer cada rol</h3>
      <span class="small muted">capacidades base del sistema</span></div>
    <div class="tbl-scroll"><table>
      <thead><tr><th>Rol</th><th>Para qué sirve</th><th>Puede</th></tr></thead>
      <tbody>${cat.roles.map(r=>`<tr>
        <td><b>${r.icono} ${esc(r.label)}</b><div class="small muted">nivel ${r.nivel}</div></td>
        <td class="small">${esc(r.desc)}</td>
        <td>${r.caps.map(c=>`<span class="doc-chip ok" style="font-size:.68rem">${esc(c.replace(/_/g," "))}</span>`).join("")}</td>
      </tr>`).join("")}</tbody></table></div></div>
    <div class="legal-note">💡 Además del rol base, puedes dar <b>permisos puntuales</b> a una persona concreta con el botón 🔐 de cada usuario. Así delegas sin cambiarle el cargo: por ejemplo, que la secretaria vea contratos sin volverla contadora.</div>`;
}

async function usrAuditoria(){
  const d = await api(`/usuarios/auditoria?institucion_id=${ST.institucion_id}&dias=60`);
  document.getElementById("usr-cont").innerHTML = `
    <div class="kpis">
      <div class="kpi"><div class="kpi-ico">🔑</div><div class="kpi-val">${d.resumen.logins}</div><div class="kpi-lbl">Ingresos correctos</div></div>
      <div class="kpi ${d.resumen.fallidos?'red':''}"><div class="kpi-ico">🚫</div><div class="kpi-val">${d.resumen.fallidos}</div><div class="kpi-lbl">Intentos fallidos</div></div>
      <div class="kpi purple"><div class="kpi-ico">⚙️</div><div class="kpi-val">${d.resumen.administrativos}</div><div class="kpi-lbl">Cambios administrativos</div></div>
    </div>
    <div class="card"><div class="card-head"><h3>📜 Registro de actividad (últimos ${d.resumen.dias} días)</h3>
      <button class="btn btn-sm" onclick="window.print()">🖨️ Imprimir</button></div>
    <div style="max-height:460px;overflow-y:auto">
      ${d.eventos.map(e=>`
        <div class="log-row ${e.resultado==='fallido'?'fallido':''}">
          <span style="min-width:150px">${esc(e.accion_label)}</span>
          <b style="flex:1;min-width:130px">${esc(e.usuario||"—")}</b>
          <span class="small muted" style="flex:2;min-width:150px">${esc(e.detalle||"")}</span>
          <span class="small muted" style="min-width:105px">${esc(e.ip||"")}</span>
          <span class="small muted" style="min-width:115px">${esc(e.fecha)}</span>
        </div>`).join("")||'<div class="empty">Sin actividad registrada.</div>'}
    </div></div>
    <div class="audit-note">🔍 Cada ingreso, cambio de rol, aprobación y suspensión queda registrado con su IP y su fecha. Esto es lo que permite responder «quién hizo qué y cuándo» ante cualquier revisión.</div>`;
}

function editarUsuario(id){
  const u=(window._usuarios||[]).find(x=>x.id===id);
  const cat=window._rolesCat;
  window._usrFoto = u?u.foto:null;
  document.getElementById("modal-srd-title").textContent = id?"✎ Editar usuario":"➕ Crear usuario";
  document.getElementById("modal-srd-body").innerHTML=`
    <input type="hidden" id="us_id" value="${id||""}">
    <div style="display:flex;gap:16px;align-items:center;margin-bottom:14px;flex-wrap:wrap">
      <div style="position:relative">
        <div id="us_foto_prev" style="width:70px;height:70px;border-radius:50%;background:#F1F5F9;display:flex;align-items:center;justify-content:center;font-size:1.4rem;overflow:hidden;border:2px solid var(--border)">
          ${u&&u.foto?`<img src="${u.foto}" style="width:100%;height:100%;object-fit:cover">`:(u?ini(u.nombre):"👤")}</div>
        <button class="btn btn-xs" style="position:absolute;bottom:-4px;right:-4px" onclick="document.getElementById('us_file').click()">📷</button>
        <input type="file" id="us_file" accept="image/*" style="display:none" onchange="usrFotoSel(this)">
      </div>
      <div class="small muted" style="flex:1;min-width:180px">Sube la foto de la persona. Aparecerá en su perfil, en las listas y en su hoja de vida.</div>
    </div>
    <div class="fsec">👤 Datos de la persona</div>
    <div class="frow"><label>Nombre completo *</label><input id="us_nombre" value="${u?esc(u.nombre):""}"></div>
    <div class="frow-2">
      <div><label>Documento</label><input id="us_doc" value="${u?esc(u.documento||""):""}"></div>
      <div><label>Teléfono</label><input id="us_tel" value="${u?esc(u.telefono||""):""}"></div>
    </div>
    <div class="fsec">🔑 Acceso al sistema</div>
    <div class="frow-2">
      <div><label>Nombre de usuario *</label><input id="us_usuario" value="${u?esc(u.usuario):""}" placeholder="mrojas"></div>
      <div><label>Correo</label><input id="us_email" value="${u?esc(u.email||""):""}"></div>
    </div>
    <div class="frow-2">
      <div><label>Rol *</label><select id="us_rol">
        ${cat.roles.map(r=>`<option value="${r.id}" ${u&&u.rol===r.id?"selected":""}>${r.icono} ${esc(r.label)}</option>`).join("")}
      </select></div>
      <div><label>Estado</label><select id="us_estado">
        ${Object.entries(cat.estados).map(([k,v])=>`<option value="${k}" ${u&&u.estado===k?"selected":""}>${v}</option>`).join("")}
      </select></div>
    </div>
    <div class="frow"><label>Sede</label><select id="us_sede"><option value="">— Sin asignar —</option></select></div>
    <div class="frow"><label>Nota interna (solo la ve rectoría)</label><input id="us_nota" value="${u?esc(u.nota_admin||""):""}"></div>
    ${!id?`<div class="legal-note">Al crear la cuenta también se genera su ficha de personal y su hoja de vida, listas para completar.</div>`:""}
    <div class="modal-foot" style="border:none;padding:14px 0 0">
      <button class="btn" onclick="cerrarModal('modal-srd')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarUsuario()">💾 Guardar</button></div>`;
  cargarSedesSelect("us_sede", u?u.sede_id:null);
  abrirModal("modal-srd");
}
async function cargarSedesSelect(elId, sel){
  try{
    const d=await api(`/sedes/?institucion_id=${ST.institucion_id}`);
    const el=document.getElementById(elId);
    if(!el) return;
    el.innerHTML='<option value="">— Sin asignar —</option>'+
      d.sedes.map(s=>`<option value="${s.id}" ${sel===s.id?"selected":""}>${s.tipo==="principal"?"🏫":"📍"} ${esc(s.nombre)}</option>`).join("");
  }catch(e){}
}
function usrFotoSel(inp){
  const f=inp.files[0]; if(!f) return;
  if(f.size>800000){ toast("Imagen muy pesada (máx 800 KB)",true); return; }
  const rd=new FileReader();
  rd.onload=()=>{ window._usrFoto=rd.result;
    document.getElementById("us_foto_prev").innerHTML=`<img src="${rd.result}" style="width:100%;height:100%;object-fit:cover">`; };
  rd.readAsDataURL(f);
}
async function guardarUsuario(){
  const body={ id:parseInt(document.getElementById("us_id").value)||0,
    institucion_id:ST.institucion_id,
    nombre:document.getElementById("us_nombre").value,
    usuario:document.getElementById("us_usuario").value,
    email:document.getElementById("us_email").value,
    telefono:document.getElementById("us_tel").value,
    documento:document.getElementById("us_doc").value,
    rol:document.getElementById("us_rol").value,
    estado:document.getElementById("us_estado").value,
    sede_id:parseInt(document.getElementById("us_sede").value)||null,
    nota_admin:document.getElementById("us_nota").value,
    foto:window._usrFoto };
  if(!body.nombre.trim()||!body.usuario.trim()){ toast("Nombre y usuario son obligatorios",true); return; }
  try{ const r=await post("/usuarios/guardar",body);
    if(!r.ok){toast(r.msg,true);return;}
    cerrarModal("modal-srd"); toast(r.msg); VISTAS.usuarios(ST._usrTab);
  }catch(e){ toast("Error",true); }
}
async function aprobarUsuario(id){
  try{ const r=await post("/usuarios/aprobar",{id}); toast(r.msg,!r.ok); if(r.ok) VISTAS.usuarios("pendientes"); }
  catch(e){ toast("Error",true); }
}
async function rechazarUsuario(id,nombre){
  const motivo=prompt(`¿Por qué rechazas el registro de ${nombre}? (lo verá en su solicitud)`);
  if(motivo===null) return;
  try{ const r=await post("/usuarios/rechazar",{id,motivo}); toast(r.msg,!r.ok); if(r.ok) VISTAS.usuarios("pendientes"); }
  catch(e){ toast("Error",true); }
}
async function suspenderUsuario(id,nombre,reactivar){
  if(!reactivar){
    const motivo=prompt(`¿Por qué suspendes a ${nombre}?\n\nNo podrá entrar, pero se conservan todos sus datos e historial.`);
    if(motivo===null) return;
    try{ const r=await post("/usuarios/suspender",{id,motivo}); toast(r.msg,!r.ok); if(r.ok) VISTAS.usuarios(ST._usrTab); }
    catch(e){ toast("Error",true); }
  } else {
    if(!confirm(`¿Reactivar la cuenta de ${nombre}?`)) return;
    try{ const r=await post("/usuarios/suspender",{id}); toast(r.msg,!r.ok); if(r.ok) VISTAS.usuarios(ST._usrTab); }
    catch(e){ toast("Error",true); }
  }
}
async function eliminarUsuario(id,nombre){
  const conf=prompt(`⚠️ Vas a ELIMINAR la cuenta de ${nombre}.\n\nSi solo quieres impedirle el acceso, es mejor SUSPENDER (conserva el historial).\n\nSi estás seguro, escribe ELIMINAR:`);
  if(conf===null) return;
  const motivo = conf.trim().toUpperCase()==="ELIMINAR" ? (prompt("Motivo (queda en la auditoría):")||"") : "";
  try{ const r=await post("/usuarios/eliminar",{id,confirmacion:conf,motivo}); toast(r.msg,!r.ok); if(r.ok) VISTAS.usuarios(ST._usrTab); }
  catch(e){ toast("Error",true); }
}
function abrirPermisos(id){
  const u=(window._usuarios||[]).find(x=>x.id===id);
  const cat=window._rolesCat;
  if(!u) return;
  window._permSel = new Set(u.permisos_extra||[]);
  document.getElementById("modal-srd-title").textContent=`🔐 Permisos de ${u.nombre}`;
  document.getElementById("modal-srd-body").innerHTML=`
    <div class="info-grid">
      <div class="info-it"><span class="k">Rol actual</span><b>${u.rol_icono} ${esc(u.rol_label)}</b></div>
      <div class="info-it"><span class="k">Estado</span><b>${esc(u.estado_label)}</b></div>
    </div>
    <div class="fsec">Ya puede hacer esto por su rol</div>
    <div>${u.permisos_base.map(c=>`<span class="doc-chip ok">${esc(c.replace(/_/g," "))}</span>`).join("")||'<span class="small muted">Sin capacidades base.</span>'}</div>
    <div class="fsec">Permisos adicionales que le concedes</div>
    <div class="small muted" style="margin-bottom:6px">Marca lo que quieras delegarle además de su rol. Se aplica al instante en sus paneles.</div>
    <div class="perm-grid" id="perm-grid">
      ${cat.permisos_extra.map(p=>`
        <label class="perm-item ${window._permSel.has(p.clave)?'on':''}" id="pi-${p.clave}">
          <input type="checkbox" ${window._permSel.has(p.clave)?"checked":""} onchange="togglePerm('${p.clave}',this.checked)">
          <span>${esc(p.label)}</span></label>`).join("")}
    </div>
    <div class="fsec">Cambiar el rol</div>
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <select id="perm_rol" style="flex:1;min-width:190px">
        ${cat.roles.map(r=>`<option value="${r.id}" ${u.rol===r.id?"selected":""}>${r.icono} ${esc(r.label)}</option>`).join("")}
      </select>
      <button class="btn btn-sm" onclick="cambiarRolUsuario(${u.id})">🔄 Cambiar rol</button>
    </div>
    <div class="modal-foot" style="border:none;padding:14px 0 0">
      <button class="btn" onclick="cerrarModal('modal-srd')">Cerrar</button>
      <button class="btn btn-primary" onclick="guardarPermisos(${u.id})">💾 Guardar permisos</button></div>`;
  abrirModal("modal-srd");
}
function togglePerm(clave, on){
  if(on) window._permSel.add(clave); else window._permSel.delete(clave);
  const el=document.getElementById("pi-"+clave);
  if(el) el.classList.toggle("on", on);
}
async function guardarPermisos(id){
  try{ const r=await post("/usuarios/permisos",{id,permisos:Array.from(window._permSel)});
    toast(r.msg,!r.ok); if(r.ok){ cerrarModal("modal-srd"); VISTAS.usuarios(ST._usrTab); }
  }catch(e){ toast("Error",true); }
}
async function cambiarRolUsuario(id){
  const rol=document.getElementById("perm_rol").value;
  try{ const r=await post("/usuarios/cambiar_rol",{id,rol});
    toast(r.msg,!r.ok); if(r.ok){ cerrarModal("modal-srd"); VISTAS.usuarios(ST._usrTab); }
  }catch(e){ toast("Error",true); }
}

/* ═══ V5 · SEDES (puntos 9 y 12) ═══ */
VISTAS.sedes = async function(){
  loading();
  try{
    const d = await api(`/sedes/?institucion_id=${ST.institucion_id}`);
    window._sedes = d.sedes;
    const t=d.totales;
    const puede=["rector","coordinador"].includes(ST.perfil.rol);
    main(head("Sedes de la institución","Cada sede con su gente, sus salones y lo que le hace falta — en tiempo real",
      puede?`<button class="btn btn-primary" onclick="editarSede(0)">➕ Agregar sede</button>`:"")+`
      <div class="kpis">
        <div class="kpi"><div class="kpi-ico">🏫</div><div class="kpi-val">${t.n_sedes}</div><div class="kpi-lbl">Sedes</div></div>
        <div class="kpi teal"><div class="kpi-ico">👨‍🎓</div><div class="kpi-val">${t.n_estudiantes}</div><div class="kpi-lbl">Estudiantes</div></div>
        <div class="kpi ${t.sin_internet?'orange':''}"><div class="kpi-ico">📡</div><div class="kpi-val">${t.sin_internet}</div><div class="kpi-lbl">Sedes sin internet</div></div>
        <div class="kpi ${t.criticos?'red':''}"><div class="kpi-ico">🎯</div><div class="kpi-val">${t.criticos}</div><div class="kpi-lbl">Estudiantes críticos</div></div>
      </div>
      <div class="grid-cards">
        ${d.sedes.map(s=>`
          <div class="va-card" style="cursor:pointer" onclick="verSede(${s.id})">
            <div class="va-top">
              <span class="va-tipo">${s.tipo==="principal"?"🏫 Sede principal":"📍 Sede satélite"}</span>
              ${s.distancia_km?`<span class="small muted">${s.distancia_km} km</span>`:""}
            </div>
            <h4>${esc(s.nombre)}</h4>
            <div class="small muted">${esc(s.barrio_vereda||"—")} · ${esc(s.zona)}</div>
            <div style="display:flex;gap:6px;flex-wrap:wrap;margin:9px 0">
              <span class="badge b-teal">👨‍🎓 ${s.n_estudiantes}</span>
              <span class="badge b-blue">👨‍🏫 ${s.n_docentes}</span>
              <span class="badge b-gray">🚪 ${s.n_salones}</span>
              ${s.criticos?`<span class="badge b-red">🎯 ${s.criticos} críticos</span>`:""}
            </div>
            <div style="display:flex;gap:6px;flex-wrap:wrap">
              <span class="doc-chip ${s.tiene_internet?'ok':'no'}">${s.tiene_internet?"✓":"✕"} Internet</span>
              <span class="doc-chip ${s.tiene_pae?'ok':'no'}">${s.tiene_pae?"✓":"✕"} PAE</span>
              ${s.solicitudes_pendientes?`<span class="doc-chip" style="background:#FEF3C7;color:#92400E">📨 ${s.solicitudes_pendientes} pedidos</span>`:""}
            </div>
            ${s.coordinador?`<div class="small muted" style="margin-top:8px">👤 Coordina: ${esc(s.coordinador)}</div>`:""}
          </div>`).join("")}
      </div>
      <div class="legal-note">🏫 Los colegios rurales del Sur de Bolívar funcionan con una sede principal y varias sedes en veredas. Aquí ves el estado real de cada una: quién está, cuántos estudiantes hay, si tiene internet y PAE, y qué le está haciendo falta.</div>`);
  }catch(e){ main(`<div class="empty">Error</div>`); }
};
async function verSede(id){
  try{
    const d = await api(`/sedes/detalle?sede_id=${id}`);
    if(!d.ok){ toast("Sede no encontrada",true); return; }
    const puede=["rector","coordinador"].includes(ST.perfil.rol);
    document.getElementById("modal-srd-title").textContent=(d.tipo==="principal"?"🏫 ":"📍 ")+d.nombre;
    document.getElementById("modal-srd-body").innerHTML=`
      <div class="info-grid">
        <div class="info-it"><span class="k">Ubicación</span><b>${esc(d.barrio_vereda||"—")}</b></div>
        <div class="info-it"><span class="k">Dirección</span><b>${esc(d.direccion||"—")}</b></div>
        <div class="info-it"><span class="k">Teléfono</span><b>${esc(d.telefono||"—")}</b></div>
        <div class="info-it"><span class="k">Distancia</span><b>${d.distancia_km} km</b></div>
        <div class="info-it"><span class="k">Código DANE</span><b>${esc(d.codigo_dane||"—")}</b></div>
        <div class="info-it"><span class="k">Niveles</span><b>${d.niveles.join(", ")||"—"}</b></div>
      </div>
      <div style="display:flex;gap:8px;margin:10px 0">
        <span class="doc-chip ${d.tiene_internet?'ok':'no'}">${d.tiene_internet?"✓":"✕"} Internet</span>
        <span class="doc-chip ${d.tiene_pae?'ok':'no'}">${d.tiene_pae?"✓":"✕"} PAE</span>
      </div>
      ${puede?`<div style="text-align:right;margin-bottom:10px"><button class="btn btn-sm" onclick="cerrarModal('modal-srd');editarSede(${d.id})">✎ Editar sede</button></div>`:""}
      <div class="fsec">🚪 Salones (${d.salones.length})</div>
      <div class="tbl-scroll"><table><thead><tr><th>Salón</th><th>Director</th><th style="text-align:center">Estudiantes</th><th style="text-align:center">Críticos</th></tr></thead>
      <tbody>${d.salones.map(s=>`<tr><td><b>${esc(s.nombre)}</b> <span class="small muted">${esc(s.jornada)}</span></td>
        <td class="small">${esc(s.director)}</td><td style="text-align:center">${s.n_estudiantes}</td>
        <td style="text-align:center">${s.criticos?`<span class="badge b-red">${s.criticos}</span>`:"—"}</td></tr>`).join("")||'<tr><td colspan="4" class="empty">Sin salones</td></tr>'}
      </tbody></table></div>
      <div class="fsec">👥 Personal en esta sede (${d.personal.length})</div>
      ${d.personal.map(p=>`
        <div class="flex-cell" style="padding:8px 0;border-bottom:1px solid #F1F5F9">
          ${avatarCell(p.foto,p.nombre)}
          <div style="flex:1"><b class="small">${esc(p.nombre)}</b>
            <div class="small muted">${esc(p.rol)}${p.area?" · "+esc(p.area):""}${p.profesion?" · "+esc(p.profesion):""}</div>
            <div class="small muted">${p.telefono?"📱 "+esc(p.telefono):""} ${p.email?" · ✉️ "+esc(p.email):""}</div></div>
          <button class="btn btn-xs" onclick="cerrarModal('modal-srd');verHV(${p.id})">📄 Hoja de vida</button>
        </div>`).join("")||'<div class="empty">Sin personal asignado</div>'}`;
    abrirModal("modal-srd");
  }catch(e){ toast("Error",true); }
}
function editarSede(id){
  const s=(window._sedes||[]).find(x=>x.id===id);
  document.getElementById("modal-srd-title").textContent=id?"✎ Editar sede":"➕ Nueva sede";
  document.getElementById("modal-srd-body").innerHTML=`
    <input type="hidden" id="sd_id" value="${id||""}">
    <div class="frow"><label>Nombre de la sede *</label><input id="sd_nombre" value="${s?esc(s.nombre):""}" placeholder="Sede La Esperanza"></div>
    <div class="frow-3">
      <div><label>Tipo</label><select id="sd_tipo"><option value="satelite" ${s&&s.tipo==="satelite"?"selected":""}>📍 Satélite</option><option value="principal" ${s&&s.tipo==="principal"?"selected":""}>🏫 Principal</option></select></div>
      <div><label>Zona</label><select id="sd_zona"><option value="rural" ${s&&s.zona==="rural"?"selected":""}>Rural</option><option value="urbana" ${s&&s.zona==="urbana"?"selected":""}>Urbana</option></select></div>
      <div><label>Distancia (km)</label><input type="number" id="sd_dist" value="${s?s.distancia_km:0}" step="0.1"></div>
    </div>
    <div class="frow-2">
      <div><label>Barrio / vereda</label><input id="sd_vereda" value="${s?esc(s.barrio_vereda||""):""}"></div>
      <div><label>Teléfono</label><input id="sd_tel" value="${s?esc(s.telefono||""):""}"></div>
    </div>
    <div class="frow"><label>Dirección</label><input id="sd_dir" value="${s?esc(s.direccion||""):""}"></div>
    <div class="frow-2">
      <div><label>Código DANE</label><input id="sd_dane" value="${s?esc(s.codigo_dane||""):""}"></div>
      <div><label>Niveles que ofrece</label><input id="sd_niveles" value="${s?(s.niveles||[]).join(","):""}" placeholder="Preescolar,Primaria"></div>
    </div>
    <div style="display:flex;gap:16px;margin:10px 0">
      <label class="check-row" style="margin:0"><input type="checkbox" id="sd_internet" ${!s||s.tiene_internet?"checked":""}> 📡 Tiene internet</label>
      <label class="check-row" style="margin:0"><input type="checkbox" id="sd_pae" ${!s||s.tiene_pae?"checked":""}> 🍽️ Tiene PAE</label>
    </div>
    <div class="modal-foot" style="border:none;padding:14px 0 0">
      <button class="btn" onclick="cerrarModal('modal-srd')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarSede()">💾 Guardar sede</button></div>`;
  abrirModal("modal-srd");
}
async function guardarSede(){
  const body={ id:parseInt(document.getElementById("sd_id").value)||0,
    institucion_id:ST.institucion_id, nombre:document.getElementById("sd_nombre").value,
    tipo:document.getElementById("sd_tipo").value, zona:document.getElementById("sd_zona").value,
    distancia_km:parseFloat(document.getElementById("sd_dist").value)||0,
    barrio_vereda:document.getElementById("sd_vereda").value,
    telefono:document.getElementById("sd_tel").value, direccion:document.getElementById("sd_dir").value,
    codigo_dane:document.getElementById("sd_dane").value, niveles:document.getElementById("sd_niveles").value,
    tiene_internet:document.getElementById("sd_internet").checked,
    tiene_pae:document.getElementById("sd_pae").checked };
  if(!body.nombre.trim()){ toast("El nombre es obligatorio",true); return; }
  try{ const r=await post("/sedes/guardar",body);
    if(!r.ok){toast(r.msg,true);return;}
    cerrarModal("modal-srd"); toast(r.msg); VISTAS.sedes();
  }catch(e){ toast("Error",true); }
}

/* ═══ V5 · BUZÓN DE NECESIDADES (punto 10) ═══ */
VISTAS.buzon = async function(t){
  loading();
  try{
    t=t||"pendiente";
    const esDocente = ST.perfil.rol==="docente";
    const d = await api(`/sedes/solicitudes?institucion_id=${ST.institucion_id}${esDocente?"&solicitante_id="+ST.perfil.personal_id:""}`);
    const r=d.resumen;
    const lista = t==="todas" ? d.solicitudes : d.solicitudes.filter(x=>x.estado===t);
    main(head(esDocente?"Mis solicitudes":"Buzón de necesidades",
      esDocente?"Pide lo que necesitas para tu salón: rectoría lo revisa y lo mete al plan de compras"
               :"Lo que los docentes están pidiendo — cada aprobación alimenta el plan de compras del FSE",
      esDocente?`<button class="btn btn-primary" onclick="nuevaSolicitudRecurso()">➕ Pedir algo</button>`:"")+`
      <div class="kpis">
        <div class="kpi ${r.pendientes?'orange':''}"><div class="kpi-ico">📨</div><div class="kpi-val">${r.pendientes}</div><div class="kpi-lbl">Sin responder</div></div>
        <div class="kpi ${r.urgentes?'red':''}"><div class="kpi-ico">🚨</div><div class="kpi-val">${r.urgentes}</div><div class="kpi-lbl">Urgentes</div></div>
        <div class="kpi"><div class="kpi-ico">💰</div><div class="kpi-val sm">${money(r.valor_pendiente)}</div><div class="kpi-lbl">Valor solicitado</div></div>
        <div class="kpi green"><div class="kpi-ico">✅</div><div class="kpi-val">${r.resueltas}</div><div class="kpi-lbl">Resueltas</div></div>
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">
        ${[["pendiente","📨 Pendientes"],["aprobada","✅ Aprobadas"],["en_compra","🛒 En compra"],["resuelta","🎉 Resueltas"],["todas","Todas"]].map(([k,l])=>
          `<button class="chip-filtro ${t===k?'active':''}" onclick="VISTAS.buzon('${k}')">${l}</button>`).join("")}
      </div>
      ${lista.map(s=>`
        <div class="card"><div class="card-body">
          <div style="display:flex;gap:12px;align-items:flex-start;flex-wrap:wrap">
            <div style="flex:1;min-width:220px">
              <b>${esc(s.categoria_label)} · ${esc(s.titulo)}</b>
              ${s.urgencia==="alta"?'<span class="badge b-red">🚨 Urgente</span>':""}
              <div class="small muted" style="margin-top:3px">${esc(s.detalle||"")}</div>
              <div class="small muted" style="margin-top:5px">
                👤 ${esc(s.solicitante)} · 📍 ${esc(s.sede)} · ${esc(s.fecha)}
                ${s.cantidad>1?" · cantidad: "+s.cantidad:""}
                ${s.valor_estimado?" · estimado: "+money(s.valor_estimado):""}</div>
              ${s.respuesta?`<div class="small" style="margin-top:7px;padding:8px 11px;background:#F0FDF4;border-radius:8px">
                💬 <b>${esc(s.resuelto_por||"Rectoría")}:</b> ${esc(s.respuesta)}</div>`:""}
            </div>
            <div style="text-align:right">
              <span class="badge ${s.estado==='resuelta'?'b-green':s.estado==='aprobada'?'b-blue':s.estado==='en_compra'?'b-purple':s.estado==='rechazada'?'b-red':'b-orange'}">${esc(s.estado)}</span>
              ${!esDocente&&s.estado==="pendiente"?`<div style="margin-top:8px;display:flex;gap:5px;flex-wrap:wrap">
                <button class="btn btn-xs btn-green" onclick="resolverRecurso(${s.id},'aprobada')">✅ Aprobar</button>
                <button class="btn btn-xs btn-danger" onclick="resolverRecurso(${s.id},'rechazada')">✕ Rechazar</button>
              </div>`:""}
              ${!esDocente&&s.estado==="aprobada"?`<div style="margin-top:8px"><button class="btn btn-xs" onclick="resolverRecurso(${s.id},'en_compra')">🛒 En compra</button></div>`:""}
              ${!esDocente&&s.estado==="en_compra"?`<div style="margin-top:8px"><button class="btn btn-xs btn-green" onclick="resolverRecurso(${s.id},'resuelta')">🎉 Entregado</button></div>`:""}
            </div>
          </div>
        </div></div>`).join("")||`<div class="empty">${esDocente?"No has hecho solicitudes. Usa ➕ Pedir algo.":"Sin solicitudes en este estado."}</div>`}
      <div class="legal-note">📨 Así rectoría sabe qué falta de verdad en cada sede: no por rumor, sino con el pedido escrito del docente. Al aprobar, la necesidad entra directo al <b>plan de compras del FSE</b> y queda trazable hasta el contrato.</div>`);
  }catch(e){ main(`<div class="empty">Error</div>`); }
};
function nuevaSolicitudRecurso(){
  document.getElementById("modal-srd-title").textContent="📨 Pedir un recurso";
  document.getElementById("modal-srd-body").innerHTML=`
    <div class="legal-note">Cuéntale a rectoría qué necesitas y por qué. Mientras mejor lo expliques, más fácil es que lo aprueben.</div>
    <div class="frow"><label>¿Qué necesitas? *</label><input id="sr_titulo" placeholder="Ej: Marcadores para el tablero"></div>
    <div class="frow-3">
      <div><label>Categoría</label><select id="sr_cat">
        <option value="material">📦 Material didáctico</option><option value="infraestructura">🏗️ Infraestructura</option>
        <option value="tecnologia">💻 Tecnología</option><option value="pae">🍽️ Alimentación</option>
        <option value="personal">👥 Personal</option><option value="otro">📌 Otro</option></select></div>
      <div><label>Cantidad</label><input type="number" id="sr_cant" value="1" min="1"></div>
      <div><label>Urgencia</label><select id="sr_urg"><option value="alta">🚨 Alta</option><option value="media" selected>Media</option><option value="baja">Baja</option></select></div>
    </div>
    <div class="frow"><label>¿Por qué lo necesitas?</label><textarea id="sr_detalle" rows="3" placeholder="Explica cómo afecta a tus estudiantes…"></textarea></div>
    <div class="frow"><label>Valor estimado (si lo sabes)</label><input type="number" id="sr_valor" placeholder="0"></div>
    <div class="modal-foot" style="border:none;padding:14px 0 0">
      <button class="btn" onclick="cerrarModal('modal-srd')">Cancelar</button>
      <button class="btn btn-primary" onclick="enviarSolicitudRecurso()">📨 Enviar solicitud</button></div>`;
  abrirModal("modal-srd");
}
async function enviarSolicitudRecurso(){
  const body={ institucion_id:ST.institucion_id, solicitante_id:ST.perfil.personal_id,
    titulo:document.getElementById("sr_titulo").value, categoria:document.getElementById("sr_cat").value,
    cantidad:parseInt(document.getElementById("sr_cant").value)||1,
    urgencia:document.getElementById("sr_urg").value, detalle:document.getElementById("sr_detalle").value,
    valor_estimado:parseFloat(document.getElementById("sr_valor").value)||0 };
  if(!body.titulo.trim()){ toast("Escribe qué necesitas",true); return; }
  try{ const r=await post("/sedes/solicitudes/crear",body);
    if(!r.ok){toast(r.msg,true);return;}
    cerrarModal("modal-srd"); toast(r.msg); VISTAS.buzon();
  }catch(e){ toast("Error",true); }
}
async function resolverRecurso(id, estado){
  const respuesta=prompt(estado==="rechazada"?"¿Por qué se rechaza? (lo verá el docente)":"Mensaje para el docente (opcional):")||"";
  if(respuesta===null) return;
  const alPlan = ["aprobada","en_compra"].includes(estado) &&
    confirm("¿Agregar esta necesidad al plan de compras del FSE?");
  try{ const r=await post("/sedes/solicitudes/resolver",{id,estado,respuesta,
      resuelto_por:ST.perfil.titulo, agregar_al_plan:alPlan});
    toast(r.msg,!r.ok); if(r.ok) VISTAS.buzon(ST._buzonTab||"pendiente");
  }catch(e){ toast("Error",true); }
}

/* ═══════════════════════════════════════════════════════════════════
   V6 · CLASES COMO CURSOS (puntos 7, 8, 14, 38)
   El alumno ve la clase igual que un curso: temario lateral, tema por
   tema, con su video de YouTube incrustado y su quiz.
   ═══════════════════════════════════════════════════════════════════ */

function videoHTML(youtubeId, url){
  if(youtubeId) return `<div class="video-wrap"><iframe src="https://www.youtube.com/embed/${esc(youtubeId)}" allowfullscreen title="Video de la clase"></iframe></div>`;
  if(url) return `<div class="video-wrap"><div class="video-ph"><div style="font-size:2rem">🎬</div>
    <a href="${esc(url)}" target="_blank" style="color:#38BDF8">Abrir el video en otra pestaña</a></div></div>`;
  return "";
}

/* ── Vista del ALUMNO: una clase completa ── */
async function abrirClaseAlumno(actId, temaId){
  loading();
  try{
    const d = await api(`/clases/clase?actividad_id=${actId}&estudiante_id=${ST.estudiante_id}`);
    if(!d.ok){ toast("No se pudo abrir la clase",true); return; }
    window._claseAl = d;
    const tid = temaId || d.tema_actual;
    main(`
      <div style="display:flex;gap:10px;align-items:center;margin-bottom:14px;flex-wrap:wrap">
        <button class="btn btn-sm" onclick="VISTAS.alclases()">← Mis clases</button>
        <h2 style="margin:0;font-size:1.2rem">${d.portada||"📘"} ${esc(d.titulo)}</h2>
        ${d.n_temas?`<span class="badge b-teal" style="margin-left:auto">${d.completados}/${d.n_temas} temas · ${d.pct}%</span>`:""}
      </div>
      ${d.n_temas ? `<div class="curso-layout">
          <div class="curso-side" id="clase-side"></div>
          <div class="curso-main" id="clase-main"></div>
        </div>`
        : `<div class="card"><div class="card-body">
            ${videoHTML(d.youtube_id,d.video_url)}
            <p style="white-space:pre-line;line-height:1.7">${esc(d.descripcion||"Sin descripción.")}</p>
            <div style="margin-top:10px">${(d.materiales||[]).map(m=>matChipHTML(m)).join("")}</div>
           </div></div>
           ${bloqueEntregaHTML(d)}`}`);
    if(d.n_temas){ pintarTemarioClase(tid); if(tid) await abrirTemaClase(tid); }
  }catch(e){ main(`<div class="empty">Error</div>`); }
}
function matChipHTML(m){
  const ico=MAT_ICO[m.tipo]||(m.tipo&&m.tipo.includes("video")?"🎬":"📎");
  const txt=esc(m.nombre||m.url||"");
  if(m.url) return `<a class="mat-chip" href="${esc(m.url)}" target="_blank">${ico} ${txt}</a>`;
  return `<span class="mat-chip">${ico} ${txt}${m.tamano?` <span style="opacity:.6">${esc(m.tamano)}</span>`:""}</span>`;
}
function pintarTemarioClase(activoId){
  const d=window._claseAl;
  document.getElementById("clase-side").innerHTML=`
    <div class="curso-side-head">
      <h4>${d.portada||"📘"} ${esc(d.titulo)}</h4>
      <div class="curso-prog-bar"><i style="width:${d.pct}%"></i></div>
      <div style="font-size:.73rem;color:#94A3B8;margin-top:6px">${esc(d.materia||"")} · ${d.docente?esc(d.docente):""}</div>
    </div>
    ${d.objetivos&&d.objetivos.length?`<div class="mod-head">🎯 Al terminar sabrás</div>
      <div style="padding:8px 16px;font-size:.78rem;color:#94A3B8;line-height:1.5">
        ${d.objetivos.map(o=>`<div style="margin-bottom:5px">• ${esc(o)}</div>`).join("")}</div>`:""}
    <div class="mod-head"><span>📖 Temas de la clase</span><span>${d.completados}/${d.n_temas}</span></div>
    ${d.temas.map(t=>`
      <div class="tema-li ${t.id===activoId?'activo':''} ${t.completado?'hecho':''}" onclick="abrirTemaClase(${t.id})">
        <span class="ic">${t.completado?"✅":t.id===activoId?"▶️":"○"}</span>
        <span class="tit">${esc(t.titulo)}
          ${t.youtube_id?'<div style="font-size:.68rem;color:#F87171">🎬 con video</div>':""}
          ${t.n_quiz?`<div style="font-size:.68rem;color:#FBBF24">📝 ${t.n_quiz} pregunta(s)</div>`:""}</span>
        <span class="dur">${t.duracion_min}m</span>
      </div>`).join("")}
    ${d.actividades.length?`<div class="mod-head">📝 Para entregar</div>
      ${d.actividades.map(a=>`<div class="tema-li" onclick="alVerActividad(${a.id})">
        <span class="ic">📤</span><span class="tit">${esc(a.titulo)}
        ${a.fecha_limite?`<div style="font-size:.68rem;color:#FBBF24">hasta ${esc(a.fecha_limite)}</div>`:""}</span></div>`).join("")}`:""}`;
}
async function abrirTemaClase(temaId){
  const c=document.getElementById("clase-main");
  if(c) c.innerHTML='<div class="empty">Cargando…</div>';
  try{
    const t=await api(`/clases/tema?tema_id=${temaId}&estudiante_id=${ST.estudiante_id}`);
    if(!t.ok) return;
    window._temaCl=t; window._quizResp={}; window._temaInicio=Date.now();
    document.getElementById("clase-main").innerHTML=`
      <div class="small muted">Tema ${t.posicion} de ${t.total}</div>
      <h2>${esc(t.titulo)}</h2>
      <div class="tema-meta"><span>⏱️ ${t.duracion_min} min</span>
        ${t.quiz.length?`<span>📝 ${t.quiz.length} pregunta(s)</span>`:""}
        ${t.completado?'<span class="badge b-green">✅ Visto</span>':""}</div>
      ${videoHTML(t.youtube_id,t.video_url)}
      ${t.resumen?`<div class="bloque"><p style="font-size:1.02rem;color:var(--muted)">${esc(t.resumen)}</p></div>`:""}
      ${t.contenido.map(b=>bloqueHTML(b)).join("")}
      ${(t.materiales||[]).length?`<div class="bloque"><h4>📎 Material de este tema</h4>
        <div>${t.materiales.map(m=>matChipHTML(m)).join("")}</div></div>`:""}
      ${t.quiz.length?`<div class="quiz-box">
        <b>📝 Comprueba lo que entendiste</b>
        <div class="small muted" style="margin-bottom:10px">Responde para marcar el tema como visto.</div>
        ${t.quiz.map((q,i)=>`<div style="margin-bottom:15px"><b class="small">${i+1}. ${esc(q.q)}</b>
          ${q.op.map((o,j)=>`<button class="quiz-op" id="q${i}-${j}" onclick="respQuiz(${i},${j})">${esc(o)}</button>`).join("")}
          <div id="exp-${i}"></div></div>`).join("")}
        <div id="quiz-res"></div>
        <button class="btn btn-primary" style="width:100%" onclick="completarTemaClase()">✅ Terminé este tema</button>
      </div>`:`<div style="margin-top:18px"><button class="btn btn-primary btn-lg" onclick="completarTemaClase()">✅ Terminé este tema</button></div>`}
      <div class="tema-nav">
        ${t.anterior?`<button class="btn" onclick="abrirTemaClase(${t.anterior})">← Anterior</button>`:"<span></span>"}
        ${t.siguiente?`<button class="btn" onclick="abrirTemaClase(${t.siguiente})">Siguiente →</button>`:
          `<button class="btn btn-primary" onclick="VISTAS.alclases()">🎉 Terminé la clase</button>`}
      </div>`;
    pintarTemarioClase(temaId);
    document.getElementById("clase-main").scrollTop=0;
  }catch(e){ toast("Error",true); }
}
async function completarTemaClase(){
  const t=window._temaCl;
  let pct=null;
  if(t.quiz.length){
    if(Object.keys(window._quizResp).length<t.quiz.length){ toast("Responde todas las preguntas 🙂",true); return; }
    let pts=0;
    t.quiz.forEach((q,i)=>{
      const r=window._quizResp[i];
      if(r===q.correcta) pts++;
      q.op.forEach((_,k)=>{const el=document.getElementById(`q${i}-${k}`); if(!el)return;
        el.classList.remove("sel");
        if(k===q.correcta) el.classList.add("ok"); else if(k===r) el.classList.add("mal");});
      const ex=document.getElementById(`exp-${i}`);
      if(ex&&q.explica) ex.innerHTML=`<div class="small" style="margin-top:6px;padding:8px 12px;border-radius:8px;background:${r===q.correcta?'#DCFCE7':'#FEF3C7'}">${r===q.correcta?"✅":"💡"} ${esc(q.explica)}</div>`;
    });
    pct=Math.round(100*pts/t.quiz.length);
  }
  const min=Math.max(1,Math.round((Date.now()-(window._temaInicio||Date.now()))/60000));
  try{
    const r=await post("/clases/tema/completar",{tema_id:t.id,estudiante_id:ST.estudiante_id,quiz_puntaje:pct,minutos:min});
    toast(r.msg);
    window._claseAl=await api(`/clases/clase?actividad_id=${window._claseAl.id}&estudiante_id=${ST.estudiante_id}`);
    pintarTemarioClase(t.id);
    if(r.siguiente) setTimeout(()=>abrirTemaClase(r.siguiente),1200);
  }catch(e){ toast("Error",true); }
}
function bloqueEntregaHTML(d){
  const en=d.mi_entrega||{};
  const ya=en.estado==="entregado"||en.estado==="revisado";
  return `<div class="card" style="border:2px solid ${ya?'var(--green)':'var(--teal)'}">
    <div class="card-head"><h3>${ya?"✅ Tu entrega":"📤 Entregar"}</h3>
      ${en.nota!=null?`<span class="badge b-green">Nota: ${en.nota}</span>`:""}</div>
    <div class="card-body">
      ${en.retro?`<div class="legal-note">💬 <b>Tu docente:</b> ${esc(en.retro)}</div>`:""}
      <div class="frow"><label>Tu respuesta</label>
        <textarea id="al_resp" rows="5" placeholder="Escribe aquí tu trabajo…">${esc(en.respuesta||"")}</textarea></div>
      <div class="frow"><label>Adjuntar archivo</label>
        <div class="dropzone" onclick="document.getElementById('al_file').click()">${en.archivo?`📎 ${esc(en.archivo)} — cambiar`:"📎 Toca para adjuntar"}</div>
        <input type="file" id="al_file" style="display:none" onchange="window._alArchivo=this.files[0]?this.files[0].name:null;this.previousElementSibling.innerHTML='📎 '+(window._alArchivo||'')"></div>
      <div style="text-align:right"><button class="btn btn-primary" onclick="alEntregar(${d.id})">${ya?"🔄 Actualizar":"📤 Enviar"}</button></div>
    </div></div>`;
}

/* ── Mis clases del alumno: agrupadas por MATERIA (punto 4 anterior) ── */
VISTAS.alclases = async function(materiaSel){
  loading();
  try{
    const cl = await api(`/alumno/clases?estudiante_id=${ST.estudiante_id}`);
    window._alClases = cl;
    const porMat={};
    cl.forEach(c=>{ const m=c.materia||"Sin materia"; (porMat[m]=porMat[m]||[]).push(c); });
    const materias=Object.keys(porMat).sort();
    if(!materiaSel){
      main(head("Mis clases","Tus materias con todo lo que tienes que ver y entregar")+`
        <div class="grid-cards">
          ${materias.map(m=>{
            const arr=porMat[m];
            const pend=arr.filter(c=>c.mi_estado==="sin_entrega"||c.mi_estado==="pendiente").length;
            const col=["#0E7C86","#7C3AED","#0EA5E9","#B45309","#BE185D","#047857"][materias.indexOf(m)%6];
            return `<div class="curso-card" onclick="VISTAS.alclases('${esc(m)}')">
              <div class="curso-top" style="background:linear-gradient(135deg,${col},${col}CC)">
                ${MATERIA_ICO[m]||"📚"}
                <span class="pill">${arr.length} clase${arr.length!=1?"s":""}</span></div>
              <div class="curso-body"><h4>${esc(m)}</h4>
                <div class="small muted">${arr[0].docente?"👨‍🏫 "+esc(arr[0].docente):""}</div>
                <div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap">
                  ${pend?`<span class="badge b-orange">⏳ ${pend} pendiente(s)</span>`:'<span class="badge b-green">✅ Al día</span>'}
                  ${arr.filter(c=>c.mi_nota!=null).length?`<span class="badge b-blue">📗 ${arr.filter(c=>c.mi_nota!=null).length} calificada(s)</span>`:""}
                </div></div></div>`;}).join("")||'<div class="empty">Tu docente aún no ha publicado clases.</div>'}
        </div>`);
      return;
    }
    const arr=porMat[materiaSel]||[];
    main(`<div style="display:flex;gap:10px;align-items:center;margin-bottom:14px;flex-wrap:wrap">
        <button class="btn btn-sm" onclick="VISTAS.alclases()">← Mis materias</button>
        <h2 style="margin:0;font-size:1.25rem">${MATERIA_ICO[materiaSel]||"📚"} ${esc(materiaSel)}</h2>
        <span class="badge b-teal" style="margin-left:auto">${arr.length} clase(s)</span></div>
      <div class="grid-cards">
        ${arr.map(c=>`
          <div class="clase-card" onclick="abrirClaseAlumno(${c.id})">
            <div class="clase-portada" style="background:linear-gradient(135deg,#0E7C86,#0EA5E9)">
              ${TIPO_ICO[c.tipo]||"📘"}
              <span class="est">${c.mi_estado==="revisado"?"✅ Calificado":c.mi_estado==="entregado"?"📤 Entregado":c.fecha_limite?"⏳ Pendiente":"📖 Material"}</span></div>
            <div class="clase-body"><h4>${esc(c.titulo)}</h4>
              <div class="small muted">${esc(c.docente||"")}</div>
              ${c.fecha_limite?`<div class="small" style="color:var(--orange);margin-top:4px">📅 Entrega: ${esc(c.fecha_limite)}</div>`:""}
              ${c.mi_nota!=null?`<div class="small" style="color:var(--green);margin-top:3px"><b>Nota: ${c.mi_nota}</b></div>`:""}
              ${c.n_sub?`<span class="badge b-purple" style="margin-top:5px">🔗 ${c.n_sub} actividad(es)</span>`:""}
            </div></div>`).join("")}
      </div>`);
  }catch(e){ main(`<div class="empty">Error</div>`); }
};
const MATERIA_ICO={"Matemáticas":"➗","Ciencias Naturales":"🔬","Lenguaje":"✍️","Sociales":"🌎",
  "Inglés":"🗣️","Educación Física":"⚽","Artística":"🎨","Ética":"🤝","Religión":"🙏",
  "Tecnología":"💻","Química":"⚗️","Física":"🧲","Filosofía":"💭"};

/* ═══════════════════════════════════════════════════════════════════
   V6 · CONSTRUCTOR DE CLASES (puntos 5, 6, 7, 8)
   Cada material se adjunta según el tipo escogido: si dices PDF, el
   selector solo acepta PDF; si dices video de YouTube, pide el enlace.
   ═══════════════════════════════════════════════════════════════════ */

let CB = null;   // clase en construcción

async function abrirConstructor(id){
  loading();
  try{
    if(!window._tiposMat) window._tiposMat = await api(`/clases/tipos_material`);
    if(id){
      const d = await api(`/clases/clase?actividad_id=${id}`);
      if(!d.ok){ toast("No se pudo abrir",true); return; }
      const temas = [];
      for(const t of d.temas){
        const td = await api(`/clases/tema?tema_id=${t.id}`);
        temas.push({titulo:td.titulo, resumen:td.resumen||"", contenido:td.contenido||[],
          video_url:td.video_url||"", duracion_min:td.duracion_min, materiales:td.materiales||[],
          quiz:td.quiz||[], _abierto:false});
      }
      CB={id:d.id, salon_id:d.salon_id, titulo:d.titulo, tipo:d.tipo, materia:d.materia||"",
        descripcion:d.descripcion||"", periodo_numero:d.periodo||3, corte:d.corte||"",
        fecha_limite:d.fecha_limite||"", duracion_min:d.duracion_min, portada:d.portada||"📘",
        color:d.color, video_url:d.video_url||"", objetivos:d.objetivos||[],
        materiales:d.materiales||[], reglas:d.reglas||"", estado:d.estado, temas, paso:1};
    } else {
      const mis=(window._misSalones||[]);
      CB={id:0, salon_id:(mis[0]?mis[0].id:ST.salon_id), titulo:"", tipo:"clase", materia:"",
        descripcion:"", periodo_numero:3, corte:"", fecha_limite:"", duracion_min:45,
        portada:"📘", color:"#0E7C86", video_url:"", objetivos:[""], materiales:[],
        reglas:"", estado:"publicada", temas:[], paso:1};
    }
    pintarConstructor();
  }catch(e){ toast("Error",true); }
}

function pintarConstructor(){
  const PASOS=["1 · La clase","2 · Temas","3 · Material","4 · Vista previa"];
  main(`
    <div style="display:flex;gap:10px;align-items:center;margin-bottom:14px;flex-wrap:wrap">
      <button class="btn btn-sm" onclick="VISTAS.aula()">← Aula virtual</button>
      <h2 style="margin:0;font-size:1.2rem">${CB.id?"✎ Editar clase":"➕ Crear clase"}</h2>
      <span style="margin-left:auto" class="small muted">${CB.temas.length} tema(s)</span>
    </div>
    <div class="paso-ind">
      ${PASOS.map((p,i)=>`<div class="${CB.paso===i+1?'on':CB.paso>i+1?'done':''}" onclick="CB.paso=${i+1};pintarConstructor()">${p}</div>`).join("")}
    </div>
    <div id="cb-body"></div>`);
  const b=document.getElementById("cb-body");
  if(CB.paso===1) b.innerHTML=cbPaso1();
  if(CB.paso===2){ b.innerHTML=cbPaso2(); }
  if(CB.paso===3) b.innerHTML=cbPaso3();
  if(CB.paso===4) b.innerHTML=cbPaso4();
}

function cbPaso1(){
  const mis=(window._misSalones||[]);
  const EMO=["📘","➗","🔬","✍️","🌎","🗣️","⚽","🎨","💻","⚗️","🧲","📊","🎵","🧪"];
  return `<div class="card"><div class="card-body">
    <div class="fsec">Lo básico</div>
    <div class="frow"><label>Título de la clase *</label>
      <input id="cb_titulo" value="${esc(CB.titulo)}" placeholder="Ej: Fracciones en la vida real" oninput="CB.titulo=this.value"></div>
    <div class="frow-3">
      <div><label>Salón</label><select id="cb_salon" onchange="CB.salon_id=parseInt(this.value)">
        ${mis.map(s=>`<option value="${s.id}" ${CB.salon_id===s.id?"selected":""}>Salón ${esc(s.nombre)}</option>`).join("")}</select></div>
      <div><label>Materia</label><input id="cb_materia" value="${esc(CB.materia)}" placeholder="Matemáticas" oninput="CB.materia=this.value"></div>
      <div><label>Tipo</label><select onchange="CB.tipo=this.value">
        ${[["clase","🧑‍🏫 Clase"],["taller","📝 Taller"],["evaluacion","🧪 Evaluación"],["lectura","📖 Lectura"],["video","🎬 Video"],["recuperacion","♻️ Recuperación"]].map(([v,l])=>`<option value="${v}" ${CB.tipo===v?"selected":""}>${l}</option>`).join("")}
      </select></div>
    </div>
    <div class="frow-3">
      <div><label>Período</label><select onchange="CB.periodo_numero=parseInt(this.value)">
        ${[1,2,3,4].map(p=>`<option value="${p}" ${CB.periodo_numero===p?"selected":""}>Período ${p}</option>`).join("")}</select></div>
      <div><label>Corte</label><input value="${esc(CB.corte)}" placeholder="Corte 1" oninput="CB.corte=this.value"></div>
      <div><label>Duración total (min)</label><input type="number" value="${CB.duracion_min}" oninput="CB.duracion_min=parseInt(this.value)||45"></div>
    </div>
    <div class="frow-2">
      <div><label>Fecha de entrega (si aplica)</label><input type="date" value="${CB.fecha_limite||""}" oninput="CB.fecha_limite=this.value"></div>
      <div><label>Color</label><input type="color" value="${CB.color}" style="height:40px" oninput="CB.color=this.value"></div>
    </div>
    <div class="fsec">Portada</div>
    <div class="small muted" style="margin-bottom:8px">Es lo primero que ve el estudiante. Escoge un ícono:</div>
    <div style="display:flex;gap:6px;flex-wrap:wrap">
      ${EMO.map(e=>`<button class="chip-filtro ${CB.portada===e?'active':''}" style="font-size:1.3rem" onclick="CB.portada='${e}';pintarConstructor()">${e}</button>`).join("")}
    </div>
    <div class="fsec">Video principal (opcional)</div>
    <div class="frow"><label>Enlace de YouTube o Vimeo</label>
      <input id="cb_video" value="${esc(CB.video_url)}" placeholder="https://www.youtube.com/watch?v=..." oninput="CB.video_url=this.value">
      <div class="small muted" style="margin-top:4px">Pega el enlace y el video queda incrustado dentro de la clase — el estudiante lo ve sin salir del sistema.</div></div>
    ${CB.video_url?videoHTML(ytId(CB.video_url),CB.video_url):""}
    <div class="fsec">¿Qué van a aprender?</div>
    <div class="small muted" style="margin-bottom:6px">Escribe los objetivos. Aparecen en el panel lateral del estudiante.</div>
    ${CB.objetivos.map((o,i)=>`<div style="display:flex;gap:6px;margin-bottom:6px">
      <input value="${esc(o)}" placeholder="Objetivo ${i+1}" style="flex:1" oninput="CB.objetivos[${i}]=this.value">
      <button class="btn btn-xs btn-danger" onclick="CB.objetivos.splice(${i},1);pintarConstructor()">✕</button></div>`).join("")}
    <button class="btn btn-sm" onclick="CB.objetivos.push('');pintarConstructor()">➕ Agregar objetivo</button>
    <div class="frow" style="margin-top:14px"><label>Descripción general</label>
      <textarea rows="4" oninput="CB.descripcion=this.value" placeholder="De qué se trata la clase…">${esc(CB.descripcion)}</textarea></div>
    <div style="text-align:right;margin-top:14px"><button class="btn btn-primary" onclick="cbSiguiente()">Siguiente: los temas →</button></div>
  </div></div>`;
}
function ytId(u){ const m=(u||"").match(/(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/)|youtu\.be\/)([A-Za-z0-9_-]{6,})/); return m?m[1]:null; }

function cbPaso2(){
  return `<div class="legal-note">📖 <b>Divide tu clase en temas.</b> Cada tema es un paso que el estudiante recorre: puede tener su propio video, su explicación, su material y su quiz. Así aprenden ordenado, como en un curso.</div>
    ${CB.temas.map((t,i)=>`
      <div class="tema-editor">
        <div class="tema-editor-head" onclick="CB.temas[${i}]._abierto=!CB.temas[${i}]._abierto;pintarConstructor()">
          <span>${t._abierto?"▼":"▶"}</span>
          <b>Tema ${i+1}: ${esc(t.titulo||"(sin título)")}</b>
          <span class="small muted">${t.duracion_min||10}m${t.video_url?" · 🎬":""}${(t.quiz||[]).length?" · 📝"+t.quiz.length:""}${(t.materiales||[]).length?" · 📎"+t.materiales.length:""}</span>
          <button class="btn btn-xs" onclick="event.stopPropagation();cbMoverTema(${i},-1)" ${i===0?"disabled":""}>↑</button>
          <button class="btn btn-xs" onclick="event.stopPropagation();cbMoverTema(${i},1)" ${i===CB.temas.length-1?"disabled":""}>↓</button>
          <button class="btn btn-xs btn-danger" onclick="event.stopPropagation();if(confirm('¿Eliminar este tema?')){CB.temas.splice(${i},1);pintarConstructor()}">🗑</button>
        </div>
        ${t._abierto?`<div class="tema-editor-body">
          <div class="frow-2">
            <div><label>Título del tema *</label><input value="${esc(t.titulo)}" oninput="CB.temas[${i}].titulo=this.value"></div>
            <div><label>Duración (min)</label><input type="number" value="${t.duracion_min||10}" oninput="CB.temas[${i}].duracion_min=parseInt(this.value)||10"></div>
          </div>
          <div class="frow"><label>Resumen corto</label><input value="${esc(t.resumen||"")}" placeholder="En una línea, de qué trata" oninput="CB.temas[${i}].resumen=this.value"></div>
          <div class="frow"><label>🎬 Video de este tema (YouTube)</label>
            <input value="${esc(t.video_url||"")}" placeholder="https://youtu.be/..." oninput="CB.temas[${i}].video_url=this.value"></div>
          <div class="fsec">Contenido</div>
          ${(t.contenido||[]).map((b,j)=>`
            <div style="border:1px solid var(--border);border-radius:9px;padding:10px;margin-bottom:7px">
              <div style="display:flex;gap:6px;margin-bottom:6px">
                <select style="max-width:150px" onchange="CB.temas[${i}].contenido[${j}].t=this.value;pintarConstructor()">
                  ${[["texto","📄 Explicación"],["ejemplo","💡 Ejemplo"],["tip","✅ Consejo"],["ojo","⚠️ Error común"],["formula","🧮 Fórmula"]].map(([v,l])=>`<option value="${v}" ${b.t===v?"selected":""}>${l}</option>`).join("")}
                </select>
                <input value="${esc(b.h||"")}" placeholder="Título del bloque" style="flex:1" oninput="CB.temas[${i}].contenido[${j}].h=this.value">
                <button class="btn btn-xs btn-danger" onclick="CB.temas[${i}].contenido.splice(${j},1);pintarConstructor()">✕</button>
              </div>
              <textarea rows="3" placeholder="Escribe aquí…" oninput="CB.temas[${i}].contenido[${j}].p=this.value">${esc(b.p||"")}</textarea>
            </div>`).join("")}
          <button class="btn btn-xs" onclick="CB.temas[${i}].contenido=CB.temas[${i}].contenido||[];CB.temas[${i}].contenido.push({t:'texto',h:'',p:''});pintarConstructor()">➕ Agregar bloque</button>
          <div class="fsec">📎 Material de este tema</div>
          <div id="mat-tema-${i}">${cbMateriales(t.materiales||[], `CB.temas[${i}].materiales`)}</div>
          ${cbAgregarMaterial(`CB.temas[${i}].materiales`, "t"+i)}
          <div class="fsec">📝 Quiz del tema</div>
          ${(t.quiz||[]).map((q,j)=>`
            <div style="border:1px solid var(--border);border-radius:9px;padding:10px;margin-bottom:7px;background:#FFFBEB">
              <div style="display:flex;gap:6px">
                <input value="${esc(q.q||"")}" placeholder="Pregunta" style="flex:1" oninput="CB.temas[${i}].quiz[${j}].q=this.value">
                <button class="btn btn-xs btn-danger" onclick="CB.temas[${i}].quiz.splice(${j},1);pintarConstructor()">✕</button></div>
              ${(q.op||[]).map((o,k)=>`<div style="display:flex;gap:6px;margin-top:5px;align-items:center">
                <input type="radio" name="c-${i}-${j}" ${q.correcta===k?"checked":""} onchange="CB.temas[${i}].quiz[${j}].correcta=${k}" title="Marcar como correcta">
                <input value="${esc(o)}" placeholder="Opción ${k+1}" style="flex:1" oninput="CB.temas[${i}].quiz[${j}].op[${k}]=this.value"></div>`).join("")}
              <button class="btn btn-xs" style="margin-top:5px" onclick="CB.temas[${i}].quiz[${j}].op.push('');pintarConstructor()">➕ Opción</button>
              <input value="${esc(q.explica||"")}" placeholder="Explicación de la respuesta correcta (el alumno la ve al fallar)" style="margin-top:6px" oninput="CB.temas[${i}].quiz[${j}].explica=this.value">
            </div>`).join("")}
          <button class="btn btn-xs" onclick="CB.temas[${i}].quiz=CB.temas[${i}].quiz||[];CB.temas[${i}].quiz.push({q:'',op:['',''],correcta:0,explica:''});pintarConstructor()">➕ Agregar pregunta</button>
        </div>`:""}
      </div>`).join("")}
    <button class="btn btn-primary" onclick="CB.temas.push({titulo:'',resumen:'',contenido:[{t:'texto',h:'',p:''}],video_url:'',duracion_min:10,materiales:[],quiz:[],_abierto:true});pintarConstructor()">➕ Agregar tema</button>
    <div style="display:flex;justify-content:space-between;margin-top:18px">
      <button class="btn" onclick="CB.paso=1;pintarConstructor()">← Atrás</button>
      <button class="btn btn-primary" onclick="cbSiguiente()">Siguiente: material →</button></div>`;
}

/* ── Materiales: el input cambia según el tipo escogido ── */
function cbMateriales(lista, ref){
  return (lista||[]).map((m,i)=>{
    const tipo=(window._tiposMat||[]).find(t=>t.id===m.tipo)||{label:m.tipo};
    return `<div class="mat-fila">
      <span>${MAT_ICO[m.tipo]||(m.tipo&&m.tipo.includes("video")?"🎬":"📎")}</span>
      <span class="nom">${esc(m.nombre||m.url||"")}${m.tamano?` <span class="small muted">${esc(m.tamano)}</span>`:""}
        <div class="small muted">${esc(tipo.label||"")}</div></span>
      <button class="btn btn-xs btn-danger" onclick="${ref}.splice(${i},1);pintarConstructor()">✕</button>
    </div>`;}).join("")||'<div class="small muted">Sin material todavía.</div>';
}
function cbAgregarMaterial(ref, uid){
  const tipos=window._tiposMat||[];
  return `<div style="display:flex;gap:7px;flex-wrap:wrap;align-items:center;margin-top:8px">
    <select id="mt-${uid}" style="max-width:190px" onchange="cbTipoCambio('${uid}')">
      ${tipos.map(t=>`<option value="${t.id}" data-modo="${t.modo}" data-accept="${t.accept}">${esc(t.label)}</option>`).join("")}
    </select>
    <span id="mi-${uid}" style="flex:1;min-width:180px">
      <button class="btn btn-sm" onclick="document.getElementById('mf-${uid}').click()">📁 Escoger archivo</button>
      <input type="file" id="mf-${uid}" style="display:none" accept=".pdf" onchange="cbArchivoSel('${uid}','${ref}',this)">
    </span>
  </div>
  <div class="small muted" id="mh-${uid}" style="margin-top:4px">Solo se aceptan archivos .pdf en esta categoría.</div>`;
}
function cbTipoCambio(uid){
  const sel=document.getElementById("mt-"+uid);
  const opt=sel.options[sel.selectedIndex];
  const modo=opt.getAttribute("data-modo"), accept=opt.getAttribute("data-accept");
  const cont=document.getElementById("mi-"+uid), hint=document.getElementById("mh-"+uid);
  const ref=sel.getAttribute("data-ref")||"";
  if(modo==="enlace"){
    cont.innerHTML=`<input id="ml-${uid}" placeholder="https://…" style="width:100%">
      <button class="btn btn-sm" style="margin-top:5px" onclick="cbEnlaceAdd('${uid}')">➕ Agregar enlace</button>`;
    hint.textContent = sel.value==="video_enlace"
      ? "Pega el enlace de YouTube o Vimeo. Quedará incrustado dentro de la clase."
      : "Pega la dirección web completa (empieza por https://).";
  } else {
    cont.innerHTML=`<button class="btn btn-sm" onclick="document.getElementById('mf-${uid}').click()">📁 Escoger archivo</button>
      <input type="file" id="mf-${uid}" style="display:none" accept="${accept}" onchange="cbArchivoSel('${uid}','${cbRefDe(uid)}',this)">`;
    hint.textContent = `Solo se aceptan archivos ${accept.split(",").join(", ")} en esta categoría.`;
  }
  window["_cbmodo_"+uid]=modo;
}
function cbRefDe(uid){
  if(uid==="clase") return "CB.materiales";
  const i=parseInt(uid.replace("t",""));
  return `CB.temas[${i}].materiales`;
}
function cbArchivoSel(uid, ref, inp){
  const f=inp.files[0]; if(!f) return;
  const sel=document.getElementById("mt-"+uid);
  const tipo=sel.value;
  const accept=(sel.options[sel.selectedIndex].getAttribute("data-accept")||"").split(",").map(x=>x.trim().replace(".",""));
  const ext=(f.name.split(".").pop()||"").toLowerCase();
  if(accept.length && !accept.includes(ext)){
    toast(`❌ «${f.name}» no es del tipo escogido. Se esperaba: ${accept.map(x=>"."+x).join(", ")}`,true);
    inp.value=""; return;
  }
  const arr=eval(cbRefDe(uid));
  arr.push({tipo, nombre:f.name, url:null, tamano:tamanoLegible(f.size)});
  inp.value="";
  toast(`📎 ${f.name} agregado.`);
  pintarConstructor();
}
function cbEnlaceAdd(uid){
  const el=document.getElementById("ml-"+uid);
  const url=(el.value||"").trim();
  const tipo=document.getElementById("mt-"+uid).value;
  if(!/^https?:\/\//i.test(url)){ toast("El enlace debe empezar por https://",true); return; }
  if(tipo==="video_enlace" && !/(youtube\.com|youtu\.be|vimeo\.com)/i.test(url)){
    toast("Ese enlace no es de YouTube ni Vimeo. Usa «🔗 Enlace web» para otras páginas.",true); return; }
  const arr=eval(cbRefDe(uid));
  arr.push({tipo, nombre:url, url, tamano:null});
  toast("🔗 Enlace agregado.");
  pintarConstructor();
}

function cbPaso3(){
  return `<div class="legal-note">📎 <b>Material de toda la clase.</b> Escoge primero el tipo y el sistema te pedirá exactamente lo que corresponde: si dices PDF solo acepta PDF, si dices video de YouTube te pide el enlace.</div>
    <div class="card"><div class="card-body">
      <div class="fsec">Material general</div>
      <div id="mat-clase">${cbMateriales(CB.materiales,"CB.materiales")}</div>
      ${cbAgregarMaterial("CB.materiales","clase")}
      <div class="fsec" style="margin-top:20px">📋 Reglas o instrucciones</div>
      <input value="${esc(CB.reglas)}" placeholder="Ej: trabajo en parejas, entregar a mano" oninput="CB.reglas=this.value" style="width:100%">
    </div></div>
    <div style="display:flex;justify-content:space-between;margin-top:18px">
      <button class="btn" onclick="CB.paso=2;pintarConstructor()">← Atrás</button>
      <button class="btn btn-primary" onclick="cbSiguiente()">Ver cómo queda →</button></div>`;
}

function cbPaso4(){
  const totalMin=CB.temas.reduce((a,t)=>a+(t.duracion_min||10),0)||CB.duracion_min;
  return `<div class="legal-note">👀 <b>Así la va a ver tu estudiante.</b> Revisa que todo esté bien y publícala.</div>
    <div class="curso-layout" style="min-height:auto">
      <div class="curso-side">
        <div class="curso-side-head">
          <h4>${CB.portada} ${esc(CB.titulo||"(sin título)")}</h4>
          <div class="curso-prog-bar"><i style="width:0%"></i></div>
          <div style="font-size:.73rem;color:#94A3B8;margin-top:6px">${esc(CB.materia||"")} · ${totalMin} min</div>
        </div>
        ${CB.objetivos.filter(o=>o.trim()).length?`<div class="mod-head">🎯 Al terminar sabrás</div>
          <div style="padding:8px 16px;font-size:.78rem;color:#94A3B8;line-height:1.5">
            ${CB.objetivos.filter(o=>o.trim()).map(o=>`<div style="margin-bottom:5px">• ${esc(o)}</div>`).join("")}</div>`:""}
        <div class="mod-head"><span>📖 Temas</span><span>0/${CB.temas.length}</span></div>
        ${CB.temas.map((t,i)=>`<div class="tema-li ${i===0?'activo':''}">
          <span class="ic">${i===0?"▶️":"○"}</span>
          <span class="tit">${esc(t.titulo||"(sin título)")}
            ${t.video_url?'<div style="font-size:.68rem;color:#F87171">🎬 con video</div>':""}
            ${(t.quiz||[]).length?`<div style="font-size:.68rem;color:#FBBF24">📝 ${t.quiz.length}</div>`:""}</span>
          <span class="dur">${t.duracion_min||10}m</span></div>`).join("")||'<div style="padding:14px;color:#64748B;font-size:.82rem">Sin temas: la clase se verá como un solo bloque.</div>'}
      </div>
      <div class="curso-main">
        ${CB.temas.length?`
          <div class="small muted">Tema 1 de ${CB.temas.length}</div>
          <h2>${esc(CB.temas[0].titulo||"(sin título)")}</h2>
          <div class="tema-meta"><span>⏱️ ${CB.temas[0].duracion_min||10} min</span></div>
          ${videoHTML(ytId(CB.temas[0].video_url||CB.video_url), CB.temas[0].video_url||CB.video_url)}
          ${CB.temas[0].resumen?`<div class="bloque"><p style="color:var(--muted)">${esc(CB.temas[0].resumen)}</p></div>`:""}
          ${(CB.temas[0].contenido||[]).map(b=>bloqueHTML(b)).join("")}
          ${(CB.temas[0].materiales||[]).length?`<div class="bloque"><h4>📎 Material</h4><div>${CB.temas[0].materiales.map(m=>matChipHTML(m)).join("")}</div></div>`:""}
        `:`
          <h2>${CB.portada} ${esc(CB.titulo||"(sin título)")}</h2>
          ${videoHTML(ytId(CB.video_url),CB.video_url)}
          <p style="white-space:pre-line;line-height:1.7">${esc(CB.descripcion||"Sin descripción.")}</p>
          <div style="margin-top:10px">${CB.materiales.map(m=>matChipHTML(m)).join("")}</div>`}
      </div>
    </div>
    <div class="card" style="margin-top:16px"><div class="card-body">
      <div class="frow"><label>Estado al guardar</label><select onchange="CB.estado=this.value">
        <option value="publicada" ${CB.estado==="publicada"?"selected":""}>✅ Publicada (los estudiantes la ven ya)</option>
        <option value="borrador" ${CB.estado==="borrador"?"selected":""}>📝 Borrador (solo yo la veo)</option>
      </select></div>
      <div style="display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap">
        <button class="btn" onclick="CB.paso=3;pintarConstructor()">← Atrás</button>
        <button class="btn btn-primary btn-lg" onclick="cbGuardar()">${CB.id?"💾 Guardar cambios":"🚀 Publicar la clase"}</button>
      </div>
    </div></div>`;
}
function cbSiguiente(){
  if(CB.paso===1 && !CB.titulo.trim()){ toast("Ponle un título a la clase",true); return; }
  if(CB.paso===2){
    const malo=CB.temas.findIndex(t=>!t.titulo.trim());
    if(malo>=0){ toast(`El tema ${malo+1} necesita título`,true); return; }
  }
  CB.paso++; pintarConstructor();
}
function cbMoverTema(i,d){
  const j=i+d; if(j<0||j>=CB.temas.length) return;
  const t=CB.temas[i]; CB.temas[i]=CB.temas[j]; CB.temas[j]=t;
  pintarConstructor();
}
async function cbGuardar(){
  const body={...CB};
  delete body.paso;
  body.objetivos=CB.objetivos.filter(o=>o.trim());
  body.temas=CB.temas.map(t=>({titulo:t.titulo,resumen:t.resumen,contenido:(t.contenido||[]).filter(b=>b.p||b.h),
    video_url:t.video_url,duracion_min:t.duracion_min,materiales:t.materiales||[],
    quiz:(t.quiz||[]).filter(q=>q.q&&q.op.filter(o=>o).length>=2)}));
  try{
    const r=await post("/clases/clase/guardar",body);
    if(!r.ok){ toast(r.msg,true); return; }
    toast(r.msg);
    VISTAS.aula();
  }catch(e){ toast("Error al guardar",true); }
}

/* ═══ V6 · PREVISUALIZAR ENTREGAS (punto 4) ═══ */
async function verEntregas(actId){
  loading();
  try{
    const d = await api(`/clases/entregas_detalle?actividad_id=${actId}`);
    if(!d.ok){ toast("No se pudo cargar",true); return; }
    window._entregas=d;
    const r=d.resumen;
    main(`<div style="display:flex;gap:10px;align-items:center;margin-bottom:14px;flex-wrap:wrap">
        <button class="btn btn-sm" onclick="VISTAS.aula()">← Aula virtual</button>
        <h2 style="margin:0;font-size:1.2rem">📝 Entregas · ${esc(d.actividad)}</h2></div>
      <div class="kpis">
        <div class="kpi green"><div class="kpi-ico">📤</div><div class="kpi-val">${r.entregadas}/${r.total}</div><div class="kpi-lbl">Entregaron</div></div>
        <div class="kpi ${r.pendientes?'orange':''}"><div class="kpi-ico">⏳</div><div class="kpi-val">${r.pendientes}</div><div class="kpi-lbl">Sin entregar</div></div>
        <div class="kpi ${r.vencidas?'red':''}"><div class="kpi-ico">🚨</div><div class="kpi-val">${r.vencidas}</div><div class="kpi-lbl">Vencidas</div></div>
        <div class="kpi"><div class="kpi-ico">📗</div><div class="kpi-val">${r.promedio!=null?r.promedio:"—"}</div><div class="kpi-lbl">Promedio</div></div>
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">
        ${[["todas","Todas"],["entregado","📤 Por calificar"],["revisado","✅ Calificadas"],["pendiente","⏳ Sin entregar"]].map(([k,l])=>
          `<button class="chip-filtro ${(window._entFiltro||'todas')===k?'active':''}" onclick="window._entFiltro='${k}';pintarEntregas()">${l}</button>`).join("")}
      </div>
      <div id="ent-cont"></div>`);
    pintarEntregas();
  }catch(e){ main(`<div class="empty">Error</div>`); }
}
function pintarEntregas(){
  const d=window._entregas;
  const f=window._entFiltro||"todas";
  const lista=f==="todas"?d.entregas:d.entregas.filter(x=>x.estado===f);
  document.getElementById("ent-cont").innerHTML = lista.map(e=>`
    <div class="entrega-card ${e.estado==='revisado'?'rev':e.estado==='entregado'?'ent':'pend'}">
      <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap">
        <div class="avatar-sm">${ini(e.estudiante)}</div>
        <div style="flex:1;min-width:170px">
          <b>${esc(e.estudiante)}</b>
          ${e.estado==="revisado"?'<span class="badge b-green">Calificado</span>':e.estado==="entregado"?'<span class="badge b-blue">Por calificar</span>':'<span class="badge b-gray">Sin entregar</span>'}
          ${e.entregado_tarde?'<span class="badge b-orange">⏰ Tarde</span>':""}
          ${e.vencida?'<span class="badge b-red">🚨 Vencida</span>':""}
          <div class="small muted">${e.fecha_entrega?"Entregó el "+esc(e.fecha_entrega):"Todavía no entrega"}${e.n_palabras?" · "+e.n_palabras+" palabras":""}</div>
        </div>
        ${e.nota!=null?`<div style="text-align:center"><div style="font-size:1.5rem;font-weight:800;color:${e.nota>=3?'var(--green)':'var(--red)'}">${e.nota}</div><div class="small muted">nota</div></div>`:""}
      </div>
      ${e.respuesta?`<div class="entrega-texto">${esc(e.respuesta)}</div>`:""}
      ${e.archivo?`<div style="margin:6px 0"><span class="mat-chip">📎 ${esc(e.archivo)}</span>
        <button class="btn btn-xs" onclick="toast('En producción aquí se abre el archivo que subió el estudiante.')">👁️ Abrir</button></div>`:""}
      ${e.estado!=="pendiente"?`
        <div style="display:flex;gap:8px;align-items:flex-end;margin-top:10px;flex-wrap:wrap">
          <div style="width:90px"><label class="small">Nota (0-5)</label>
            <input type="number" id="nt-${e.entrega_id}" value="${e.nota!=null?e.nota:""}" min="0" max="5" step="0.1"></div>
          <div style="flex:1;min-width:170px"><label class="small">Comentario para el estudiante</label>
            <input id="rt-${e.entrega_id}" value="${esc(e.retro||"")}" placeholder="Qué hizo bien y qué mejorar…"></div>
          <button class="btn btn-sm btn-primary" onclick="calificarEntregaV6(${e.entrega_id})">💾 Guardar</button>
        </div>`:`
        <div style="margin-top:8px"><button class="btn btn-xs" onclick="toast('📱 Recordatorio enviado al acudiente (simulado).')">📱 Recordar al acudiente</button></div>`}
    </div>`).join("")||'<div class="empty">Sin entregas con este filtro.</div>';
}
async function calificarEntregaV6(id){
  const nota=parseFloat(document.getElementById("nt-"+id).value);
  const retro=document.getElementById("rt-"+id).value;
  try{
    const r=await post("/clases/calificar",{entrega_id:id,nota:isNaN(nota)?null:nota,retro});
    toast(r.msg,!r.ok);
    if(r.ok) verEntregas(window._entregas.entregas[0]?window._entregasActId:null) || 0;
  }catch(e){ toast("Error",true); }
}

/* ═══ V6 · BIBLIOTECA DE CLASES GRABADAS (punto 17) ═══ */
VISTAS.biblioteca = async function(materia){
  loading();
  try{
    const d = await api(`/clases/biblioteca?institucion_id=${ST.institucion_id}${materia?"&materia="+encodeURIComponent(materia):""}`);
    main(head("Biblioteca de clases","Las clases en vivo quedan grabadas: si faltaste o quieres repasar, aquí están")+`
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px">
        <button class="chip-filtro ${!materia?'active':''}" onclick="VISTAS.biblioteca()">Todas</button>
        ${d.materias.map(m=>`<button class="chip-filtro ${materia===m?'active':''}" onclick="VISTAS.biblioteca('${esc(m)}')">${MATERIA_ICO[m]||"📚"} ${esc(m)}</button>`).join("")}
      </div>
      <div class="grid-cards">
        ${d.grabaciones.map(g=>`
          <div class="clase-card" onclick="verGrabacion(${g.id})">
            <div class="clase-portada" style="background:linear-gradient(135deg,#1E293B,#334155)">
              ${g.youtube_id?"▶️":"📼"}
              <span class="est">${g.duracion_min} min</span></div>
            <div class="clase-body">
              <h4>${esc(g.titulo)}</h4>
              <div class="small muted">${MATERIA_ICO[g.materia]||"📚"} ${esc(g.materia||"")} · Salón ${esc(g.salon)}</div>
              <div class="small muted">👨‍🏫 ${esc(g.docente||"")}</div>
              <div class="small muted" style="margin-top:4px">📅 ${esc(g.fecha)} · 👁️ ${g.n_vistas} vistas</div>
            </div></div>`).join("")||'<div class="empty">Todavía no hay clases grabadas.</div>'}
      </div>
      <div class="legal-note">📼 Cada clase en vivo que el docente finaliza queda guardada aquí con su chat. Así el estudiante que no tuvo señal ese día no se queda atrás.</div>`);
  }catch(e){ main(`<div class="empty">Error</div>`); }
};
async function verGrabacion(id){
  try{
    const g = await api(`/clases/biblioteca/ver?id=${id}`);
    if(!g.ok) return;
    document.getElementById("modal-srd-title").textContent="📼 "+g.titulo;
    document.getElementById("modal-srd-body").innerHTML=`
      ${videoHTML(g.youtube_id,g.video_url)||`<div class="video-wrap"><div class="video-ph">
        <div style="font-size:2.4rem">📼</div><div>Grabación de la clase</div>
        <div class="small">En producción aquí se reproduce el video guardado.</div></div></div>`}
      <div class="info-grid">
        <div class="info-it"><span class="k">Materia</span><b>${esc(g.materia||"—")}</b></div>
        <div class="info-it"><span class="k">Docente</span><b>${esc(g.docente||"—")}</b></div>
        <div class="info-it"><span class="k">Salón</span><b>${esc(g.salon)}</b></div>
        <div class="info-it"><span class="k">Duración</span><b>${g.duracion_min} min</b></div>
      </div>
      ${g.resumen?`<div class="legal-note">📝 ${esc(g.resumen)}</div>`:""}
      ${g.chat&&g.chat.length?`<div class="fsec">💬 Chat de esa clase</div>
        <div class="chat-box">${g.chat.map(m=>`<div class="chat-msg ${m.tipo==='docente'?'doc':''}">
          <div class="bub"><div class="aut">${m.tipo==='docente'?'🧑‍🏫 ':'🎒 '}${esc(m.autor)} · ${esc(m.hora)}</div>${esc(m.texto)}</div></div>`).join("")}</div>`:""}`;
    abrirModal("modal-srd");
  }catch(e){ toast("Error",true); }
}

/* ═══ V6 · MODO SIN INTERNET ═══ */
const OFF = {cola:[], online:true};
function initOffline(){
  OFF.online = navigator.onLine !== false;
  try{ const g=sessionStorage.getItem("gyver_cola"); if(g) OFF.cola=JSON.parse(g); }catch(e){}
  window.addEventListener("online", ()=>{ OFF.online=true; pintarBarraOffline();
    if(OFF.cola.length){ toast("📶 Volvió el internet. Sincronizando tu trabajo…"); sincronizarOffline(); } });
  window.addEventListener("offline", ()=>{ OFF.online=false; pintarBarraOffline();
    toast("📴 Sin conexión. Puedes seguir trabajando: todo se guarda y se sube cuando vuelva la señal."); });
  pintarBarraOffline();
}
function guardarCola(){
  try{ sessionStorage.setItem("gyver_cola", JSON.stringify(OFF.cola)); }catch(e){}
  pintarBarraOffline();
}
function pintarBarraOffline(){
  const b=document.getElementById("offline-bar");
  if(!b) return;
  const n=OFF.cola.length;
  b.classList.toggle("on", !OFF.online || n>0);
  const el=document.getElementById("offline-n");
  if(el) el.textContent = n ? `${n} pendiente(s)` : "";
  b.querySelector("span").textContent = OFF.online
    ? "📶 Con conexión — tienes trabajo guardado sin subir"
    : "📴 Sin conexión — tu trabajo se está guardando en el dispositivo";
}
function encolarOffline(tipo, payload){
  OFF.cola.push({tipo, payload, creado_en:new Date().toISOString()});
  guardarCola();
  toast(`💾 Guardado en el dispositivo (${OFF.cola.length} sin subir). Se enviará cuando vuelva el internet.`);
}
async function sincronizarOffline(){
  if(!OFF.cola.length){ toast("No hay nada pendiente por sincronizar."); return; }
  const n=OFF.cola.length;
  try{
    const r=await post("/dominios/offline/sincronizar",{institucion_id:ST.institucion_id,
      origen:(ST.perfil.nombre||"Docente"), acciones:OFF.cola});
    if(r.ok){
      OFF.cola=[]; guardarCola();
      toast(r.msg);
      if(r.detalles&&r.detalles.length) setTimeout(()=>toast("✓ "+r.detalles.slice(0,3).join(" · ")),1200);
    } else toast("No se pudo sincronizar. Se intentará de nuevo.",true);
  }catch(e){ toast(`Sin conexión todavía. Tus ${n} acciones siguen guardadas.`,true); }
}
/* Envoltura: si no hay internet, encola en vez de fallar */
async function postOffline(path, body, tipoCola){
  if(!OFF.online){ encolarOffline(tipoCola, body); return {ok:true, offline:true, msg:"Guardado sin conexión."}; }
  try{ return await post(path, body); }
  catch(e){ encolarOffline(tipoCola, body); return {ok:true, offline:true, msg:"Se guardó en el dispositivo."}; }
}

/* ═══════════════════════════════════════════════════════════════════
   V6 · DOMINIOS Y DNS (puntos 1, 2, 3) — panel del súper admin
   ═══════════════════════════════════════════════════════════════════ */

VISTAS.dominios = async function(){
  loading();
  try{
    if(!window._domCat) window._domCat = await api(`/dominios/catalogo`);
    const d = await api(`/dominios/`);
    window._domData = d;
    const r=d.resumen;
    main(head("Dominios y contratos","Conecta el dominio de cada institución y controla su suscripción")+`
      <div class="kpis">
        <div class="kpi green"><div class="kpi-ico">🌐</div><div class="kpi-val">${r.dns_activos}/${r.n_tenants}</div><div class="kpi-lbl">Dominios activos</div></div>
        <div class="kpi ${r.por_vencer?'orange':''}"><div class="kpi-ico">⏳</div><div class="kpi-val">${r.por_vencer}</div><div class="kpi-lbl">Contratos por vencer</div></div>
        <div class="kpi ${r.vencidas?'red':''}"><div class="kpi-ico">🚨</div><div class="kpi-val">${r.vencidas}</div><div class="kpi-lbl">Vencidos</div></div>
        <div class="kpi gold"><div class="kpi-ico">💰</div><div class="kpi-val sm">${money(r.por_cobrar)}</div><div class="kpi-lbl">Por cobrar</div></div>
      </div>
      <div class="card"><div class="card-head"><h3>💵 Ingresos de la red</h3></div><div class="card-body">
        <div style="display:flex;gap:20px;flex-wrap:wrap">
          <div><div class="small muted">Facturación anual</div><b style="font-size:1.3rem">${money(r.ingreso_anual)}</b></div>
          <div><div class="small muted">Recaudado</div><b style="font-size:1.3rem;color:var(--green)">${money(r.recaudado)}</b></div>
          <div><div class="small muted">Pendiente</div><b style="font-size:1.3rem;color:var(--orange)">${money(r.por_cobrar)}</b></div>
          <div><div class="small muted">Estudiantes en la red</div><b style="font-size:1.3rem">${r.total_estudiantes}</b></div>
        </div>
        <div class="prog" style="margin-top:12px"><div class="prog-fill" style="width:${r.ingreso_anual?Math.round(100*r.recaudado/r.ingreso_anual):0}%"></div></div>
      </div></div>
      <div class="card"><div class="card-head"><h3>🏫 Instituciones y sus dominios</h3></div>
      <div class="tbl-scroll"><table>
        <thead><tr><th>Institución</th><th>Dominio</th><th>DNS</th><th>Contrato</th><th style="text-align:right">Valor</th><th></th></tr></thead>
        <tbody>${d.tenants.map(t=>{
          const s=t.suscripcion, dn=t.dns;
          return `<tr>
            <td><div class="flex-cell">
              ${t.logo?`<img src="${t.logo}" style="width:30px;height:30px;object-fit:contain;border-radius:6px;background:#fff;border:1px solid var(--border)">`:`<span class="tn-dot" style="background:${t.color}"></span>`}
              <div><b>${esc(t.nombre)}</b><div class="small muted">${t.tipo==="secretaria"?"🏛️ Secretaría":"🏫 Colegio"} · ${t.n_estudiantes} est.</div></div></div></td>
            <td class="small">${dn.configurado?`<code>${esc((dn.subdominio?dn.subdominio+".":"")+dn.dominio)}</code>`:'<span class="muted">sin configurar</span>'}
              ${dn.wordpress_url?'<div class="small muted">web en WordPress</div>':""}</td>
            <td><span class="dns-estado dns-${dn.estado_dns}">${dn.estado_dns==="activo"?"✅ Activo":dn.estado_dns==="propagando"?"🔄 Propagando":dn.estado_dns==="pendiente"?"⏳ Pendiente":"— Sin configurar"}</span></td>
            <td class="small">${s.activa?`${esc(s.plan)}<div class="muted">${s.vencida?'<span style="color:var(--red)">vencido</span>':s.por_vencer?`<span style="color:var(--orange)">vence en ${s.dias_restantes} días</span>`:`${s.dias_restantes} días restantes`}</div>`:'<span class="muted">sin contrato</span>'}</td>
            <td style="text-align:right" class="small">${s.valor_anual?`${money(s.valor_anual)}<div class="muted">pagado ${money(s.pagado)}</div>`:"—"}</td>
            <td><button class="btn btn-xs btn-primary" onclick="abrirDominio(${t.tenant_id})">⚙️ Configurar</button></td>
          </tr>`;}).join("")}
        </tbody></table></div></div>
      <div class="legal-note">🌐 <b>Cómo funciona:</b> compras el dominio donde quieras (Hostinger, GoDaddy, Namecheap…), entras aquí, escoges dónde montar el sistema, y el panel te da los registros DNS exactos para pegar en tu proveedor. La página web actual del colegio en WordPress no se toca.</div>`);
  }catch(e){ main(`<div class="empty">Error</div>`); }
};

async function abrirDominio(tenantId){
  loading();
  try{
    const d = await api(`/dominios/detalle?tenant_id=${tenantId}`);
    if(!d.ok){ toast("No se pudo cargar",true); return; }
    window._dom = d;
    const c=d.config, cat=window._domCat;
    main(`<div style="display:flex;gap:10px;align-items:center;margin-bottom:14px;flex-wrap:wrap">
        <button class="btn btn-sm" onclick="VISTAS.dominios()">← Dominios</button>
        <h2 style="margin:0;font-size:1.2rem">🌐 ${esc(d.tenant.nombre)}</h2>
        <span class="dns-estado dns-${c.estado_dns}" style="margin-left:auto">${c.estado_dns==="activo"?"✅ Activo":c.estado_dns==="propagando"?"🔄 Propagando":"⏳ Pendiente"}</span></div>
      <div class="subtabs">
        ${[["config","⚙️ Configuración"],["dns","📋 Registros DNS"],["wp","🔌 Sitio actual"],["contrato","💰 Contrato"]].map(([k,l])=>
          `<button class="subtab ${(window._domTab||'config')===k?'active':''}" onclick="window._domTab='${k}';abrirDominio(${tenantId})">${l}</button>`).join("")}</div>
      <div id="dom-cont"></div>`);
    const t=window._domTab||"config";
    const cont=document.getElementById("dom-cont");
    if(t==="config") cont.innerHTML=domConfig(d,cat);
    if(t==="dns") cont.innerHTML=domDNS(d);
    if(t==="wp") cont.innerHTML=domWP(d);
    if(t==="contrato") cont.innerHTML=domContrato(d);
  }catch(e){ main(`<div class="empty">Error</div>`); }
}
function domConfig(d,cat){
  const c=d.config;
  return `<div class="card"><div class="card-body">
    <div class="fsec">1️⃣ ¿Dónde va a vivir el sistema?</div>
    <div class="small muted" style="margin-bottom:10px">La mayoría de colegios ya tiene su página en WordPress. Lo recomendado es dejarla intacta y montar el sistema en un subdominio.</div>
    <div class="wiz-modos" style="grid-template-columns:repeat(auto-fit,minmax(230px,1fr))">
      ${cat.modos.map(m=>`
        <div class="wiz-modo ${c.modo_montaje===m.id?'sel':''}" onclick="window._dom.config.modo_montaje='${m.id}';abrirDominio(${d.tenant.id})">
          <div class="ic">${m.id==="subdominio"?"🔗":m.id==="dominio_propio"?"🌐":"📁"}</div>
          <b>${esc(m.label)}</b>
          <div class="small">${esc(m.desc)}</div>
          <div class="small" style="margin-top:6px;color:var(--teal)"><code>${esc(m.ejemplo)}</code></div>
        </div>`).join("")}
    </div>
    <div class="legal-note">💡 ${esc((cat.modos.find(m=>m.id===c.modo_montaje)||{}).ventaja||"")}</div>
    <div class="fsec">2️⃣ El dominio</div>
    <div class="frow-2">
      <div><label>Dominio comprado *</label><input id="dm_dominio" value="${esc(c.dominio||"")}" placeholder="ietac.edu.co">
        <div class="small muted" style="margin-top:4px">Sin https:// ni www</div></div>
      <div><label>Subdominio</label><input id="dm_sub" value="${esc(c.subdominio||"sistema")}" placeholder="sistema" ${c.modo_montaje!=="subdominio"?"disabled":""}>
        <div class="small muted" style="margin-top:4px">Queda: <code>${esc(c.subdominio||"sistema")}.${esc(c.dominio||"dominio.edu.co")}</code></div></div>
    </div>
    <div class="frow-2">
      <div><label>¿Dónde compraste el dominio?</label><select id="dm_prov">
        ${cat.proveedores.map(p=>`<option value="${p.id}" ${c.proveedor===p.id?"selected":""}>${esc(p.label)}</option>`).join("")}</select></div>
      <div><label>IP del servidor</label><input id="dm_ip" value="${esc(c.ip_servidor||cat.ip_servidor)}">
        <div class="small muted" style="margin-top:4px">La del servidor donde corre el sistema</div></div>
    </div>
    <div class="frow"><label>Notas internas</label><input id="dm_notas" value="${esc(c.notas||"")}" placeholder="Ej: el dominio lo maneja el rector"></div>
    <div style="display:flex;gap:8px;justify-content:flex-end;flex-wrap:wrap">
      <button class="btn btn-primary" onclick="guardarDominio(${d.tenant.id})">💾 Guardar y generar DNS</button>
    </div>
    <div class="legal-note" style="margin-top:12px;background:#F0FDFA;border-color:var(--teal)">
      🎯 <b>Dirección final:</b> <code>${esc(d.url_final)}</code> — así entrarán los docentes y estudiantes de esta institución. Sin ningún rastro de GyverLabs.</div>
  </div></div>`;
}
function domDNS(d){
  const c=d.config, p=d.proveedor_info||{};
  return `<div class="legal-note">📋 <b>Copia estos registros</b> en el panel de tu proveedor. Es un copiar y pegar: no hay que saber de redes.</div>
    <div class="card"><div class="card-head"><h3>Paso a paso en ${esc(p.label||"tu proveedor")}</h3></div><div class="card-body">
      <div class="paso-dns"><div class="num">1</div><div>Entra a tu cuenta de <b>${esc(p.label||"tu proveedor")}</b> y busca:<br><code>${esc(p.panel||"Zona DNS")}</code></div></div>
      <div class="paso-dns"><div class="num">2</div><div>Agrega cada uno de los registros de la tabla de abajo (botón «Agregar registro»).</div></div>
      <div class="paso-dns"><div class="num">3</div><div>Guarda los cambios. La propagación tarda entre 5 minutos y 24 horas.</div></div>
      <div class="paso-dns" style="border:none"><div class="num">4</div><div>Vuelve aquí y presiona <b>Verificar</b>. Cuando quede en verde, el certificado SSL se emite solo.</div></div>
      ${p.ayuda?`<div style="margin-top:10px"><a href="${esc(p.ayuda)}" target="_blank" class="btn btn-sm">📖 Guía oficial de ${esc(p.label)}</a></div>`:""}
    </div></div>
    <div class="card"><div class="card-head"><h3>📋 Registros que debes crear</h3>
      <button class="btn btn-sm" onclick="copiarDNS()">📄 Copiar todo</button></div>
    <div class="tbl-scroll"><table class="dns-tabla">
      <thead><tr><th>Tipo</th><th>Nombre / Host</th><th>Valor / Apunta a</th><th>TTL</th></tr></thead>
      <tbody>${d.registros_dns.map(r=>`<tr>
        <td><b>${esc(r.tipo)}</b></td>
        <td>${esc(r.nombre)}</td>
        <td>${esc(r.valor)}<div class="small muted" style="font-family:system-ui">${esc(r.para)}</div></td>
        <td>${esc(r.ttl)}</td></tr>`).join("")}
      </tbody></table></div></div>
    <div class="card"><div class="card-body" style="text-align:center">
      <div class="dns-estado dns-${c.estado_dns}" style="font-size:.95rem;padding:8px 18px">
        ${c.estado_dns==="activo"?"✅ DNS activo y SSL emitido":c.estado_dns==="propagando"?"🔄 Propagando…":"⏳ Esperando los registros"}</div>
      <div class="small muted" style="margin:10px 0">${c.ultima_verificacion?"Última verificación: "+esc(c.ultima_verificacion):"Todavía no se ha verificado"}</div>
      <button class="btn btn-primary" onclick="verificarDNS(${d.tenant.id})">🔍 Verificar ahora</button>
    </div></div>`;
}
function domWP(d){
  const c=d.config;
  return `<div class="legal-note">🔌 <b>La página web actual del colegio.</b> Casi todos tienen su sitio en WordPress. Aquí decides cómo se conecta con el sistema, sin dañar lo que ya existe.</div>
    <div class="card"><div class="card-body">
      <div class="frow"><label>Dirección de la web institucional actual</label>
        <input id="wp_url" value="${esc(c.wordpress_url||"")}" placeholder="https://ietac.edu.co"></div>
      <div class="fsec">¿Cómo se conecta con el sistema?</div>
      ${[["enlace","🔗 Botón en el menú de WordPress",
          "Se agrega un botón «Plataforma» que lleva al subdominio. Es lo más simple y lo que menos puede fallar.",
          "En WordPress: Apariencia → Menús → Enlace personalizado → pegar la dirección."],
         ["plugin","🧩 Plugin de conexión",
          "Un plugin muestra el acceso y el estado del sistema dentro de WordPress, con inicio de sesión unificado.",
          "Se instala el plugin GyverLabs Connect y se pega la clave de la institución."],
         ["iframe","🖼️ Incrustado en una página",
          "El sistema se ve dentro de una página del sitio. Funciona, pero se pierde parte de la experiencia en celular.",
          "Se crea una página y se incrusta el sistema con un iframe."],
         ["ninguna","🚫 Sin conexión",
          "El sistema vive aparte. Los usuarios entran directo por su dirección.",
          "No requiere tocar WordPress."]
        ].map(([id,tit,desc,como])=>`
        <div class="wiz-modo ${c.integracion_wp===id?'sel':''}" style="text-align:left;margin-bottom:9px" onclick="window._dom.config.integracion_wp='${id}';abrirDominio(${d.tenant.id})">
          <b>${tit}</b>
          <div class="small" style="margin:4px 0">${desc}</div>
          <div class="small muted">📌 ${como}</div>
        </div>`).join("")}
      <div style="text-align:right"><button class="btn btn-primary" onclick="guardarDominio(${d.tenant.id})">💾 Guardar</button></div>
    </div></div>`;
}
function domContrato(d){
  const s=d.suscripcion;
  const pagado=(s.facturas||[]).reduce((a,f)=>a+(f.valor||0),0);
  return `<div class="card"><div class="card-body">
    <div class="fsec">📅 Vigencia del contrato</div>
    <div class="frow-3">
      <div><label>Plan</label><select id="su_plan">
        ${[["piloto","Piloto (1 colegio)"],["institucional","Institucional"],["municipal","Municipal"],["departamental","Departamental"]].map(([v,l])=>`<option value="${v}" ${s.plan===v?"selected":""}>${l}</option>`).join("")}</select></div>
      <div><label>Fecha de inicio</label><input type="date" id="su_ini" value="${s.inicio||""}"></div>
      <div><label>Duración (meses)</label><input type="number" id="su_meses" value="12"></div>
    </div>
    <div class="frow-2">
      <div><label>Valor anual (COP)</label><input type="number" id="su_valor" value="${s.valor_anual||0}"></div>
      <div><label>Usuarios incluidos</label><input type="number" id="su_usuarios" value="${s.n_usuarios_incluidos||100}"></div>
    </div>
    ${s.fin?`<div class="legal-note" style="background:${s.estado==='vencida'?'#FEE2E2':s.estado==='por_vencer'?'#FEF3C7':'#DCFCE7'}">
      📅 Del <b>${esc(s.inicio||"—")}</b> al <b>${esc(s.fin)}</b> — estado: <b>${esc(s.estado)}</b></div>`:""}
    <div style="text-align:right"><button class="btn btn-primary" onclick="guardarSuscripcion(${d.tenant.id})">💾 Guardar contrato</button></div>
    <div class="fsec">💰 Pagos recibidos</div>
    <div class="tbl-scroll"><table><thead><tr><th>Fecha</th><th>Concepto</th><th style="text-align:right">Valor</th></tr></thead>
      <tbody>${(s.facturas||[]).map(f=>`<tr><td class="small">${esc(f.fecha)}</td><td class="small">${esc(f.concepto)}</td>
        <td style="text-align:right"><b>${money(f.valor)}</b></td></tr>`).join("")||'<tr><td colspan="3" class="empty">Sin pagos registrados</td></tr>'}
      <tr style="background:#F8FAFC"><td colspan="2"><b>Total recaudado</b></td><td style="text-align:right"><b>${money(pagado)}</b></td></tr>
      <tr><td colspan="2" class="small muted">Saldo pendiente</td><td style="text-align:right" class="small"><b style="color:var(--orange)">${money((s.valor_anual||0)-pagado)}</b></td></tr>
      </tbody></table></div>
    <div style="display:flex;gap:8px;align-items:flex-end;margin-top:12px;flex-wrap:wrap">
      <div style="width:150px"><label class="small">Valor del pago</label><input type="number" id="pg_valor"></div>
      <div style="flex:1;min-width:160px"><label class="small">Concepto</label><input id="pg_concepto" placeholder="Cuota 2 de 3"></div>
      <button class="btn btn-sm btn-primary" onclick="registrarPagoSus(${d.tenant.id})">💰 Registrar pago</button>
    </div>
  </div></div>`;
}
async function guardarDominio(tid){
  const g=id=>{const e=document.getElementById(id);return e?e.value:null;};
  const body={tenant_id:tid,
    dominio:g("dm_dominio")||window._dom.config.dominio,
    subdominio:g("dm_sub")||window._dom.config.subdominio,
    proveedor:g("dm_prov")||window._dom.config.proveedor,
    modo_montaje:window._dom.config.modo_montaje,
    ip_servidor:g("dm_ip")||window._dom.config.ip_servidor,
    wordpress_url:g("wp_url")||window._dom.config.wordpress_url,
    integracion_wp:window._dom.config.integracion_wp,
    notas:g("dm_notas")||window._dom.config.notas};
  try{ const r=await post("/dominios/guardar",body);
    toast(r.msg,!r.ok);
    if(r.ok){ window._domTab="dns"; abrirDominio(tid); }
  }catch(e){ toast("Error",true); }
}
async function verificarDNS(tid){
  toast("🔍 Consultando los registros DNS…");
  try{ const r=await post("/dominios/verificar",{tenant_id:tid});
    toast(r.msg,!r.ok); if(r.ok) abrirDominio(tid);
  }catch(e){ toast("Error",true); }
}
function copiarDNS(){
  const d=window._dom;
  const txt=d.registros_dns.map(r=>`${r.tipo}\t${r.nombre}\t${r.valor}\t${r.ttl}`).join("\n");
  try{ navigator.clipboard.writeText(txt); toast("📄 Registros copiados. Pégalos en tu proveedor."); }
  catch(e){ prompt("Copia estos registros:", txt); }
}
async function guardarSuscripcion(tid){
  const body={tenant_id:tid, plan:document.getElementById("su_plan").value,
    fecha_inicio:document.getElementById("su_ini").value||null,
    meses:parseInt(document.getElementById("su_meses").value)||12,
    valor_anual:parseFloat(document.getElementById("su_valor").value)||0,
    n_usuarios_incluidos:parseInt(document.getElementById("su_usuarios").value)||100};
  try{ const r=await post("/dominios/suscripcion/guardar",body); toast(r.msg,!r.ok); if(r.ok) abrirDominio(tid); }
  catch(e){ toast("Error",true); }
}
async function registrarPagoSus(tid){
  const valor=parseFloat(document.getElementById("pg_valor").value)||0;
  if(!valor){ toast("Escribe el valor del pago",true); return; }
  try{ const r=await post("/dominios/suscripcion/pago",{tenant_id:tid,valor,
      concepto:document.getElementById("pg_concepto").value}); toast(r.msg,!r.ok); if(r.ok) abrirDominio(tid); }
  catch(e){ toast("Error",true); }
}

/* ── Acciones de gestión de clases (punto 8) ── */
function verEntregasDe(id){ window._entregasActId=id; window._entFiltro="todas"; verEntregas(id); }
async function duplicarClase(id){
  if(!confirm("¿Duplicar esta clase? Quedará como borrador para que la edites.")) return;
  try{ const r=await post("/clases/clase/duplicar",{id}); toast(r.msg,!r.ok);
    if(r.ok) setTimeout(()=>abrirConstructor(r.id),700);
  }catch(e){ toast("Error",true); }
}
async function eliminarClase(id,titulo){
  if(!confirm(`¿Eliminar «${titulo}»?\n\nSe borran también sus temas y las entregas de los estudiantes. Esta acción no se puede deshacer.`)) return;
  try{ const r=await post("/clases/clase/eliminar",{id}); toast(r.msg,!r.ok); if(r.ok) VISTAS.aula(); }
  catch(e){ toast("Error",true); }
}
/* Vista de la clase para el DOCENTE (igual que la ve el alumno, pero con sus botones) */
async function abrirClaseDocente(id){
  loading();
  try{
    const d = await api(`/clases/clase?actividad_id=${id}`);
    if(!d.ok){ toast("No se pudo abrir",true); return; }
    window._claseAl = d;
    main(`<div style="display:flex;gap:10px;align-items:center;margin-bottom:14px;flex-wrap:wrap">
        <button class="btn btn-sm" onclick="VISTAS.aula()">← Aula virtual</button>
        <h2 style="margin:0;font-size:1.2rem">${d.portada||"📘"} ${esc(d.titulo)}</h2>
        <div style="margin-left:auto;display:flex;gap:6px;flex-wrap:wrap">
          <button class="btn btn-sm btn-primary" onclick="verEntregasDe(${d.id})">📝 Entregas</button>
          <button class="btn btn-sm" onclick="abrirConstructor(${d.id})">✎ Editar</button>
          <button class="btn btn-sm" onclick="window.open(API+'/aula/actividades/guia?id=${d.id}')">⬇️ Guía PDF</button>
        </div></div>
      <div class="legal-note">👀 Así ven tus estudiantes esta clase.</div>
      ${d.n_temas?`<div class="curso-layout">
          <div class="curso-side" id="clase-side"></div>
          <div class="curso-main" id="clase-main"></div></div>`
        :`<div class="card"><div class="card-body">
            ${videoHTML(d.youtube_id,d.video_url)}
            <p style="white-space:pre-line;line-height:1.7">${esc(d.descripcion||"Sin descripción.")}</p>
            <div style="margin-top:10px">${(d.materiales||[]).map(m=>matChipHTML(m)).join("")}</div>
            <div class="legal-note" style="margin-top:14px;background:#FEF3C7;border-color:var(--gold)">
              💡 Esta clase todavía no tiene temas. Con <b>✎ Editar</b> puedes dividirla en temas con video y quiz, para que los estudiantes la recorran paso a paso.</div>
          </div></div>`}`);
    if(d.n_temas){ pintarTemarioClase(d.tema_actual); if(d.tema_actual) await abrirTemaClaseDocente(d.tema_actual); }
  }catch(e){ main(`<div class="empty">Error</div>`); }
}
async function abrirTemaClaseDocente(temaId){
  try{
    const t=await api(`/clases/tema?tema_id=${temaId}`);
    if(!t.ok) return;
    document.getElementById("clase-main").innerHTML=`
      <div class="small muted">Tema ${t.posicion} de ${t.total}</div>
      <h2>${esc(t.titulo)}</h2>
      <div class="tema-meta"><span>⏱️ ${t.duracion_min} min</span>${t.quiz.length?`<span>📝 ${t.quiz.length} pregunta(s)</span>`:""}</div>
      ${videoHTML(t.youtube_id,t.video_url)}
      ${t.resumen?`<div class="bloque"><p style="color:var(--muted)">${esc(t.resumen)}</p></div>`:""}
      ${t.contenido.map(b=>bloqueHTML(b)).join("")}
      ${(t.materiales||[]).length?`<div class="bloque"><h4>📎 Material</h4><div>${t.materiales.map(m=>matChipHTML(m)).join("")}</div></div>`:""}
      ${t.quiz.length?`<div class="quiz-box"><b>📝 Quiz de este tema</b>
        ${t.quiz.map((q,i)=>`<div style="margin-top:10px"><b class="small">${i+1}. ${esc(q.q)}</b>
          ${q.op.map((o,j)=>`<div class="quiz-op ${j===q.correcta?'ok':''}" style="cursor:default">${j===q.correcta?"✅ ":""}${esc(o)}</div>`).join("")}
          ${q.explica?`<div class="small muted" style="margin-top:4px">💡 ${esc(q.explica)}</div>`:""}</div>`).join("")}
        </div>`:""}
      <div class="tema-nav">
        ${t.anterior?`<button class="btn" onclick="abrirTemaClaseDocente(${t.anterior})">← Anterior</button>`:"<span></span>"}
        ${t.siguiente?`<button class="btn" onclick="abrirTemaClaseDocente(${t.siguiente})">Siguiente →</button>`:"<span></span>"}
      </div>`;
    pintarTemarioClase(temaId);
  }catch(e){ toast("Error",true); }
}

/* ═══════════════════════════════════════════════════════════════════
   V7 · SINCRONIZACIÓN EN VIVO (puntos 9, 10)
   ═══════════════════════════════════════════════════════════════════ */
const VIVO = {version:0, timer:null, vista:null, otros:[], ultimo:null};

function iniciarVivo(vista){
  VIVO.vista = vista;
  if(VIVO.timer) clearInterval(VIVO.timer);
  latirVivo();
  VIVO.timer = setInterval(latirVivo, 8000);
}
function pararVivo(){ if(VIVO.timer){ clearInterval(VIVO.timer); VIVO.timer=null; } }
async function latirVivo(){
  if(!ST.institucion_id || ST.vista!==VIVO.vista){ pararVivo(); return; }
  try{
    const u = encodeURIComponent(ST.perfil.nombre||ST.perfil.titulo||"Usuario");
    const d = await api(`/vivo/estado?institucion_id=${ST.institucion_id}&version=${VIVO.version}&usuario=${u}&vista=${VIVO.vista}`);
    VIVO.otros = d.otros_conectados||[];
    if(d.hay_cambio && VIVO.version>0){
      VIVO.ultimo = d.ultimo;
      pintarBarraVivo(true);
      toast(`🔄 ${d.ultimo?d.ultimo.detalle||"Hubo cambios":"Hubo cambios"} — actualizando…`);
      VIVO.version = d.version;
      if(ST.vista==="alertas") VISTAS.alertas(ST._alertaFiltro||"abierta");
      else if(ST.vista==="resumen") VISTAS.resumen();
    } else {
      VIVO.version = d.version;
      pintarBarraVivo(false);
    }
  }catch(e){}
}
function pintarBarraVivo(hubo){
  const el=document.getElementById("vivo-bar");
  if(!el) return;
  const otros=VIVO.otros;
  el.className = "vivo-bar"+(hubo?" cambio":"");
  el.innerHTML = `
    <span><span class="vivo-dot"></span><b>En vivo</b></span>
    ${otros.length?`<span class="conectado-chip">👥 ${otros.length} más conectado(s): ${otros.map(o=>esc(o.usuario)).join(", ")}</span>`:'<span class="small muted">solo tú en esta vista</span>'}
    ${VIVO.ultimo?`<span class="small muted" style="margin-left:auto">Último cambio: ${esc(VIVO.ultimo.detalle||VIVO.ultimo.tipo)} · ${esc(VIVO.ultimo.hora)}</span>`:""}`;
}
async function tomarCaso(id){
  try{
    const r=await post("/vivo/caso",{institucion_id:ST.institucion_id,
      usuario:(ST.perfil.nombre||ST.perfil.titulo), caso_id:id, accion:"tomar"});
    toast(r.msg,!r.ok);
    return r.ok;
  }catch(e){ return true; }
}

/* ═══ FEED EN VIVO de la institución ═══ */
VISTAS.feed = async function(){
  loading();
  try{
    const d = await api(`/vivo/feed?institucion_id=${ST.institucion_id}&minutos=1440`);
    VIVO.version = d.version;
    main(head("Qué está pasando","Todo lo que ocurre en la institución, en orden y al instante")+`
      <div id="vivo-bar" class="vivo-bar"></div>
      <div class="card"><div class="card-head"><h3>📡 Últimas 24 horas</h3>
        <span class="small muted">${d.eventos.length} eventos · ${d.n_conectados} usuario(s) conectado(s)</span></div>
      <div style="max-height:560px;overflow-y:auto">
        ${d.eventos.map(e=>`
          <div class="log-row" style="align-items:flex-start">
            <span style="font-size:1.15rem">${e.icono}</span>
            <div style="flex:1">
              <b>${esc(e.titulo)}</b>
              <div class="small muted">${esc(e.detalle||"")}</div>
            </div>
            <span class="badge ${e.estado==='abierta'?'b-orange':e.estado==='info'?'b-blue':'b-green'}">${esc(e.estado)}</span>
            <span class="small muted" style="min-width:44px;text-align:right">${esc(e.hora)}</span>
          </div>`).join("")||'<div class="empty">Sin actividad reciente.</div>'}
      </div></div>
      <div class="legal-note">📡 Esta vista se actualiza sola. Cuando un docente marca una ausencia o rectoría manda un comunicado, aparece aquí sin recargar la página.</div>`);
    iniciarVivo("feed");
    pintarBarraVivo(false);
  }catch(e){ main(`<div class="empty">Error</div>`); }
};

/* ═══════════════════════════════════════════════════════════════════
   V7 · ALUMNO: mi salón, mi calendario, mis alertas (11, 12, 13)
   ═══════════════════════════════════════════════════════════════════ */
VISTAS.misalon = async function(){
  loading();
  try{
    const d = await api(`/alumno/mi_salon?estudiante_id=${ST.estudiante_id}`);
    if(!d.ok){ main(`<div class="empty">${esc(d.msg)}</div>`); return; }
    const DIAS=["Lunes","Martes","Miércoles","Jueves","Viernes"];
    main(head("Mi salón","Tu grupo, tus profesores y tu horario")+`
      <div class="al-hero">
        <div style="font-size:2.6rem">🏫</div>
        <div><h2>Salón ${esc(d.salon.nombre)}</h2>
          <div class="sub">Grado ${esc(d.salon.grado)} · Jornada ${esc(d.salon.jornada)} · ${d.salon.n_estudiantes} compañeros</div></div>
      </div>
      ${d.director?`<div class="card"><div class="card-head"><h3>👩‍🏫 Mi director(a) de grupo</h3></div>
      <div class="card-body"><div style="display:flex;gap:14px;align-items:center;flex-wrap:wrap">
        ${d.director.foto?`<img class="avatar-foto lg" src="${d.director.foto}">`:`<div class="avatar-sm" style="width:56px;height:56px;font-size:1.1rem">${ini(d.director.nombre)}</div>`}
        <div style="flex:1;min-width:190px">
          <b style="font-size:1.05rem">${esc(d.director.nombre)}</b>
          <div class="small muted">${esc(d.director.area||"Director de grupo")}</div>
          <div class="small muted">${d.director.email?"✉️ "+esc(d.director.email):""} ${d.director.telefono?" · 📱 "+esc(d.director.telefono):""}</div>
        </div>
        <button class="btn btn-sm btn-primary" onclick="toast('📱 En producción esto abre el chat con tu director(a).')">💬 Escribirle</button>
      </div></div></div>`:""}
      <div class="card"><div class="card-head"><h3>👨‍🏫 Mis profesores</h3></div><div class="card-body">
        ${d.docentes.map(x=>`<div class="flex-cell" style="padding:8px 0;border-bottom:1px solid #F1F5F9">
          ${x.foto?`<img class="avatar-foto" src="${x.foto}">`:`<div class="avatar-sm">${ini(x.nombre)}</div>`}
          <div style="flex:1"><b class="small">${esc(x.nombre)}</b>
            <div class="small muted">${MATERIA_ICO[x.materia]||"📚"} ${esc(x.materia)}</div></div>
          ${x.email?`<span class="small muted">${esc(x.email)}</span>`:""}
        </div>`).join("")||'<div class="small muted">Tu horario aún no tiene materias asignadas.</div>'}
      </div></div>
      <div class="card"><div class="card-head"><h3>🕐 Mi horario</h3></div><div class="card-body">
        <div class="horario-grid">
          ${DIAS.map(dia=>`<div class="horario-col"><h5>${dia}</h5>
            ${(d.horario[dia]||[]).map(h=>`<div class="horario-bloque">
              <b>${esc(h.hora||"")}</b><div>${MATERIA_ICO[h.materia]||"📚"} ${esc(h.materia||"")}</div></div>`).join("")
              ||'<div class="small muted" style="text-align:center">—</div>'}
          </div>`).join("")}
        </div>
      </div></div>
      <div class="card"><div class="card-head"><h3>👥 Mis compañeros (${d.companeros.length})</h3></div>
      <div class="card-body">${d.companeros.map(c=>`<span class="comp-chip ${c.yo?'yo':''}">${c.yo?"⭐":"👤"} ${esc(c.nombre)}${c.yo?" (yo)":""}</span>`).join("")}</div></div>`);
  }catch(e){ main(`<div class="empty">Error</div>`); }
};

VISTAS.alcalendario = async function(){
  loading();
  try{
    const d = await api(`/alumno/mi_calendario?estudiante_id=${ST.estudiante_id}`);
    const hoy=d.hoy;
    const porFecha={};
    d.eventos.forEach(e=>{ (porFecha[e.fecha]=porFecha[e.fecha]||[]).push(e); });
    const ICO={taller:"📝",evaluacion:"🧪",clase:"🧑‍🏫",corte:"📆",obligacion:"📌",reunion:"👥",recuperacion:"♻️",video:"🎬",lectura:"📖"};
    main(head("Mi calendario","Todo lo que tienes que entregar y las fechas importantes del colegio")+`
      ${d.vencidos.length?`<div class="digest" style="border-color:var(--red);background:#FEF2F2">
        <div style="font-size:1.9rem">🚨</div><div style="flex:1">
        <b>${d.vencidos.length} entrega(s) vencida(s)</b>
        ${d.vencidos.slice(0,3).map(v=>`<div class="small">• ${esc(v.titulo)} — venció el ${esc(v.fecha)}</div>`).join("")}
        <div class="small muted">Habla con tu docente: casi siempre hay forma de recuperar.</div></div></div>`:""}
      ${d.proximos.length?`<div class="card"><div class="card-head"><h3>⏰ Lo que viene</h3></div><div class="card-body">
        ${d.proximos.map(p=>{
          const dias=Math.round((new Date(p.fecha)-new Date(hoy))/86400000);
          return `<div class="al-pend ${dias<=1?'urg':''}">
            <div><b>${ICO[p.tipo]||"📌"} ${esc(p.titulo)}</b>
              <div class="small muted">${esc(p.materia||"")}${p.origen==="rectoria"?" · 🏫 de rectoría":p.origen==="institucion"?" · 📆 institucional":""}</div></div>
            <div style="display:flex;gap:8px;align-items:center">
              <span class="dias">${dias<0?"¡vencido!":dias===0?"¡HOY!":dias===1?"mañana":"en "+dias+" días"}</span>
              ${p.actividad_id?`<button class="btn btn-sm btn-primary" onclick="alVerActividad(${p.actividad_id})">Ver</button>`:""}
            </div></div>`;}).join("")}
      </div></div>`:'<div class="digest"><div style="font-size:1.9rem">🎉</div><div><b>Estás al día</b><div class="small muted">No tienes entregas próximas.</div></div></div>'}
      <div class="card"><div class="card-head"><h3>📅 Todo el mes</h3></div><div class="card-body">
        ${Object.keys(porFecha).sort().map(f=>`
          <div class="cal-day"><div class="cal-fecha ${f===hoy?'hoy':''}">
            <span>${f===hoy?"⭐ HOY — ":""}${fechaBonita(f)}</span></div>
            ${porFecha[f].map(e=>`<div class="cal-ev ${e.hecho?'donee':''}" style="border-left:3px solid ${e.vencido?'var(--red)':e.hecho?'var(--green)':'var(--teal)'}">
              <span>${ICO[e.tipo]||"📌"}</span>
              <span class="titulo" style="flex:1">${esc(e.titulo)}${e.materia?` <span class="small muted">${esc(e.materia)}</span>`:""}</span>
              ${e.nota!=null?`<span class="badge b-green">${e.nota}</span>`:e.hecho?'<span class="badge b-green">✓</span>':e.vencido?'<span class="badge b-red">vencido</span>':""}
            </div>`).join("")}
          </div>`).join("")||'<div class="empty">Sin fechas registradas.</div>'}
      </div></div>`);
  }catch(e){ main(`<div class="empty">Error</div>`); }
};

VISTAS.alalertas = async function(){
  loading();
  try{
    const [d, ra] = await Promise.all([
      api(`/alumno/mis_alertas?estudiante_id=${ST.estudiante_id}`),
      api(`/alumno/resumen_academico?estudiante_id=${ST.estudiante_id}`),
    ]);
    const COL={critico:"#FEE2E2|var(--red)",alto:"#FEF3C7|var(--orange)",medio:"#DBEAFE|var(--blue)",bajo:"#F1F5F9|var(--muted)"};
    main(head("Mis alertas","Lo que necesitas atender — y cómo vas en general")+`
      <div class="kpis">
        <div class="kpi ${d.n_criticas?'red':'green'}"><div class="kpi-ico">${d.n_criticas?"🚨":"✅"}</div>
          <div class="kpi-val">${d.n_total}</div><div class="kpi-lbl">Alertas activas</div></div>
        <div class="kpi"><div class="kpi-ico">📋</div><div class="kpi-val">${ra.asistencia.pct}%</div><div class="kpi-lbl">Mi asistencia</div></div>
        <div class="kpi ${ra.notas.materias_perdiendo.length?'orange':'green'}"><div class="kpi-ico">📗</div>
          <div class="kpi-val">${ra.notas.promedio!=null?ra.notas.promedio:"—"}</div><div class="kpi-lbl">Mi promedio</div></div>
        <div class="kpi"><div class="kpi-ico">📤</div><div class="kpi-val">${ra.entregas.pendientes}</div><div class="kpi-lbl">Por entregar</div></div>
      </div>
      ${d.alertas.map(a=>{const[bg,fg]=(COL[a.nivel]||COL.bajo).split("|");
        return `<div class="card" style="border-left:4px solid ${fg};background:${bg}"><div class="card-body">
          <div style="display:flex;gap:12px;align-items:flex-start;flex-wrap:wrap">
            <span style="font-size:1.6rem">${a.icono}</span>
            <div style="flex:1;min-width:190px"><b>${esc(a.titulo)}</b>
              <div class="small" style="margin-top:3px">${esc(a.detalle)}</div></div>
            ${a.accion==="abrir_actividad"?`<button class="btn btn-sm btn-primary" onclick="alVerActividad(${a.id})">Ir a resolverlo</button>`:
              a.accion==="ver_notas"?`<button class="btn btn-sm" onclick="irVista('alnotas')">Ver mis notas</button>`:
              a.accion==="ver_observador"?`<button class="btn btn-sm" onclick="verMiObservador()">Ver anotaciones</button>`:""}
          </div></div></div>`;}).join("")||`
        <div class="digest"><div style="font-size:2rem">🎉</div><div><b>¡Todo en orden!</b>
          <div class="small muted">No tienes alertas. Sigue así.</div></div></div>`}
      <div class="card"><div class="card-head"><h3>📊 Cómo voy</h3>
        <span class="small muted">esto mismo lo ve tu acudiente</span></div>
      <div class="card-body">
        <div class="info-grid">
          <div class="info-it"><span class="k">Asistencia</span><b>${ra.asistencia.pct}% · ${ra.asistencia.faltas} faltas</b></div>
          <div class="info-it"><span class="k">Promedio general</span><b>${ra.notas.promedio!=null?ra.notas.promedio:"—"}</b></div>
          <div class="info-it"><span class="k">Materias</span><b>${ra.notas.n_materias}${ra.notas.materias_perdiendo.length?` (${ra.notas.materias_perdiendo.length} en riesgo)`:""}</b></div>
          <div class="info-it"><span class="k">Entregas</span><b>${ra.entregas.entregadas}/${ra.entregas.total}</b></div>
          <div class="info-it"><span class="k">Temas de clase vistos</span><b>${ra.temas_vistos}</b></div>
          ${ra.riesgo?`<div class="info-it"><span class="k">Nivel de acompañamiento</span><b>${esc(ra.riesgo.nivel)}</b></div>`:""}
        </div>
        ${ra.notas.materias_perdiendo.length?`<div class="legal-note" style="background:#FEF3C7;border-color:var(--gold)">
          📉 Vas bajo en: <b>${ra.notas.materias_perdiendo.map(m=>esc(m)).join(", ")}</b>. Todavía puedes recuperar — pide ayuda a tu docente.</div>`:""}
      </div></div>`);
  }catch(e){ main(`<div class="empty">Error</div>`); }
};
async function verMiObservador(){
  try{
    const d=await api(`/alumno/mi_observador?estudiante_id=${ST.estudiante_id}`);
    document.getElementById("modal-srd-title").textContent="📔 Mi observador";
    document.getElementById("modal-srd-body").innerHTML=`
      <div class="legal-note">Estas son las anotaciones de tu observador. Las que no están firmadas debes firmarlas con tu acudiente.</div>
      ${d.map(o=>`<div class="obs-item ${o.tipo==='felicitacion'?'obs-compromiso':o.tipo==='comportamiento'?'obs-riesgo':''}">
        <div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap">
          <b class="small">${o.tipo==="felicitacion"?"🌟":o.tipo==="comportamiento"?"⚠️":"📘"} ${esc(o.tipo)}</b>
          <span class="small muted">${esc(o.fecha)}</span></div>
        <div class="small" style="margin:5px 0">${esc(o.descripcion)}</div>
        <div class="small muted">Registró: ${esc(o.registrado_por||"—")} ·
          ${o.firmado?`<span style="color:var(--green)">✍️ Firmado (${esc(o.metodo||"")})</span>`:'<span style="color:var(--orange)">⏳ Sin firmar</span>'}</div>
      </div>`).join("")||'<div class="empty">No tienes anotaciones. 🎉</div>'}`;
    abrirModal("modal-srd");
  }catch(e){ toast("Error",true); }
}

/* ═══════════════════════════════════════════════════════════════════
   V7 · CONTRATACIÓN: SECOP, pipeline detallado, crear contrato
   ═══════════════════════════════════════════════════════════════════ */

async function secopView(){
  const d = await api(`/contratos/secop?institucion_id=${ST.institucion_id}`);
  window._secop=d;
  document.getElementById("con-cont").innerHTML = `
    <div class="legal-note">📤 <b>Publicación en SECOP.</b> El sistema valida primero que el expediente esté completo y vigente, y que existan CDP y RP. Si algo falta, no deja publicar — porque un proceso mal publicado es un hallazgo seguro.</div>
    ${d.contratos.map(c=>`
      <div class="card"><div class="card-body">
        <div style="display:flex;gap:12px;align-items:flex-start;flex-wrap:wrap">
          <div style="flex:1;min-width:220px">
            <b>${esc(c.numero)}</b> · ${esc(c.objeto)}
            <div class="small muted">${esc(c.contratista)} · ${money(c.valor)} · estado: ${esc(c.estado)}</div>
            ${c.publicaciones.length?`<div style="margin-top:7px">
              ${c.publicaciones.map(p=>`<a class="mat-chip" href="${esc(p.url||"#")}" target="_blank">
                ${p.plataforma==="secop1"?"📋 SECOP I":"🌐 SECOP II"} · ${esc(p.numero_proceso)} <span style="opacity:.7">${esc(p.fecha||"")}</span></a>`).join("")}
            </div>`:'<div class="small muted" style="margin-top:5px">Sin publicar</div>'}
            ${!c.docs_completos?`<div class="small" style="color:var(--red);margin-top:5px">⛔ Faltan: ${c.faltantes.map(f=>esc(f)).join(", ")}</div>`:""}
          </div>
          <div style="display:flex;flex-direction:column;gap:5px">
            ${c.publicable?`
              <button class="btn btn-sm btn-primary" onclick="publicarSECOP(${c.id},'secop2')">🌐 Publicar SECOP II</button>
              <button class="btn btn-sm" onclick="publicarSECOP(${c.id},'secop1')">📋 SECOP I</button>
              <button class="btn btn-sm btn-gold" onclick="publicarSECOP(${c.id},'ambos')">📤 Ambos</button>`
              :`<span class="badge b-gray">No publicable aún</span>
                <button class="btn btn-xs" onclick="verPipelineDetalle(${c.id})">¿Qué falta?</button>`}
          </div>
        </div></div></div>`).join("")}`;
}
async function publicarSECOP(id, plataforma){
  const mod=prompt("Modalidad de contratación:\n\n1 = Régimen especial FSE (Decreto 4791/2008)\n2 = Mínima cuantía\n3 = Contratación directa\n\nEscribe el número:","1");
  if(mod===null) return;
  const MODS={"1":"regimen_especial","2":"minima_cuantia","3":"contratacion_directa"};
  try{
    const r=await post("/contratos/secop/publicar",{contrato_id:id,plataforma,modalidad:MODS[mod]||"regimen_especial"});
    toast(r.msg,!r.ok);
    if(r.ok) secopView();
  }catch(e){ toast("Error",true); }
}

async function verPipelineDetalle(id){
  try{
    const d = await api(`/contratos/pipeline_detalle?contrato_id=${id}`);
    if(!d.ok){ toast(d.msg,true); return; }
    window._pipeDet=d;
    document.getElementById("modal-srd-title").textContent=`📜 ${d.contrato} · paso a paso`;
    document.getElementById("modal-srd-body").innerHTML=`
      <div class="legal-note" style="background:${d.puede_avanzar?'#DCFCE7':d.bloqueos_criticos.length?'#FEE2E2':'#FEF3C7'};border-color:${d.puede_avanzar?'var(--green)':d.bloqueos_criticos.length?'var(--red)':'var(--gold)'}">
        <b>${d.puede_avanzar?"✅ Listo para avanzar":d.bloqueos_criticos.length?"⛔ Bloqueado":"⚠️ Con pendientes"}</b>
        ${d.bloqueos.length?`<div class="small" style="margin-top:4px">Falta: ${d.bloqueos.map(b=>esc(b)).join(" · ")}</div>`:""}
        ${d.documentos_vencidos.length?`<div class="small" style="margin-top:4px;color:var(--red)"><b>Documentos vencidos:</b> ${d.documentos_vencidos.map(x=>esc(x)).join(", ")}</div>`:""}
      </div>
      ${d.etapas.map(e=>`
        <div class="etapa-det ${e.estado}">
          <div class="etapa-det-head" onclick="this.parentElement.classList.toggle('abierto');this.nextElementSibling.style.display=this.nextElementSibling.style.display==='none'?'block':'none'">
            <span style="font-size:1.15rem">${e.estado==="completada"?"✅":e.estado==="actual"?"▶️":"⚪"}</span>
            <div style="flex:1"><b>${e.orden}. ${esc(e.etapa)}</b>
              <div class="small muted">${e.n_cumplidos}/${e.n_total} requisitos${e.fecha?" · "+esc(e.fecha):""}</div></div>
            ${e.pendientes.length&&e.estado!=="pendiente"?`<span class="badge b-orange">${e.pendientes.length} pendiente(s)</span>`:""}
          </div>
          <div style="display:${e.estado==='actual'?'block':'none'}">
            ${e.requisitos.map(r=>`<div class="req-fila">
              <span>${r.cumple?"✅":"⬜"}</span>
              <span style="${r.cumple?'':'color:var(--red)'}">${esc(r.label)}</span></div>`).join("")}
          </div>
        </div>`).join("")}
      <div style="margin-top:14px;display:flex;gap:8px;justify-content:flex-end;flex-wrap:wrap">
        <button class="btn" onclick="cerrarModal('modal-srd')">Cerrar</button>
        ${d.bloqueos_criticos.length?`<button class="btn btn-danger" disabled title="No se puede saltar">⛔ No se puede avanzar</button>`:
          d.puede_avanzar?`<button class="btn btn-primary" onclick="avanzarValidado(${id},false)">▶️ Avanzar de etapa</button>`:
          `<button class="btn btn-gold" onclick="avanzarValidado(${id},true)">⚠️ Avanzar bajo mi responsabilidad</button>`}
      </div>`;
    abrirModal("modal-srd");
  }catch(e){ toast("Error",true); }
}
async function avanzarValidado(id, forzar){
  let just="";
  if(forzar){
    just=prompt("Vas a avanzar con requisitos pendientes.\n\nEscribe la justificación (queda registrada en el contrato y en la auditoría):");
    if(just===null) return;
    if(!just.trim()){ toast("La justificación es obligatoria para avanzar con pendientes",true); return; }
  }
  try{
    const r=await post("/contratos/avanzar_validado",{id,acepto_riesgo:forzar,justificacion:just});
    if(!r.ok && r.requiere_autorizacion){ toast(r.msg,true); return; }
    toast(r.msg,!r.ok);
    if(r.ok){ cerrarModal("modal-srd"); VISTAS.contratos(ST._conTab||"pipeline"); }
  }catch(e){ toast("Error",true); }
}

/* ── Crear contrato completo (puntos 35, 37) ── */
let NC=null;
async function abrirCrearContrato(){
  loading();
  try{
    const [pl, prov] = await Promise.all([
      api(`/contratos/plantillas`),
      api(`/contratos/contratistas`),
    ]);
    window._plantillas=pl; window._provs=prov;
    NC={paso:1, tipo_contrato:"suministro", objeto:"", valor:0, contratista_id:null,
        plazo_dias:30, items:[], obligaciones:[], cotizaciones:[], supervisor:"",
        modalidad:"regimen_especial", fecha_inicio:hoyISO()};
    pintarCrearContrato();
  }catch(e){ toast("Error",true); }
}
function pintarCrearContrato(){
  const pl=window._plantillas, prov=window._provs;
  const P=pl.plantillas.find(x=>x.id===NC.tipo_contrato)||pl.plantillas[0];
  const totalItems=NC.items.reduce((a,i)=>a+i.cantidad*i.valor_unitario,0);
  main(`<div style="display:flex;gap:10px;align-items:center;margin-bottom:14px;flex-wrap:wrap">
      <button class="btn btn-sm" onclick="VISTAS.contratos('pipeline')">← Contratación</button>
      <h2 style="margin:0;font-size:1.2rem">📄 Crear contrato</h2></div>
    <div class="paso-ind">
      ${["1 · Tipo y objeto","2 · Ítems y valor","3 · Contratista","4 · Revisar"].map((p,i)=>
        `<div class="${NC.paso===i+1?'on':NC.paso>i+1?'done':''}" onclick="NC.paso=${i+1};pintarCrearContrato()">${p}</div>`).join("")}
    </div>
    <div id="nc-body"></div>`);
  const b=document.getElementById("nc-body");
  if(NC.paso===1){
    b.innerHTML=`<div class="card"><div class="card-body">
      <div class="fsec">¿Qué tipo de contrato es?</div>
      <div class="wiz-modos" style="grid-template-columns:repeat(auto-fit,minmax(210px,1fr))">
        ${pl.plantillas.map(t=>`<div class="wiz-modo ${NC.tipo_contrato===t.id?'sel':''}" onclick="NC.tipo_contrato='${t.id}';NC.plazo_dias=${t.plazo_sugerido};pintarCrearContrato()">
          <div class="ic">${t.label.split(" ")[0]}</div><b>${esc(t.label.substring(2))}</b>
          <div class="small">Plazo sugerido: ${t.plazo_sugerido} días${t.requiere_poliza?" · requiere póliza":""}</div></div>`).join("")}
      </div>
      <div class="fsec">Objeto del contrato</div>
      <div class="small muted" style="margin-bottom:6px">Debe describir con precisión qué se contrata. Es lo primero que mira una auditoría.</div>
      <textarea id="nc_objeto" rows="3" oninput="NC.objeto=this.value" placeholder="${esc(P.objeto_ejemplo)}">${esc(NC.objeto)}</textarea>
      <button class="btn btn-xs" style="margin-top:6px" onclick="NC.objeto='${esc(P.objeto_ejemplo)}';pintarCrearContrato()">📋 Usar ejemplo</button>
      <div class="fsec">Obligaciones del contratista</div>
      ${(NC.obligaciones.length?NC.obligaciones:P.obligaciones).map((o,i)=>`
        <div style="display:flex;gap:6px;margin-bottom:5px">
          <input value="${esc(o)}" style="flex:1" oninput="NC.obligaciones[${i}]=this.value">
          <button class="btn btn-xs btn-danger" onclick="NC.obligaciones.splice(${i},1);pintarCrearContrato()">✕</button></div>`).join("")}
      <button class="btn btn-xs" onclick="if(!NC.obligaciones.length)NC.obligaciones=${JSON.stringify(P.obligaciones)};NC.obligaciones.push('');pintarCrearContrato()">➕ Agregar obligación</button>
      <div class="frow-3" style="margin-top:14px">
        <div><label>Plazo (días)</label><input type="number" value="${NC.plazo_dias}" oninput="NC.plazo_dias=parseInt(this.value)||30"></div>
        <div><label>Fecha de inicio</label><input type="date" value="${NC.fecha_inicio}" oninput="NC.fecha_inicio=this.value"></div>
        <div><label>Supervisor</label><input value="${esc(NC.supervisor)}" placeholder="Quién vigila el contrato" oninput="NC.supervisor=this.value"></div>
      </div>
      <div style="text-align:right;margin-top:14px"><button class="btn btn-primary" onclick="if(!NC.objeto.trim()){toast('Escribe el objeto',true);return}NC.paso=2;pintarCrearContrato()">Siguiente →</button></div>
    </div></div>`;
  }
  if(NC.paso===2){
    b.innerHTML=`<div class="card"><div class="card-body">
      <div class="legal-note">🧾 Detalla qué se compra exactamente. La suma de los ítems debe coincidir con el valor del contrato — si no cuadra, el sistema no deja seguir.</div>
      ${NC.items.map((it,i)=>`<div class="mat-fila">
        <input value="${esc(it.descripcion)}" style="flex:2;min-width:130px" oninput="NC.items[${i}].descripcion=this.value" placeholder="Descripción">
        <input type="number" value="${it.cantidad}" style="width:70px" oninput="NC.items[${i}].cantidad=parseInt(this.value)||1;pintarCrearContrato()" placeholder="Cant">
        <input type="number" value="${it.valor_unitario}" style="width:110px" oninput="NC.items[${i}].valor_unitario=parseFloat(this.value)||0;pintarCrearContrato()" placeholder="Valor unit.">
        <b class="small">${money(it.cantidad*it.valor_unitario)}</b>
        <button class="btn btn-xs btn-danger" onclick="NC.items.splice(${i},1);pintarCrearContrato()">✕</button></div>`).join("")}
      <button class="btn btn-sm" onclick="NC.items.push({descripcion:'',cantidad:1,valor_unitario:0});pintarCrearContrato()">➕ Agregar ítem</button>
      <div class="frow" style="margin-top:14px"><label>Valor total del contrato (COP) *</label>
        <div style="display:flex;gap:8px">
          <input type="number" id="nc_valor" value="${NC.valor||totalItems}" style="flex:1" oninput="NC.valor=parseFloat(this.value)||0">
          ${totalItems?`<button class="btn btn-sm" onclick="NC.valor=${totalItems};pintarCrearContrato()">= ítems (${money(totalItems)})</button>`:""}
        </div>
        <div class="small muted" style="margin-top:5px">Tope legal del FSE: <b>${money(pl.tope_cop)}</b> (${pl.tope_smmlv} SMMLV)</div>
        ${(NC.valor||totalItems)>pl.tope_cop?`<div class="small" style="color:var(--red);margin-top:4px">⚖️ Supera el tope del régimen especial.</div>`:""}
      </div>
      <div class="fsec">💬 Cotizaciones (mínimo 2 recomendadas)</div>
      ${NC.cotizaciones.map((q,i)=>`<div class="mat-fila">
        <input value="${esc(q.proveedor)}" style="flex:2" placeholder="Proveedor" oninput="NC.cotizaciones[${i}].proveedor=this.value">
        <input type="number" value="${q.valor}" style="width:120px" placeholder="Valor" oninput="NC.cotizaciones[${i}].valor=parseFloat(this.value)||0">
        <button class="btn btn-xs btn-danger" onclick="NC.cotizaciones.splice(${i},1);pintarCrearContrato()">✕</button></div>`).join("")}
      <button class="btn btn-sm" onclick="NC.cotizaciones.push({proveedor:'',valor:0});pintarCrearContrato()">➕ Agregar cotización</button>
      <div style="display:flex;justify-content:space-between;margin-top:16px">
        <button class="btn" onclick="NC.paso=1;pintarCrearContrato()">← Atrás</button>
        <button class="btn btn-primary" onclick="NC.paso=3;pintarCrearContrato()">Siguiente →</button></div>
    </div></div>`;
  }
  if(NC.paso===3){
    b.innerHTML=`<div class="card"><div class="card-body">
      <div class="fsec">¿Quién va a ejecutar el contrato?</div>
      ${prov.map(p=>`<div class="wiz-modo ${NC.contratista_id===p.id?'sel':''}" style="text-align:left;margin-bottom:8px" onclick="NC.contratista_id=${p.id};pintarCrearContrato()">
        <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
          <div style="flex:1;min-width:180px"><b>${esc(p.nombre)}</b>
            <div class="small muted">NIT ${esc(p.nit||"—")} · confianza ${p.confianza}%</div></div>
          ${p.docs_completos?'<span class="badge b-green">✓ Expediente completo</span>':`<span class="badge b-red">Faltan ${p.documentos.filter(d=>!d.ok).length} doc(s)</span>`}
        </div></div>`).join("")}
      <div class="legal-note">💡 Puedes crear el contrato sin contratista y asignarlo después, pero no podrás avanzar de etapa hasta que el expediente esté completo.</div>
      <div style="display:flex;justify-content:space-between;margin-top:14px">
        <button class="btn" onclick="NC.paso=2;pintarCrearContrato()">← Atrás</button>
        <button class="btn btn-primary" onclick="NC.paso=4;pintarCrearContrato()">Revisar →</button></div>
    </div></div>`;
  }
  if(NC.paso===4){
    const p=prov.find(x=>x.id===NC.contratista_id);
    const cot=NC.cotizaciones.filter(q=>q.proveedor);
    b.innerHTML=`<div class="card"><div class="card-body">
      <div class="fsec">📄 Así queda el contrato</div>
      <div class="info-grid">
        <div class="info-it"><span class="k">Tipo</span><b>${esc(P.label)}</b></div>
        <div class="info-it"><span class="k">Valor</span><b>${money(NC.valor)}</b></div>
        <div class="info-it"><span class="k">Plazo</span><b>${NC.plazo_dias} días</b></div>
        <div class="info-it"><span class="k">Contratista</span><b>${p?esc(p.nombre):"Por asignar"}</b></div>
        <div class="info-it"><span class="k">Supervisor</span><b>${esc(NC.supervisor||"Por designar")}</b></div>
        <div class="info-it"><span class="k">Cotizaciones</span><b>${cot.length}</b></div>
      </div>
      <div class="fsec">Objeto</div>
      <p style="line-height:1.65">${esc(NC.objeto)}</p>
      ${NC.items.length?`<div class="fsec">Ítems</div>
        <div class="tbl-scroll"><table><thead><tr><th>Descripción</th><th style="text-align:center">Cant</th><th style="text-align:right">Unitario</th><th style="text-align:right">Total</th></tr></thead>
        <tbody>${NC.items.map(i=>`<tr><td>${esc(i.descripcion)}</td><td style="text-align:center">${i.cantidad}</td>
          <td style="text-align:right">${money(i.valor_unitario)}</td><td style="text-align:right"><b>${money(i.cantidad*i.valor_unitario)}</b></td></tr>`).join("")}
        <tr style="background:#F8FAFC"><td colspan="3"><b>Total</b></td><td style="text-align:right"><b>${money(totalItems)}</b></td></tr>
        </tbody></table></div>`:""}
      ${NC.obligaciones.filter(o=>o).length?`<div class="fsec">Obligaciones</div>
        <ul style="line-height:1.7">${NC.obligaciones.filter(o=>o).map(o=>`<li>${esc(o)}</li>`).join("")}</ul>`:""}
      <div class="legal-note">📌 Al crear, el sistema expide el <b>CDP automáticamente</b> y el contrato entra en estado borrador. El RP se expide cuando jurídica dé el visto bueno.</div>
      <div style="display:flex;justify-content:space-between;margin-top:14px">
        <button class="btn" onclick="NC.paso=3;pintarCrearContrato()">← Atrás</button>
        <button class="btn btn-primary btn-lg" onclick="guardarContratoCompleto()">📄 Crear contrato + CDP</button></div>
    </div></div>`;
  }
}
async function guardarContratoCompleto(){
  const body={institucion_id:ST.institucion_id, contratista_id:NC.contratista_id,
    tipo_contrato:NC.tipo_contrato, objeto:NC.objeto, valor:NC.valor,
    plazo_dias:NC.plazo_dias, items:NC.items.filter(i=>i.descripcion),
    obligaciones:NC.obligaciones.filter(o=>o), supervisor:NC.supervisor,
    cotizaciones:NC.cotizaciones.filter(q=>q.proveedor), modalidad:NC.modalidad,
    fecha_inicio:NC.fecha_inicio};
  try{
    const r=await post("/contratos/crear_completo",body);
    if(!r.ok){ toast(r.msg,true); return; }
    toast(r.msg);
    setTimeout(()=>VISTAS.contratos("pipeline"),900);
  }catch(e){ toast("Error",true); }
}

/* ═══════════════════════════════════════════════════════════════════
   V7 · DATOS & IA: el cerebro (punto 32)
   ═══════════════════════════════════════════════════════════════════ */
async function cerebroView(){
  const d = await api(`/metadatos/cerebro?institucion_id=${ST.institucion_id}`);
  document.getElementById("datos-cont").innerHTML = `
    <div class="card"><div class="card-head"><h3>🧠 Qué motor está usando</h3>
      <span class="badge ${d.motor==='lightgbm'?'b-green':'b-orange'}">${esc(d.motor_label)}</span></div>
    <div class="card-body">
      <div class="kpis">
        <div class="kpi"><div class="kpi-ico">👥</div><div class="kpi-val">${d.poblacion.evaluados}</div><div class="kpi-lbl">Estudiantes evaluados</div></div>
        <div class="kpi red"><div class="kpi-ico">🔴</div><div class="kpi-val">${d.poblacion.criticos}</div><div class="kpi-lbl">Críticos</div></div>
        <div class="kpi orange"><div class="kpi-ico">🟡</div><div class="kpi-val">${d.poblacion.moderados}</div><div class="kpi-lbl">Moderados</div></div>
        <div class="kpi green"><div class="kpi-ico">🟢</div><div class="kpi-val">${d.poblacion.estables}</div><div class="kpi-lbl">Estables</div></div>
      </div>
    </div></div>
    <div class="card"><div class="card-head"><h3>⚖️ En qué se fija el modelo</h3>
      <span class="small muted">peso de cada señal en la decisión</span></div>
    <div class="card-body">
      ${d.variables.map(v=>`
        <div class="var-fila">
          <div style="width:190px;min-width:130px"><b class="small">${esc(v.variable.replace(/_/g," "))}</b></div>
          <div class="var-barra"><i style="width:${Math.min(100,v.peso)}%"></i><span>${v.peso}%</span></div>
        </div>
        <div class="small muted" style="padding:0 0 8px 4px">${esc(v.explica)}</div>`).join("")}
      <div class="legal-note">💡 Así se lee: la <b>asistencia del último mes</b> es lo que más pesa. No es casualidad — el estudiante que empieza a faltar seguido es el que termina retirándose. Por eso el sistema avisa apenas eso empieza a pasar, no cuando ya se fue.</div>
    </div></div>
    <div class="card"><div class="card-head"><h3>👁️ Qué ve el modelo en cada grupo</h3></div><div class="card-body">
      ${d.perfiles.map(p=>`
        <div class="perfil-ia" style="background:linear-gradient(135deg,${p.color},${p.color}DD)">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
            <b style="font-size:1.05rem">${esc(p.nivel)} · ${p.n} estudiantes</b>
            <span class="small" style="opacity:.9">asistencia promedio ${p.asistencia!=null?p.asistencia+"%":"—"} · ${p.faltas!=null?p.faltas+" faltas":""}</span>
          </div>
          <div class="small" style="opacity:.95;margin-top:5px">${esc(p.lectura)}</div>
        </div>`).join("")}
    </div></div>
    <div class="card"><div class="card-head"><h3>📖 Cómo funciona, en palabras simples</h3></div><div class="card-body">
      ${d.como_funciona.map((x,i)=>`<div class="paso-dns"><div class="num">${i+1}</div><div>${esc(x)}</div></div>`).join("")}
      <div class="small muted" style="margin-top:10px">Próximo reentrenamiento: <b>${esc(d.proximo_reentreno)}</b></div>
    </div></div>`;
}

async function datasetsView(){
  const [d, ex] = await Promise.all([
    api(`/metadatos/datasets?institucion_id=${ST.institucion_id}`),
    api(`/metadatos/exportaciones?institucion_id=${ST.institucion_id}`),
  ]);
  window._datasets=d.datasets;
  document.getElementById("datos-cont").innerHTML = `
    <div class="legal-note">📦 <b>Datos vivos y limpios.</b> El sistema exporta cada conjunto listo para usar: para publicar en datos.gov.co, para entregarle al MinTIC, para el portal de la institución, o para reentrenar modelos en Colab. Siempre <b>anonimizado</b>: nunca sale el nombre ni el documento de nadie.</div>
    <div class="grid-cards">
      ${d.datasets.map(x=>`
        <div class="va-card" style="cursor:default">
          <div class="va-top"><span class="va-tipo">📊 ${x.n_registros.toLocaleString("es-CO")} registros</span>
            <span class="small muted">${esc(x.formato_sugerido)}</span></div>
          <h4>${esc(x.nombre)}</h4>
          <div class="small muted" style="min-height:38px">${esc(x.descripcion)}</div>
          <div class="small" style="margin:7px 0;color:var(--teal)">🎯 ${esc(x.uso)}</div>
          <div>${x.campos.map(c=>`<span class="doc-chip ok" style="font-size:.66rem">${esc(c)}</span>`).join("")}</div>
          <div style="margin-top:10px;display:flex;gap:5px;flex-wrap:wrap">
            <button class="btn btn-xs btn-primary" onclick="abrirExportar('${x.id}','${esc(x.nombre)}')">📤 Exportar</button>
            <button class="btn btn-xs" onclick="verMuestra('${x.id}')">👁️ Ver muestra</button>
          </div>
        </div>`).join("")}
    </div>
    <div class="card"><div class="card-head"><h3>📋 Exportaciones realizadas</h3>
      <span class="small muted">${ex.programadas} con sincronización automática</span></div>
    <div class="tbl-scroll"><table>
      <thead><tr><th>Dataset</th><th>Destino</th><th>Formato</th><th style="text-align:center">Registros</th><th>Frecuencia</th><th>Fecha</th></tr></thead>
      <tbody>${ex.exportaciones.map(e=>`<tr>
        <td><b>${esc(e.dataset)}</b>${e.anonimizado?' <span class="badge b-green" style="font-size:.62rem">anónimo</span>':""}</td>
        <td class="small">${esc(e.destino_label)}</td>
        <td class="small">${esc(e.formato)}</td>
        <td style="text-align:center">${e.n_registros}</td>
        <td class="small">${e.frecuencia==="manual"?"—":esc(e.frecuencia)}${e.proxima_sync?`<div class="muted">próx: ${esc(e.proxima_sync.slice(0,10))}</div>`:""}</td>
        <td class="small">${esc(e.fecha)}</td></tr>`).join("")||'<tr><td colspan="6" class="empty">Sin exportaciones todavía.</td></tr>'}
    </tbody></table></div></div>`;
}
function abrirExportar(id, nombre){
  document.getElementById("modal-srd-title").textContent="📤 Exportar "+nombre;
  document.getElementById("modal-srd-body").innerHTML=`
    <input type="hidden" id="ex_ds" value="${id}">
    <div class="fsec">¿Para dónde va?</div>
    ${[["datos_gov","🏛️ datos.gov.co","Portal de datos abiertos del Estado. Cumple el estándar y suma en los indicadores de transparencia."],
       ["mintic","📡 MinTIC / MEN","Reporte a las entidades nacionales."],
       ["entrenamiento","🧠 Entrenamiento de modelos","Formato listo para Colab: LSTM, LightGBM o Transformers."],
       ["portal_institucion","🏫 Portal de la institución","Para publicar en la web del colegio."]].map(([v,l,d])=>`
      <label class="wiz-modo" style="text-align:left;display:block;margin-bottom:7px" onclick="document.querySelectorAll('#modal-srd-body .wiz-modo').forEach(e=>e.classList.remove('sel'));this.classList.add('sel');window._exDest='${v}'">
        <b>${l}</b><div class="small">${d}</div></label>`).join("")}
    <div class="frow-3" style="margin-top:12px">
      <div><label>Formato</label><select id="ex_fmt">
        <option value="json">JSON</option><option value="csv">CSV</option>
        <option value="jsonl">JSONL (entrenamiento)</option></select></div>
      <div><label>Sincronizar</label><select id="ex_freq">
        <option value="manual">Solo esta vez</option><option value="diaria">Cada día</option>
        <option value="semanal">Cada semana</option><option value="mensual">Cada mes</option></select></div>
      <div><label>Anonimizar</label><select id="ex_anon"><option value="1">Sí (recomendado)</option><option value="0">No</option></select></div>
    </div>
    <div class="legal-note">🔒 Con anonimización activada, cada estudiante sale como <code>EST-00123</code>. Los datos sirven igual para analizar y no exponen a nadie.</div>
    <div class="modal-foot" style="border:none;padding:14px 0 0">
      <button class="btn" onclick="cerrarModal('modal-srd')">Cancelar</button>
      <button class="btn btn-primary" onclick="ejecutarExportar()">📤 Exportar</button></div>`;
  window._exDest="datos_gov";
  abrirModal("modal-srd");
}
async function ejecutarExportar(){
  try{
    const r=await post("/metadatos/exportar",{institucion_id:ST.institucion_id,
      dataset:document.getElementById("ex_ds").value, destino:window._exDest||"datos_gov",
      formato:document.getElementById("ex_fmt").value,
      frecuencia:document.getElementById("ex_freq").value,
      anonimizado:document.getElementById("ex_anon").value==="1"});
    toast(r.msg,!r.ok);
    if(r.ok){ cerrarModal("modal-srd"); datasetsView(); }
  }catch(e){ toast("Error",true); }
}
async function verMuestra(id){
  try{
    const d=await api(`/metadatos/muestra?dataset=${id}&n=5`);
    document.getElementById("modal-srd-title").textContent="👁️ Muestra de "+id;
    document.getElementById("modal-srd-body").innerHTML=`
      <div class="legal-note">${esc(d.nota)}</div>
      <pre style="background:#0F172A;color:#E2E8F0;padding:16px;border-radius:10px;overflow-x:auto;font-size:.8rem;line-height:1.6">${esc(JSON.stringify(d.muestra,null,2))}</pre>`;
    abrirModal("modal-srd");
  }catch(e){ toast("Error",true); }
}

/* ═══════════════════════════════════════════════════════════════════
   V8 · MI PERFIL para todos los roles (punto 16)
   ═══════════════════════════════════════════════════════════════════ */
VISTAS.miperfil = async function(){
  loading();
  try{
    const q = ST.perfil.personal_id ? `personal_id=${ST.perfil.personal_id}`
            : ST.estudiante_id ? `estudiante_id=${ST.estudiante_id}` : "";
    if(!q){ main('<div class="empty">Este perfil no tiene datos editables.</div>'); return; }
    const d = await api(`/usuarios/mi_perfil?${q}`);
    if(!d.ok){ main(`<div class="empty">${esc(d.msg||"No se pudo cargar")}</div>`); return; }
    window._miPerfil=d; window._miFoto=d.foto;
    const esDocente = d.rol==="docente";
    main(head("Mi perfil","Tus datos personales — puedes editarlos cuando quieras")+`
      <div class="card"><div class="card-body">
        <div style="display:flex;gap:18px;align-items:center;flex-wrap:wrap;margin-bottom:14px">
          <div style="position:relative">
            <div id="mp_foto" style="width:84px;height:84px;border-radius:50%;background:#F1F5F9;display:flex;align-items:center;justify-content:center;font-size:1.7rem;overflow:hidden;border:3px solid var(--border)">
              ${d.foto?`<img src="${d.foto}" style="width:100%;height:100%;object-fit:cover">`:ini(d.nombre)}</div>
            <button class="btn btn-xs" style="position:absolute;bottom:0;right:-4px" onclick="document.getElementById('mp_file').click()">📷</button>
            <input type="file" id="mp_file" accept="image/*" style="display:none" onchange="miFotoSel(this)">
          </div>
          <div style="flex:1;min-width:200px">
            <b style="font-size:1.15rem">${esc(d.nombre)}</b>
            <div class="small muted">${d.rol_icono} ${esc(d.rol_label)}${d.area?" · "+esc(d.area):""}${d.sede?" · "+esc(d.sede):""}</div>
            <div class="small muted">${d.usuario?"@"+esc(d.usuario):""}${d.ultimo_acceso?" · último ingreso "+esc(d.ultimo_acceso):""}</div>
          </div>
          <span class="usr-chip st-${d.estado}">${esc(d.estado)}</span>
        </div>
        <div class="fsec">👤 Datos personales</div>
        <div class="frow"><label>Nombre completo</label><input id="mp_nombre" value="${esc(d.nombre||"")}"></div>
        <div class="frow-2">
          <div><label>Teléfono / WhatsApp</label><input id="mp_tel" value="${esc(d.telefono||"")}"></div>
          <div><label>Correo</label><input id="mp_email" value="${esc(d.email||"")}"></div>
        </div>
        <div class="frow-2">
          <div><label>Dirección</label><input id="mp_dir" value="${esc(d.direccion||"")}"></div>
          <div><label>Barrio / vereda</label><input id="mp_barrio" value="${esc(d.barrio_vereda||"")}"></div>
        </div>
        ${d.personal_id?`<div class="frow"><label>Profesión / título</label><input id="mp_prof" value="${esc(d.profesion||"")}"></div>`:""}
        <div style="text-align:right;margin-top:12px"><button class="btn btn-primary" onclick="guardarMiPerfil()">💾 Guardar mis datos</button></div>
        <div class="fsec">🔔 Notificaciones</div>
        <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
          <button class="btn btn-sm btn-primary" onclick="activarPush()">🔔 Activar notificaciones</button>
          <span class="small muted" style="flex:1;min-width:180px">Te avisamos de tus pendientes aunque tengas la app cerrada. Funciona en celular y computador.</span>
        </div>
        <div class="legal-note">🔒 Tu <b>rol y tus permisos</b> los define rectoría; tus datos personales los manejas tú. El documento tampoco se edita aquí: si está mal, avísale a secretaría.</div>
      </div></div>
      ${d.permisos&&d.permisos.length?`<div class="card"><div class="card-head"><h3>🔐 Lo que puedes hacer</h3></div>
        <div class="card-body">${d.permisos.map(p=>`<span class="doc-chip ok">${esc(p.replace(/_/g," "))}</span>`).join("")}</div></div>`:""}
      ${d.rol==="rector"?`<div class="card" id="cfg-inst-card"><div class="card-head"><h3>🏛️ Configuración de mi institución</h3></div>
        <div class="card-body"><div class="small muted">Cargando…</div></div></div>`:""}
      ${esDocente?`<div class="card"><div class="card-head"><h3>📄 Mi hoja de vida</h3>
        <button class="btn btn-sm btn-primary" onclick="verHV(${d.personal_id})">Abrir hoja de vida</button></div>
        <div class="card-body"><div class="small muted">Ahí registras estudios, certificados y experiencia. Rectoría la ve y también puede complementarla.</div></div></div>`:""}
      ${d.personal_id?`<div class="card"><div class="card-head"><h3>🕐 Mi horario</h3></div>
        <div class="card-body" id="mp_horario"><div class="small muted">Cargando…</div></div></div>`:""}`);
    if(d.personal_id) cargarMiHorario(d.personal_id);
    if(d.rol==="rector") cargarTarjetaInstitucion();
  }catch(e){ main(`<div class="empty">Error</div>`); }
};
function miFotoSel(inp){
  const f=inp.files[0]; if(!f) return;
  if(f.size>800000){ toast("Imagen muy pesada (máx 800 KB)",true); return; }
  const rd=new FileReader();
  rd.onload=()=>{ window._miFoto=rd.result;
    document.getElementById("mp_foto").innerHTML=`<img src="${rd.result}" style="width:100%;height:100%;object-fit:cover">`; };
  rd.readAsDataURL(f);
}
async function guardarMiPerfil(){
  const d=window._miPerfil;
  const g=id=>{const e=document.getElementById(id);return e?e.value:undefined;};
  try{
    const r=await post("/usuarios/mi_perfil/guardar",{
      personal_id:d.personal_id, estudiante_id:d.estudiante_id, usuario_id:d.usuario_id,
      nombre:g("mp_nombre"), telefono:g("mp_tel"), email:g("mp_email"),
      direccion:g("mp_dir"), barrio_vereda:g("mp_barrio"), profesion:g("mp_prof"),
      foto:window._miFoto});
    toast(r.msg,!r.ok);
    if(r.ok){
      if(window._miFoto!==undefined){ ST.perfil.foto=window._miFoto; pintarAvatarSidebar(); }
      VISTAS.miperfil();
    }
  }catch(e){ toast("Error",true); }
}
async function cargarMiHorario(pid){
  try{
    const h=await api(`/academico/horarios/docente?personal_id=${pid}`);
    const DIAS=["Lunes","Martes","Miércoles","Jueves","Viernes"];
    document.getElementById("mp_horario").innerHTML=`
      <div class="small muted" style="margin-bottom:8px">${h.horas_semana} horas semanales · ${h.materias.length} materia(s)</div>
      <div class="horario-grid">
        ${DIAS.map(d=>`<div class="horario-col"><h5>${d}</h5>
          ${(h.horario[d]||[]).map(x=>`<div class="horario-bloque"><b>${esc(x.hora)}</b>
            <div>${MATERIA_ICO[x.materia]||"📚"} ${esc(x.materia)}</div>
            <div class="small muted">Salón ${esc(x.salon)}</div></div>`).join("")||'<div class="small muted" style="text-align:center">—</div>'}
        </div>`).join("")}
      </div>
      ${h.horas_semana?"":'<div class="small muted">Coordinación aún no te ha asignado horario.</div>'}`;
  }catch(e){ document.getElementById("mp_horario").innerHTML='<div class="small muted">Sin horario asignado.</div>'; }
}

/* ═══════════════════════════════════════════════════════════════════
   V8 · MAPA DE HORARIOS (puntos 11, 19)
   ═══════════════════════════════════════════════════════════════════ */
VISTAS.horarios = async function(){
  loading();
  try{
    const d = await api(`/academico/horarios/mapa?institucion_id=${ST.institucion_id}`);
    window._hmapa=d;
    const per=await api(`/academico/personal?institucion_id=${ST.institucion_id}&rol=docente`);
    window._hdocentes=per;
    main(head("Mapa de horarios","Todo el colegio de un vistazo: qué docente, qué materia, qué salón y a qué hora")+`
      <div class="kpis">
        <div class="kpi teal"><div class="kpi-ico">📅</div><div class="kpi-val">${d.n_asignaciones}</div><div class="kpi-lbl">Clases asignadas</div></div>
        <div class="kpi"><div class="kpi-ico">📊</div><div class="kpi-val">${d.cobertura}%</div><div class="kpi-lbl">Franjas cubiertas</div></div>
        <div class="kpi ${d.choques.length?'red':'green'}"><div class="kpi-ico">${d.choques.length?"⚠️":"✅"}</div>
          <div class="kpi-val">${d.choques.length}</div><div class="kpi-lbl">Choques de horario</div></div>
        <div class="kpi ${d.docentes_sin_horario.length?'orange':''}"><div class="kpi-ico">👤</div>
          <div class="kpi-val">${d.docentes_sin_horario.length}</div><div class="kpi-lbl">Docentes sin horario</div></div>
      </div>
      ${d.choques.length?`<div class="card"><div class="card-head"><h3>⚠️ Choques detectados</h3></div><div class="card-body">
        ${d.choques.map(c=>`<div class="choque"><b>${esc(c.docente)}</b> está asignado(a) el <b>${esc(c.dia)} ${esc(c.franja)}</b> en dos salones: ${c.salones.map(s=>esc(s)).join(" y ")}. Hay que corregirlo.</div>`).join("")}
      </div></div>`:""}
      <div class="card"><div class="card-head"><h3>🗓️ Horario general</h3>
        <span class="small muted">toca una casilla para asignar o cambiar</span></div>
      <div class="hmapa" id="hmapa-cont"></div></div>
      <div class="card"><div class="card-head"><h3>👨‍🏫 Carga de cada docente</h3></div>
      <div class="tbl-scroll"><table>
        <thead><tr><th>Docente</th><th style="text-align:center">Horas</th><th>Materias</th><th>Salones</th></tr></thead>
        <tbody>${d.carga_docentes.map(c=>`<tr>
          <td><div class="flex-cell">${avatarCell(c.foto,c.nombre)}<b>${esc(c.nombre)}</b></div></td>
          <td style="text-align:center"><span class="badge ${c.horas>25?'b-red':c.horas>18?'b-orange':'b-green'}">${c.horas}</span></td>
          <td class="small">${c.materias.map(m=>esc(m)).join(", ")}</td>
          <td class="small">${c.salones.map(s=>esc(s)).join(", ")}</td></tr>`).join("")}
        ${d.docentes_sin_horario.map(x=>`<tr style="opacity:.6"><td><b>${esc(x.nombre)}</b></td>
          <td style="text-align:center"><span class="badge b-gray">0</span></td>
          <td class="small" colspan="2">Sin horario asignado${x.area?" · área: "+esc(x.area):""}</td></tr>`).join("")}
        </tbody></table></div></div>
      <div class="legal-note">🕐 El horario lo asigna <b>coordinación o rectoría</b>, no cada docente. El sistema avisa si un docente queda en dos salones a la misma hora, y el horario aparece automáticamente en el portal del estudiante y en el perfil del docente.</div>`);
    pintarMapaHorario();
  }catch(e){ main(`<div class="empty">Error</div>`); }
};
function pintarMapaHorario(){
  const d=window._hmapa;
  document.getElementById("hmapa-cont").innerHTML=`
    <table><thead><tr><th class="sal">Salón</th>
      ${d.dias.map(dia=>`<th colspan="${d.franjas.length}">${dia}</th>`).join("")}</tr>
      <tr><th class="sal"></th>
      ${d.dias.map(()=>d.franjas.map(f=>`<th style="font-size:.6rem">${f.split("-")[0]}</th>`).join("")).join("")}</tr>
    </thead><tbody>
      ${d.salones.map(s=>{
        const g=d.grid[s.id]||{franjas:{}};
        return `<tr><td class="sal">${esc(s.nombre)}<div class="small muted" style="font-weight:400">${esc(s.grado)}</div></td>
        ${d.dias.map(dia=>d.franjas.map(f=>{
          const c=(g.franjas[dia]||{})[f];
          return `<td>${c?`<div class="hcelda lleno" onclick="editarFranja(${s.id},'${dia}','${f}',${c.id})">
              <div class="mat">${esc((c.materia||"").slice(0,11))}</div>
              <div class="doc">${esc((c.docente||"").split(" ")[0])}</div></div>`
            :`<div class="hcelda vacio" onclick="editarFranja(${s.id},'${dia}','${f}',0)">+</div>`}</td>`;
        }).join("")).join("")}</tr>`;}).join("")}
    </tbody></table>`;
}
function editarFranja(salonId, dia, franja, asigId){
  const d=window._hmapa;
  const sal=d.salones.find(s=>s.id===salonId);
  const actual=asigId?((d.grid[salonId].franjas[dia]||{})[franja]):null;
  const [ini,fin]=franja.split("-");
  document.getElementById("modal-srd-title").textContent=`🕐 ${sal?sal.nombre:""} · ${dia} ${franja}`;
  document.getElementById("modal-srd-body").innerHTML=`
    <input type="hidden" id="hf_id" value="${asigId||""}">
    <input type="hidden" id="hf_salon" value="${salonId}">
    <input type="hidden" id="hf_dia" value="${dia}">
    <input type="hidden" id="hf_ini" value="${ini}">
    <input type="hidden" id="hf_fin" value="${fin}">
    <div class="frow"><label>Materia *</label>
      <input id="hf_materia" value="${actual?esc(actual.materia):""}" placeholder="Matemáticas" list="materias-list">
      <datalist id="materias-list">${Object.keys(MATERIA_ICO).map(m=>`<option value="${m}">`).join("")}</datalist></div>
    <div class="frow"><label>Docente</label><select id="hf_docente">
      <option value="">— Sin asignar todavía —</option>
      ${(window._hdocentes||[]).map(p=>`<option value="${p.id}" ${actual&&actual.docente_id===p.id?"selected":""}>${esc(p.nombre)}${p.area?" · "+esc(p.area):""}</option>`).join("")}
    </select></div>
    <div class="legal-note">Si el docente ya tiene clase a esa hora en otro salón, el sistema te avisa y no deja guardar.</div>
    <div class="modal-foot" style="border:none;padding:14px 0 0">
      ${asigId?`<button class="btn btn-danger" onclick="quitarFranja(${asigId})">🗑 Quitar</button>`:""}
      <button class="btn" onclick="cerrarModal('modal-srd')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarFranja()">💾 Guardar</button></div>`;
  abrirModal("modal-srd");
}
async function guardarFranja(){
  const g=id=>document.getElementById(id).value;
  if(!g("hf_materia").trim()){ toast("Escribe la materia",true); return; }
  try{
    const r=await post("/academico/horarios/asignar",{institucion_id:ST.institucion_id,
      id:parseInt(g("hf_id"))||0, salon_id:parseInt(g("hf_salon")),
      personal_id:parseInt(g("hf_docente"))||null, materia:g("hf_materia"),
      dia:g("hf_dia"), hora_inicio:g("hf_ini"), hora_fin:g("hf_fin"),
      asignado_por:ST.perfil.titulo});
    toast(r.msg,!r.ok);
    if(r.ok){ cerrarModal("modal-srd"); VISTAS.horarios(); }
  }catch(e){ toast("Error",true); }
}
async function quitarFranja(id){
  if(!confirm("¿Quitar esta clase del horario?")) return;
  try{ const r=await post("/academico/horarios/quitar",{id}); toast(r.msg,!r.ok);
    if(r.ok){ cerrarModal("modal-srd"); VISTAS.horarios(); }
  }catch(e){ toast("Error",true); }
}

/* ═══════════════════════════════════════════════════════════════════
   V8 · SUPERVISIÓN de coordinación (puntos 20, 21, 22)
   ═══════════════════════════════════════════════════════════════════ */
VISTAS.supervision = async function(tab){
  loading();
  try{
    const t=tab||"pendientes";
    const [pend, docs] = await Promise.all([
      api(`/academico/supervision/pendientes?institucion_id=${ST.institucion_id}`),
      api(`/academico/personal?institucion_id=${ST.institucion_id}&rol=docente`),
    ]);
    main(head("Supervisión académica","Revisa el material que están usando tus docentes y cómo va cada salón")+`
      <div class="subtabs">
        ${[["pendientes",`📋 Por revisar (${pend.n})`],["docentes","👨‍🏫 Por docente"]].map(([k,l])=>
          `<button class="subtab ${t===k?'active':''}" onclick="VISTAS.supervision('${k}')">${l}</button>`).join("")}</div>
      ${t==="pendientes"?`
        <div class="legal-note">📋 Estas clases ya están publicadas y los estudiantes las ven, pero coordinación todavía no las ha revisado. Revisar no es censurar: es acompañar y asegurar que el material corresponda al plan de área.</div>
        ${pend.pendientes.map(p=>`
          <div class="card"><div class="card-body">
            <div style="display:flex;gap:12px;align-items:flex-start;flex-wrap:wrap">
              <div style="flex:1;min-width:210px">
                <b>${TIPO_ICO[p.tipo]||"📝"} ${esc(p.titulo)}</b>
                <div class="small muted">${esc(p.materia||"")} · Salón ${esc(p.salon)} · ${esc(p.docente)}${p.corte?" · "+esc(p.corte):""}</div>
                <div style="margin-top:5px">
                  <span class="badge ${p.n_materiales?'b-green':'b-orange'}">📎 ${p.n_materiales} material(es)</span>
                  ${p.tiene_video?'<span class="badge b-purple">🎬 con video</span>':""}
                </div>
              </div>
              <div style="display:flex;gap:5px;flex-wrap:wrap">
                <button class="btn btn-xs" onclick="abrirClaseDocente(${p.id})">👁️ Ver material</button>
                <button class="btn btn-xs btn-green" onclick="revisarMaterial(${p.id},'aprobado')">✅ Aprobar</button>
                <button class="btn btn-xs btn-gold" onclick="revisarMaterial(${p.id},'ajustes')">📝 Pedir ajustes</button>
              </div>
            </div></div></div>`).join("")||'<div class="empty">🎉 Todo el material está revisado.</div>'}`
      :`
        <div class="grid-cards">
          ${docs.map(d=>`<div class="va-card" style="cursor:pointer" onclick="verSupervisionDocente(${d.id})">
            <div style="display:flex;gap:10px;align-items:center">
              ${avatarCell(d.foto,d.nombre)}
              <div style="flex:1"><b>${esc(d.nombre)}</b>
                <div class="small muted">${esc(d.area||"—")}${d.experiencia_anios?" · "+d.experiencia_anios+" años":""}</div></div>
            </div>
            <button class="btn btn-sm" style="width:100%;margin-top:10px">Ver su trabajo →</button>
          </div>`).join("")}
        </div>`}`);
  }catch(e){ main(`<div class="empty">Error</div>`); }
};
async function revisarMaterial(actId, estado){
  const obs=prompt(estado==="aprobado"?"Observación (opcional):":"¿Qué debe ajustar el docente?");
  if(obs===null) return;
  if(estado==="ajustes" && !obs.trim()){ toast("Escribe qué debe ajustar",true); return; }
  try{
    const r=await post("/academico/supervision/revisar",{institucion_id:ST.institucion_id,
      actividad_id:actId, revisor:ST.perfil.nombre||ST.perfil.titulo, estado, observacion:obs});
    toast(r.msg,!r.ok);
    if(r.ok) VISTAS.supervision("pendientes");
  }catch(e){ toast("Error",true); }
}
async function verSupervisionDocente(pid){
  loading();
  try{
    const d = await api(`/academico/supervision/docente?personal_id=${pid}`);
    if(!d.ok){ toast(d.msg,true); return; }
    const r=d.resumen_clases;
    main(`<div style="display:flex;gap:10px;align-items:center;margin-bottom:14px;flex-wrap:wrap">
        <button class="btn btn-sm" onclick="VISTAS.supervision('docentes')">← Docentes</button>
        <h2 style="margin:0;font-size:1.2rem">👨‍🏫 ${esc(d.docente.nombre)}</h2></div>
      <div class="card"><div class="card-body">
        <div style="display:flex;gap:14px;align-items:center;flex-wrap:wrap">
          ${d.docente.foto?`<img class="avatar-foto lg" src="${d.docente.foto}">`:`<div class="avatar-sm" style="width:56px;height:56px">${ini(d.docente.nombre)}</div>`}
          <div style="flex:1;min-width:200px">
            <b>${esc(d.docente.nombre)}</b>
            <div class="small muted">${esc(d.docente.profesion||"")}${d.docente.experiencia?" · "+d.docente.experiencia+" años de experiencia":""}</div>
            <div class="small muted">${d.docente.telefono?"📱 "+esc(d.docente.telefono):""}${d.docente.email?" · ✉️ "+esc(d.docente.email):""}</div>
            <div class="small muted">${d.horas_semana} horas/semana · ${d.materias.map(m=>esc(m)).join(", ")}</div>
          </div>
          <button class="btn btn-sm" onclick="verHV(${d.docente.id})">📄 Hoja de vida</button>
        </div>
      </div></div>
      <div class="kpis">
        <div class="kpi"><div class="kpi-ico">📚</div><div class="kpi-val">${r.total}</div><div class="kpi-lbl">Clases publicadas</div></div>
        <div class="kpi ${r.con_material<r.total?'orange':'green'}"><div class="kpi-ico">📎</div><div class="kpi-val">${r.con_material}</div><div class="kpi-lbl">Con material</div></div>
        <div class="kpi ${r.sin_calificar?'red':'green'}"><div class="kpi-ico">📝</div><div class="kpi-val">${r.sin_calificar}</div><div class="kpi-lbl">Sin calificar</div></div>
        <div class="kpi"><div class="kpi-ico">📋</div><div class="kpi-val">${d.asistencia.pct!=null?d.asistencia.pct+"%":"—"}</div><div class="kpi-lbl">Su asistencia</div></div>
      </div>
      ${d.su_salon.n_estudiantes?`<div class="card"><div class="card-head"><h3>🏫 Cómo va su salón</h3></div><div class="card-body">
        <div class="info-grid">
          <div class="info-it"><span class="k">Estudiantes</span><b>${d.su_salon.n_estudiantes}</b></div>
          <div class="info-it"><span class="k">En riesgo crítico</span><b style="color:${d.su_salon.criticos?'var(--red)':'var(--green)'}">${d.su_salon.criticos}</b></div>
          <div class="info-it"><span class="k">Moderados</span><b>${d.su_salon.moderados}</b></div>
          <div class="info-it"><span class="k">Asistencia promedio</span><b>${d.su_salon.asistencia_promedio!=null?d.su_salon.asistencia_promedio+"%":"—"}</b></div>
        </div></div></div>`:""}
      <div class="card"><div class="card-head"><h3>📚 Su material de clase</h3>
        <span class="small muted">${d.clases.length} clases</span></div>
      <div style="max-height:480px;overflow-y:auto">
        ${d.clases.map(c=>`
          <div class="usr-row" style="align-items:flex-start">
            <span style="font-size:1.2rem">${TIPO_ICO[c.tipo]||"📝"}</span>
            <div style="flex:1;min-width:180px">
              <b>${esc(c.titulo)}</b>
              <div class="small muted">${esc(c.materia||"")} · Salón ${esc(c.salon)}${c.corte?" · "+esc(c.corte):""}</div>
              <div style="margin-top:4px">
                <span class="badge ${c.n_materiales?'b-green':'b-gray'}">📎 ${c.n_materiales}</span>
                ${c.tiene_video?'<span class="badge b-purple">🎬</span>':""}
                ${c.n_temas?`<span class="badge b-teal">📖 ${c.n_temas} temas</span>`:""}
                <span class="badge ${c.calificadas<c.entregas?'b-orange':'b-blue'}">${c.entregas}/${c.total} entregas · ${c.calificadas} calificadas</span>
              </div>
              ${c.materiales.length?`<div class="small muted" style="margin-top:4px">${c.materiales.map(m=>`${MAT_ICO[m.tipo]||"📎"} ${esc(m.nombre)}`).join(" · ")}</div>`:""}
              ${c.revision?`<div class="small" style="margin-top:5px;padding:6px 10px;border-radius:7px;background:${c.revision.estado==='aprobado'?'#DCFCE7':'#FEF3C7'}">
                ${c.revision.estado==="aprobado"?"✅":"📝"} <b>${esc(c.revision.revisor)}:</b> ${esc(c.revision.observacion||c.revision.estado)}</div>`:""}
            </div>
            <div style="display:flex;gap:4px;flex-direction:column">
              <button class="btn btn-xs" onclick="abrirClaseDocente(${c.id})">👁️</button>
              ${!c.revision?`<button class="btn btn-xs btn-green" onclick="revisarMaterial(${c.id},'aprobado')">✅</button>`:""}
            </div>
          </div>`).join("")||'<div class="empty">Este docente no ha publicado clases.</div>'}
      </div></div>
      ${d.temas_plan.length?`<div class="card"><div class="card-head"><h3>📖 Temas de su plan por corte</h3></div>
        <div class="tbl-scroll"><table><thead><tr><th>Tema</th><th>Materia</th><th>Período</th><th>Corte</th></tr></thead>
        <tbody>${d.temas_plan.map(t=>`<tr><td><b>${esc(t.tema)}</b>${t.detalle?`<div class="small muted">${esc(t.detalle)}</div>`:""}</td>
          <td class="small">${esc(t.materia||"—")}</td><td>P${t.periodo}</td><td class="small">${esc(t.corte||"—")}</td></tr>`).join("")}
        </tbody></table></div></div>`:""}`);
  }catch(e){ main(`<div class="empty">Error</div>`); }
}

/* ═══════════════════════════════════════════════════════════════════
   V8 · PRESUPUESTO con rubros normativos (punto 28)
   ═══════════════════════════════════════════════════════════════════ */
async function fsePresupuesto(){
  const [p, cat] = await Promise.all([
    api(`/fse/presupuesto?institucion_id=${ST.institucion_id}`),
    api(`/fse/rubros/catalogo`),
  ]);
  window._catRubros=cat;
  const t=p.totales;
  document.getElementById("fse-cont").innerHTML = `
    <div class="kpis">
      <div class="kpi"><div class="kpi-ico">📊</div><div class="kpi-val sm">${money(t.presupuesto)}</div><div class="kpi-lbl">Presupuestado</div></div>
      <div class="kpi orange"><div class="kpi-ico">📤</div><div class="kpi-val sm">${money(t.ejecutado)}</div><div class="kpi-lbl">Ejecutado (${t.pct_ejecucion}%)</div></div>
      <div class="kpi green"><div class="kpi-ico">💰</div><div class="kpi-val sm">${money(t.disponible)}</div><div class="kpi-lbl">Disponible</div></div>
      <div class="kpi ${t.sobre_ejecutados?'red':''}"><div class="kpi-ico">⚠️</div><div class="kpi-val">${t.sobre_ejecutados}</div><div class="kpi-lbl">Rubros excedidos</div></div>
    </div>
    ${p.alertas.length?`<div class="card" style="border-color:var(--red)"><div class="card-body">
      ${p.alertas.map(a=>`<div class="choque">⚠️ ${esc(a)}</div>`).join("")}</div></div>`:""}
    <div style="text-align:right;margin-bottom:10px">
      <button class="btn btn-primary btn-sm" onclick="abrirRubroCatalogo()">➕ Agregar rubro del catálogo</button></div>
    ${p.por_grupo.map(g=>`
      <div class="grupo-head">${esc(g.grupo)} · ${money(g.ejecutado)} de ${money(g.presupuesto)} (${g.pct}%)</div>
      ${p.rubros.filter(r=>r.grupo===g.grupo).map(r=>`
        <div class="rubro-fila ${r.sobre_ejecutado?'sobre':''}">
          <span class="rubro-cod">${esc(r.codigo||"—")}</span>
          <div style="flex:1;min-width:180px">
            <b class="small">${esc(r.nombre)}</b>
            ${r.detalle?`<div class="small muted">${esc(r.detalle)}</div>`:""}
            <div class="small muted">${r.n_movimientos} movimiento(s)</div>
          </div>
          <div style="width:150px">
            <div class="prog"><div class="prog-fill" style="width:${Math.min(100,r.pct)}%;background:${r.sobre_ejecutado?'var(--red)':r.pct>80?'var(--orange)':'var(--green)'}"></div></div>
            <div class="small muted" style="text-align:center">${r.pct}%</div>
          </div>
          <div style="text-align:right;min-width:110px">
            <b class="small">${money(r.disponible)}</b>
            <div class="small muted">de ${money(r.presupuesto)}</div>
          </div>
          <button class="btn btn-xs" onclick="editarRubro(${r.id})">✎</button>
        </div>`).join("")}`).join("")}
    <div class="legal-note">🏛️ Los rubros siguen el <b>${esc(cat.marco_legal.decreto)}</b>. Tope de contratación: <b>${esc(cat.marco_legal.tope_contratacion)}</b>.
      <div class="small" style="margin-top:6px">${cat.marco_legal.reglas.map(x=>"• "+esc(x)).join("<br>")}</div></div>`;
}
function abrirRubroCatalogo(){
  const cat=window._catRubros;
  document.getElementById("modal-srd-title").textContent="➕ Agregar rubro del catálogo oficial";
  document.getElementById("modal-srd-body").innerHTML=`
    <div class="legal-note">🏛️ Los rubros no se inventan: se toman del catálogo del Decreto 1075. Así el presupuesto queda como lo espera la Contraloría.</div>
    <div class="frow"><label>Rubro *</label><select id="rc_codigo">
      <optgroup label="Gastos">
        ${cat.gastos.map(g=>`<option value="${g.codigo}">${g.codigo} · ${esc(g.nombre)}</option>`).join("")}</optgroup>
      <optgroup label="Ingresos">
        ${cat.ingresos.map(g=>`<option value="${g.codigo}">${g.codigo} · ${esc(g.nombre)}</option>`).join("")}</optgroup>
    </select></div>
    <div class="frow"><label>Presupuesto asignado (COP)</label><input type="number" id="rc_valor" placeholder="0"></div>
    <div class="modal-foot" style="border:none;padding:14px 0 0">
      <button class="btn" onclick="cerrarModal('modal-srd')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarRubroCatalogo()">💾 Agregar</button></div>`;
  abrirModal("modal-srd");
}
async function guardarRubroCatalogo(){
  try{
    const r=await post("/fse/rubros/desde_catalogo",{institucion_id:ST.institucion_id,
      codigo:document.getElementById("rc_codigo").value,
      presupuesto:parseFloat(document.getElementById("rc_valor").value)||0});
    toast(r.msg,!r.ok);
    if(r.ok){ cerrarModal("modal-srd"); VISTAS.fse("presupuesto"); }
  }catch(e){ toast("Error",true); }
}

/* ═══════════════════════════════════════════════════════════════════
   V8 · SEGURIDAD DEL REGISTRO (punto 26)
   ═══════════════════════════════════════════════════════════════════ */
async function usrSeguridad(){
  const d = await api(`/usuarios/seguridad?institucion_id=${ST.institucion_id}&dias=7`);
  const r=d.resumen;
  document.getElementById("usr-cont").innerHTML = `
    <div class="kpis">
      <div class="kpi ${r.bloqueados?'red':'green'}"><div class="kpi-ico">🛡️</div><div class="kpi-val">${r.bloqueados}</div><div class="kpi-lbl">Registros bloqueados</div></div>
      <div class="kpi ${r.logins_fallidos?'orange':''}"><div class="kpi-ico">🚫</div><div class="kpi-val">${r.logins_fallidos}</div><div class="kpi-lbl">Ingresos fallidos</div></div>
      <div class="kpi"><div class="kpi-ico">📧</div><div class="kpi-val">${r.correos_sin_verificar}</div><div class="kpi-lbl">Correos sin verificar</div></div>
      <div class="kpi ${r.ips_sospechosas.length?'red':''}"><div class="kpi-ico">📡</div><div class="kpi-val">${r.ips_sospechosas.length}</div><div class="kpi-lbl">IP sospechosas</div></div>
    </div>
    <div class="card"><div class="card-head"><h3>🛡️ Protecciones activas</h3></div><div class="card-body">
      ${d.protecciones.map(p=>`<div class="prot-item">
        <span class="ok">${p.activa?"✅":"⬜"}</span>
        <div><b class="small">${esc(p.nombre)}</b><div class="small muted">${esc(p.detalle)}</div></div>
      </div>`).join("")}
      <div class="legal-note">🔐 Son <b>siete capas</b>. Un bot tendría que pasar la operación matemática, tener un correo real no desechable, no repetir IP, y aun así <b>rectoría decide</b> si entra o no.</div>
    </div></div>
    ${r.ips_sospechosas.length?`<div class="card"><div class="card-head"><h3>📡 Conexiones con varios intentos</h3></div><div class="card-body">
      ${r.ips_sospechosas.map(x=>`<div class="choque">La IP <b>${esc(x.ip)}</b> hizo ${x.n} intentos en los últimos ${r.dias} días.</div>`).join("")}
    </div></div>`:""}
    <div class="card"><div class="card-head"><h3>📜 Intentos de registro</h3></div>
    <div style="max-height:420px;overflow-y:auto">
      ${d.intentos.map(x=>`<div class="log-row ${x.resultado!=='ok'?'fallido':''}">
        <span>${x.resultado==="ok"?"✅":x.resultado==="bloqueado"?"🛡️":"⚠️"}</span>
        <b style="flex:1;min-width:140px">${esc(x.email||"—")}</b>
        <span class="small muted" style="flex:2">${esc(x.motivo||x.resultado)}</span>
        <span class="small muted">${esc(x.ip||"")}</span>
        <span class="small muted">${esc(x.fecha)}</span></div>`).join("")||'<div class="empty">Sin intentos registrados.</div>'}
    </div></div>`;
}

/* Vista previa del portal del contratista (punto 29) */
async function vistaPreviaPortal(id){
  try{
    const d=await api(`/contratos/portal/vista_previa?contratista_id=${id}`);
    if(!d.ok){ toast(d.msg,true); return; }
    document.getElementById("modal-srd-title").textContent="👁️ Así lo ve el contratista";
    document.getElementById("modal-srd-body").innerHTML=`
      <div class="legal-note">${esc(d.nota_produccion)}</div>
      <div class="fsec">🔑 Dos formas de entrar</div>
      <div class="mat-fila"><span>🆔</span><div class="nom"><b>Con su cédula o NIT</b>
        <div class="small muted">${esc(d.url_cedula)} — no necesita recordar ningún enlace</div></div>
        <button class="btn btn-xs" onclick="probarIngresoCedula('${esc(d.contratista.nit||"")}')">▶️ Probar</button></div>
      <div class="mat-fila"><span>🔗</span><div class="nom"><b>Con enlace directo</b>
        <div class="small muted" style="word-break:break-all">${esc(d.url_token)}</div></div>
        <button class="btn btn-xs" onclick="navigator.clipboard&&navigator.clipboard.writeText('${esc(d.url_token)}');toast('Enlace copiado')">📋</button></div>
      <div class="fsec">📱 Lo que ve al entrar</div>
      <div style="border:2px solid var(--border);border-radius:12px;padding:16px;background:#F8FAFC">
        <div style="text-align:center;margin-bottom:12px">
          <b style="font-size:1.05rem">Hola, ${esc(d.contratista.nombre)}</b>
          <div class="small muted">NIT ${esc(d.contratista.nit||"—")}</div></div>
        <b class="small">📋 Tus documentos</b>
        <div style="margin:6px 0">${d.vista.documentos.map(x=>`<span class="doc-chip ${x.ok?'ok':'no'}">${x.ok?"✓":"✕"} ${esc(x.label)}${x.por_vencer?" ⏳":""}${x.vencido?" 🚨":""}</span>`).join("")}</div>
        ${d.vista.faltantes.length?`<div class="small" style="color:var(--red)">Te faltan: ${d.vista.faltantes.map(f=>esc(f)).join(", ")}</div>`:'<div class="small" style="color:var(--green)">✅ Expediente completo</div>'}
        <b class="small" style="display:block;margin-top:12px">📜 Tus contratos</b>
        ${d.vista.contratos.map(c=>`<div class="small muted">• ${esc(c.numero)} · ${esc(c.objeto.slice(0,44))} · ${esc(c.estado)}</div>`).join("")||'<div class="small muted">Sin contratos todavía.</div>'}
        <b class="small" style="display:block;margin-top:12px">📨 Tus propuestas</b>
        ${(d.vista.propuestas||[]).map(p=>`<div class="small muted">• ${money(p.valor)} · ${esc((p.descripcion||"").slice(0,50))}</div>`).join("")||'<div class="small muted">Sin propuestas enviadas.</div>'}
      </div>
      <div class="fsec">📌 Cómo funciona</div>
      <ol style="line-height:1.75;font-size:.87rem">${d.instrucciones.map(x=>`<li>${esc(x)}</li>`).join("")}</ol>`;
    abrirModal("modal-srd");
  }catch(e){ toast("Error",true); }
}
async function probarIngresoCedula(doc){
  const d=prompt("Simula el ingreso del contratista.\n\nEscribe la cédula o NIT:", doc);
  if(d===null) return;
  try{
    const r=await post("/contratos/portal/ingresar",{documento:d});
    toast(r.msg,!r.ok);
  }catch(e){ toast("Error",true); }
}

/* ═══════════════════════════════════════════════════════════════════
   V9 · REJILLA DE CONTRATACIÓN y documentos legales
   La rejilla amarra todo: rubro → CDP → invitación → contrato → RP.
   De ahí salen los 7 documentos con sus fechas coherentes.
   ═══════════════════════════════════════════════════════════════════ */

VISTAS.rejilla = async function(tab){
  loading();
  try{
    const t = tab||"rejilla";
    ST._rjTab = t;
    const [rj, pf] = await Promise.all([
      api(`/legal/rejilla?institucion_id=${ST.institucion_id}`),
      api(`/legal/perfil?institucion_id=${ST.institucion_id}`),
    ]);
    window._rejilla = rj; window._perfilLegal = pf;
    const r = rj.resumen;
    main(head("Contratación institucional","La rejilla es el registro maestro: de ahí salen todos los documentos con sus fechas",
      `<button class="btn btn-primary" onclick="editarFilaRejilla(0)">➕ Nuevo proceso</button>`)+`
      ${!pf.completo?`<div class="digest" style="border-color:var(--orange);background:#FEF3C7">
        <div style="font-size:1.8rem">⚠️</div><div style="flex:1">
          <b>Faltan datos legales de la institución</b>
          <div class="small">Sin ${pf.faltantes.slice(0,4).map(x=>esc(x)).join(", ")} los documentos salen con espacios en blanco y no tienen validez.</div>
        </div><button class="btn btn-sm btn-gold" onclick="VISTAS.rejilla('perfil')">Completar ahora</button></div>`:""}
      <div class="kpis">
        <div class="kpi teal"><div class="kpi-ico">📋</div><div class="kpi-val">${r.n}</div><div class="kpi-lbl">Procesos ${rj.vigencia}</div></div>
        <div class="kpi"><div class="kpi-ico">💰</div><div class="kpi-val sm">${money(r.valor_total)}</div><div class="kpi-lbl">Valor contratado</div></div>
        <div class="kpi green"><div class="kpi-ico">✅</div><div class="kpi-val">${r.liquidados}</div><div class="kpi-lbl">Liquidados</div></div>
        <div class="kpi ${r.docs_faltantes?'orange':''}"><div class="kpi-ico">📄</div><div class="kpi-val">${r.docs_faltantes}</div><div class="kpi-lbl">Documentos por generar</div></div>
      </div>
      <div class="subtabs">
        ${[["rejilla","📋 Rejilla"],["perfil","🏛️ Datos legales"],["cartas","✉️ Correspondencia"]].map(([k,l])=>
          `<button class="subtab ${t===k?'active':''}" onclick="VISTAS.rejilla('${k}')">${l}</button>`).join("")}</div>
      <div id="rj-cont"><div class="empty">Cargando…</div></div>`);
    if(t==="rejilla") pintarRejilla();
    if(t==="perfil") pintarPerfilLegal();
    if(t==="cartas") await pintarCorrespondencia();
  }catch(e){ main(`<div class="empty">Error</div>`); }
};

function pintarRejilla(){
  const rj=window._rejilla;
  document.getElementById("rj-cont").innerHTML=`
    <div class="legal-note">📋 <b>Así funciona la rejilla:</b> cada fila es un proceso. Al crearla, el sistema numera el <b>CDP (04-N)</b>, la <b>invitación</b>, el <b>contrato (año+N)</b> y el <b>RP (05-N)</b>, y calcula todas las fechas en cascada. Los documentos toman sus datos de aquí, así nunca se contradicen entre ellos.</div>
    <div class="card"><div class="card-head"><h3>Rejilla de contratación ${rj.vigencia}</h3>
      <button class="btn btn-sm" onclick="window.print()">🖨️ Imprimir rejilla</button></div>
    <div class="rejilla-tabla"><table>
      <thead><tr>
        <th style="width:34px">N°</th>
        <th class="g1">RUBRO</th><th class="g1">FUENTE</th><th class="g1" style="text-align:right">VALOR</th>
        <th class="g2">CDP</th><th class="g2">FECHA</th>
        <th>OBJETO</th>
        <th class="g3">CONTRATO</th><th class="g3">FECHA</th><th class="g3">CONTRATISTA</th>
        <th class="g4">RP</th><th class="g4">FECHA</th>
        <th>ACTA FINAL</th><th>DOCUMENTOS</th><th></th>
      </tr></thead>
      <tbody>${rj.filas.map(f=>`
        <tr>
          <td class="rj-num">${f.consecutivo}</td>
          <td><span class="rj-num" style="font-size:.7rem">${esc(f.rubro_codigo||"—")}</span>
            <div class="rj-fecha">${esc((f.rubro_nombre||"").slice(0,26))}</div></td>
          <td class="rj-fecha">${esc((f.fuente||"").slice(0,18))}</td>
          <td style="text-align:right"><b>${money(f.valor)}</b></td>
          <td class="rj-num">${esc(f.cdp_num||"—")}</td>
          <td class="rj-fecha">${esc(f.cdp_fecha||"—")}</td>
          <td class="rj-obj">${esc((f.descripcion||"").slice(0,80))}</td>
          <td class="rj-num">${esc(f.contrato_num||"—")}</td>
          <td class="rj-fecha">${esc(f.contrato_fecha||"—")}</td>
          <td class="rj-fecha">${esc((f.contratista_nombre||"—").slice(0,24))}
            ${f.contratista_doc?`<div style="opacity:.7">${esc(f.contratista_doc)}</div>`:""}</td>
          <td class="rj-num">${esc(f.rp_num||"—")}</td>
          <td class="rj-fecha">${esc(f.rp_fecha||"—")}</td>
          <td class="rj-fecha">${esc(f.acta_final_fecha||"—")}
            ${f.vencido?'<div style="color:var(--red);font-weight:700">⚠️ venció</div>':""}</td>
          <td><span class="badge ${f.n_docs>=7?'b-green':f.n_docs?'b-orange':'b-gray'}">${f.n_docs}/7</span></td>
          <td><div style="display:flex;gap:3px;flex-direction:column">
            <button class="btn btn-xs btn-primary" onclick="abrirProceso(${f.id})">📂 Abrir</button>
            <button class="btn btn-xs" onclick="editarFilaRejilla(${f.id})">✎</button>
          </div></td>
        </tr>`).join("")||'<tr><td colspan="15" class="empty">Sin procesos este año.</td></tr>'}
      </tbody></table></div></div>
    ${rj.por_rubro.length?`<div class="card"><div class="card-head"><h3>💰 Por rubro</h3></div><div class="card-body">
      ${rj.por_rubro.map(x=>`<span class="badge b-teal" style="font-size:.82rem;padding:6px 12px;margin:3px">
        <b>${esc(x.codigo)}</b>: ${money(x.valor)} · ${x.n} proceso(s)</span>`).join("")}
    </div></div>`:""}`;
}

/* ── El proceso completo de una fila ── */
async function abrirProceso(rejillaId){
  loading();
  try{
    const [docs, rj] = await Promise.all([
      api(`/legal/documentos?rejilla_id=${rejillaId}`),
      api(`/legal/rejilla?institucion_id=${ST.institucion_id}`),
    ]);
    const f = rj.filas.find(x=>x.id===rejillaId);
    if(!f){ toast("Proceso no encontrado",true); return; }
    window._procF = f; window._procD = docs;
    const HITOS=[["cotizacion_fecha","Cotización","📨"],["cdp_fecha","CDP","💰"],
      ["invitacion_fecha","Invitación","📢"],["contrato_fecha","Contrato","📜"],
      ["rp_fecha","RP","🧾"],["acta_inicio_fecha","Inicio","🚀"],
      ["acta_final_fecha","Final","✅"],["liquidacion_fecha","Liquidación","🏁"]];
    const hoy=hoyISO();
    main(`<div style="display:flex;gap:10px;align-items:center;margin-bottom:14px;flex-wrap:wrap">
        <button class="btn btn-sm" onclick="VISTAS.rejilla('rejilla')">← Rejilla</button>
        <h2 style="margin:0;font-size:1.15rem">📂 Proceso ${esc(f.contrato_num||f.consecutivo)}</h2>
        <span class="badge b-teal" style="margin-left:auto">${docs.completos}/${docs.total} documentos</span></div>
      <div class="card"><div class="card-body">
        <b>${esc(f.descripcion)}</b>
        <div class="small muted" style="margin-top:4px">
          ${esc(f.rubro_codigo||"")} · ${esc(f.rubro_nombre||"")} · ${money(f.valor)}
          ${f.contratista_nombre?" · "+esc(f.contratista_nombre):""}</div>
        <div class="linea-proceso">
          ${HITOS.map(([campo,lbl,ico])=>{
            const fe=f[campo];
            const done=fe&&fe<=hoy;
            const now=fe&&fe>hoy&&!HITOS.some(([c2])=>f[c2]&&f[c2]>hoy&&f[c2]<fe);
            return `<div class="lp-hito ${done?'done':now?'now':''}">
              <div class="lp-dot">${done?"✓":ico}</div>
              <div class="lp-lbl">${lbl}</div>
              <div class="lp-fec">${esc(fe||"—")}</div></div>`;}).join("")}
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px">
          <button class="btn btn-sm" onclick="editarFechas(${f.id})">📅 Ajustar fechas</button>
          <button class="btn btn-sm" onclick="editarFilaRejilla(${f.id})">✎ Editar datos</button>
          <button class="btn btn-sm btn-gold" onclick="window.open(API+'/legal/documentos/expediente?rejilla_id=${f.id}')">📚 Expediente completo</button>
        </div>
      </div></div>
      <div class="card"><div class="card-head"><h3>📄 Documentos del proceso</h3>
        <span class="small muted">se generan con las fechas de la rejilla</span></div>
      <div class="card-body">
        ${docs.documentos.map(d=>`
          <div class="mat-fila ${d.bloqueado?'mat-err':''}">
            <span style="font-size:1.15rem">${d.generado?"✅":d.bloqueado?"🔒":"⬜"}</span>
            <div class="nom"><b>${esc(d.label)}</b>
              <div class="small muted">${d.fecha?"Fecha: "+esc(d.fecha):"sin fecha"}
                ${d.numero?" · N° "+esc(d.numero):""}
                ${d.version?" · v"+d.version:""}
                ${d.estado?" · "+esc(d.estado):""}</div>
              ${d.bloqueado?`<div class="small" style="color:var(--red)">⛔ ${esc(d.motivo||"")}</div>`:""}</div>
            <div style="display:flex;gap:4px;flex-wrap:wrap">
              ${d.generado?`
                <button class="btn btn-xs btn-primary" onclick="window.open(API+'/legal/documentos/ver?id=${d.id}')">👁️ Ver / PDF</button>
                <button class="btn btn-xs" onclick="regenerarDoc(${f.id},'${d.tipo}')">🔄 Regenerar</button>
                ${d.estado!=="firmado"?`<button class="btn btn-xs btn-green" onclick="estadoDoc(${d.id},'firmado')">✍️ Firmado</button>`:""}`
              :d.bloqueado?`<span class="badge b-gray">Bloqueado</span>`
              :`<button class="btn btn-xs btn-primary" onclick="generarDoc(${f.id},'${d.tipo}')">⚡ Generar</button>`}
            </div>
          </div>`).join("")}
        <div class="legal-note" style="margin-top:12px">🔒 Los bloqueos no son capricho: no puede haber <b>acta de inicio sin RP</b>, ni <b>acta final sin acta de inicio</b>, ni <b>liquidación sin acta final</b>. Es el orden que exige la ley y lo que revisa la Contraloría.</div>
      </div></div>`);
  }catch(e){ main(`<div class="empty">Error</div>`); }
}
async function generarDoc(rejillaId, tipo){
  const EXTRA={contrato:["supervisor","domicilio_contratista"],
    acta_inicio:["supervisor"],acta_final:["supervisor","observaciones"],
    acta_liquidacion:["supervisor","observaciones"],estudios_previos:["supervisor","necesidad"]};
  let datos={};
  if(EXTRA[tipo]){
    if(EXTRA[tipo].includes("supervisor")){
      const s=prompt("¿Quién es el supervisor del contrato?\n(Aparecerá en el documento y firmará las actas)","Rectoría");
      if(s===null) return;
      datos.supervisor=s;
    }
    if(EXTRA[tipo].includes("domicilio_contratista")){
      datos.domicilio_contratista=prompt("Domicilio del contratista (para la minuta):")||"";
    }
    if(EXTRA[tipo].includes("observaciones")){
      datos.observaciones=prompt("Observaciones (opcional):")||"";
    }
  }
  try{
    const r=await post("/legal/documentos/generar",{rejilla_id:rejillaId,tipo,datos,
      generado_por:ST.perfil.titulo});
    toast(r.msg,!r.ok);
    if(r.ok){ abrirProceso(rejillaId); setTimeout(()=>window.open(API+r.url),600); }
  }catch(e){ toast("Error",true); }
}
async function regenerarDoc(rejillaId,tipo){
  if(!confirm("¿Regenerar el documento con los datos actuales de la rejilla?\n\nSe crea una versión nueva.")) return;
  generarDoc(rejillaId,tipo);
}
async function estadoDoc(id,estado){
  try{ const r=await post("/legal/documentos/estado",{id,estado}); toast(r.msg,!r.ok);
    if(r.ok) abrirProceso(window._procF.id);
  }catch(e){ toast("Error",true); }
}

function editarFilaRejilla(id){
  const f=id?(window._rejilla.filas.find(x=>x.id===id)||{}):{};
  document.getElementById("modal-srd-title").textContent=id?"✎ Editar proceso":"➕ Nuevo proceso de contratación";
  document.getElementById("modal-srd-body").innerHTML=`
    <input type="hidden" id="rf_id" value="${id||""}">
    <div class="legal-note">Al guardar, el sistema numera el CDP, la invitación, el contrato y el RP, y calcula todas las fechas en cascada. Después puedes ajustarlas una por una.</div>
    <div class="frow"><label>Objeto del proceso *</label>
      <textarea id="rf_desc" rows="2" placeholder="SUMINISTRO DE MATERIALES DIDÁCTICOS PARA LAS SEDES">${esc(f.descripcion||"")}</textarea></div>
    <div class="frow-2">
      <div><label>Código del rubro</label><input id="rf_rc" value="${esc(f.rubro_codigo||"")}" placeholder="2.1.3.1.3.02"></div>
      <div><label>Nombre del rubro</label><input id="rf_rn" value="${esc(f.rubro_nombre||"")}" placeholder="Dotaciones pedagógicas"></div>
    </div>
    <div class="frow-3">
      <div><label>Valor (COP) *</label><input type="number" id="rf_val" value="${f.valor||0}"></div>
      <div><label>Fuente</label><select id="rf_fu">
        ${["Recurso de gratuidad","Recursos propios","Otras transferencias","Recursos del balance","Donaciones"].map(x=>
          `<option ${f.fuente===x?"selected":""}>${x}</option>`).join("")}</select></div>
      <div><label>Plazo (días)</label><input type="number" id="rf_pl" value="${f.plazo_dias||5}"></div>
    </div>
    <div class="frow-2">
      <div><label>Fecha del CDP</label><input type="date" id="rf_cdp" value="${f.cdp_fecha||hoyISO()}">
        <div class="small muted" style="margin-top:4px">Es la fecha ancla: las demás se calculan desde aquí</div></div>
      <div><label>Código UNSPSC</label><input id="rf_uns" value="${esc(f.unspsc||"")}" placeholder="72154100"></div>
    </div>
    <div class="frow"><label>Contratista</label><select id="rf_prov">
      <option value="">— Por definir —</option></select></div>
    ${id?`<label class="check-row"><input type="checkbox" id="rf_auto"> Recalcular todas las fechas desde el CDP</label>`:""}
    <div class="modal-foot" style="border:none;padding:14px 0 0">
      ${id?`<button class="btn btn-danger" onclick="eliminarFilaRejilla(${id})">🗑 Eliminar</button>`:""}
      <button class="btn" onclick="cerrarModal('modal-srd')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarFilaRejilla()">💾 Guardar</button></div>`;
  cargarProvSelect("rf_prov", f.contratista_id);
  abrirModal("modal-srd");
}
async function cargarProvSelect(elId, sel){
  try{
    const d=await api(`/contratos/contratistas`);
    const el=document.getElementById(elId);
    if(!el) return;
    el.innerHTML='<option value="">— Por definir —</option>'+
      d.map(p=>`<option value="${p.id}" ${sel===p.id?"selected":""}>${esc(p.nombre)} · ${esc(p.nit||"")}</option>`).join("");
  }catch(e){}
}
async function guardarFilaRejilla(){
  const g=id=>{const e=document.getElementById(id);return e?e.value:"";};
  const auto=document.getElementById("rf_auto");
  const body={id:parseInt(g("rf_id"))||0, institucion_id:ST.institucion_id,
    descripcion:g("rf_desc"), rubro_codigo:g("rf_rc"), rubro_nombre:g("rf_rn"),
    valor:parseFloat(g("rf_val"))||0, fuente:g("rf_fu"),
    plazo_dias:parseInt(g("rf_pl"))||5, cdp_fecha:g("rf_cdp"), unspsc:g("rf_uns"),
    contratista_id:parseInt(g("rf_prov"))||null,
    auto_fechas: auto?auto.checked:true};
  if(!body.descripcion.trim()){ toast("Escribe el objeto del proceso",true); return; }
  try{ const r=await post("/legal/rejilla/guardar",body);
    if(!r.ok){toast(r.msg,true);return;}
    cerrarModal("modal-srd"); toast(r.msg); VISTAS.rejilla("rejilla");
  }catch(e){ toast("Error",true); }
}
async function eliminarFilaRejilla(id){
  if(!confirm("¿Eliminar este proceso y todos sus documentos?\n\nNo se puede deshacer.")) return;
  try{ const r=await post("/legal/rejilla/eliminar?id="+id,{});
    toast(r.msg,!r.ok); if(r.ok){ cerrarModal("modal-srd"); VISTAS.rejilla("rejilla"); }
  }catch(e){ toast("Error",true); }
}
function editarFechas(id){
  const f=window._procF||window._rejilla.filas.find(x=>x.id===id);
  const CAMPOS=[["cdp_fecha","💰 CDP"],["invitacion_fecha","📢 Invitación"],
    ["cierre_fecha","🔒 Cierre de ofertas"],["evaluacion_fecha","📊 Evaluación"],
    ["contrato_fecha","📜 Contrato"],["rp_fecha","🧾 RP"],
    ["acta_inicio_fecha","🚀 Acta de inicio"],["acta_final_fecha","✅ Acta final"],
    ["liquidacion_fecha","🏁 Liquidación"]];
  document.getElementById("modal-srd-title").textContent="📅 Fechas del proceso";
  document.getElementById("modal-srd-body").innerHTML=`
    <input type="hidden" id="fx_id" value="${id}">
    <div class="legal-note">Estas fechas van a TODOS los documentos. Si cambias una, el sistema avisa si queda incoherente con las demás.</div>
    <div class="frow-2">
      <div><label>N° de CDP</label><input id="fx_cdp_num" value="${esc(f.cdp_num||"")}"></div>
      <div><label>N° de RP</label><input id="fx_rp_num" value="${esc(f.rp_num||"")}"></div>
    </div>
    <div class="frow-2">
      <div><label>N° de contrato</label><input id="fx_contrato_num" value="${esc(f.contrato_num||"")}"></div>
      <div><label>N° de invitación</label><input id="fx_invitacion_num" value="${esc(f.invitacion_num||"")}"></div>
    </div>
    <div class="fsec">Cronología</div>
    ${CAMPOS.map(([c,l])=>`<div class="frow-2" style="margin-bottom:6px">
      <label style="align-self:center">${l}</label>
      <input type="date" id="fx_${c}" value="${f[c]||""}"></div>`).join("")}
    <div class="modal-foot" style="border:none;padding:14px 0 0">
      <button class="btn" onclick="cerrarModal('modal-srd')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarFechas()">💾 Guardar fechas</button></div>`;
  abrirModal("modal-srd");
}
async function guardarFechas(){
  const body={id:parseInt(document.getElementById("fx_id").value)};
  ["cdp_num","rp_num","contrato_num","invitacion_num","cdp_fecha","invitacion_fecha",
   "cierre_fecha","evaluacion_fecha","contrato_fecha","rp_fecha","acta_inicio_fecha",
   "acta_final_fecha","liquidacion_fecha"].forEach(c=>{
    const e=document.getElementById("fx_"+c);
    if(e&&e.value) body[c]=e.value;
  });
  try{ const r=await post("/legal/rejilla/fechas",body);
    toast(r.msg,!r.ok);
    if(r.problemas&&r.problemas.length) setTimeout(()=>toast("⚠️ "+r.problemas[0],true),1400);
    if(r.ok){ cerrarModal("modal-srd"); abrirProceso(body.id); }
  }catch(e){ toast("Error",true); }
}

/* ── PANEL DE CONFIGURACIÓN INSTITUCIONAL ──
   Cada institución carga SUS datos: su rector, su acta de posesión, su logo.
   Lo que llenen aquí sale en todos los documentos del sistema. */
function pintarPerfilLegal(){
  const d=window._perfilLegal;
  window._cfgArch={};
  const col = d.pct>=100?"var(--green)":d.pct>=60?"var(--gold)":"var(--red)";
  document.getElementById("rj-cont").innerHTML=`
    ${d.es_demo?`<div class="demo-banner">
      <div style="font-size:2.2rem">⚠️</div>
      <div style="flex:1;min-width:220px">
        <b style="font-size:1.05rem">Estos son datos de ejemplo</b>
        <div class="small" style="opacity:.95">El sistema viene con una institución de muestra para que veas cómo funciona. Antes de generar documentos reales, carga los datos de <b>tu</b> institución: tu rector, tu acta de posesión, tu logo.</div>
      </div>
      <button class="btn" style="background:#fff;color:#B45309" onclick="limpiarDemo()">🧹 Empezar de cero</button>
    </div>`:""}
    <div class="card"><div class="card-body">
      <div style="display:flex;gap:16px;align-items:center;flex-wrap:wrap">
        <div class="cfg-anillo" style="background:conic-gradient(${col} ${d.pct*3.6}deg,#E2E8F0 0);position:relative">
          <div style="position:absolute;inset:6px;background:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center">
            <span style="color:${col}">${d.pct}%</span></div></div>
        <div style="flex:1;min-width:210px">
          <b style="font-size:1.05rem">Configuración institucional</b>
          <div class="small muted">${esc(d.aviso)}</div>
          ${d.configurado_por?`<div class="small muted">Configurado por ${esc(d.configurado_por)}${d.fecha_configuracion?" · "+esc(d.fecha_configuracion):""}</div>`:""}
        </div>
        <button class="btn btn-primary" onclick="guardarPerfilLegal()">💾 Guardar todo</button>
      </div>
      <div class="legal-note" style="margin-top:12px">📄 Lo que cargues aquí aparece en <b>cada documento que genere el sistema</b>: el membrete de los contratos, las actas, las invitaciones, los certificados y las cartas. Se llena una sola vez.</div>
    </div></div>
    ${d.secciones.map((s,i)=>`
      <div class="cfg-sec ${s.completa?'lista':''}" id="cfg-${s.id}">
        <div class="cfg-sec-head" onclick="toggleSeccion('${s.id}')">
          <span class="ico">${s.icono}</span>
          <div class="tit"><b>${esc(s.titulo)}</b>
            <div class="small muted">${esc(s.ayuda)}</div></div>
          <div style="text-align:right">
            <div class="cfg-barra"><i style="width:${s.pct}%"></i></div>
            <div class="small muted" style="margin-top:3px">${s.completos}/${s.obligatorios} ${s.completa?"✅":""}</div>
          </div>
          <span id="ar-${s.id}">${s.completa?"▶":"▼"}</span>
        </div>
        <div class="cfg-body" id="cb-${s.id}" style="display:${s.completa?'none':'block'}">
          ${s.campos.map(c=>cfgCampoHTML(c,s.id)).join("")}
          ${s.id==="consejo"?cfgConsejoHTML():""}
        </div>
      </div>`).join("")}
    <div style="text-align:right;margin-top:16px">
      <button class="btn btn-primary btn-lg" onclick="guardarPerfilLegal()">💾 Guardar configuración institucional</button></div>`;
}
function cfgCampoHTML(c, secId){
  const p=window._perfilLegal.perfil;
  const req=c.obligatorio?'<span class="req">*</span>':"";
  if(c.es_archivo){
    const tiene=c.lleno;
    return `<div class="cfg-campo">
      <label>${esc(c.label)} ${req}</label>
      <div class="cfg-drop ${tiene?'tiene':''}" id="dz-${c.clave}" onclick="document.getElementById('f-${c.clave}').click()">
        ${tiene?`✅ Cargado — toca para reemplazar`:`📎 Toca para subir ${c.clave.startsWith("doc_")?"el documento (PDF o imagen)":"la imagen"}`}
      </div>
      <input type="file" id="f-${c.clave}" style="display:none"
        accept="${c.clave.startsWith("doc_")?".pdf,.jpg,.jpeg,.png":"image/*"}"
        onchange="cfgArchivoSel('${c.clave}',this)">
    </div>`;
  }
  const tipo=c.clave.includes("fecha")?"date":(c.clave==="vigencia"?"number":"text");
  const PH={nombre_oficial:"INSTITUCIÓN EDUCATIVA TÉCNICA…",nit:"800123456",nit_dv:"7",
    dane:"213670000200",ordenanza:"020 de Noviembre 29 de 2002",
    decreto:"773 del 10 de octubre de 2003",licencia:"Resolución 149 del 25 de Febrero de 2011",
    rector_nombre:"Nombre completo del rector(a)",rector_cc:"Número de cédula",
    rector_acta_posesion:"Número del acta",consec_cdp:"04",consec_rp:"05",
    pie_pagina:"Fondo de Servicios Educativos — Decreto 1075 de 2015",
    contador_tp:"TP-12345-T",consejo_acta_vigente:"001"};
  const val=(p[c.clave]!=null&&p[c.clave]!==undefined)?p[c.clave]:"";
  return `<div class="cfg-campo">
    <label>${esc(c.label)} ${req}</label>
    <input type="${tipo}" id="pl_${c.clave}" value="${esc(String(val))}"
      placeholder="${esc(PH[c.clave]||"")}">
  </div>`;
}
function cfgConsejoHTML(){
  const m=window._perfilLegal.consejo_miembros||[];
  window._consejo=JSON.parse(JSON.stringify(m));
  return `<div class="fsec">Miembros del Consejo Directivo</div>
    <div class="small muted" style="margin-bottom:7px">Son quienes aprueban el presupuesto y los traslados entre rubros.</div>
    <div id="consejo-lista">${consejoFilasHTML()}</div>
    <button class="btn btn-xs" onclick="window._consejo.push({rol:'',nombre:''});document.getElementById('consejo-lista').innerHTML=consejoFilasHTML()">➕ Agregar miembro</button>
    <button class="btn btn-xs btn-primary" onclick="guardarConsejo()">💾 Guardar consejo</button>`;
}
function consejoFilasHTML(){
  return (window._consejo||[]).map((x,i)=>`
    <div class="mat-fila">
      <input value="${esc(x.rol||"")}" placeholder="Rol (ej: Representante de los docentes)"
        style="flex:1;min-width:150px" oninput="window._consejo[${i}].rol=this.value">
      <input value="${esc(x.nombre||"")}" placeholder="Nombre completo"
        style="flex:1;min-width:140px" oninput="window._consejo[${i}].nombre=this.value">
      <button class="btn btn-xs btn-danger" onclick="window._consejo.splice(${i},1);document.getElementById('consejo-lista').innerHTML=consejoFilasHTML()">✕</button>
    </div>`).join("")||'<div class="small muted">Sin miembros registrados.</div>';
}
async function guardarConsejo(){
  try{ const r=await post("/legal/perfil/consejo",{institucion_id:ST.institucion_id,
      miembros:window._consejo||[]}); toast(r.msg,!r.ok);
  }catch(e){ toast("Error",true); }
}
function toggleSeccion(id){
  const b=document.getElementById("cb-"+id), a=document.getElementById("ar-"+id);
  if(!b) return;
  const abierto=b.style.display!=="none";
  b.style.display=abierto?"none":"block";
  if(a) a.textContent=abierto?"▶":"▼";
}
function cfgArchivoSel(clave, inp){
  const f=inp.files[0]; if(!f) return;
  const max=clave.startsWith("doc_")?2500000:600000;
  if(f.size>max){ toast(`Archivo muy pesado (máx ${Math.round(max/1000000*10)/10} MB)`,true); return; }
  const rd=new FileReader();
  rd.onload=()=>{
    window._cfgArch[clave]=rd.result;
    if(clave==="doc_acta_posesion") window._cfgArch.doc_acta_nombre=f.name;
    const dz=document.getElementById("dz-"+clave);
    if(dz){ dz.classList.add("tiene");
      dz.innerHTML = (clave==="logo_izq"||clave==="rector_firma")
        ? `<img src="${rd.result}" style="max-height:52px"><div class="small">${esc(f.name)}</div>`
        : `✅ ${esc(f.name)} — toca para reemplazar`; }
    toast(`📎 ${f.name} cargado. Recuerda guardar.`);
  };
  rd.readAsDataURL(f);
}
async function guardarPerfilLegal(){
  const body={institucion_id:ST.institucion_id, configurado_por:(ST.perfil.nombre||ST.perfil.titulo)};
  document.querySelectorAll('[id^="pl_"]').forEach(e=>{
    const k=e.id.replace("pl_","");
    if(e.value!=="") body[k]=(k==="vigencia")?(parseInt(e.value)||new Date().getFullYear()):e.value;
  });
  Object.keys(window._cfgArch||{}).forEach(k=>{ body[k]=window._cfgArch[k]; });
  try{ const r=await post("/legal/perfil/guardar",body);
    toast(r.msg,!r.completo);
    if(r.ok) VISTAS.rejilla("perfil");
  }catch(e){ toast("Error al guardar",true); }
}
async function limpiarDemo(){
  if(!confirm("¿Borrar los datos de ejemplo?\n\nQuedará todo en blanco para que cargues la información real de tu institución. Los procesos de la rejilla no se tocan.")) return;
  try{ const r=await post("/legal/perfil/limpiar_demo?institucion_id="+ST.institucion_id,{});
    toast(r.msg,!r.ok); if(r.ok) VISTAS.rejilla("perfil");
  }catch(e){ toast("Error",true); }
}

/* ── Correspondencia: cartas, oficios y derechos de petición ── */
async function pintarCorrespondencia(){
  const [c, m] = await Promise.all([
    api(`/legal/correspondencia?institucion_id=${ST.institucion_id}`),
    api(`/legal/correspondencia/modelos`),
  ]);
  window._corrModelos=m.modelos;
  const r=c.resumen;
  document.getElementById("rj-cont").innerHTML=`
    <div class="kpis">
      <div class="kpi"><div class="kpi-ico">📬</div><div class="kpi-val">${r.total}</div><div class="kpi-lbl">Documentos</div></div>
      <div class="kpi ${r.dp_pendientes?'orange':''}"><div class="kpi-ico">⚖️</div><div class="kpi-val">${r.dp_pendientes}</div><div class="kpi-lbl">DP por responder</div></div>
      <div class="kpi ${r.urgentes?'red':''}"><div class="kpi-ico">⏰</div><div class="kpi-val">${r.urgentes}</div><div class="kpi-lbl">Vencen pronto</div></div>
      <div class="kpi ${r.vencidos?'red':''}"><div class="kpi-ico">🚨</div><div class="kpi-val">${r.vencidos}</div><div class="kpi-lbl">Vencidos</div></div>
    </div>
    <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px">
      ${m.modelos.map(x=>`<button class="btn btn-sm" onclick="nuevaCarta('${x.tipo}')">➕ ${esc(x.asunto)}</button>`).join("")}
      <button class="btn btn-sm" onclick="nuevaCarta('carta')">➕ Carta libre</button>
    </div>
    ${c.correspondencia.map(x=>`
      <div class="carta-card ${x.tipo==='derecho_peticion'?'dp':''} ${x.urgente?'urg':''} ${x.vencido?'venc':''}">
        <div style="display:flex;gap:12px;align-items:flex-start;flex-wrap:wrap">
          <div style="flex:1;min-width:210px">
            <b>${esc(x.tipo_label)} · ${esc(x.asunto)}</b>
            <div class="small muted">Radicado ${esc(x.radicado||"—")} · ${esc(x.fecha||"")}
              ${x.destinatario?" · Para: "+esc(x.destinatario):""}${x.entidad?" ("+esc(x.entidad)+")":""}</div>
            ${x.fecha_limite?`<div class="small" style="color:${x.vencido?'var(--red)':x.urgente?'var(--orange)':'var(--muted)'}">
              ⏰ Término legal: ${esc(x.fecha_limite)}
              ${x.vencido?` — VENCIDO hace ${Math.abs(x.dias_restantes)} días`:x.dias_restantes!=null?` — quedan ${x.dias_restantes} días`:""}</div>`:""}
          </div>
          <div style="display:flex;gap:4px;flex-wrap:wrap;align-items:flex-start">
            <span class="badge ${x.estado==='respondido'?'b-green':x.estado==='enviado'?'b-blue':'b-gray'}">${esc(x.estado)}</span>
            <button class="btn btn-xs btn-primary" onclick="window.open(API+'/legal/correspondencia/ver?id=${x.id}')">👁️ Ver / PDF</button>
            <button class="btn btn-xs" onclick="editarCarta(${x.id})">✎</button>
            ${x.estado!=="respondido"?`<button class="btn btn-xs btn-green" onclick="estadoCarta(${x.id},'respondido')">✓ Respondido</button>`:""}
          </div>
        </div>
      </div>`).join("")||'<div class="empty">Sin correspondencia registrada.</div>'}
    <div class="legal-note">⚖️ Los <b>derechos de petición</b> tienen término legal de 15 días hábiles (Ley 1755 de 2015). El sistema calcula la fecha límite y avisa cuando está por vencerse — responder tarde puede acarrear sanción disciplinaria.</div>`;
}
function nuevaCarta(tipo, existente){
  const mod=(window._corrModelos||[]).find(m=>m.tipo===tipo)||{asunto:"",cuerpo:""};
  const x=existente||{};
  document.getElementById("modal-srd-title").textContent=(x.id?"✎ Editar ":"➕ ")+(mod.asunto||"Carta");
  document.getElementById("modal-srd-body").innerHTML=`
    <input type="hidden" id="ct_id" value="${x.id||""}">
    <input type="hidden" id="ct_tipo" value="${tipo}">
    <div class="frow"><label>Asunto *</label><input id="ct_asunto" value="${esc(x.asunto||mod.asunto||"")}"></div>
    <div class="frow-2">
      <div><label>Destinatario</label><input id="ct_dest" value="${esc(x.destinatario||"")}" placeholder="Nombre completo"></div>
      <div><label>Cargo</label><input id="ct_cargo" value="${esc(x.destinatario_cargo||"")}" placeholder="Secretario de Educación"></div>
    </div>
    <div class="frow"><label>Entidad</label><input id="ct_entidad" value="${esc(x.destinatario_entidad||"")}" placeholder="Gobernación de Bolívar"></div>
    <div class="frow"><label>Fecha</label><input type="date" id="ct_fecha" value="${x.fecha||hoyISO()}"></div>
    <div class="frow"><label>Contenido</label>
      <textarea id="ct_cuerpo" rows="11" style="font-family:ui-monospace,monospace;font-size:.84rem">${esc(x.cuerpo||mod.cuerpo||"")}</textarea>
      <div class="small muted" style="margin-top:4px">Reemplaza lo que está entre corchetes con tu texto. El membrete, la firma y el pie salen automáticos.</div></div>
    ${tipo==="derecho_peticion"?'<div class="legal-note">⚖️ Al guardarlo, el sistema calcula la fecha límite de respuesta (15 días hábiles) y te avisa antes de que se venza.</div>':""}
    <div class="modal-foot" style="border:none;padding:14px 0 0">
      <button class="btn" onclick="cerrarModal('modal-srd')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarCarta()">💾 Guardar</button></div>`;
  abrirModal("modal-srd");
}
async function editarCarta(id){
  try{
    const c=await api(`/legal/correspondencia?institucion_id=${ST.institucion_id}`);
    const x=c.correspondencia.find(y=>y.id===id);
    if(!x) return;
    // traer el cuerpo completo del render
    nuevaCarta(x.tipo, x);
  }catch(e){ toast("Error",true); }
}
async function guardarCarta(){
  const g=id=>{const e=document.getElementById(id);return e?e.value:"";};
  const body={id:parseInt(g("ct_id"))||0, institucion_id:ST.institucion_id,
    tipo:g("ct_tipo"), asunto:g("ct_asunto"), destinatario:g("ct_dest"),
    destinatario_cargo:g("ct_cargo"), destinatario_entidad:g("ct_entidad"),
    cuerpo:g("ct_cuerpo"), fecha:g("ct_fecha"),
    remitente:ST.perfil.nombre||"", creado_por:ST.perfil.titulo};
  if(!body.asunto.trim()){ toast("Escribe el asunto",true); return; }
  try{ const r=await post("/legal/correspondencia/guardar",body);
    toast(r.msg,!r.ok);
    if(r.ok){ cerrarModal("modal-srd"); VISTAS.rejilla("cartas");
      setTimeout(()=>window.open(API+`/legal/correspondencia/ver?id=${r.id}`),700); }
  }catch(e){ toast("Error",true); }
}
async function estadoCarta(id,estado){
  try{ const r=await post("/legal/correspondencia/estado",{id,estado}); toast(r.msg,!r.ok);
    if(r.ok) VISTAS.rejilla("cartas");
  }catch(e){ toast("Error",true); }
}

/* Tarjeta de configuración institucional dentro del perfil del rector */
async function cargarTarjetaInstitucion(){
  const c=document.getElementById("cfg-inst-card");
  if(!c) return;
  try{
    const d=await api(`/legal/perfil?institucion_id=${ST.institucion_id}`);
    const col=d.pct>=100?"var(--green)":d.pct>=60?"var(--gold)":"var(--red)";
    c.querySelector(".card-body").innerHTML=`
      ${d.es_demo?`<div class="legal-note" style="background:#FEF3C7;border-color:var(--gold)">
        ⚠️ <b>Todavía están los datos de ejemplo.</b> Carga los de tu institución: tu acta de posesión, tu logo y los actos de creación. Todo eso sale en los contratos y las actas que firmes.</div>`:""}
      <div style="display:flex;gap:16px;align-items:center;flex-wrap:wrap">
        <div class="cfg-anillo" style="background:conic-gradient(${col} ${d.pct*3.6}deg,#E2E8F0 0);position:relative">
          <div style="position:absolute;inset:6px;background:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center">
            <span style="color:${col};font-size:.9rem">${d.pct}%</span></div></div>
        <div style="flex:1;min-width:200px">
          <b>${esc(d.perfil.nombre_oficial||"Sin configurar")}</b>
          <div class="small muted">${d.perfil.nit?"NIT "+esc(d.perfil.nit):""}${d.perfil.dane?" · DANE "+esc(d.perfil.dane):""}</div>
          ${d.faltantes.length?`<div class="small" style="color:var(--orange);margin-top:4px">
            Falta: ${d.faltantes.slice(0,3).map(x=>esc(x)).join(", ")}${d.faltantes.length>3?` y ${d.faltantes.length-3} más`:""}</div>`
            :'<div class="small" style="color:var(--green);margin-top:4px">✅ Todo listo para generar documentos oficiales</div>'}
        </div>
        <button class="btn btn-primary" onclick="irVista('rejilla');setTimeout(()=>VISTAS.rejilla('perfil'),80)">
          ${d.pct>=100?"⚙️ Revisar":"📝 Completar ahora"}</button>
      </div>
      <div style="display:flex;gap:5px;flex-wrap:wrap;margin-top:12px">
        ${d.secciones.map(s=>`<span class="doc-pill ${s.completa?'ok':'no'}"
          onclick="irVista('rejilla');setTimeout(()=>VISTAS.rejilla('perfil'),80)">
          ${s.icono} ${esc(s.titulo.split(" ")[0])} ${s.completa?"✓":s.completos+"/"+s.obligatorios}</span>`).join("")}
      </div>`;
  }catch(e){ c.querySelector(".card-body").innerHTML='<div class="small muted">No disponible.</div>'; }
}

/* ═══════════════════════════════════════════════════════════════════
   V10 · MÓVIL: menú lateral, notificaciones push y clase en vivo real
   ═══════════════════════════════════════════════════════════════════ */
function toggleMenu(){
  const s=document.querySelector(".sidebar"), o=document.getElementById("overlay-menu");
  if(!s) return;
  const abierta=s.classList.toggle("abierta");
  if(o) o.classList.toggle("on", abierta);
}
function cerrarMenuMovil(){
  const s=document.querySelector(".sidebar"), o=document.getElementById("overlay-menu");
  if(s) s.classList.remove("abierta");
  if(o) o.classList.remove("on");
}

/* ── Notificaciones push ── */
const PUSH={permiso:"default", timer:null, vistos:new Set()};
async function activarPush(){
  if(!("Notification" in window)){ toast("Este navegador no soporta notificaciones",true); return; }
  try{
    const p=await Notification.requestPermission();
    PUSH.permiso=p;
    if(p==="granted"){
      toast("🔔 Notificaciones activadas. Te avisaremos de lo importante aunque tengas la app cerrada.");
      notificar("GyverLabs","Listo, aquí te avisaremos de tus pendientes.");
      iniciarPush();
    } else toast("No activaste las notificaciones. Puedes hacerlo después desde tu perfil.",true);
  }catch(e){ toast("No se pudo activar",true); }
}
function notificar(titulo, cuerpo, tag){
  if(PUSH.permiso!=="granted") return;
  try{
    const n=new Notification(titulo,{body:cuerpo, tag:tag||"gv", badge:"/favicon.ico",
      icon:"/favicon.ico", vibrate:[120,60,120]});
    n.onclick=()=>{ window.focus(); n.close(); };
  }catch(e){}
}
function iniciarPush(){
  if(PUSH.timer) clearInterval(PUSH.timer);
  PUSH.timer=setInterval(revisarPendientes, 90000);
  revisarPendientes();
}
async function revisarPendientes(){
  if(PUSH.permiso!=="granted") return;
  try{
    if(ST.estudiante_id){
      const d=await api(`/alumno/mis_alertas?estudiante_id=${ST.estudiante_id}`);
      (d.alertas||[]).filter(a=>a.nivel==="critico").slice(0,2).forEach(a=>{
        const k="al-"+a.titulo;
        if(!PUSH.vistos.has(k)){ PUSH.vistos.add(k); notificar(a.icono+" "+a.titulo, a.detalle, k); }
      });
    } else if(ST.institucion_id && ST.perfil.personal_id){
      const d=await api(`/vivo/estado?institucion_id=${ST.institucion_id}&version=${VIVO.version||0}`);
      if(d.hay_cambio && d.ultimo){
        const k="v-"+d.version;
        if(!PUSH.vistos.has(k)){ PUSH.vistos.add(k);
          notificar("🔔 "+(d.ultimo.tipo||"Novedad"), d.ultimo.detalle||"Hay cambios en tu institución", k); }
      }
    }
  }catch(e){}
}

/* ═══ CLASE EN VIVO con cámara y micrófono ═══ */
const VC={stream:null, video:true, audio:true, pantalla:null, sala:null, timer:null};

async function entrarSalaVivo(salaId){
  loading();
  try{
    const d=await api(`/salas/detalle?id=${salaId}`).catch(()=>null) ||
            {titulo:"Clase en vivo", id:salaId};
    VC.sala=salaId;
    const esDocente=!!ST.perfil.personal_id;
    main(`<div style="display:flex;gap:10px;align-items:center;margin-bottom:12px;flex-wrap:wrap">
        <button class="btn btn-sm" onclick="salirSalaVivo()">← Salir</button>
        <h2 style="margin:0;font-size:1.15rem">🎥 ${esc(d.titulo||"Clase en vivo")}</h2>
        <span class="badge b-red" style="margin-left:auto"><span class="vivo-dot"></span>EN VIVO</span></div>
      <div id="vc-alerta"></div>
      <div class="vc-grid" id="vc-grid">
        <div class="vc-tile yo" id="vc-yo">
          <video id="vc-video-yo" autoplay muted playsinline></video>
          <div class="vc-ph" id="vc-ph-yo">
            <div class="vc-avatar">${ini(ST.perfil.nombre||"Yo")}</div>
            <div class="small">Cámara apagada</div></div>
          <span class="nom">${esc((ST.perfil.nombre||"Tú").split(" ")[0])} (tú)</span>
          <div class="ind"><span id="vc-ind-mic">🎤</span><span id="vc-ind-cam">📷</span></div>
        </div>
        ${[["Docente","🧑‍🏫"],["Ana M.","🎒"],["Carlos P.","🎒"]].map((x,i)=>`
          <div class="vc-tile">
            <div class="vc-ph"><div class="vc-avatar">${ini(x[0])}</div>
              <div class="small">${i===0?"Conectando…":"Cámara apagada"}</div></div>
            <span class="nom">${x[1]} ${esc(x[0])}</span>
            <div class="ind"><span>${i===0?"🎤":"🔇"}</span></div>
          </div>`).join("")}
      </div>
      <div class="vc-barra">
        <button class="vc-btn" id="vc-b-mic" onclick="vcToggleAudio()" title="Micrófono">🎤</button>
        <button class="vc-btn" id="vc-b-cam" onclick="vcToggleVideo()" title="Cámara">📷</button>
        <button class="vc-btn" id="vc-b-pant" onclick="vcCompartirPantalla()" title="Compartir pantalla">🖥️</button>
        <button class="vc-btn" onclick="vcLevantarMano()" title="Levantar la mano">✋</button>
        ${esDocente?`<button class="vc-btn" id="vc-b-grabar" onclick="vcGrabar()" title="Grabar">⏺️</button>`:""}
        <button class="vc-btn colgar" onclick="salirSalaVivo()" title="Salir">📞</button>
      </div>
      <div class="card"><div class="card-head"><h3>💬 Chat de la clase</h3></div>
        <div class="chat-box" id="vc-chat">
          <div class="chat-msg doc"><div class="bub"><div class="aut">🧑‍🏫 Docente</div>
            Bienvenidos. Recuerden activar el micrófono solo para participar.</div></div>
        </div>
        <div style="display:flex;gap:8px;padding:10px">
          <input id="vc-msg" placeholder="Escribe un mensaje…" style="flex:1"
            onkeyup="if(event.key==='Enter')vcEnviarChat()">
          <button class="btn btn-sm btn-primary" onclick="vcEnviarChat()">Enviar</button></div>
      </div>
      <div class="legal-note">🎥 La cámara y el micrófono salen de tu dispositivo. Si estás en zona con poca señal, apaga la cámara y deja solo el audio: consume mucho menos datos.</div>`);
    await vcIniciarMedios();
  }catch(e){ main(`<div class="empty">Error</div>`); }
}
async function vcIniciarMedios(){
  const al=document.getElementById("vc-alerta");
  if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){
    if(al) al.innerHTML='<div class="vc-alerta">⚠️ Este navegador no permite usar la cámara. Prueba con Chrome o Firefox actualizado.</div>';
    return;
  }
  try{
    VC.stream=await navigator.mediaDevices.getUserMedia({
      video:{width:{ideal:640},height:{ideal:480},facingMode:"user"},
      audio:{echoCancellation:true,noiseSuppression:true}});
    const v=document.getElementById("vc-video-yo");
    if(v){ v.srcObject=VC.stream; v.style.display="block"; }
    const ph=document.getElementById("vc-ph-yo");
    if(ph) ph.style.display="none";
    toast("🎥 Cámara y micrófono conectados.");
    vcDetectarVoz();
  }catch(err){
    let msg="No se pudo acceder a la cámara.";
    if(err.name==="NotAllowedError") msg="Bloqueaste el permiso de cámara y micrófono. Actívalo en el candado 🔒 de la barra de direcciones.";
    else if(err.name==="NotFoundError") msg="No se detectó cámara ni micrófono en este dispositivo. Puedes seguir por el chat.";
    else if(err.name==="NotReadableError") msg="Otra aplicación está usando la cámara. Ciérrala e intenta de nuevo.";
    if(al) al.innerHTML=`<div class="vc-alerta">⚠️ ${esc(msg)}</div>`;
    const v=document.getElementById("vc-video-yo");
    if(v) v.style.display="none";
  }
}
function vcToggleAudio(){
  if(!VC.stream){ toast("Primero permite el acceso al micrófono",true); return; }
  VC.audio=!VC.audio;
  VC.stream.getAudioTracks().forEach(t=>t.enabled=VC.audio);
  const b=document.getElementById("vc-b-mic"), i=document.getElementById("vc-ind-mic");
  if(b){ b.classList.toggle("off",!VC.audio); b.textContent=VC.audio?"🎤":"🔇"; }
  if(i) i.textContent=VC.audio?"🎤":"🔇";
  toast(VC.audio?"🎤 Micrófono activado":"🔇 Micrófono silenciado");
}
function vcToggleVideo(){
  if(!VC.stream){ toast("Primero permite el acceso a la cámara",true); return; }
  VC.video=!VC.video;
  VC.stream.getVideoTracks().forEach(t=>t.enabled=VC.video);
  const b=document.getElementById("vc-b-cam"), i=document.getElementById("vc-ind-cam");
  const v=document.getElementById("vc-video-yo"), ph=document.getElementById("vc-ph-yo");
  if(b){ b.classList.toggle("off",!VC.video); b.textContent=VC.video?"📷":"🚫"; }
  if(i) i.textContent=VC.video?"📷":"🚫";
  if(v) v.style.display=VC.video?"block":"none";
  if(ph) ph.style.display=VC.video?"none":"flex";
  toast(VC.video?"📷 Cámara activada":"📷 Cámara apagada — sigues escuchando y hablando");
}
async function vcCompartirPantalla(){
  if(!navigator.mediaDevices||!navigator.mediaDevices.getDisplayMedia){
    toast("Este dispositivo no permite compartir pantalla",true); return; }
  try{
    if(VC.pantalla){
      VC.pantalla.getTracks().forEach(t=>t.stop());
      VC.pantalla=null;
      const v=document.getElementById("vc-video-yo");
      if(v&&VC.stream) v.srcObject=VC.stream;
      document.getElementById("vc-b-pant").classList.remove("off");
      toast("Dejaste de compartir la pantalla");
      return;
    }
    VC.pantalla=await navigator.mediaDevices.getDisplayMedia({video:true});
    const v=document.getElementById("vc-video-yo");
    if(v){ v.srcObject=VC.pantalla; v.style.display="block"; }
    const ph=document.getElementById("vc-ph-yo");
    if(ph) ph.style.display="none";
    document.getElementById("vc-b-pant").classList.add("off");
    VC.pantalla.getVideoTracks()[0].onended=()=>{ VC.pantalla=null;
      if(v&&VC.stream) v.srcObject=VC.stream;
      document.getElementById("vc-b-pant").classList.remove("off"); };
    toast("🖥️ Compartiendo tu pantalla");
  }catch(e){ toast("No se compartió la pantalla",true); }
}
function vcDetectarVoz(){
  if(!VC.stream||!window.AudioContext) return;
  try{
    const ctx=new AudioContext();
    const src=ctx.createMediaStreamSource(VC.stream);
    const an=ctx.createAnalyser();
    an.fftSize=512;
    src.connect(an);
    const buf=new Uint8Array(an.frequencyBinCount);
    const tile=document.getElementById("vc-yo");
    VC.timer=setInterval(()=>{
      if(!tile||!VC.audio){ if(tile) tile.classList.remove("vc-hablando"); return; }
      an.getByteFrequencyData(buf);
      const vol=buf.reduce((a,b)=>a+b,0)/buf.length;
      tile.classList.toggle("vc-hablando", vol>22);
    },220);
  }catch(e){}
}
function vcLevantarMano(){
  toast("✋ Levantaste la mano. El docente lo ve en su pantalla.");
  const c=document.getElementById("vc-chat");
  if(c){ c.innerHTML+=`<div class="chat-msg"><div class="bub"><div class="aut">✋ ${esc(ST.perfil.nombre||"Tú")}</div>
    levantó la mano</div></div>`; c.scrollTop=c.scrollHeight; }
}
function vcGrabar(){
  const b=document.getElementById("vc-b-grabar");
  const grabando=b&&b.classList.toggle("off");
  toast(grabando?"⏺️ Grabando. Al terminar, la clase queda en la biblioteca para quien no pudo conectarse."
                :"⏹️ Grabación detenida y guardada en la biblioteca.");
}
function vcEnviarChat(){
  const i=document.getElementById("vc-msg");
  if(!i||!i.value.trim()) return;
  const c=document.getElementById("vc-chat");
  if(c){ c.innerHTML+=`<div class="chat-msg"><div class="bub"><div class="aut">${esc(ST.perfil.nombre||"Tú")}</div>${esc(i.value)}</div></div>`;
    c.scrollTop=c.scrollHeight; }
  i.value="";
}
function salirSalaVivo(){
  if(VC.stream) VC.stream.getTracks().forEach(t=>t.stop());
  if(VC.pantalla) VC.pantalla.getTracks().forEach(t=>t.stop());
  if(VC.timer) clearInterval(VC.timer);
  VC.stream=null; VC.pantalla=null; VC.timer=null;
  toast("Saliste de la clase");
  irVista(ST.estudiante_id?"alsalas":"salas");
}

/* ═══════════════════════════════════════════════════════════════════
   V10 · PLANEACIÓN (en el perfil del docente), SIMAT y CERTIFICADOS
   ═══════════════════════════════════════════════════════════════════ */
VISTAS.planeacion = async function(estado){
  loading();
  try{
    const esDocente = ST.perfil.rol==="docente";
    const q = esDocente ? `&personal_id=${ST.perfil.personal_id}` : (estado?`&estado=${estado}`:"");
    const d = await api(`/secretaria/planeacion?institucion_id=${ST.institucion_id}${q}`);
    window._planes = d.planeaciones;
    const r=d.resumen;
    main(head(esDocente?"Mi planeación":"Planeación de los docentes",
      esDocente?"Arma tu plan aquí mismo y envíalo a coordinación — no hace falta ningún Drive"
               :"Lo que los docentes enviaron para tu revisión",
      esDocente?`<button class="btn btn-primary" onclick="editarPlan(0)">➕ Nueva planeación</button>`:"")+`
      <div class="kpis">
        <div class="kpi ${r.por_revisar?'orange':''}"><div class="kpi-ico">📤</div><div class="kpi-val">${r.por_revisar}</div><div class="kpi-lbl">Por revisar</div></div>
        <div class="kpi green"><div class="kpi-ico">✅</div><div class="kpi-val">${r.aprobadas}</div><div class="kpi-lbl">Aprobadas</div></div>
        <div class="kpi ${r.con_ajustes?'red':''}"><div class="kpi-ico">📝</div><div class="kpi-val">${r.con_ajustes}</div><div class="kpi-lbl">Con ajustes</div></div>
        <div class="kpi"><div class="kpi-ico">📄</div><div class="kpi-val">${r.borradores}</div><div class="kpi-lbl">Borradores</div></div>
      </div>
      ${!esDocente?`<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">
        ${[["","Todas"],["enviada","📤 Por revisar"],["aprobada","✅ Aprobadas"],["ajustes","📝 Con ajustes"]].map(([k,l])=>
          `<button class="chip-filtro ${(estado||"")===k?'active':''}" onclick="VISTAS.planeacion('${k}')">${l}</button>`).join("")}
      </div>`:""}
      ${d.planeaciones.map(p=>`
        <div class="card"><div class="card-body">
          <div style="display:flex;gap:12px;align-items:flex-start;flex-wrap:wrap">
            <div style="flex:1;min-width:210px">
              <b>${esc(p.titulo)}</b>
              ${p.generado_ia?'<span class="badge b-purple">🤖 con IA</span>':""}
              <div class="small muted">${esc(p.materia||"")} · Salón ${esc(p.salon)} ·
                ${esc(p.tipo)} · ${p.n_semanas} semana(s)${p.n_materiales?" · 📎 "+p.n_materiales:""}</div>
              ${!esDocente?`<div class="small muted">👨‍🏫 ${esc(p.docente)}</div>`:""}
              <div class="small muted">${p.desde?esc(p.desde)+" → "+esc(p.hasta||""):""}
                ${p.fecha_envio?" · enviada "+esc(p.fecha_envio):""}</div>
              ${p.observacion?`<div class="small" style="margin-top:6px;padding:8px 11px;border-radius:8px;
                background:${p.estado==='aprobada'?'#DCFCE7':'#FEF3C7'}">
                ${p.estado==='aprobada'?"✅":"📝"} <b>${esc(p.revisor||"Coordinación")}:</b> ${esc(p.observacion)}</div>`:""}
            </div>
            <div style="display:flex;gap:5px;flex-direction:column;align-items:flex-end">
              <span class="badge ${p.estado==='aprobada'?'b-green':p.estado==='enviada'?'b-blue':p.estado==='ajustes'?'b-orange':'b-gray'}">${esc(p.estado)}</span>
              <div style="display:flex;gap:4px;flex-wrap:wrap;justify-content:flex-end">
                <button class="btn btn-xs" onclick="verPlan(${p.id})">👁️</button>
                <button class="btn btn-xs" onclick="window.open(API+'/secretaria/planeacion/imprimir?id=${p.id}')">🖨️</button>
                ${esDocente&&p.estado!=="aprobada"?`<button class="btn btn-xs btn-primary" onclick="editarPlan(${p.id})">✎</button>`:""}
                ${!esDocente&&p.estado==="enviada"?`
                  <button class="btn btn-xs btn-green" onclick="revisarPlan(${p.id},'aprobada')">✅</button>
                  <button class="btn btn-xs btn-gold" onclick="revisarPlan(${p.id},'ajustes')">📝</button>`:""}
              </div>
            </div>
          </div></div></div>`).join("")||`<div class="empty">${esDocente?"No has creado planeaciones. Usa ➕ Nueva planeación.":"No hay planeaciones para revisar."}</div>`}
      <div class="legal-note">📋 ${esDocente
        ?"Tu planeación se guarda aquí, no en un Drive aparte. Coordinación la ve, la aprueba o te pide ajustes, y todo queda registrado con fecha."
        :"Aquí llegan las planeaciones de los docentes. Al aprobar o pedir ajustes, el docente ve tu observación en su perfil de inmediato."}</div>`);
  }catch(e){ main(`<div class="empty">Error</div>`); }
};
let PLN=null;
async function editarPlan(id){
  loading();
  try{
    if(!window._misSalones) window._misSalones=await api(`/academico/salones?institucion_id=${ST.institucion_id}`);
    if(id){
      const d=await api(`/secretaria/planeacion/detalle?id=${id}`);
      if(!d.ok||!d.editable){ toast(d.editable===false?"Esta planeación ya está aprobada":"Error",true); return; }
      PLN={...d, id};
    } else {
      PLN={id:0, titulo:"", materia:"", tipo:"semanal", salon_id:(window._misSalones[0]||{}).id,
           periodo_numero:3, corte:"", desde:hoyISO(), hasta:"", objetivos:[""],
           contenidos:[{semana:1,tema:"",actividades:"",recursos:""}],
           metodologia:"", evaluacion:"", materiales:[]};
    }
    pintarEditorPlan();
  }catch(e){ toast("Error",true); }
}
function pintarEditorPlan(){
  const sal=window._misSalones||[];
  main(`<div style="display:flex;gap:10px;align-items:center;margin-bottom:14px;flex-wrap:wrap">
      <button class="btn btn-sm" onclick="VISTAS.planeacion()">← Mis planeaciones</button>
      <h2 style="margin:0;font-size:1.15rem">${PLN.id?"✎ Editar":"➕ Nueva"} planeación</h2></div>
    <div class="card"><div class="card-body">
      <div class="frow"><label>Título *</label>
        <input value="${esc(PLN.titulo||"")}" placeholder="Plan semanal — Fracciones" oninput="PLN.titulo=this.value"></div>
      <div class="frow-3">
        <div><label>Tipo</label><select onchange="PLN.tipo=this.value">
          ${[["semanal","📅 Semanal"],["mensual","🗓️ Mensual"],["periodo","📚 Todo el período"]].map(([v,l])=>
            `<option value="${v}" ${PLN.tipo===v?"selected":""}>${l}</option>`).join("")}</select></div>
        <div><label>Materia</label><input value="${esc(PLN.materia||"")}" oninput="PLN.materia=this.value"></div>
        <div><label>Salón</label><select onchange="PLN.salon_id=parseInt(this.value)">
          ${sal.map(s=>`<option value="${s.id}" ${PLN.salon_id===s.id?"selected":""}>${esc(s.nombre)}</option>`).join("")}</select></div>
      </div>
      <div class="frow-3">
        <div><label>Período</label><select onchange="PLN.periodo_numero=parseInt(this.value)">
          ${[1,2,3,4].map(p=>`<option value="${p}" ${PLN.periodo_numero===p?"selected":""}>Período ${p}</option>`).join("")}</select></div>
        <div><label>Desde</label><input type="date" value="${PLN.desde||""}" oninput="PLN.desde=this.value"></div>
        <div><label>Hasta</label><input type="date" value="${PLN.hasta||""}" oninput="PLN.hasta=this.value"></div>
      </div>
      <div class="fsec">🎯 Objetivos de aprendizaje</div>
      ${(PLN.objetivos||[]).map((o,i)=>`<div style="display:flex;gap:6px;margin-bottom:5px">
        <input value="${esc(o)}" placeholder="Objetivo ${i+1}" style="flex:1" oninput="PLN.objetivos[${i}]=this.value">
        <button class="btn btn-xs btn-danger" onclick="PLN.objetivos.splice(${i},1);pintarEditorPlan()">✕</button></div>`).join("")}
      <button class="btn btn-xs" onclick="PLN.objetivos.push('');pintarEditorPlan()">➕ Objetivo</button>
      <div class="fsec">📅 Desarrollo por semana</div>
      ${(PLN.contenidos||[]).map((c,i)=>`
        <div style="border:1px solid var(--border);border-radius:10px;padding:11px;margin-bottom:8px">
          <div style="display:flex;gap:6px;align-items:center;margin-bottom:6px">
            <b class="small">Semana</b>
            <input type="number" value="${c.semana||i+1}" style="width:64px" oninput="PLN.contenidos[${i}].semana=parseInt(this.value)||1">
            <input value="${esc(c.tema||"")}" placeholder="Tema" style="flex:1" oninput="PLN.contenidos[${i}].tema=this.value">
            <button class="btn btn-xs btn-danger" onclick="PLN.contenidos.splice(${i},1);pintarEditorPlan()">✕</button>
          </div>
          <textarea rows="2" placeholder="Actividades que se van a desarrollar" oninput="PLN.contenidos[${i}].actividades=this.value">${esc(c.actividades||"")}</textarea>
          <input value="${esc(c.recursos||"")}" placeholder="Recursos (guía, video, material concreto…)" style="margin-top:5px" oninput="PLN.contenidos[${i}].recursos=this.value">
        </div>`).join("")}
      <button class="btn btn-sm" onclick="PLN.contenidos.push({semana:PLN.contenidos.length+1,tema:'',actividades:'',recursos:''});pintarEditorPlan()">➕ Agregar semana</button>
      <button class="btn btn-sm btn-gold" onclick="planConIA()">🤖 Que la IA me la arme</button>
      <div class="fsec">📖 Metodología</div>
      <textarea rows="3" placeholder="Cómo vas a desarrollar la clase…" oninput="PLN.metodologia=this.value">${esc(PLN.metodologia||"")}</textarea>
      <div class="fsec">📊 Evaluación</div>
      <textarea rows="3" placeholder="Cómo vas a evaluar y con qué porcentajes…" oninput="PLN.evaluacion=this.value">${esc(PLN.evaluacion||"")}</textarea>
      <div class="fsec">📎 Material anexo</div>
      <div id="pln-mats">${(PLN.materiales||[]).map((m,i)=>`<span class="mat-chip">${MAT_ICO[m.tipo]||"📎"} ${esc(m.nombre)}
        <a href="#" onclick="PLN.materiales.splice(${i},1);pintarEditorPlan();return false">✕</a></span>`).join("")||'<span class="small muted">Sin anexos</span>'}</div>
      <button class="btn btn-sm" style="margin-top:6px" onclick="document.getElementById('pln-file').click()">📎 Anexar guía o taller</button>
      <input type="file" id="pln-file" style="display:none" multiple onchange="plnArchivos(this)">
      <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:18px;flex-wrap:wrap">
        <button class="btn" onclick="guardarPlan(false)">💾 Guardar borrador</button>
        <button class="btn btn-primary" onclick="guardarPlan(true)">📤 Enviar a coordinación</button></div>
    </div></div>`);
}
function plnArchivos(inp){
  Array.from(inp.files).slice(0,8).forEach(f=>{
    if(!PLN.materiales) PLN.materiales=[];
    if(!PLN.materiales.find(m=>m.nombre===f.name))
      PLN.materiales.push({tipo:tipoDeArchivo(f.name), nombre:f.name, tamano:tamanoLegible(f.size)});
  });
  inp.value=""; pintarEditorPlan();
}
async function planConIA(){
  if(!PLN.materia||!PLN.titulo){ toast("Escribe primero el título y la materia",true); return; }
  const n=parseInt(prompt("¿Cuántas semanas quieres planear?","4"))||4;
  const tema=prompt("¿Sobre qué tema general?", PLN.titulo.replace(/^Plan \w+ — /,""))||PLN.titulo;
  toast("🤖 Armando tu planeación…");
  try{
    const r=await post("/clases/generar_ia",{salon_id:PLN.salon_id, materia:PLN.materia,
      tema, duracion_min:45, n_temas:n});
    if(!r.ok){ toast(r.msg,true); return; }
    PLN.objetivos=r.propuesta.objetivos;
    PLN.contenidos=r.propuesta.temas.map((t,i)=>({semana:i+1, tema:t.titulo,
      actividades:(t.contenido||[]).map(b=>b.h).filter(Boolean).join(" · ')").slice(0,300)||t.resumen,
      recursos:"Guía impresa, tablero"}));
    PLN.metodologia=PLN.metodologia||"Aprendizaje activo con ejemplos del contexto local, trabajo en parejas y socialización.";
    PLN.evaluacion=PLN.evaluacion||"Participación 20%, talleres 30%, evaluación 40%, autoevaluación 10%.";
    PLN.generado_ia=true;
    pintarEditorPlan();
    toast(`🤖 Listo: ${n} semanas planeadas. Revísalas y ajusta lo que quieras.`);
  }catch(e){ toast("Error",true); }
}
async function guardarPlan(enviar){
  const body={...PLN, institucion_id:ST.institucion_id, personal_id:ST.perfil.personal_id,
    objetivos:(PLN.objetivos||[]).filter(o=>o.trim()),
    contenidos:(PLN.contenidos||[]).filter(c=>c.tema||c.actividades), enviar};
  if(!body.titulo||!body.titulo.trim()){ toast("Ponle un título",true); return; }
  try{ const r=await post("/secretaria/planeacion/guardar",body);
    toast(r.msg,!r.ok); if(r.ok) VISTAS.planeacion();
  }catch(e){ toast("Error",true); }
}
async function verPlan(id){
  try{
    const d=await api(`/secretaria/planeacion/detalle?id=${id}`);
    if(!d.ok) return;
    document.getElementById("modal-srd-title").textContent="📋 "+d.titulo;
    document.getElementById("modal-srd-body").innerHTML=`
      <div class="info-grid">
        <div class="info-it"><span class="k">Docente</span><b>${esc(d.docente)}</b></div>
        <div class="info-it"><span class="k">Materia</span><b>${esc(d.materia||"—")}</b></div>
        <div class="info-it"><span class="k">Salón</span><b>${esc(d.salon||"—")}</b></div>
        <div class="info-it"><span class="k">Vigencia</span><b>${esc(d.desde||"")} → ${esc(d.hasta||"")}</b></div>
      </div>
      ${d.objetivos.length?`<div class="fsec">🎯 Objetivos</div><ol style="line-height:1.7">${d.objetivos.map(o=>`<li>${esc(o)}</li>`).join("")}</ol>`:""}
      <div class="fsec">📅 Desarrollo</div>
      <div class="tbl-scroll"><table><thead><tr><th>Sem.</th><th>Tema</th><th>Actividades</th><th>Recursos</th></tr></thead>
        <tbody>${d.contenidos.map(c=>`<tr><td style="text-align:center">${c.semana||""}</td>
          <td><b>${esc(c.tema||"")}</b></td><td class="small">${esc(c.actividades||"")}</td>
          <td class="small">${esc(c.recursos||"")}</td></tr>`).join("")}</tbody></table></div>
      ${d.metodologia?`<div class="fsec">📖 Metodología</div><p class="small">${esc(d.metodologia)}</p>`:""}
      ${d.evaluacion?`<div class="fsec">📊 Evaluación</div><p class="small">${esc(d.evaluacion)}</p>`:""}
      ${d.materiales.length?`<div class="fsec">📎 Anexos</div><div>${d.materiales.map(m=>`<span class="mat-chip">${MAT_ICO[m.tipo]||"📎"} ${esc(m.nombre)}</span>`).join("")}</div>`:""}
      ${d.observacion?`<div class="legal-note" style="background:${d.estado==='aprobada'?'#DCFCE7':'#FEF3C7'}">
        <b>${esc(d.revisor||"Coordinación")}:</b> ${esc(d.observacion)}</div>`:""}
      <div class="modal-foot" style="border:none;padding:14px 0 0">
        <button class="btn" onclick="window.open(API+'/secretaria/planeacion/imprimir?id=${id}')">🖨️ Imprimir</button>
        <button class="btn" onclick="cerrarModal('modal-srd')">Cerrar</button>
        ${d.estado==="enviada"&&ST.perfil.rol!=="docente"?`
          <button class="btn btn-gold" onclick="cerrarModal('modal-srd');revisarPlan(${id},'ajustes')">📝 Pedir ajustes</button>
          <button class="btn btn-green" onclick="cerrarModal('modal-srd');revisarPlan(${id},'aprobada')">✅ Aprobar</button>`:""}
      </div>`;
    abrirModal("modal-srd");
  }catch(e){ toast("Error",true); }
}
async function revisarPlan(id, estado){
  const obs=prompt(estado==="aprobada"?"Observación para el docente (opcional):"
                   :"¿Qué debe ajustar el docente? (obligatorio)");
  if(obs===null) return;
  if(estado!=="aprobada"&&!obs.trim()){ toast("Escribe qué debe ajustar",true); return; }
  try{ const r=await post("/secretaria/planeacion/revisar",{id,estado,observacion:obs,
      revisor:(ST.perfil.nombre||ST.perfil.titulo)});
    toast(r.msg,!r.ok); if(r.ok) VISTAS.planeacion();
  }catch(e){ toast("Error",true); }
}

/* ═══ CERTIFICADOS: el alumno los pide y los descarga ═══ */
VISTAS.alcertificados = async function(){
  loading();
  try{
    const [t, c, h] = await Promise.all([
      api(`/secretaria/certificados/tipos`),
      api(`/secretaria/certificados?estudiante_id=${ST.estudiante_id}`),
      api(`/secretaria/historico?estudiante_id=${ST.estudiante_id}`),
    ]);
    main(head("Mis certificados","Pídelos desde aquí y descárgalos cuando estén listos — sin ir al colegio")+`
      <div class="grid-cards">
        ${t.tipos.map(x=>`
          <div class="va-card" style="cursor:pointer" onclick="pedirCertificado('${x.id}','${esc(x.label)}')">
            <div style="font-size:1.9rem">${x.label.split(" ")[0]}</div>
            <h4>${esc(x.label.substring(2))}</h4>
            <div class="small muted">${esc(x.desc)}</div>
            <button class="btn btn-sm btn-primary" style="width:100%;margin-top:10px">📨 Solicitar</button>
          </div>`).join("")}
      </div>
      <div class="card"><div class="card-head"><h3>📋 Mis solicitudes</h3></div><div class="card-body">
        ${c.certificados.map(x=>`
          <div class="mat-fila">
            <span style="font-size:1.15rem">${x.estado==="solicitado"?"⏳":"✅"}</span>
            <div class="nom"><b>${esc(x.tipo_label)}</b>
              <div class="small muted">${esc(x.numero||"")} · pedido ${esc(x.solicitado||"")}
                ${x.emitido?" · emitido "+esc(x.emitido):""}
                ${x.codigo?" · código "+esc(x.codigo):""}</div></div>
            ${x.estado==="solicitado"
              ?'<span class="badge b-orange">En trámite</span>'
              :`<button class="btn btn-xs btn-primary" onclick="window.open(API+'/secretaria/certificados/ver?id=${x.id}')">⬇️ Descargar</button>`}
          </div>`).join("")||'<div class="small muted">No has pedido certificados.</div>'}
      </div></div>
      ${h.ok&&h.n_anios?`<div class="card"><div class="card-head"><h3>📚 Mi historial académico</h3>
        <span class="small muted">${esc(h.origen)}</span></div>
        <div class="card-body">
        ${h.anios.map(a=>`
          <div style="margin-bottom:14px">
            <b>Año ${a.anio}${a.grado?" · grado "+esc(a.grado):""}</b>
            <span class="badge ${a.promedio>=3.5?'b-green':a.promedio>=3?'b-blue':'b-orange'}">Promedio ${a.promedio}</span>
            ${a.perdidas?`<span class="badge b-red">${a.perdidas} perdida(s)</span>`:""}
            ${a.fallas?`<span class="badge b-gray">${a.fallas} fallas</span>`:""}
            <div class="tbl-scroll" style="margin-top:6px"><table><thead><tr><th>Materia</th>
              ${[1,2,3,4].map(p=>`<th style="text-align:center">P${p}</th>`).join("")}
              <th style="text-align:center">Def.</th></tr></thead>
              <tbody>${a.materias.map(m=>`<tr><td class="small">${esc(m.materia)}</td>
                ${[1,2,3,4].map(p=>`<td style="text-align:center">${m.periodos[p]!=null?m.periodos[p]:"—"}</td>`).join("")}
                <td style="text-align:center"><b style="color:${(m.definitiva||0)>=3?'var(--green)':'var(--red)'}">${m.definitiva!=null?m.definitiva:"—"}</b></td>
              </tr>`).join("")}</tbody></table></div>
          </div>`).join("")}
        </div></div>`:""}
      <div class="legal-note">📄 Los certificados salen con el membrete de tu institución, la firma del rector y un código de verificación. Secretaría los revisa antes de emitirlos.</div>`);
  }catch(e){ main(`<div class="empty">Error</div>`); }
};
async function pedirCertificado(tipo, label){
  let periodo="", datos={};
  if(tipo==="notas") periodo=prompt("¿De qué período?\n\nEscribe por ejemplo: Período 3, o «Todo el año»","Período 3")||"";
  if(tipo==="recuperacion"){
    datos.materia=prompt("¿De qué materia?")||"";
    if(!datos.materia) return;
  }
  if(tipo==="taller") datos.curso=prompt("¿De qué taller o curso?")||"";
  if(!confirm(`¿Solicitar ${label}?\n\nSecretaría lo revisa y te avisa para descargarlo aquí mismo.`)) return;
  try{
    const r=await post("/secretaria/certificados/solicitar",{institucion_id:ST.institucion_id,
      estudiante_id:ST.estudiante_id, tipo, periodo, datos});
    toast(r.msg,!r.ok);
    if(r.ok) VISTAS.alcertificados();
  }catch(e){ toast("Error",true); }
}

/* ═══ SECRETARÍA: emitir certificados e importar SIMAT ═══ */
VISTAS.secretaria = async function(tab){
  loading();
  try{
    const t=tab||"certificados";
    ST._secTab=t;
    main(head("Secretaría académica","Certificados, historial académico e importación de la plataforma anterior")+`
      <div class="subtabs">
        ${[["certificados","📜 Certificados"],["simat","📥 Importar SIMAT"],["historico","📚 Historial"]].map(([k,l])=>
          `<button class="subtab ${t===k?'active':''}" onclick="VISTAS.secretaria('${k}')">${l}</button>`).join("")}</div>
      <div id="sec-cont"><div class="empty">Cargando…</div></div>`);
    if(t==="certificados") await secCertificados();
    if(t==="simat") await secSimat();
    if(t==="historico") await secHistorico();
  }catch(e){ main(`<div class="empty">Error</div>`); }
};
async function secCertificados(){
  const d=await api(`/secretaria/certificados?institucion_id=${ST.institucion_id}`);
  const r=d.resumen;
  document.getElementById("sec-cont").innerHTML=`
    <div class="kpis">
      <div class="kpi ${r.pendientes?'orange':''}"><div class="kpi-ico">⏳</div><div class="kpi-val">${r.pendientes}</div><div class="kpi-lbl">Por emitir</div></div>
      <div class="kpi green"><div class="kpi-ico">✅</div><div class="kpi-val">${r.emitidos}</div><div class="kpi-lbl">Emitidos</div></div>
      <div class="kpi"><div class="kpi-ico">📜</div><div class="kpi-val">${r.total}</div><div class="kpi-lbl">Total</div></div>
    </div>
    ${d.certificados.map(x=>`
      <div class="mat-fila">
        <span style="font-size:1.15rem">${x.estado==="solicitado"?"⏳":"✅"}</span>
        <div class="nom"><b>${esc(x.estudiante)}</b> — ${esc(x.tipo_label)}
          <div class="small muted">${esc(x.numero||"")}${x.periodo?" · "+esc(x.periodo):""} ·
            pedido ${esc(x.solicitado||"")}${x.n_descargas?` · ${x.n_descargas} descarga(s)`:""}</div></div>
        <div style="display:flex;gap:4px;flex-wrap:wrap">
          ${x.estado==="solicitado"
            ?`<button class="btn btn-xs btn-green" onclick="emitirCert(${x.id})">✍️ Emitir</button>`
            :`<button class="btn btn-xs" onclick="window.open(API+'/secretaria/certificados/ver?id=${x.id}')">👁️ Ver</button>`}
        </div>
      </div>`).join("")||'<div class="empty">Sin solicitudes.</div>'}
    <div class="legal-note">📜 Cuando emites, el estudiante lo ve al instante en su portal y lo descarga con código de verificación. Ya no tiene que venir hasta el colegio por un papel.</div>`;
}
async function emitirCert(id){
  if(!confirm("¿Emitir este certificado?\n\nEl estudiante podrá descargarlo de inmediato.")) return;
  try{ const r=await post("/secretaria/certificados/emitir",{id,
      emitido_por:(ST.perfil.nombre||"Secretaría académica")});
    toast(r.msg,!r.ok);
    if(r.ok){ secCertificados(); setTimeout(()=>window.open(API+`/secretaria/certificados/ver?id=${id}`),600); }
  }catch(e){ toast("Error",true); }
}
async function secSimat(){
  const [f, i]=await Promise.all([
    api(`/secretaria/simat/formato`),
    api(`/secretaria/simat/importaciones?institucion_id=${ST.institucion_id}`),
  ]);
  const r=i.resumen;
  document.getElementById("sec-cont").innerHTML=`
    <div class="kpis">
      <div class="kpi teal"><div class="kpi-ico">📚</div><div class="kpi-val">${r.notas_historicas}</div><div class="kpi-lbl">Notas históricas</div></div>
      <div class="kpi"><div class="kpi-ico">📅</div><div class="kpi-val">${r.anios.length}</div><div class="kpi-lbl">Años cargados</div></div>
      <div class="kpi ${r.sin_vincular?'orange':''}"><div class="kpi-ico">🔗</div><div class="kpi-val">${r.sin_vincular}</div><div class="kpi-lbl">Sin vincular</div></div>
      <div class="kpi"><div class="kpi-ico">📥</div><div class="kpi-val">${r.n_importaciones}</div><div class="kpi-lbl">Importaciones</div></div>
    </div>
    <div class="card"><div class="card-head"><h3>📥 Traer las notas de la plataforma anterior</h3></div>
    <div class="card-body">
      <div class="legal-note">📌 Exporta el histórico desde SIMAT (o de la plataforma que usen) en <b>CSV</b> y súbelo aquí. El cruce se hace por <b>documento</b>. Lo que no cruce queda guardado y se vincula solo cuando el estudiante se matricule.</div>
      <div class="fsec">Columnas que debe traer</div>
      <div class="tbl-scroll"><table><thead><tr><th>Columna</th><th>Obligatoria</th><th>Qué es</th></tr></thead>
        <tbody>${f.columnas.map(c=>`<tr><td><code>${esc(c.nombre)}</code></td>
          <td style="text-align:center">${c.obligatoria?"✅":"—"}</td>
          <td class="small">${esc(c.desc)}</td></tr>`).join("")}</tbody></table></div>
      <div class="fsec">Ejemplo</div>
      <pre style="background:#0F172A;color:#E2E8F0;padding:12px;border-radius:9px;overflow-x:auto;font-size:.76rem">${esc(f.ejemplo_csv)}</pre>
      <div class="dropzone" onclick="document.getElementById('simat-file').click()" style="margin-top:12px">
        📥 Toca para escoger el archivo CSV del histórico</div>
      <input type="file" id="simat-file" accept=".csv,.txt" style="display:none" onchange="simatArchivo(this)">
      <ul class="small muted" style="margin-top:10px;line-height:1.7">
        ${f.notas.map(n=>`<li>${esc(n)}</li>`).join("")}</ul>
      <button class="btn btn-sm" style="margin-top:8px" onclick="reconciliarSimat()">🔗 Reintentar vincular los sin cruce</button>
    </div></div>
    <div class="card"><div class="card-head"><h3>📋 Importaciones hechas</h3></div>
    <div class="tbl-scroll"><table><thead><tr><th>Lote</th><th>Archivo</th><th style="text-align:center">Filas</th>
      <th style="text-align:center">Notas</th><th style="text-align:center">Cruzadas</th><th style="text-align:center">Sin cruce</th><th>Fecha</th></tr></thead>
      <tbody>${i.importaciones.map(x=>`<tr>
        <td class="rj-num">${esc(x.lote)}</td><td class="small">${esc(x.archivo||"—")}</td>
        <td style="text-align:center">${x.n_filas}</td><td style="text-align:center">${x.n_notas}</td>
        <td style="text-align:center"><span class="badge b-green">${x.cruzadas}</span></td>
        <td style="text-align:center">${x.sin_cruce?`<span class="badge b-orange" style="cursor:pointer" onclick='verSinCruce(${JSON.stringify(x.sin_cruce_detalle)})'>${x.sin_cruce}</span>`:"0"}</td>
        <td class="small">${esc(x.fecha)}</td></tr>`).join("")||'<tr><td colspan="7" class="empty">Sin importaciones.</td></tr>'}
      </tbody></table></div></div>`;
}
function simatArchivo(inp){
  const f=inp.files[0]; if(!f) return;
  const rd=new FileReader();
  rd.onload=()=>{
    const txt=rd.result;
    const lineas=txt.split(/\r?\n/).filter(l=>l.trim());
    if(lineas.length<2){ toast("El archivo está vacío",true); return; }
    const sep=lineas[0].includes(";")?";":",";
    const cols=lineas[0].split(sep).map(c=>c.trim().toLowerCase().replace(/[^a-z]/g,""));
    const filas=lineas.slice(1).map(l=>{
      const v=l.split(sep);
      const o={};
      cols.forEach((c,i)=>{ o[c]=(v[i]||"").trim(); });
      return o;
    });
    if(!cols.includes("documento")||!cols.includes("materia")){
      toast("El archivo debe traer al menos las columnas documento y materia",true); return; }
    if(!confirm(`Se van a importar ${filas.length} fila(s) de «${f.name}».\n\n¿Continuar?`)) return;
    enviarSimat(f.name, filas);
  };
  rd.readAsText(f, "UTF-8");
  inp.value="";
}
async function enviarSimat(archivo, filas){
  toast("📥 Procesando el archivo…");
  try{
    const r=await post("/secretaria/simat/importar",{institucion_id:ST.institucion_id,
      archivo, filas, hecho_por:(ST.perfil.nombre||"Secretaría")});
    toast(r.msg,!r.ok);
    if(r.ok){
      if(r.detalle_sin_cruce&&r.detalle_sin_cruce.length)
        setTimeout(()=>verSinCruce(r.detalle_sin_cruce),900);
      secSimat();
    }
  }catch(e){ toast("Error al importar",true); }
}
function verSinCruce(lista){
  document.getElementById("modal-srd-title").textContent="⚠️ Documentos que no cruzaron";
  document.getElementById("modal-srd-body").innerHTML=`
    <div class="legal-note">Estos documentos no están matriculados en la institución. Sus notas quedaron guardadas: cuando se matriculen, se vinculan solas. También puedes usar «Reintentar vincular».</div>
    ${(lista||[]).map(x=>`<div class="mat-fila"><span>👤</span>
      <div class="nom"><b>${esc(x.documento)}</b>
        <div class="small muted">${esc(x.nombre||"—")}</div></div></div>`).join("")||'<div class="empty">Ninguno.</div>'}`;
  abrirModal("modal-srd");
}
async function reconciliarSimat(){
  try{ const r=await post(`/secretaria/simat/reconciliar?institucion_id=${ST.institucion_id}`,{});
    toast(r.msg,!r.ok); if(r.ok) secSimat();
  }catch(e){ toast("Error",true); }
}
async function secHistorico(){
  const sal=await api(`/academico/salones?institucion_id=${ST.institucion_id}`);
  document.getElementById("sec-cont").innerHTML=`
    <div class="legal-note">📚 Consulta el historial completo de un estudiante, incluyendo lo importado de la plataforma anterior.</div>
    <div class="card"><div class="card-body">
      <div class="frow"><label>Salón</label><select id="sh_salon" onchange="cargarEstHist()">
        ${sal.map(s=>`<option value="${s.id}">${esc(s.nombre)}</option>`).join("")}</select></div>
      <div class="frow"><label>Estudiante</label><select id="sh_est" onchange="verHistorial()">
        <option>Cargando…</option></select></div>
    </div></div>
    <div id="sh-res"></div>`;
  cargarEstHist();
}
async function cargarEstHist(){
  const s=document.getElementById("sh_salon");
  if(!s) return;
  try{
    const d=await api(`/academico/salones/detalle?salon_id=${s.value}`);
    const e=document.getElementById("sh_est");
    e.innerHTML=d.estudiantes.map(x=>`<option value="${x.id}">${esc(x.nombre)}</option>`).join("");
    verHistorial();
  }catch(err){}
}
async function verHistorial(){
  const e=document.getElementById("sh_est");
  if(!e||!e.value) return;
  try{
    const h=await api(`/secretaria/historico?estudiante_id=${e.value}`);
    document.getElementById("sh-res").innerHTML = h.ok&&h.n_anios?`
      <div class="card"><div class="card-head"><h3>📚 ${esc(h.estudiante)}</h3>
        <span class="small muted">${h.n_anios} año(s) · ${esc(h.origen)}</span></div>
      <div class="card-body">
        ${h.anios.map(a=>`<div style="margin-bottom:14px">
          <b>Año ${a.anio}${a.grado?" · grado "+esc(a.grado):""}</b>
          <span class="badge ${a.promedio>=3.5?'b-green':a.promedio>=3?'b-blue':'b-orange'}">Promedio ${a.promedio}</span>
          ${a.perdidas?`<span class="badge b-red">${a.perdidas} perdida(s)</span>`:""}
          <div class="tbl-scroll" style="margin-top:6px"><table><thead><tr><th>Materia</th>
            ${[1,2,3,4].map(p=>`<th style="text-align:center">P${p}</th>`).join("")}
            <th style="text-align:center">Def.</th></tr></thead>
            <tbody>${a.materias.map(m=>`<tr><td class="small">${esc(m.materia)}</td>
              ${[1,2,3,4].map(p=>`<td style="text-align:center">${m.periodos[p]!=null?m.periodos[p]:"—"}</td>`).join("")}
              <td style="text-align:center"><b>${m.definitiva!=null?m.definitiva:"—"}</b></td></tr>`).join("")}
            </tbody></table></div></div>`).join("")}
      </div></div>`
      : '<div class="empty">Este estudiante no tiene historial importado.</div>';
  }catch(err){}
}
