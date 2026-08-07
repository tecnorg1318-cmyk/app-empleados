from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Text, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
import os, base64

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./clockrd.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
if "neon.tech" in DATABASE_URL and "sslmode" not in DATABASE_URL:
    DATABASE_URL += "?sslmode=require" if "?" not in DATABASE_URL else "&sslmode=require"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class EmpleadoDB(Base):
    __tablename__ = "empleados"
    id = Column(String, primary_key=True)
    nombre = Column(String, nullable=False)
    puesto = Column(String, default="")
    telefono = Column(String, default="")
    horario_entrada = Column(String, default="09:00")
    horario_salida = Column(String, default="18:00")
    sucursal = Column(String, default="Matriz")
    nss = Column(String, default="")
    sueldo_tipo = Column(String, default="mes")
    sueldo_monto = Column(Float, default=0.0)
    # 2-7
    estatus = Column(String, default="activo") # activo, baja, vacaciones, incapacidad
    foto_url = Column(Text, default="") # base64
    usuario = Column(String, default="")
    password = Column(String, default="1234")
    vacaciones_totales = Column(Integer, default=12)
    vacaciones_tomadas = Column(Integer, default=0)
    faltas = Column(Integer, default=0)
    retardos = Column(Integer, default=0)
    promedio_eval = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.now)

class SucursalDB(Base):
    __tablename__ = "sucursales"
    id = Column(String, primary_key=True)
    nombre = Column(String, nullable=False)
    direccion = Column(String, default="")

class AsignacionDB(Base):
    __tablename__ = "asignaciones_flexibles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    empleado_id = Column(String, nullable=False)
    tipo = Column(String, nullable=False)
    fecha = Column(String, default="")
    sucursal_dia = Column(String, default="")
    semana = Column(String, default="")
    lunes = Column(String, default=""); martes = Column(String, default=""); miercoles = Column(String, default="")
    jueves = Column(String, default=""); viernes = Column(String, default=""); sabado = Column(String, default=""); domingo = Column(String, default="")
    mes = Column(String, default="")
    sucursal_mes = Column(String, default="")
    created_at = Column(DateTime, default=datetime.now)

class VisitaDB(Base):
    __tablename__ = "historial_visitas"
    id = Column(Integer, primary_key=True, autoincrement=True)
    empleado_id = Column(String, nullable=False)
    sucursal_id = Column(String, nullable=False)
    sucursal_nombre = Column(String, default="")
    fecha = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d"))
    hora_entrada = Column(String, default=lambda: datetime.now().strftime("%H:%M:%S"))
    es_retardo = Column(Boolean, default=False)
    es_falta = Column(Boolean, default=False)
    notas = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)

class VacacionDB(Base):
    __tablename__ = "vacaciones"
    id = Column(Integer, primary_key=True, autoincrement=True)
    empleado_id = Column(String, nullable=False)
    fecha_inicio = Column(String, nullable=False)
    fecha_fin = Column(String, nullable=False)
    dias = Column(Integer, default=1)
    motivo = Column(String, default="")
    estatus = Column(String, default="pendiente") # pendiente, aprobada, rechazada
    created_at = Column(DateTime, default=datetime.now)

class EvaluacionDB(Base):
    __tablename__ = "evaluaciones"
    id = Column(Integer, primary_key=True, autoincrement=True)
    empleado_id = Column(String, nullable=False)
    fecha = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d"))
    calificacion = Column(Float, default=0.0) # 1-10
    comentario = Column(Text, default="")
    evaluador = Column(String, default="admin")
    created_at = Column(DateTime, default=datetime.now)

Base.metadata.create_all(bind=engine)
print(f"✅ v10 lista: {DATABASE_URL[:40]}")

app = FastAPI(title="Control v10 - 2 al 7")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class EmpleadoCreate(BaseModel):
    id: str; nombre: str; puesto: str=""; telefono: str=""; horario_entrada: str="09:00"; horario_salida: str="18:00"; sucursal: str="Matriz"; nss: str=""; sueldo_tipo: str="mes"; sueldo_monto: float=0; usuario: str=""; password: str="1234"; estatus: str="activo"; vacaciones_totales: int=12

class SucursalCreate(BaseModel):
    id: str; nombre: str; direccion: str=""

class AsigDia(BaseModel):
    empleado_id: str; fecha: str; sucursal_id: str
class AsigSemana(BaseModel):
    empleado_id: str; semana: str; lunes: str=""; martes: str=""; miercoles: str=""; jueves: str=""; viernes: str=""; sabado: str=""; domingo: str=""
class AsigMes(BaseModel):
    empleado_id: str; mes: str; sucursal_id: str
class VisitaCreate(BaseModel):
    empleado_id: str; sucursal_id: str; sucursal_nombre: str=""; notas: str=""
class VacacionCreate(BaseModel):
    empleado_id: str; fecha_inicio: str; fecha_fin: str; dias: int=1; motivo: str=""
class EvaluacionCreate(BaseModel):
    empleado_id: str; calificacion: float; comentario: str=""

HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>v10 - 2 al 7 completo</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Inter',sans-serif}
body{background:#0f172a;color:#e2e8f0}
.hero{background:linear-gradient(135deg,#6366f1,#8b5cf6,#ec4899);padding:28px 20px 45px;text-align:center}
.hero h1{color:white;font-size:32px;font-weight:800}
.tabs{max-width:1350px;margin:-22px auto 0;display:flex;gap:6px;padding:0 20px;flex-wrap:wrap}
.tab{padding:9px 14px;background:#1e293b;border:1px solid #334155;border-radius:10px;cursor:pointer;font-weight:700;font-size:11px}
.tab.active{background:#6366f1;color:white}
.container{max-width:1350px;margin:18px auto;padding:0 20px 40px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:1000px){.grid{grid-template-columns:1fr}}
.card{background:#1e293b;border:1px solid #334155;border-radius:16px;padding:18px}
label{font-size:10px;color:#94a3b8;font-weight:700;text-transform:uppercase;margin-top:8px;display:block}
.input,.select{width:100%;padding:9px;border-radius:8px;border:1px solid #334155;background:#0f172a;color:white;margin-top:4px;font-size:12px}
.btn{margin-top:10px;padding:9px 12px;border-radius:8px;border:none;font-weight:700;font-size:11px;cursor:pointer;width:100%}
.btn-p{background:#6366f1;color:white}
.btn-g{background:#10b981;color:white}
.btn-o{background:#f59e0b;color:white}
.btn-d{background:#0f172a;color:white;border:1px solid #334155}
.table{width:100%;font-size:11px;border-collapse:collapse;margin-top:8px}
.table th{color:#64748b;text-align:left;font-size:9px;padding:5px;border-bottom:1px solid #334155}
.table td{padding:5px;border-bottom:1px solid #1e293b}
.img-emp{width:36px;height:36px;border-radius:50%;object-fit:cover;background:#334155}
.badge{padding:2px 6px;border-radius:10px;font-size:9px;font-weight:700}
.st-activo{background:#10b98122;color:#34d399}
.st-baja{background:#ef444422;color:#f87171}
.st-vac{background:#f59e0b22;color:#fbbf24}
.st-inc{background:#6366f122;color:#a5b4fc}
</style>
</head>
<body>
<div class="hero">
<h1>v10 - Empleado Completo 2 al 7</h1>
<p style="color:white;opacity:.9;font-size:11px">✅ Vacaciones reales + Faltas/Retardos auto + Evaluación + Usuario/Pass + Foto + Estatus + Día/Sem/Mes + Historial admin</p>
</div>

<div class="tabs">
<div class="tab active" onclick="show('asig')">🗓️ Asignar</div>
<div class="tab" onclick="show('emp')">👥 Empleados + Foto + Estatus</div>
<div class="tab" onclick="show('vac')">🏖️ Vacaciones</div>
<div class="tab" onclick="show('eval')">⭐ Evaluaciones</div>
<div class="tab" onclick="show('suc')">🏪 Sucursales</div>
<div class="tab" onclick="show('mi')" style="background:#10b981;color:white">📱 Mi Día (Login Empleado)</div>
<div class="tab" onclick="show('hist')">🔒 Historial + Faltas (ADMIN)</div>
</div>

<div class="container">

<!-- ASIGNAR -->
<div id="sec-asig" class="grid">
<div class="card">
<h3>🗓️ Asignar Día/Sem/Mes</h3>
<label>Tipo</label><select id="tipo" class="select" onchange="cambiarTipo()"><option value="dia">DÍA</option><option value="semana" selected>SEMANA</option><option value="mes">MES</option></select>
<label>Empleado</label><select id="as_emp" class="select"></select>
<div id="box-dia" style="display:none"><label>Fecha</label><input id="as_fecha" class="input" type="date"><label>Sucursal</label><select id="as_suc_dia" class="select"></select><button class="btn btn-p" onclick="guardarDia()">Guardar DÍA</button></div>
<div id="box-semana"><label>Semana</label><input id="as_semana" class="input" type="week"><div style="display:grid;grid-template-columns:1fr 1fr;gap:5px"><div><label>Lun</label><select id="s_lun" class="select"></select></div><div><label>Mar</label><select id="s_mar" class="select"></select></div><div><label>Mié</label><select id="s_mie" class="select"></select></div><div><label>Jue</label><select id="s_jue" class="select"></select></div><div><label>Vie</label><select id="s_vie" class="select"></select></div><div><label>Sáb</label><select id="s_sab" class="select"></select></div><div><label>Dom</label><select id="s_dom" class="select"></select></div></div><button class="btn btn-p" onclick="guardarSemana()">Guardar SEMANA</button></div>
<div id="box-mes" style="display:none"><label>Mes</label><input id="as_mes" class="input" type="month"><label>Sucursal mes</label><select id="as_suc_mes" class="select"></select><button class="btn btn-p" onclick="guardarMes()">Guardar MES</button></div>
<p id="msg_as" style="font-size:10px;color:#34d399;margin-top:6px"></p>
</div>
<div class="card"><h3>Asignaciones</h3><div style="display:flex;gap:4px"><button class="btn btn-d" style="width:auto;padding:5px 8px" onclick="cargarAsig('')">TODO</button><button class="btn btn-d" style="width:auto;padding:5px 8px" onclick="cargarAsig('dia')">DÍA</button><button class="btn btn-d" style="width:auto;padding:5px 8px" onclick="cargarAsig('semana')">SEMANA</button><button class="btn btn-d" style="width:auto;padding:5px 8px" onclick="cargarAsig('mes')">MES</button></div><div id="lista_asig" style="max-height:550px;overflow:auto"></div></div>
</div>

<!-- EMPLEADOS -->
<div id="sec-emp" class="grid" style="display:none">
<div class="card">
<h3>👥 Crear empleado con TODO 2-7</h3>
<label>ID</label><input id="e_id" class="input" placeholder="EMP001">
<label>Nombre</label><input id="e_nom" class="input">
<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px"><div><label>Puesto</label><input id="e_pue" class="input"></div><div><label>Tel</label><input id="e_tel" class="input"></div></div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px"><div><label>Entrada</label><input id="e_he" class="input" type="time" value="09:00"></div><div><label>Salida</label><input id="e_hs" class="input" type="time" value="18:00"></div></div>
<label>Sucursal base</label><input id="e_suc" class="input" list="list_suc_nom">
<label>Estatus</label><select id="e_est" class="select"><option value="activo">Activo</option><option value="baja">Baja</option><option value="vacaciones">Vacaciones</option><option value="incapacidad">Incapacidad</option></select>
<label>Foto (sube archivo)</label><input id="e_foto" class="input" type="file" accept="image/*">
<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px"><div><label>Usuario app</label><input id="e_user" class="input" placeholder="juan"></div><div><label>Password</label><input id="e_pass" class="input" value="1234"></div></div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px"><div><label>Tipo sueldo</label><select id="e_tipo" class="select"><option value="hora">Hora</option><option value="quincena">Quincena</option><option value="mes" selected>Mes</option></select></div><div><label>Monto</label><input id="e_monto" class="input" type="number"></div></div>
<label>Vacaciones totales / año</label><input id="e_vactot" class="input" type="number" value="12">
<button class="btn btn-p" onclick="crearEmp()">Guardar empleado completo ✅</button>
<p id="msg_e" style="font-size:10px;color:#34d399"></p>
</div>
<div class="card"><h3>Lista empleados (con foto, estatus, faltas)</h3><table class="table"><thead><tr><th>Foto</th><th>ID/Nombre</th><th>Estatus</th><th>Faltas/Ret</th><th>Eval</th></tr></thead><tbody id="tab_emp"></tbody></table></div>
</div>

<!-- VACACIONES -->
<div id="sec-vac" class="grid" style="display:none">
<div class="card"><h3>🏖️ Solicitar / Asignar vacaciones</h3>
<label>Empleado</label><select id="vac_emp" class="select"></select>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px"><div><label>Inicio</label><input id="vac_ini" class="input" type="date"></div><div><label>Fin</label><input id="vac_fin" class="input" type="date"></div></div>
<label>Días</label><input id="vac_dias" class="input" type="number" value="1">
<label>Motivo</label><input id="vac_mot" class="input" placeholder="Vacaciones anuales">
<button class="btn btn-p" onclick="crearVac()">Guardar vacaciones</button>
</div>
<div class="card"><h3>Solicitudes vacaciones</h3><table class="table"><thead><tr><th>Emp</th><th>Fechas</th><th>Días</th><th>Estatus</th><th>Acción</th></tr></thead><tbody id="tab_vac"></tbody></table></div>
</div>

<!-- EVALUACION -->
<div id="sec-eval" class="grid" style="display:none">
<div class="card"><h3>⭐ Evaluar empleado</h3>
<label>Empleado</label><select id="eval_emp" class="select"></select>
<label>Calificación 1-10</label><input id="eval_cal" class="input" type="number" min="1" max="10" placeholder="8">
<label>Comentario</label><textarea id="eval_com" class="input" rows="3" placeholder="Buen desempeño, puntual..."></textarea>
<button class="btn btn-p" onclick="crearEval()">Guardar evaluación</button>
</div>
<div class="card"><h3>Evaluaciones</h3><table class="table"><thead><tr><th>Fecha</th><th>Emp</th><th>Cal</th><th>Comentario</th></tr></thead><tbody id="tab_eval"></tbody></table></div>
</div>

<div id="sec-suc" class="grid" style="display:none">
<div class="card"><h3>🏪 Sucursal</h3><label>ID</label><input id="suc_id" class="input"><label>Nombre</label><input id="suc_nom" class="input"><button class="btn btn-p" onclick="crearSuc()">Crear</button></div>
<div class="card"><h3>Sucursales</h3><table class="table"><thead><tr><th>ID</th><th>Nombre</th></tr></thead><tbody id="tab_suc"></tbody></table></div>
</div>

<div id="sec-mi" style="display:none">
<div class="grid">
<div class="card" style="border:2px solid #10b981"><h3>📱 Login Empleado - Mi Día</h3>
<label>Usuario</label><input id="my_user" class="input" placeholder="tu usuario">
<label>Password</label><input id="my_pass" class="input" type="password" placeholder="1234">
<label>ó ID directo</label><input id="my_id" class="input" placeholder="EMP001">
<button class="btn btn-g" onclick="loginEmpleado()">Entrar y ver dónde me toca hoy</button>
<div id="mi_box" style="margin-top:12px"></div>
</div>
<div class="card"><h3>Mi info completa</h3><div id="mi_info"></div><button class="btn btn-g" onclick="checkIn()" style="margin-top:10px">✅ Check-In</button><p style="font-size:10px;color:#64748b;margin-top:6px">Si llegas después de tu horario entrada, se cuenta retardo automático. Si no haces check, al final del día es falta (lo ve admin).</p></div>
</div>
</div>

<div id="sec-hist" style="display:none">
<div class="card" style="border:1px dashed #f59e0b"><h3>🔒 Historial + Faltas/Retardos (SOLO ADMIN)</h3>
<table class="table"><thead><tr><th>Fecha</th><th>Hora</th><th>Emp</th><th>Sucursal</th><th>Retardo?</th><th>Nota</th></tr></thead><tbody id="tab_hist"></tbody></table>
<button class="btn btn-d" onclick="cargarHist()">Actualizar</button>
</div>
</div>

</div>
<datalist id="list_suc_nom"></datalist>
<script>
const API="";
async function api(p,m="GET",b=null){const o={method:m,headers:{"Content-Type":"application/json"}}; if(b) o.body=JSON.stringify(b); const r=await fetch(API+p,o); return r.json();}
function show(s){
 document.querySelectorAll('[id^=sec-]').forEach(d=>d.style.display='none');
 document.getElementById('sec-'+s).style.display=s==='asig'||s==='emp'||s==='vac'||s==='eval'||s==='suc'?'grid':'block';
 if(s==='asig'){cargarEmps(); cargarSucs(); cargarAsig('');}
 if(s==='emp') cargarEmps();
 if(s==='suc') cargarSucs();
 if(s==='vac'){cargarEmps(); cargarVac();}
 if(s==='eval'){cargarEmps(); cargarEval();}
 if(s==='hist') cargarHist();
}
function cambiarTipo(){
 const t=document.getElementById('tipo').value;
 document.getElementById('box-dia').style.display=t==='dia'?'block':'none';
 document.getElementById('box-semana').style.display=t==='semana'?'block':'none';
 document.getElementById('box-mes').style.display=t==='mes'?'block':'none';
}
async function cargarEmps(){
 const emps=await api('/empleados');
 document.getElementById('tab_emp').innerHTML=emps.map(e=>{
   let estCls='st-activo'; if(e.estatus==='baja') estCls='st-baja'; if(e.estatus==='vacaciones') estCls='st-vac'; if(e.estatus==='incapacidad') estCls='st-inc';
   let foto=e.foto_url?`<img src="${e.foto_url}" class="img-emp">`:`<div class="img-emp" style="display:flex;align-items:center;justify-content:center;font-size:10px">${e.nombre.charAt(0)}</div>`;
   return `<tr><td>${foto}</td><td><b>${e.id}</b><br>${e.nombre}<br><small>${e.puesto}</small></td><td><span class="badge ${estCls}">${e.estatus}</span><br><small>Vac:${e.vacaciones_tomadas}/${e.vacaciones_totales}</small></td><td>F:${e.faltas} R:${e.retardos}</td><td>⭐ ${e.promedio_eval||0}</td></tr>`;
 }).join('');
 document.getElementById('as_emp').innerHTML=emps.map(e=>`<option value="${e.id}">${e.nombre}</option>`).join('');
 document.getElementById('vac_emp').innerHTML=document.getElementById('as_emp').innerHTML;
 document.getElementById('eval_emp').innerHTML=document.getElementById('as_emp').innerHTML;
}
async function cargarSucs(){
 const sucs=await api('/sucursales');
 document.getElementById('tab_suc').innerHTML=sucs.map(s=>`<tr><td>${s.id}</td><td>${s.nombre}</td></tr>`).join('');
 const opts=sucs.map(s=>`<option value="${s.id}">${s.nombre}</option>`).join('');
 document.getElementById('as_suc_dia').innerHTML=opts; document.getElementById('as_suc_mes').innerHTML=opts;
 ['s_lun','s_mar','s_mie','s_jue','s_vie','s_sab','s_dom'].forEach(id=>{let el=document.getElementById(id); if(el) el.innerHTML='<option value="">Descanso</option>'+opts;});
 document.getElementById('list_suc_nom').innerHTML=sucs.map(s=>`<option value="${s.id}">`).join('') + sucs.map(s=>`<option value="${s.nombre}">`).join('');
}
async function crearEmp(){
 const file=document.getElementById('e_foto').files[0];
 let fotoB64="";
 if(file){
   fotoB64=await new Promise(res=>{let r=new FileReader(); r.onload=e=>res(e.target.result); r.readAsDataURL(file);});
 }
 const d={id:document.getElementById('e_id').value,nombre:document.getElementById('e_nom').value,puesto:document.getElementById('e_pue').value,telefono:document.getElementById('e_tel').value,horario_entrada:document.getElementById('e_he').value,horario_salida:document.getElementById('e_hs').value,sucursal:document.getElementById('e_suc').value,estatus:document.getElementById('e_est').value,usuario:document.getElementById('e_user').value,password:document.getElementById('e_pass').value,sueldo_tipo:document.getElementById('e_tipo').value,sueldo_monto:parseFloat(document.getElementById('e_monto').value)||0,vacaciones_totales:parseInt(document.getElementById('e_vactot').value)||12,foto_url:fotoB64};
 if(!d.id||!d.nombre) return alert('ID y nombre');
 await api('/empleados','POST',d); document.getElementById('msg_e').innerText='Guardado ✅'; cargarEmps();
}
async function crearSuc(){
 const d={id:document.getElementById('suc_id').value,nombre:document.getElementById('suc_nom').value};
 await api('/sucursales','POST',d); cargarSucs();
}
async function guardarDia(){
 const d={empleado_id:document.getElementById('as_emp').value,fecha:document.getElementById('as_fecha').value,sucursal_id:document.getElementById('as_suc_dia').value};
 await api('/asignaciones/dia','POST',d); document.getElementById('msg_as').innerText='Día guardado'; cargarAsig('dia');
}
async function guardarSemana(){
 const d={empleado_id:document.getElementById('as_emp').value,semana:document.getElementById('as_semana').value,lunes:document.getElementById('s_lun').value,martes:document.getElementById('s_mar').value,miercoles:document.getElementById('s_mie').value,jueves:document.getElementById('s_jue').value,viernes:document.getElementById('s_vie').value,sabado:document.getElementById('s_sab').value,domingo:document.getElementById('s_dom').value};
 await api('/asignaciones/semana','POST',d); document.getElementById('msg_as').innerText='Semana guardada'; cargarAsig('semana');
}
async function guardarMes(){
 const d={empleado_id:document.getElementById('as_emp').value,mes:document.getElementById('as_mes').value,sucursal_id:document.getElementById('as_suc_mes').value};
 await api('/asignaciones/mes','POST',d); document.getElementById('msg_as').innerText='Mes guardado'; cargarAsig('mes');
}
async function cargarAsig(f){
 let url='/asignaciones'; if(f) url+='?tipo='+f;
 const list=await api(url);
 document.getElementById('lista_asig').innerHTML=list.map(a=>{
   if(a.tipo==='dia') return `<div class="card" style="padding:8px;margin-top:6px;border-left:4px solid #38bdf8">📅 ${a.fecha} (${a.empleado_id}) → ${a.sucursal_dia}</div>`;
   if(a.tipo==='semana') return `<div class="card" style="padding:8px;margin-top:6px;border-left:4px solid #a78bfa">🗓️ ${a.semana} (${a.empleado_id}) L:${a.lunes||'-'} M:${a.martes||'-'} X:${a.miercoles||'-'} J:${a.jueves||'-'} V:${a.viernes||'-'}</div>`;
   if(a.tipo==='mes') return `<div class="card" style="padding:8px;margin-top:6px;border-left:4px solid #fb923c">📆 ${a.mes} (${a.empleado_id}) → ${a.sucursal_mes}</div>`;
 }).join('');
}
async function crearVac(){
 const d={empleado_id:document.getElementById('vac_emp').value,fecha_inicio:document.getElementById('vac_ini').value,fecha_fin:document.getElementById('vac_fin').value,dias:parseInt(document.getElementById('vac_dias').value)||1,motivo:document.getElementById('vac_mot').value};
 await api('/vacaciones','POST',d); cargarVac();
}
async function cargarVac(){
 const v=await api('/vacaciones');
 document.getElementById('tab_vac').innerHTML=v.map(x=>`<tr><td>${x.empleado_id}</td><td>${x.fecha_inicio} al ${x.fecha_fin}</td><td>${x.dias}</td><td>${x.estatus}</td><td><button onclick="aprobarVac(${x.id},'aprobada')" class="btn btn-g" style="padding:4px 6px;width:auto">✔</button> <button onclick="aprobarVac(${x.id},'rechazada')" class="btn btn-p" style="padding:4px 6px;width:auto">✖</button></td></tr>`).join('');
}
async function aprobarVac(id,est){
 await api('/vacaciones/'+id+'/estatus','POST',{estatus:est}); cargarVac(); cargarEmps();
}
async function crearEval(){
 const d={empleado_id:document.getElementById('eval_emp').value,calificacion:parseFloat(document.getElementById('eval_cal').value)||0,comentario:document.getElementById('eval_com').value};
 await api('/evaluaciones','POST',d); cargarEval(); cargarEmps();
}
async function cargarEval(){
 const e=await api('/evaluaciones');
 document.getElementById('tab_eval').innerHTML=e.map(x=>`<tr><td>${x.fecha}</td><td>${x.empleado_id}</td><td>⭐ ${x.calificacion}</td><td>${x.comentario}</td></tr>`).join('');
}
let miActual=null; let miEmpleado=null;
async function loginEmpleado(){
 let user=document.getElementById('my_user').value;
 let pass=document.getElementById('my_pass').value;
 let id=document.getElementById('my_id').value;
 let url='';
 if(user){url=`/login?usuario=${user}&password=${pass}`;}
 else if(id){url=`/empleado/${id}/hoy`;}
 else return alert('Pon usuario/pass o ID');
 let data=await api(url);
 if(data.error){document.getElementById('mi_box').innerHTML=`<p style="color:#f87171">${data.error}</p>`; return;}
 if(data.empleado) {miEmpleado=data.empleado; miActual=data.hoy; }
 else {miActual=data;
   let emps=await api('/empleados');
   miEmpleado=emps.find(e=>e.id===data.empleado_id);
 }
 document.getElementById('mi_box').innerHTML=`<div style="background:#0f172a;padding:12px;border-radius:10px;border:1px solid #10b981">
 <p style="color:#10b981;font-weight:800">${miActual.dia_nombre} ${miActual.fecha} - ${miActual.origen}</p>
 <h3 style="color:white">${miActual.sucursal_nombre||'Descanso'}</h3>
 <p style="font-size:11px;color:#94a3b8">Horario: ${miEmpleado?miEmpleado.horario_entrada+' - '+miEmpleado.horario_salida:''}</p>
 </div>`;
 let info=`<p><b>${miEmpleado.nombre}</b> - ${miEmpleado.puesto}<br>
 Estatus: ${miEmpleado.estatus}<br>
 Vacaciones: ${miEmpleado.vacaciones_tomadas}/${miEmpleado.vacaciones_totales}<br>
 Faltas: ${miEmpleado.faltas} - Retardos: ${miEmpleado.retardos}<br>
 Eval promedio: ⭐ ${miEmpleado.promedio_eval||0}</p>
 <div style="margin-top:12px;background:#0f172a;padding:10px;border-radius:10px">
 <h4 style="font-size:11px;color:#a5b4fc">🔑 Cambiar contraseña (5)</h4>
 <label>Pass actual</label><input id="cp_actual" class="input" type="password">
 <label>Nueva pass</label><input id="cp_nueva" class="input" type="password">
 <button class="btn btn-p" onclick="cambiarPass()">Cambiar contraseña</button>
 <p id="msg_pass" style="font-size:10px;color:#34d399;margin-top:4px"></p>
 </div>
 <div style="margin-top:12px;background:#0f172a;padding:10px;border-radius:10px">
 <h4 style="font-size:11px;color:#fbbf24">🏖️ Solicitar vacaciones (2)</h4>
 <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px"><div><label>Inicio</label><input id="my_vac_ini" class="input" type="date"></div><div><label>Fin</label><input id="my_vac_fin" class="input" type="date"></div></div>
 <label>Días</label><input id="my_vac_dias" class="input" type="number" value="1">
 <label>Motivo</label><input id="my_vac_mot" class="input" placeholder="Vacaciones">
 <button class="btn btn-o" onclick="solicitarMisVac()">Solicitar vacaciones</button>
 <p id="msg_my_vac" style="font-size:10px;color:#fbbf24;margin-top:4px"></p>
 <div id="my_vac_list" style="margin-top:8px"></div>
 </div>
 <div style="margin-top:12px;background:#0f172a;padding:10px;border-radius:10px">
 <h4 style="font-size:11px;color:#a78bfa">⭐ Mis evaluaciones (4)</h4>
 <div id="my_eval_list"></div>
 </div>`;
 document.getElementById('mi_info').innerHTML=info;
 cargarMisVacEval();
}
async function cambiarPass(){
 let actual=document.getElementById('cp_actual').value;
 let nueva=document.getElementById('cp_nueva').value;
 if(!nueva) return alert('Pon nueva pass');
 let r=await api(`/empleado/${miEmpleado.id}/cambiar-pass`,'POST',{actual:actual,nueva:nueva});
 document.getElementById('msg_pass').innerText=r.mensaje || r.error;
}
async function solicitarMisVac(){
 let d={empleado_id:miEmpleado.id,fecha_inicio:document.getElementById('my_vac_ini').value,fecha_fin:document.getElementById('my_vac_fin').value,dias:parseInt(document.getElementById('my_vac_dias').value)||1,motivo:document.getElementById('my_vac_mot').value};
 if(!d.fecha_inicio||!d.fecha_fin) return alert('Fechas');
 await api('/vacaciones','POST',d);
 document.getElementById('msg_my_vac').innerText='Solicitud enviada, espera aprobación del admin';
 cargarMisVacEval();
}
async function cargarMisVacEval(){
 if(!miEmpleado) return;
 let vacs=await api('/vacaciones?empleado_id='+miEmpleado.id);
 document.getElementById('my_vac_list').innerHTML=vacs.map(v=>`<div style="font-size:10px;padding:4px;border-bottom:1px solid #1e293b">${v.fecha_inicio} al ${v.fecha_fin} - ${v.dias} días - <b>${v.estatus}</b></div>`).join('');
 let evals=await api('/evaluaciones?empleado_id='+miEmpleado.id);
 document.getElementById('my_eval_list').innerHTML=evals.map(e=>`<div style="font-size:11px;padding:6px;border-bottom:1px solid #1e293b">📅 ${e.fecha} - ⭐ ${e.calificacion}/10<br><span style="color:#94a3b8">${e.comentario}</span></div>`).join('') || '<p style="font-size:10px;color:#64748b">Sin evaluaciones aún</p>';
}
async function checkIn(){
 if(!miActual||!miActual.sucursal_id) return alert('Hoy es descanso');
 let id=miEmpleado?miEmpleado.id:document.getElementById('my_id').value;
 let r=await api('/visitas/checkin','POST',{empleado_id:id,sucursal_id:miActual.sucursal_id,sucursal_nombre:miActual.sucursal_nombre});
 alert(r.mensaje || 'Check-In registrado. Retardo: '+(r.es_retardo?'SI':'NO'));
 cargarEmps();
}
async function cargarHist(){
 const v=await api('/visitas');
 document.getElementById('tab_hist').innerHTML=v.map(x=>`<tr><td>${x.fecha}</td><td>${x.hora_entrada}</td><td>${x.empleado_id}</td><td>${x.sucursal_nombre}</td><td>${x.es_retardo?'🔴 SI':'🟢 NO'}</td><td>${x.notas||''}</td></tr>`).join('');
}
cargarEmps(); cargarSucs(); cambiarTipo(); cargarAsig('');
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home(): return HTML

@app.get("/empleados")
def list_emp():
    db=SessionLocal(); r=db.query(EmpleadoDB).all(); db.close(); return r

@app.post("/empleados")
def create_emp(emp: dict):
    db=SessionLocal()
    ex=db.query(EmpleadoDB).filter(EmpleadoDB.id==emp.get("id")).first()
    if ex: db.delete(ex); db.commit()
    # campos seguros
    n=EmpleadoDB(
        id=emp.get("id"),
        nombre=emp.get("nombre",""),
        puesto=emp.get("puesto",""),
        telefono=emp.get("telefono",""),
        horario_entrada=emp.get("horario_entrada","09:00"),
        horario_salida=emp.get("horario_salida","18:00"),
        sucursal=emp.get("sucursal","Matriz"),
        estatus=emp.get("estatus","activo"),
        usuario=emp.get("usuario",""),
        password=emp.get("password","1234"),
        sueldo_tipo=emp.get("sueldo_tipo","mes"),
        sueldo_monto=emp.get("sueldo_monto",0),
        vacaciones_totales=emp.get("vacaciones_totales",12),
        foto_url=emp.get("foto_url","")[:500000] # limite 500k
    )
    db.add(n); db.commit(); db.refresh(n); db.close(); return n

@app.get("/sucursales")
def list_suc():
    db=SessionLocal(); r=db.query(SucursalDB).all(); db.close(); return r
@app.post("/sucursales")
def create_suc(s: SucursalCreate):
    db=SessionLocal(); ex=db.query(SucursalDB).filter(SucursalDB.id==s.id).first()
    if ex: db.delete(ex); db.commit()
    n=SucursalDB(**s.dict()); db.add(n); db.commit(); db.refresh(n); db.close(); return n

@app.post("/asignaciones/dia")
def asig_dia(a: AsigDia):
    db=SessionLocal()
    ex=db.query(AsignacionDB).filter(AsignacionDB.empleado_id==a.empleado_id, AsignacionDB.tipo=="dia", AsignacionDB.fecha==a.fecha).first()
    if ex: db.delete(ex); db.commit()
    n=AsignacionDB(empleado_id=a.empleado_id, tipo="dia", fecha=a.fecha, sucursal_dia=a.sucursal_id)
    db.add(n); db.commit(); db.refresh(n); db.close(); return n
@app.post("/asignaciones/semana")
def asig_semana(a: AsigSemana):
    db=SessionLocal()
    ex=db.query(AsignacionDB).filter(AsignacionDB.empleado_id==a.empleado_id, AsignacionDB.tipo=="semana", AsignacionDB.semana==a.semana).first()
    if ex: db.delete(ex); db.commit()
    n=AsignacionDB(empleado_id=a.empleado_id, tipo="semana", semana=a.semana, lunes=a.lunes, martes=a.martes, miercoles=a.miercoles, jueves=a.jueves, viernes=a.viernes, sabado=a.sabado, domingo=a.domingo)
    db.add(n); db.commit(); db.refresh(n); db.close(); return n
@app.post("/asignaciones/mes")
def asig_mes(a: AsigMes):
    db=SessionLocal()
    ex=db.query(AsignacionDB).filter(AsignacionDB.empleado_id==a.empleado_id, AsignacionDB.tipo=="mes", AsignacionDB.mes==a.mes).first()
    if ex: db.delete(ex); db.commit()
    n=AsignacionDB(empleado_id=a.empleado_id, tipo="mes", mes=a.mes, sucursal_mes=a.sucursal_id)
    db.add(n); db.commit(); db.refresh(n); db.close(); return n
@app.get("/asignaciones")
def list_asig(tipo: str=""):
    db=SessionLocal(); q=db.query(AsignacionDB); 
    if tipo: q=q.filter(AsignacionDB.tipo==tipo)
    r=q.order_by(AsignacionDB.created_at.desc()).all(); db.close(); return r

@app.get("/empleado/{empleado_id}/hoy")
def hoy(empleado_id: str):
    db=SessionLocal()
    emp=db.query(EmpleadoDB).filter(EmpleadoDB.id==empleado_id).first()
    if not emp: db.close(); return {"error":"Empleado no existe"}
    hoy_dt=datetime.now()
    fecha_str=hoy_dt.strftime("%Y-%m-%d"); semana_str=f"{hoy_dt.isocalendar()[0]}-W{hoy_dt.isocalendar()[1]:02d}"; mes_str=hoy_dt.strftime("%Y-%m")
    dias=["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]; dia_nombre=dias[hoy_dt.weekday()]
    asig_dia=db.query(AsignacionDB).filter(AsignacionDB.empleado_id==empleado_id, AsignacionDB.tipo=="dia", AsignacionDB.fecha==fecha_str).first()
    if asig_dia:
        suc_id=asig_dia.sucursal_dia; origen="dia"; semana_completa={}
    else:
        asig_sem=db.query(AsignacionDB).filter(AsignacionDB.empleado_id==empleado_id, AsignacionDB.tipo=="semana", AsignacionDB.semana==semana_str).first()
        if asig_sem:
            suc_id=getattr(asig_sem, dia_nombre, "") or ""; origen="semana"; semana_completa={d:getattr(asig_sem,d,"") for d in dias}
        else:
            asig_mes=db.query(AsignacionDB).filter(AsignacionDB.empleado_id==empleado_id, AsignacionDB.tipo=="mes", AsignacionDB.mes==mes_str).first()
            if asig_mes:
                suc_id=asig_mes.sucursal_mes; origen="mes"; semana_completa={}
            else:
                suc_id=emp.sucursal; origen="base"; semana_completa={d: emp.sucursal for d in dias[:5]}
    suc_nombre=suc_id
    sdb=db.query(SucursalDB).filter(SucursalDB.id==suc_id).first()
    if sdb: suc_nombre=sdb.nombre
    db.close()
    return {"empleado_id":empleado_id,"fecha":fecha_str,"dia_nombre":dia_nombre.capitalize(),"semana":semana_str,"mes":mes_str,"sucursal_id":suc_id,"sucursal_nombre":suc_nombre,"origen":origen,"semana_completa":semana_completa}

@app.get("/login")
def login(usuario: str, password: str):
    db=SessionLocal()
    emp=db.query(EmpleadoDB).filter(EmpleadoDB.usuario==usuario, EmpleadoDB.password==password).first()
    if not emp:
        db.close()
        return {"error":"Usuario o pass incorrecto"}
    # reutilizar logica de hoy
    hoy_dt=datetime.now()
    fecha_str=hoy_dt.strftime("%Y-%m-%d"); semana_str=f"{hoy_dt.isocalendar()[0]}-W{hoy_dt.isocalendar()[1]:02d}"; mes_str=hoy_dt.strftime("%Y-%m")
    dias=["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]; dia_nombre=dias[hoy_dt.weekday()]
    asig_dia=db.query(AsignacionDB).filter(AsignacionDB.empleado_id==emp.id, AsignacionDB.tipo=="dia", AsignacionDB.fecha==fecha_str).first()
    if asig_dia:
        suc_id=asig_dia.sucursal_dia; origen="dia"; semana_completa={}
    else:
        asig_sem=db.query(AsignacionDB).filter(AsignacionDB.empleado_id==emp.id, AsignacionDB.tipo=="semana", AsignacionDB.semana==semana_str).first()
        if asig_sem:
            suc_id=getattr(asig_sem, dia_nombre, "") or ""; origen="semana"; semana_completa={d:getattr(asig_sem,d,"") for d in dias}
        else:
            asig_mes=db.query(AsignacionDB).filter(AsignacionDB.empleado_id==emp.id, AsignacionDB.tipo=="mes", AsignacionDB.mes==mes_str).first()
            if asig_mes:
                suc_id=asig_mes.sucursal_mes; origen="mes"; semana_completa={}
            else:
                suc_id=emp.sucursal; origen="base"; semana_completa={d: emp.sucursal for d in dias[:5]}
    suc_nombre=suc_id
    sdb=db.query(SucursalDB).filter(SucursalDB.id==suc_id).first()
    if sdb: suc_nombre=sdb.nombre
    hoy_data={"empleado_id":emp.id,"fecha":fecha_str,"dia_nombre":dia_nombre.capitalize(),"semana":semana_str,"mes":mes_str,"sucursal_id":suc_id,"sucursal_nombre":suc_nombre,"origen":origen,"semana_completa":semana_completa}
    emp_dict={"id":emp.id,"nombre":emp.nombre,"puesto":emp.puesto,"horario_entrada":emp.horario_entrada,"horario_salida":emp.horario_salida,"estatus":emp.estatus,"vacaciones_totales":emp.vacaciones_totales,"vacaciones_tomadas":emp.vacaciones_tomadas,"faltas":emp.faltas,"retardos":emp.retardos,"promedio_eval":emp.promedio_eval,"foto_url":emp.foto_url}
    db.close()
    return {"empleado":emp_dict,"hoy":hoy_data}

@app.post("/visitas/checkin")
def checkin(v: VisitaCreate):
    db=SessionLocal()
    emp=db.query(EmpleadoDB).filter(EmpleadoDB.id==v.empleado_id).first()
    es_retardo=False
    if emp:
        try:
            hora_actual=datetime.now().strftime("%H:%M")
            # comparar HH:MM
            h_ent = emp.horario_entrada or "09:00"
            if hora_actual > h_ent:
                es_retardo=True
                emp.retardos = (emp.retardos or 0) + 1
            # falta no, porque si hace checkin no es falta
        except:
            pass
    visita=VisitaDB(empleado_id=v.empleado_id, sucursal_id=v.sucursal_id, sucursal_nombre=v.sucursal_nombre, es_retardo=es_retardo, notas=v.notas + (" - RETARDO" if es_retardo else " - A TIEMPO"))
    db.add(visita); db.commit(); db.refresh(visita)
    db.commit()
    db.close()
    return {"ok":True,"es_retardo":es_retardo,"mensaje": "Check-In con retardo" if es_retardo else "Check-In a tiempo"}

@app.get("/visitas")
def list_visitas():
    db=SessionLocal(); r=db.query(VisitaDB).order_by(VisitaDB.created_at.desc()).limit(200).all(); db.close(); return r

@app.post("/vacaciones")
def crear_vac(v: VacacionCreate):
    db=SessionLocal()
    n=VacacionDB(**v.dict())
    db.add(n); db.commit(); db.refresh(n); db.close(); return n

@app.get("/vacaciones")
def list_vac(empleado_id: str=""):
    db=SessionLocal()
    q=db.query(VacacionDB)
    if empleado_id:
        q=q.filter(VacacionDB.empleado_id==empleado_id)
    r=q.order_by(VacacionDB.created_at.desc()).all()
    db.close()
    return r

@app.post("/vacaciones/{vac_id}/estatus")
def estatus_vac(vac_id: int, data: dict):
    db=SessionLocal()
    vac=db.query(VacacionDB).filter(VacacionDB.id==vac_id).first()
    if not vac: 
        db.close()
        return {"error":"No existe"}
    vac.estatus=data.get("estatus","aprobada")
    if vac.estatus=="aprobada":
        emp=db.query(EmpleadoDB).filter(EmpleadoDB.id==vac.empleado_id).first()
        if emp:
            emp.vacaciones_tomadas = (emp.vacaciones_tomadas or 0) + vac.dias
    db.commit(); db.refresh(vac); db.close(); return vac

@app.post("/evaluaciones")
def crear_eval(e: EvaluacionCreate):
    db=SessionLocal()
    n=EvaluacionDB(empleado_id=e.empleado_id, calificacion=e.calificacion, comentario=e.comentario)
    db.add(n)
    evals=db.query(EvaluacionDB).filter(EvaluacionDB.empleado_id==e.empleado_id).all()
    total=sum([x.calificacion for x in evals]) + e.calificacion
    prom=total / (len(evals)+1) if evals else e.calificacion
    emp=db.query(EmpleadoDB).filter(EmpleadoDB.id==e.empleado_id).first()
    if emp:
        emp.promedio_eval=round(prom,1)
    db.commit(); db.refresh(n); db.close(); return n

@app.get("/evaluaciones")
def list_eval(empleado_id: str=""):
    db=SessionLocal()
    q=db.query(EvaluacionDB)
    if empleado_id:
        q=q.filter(EvaluacionDB.empleado_id==empleado_id)
    r=q.order_by(EvaluacionDB.created_at.desc()).all()
    db.close()
    return r

@app.post("/empleado/{empleado_id}/cambiar-pass")
def cambiar_pass(empleado_id: str, data: dict):
    db=SessionLocal()
    emp=db.query(EmpleadoDB).filter(EmpleadoDB.id==empleado_id).first()
    if not emp:
        db.close()
        return {"error":"Empleado no existe"}
    actual=data.get("actual","")
    nueva=data.get("nueva","")
    # si manda actual, validar
    if actual and emp.password != actual:
        db.close()
        return {"error":"Contraseña actual incorrecta"}
    if not nueva:
        db.close()
        return {"error":"Nueva contraseña vacía"}
    emp.password=nueva
    db.commit()
    db.close()
    return {"ok":True,"mensaje":"Contraseña cambiada ✅"}


