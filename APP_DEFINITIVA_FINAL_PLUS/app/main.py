from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import os
import base64

app = FastAPI(title="Control Empleados - DEFINITIVA v6")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- BASE DE DATOS EN MEMORIA (simple para Render free) ---
empleados_db = {}
preguntas_db = []
evaluaciones_db = []
fotos_db = {}

# --- MODELOS ---
class Empleado(BaseModel):
    id: str
    nombre: str
    puesto: str
    area: str
    fecha_ingreso: Optional[str] = None

class Pregunta(BaseModel):
    id: int
    texto: str
    tipo: str = "calificacion"  # calificacion, texto

class Evaluacion(BaseModel):
    id: int
    empleado_id: str
    fecha: str
    calificaciones: dict
    comentario: str
    fotos: List[str] = []
    promedio: float

# --- FRONTEND BONITO EN / ---
HTML_PANEL = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Control Empleados - DEFINITIVA v6</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Inter',sans-serif}
body{background:#0f172a;color:#e2e8f0;min-height:100vh}
.hero{background:linear-gradient(135deg,#6366f1 0%,#8b5cf6 50%,#ec4899 100%);padding:70px 20px 80px;text-align:center}
.hero h1{font-size:52px;font-weight:800;letter-spacing:-2px;color:white}
.hero p{font-size:18px;opacity:.95;margin-top:10px;color:white;max-width:700px;margin-left:auto;margin-right:auto}
.badge{margin-top:20px;display:inline-flex;align-items:center;gap:8px;background:rgba(255,255,255,.2);backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,.3);color:white;padding:8px 16px;border-radius:100px;font-weight:600;font-size:13px}
.container{max-width:1200px;margin:-50px auto 0;padding:0 20px 50px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:24px}
.card{background:#1e293b;border:1px solid #334155;border-radius:24px;padding:32px;transition:.3s;position:relative;overflow:hidden}
.card:hover{transform:translateY(-6px);border-color:#6366f1;box-shadow:0 20px 50px rgba(99,102,241,.25)}
.card::before{content:'';position:absolute;top:0;left:0;right:0;height:4px;background:linear-gradient(90deg,#6366f1,#ec4899)}
.card h3{font-size:22px;color:white;margin-bottom:8px}
.card p{color:#94a3b8;font-size:14.5px;line-height:1.6}
.btn{margin-top:18px;display:inline-flex;align-items:center;gap:8px;padding:12px 20px;border-radius:12px;text-decoration:none;font-weight:600;font-size:14px;transition:.2s;cursor:pointer;border:none}
.btn-primary{background:#6366f1;color:white}.btn-primary:hover{background:#4f46e5}
.btn-ghost{background:#0f172a;color:#e2e8f0;border:1px solid #334155}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:20px}
.stat{background:#0f172a;border-radius:16px;padding:16px;text-align:center;border:1px solid #1e293b}
.stat b{font-size:24px;color:white;display:block}
.stat span{font-size:12px;color:#64748b}
.tabs{margin-top:30px;background:#1e293b;border-radius:20px;border:1px solid #334155;overflow:hidden}
.tab-header{display:flex;background:#0f172a;border-bottom:1px solid #334155}
.tab{flex:1;padding:16px;text-align:center;cursor:pointer;font-weight:600;font-size:14px;color:#64748b;border-bottom:2px solid transparent}
.tab.active{color:white;border-bottom-color:#6366f1;background:#1e293b}
.tab-content{padding:28px}
.input{width:100%;padding:14px 16px;border-radius:12px;border:1px solid #334155;background:#0f172a;color:white;margin-top:8px;outline:none}
.input:focus{border-color:#6366f1}
label{font-size:12px;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:.5px}
@media(max-width:700px){.hero h1{font-size:34px}.grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="hero">
<h1>Control Empleados</h1>
<p>DEFINITIVA v6 - Sistema completo: Admin crea preguntas dinámicas + Evalúa con calificación, comentario y fotos + Empleado ve su historial</p>
<div class="badge">🟢 LIVE en Render - control-empleados-3oz6.onrender.com</div>
</div>

<div class="container">
<div class="stats">
<div class="stat"><b id="count-emp">0</b><span>Empleados</span></div>
<div class="stat"><b id="count-preg">0</b><span>Preguntas</span></div>
<div class="stat"><b id="count-eval">0</b><span>Evaluaciones</span></div>
</div>

<div class="grid" style="margin-top:28px">
<div class="card">
<h3>👑 Panel Administrador</h3>
<p>Crea preguntas dinámicas, registra empleados, realiza evaluaciones con calificación 1-10, comentario detallado y fotos de evidencia.</p>
<a class="btn btn-primary" href="/docs">Abrir API Docs →</a>
<button class="btn btn-ghost" onclick="document.getElementById('admin-tab').click()">Probar aquí abajo ↓</button>
</div>
<div class="card">
<h3>👤 Portal Empleado</h3>
<p>Consulta tu historial completo, promedios, evolución y fotos de tus evaluaciones en tiempo real.</p>
<a class="btn btn-primary" href="#empleado">Ver mi historial →</a>
<button class="btn btn-ghost" onclick="alert('El empleado ingresa su ID para ver su historial. Prueba con /empleado/{id}/historial en /docs')">Cómo funciona</button>
</div>
<div class="card">
<h3>📱 Apps Móviles</h3>
<p>Android APK e iPhone PWA conectadas a este mismo backend. Instalables en 1 click.</p>
<p style="margin-top:12px;color:#a5b4fc;font-size:12px"><b>Backend:</b> control-empleados-3oz6.onrender.com</p>
<a class="btn btn-ghost" href="/docs">Descargar / Instalar</a>
</div>
</div>

<div class="tabs">
<div class="tab-header">
<div class="tab active" id="admin-tab" onclick="switchTab('admin')">🛠️ Admin - Crear</div>
<div class="tab" onclick="switchTab('evaluar')">⭐ Evaluar</div>
<div class="tab" onclick="switchTab('empleado')">📊 Consultar Historial</div>
</div>

<div id="content-admin" class="tab-content">
<div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
<div>
<label>Registrar Empleado</label>
<input id="emp_id" class="input" placeholder="ID - Ej: EMP001">
<input id="emp_nombre" class="input" placeholder="Nombre completo">
<input id="emp_puesto" class="input" placeholder="Puesto - Ej: Cajero">
<input id="emp_area" class="input" placeholder="Área - Ej: Ventas">
<button class="btn btn-primary" style="width:100%;margin-top:12px" onclick="crearEmpleado()">+ Crear Empleado</button>
</div>
<div>
<label>Crear Pregunta Dinámica</label>
<input id="preg_texto" class="input" placeholder="Ej: ¿Puntualidad? ¿Atención al cliente?">
<select id="preg_tipo" class="input"><option value="calificacion">Calificación 1-10</option><option value="texto">Texto libre</option></select>
<button class="btn btn-primary" style="width:100%;margin-top:12px" onclick="crearPregunta()">+ Crear Pregunta</button>
<div id="lista-preguntas" style="margin-top:15px;font-size:13px;color:#94a3b8"></div>
</div>
</div>
<p id="msg-admin" style="margin-top:15px;font-size:13px"></p>
</div>

<div id="content-evaluar" class="tab-content" style="display:none">
<label>ID Empleado a Evaluar</label>
<input id="eval_emp_id" class="input" placeholder="EMP001">
<label style="margin-top:12px;display:block">Comentario General</label>
<textarea id="eval_comentario" class="input" rows="3" placeholder="Desempeño excelente, mejorar puntualidad..."></textarea>
<div id="eval_preguntas_area" style="margin-top:15px"></div>
<button class="btn btn-primary" style="width:100%;margin-top:15px;padding:16px" onclick="evaluar()">⭐ Guardar Evaluación</button>
<p id="msg-eval" style="margin-top:12px;font-size:13px"></p>
</div>

<div id="content-empleado" class="tab-content" style="display:none">
<label>ID de Empleado para ver historial</label>
<div style="display:flex;gap:10px;margin-top:8px">
<input id="hist_id" class="input" style="margin-top:0" placeholder="EMP001">
<button class="btn btn-primary" onclick="verHistorial()">Ver Historial</button>
</div>
<div id="historial-result" style="margin-top:20px"></div>
</div>

</div>

<p style="text-align:center;margin-top:40px;color:#475569;font-size:11px">DEFINITIVA v6 - Render + FastAPI + Panel Bonito | Hecho para tecnorg1318 | 2026</p>
</div>

<script>
const API = "";
async function api(path, method="GET", body=null){
  const opts={method,headers:{"Content-Type":"application/json"}};
  if(body) opts.body=JSON.stringify(body);
  const r=await fetch(API+path,opts);
  return r.json();
}
function switchTab(name){
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('[id^="content-"]').forEach(c=>c.style.display='none');
  if(name==='admin'){document.getElementById('admin-tab').classList.add('active');document.getElementById('content-admin').style.display='block';}
  if(name==='evaluar'){document.querySelectorAll('.tab')[1].classList.add('active');document.getElementById('content-evaluar').style.display='block';cargarPreguntasEval();}
  if(name==='empleado'){document.querySelectorAll('.tab')[2].classList.add('active');document.getElementById('content-empleado').style.display='block';}
}
async function refreshStats(){
  try{
    const emps = await api('/empleados');
    const pregs = await api('/preguntas');
    const evals = await api('/evaluaciones');
    document.getElementById('count-emp').innerText = emps.length || 0;
    document.getElementById('count-preg').innerText = pregs.length || 0;
    document.getElementById('count-eval').innerText = evals.length || 0;
    const lista = document.getElementById('lista-preguntas');
    lista.innerHTML = pregs.map(p=>`• ${p.texto} <small>(${p.tipo})</small>`).join('<br>');
  }catch(e){}
}
async function crearEmpleado(){
  const id=document.getElementById('emp_id').value;
  const nombre=document.getElementById('emp_nombre').value;
  const puesto=document.getElementById('emp_puesto').value;
  const area=document.getElementById('emp_area').value;
  if(!id||!nombre) return alert('ID y Nombre obligatorios');
  const res=await api('/empleados','POST',{id,nombre,puesto,area,fecha_ingreso:new Date().toISOString().split('T')[0]});
  document.getElementById('msg-admin').innerText='✅ Empleado creado: '+res.nombre;
  refreshStats();
}
async function crearPregunta(){
  const texto=document.getElementById('preg_texto').value;
  const tipo=document.getElementById('preg_tipo').value;
  if(!texto) return alert('Escribe la pregunta');
  await api('/preguntas','POST',{texto,tipo});
  document.getElementById('msg-admin').innerText='✅ Pregunta creada';
  document.getElementById('preg_texto').value='';
  refreshStats();
}
async function cargarPreguntasEval(){
  const pregs=await api('/preguntas');
  const area=document.getElementById('eval_preguntas_area');
  area.innerHTML=pregs.map(p=>`<div style="margin-top:10px"><label>${p.texto}</label><input data-preg="${p.id}" class="input" type="number" min="1" max="10" placeholder="Calificación 1-10"></div>`).join('');
}
async function evaluar(){
  const empleado_id=document.getElementById('eval_emp_id').value;
  const comentario=document.getElementById('eval_comentario').value;
  const inputs=document.querySelectorAll('[data-preg]');
  const calificaciones={};
  inputs.forEach(i=>calificaciones[i.dataset.preg]=i.value);
  if(!empleado_id) return alert('Pon ID empleado');
  const res=await api('/evaluaciones','POST',{empleado_id,calificaciones,comentario});
  document.getElementById('msg-eval').innerText='✅ Evaluación guardada. Promedio: '+res.promedio;
  refreshStats();
}
async function verHistorial(){
  const id=document.getElementById('hist_id').value;
  if(!id) return;
  const data=await api('/empleado/'+id+'/historial');
  const div=document.getElementById('historial-result');
  if(!data.length){div.innerHTML='<p style="color:#94a3b8">Sin evaluaciones aún</p>';return;}
  div.innerHTML=data.map(e=>`
    <div style="background:#0f172a;border:1px solid #334155;border-radius:16px;padding:16px;margin-top:12px">
      <b>📅 ${e.fecha}</b> - Promedio: <span style="color:#10b981;font-weight:800">${e.promedio}</span>
      <p style="margin-top:8px;color:#cbd5e1">${e.comentario}</p>
      <pre style="margin-top:8px;font-size:12px;color:#94a3b8">${JSON.stringify(e.calificaciones,null,2)}</pre>
    </div>
  `).join('');
}
refreshStats();
setInterval(refreshStats,5000);
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def home():
    return HTML_PANEL

@app.get("/api", include_in_schema=False)
async def api_info_old():
    return {"version": "DEFINITIVA v6 - TODO", "nuevo": "Admin crea preguntas dinamicas + evalua con calificacion/comentario/fotos + empleado ve historial", "frontend": "/", "docs": "/docs"}

# --- RUTAS API ORIGINALES ---

@app.get("/empleados")
def listar_empleados():
    return list(empleados_db.values())

@app.post("/empleados")
def crear_empleado(emp: Empleado):
    empleados_db[emp.id] = emp.dict()
    return emp

@app.get("/preguntas")
def listar_preguntas():
    return preguntas_db

@app.post("/preguntas")
def crear_pregunta(preg: dict):
    nueva = {"id": len(preguntas_db)+1, "texto": preg.get("texto"), "tipo": preg.get("tipo","calificacion")}
    preguntas_db.append(nueva)
    return nueva

@app.get("/evaluaciones")
def listar_evaluaciones():
    return evaluaciones_db

@app.post("/evaluaciones")
def crear_evaluacion(data: dict):
    empleado_id = data.get("empleado_id")
    califs = data.get("calificaciones", {})
    comentario = data.get("comentario","")
    # calcular promedio
    try:
        nums = [float(v) for v in califs.values() if str(v).replace('.','',1).isdigit()]
        prom = round(sum(nums)/len(nums),2) if nums else 0
    except:
        prom = 0
    nueva = {
        "id": len(evaluaciones_db)+1,
        "empleado_id": empleado_id,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "calificaciones": califs,
        "comentario": comentario,
        "fotos": data.get("fotos",[]),
        "promedio": prom
    }
    evaluaciones_db.append(nueva)
    return nueva

@app.get("/empleado/{empleado_id}/historial")
def historial_empleado(empleado_id: str):
    return [e for e in evaluaciones_db if e["empleado_id"] == empleado_id]

@app.get("/version")
def version():
    return {"version": "DEFINITIVA v6 - TODO", "nuevo": "Admin crea preguntas dinamicas + evalua con calificacion/comentario/fotos + empleado ve historial"}
scheduler.start()
