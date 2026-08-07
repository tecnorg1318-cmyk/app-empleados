
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Text, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./clockrd.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
if "neon.tech" in DATABASE_URL and "sslmode" not in DATABASE_URL:
    DATABASE_URL += "?sslmode=require" if "?" not in DATABASE_URL else "&sslmode=require"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class EmpresaDB(Base):
    __tablename__ = "empresas"
    id = Column(String, primary_key=True) # EMPRESA001
    nombre = Column(String, nullable=False)
    rfc = Column(String, default="")
    telefono = Column(String, default="")
    direccion = Column(String, default="")
    admin_user = Column(String, nullable=False)
    admin_pass = Column(String, default="admin123")
    logo_url = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)

class EmpleadoDB(Base):
    __tablename__ = "empleados"
    id = Column(String, primary_key=True)
    empresa_id = Column(String, default="DEFAULT")
    nombre = Column(String, nullable=False)
    puesto = Column(String, default="")
    telefono = Column(String, default="")
    horario_entrada = Column(String, default="09:00")
    horario_salida = Column(String, default="18:00")
    sucursal = Column(String, default="Matriz")
    nss = Column(String, default="")
    sueldo_tipo = Column(String, default="mes")
    sueldo_monto = Column(Float, default=0.0)
    estatus = Column(String, default="activo")
    foto_url = Column(Text, default="")
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
    empresa_id = Column(String, default="DEFAULT")
    nombre = Column(String, nullable=False)
    direccion = Column(String, default="")

class AsignacionDB(Base):
    __tablename__ = "asignaciones_flexibles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(String, default="DEFAULT")
    empleado_id = Column(String, nullable=False)
    tipo = Column(String, nullable=False)
    fecha = Column(String, default="")
    sucursal_dia = Column(String, default="")
    semana = Column(String, default="")
    lunes = Column(String, default=""); martes = Column(String, default=""); miercoles = Column(String, default=""); jueves = Column(String, default=""); viernes = Column(String, default=""); sabado = Column(String, default=""); domingo = Column(String, default="")
    mes = Column(String, default="")
    sucursal_mes = Column(String, default="")
    created_at = Column(DateTime, default=datetime.now)

class VisitaDB(Base):
    __tablename__ = "historial_visitas"
    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(String, default="DEFAULT")
    empleado_id = Column(String, nullable=False)
    sucursal_id = Column(String, nullable=False)
    sucursal_nombre = Column(String, default="")
    fecha = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d"))
    hora_entrada = Column(String, default=lambda: datetime.now().strftime("%H:%M:%S"))
    es_retardo = Column(Boolean, default=False)
    notas = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)

class VacacionDB(Base):
    __tablename__ = "vacaciones"
    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(String, default="DEFAULT")
    empleado_id = Column(String, nullable=False)
    fecha_inicio = Column(String, nullable=False)
    fecha_fin = Column(String, nullable=False)
    dias = Column(Integer, default=1)
    motivo = Column(String, default="")
    estatus = Column(String, default="pendiente")
    created_at = Column(DateTime, default=datetime.now)

class EvaluacionDB(Base):
    __tablename__ = "evaluaciones"
    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(String, default="DEFAULT")
    empleado_id = Column(String, nullable=False)
    fecha = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d"))
    calificacion = Column(Float, default=0.0)
    comentario = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)

Base.metadata.create_all(bind=engine)
print(f"✅ v11 ULTIMATE lista")

app = FastAPI(title="Control v11 ULTIMATE")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class EmpresaCreate(BaseModel):
    id: str; nombre: str; rfc: str=""; telefono: str=""; direccion: str=""; admin_user: str; admin_pass: str="admin123"
class EmpleadoCreate(BaseModel):
    id: str; empresa_id: str="DEFAULT"; nombre: str; puesto: str=""; telefono: str=""; horario_entrada: str="09:00"; horario_salida: str="18:00"; sucursal: str="Matriz"; nss: str=""; sueldo_tipo: str="mes"; sueldo_monto: float=0; usuario: str=""; password: str="1234"; estatus: str="activo"; vacaciones_totales: int=12; foto_url: str=""
class SucursalCreate(BaseModel):
    id: str; empresa_id: str="DEFAULT"; nombre: str; direccion: str=""
class AsigDia(BaseModel):
    empresa_id: str="DEFAULT"; empleado_id: str; fecha: str; sucursal_id: str
class AsigSemana(BaseModel):
    empresa_id: str="DEFAULT"; empleado_id: str; semana: str; lunes: str=""; martes: str=""; miercoles: str=""; jueves: str=""; viernes: str=""; sabado: str=""; domingo: str=""
class AsigMes(BaseModel):
    empresa_id: str="DEFAULT"; empleado_id: str; mes: str; sucursal_id: str
class VisitaCreate(BaseModel):
    empresa_id: str="DEFAULT"; empleado_id: str; sucursal_id: str; sucursal_nombre: str=""; notas: str=""
class VacacionCreate(BaseModel):
    empresa_id: str="DEFAULT"; empleado_id: str; fecha_inicio: str; fecha_fin: str; dias: int=1; motivo: str=""
class EvaluacionCreate(BaseModel):
    empresa_id: str="DEFAULT"; empleado_id: str; calificacion: float; comentario: str=""

HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>v11 ULTIMATE - Empresa + Admin + Empleado</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Inter',sans-serif}
body{background:#0f172a;color:#e2e8f0}
.hero{background:linear-gradient(135deg,#6366f1,#8b5cf6,#ec4899);padding:20px;text-align:center}
.card{background:#1e293b;border:1px solid #334155;border-radius:16px;padding:16px;margin-top:12px}
.input,.select{width:100%;padding:9px;border-radius:8px;border:1px solid #334155;background:#0f172a;color:white;margin-top:4px;font-size:12px}
.btn{padding:9px 12px;border-radius:8px;border:none;font-weight:700;font-size:11px;cursor:pointer;width:100%;margin-top:8px}
.btn-p{background:#6366f1;color:white}
.btn-g{background:#10b981;color:white}
.btn-o{background:#f59e0b;color:white}
.btn-d{background:#0f172a;color:white;border:1px solid #334155}
.tabs{display:flex;gap:6px;flex-wrap:wrap;padding:10px}
.tab{padding:8px 12px;background:#1e293b;border:1px solid #334155;border-radius:8px;cursor:pointer;font-size:11px;font-weight:700}
.tab.active{background:#6366f1;color:white}
.table{width:100%;font-size:11px;border-collapse:collapse;margin-top:8px}
.table th{color:#64748b;text-align:left;font-size:9px;padding:5px;border-bottom:1px solid #334155}
.table td{padding:5px;border-bottom:1px solid #1e293b}
.login-box{max-width:420px;margin:60px auto;background:#1e293b;border-radius:20px;padding:24px;border:1px solid #334155}
.badge{padding:2px 6px;border-radius:10px;font-size:9px;font-weight:700}
.kpi{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:10px}
@media(max-width:800px){.kpi{grid-template-columns:1fr 1fr}}
.kpi .card{text-align:center}
.kpi h2{font-size:22px;color:white}
</style>
</head>
<body>
<div id="login-screen">
<div class="login-box">
<h2 style="color:white;text-align:center">🏢 Control Empleados v11</h2>
<p style="font-size:11px;text-align:center;color:#94a3b8;margin-top:4px">Empresa + Admin + Empleado + Asignación Flexible</p>

<div style="margin-top:18px;display:flex;gap:6px">
<button class="btn btn-p" onclick="setLogin('empresa')" id="btn-log-empresa">Empresa Admin</button>
<button class="btn btn-d" onclick="setLogin('empleado')" id="btn-log-empleado">Empleado</button>
<button class="btn btn-d" onclick="setLogin('crear')" id="btn-log-crear">Crear Empresa</button>
</div>

<div id="form-empresa-login">
<label>Empresa ID</label><input id="l_emp_id" class="input" placeholder="EMPRESA001">
<label>Usuario Admin</label><input id="l_user" class="input" placeholder="admin">
<label>Password</label><input id="l_pass" class="input" type="password" placeholder="admin123">
<button class="btn btn-p" onclick="loginEmpresa()">Entrar como Empresa ADMIN 🔐</button>
<p id="msg_login" style="font-size:11px;color:#f87171;margin-top:6px"></p>
</div>

<div id="form-empleado-login" style="display:none">
<label>Empresa ID</label><input id="le_emp_id" class="input" placeholder="EMPRESA001">
<label>Usuario Empleado</label><input id="le_user" class="input" placeholder="juan">
<label>Password</label><input id="le_pass" class="input" type="password" value="1234">
<button class="btn btn-g" onclick="loginEmpleado()">Entrar como Empleado 📱</button>
<p id="msg_login_e" style="font-size:11px;color:#f87171;margin-top:6px"></p>
</div>

<div id="form-crear-empresa" style="display:none">
<label>ID Empresa (único)</label><input id="c_id" class="input" placeholder="EMPRESA001">
<label>Nombre Empresa</label><input id="c_nombre" class="input" placeholder="Mi Empresa SA">
<label>RFC</label><input id="c_rfc" class="input" placeholder="XAXX010101000">
<label>Tel</label><input id="c_tel" class="input">
<label>Usuario Admin</label><input id="c_user" class="input" placeholder="admin">
<label>Password Admin</label><input id="c_pass" class="input" value="admin123">
<button class="btn btn-p" onclick="crearEmpresa()">Crear Empresa ✅</button>
<p id="msg_crear" style="font-size:11px;color:#34d399;margin-top:6px"></p>
</div>
</div>
</div>

<div id="app-screen" style="display:none">
<div class="hero">
<div style="display:flex;justify-content:space-between;align-items:center">
<div><h1 id="hero_title" style="color:white;font-size:20px;font-weight:800">Empresa</h1><p id="hero_sub" style="color:white;opacity:.8;font-size:11px"></p></div>
<button class="btn btn-d" style="width:auto" onclick="logout()">Salir</button>
</div>
</div>

<div id="admin-tabs" class="tabs">
<div class="tab active" onclick="show('dash')">📊 Dashboard</div>
<div class="tab" onclick="show('emp')">👥 Empleados</div>
<div class="tab" onclick="show('asig')">🗓️ Asignar Día/Sem/Mes</div>
<div class="tab" onclick="show('suc')">🏪 Sucursales</div>
<div class="tab" onclick="show('vac')">🏖️ Vacaciones</div>
<div class="tab" onclick="show('eval')">⭐ Evaluaciones</div>
<div class="tab" onclick="show('hist')">🔒 Historial + Reporte</div>
</div>

<div id="empleado-tabs" class="tabs" style="display:none">
<div class="tab active" onclick="showE('mi')">📱 Mi Día</div>
</div>

<div style="padding:0 16px 40px;max-width:1350px;margin:0 auto">

<!-- DASHBOARD -->
<div id="sec-dash">
<div class="kpi">
<div class="card"><h2 id="kpi_total">0</h2><p style="font-size:10px">Total Empleados</p></div>
<div class="card"><h2 id="kpi_act">0</h2><p style="font-size:10px">Activos</p></div>
<div class="card"><h2 id="kpi_falta">0</h2><p style="font-size:10px">Faltas hoy (sin check)</p></div>
<div class="card"><h2 id="kpi_vac">0</h2><p style="font-size:10px">Vacaciones pendientes</p></div>
</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px">
<div class="card"><h3>🔴 Quién faltó hoy (no hizo check-in)</h3><div id="dash_faltas"></div><button class="btn btn-d" onclick="cargarDashboard()">Actualizar</button></div>
<div class="card"><h3>🔔 Notificaciones</h3><div id="dash_notis" style="font-size:11px"></div></div>
</div>
</div>

<div id="sec-emp" style="display:none">
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
<div class="card">
<h3>👥 Crear / Editar empleado</h3>
<label>ID</label><input id="e_id" class="input" placeholder="EMP001">
<label>Nombre</label><input id="e_nom" class="input">
<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px"><div><label>Puesto</label><input id="e_pue" class="input"></div><div><label>Tel</label><input id="e_tel" class="input"></div></div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px"><div><label>Entrada</label><input id="e_he" class="input" type="time" value="09:00"></div><div><label>Salida</label><input id="e_hs" class="input" type="time" value="18:00"></div></div>
<label>Sucursal base</label><select id="e_suc" class="select"></select>
<label>Estatus</label><select id="e_est" class="select"><option value="activo">Activo</option><option value="baja">Baja</option><option value="vacaciones">Vacaciones</option><option value="incapacidad">Incapacidad</option></select>
<label>Foto</label><input id="e_foto" class="input" type="file" accept="image/*">
<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px"><div><label>Usuario</label><input id="e_user" class="input"></div><div><label>Pass</label><input id="e_pass" class="input" value="1234"></div></div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px"><div><label>Tipo sueldo</label><select id="e_tipo" class="select"><option value="hora">Hora</option><option value="quincena">Quincena</option><option value="mes" selected>Mes</option></select></div><div><label>Monto</label><input id="e_monto" class="input" type="number"></div></div>
<label>Vac totales</label><input id="e_vactot" class="input" type="number" value="12">
<button class="btn btn-p" onclick="crearEmp()">Guardar empleado</button>
<button class="btn btn-d" onclick="limpiarEmp()">Limpiar / Nuevo</button>
<p id="msg_e" style="font-size:10px;color:#34d399"></p>
</div>
<div class="card"><h3>Empleados (click para editar, con eliminar)</h3><table class="table"><thead><tr><th>Foto</th><th>ID/Nombre</th><th>Estatus</th><th>F/R</th><th>Acción</th></tr></thead><tbody id="tab_emp"></tbody></table></div>
</div>
</div>

<div id="sec-asig" style="display:none">
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
<div class="card">
<h3>🗓️ Asignar Día/Sem/Mes</h3>
<label>Tipo</label><select id="tipo" class="select" onchange="cambiarTipo()"><option value="dia">DÍA</option><option value="semana" selected>SEMANA</option><option value="mes">MES</option></select>
<label>Empleado</label><select id="as_emp" class="select"></select>
<div id="box-dia" style="display:none"><label>Fecha</label><input id="as_fecha" class="input" type="date"><label>Sucursal</label><select id="as_suc_dia" class="select"></select><button class="btn btn-p" onclick="guardarDia()">Guardar DÍA</button></div>
<div id="box-semana"><label>Semana</label><input id="as_semana" class="input" type="week"><div style="display:grid;grid-template-columns:1fr 1fr;gap:5px"><div><label>Lun</label><select id="s_lun" class="select"></select></div><div><label>Mar</label><select id="s_mar" class="select"></select></div><div><label>Mié</label><select id="s_mie" class="select"></select></div><div><label>Jue</label><select id="s_jue" class="select"></select></div><div><label>Vie</label><select id="s_vie" class="select"></select></div><div><label>Sáb</label><select id="s_sab" class="select"></select></div><div><label>Dom</label><select id="s_dom" class="select"></select></div></div><button class="btn btn-p" onclick="guardarSemana()">Guardar SEMANA</button></div>
<div id="box-mes" style="display:none"><label>Mes</label><input id="as_mes" class="input" type="month"><label>Sucursal mes</label><select id="as_suc_mes" class="select"></select><button class="btn btn-p" onclick="guardarMes()">Guardar MES</button></div>
<p id="msg_as" style="font-size:10px;color:#34d399"></p>
</div>
<div class="card"><h3>Asignaciones</h3><div style="display:flex;gap:4px"><button class="btn btn-d" style="width:auto;padding:5px 8px" onclick="cargarAsig('')">TODO</button><button class="btn btn-d" style="width:auto;padding:5px 8px" onclick="cargarAsig('dia')">DÍA</button><button class="btn btn-d" style="width:auto;padding:5px 8px" onclick="cargarAsig('semana')">SEM</button><button class="btn btn-d" style="width:auto;padding:5px 8px" onclick="cargarAsig('mes')">MES</button></div><div id="lista_asig" style="max-height:600px;overflow:auto"></div></div>
</div>
</div>

<div id="sec-suc" style="display:none"><div style="display:grid;grid-template-columns:1fr 1fr;gap:12px"><div class="card"><h3>🏪 Nueva sucursal</h3><label>ID</label><input id="suc_id" class="input"><label>Nombre</label><input id="suc_nom" class="input"><button class="btn btn-p" onclick="crearSuc()">Crear</button></div><div class="card"><h3>Sucursales</h3><table class="table"><thead><tr><th>ID</th><th>Nombre</th></tr></thead><tbody id="tab_suc"></tbody></table></div></div></div>

<div id="sec-vac" style="display:none"><div style="display:grid;grid-template-columns:1fr 1fr;gap:12px"><div class="card"><h3>🏖️ Crear vacaciones (admin)</h3><label>Empleado</label><select id="vac_emp" class="select"></select><div style="display:grid;grid-template-columns:1fr 1fr;gap:6px"><div><label>Inicio</label><input id="vac_ini" class="input" type="date"></div><div><label>Fin</label><input id="vac_fin" class="input" type="date"></div></div><label>Días</label><input id="vac_dias" class="input" type="number" value="1"><button class="btn btn-p" onclick="crearVac()">Guardar</button></div><div class="card"><h3>Solicitudes</h3><table class="table"><thead><tr><th>Emp</th><th>Fechas</th><th>Días</th><th>Est</th><th>Acción</th></tr></thead><tbody id="tab_vac"></tbody></table></div></div></div>

<div id="sec-eval" style="display:none"><div style="display:grid;grid-template-columns:1fr 1fr;gap:12px"><div class="card"><h3>⭐ Evaluar</h3><label>Empleado</label><select id="eval_emp" class="select"></select><label>Cal 1-10</label><input id="eval_cal" class="input" type="number" min="1" max="10"><label>Comentario</label><textarea id="eval_com" class="input" rows="3"></textarea><button class="btn btn-p" onclick="crearEval()">Guardar evaluación</button></div><div class="card"><h3>Evaluaciones</h3><table class="table"><thead><tr><th>Fecha</th><th>Emp</th><th>Cal</th><th>Com</th></tr></thead><tbody id="tab_eval"></tbody></table></div></div></div>

<div id="sec-hist" style="display:none">
<div class="card" style="border:1px dashed #f59e0b"><h3>🔒 Historial + Reporte Nómina (ADMIN)</h3>
<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px">
<button class="btn btn-d" style="width:auto" onclick="cargarHist()">🔄 Historial</button>
<button class="btn btn-o" style="width:auto" onclick="descargarReporte()">📥 Descargar Reporte Nómina CSV</button>
</div>
<table class="table"><thead><tr><th>Fecha</th><th>Hora</th><th>Emp</th><th>Suc</th><th>Ret</th><th>Nota</th></tr></thead><tbody id="tab_hist"></tbody></table>
<div style="margin-top:12px;background:#0f172a;padding:10px;border-radius:10px"><h4 style="font-size:11px">Reporte nómina estimado</h4><div id="reporte_box" style="font-size:11px;margin-top:6px"></div></div>
</div>
</div>

<!-- EMPLEADO VIEW -->
<div id="sec-mi" style="display:none">
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
<div class="card" style="border:2px solid #10b981"><h3>📱 Mi Día</h3><div id="mi_box"></div></div>
<div class="card"><h3>Mi info + Acciones empleado</h3><div id="mi_info"></div><button class="btn btn-g" onclick="checkIn()">✅ Check-In hoy</button></div>
</div>
</div>

</div>
</div>

<script>
let EMPRESA_ID = localStorage.getItem('empresa_id') || '';
let EMPRESA_NOM = localStorage.getItem('empresa_nombre') || '';
let ROLE = localStorage.getItem('role') || '';
let MI_EMPLEADO = null;
let MI_HOY = null;
const API="";
async function api(p,m="GET",b=null){const o={method:m,headers:{"Content-Type":"application/json"}}; if(b) o.body=JSON.stringify(b); const r=await fetch(API+p,o); return r.json();}

function setLogin(t){
 document.getElementById('form-empresa-login').style.display=t==='empresa'?'block':'none';
 document.getElementById('form-empleado-login').style.display=t==='empleado'?'block':'none';
 document.getElementById('form-crear-empresa').style.display=t==='crear'?'block':'none';
}

async function crearEmpresa(){
 const d={id:document.getElementById('c_id').value,nombre:document.getElementById('c_nombre').value,rfc:document.getElementById('c_rfc').value,telefono:document.getElementById('c_tel').value,admin_user:document.getElementById('c_user').value,admin_pass:document.getElementById('c_pass').value};
 if(!d.id||!d.nombre||!d.admin_user) return alert('ID, nombre y usuario admin');
 let r=await api('/empresas','POST',d);
 if(r.error){document.getElementById('msg_crear').innerText=r.error; return;}
 document.getElementById('msg_crear').innerText='✅ Empresa creada, ahora logueate como empresa admin';
 setLogin('empresa');
 document.getElementById('l_emp_id').value=d.id;
}

async function loginEmpresa(){
 let emp_id=document.getElementById('l_emp_id').value;
 let user=document.getElementById('l_user').value;
 let pass=document.getElementById('l_pass').value;
 let r=await api(`/login-empresa?empresa_id=${emp_id}&usuario=${user}&password=${pass}`);
 if(r.error){document.getElementById('msg_login').innerText=r.error; return;}
 localStorage.setItem('empresa_id',emp_id);
 localStorage.setItem('empresa_nombre',r.nombre);
 localStorage.setItem('role','admin');
 location.reload();
}

async function loginEmpleado(){
 let emp_id=document.getElementById('le_emp_id').value;
 let user=document.getElementById('le_user').value;
 let pass=document.getElementById('le_pass').value;
 let r=await api(`/login-empleado?empresa_id=${emp_id}&usuario=${user}&password=${pass}`);
 if(r.error){document.getElementById('msg_login_e').innerText=r.error; return;}
 localStorage.setItem('empresa_id',emp_id);
 localStorage.setItem('empresa_nombre',r.empresa_nombre||emp_id);
 localStorage.setItem('role','empleado');
 localStorage.setItem('empleado_id',r.empleado.id);
 localStorage.setItem('empleado_data',JSON.stringify(r));
 location.reload();
}

function logout(){
 localStorage.clear(); location.reload();
}

function init(){
 let eid=localStorage.getItem('empresa_id');
 let role=localStorage.getItem('role');
 if(!eid || !role){
   document.getElementById('login-screen').style.display='block';
   document.getElementById('app-screen').style.display='none';
   return;
 }
 EMPRESA_ID=eid; ROLE=role;
 document.getElementById('login-screen').style.display='none';
 document.getElementById('app-screen').style.display='block';
 document.getElementById('hero_title').innerText=localStorage.getItem('empresa_nombre') || eid;
 document.getElementById('hero_sub').innerText=role==='admin'?'ADMIN EMPRESA':'EMPLEADO - '+eid;
 if(role==='admin'){
   document.getElementById('admin-tabs').style.display='flex';
   document.getElementById('empleado-tabs').style.display='none';
   show('dash');
   cargarEmps(); cargarSucs(); cargarDashboard();
 } else {
   document.getElementById('admin-tabs').style.display='none';
   document.getElementById('empleado-tabs').style.display='flex';
   // cargar datos empleado guardados
   try{
     let data=JSON.parse(localStorage.getItem('empleado_data'));
     MI_EMPLEADO=data.empleado; MI_HOY=data.hoy;
     renderMiDia();
   }catch(e){ showE('mi'); loginEmpleadoReload(); }
 }
}

function show(s){
 document.querySelectorAll('[id^=sec-]').forEach(d=>d.style.display='none');
 document.getElementById('sec-'+s).style.display=s==='dash'?'block':'grid';
 if(s==='dash') cargarDashboard();
 if(s==='emp') cargarEmps();
 if(s==='suc') cargarSucs();
 if(s==='vac'){cargarEmps(); cargarVac();}
 if(s==='eval'){cargarEmps(); cargarEval();}
 if(s==='hist'){cargarHist(); cargarReporte();}
 if(s==='asig'){cargarEmps(); cargarSucs(); cargarAsig('');}
}
function showE(s){
 document.querySelectorAll('[id^=sec-]').forEach(d=>d.style.display='none');
 document.getElementById('sec-'+s).style.display='block';
}

function cambiarTipo(){
 const t=document.getElementById('tipo').value;
 document.getElementById('box-dia').style.display=t==='dia'?'block':'none';
 document.getElementById('box-semana').style.display=t==='semana'?'block':'none';
 document.getElementById('box-mes').style.display=t==='mes'?'block':'none';
}

async function cargarEmps(){
 const emps=await api('/empleados?empresa_id='+EMPRESA_ID);
 document.getElementById('tab_emp').innerHTML=emps.map(e=>{
   let foto=e.foto_url?`<img src="${e.foto_url}" style="width:28px;height:28px;border-radius:50%;object-fit:cover">`:`<div style="width:28px;height:28px;border-radius:50%;background:#334155;display:flex;align-items:center;justify-content:center;font-size:10px">${e.nombre.charAt(0)}</div>`;
   return `<tr><td>${foto}</td><td onclick="editarEmp('${e.id}')" style="cursor:pointer"><b>${e.id}</b><br>${e.nombre}<br><small>${e.puesto}</small></td><td><span class="badge" style="background:#1e293b;border:1px solid #334155">${e.estatus}</span><br><small>V:${e.vacaciones_tomadas}/${e.vacaciones_totales}</small></td><td>F:${e.faltas} R:${e.retardos}</td><td><button onclick="editarEmp('${e.id}')" class="btn btn-d" style="padding:4px 6px;width:auto">✏️</button> <button onclick="eliminarEmp('${e.id}')" class="btn btn-d" style="padding:4px 6px;width:auto;color:#f87171">🗑️</button></td></tr>`;
 }).join('');
 document.getElementById('as_emp').innerHTML=emps.map(e=>`<option value="${e.id}">${e.nombre}</option>`).join('');
 document.getElementById('vac_emp').innerHTML=document.getElementById('as_emp').innerHTML;
 document.getElementById('eval_emp').innerHTML=document.getElementById('as_emp').innerHTML;
}

async function cargarSucs(){
 const sucs=await api('/sucursales?empresa_id='+EMPRESA_ID);
 document.getElementById('tab_suc').innerHTML=sucs.map(s=>`<tr><td>${s.id}</td><td>${s.nombre}</td></tr>`).join('');
 const opts=sucs.map(s=>`<option value="${s.id}">${s.nombre}</option>`).join('');
 document.getElementById('e_suc').innerHTML=opts;
 document.getElementById('as_suc_dia').innerHTML=opts; document.getElementById('as_suc_mes').innerHTML=opts;
 ['s_lun','s_mar','s_mie','s_jue','s_vie','s_sab','s_dom'].forEach(id=>{let el=document.getElementById(id); if(el) el.innerHTML='<option value="">Descanso</option>'+opts;});
}

async function crearEmp(){
 const file=document.getElementById('e_foto').files[0];
 let fotoB64="";
 if(file){ fotoB64=await new Promise(res=>{let r=new FileReader(); r.onload=e=>res(e.target.result); r.readAsDataURL(file);}); }
 const d={id:document.getElementById('e_id').value,empresa_id:EMPRESA_ID,nombre:document.getElementById('e_nom').value,puesto:document.getElementById('e_pue').value,telefono:document.getElementById('e_tel').value,horario_entrada:document.getElementById('e_he').value,horario_salida:document.getElementById('e_hs').value,sucursal:document.getElementById('e_suc').value,estatus:document.getElementById('e_est').value,usuario:document.getElementById('e_user').value,password:document.getElementById('e_pass').value,sueldo_tipo:document.getElementById('e_tipo').value,sueldo_monto:parseFloat(document.getElementById('e_monto').value)||0,vacaciones_totales:parseInt(document.getElementById('e_vactot').value)||12,foto_url:fotoB64};
 if(!d.id||!d.nombre) return alert('ID y nombre');
 await api('/empleados','POST',d); document.getElementById('msg_e').innerText='Guardado ✅'; cargarEmps(); cargarDashboard();
}
function limpiarEmp(){
 document.getElementById('e_id').value=''; document.getElementById('e_nom').value=''; document.getElementById('e_pue').value='';
}
async function editarEmp(id){
 let emps=await api('/empleados?empresa_id='+EMPRESA_ID);
 let e=emps.find(x=>x.id===id); if(!e) return;
 document.getElementById('e_id').value=e.id; document.getElementById('e_nom').value=e.nombre; document.getElementById('e_pue').value=e.puesto; document.getElementById('e_tel').value=e.telefono; document.getElementById('e_he').value=e.horario_entrada; document.getElementById('e_hs').value=e.horario_salida; document.getElementById('e_suc').value=e.sucursal; document.getElementById('e_est').value=e.estatus; document.getElementById('e_user').value=e.usuario; document.getElementById('e_pass').value=e.password; document.getElementById('e_tipo').value=e.sueldo_tipo; document.getElementById('e_monto').value=e.sueldo_monto; document.getElementById('e_vactot').value=e.vacaciones_totales;
 window.scrollTo(0,0);
}
async function eliminarEmp(id){
 if(!confirm('¿Eliminar '+id+'?')) return;
 await api('/empleados/'+id+'?empresa_id='+EMPRESA_ID,'DELETE'); cargarEmps(); cargarDashboard();
}
async function crearSuc(){
 const d={id:document.getElementById('suc_id').value,empresa_id:EMPRESA_ID,nombre:document.getElementById('suc_nom').value};
 await api('/sucursales','POST',d); cargarSucs();
}
async function guardarDia(){ const d={empresa_id:EMPRESA_ID,empleado_id:document.getElementById('as_emp').value,fecha:document.getElementById('as_fecha').value,sucursal_id:document.getElementById('as_suc_dia').value}; await api('/asignaciones/dia','POST',d); document.getElementById('msg_as').innerText='Día guardado'; cargarAsig('dia'); }
async function guardarSemana(){ const d={empresa_id:EMPRESA_ID,empleado_id:document.getElementById('as_emp').value,semana:document.getElementById('as_semana').value,lunes:document.getElementById('s_lun').value,martes:document.getElementById('s_mar').value,miercoles:document.getElementById('s_mie').value,jueves:document.getElementById('s_jue').value,viernes:document.getElementById('s_vie').value,sabado:document.getElementById('s_sab').value,domingo:document.getElementById('s_dom').value}; await api('/asignaciones/semana','POST',d); document.getElementById('msg_as').innerText='Semana guardada'; cargarAsig('semana'); }
async function guardarMes(){ const d={empresa_id:EMPRESA_ID,empleado_id:document.getElementById('as_emp').value,mes:document.getElementById('as_mes').value,sucursal_id:document.getElementById('as_suc_mes').value}; await api('/asignaciones/mes','POST',d); document.getElementById('msg_as').innerText='Mes guardado'; cargarAsig('mes'); }
async function cargarAsig(f){ let url='/asignaciones?empresa_id='+EMPRESA_ID; if(f) url+='&tipo='+f; const list=await api(url); document.getElementById('lista_asig').innerHTML=list.map(a=>{ if(a.tipo==='dia') return `<div class="card" style="padding:8px;margin-top:6px;border-left:4px solid #38bdf8">📅 ${a.fecha} (${a.empleado_id}) → ${a.sucursal_dia}</div>`; if(a.tipo==='semana') return `<div class="card" style="padding:8px;margin-top:6px;border-left:4px solid #a78bfa">🗓️ ${a.semana} (${a.empleado_id}) L:${a.lunes||'-'} M:${a.martes||'-'} X:${a.miercoles||'-'} J:${a.jueves||'-'} V:${a.viernes||'-'}</div>`; if(a.tipo==='mes') return `<div class="card" style="padding:8px;margin-top:6px;border-left:4px solid #fb923c">📆 ${a.mes} (${a.empleado_id}) → ${a.sucursal_mes}</div>`; }).join(''); }

async function crearVac(){ const d={empresa_id:EMPRESA_ID,empleado_id:document.getElementById('vac_emp').value,fecha_inicio:document.getElementById('vac_ini').value,fecha_fin:document.getElementById('vac_fin').value,dias:parseInt(document.getElementById('vac_dias').value)||1,motivo:''}; await api('/vacaciones','POST',d); cargarVac(); }
async function cargarVac(){ const v=await api('/vacaciones?empresa_id='+EMPRESA_ID); document.getElementById('tab_vac').innerHTML=v.map(x=>`<tr><td>${x.empleado_id}</td><td>${x.fecha_inicio} al ${x.fecha_fin}</td><td>${x.dias}</td><td>${x.estatus}</td><td><button onclick="aprobarVac(${x.id},'aprobada')" class="btn btn-g" style="padding:4px 6px;width:auto">✔</button> <button onclick="aprobarVac(${x.id},'rechazada')" class="btn btn-p" style="padding:4px 6px;width:auto">✖</button></td></tr>`).join(''); }
async function aprobarVac(id,est){ await api('/vacaciones/'+id+'/estatus?empresa_id='+EMPRESA_ID,'POST',{estatus:est}); cargarVac(); cargarEmps(); cargarDashboard(); }

async function crearEval(){ const d={empresa_id:EMPRESA_ID,empleado_id:document.getElementById('eval_emp').value,calificacion:parseFloat(document.getElementById('eval_cal').value)||0,comentario:document.getElementById('eval_com').value}; await api('/evaluaciones','POST',d); cargarEval(); cargarEmps(); }
async function cargarEval(){ const e=await api('/evaluaciones?empresa_id='+EMPRESA_ID); document.getElementById('tab_eval').innerHTML=e.map(x=>`<tr><td>${x.fecha}</td><td>${x.empleado_id}</td><td>⭐ ${x.calificacion}</td><td>${x.comentario}</td></tr>`).join(''); }

async function cargarHist(){ const v=await api('/visitas?empresa_id='+EMPRESA_ID); document.getElementById('tab_hist').innerHTML=v.map(x=>`<tr><td>${x.fecha}</td><td>${x.hora_entrada}</td><td>${x.empleado_id}</td><td>${x.sucursal_nombre}</td><td>${x.es_retardo?'🔴':'🟢'}</td><td>${x.notas||''}</td></tr>`).join(''); }
async function cargarReporte(){ const r=await api('/reporte?empresa_id='+EMPRESA_ID); document.getElementById('reporte_box').innerHTML=r.map(e=>`<div style="padding:6px;border-bottom:1px solid #1e293b"><b>${e.nombre}</b> - Sueldo $${e.sueldo_monto} ${e.sueldo_tipo} - Faltas:${e.faltas} Ret:${e.retardos} - Vac:${e.vacaciones_tomadas}/${e.vacaciones_totales} - Eval:${e.promedio_eval}</div>`).join(''); }
function descargarReporte(){ window.open('/reporte/csv?empresa_id='+EMPRESA_ID,'_blank'); }

async function cargarDashboard(){
 const emps=await api('/empleados?empresa_id='+EMPRESA_ID);
 const vacs=await api('/vacaciones?empresa_id='+EMPRESA_ID);
 const visitas=await api('/visitas?empresa_id='+EMPRESA_ID);
 let hoy=new Date().toISOString().slice(0,10);
 let visitasHoy=visitas.filter(v=>v.fecha===hoy).map(v=>v.empleado_id);
 let faltasHoy=emps.filter(e=>e.estatus==='activo' && !visitasHoy.includes(e.id));
 document.getElementById('kpi_total').innerText=emps.length;
 document.getElementById('kpi_act').innerText=emps.filter(e=>e.estatus==='activo').length;
 document.getElementById('kpi_falta').innerText=faltasHoy.length;
 document.getElementById('kpi_vac').innerText=vacs.filter(v=>v.estatus==='pendiente').length;
 document.getElementById('dash_faltas').innerHTML=faltasHoy.map(e=>`<div style="padding:6px;border-bottom:1px solid #1e293b">🔴 ${e.nombre} (${e.id}) - ${e.sucursal}</div>`).join('') || '<p style="font-size:11px;color:#34d399">Todos hicieron check hoy ✅</p>';
 let notis=[];
 vacs.filter(v=>v.estatus==='pendiente').forEach(v=>notis.push(`🏖️ Vacaciones pendientes: ${v.empleado_id} del ${v.fecha_inicio} al ${v.fecha_fin}`));
 visitas.filter(v=>v.es_retardo && v.fecha===hoy).forEach(v=>notis.push(`⏰ Retardo hoy: ${v.empleado_id} a las ${v.hora_entrada} en ${v.sucursal_nombre}`));
 document.getElementById('dash_notis').innerHTML=notis.map(n=>`<div style="padding:6px;border-bottom:1px solid #1e293b">${n}</div>`).join('') || '<p style="color:#34d399">Sin notificaciones ✅</p>';
}

function renderMiDia(){
 if(!MI_EMPLEADO || !MI_HOY) return;
 document.getElementById('mi_box').innerHTML=`<div style="background:#0f172a;padding:12px;border-radius:10px;border:1px solid #10b981"><p style="color:#10b981;font-weight:800">${MI_HOY.dia_nombre} ${MI_HOY.fecha} - ${MI_HOY.origen}</p><h3 style="color:white">${MI_HOY.sucursal_nombre||'Descanso'}</h3></div>`;
 document.getElementById('mi_info').innerHTML=`<p><b>${MI_EMPLEADO.nombre}</b><br>Estatus:${MI_EMPLEADO.estatus}<br>Vac:${MI_EMPLEADO.vacaciones_tomadas}/${MI_EMPLEADO.vacaciones_totales}<br>F:${MI_EMPLEADO.faltas} R:${MI_EMPLEADO.retardos}<br>Eval:${MI_EMPLEADO.promedio_eval}</p>
 <div style="margin-top:10px;background:#0f172a;padding:10px;border-radius:10px"><h4 style="font-size:11px">🔑 Cambiar pass</h4><label>Nueva</label><input id="cp_nueva" class="input" type="password"><button class="btn btn-p" onclick="cambiarPassEmp()">Cambiar</button><p id="msg_pass" style="font-size:10px;color:#34d399"></p></div>
 <div style="margin-top:10px;background:#0f172a;padding:10px;border-radius:10px"><h4 style="font-size:11px">🏖️ Pedir vacaciones</h4><div style="display:grid;grid-template-columns:1fr 1fr;gap:6px"><div><label>Ini</label><input id="my_vac_ini" class="input" type="date"></div><div><label>Fin</label><input id="my_vac_fin" class="input" type="date"></div></div><label>Días</label><input id="my_vac_dias" class="input" type="number" value="1"><button class="btn btn-o" onclick="pedirVacEmp()">Solicitar</button><div id="my_vac_list" style="margin-top:6px"></div></div>
 <div style="margin-top:10px;background:#0f172a;padding:10px;border-radius:10px"><h4 style="font-size:11px">⭐ Mis evaluaciones</h4><div id="my_eval_list"></div></div>`;
 cargarMisVacEvalEmp();
}
async function cargarMisVacEvalEmp(){
 if(!MI_EMPLEADO) return;
 let vacs=await api('/vacaciones?empresa_id='+EMPRESA_ID+'&empleado_id='+MI_EMPLEADO.id);
 document.getElementById('my_vac_list').innerHTML=vacs.map(v=>`<div style="font-size:10px;padding:4px;border-bottom:1px solid #1e293b">${v.fecha_inicio} al ${v.fecha_fin} - ${v.dias}d - <b>${v.estatus}</b></div>`).join('');
 let evals=await api('/evaluaciones?empresa_id='+EMPRESA_ID+'&empleado_id='+MI_EMPLEADO.id);
 document.getElementById('my_eval_list').innerHTML=evals.map(e=>`<div style="font-size:11px;padding:6px;border-bottom:1px solid #1e293b">📅 ${e.fecha} - ⭐ ${e.calificacion}<br><span style="color:#94a3b8">${e.comentario}</span></div>`).join('') || '<p style="font-size:10px;color:#64748b">Sin evaluaciones</p>';
}
async function cambiarPassEmp(){
 let nueva=document.getElementById('cp_nueva').value;
 let r=await api(`/empleado/${MI_EMPLEADO.id}/cambiar-pass?empresa_id=${EMPRESA_ID}`,'POST',{nueva:nueva});
 document.getElementById('msg_pass').innerText=r.mensaje || r.error;
}
async function pedirVacEmp(){
 let d={empresa_id:EMPRESA_ID,empleado_id:MI_EMPLEADO.id,fecha_inicio:document.getElementById('my_vac_ini').value,fecha_fin:document.getElementById('my_vac_fin').value,dias:parseInt(document.getElementById('my_vac_dias').value)||1,motivo:'Solicitud empleado'};
 await api('/vacaciones','POST',d); cargarMisVacEvalEmp();
}
async function checkIn(){
 let r=await api('/visitas/checkin?empresa_id='+EMPRESA_ID,'POST',{empleado_id:MI_EMPLEADO.id,sucursal_id:MI_HOY.sucursal_id,sucursal_nombre:MI_HOY.sucursal_nombre});
 alert(r.mensaje);
}
async function loginEmpleadoReload(){
 let eid=localStorage.getItem('empresa_id');
 let emp_id=localStorage.getItem('empleado_id');
 if(!eid||!emp_id) return;
 let data=await api(`/empleado/${emp_id}/hoy?empresa_id=${eid}`);
 MI_HOY=data; // y buscar empleado
 let emps=await api('/empleados?empresa_id='+eid);
 MI_EMPLEADO=emps.find(e=>e.id===emp_id);
 renderMiDia();
 document.getElementById('sec-mi').style.display='block';
}
init();
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home(): return HTML

@app.get("/empresas")
def list_emppresas():
    db=SessionLocal(); r=db.query(EmpresaDB).all(); db.close(); return r

@app.post("/empresas")
def crear_empresa(e: EmpresaCreate):
    db=SessionLocal()
    ex=db.query(EmpresaDB).filter(EmpresaDB.id==e.id).first()
    if ex:
        db.close()
        return {"error":"Empresa ID ya existe"}
    n=EmpresaDB(**e.dict()); db.add(n); db.commit(); db.refresh(n); db.close(); return n

@app.get("/login-empresa")
def login_empresa(empresa_id: str, usuario: str, password: str):
    db=SessionLocal()
    emp=db.query(EmpresaDB).filter(EmpresaDB.id==empresa_id, EmpresaDB.admin_user==usuario, EmpresaDB.admin_pass==password).first()
    db.close()
    if not emp:
        return {"error":"Empresa, usuario o pass incorrecto"}
    return {"ok":True,"nombre":emp.nombre,"id":emp.id}

@app.get("/login-empleado")
def login_empleado(empresa_id: str, usuario: str, password: str):
    db=SessionLocal()
    emp=db.query(EmpleadoDB).filter(EmpleadoDB.empresa_id==empresa_id, EmpleadoDB.usuario==usuario, EmpleadoDB.password==password).first()
    if not emp:
        db.close()
        return {"error":"Usuario o pass incorrecto"}
    # hoy
    from datetime import datetime
    hoy_dt=datetime.now()
    fecha_str=hoy_dt.strftime("%Y-%m-%d"); semana_str=f"{hoy_dt.isocalendar()[0]}-W{hoy_dt.isocalendar()[1]:02d}"; mes_str=hoy_dt.strftime("%Y-%m")
    dias=["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]; dia_nombre=dias[hoy_dt.weekday()]
    asig_dia=db.query(AsignacionDB).filter(AsignacionDB.empresa_id==empresa_id, AsignacionDB.empleado_id==emp.id, AsignacionDB.tipo=="dia", AsignacionDB.fecha==fecha_str).first()
    if asig_dia:
        suc_id=asig_dia.sucursal_dia; origen="dia"; semana_completa={}
    else:
        asig_sem=db.query(AsignacionDB).filter(AsignacionDB.empresa_id==empresa_id, AsignacionDB.empleado_id==emp.id, AsignacionDB.tipo=="semana", AsignacionDB.semana==semana_str).first()
        if asig_sem:
            suc_id=getattr(asig_sem, dia_nombre, "") or ""; origen="semana"; semana_completa={d:getattr(asig_sem,d,"") for d in dias}
        else:
            asig_mes=db.query(AsignacionDB).filter(AsignacionDB.empresa_id==empresa_id, AsignacionDB.empleado_id==emp.id, AsignacionDB.tipo=="mes", AsignacionDB.mes==mes_str).first()
            if asig_mes:
                suc_id=asig_mes.sucursal_mes; origen="mes"; semana_completa={}
            else:
                suc_id=emp.sucursal; origen="base"; semana_completa={d: emp.sucursal for d in dias[:5]}
    suc_nombre=suc_id
    sdb=db.query(SucursalDB).filter(SucursalDB.id==suc_id, SucursalDB.empresa_id==empresa_id).first()
    if sdb: suc_nombre=sdb.nombre
    hoy_data={"empleado_id":emp.id,"fecha":fecha_str,"dia_nombre":dia_nombre.capitalize(),"semana":semana_str,"mes":mes_str,"sucursal_id":suc_id,"sucursal_nombre":suc_nombre,"origen":origen,"semana_completa":semana_completa}
    emp_dict={"id":emp.id,"nombre":emp.nombre,"puesto":emp.puesto,"horario_entrada":emp.horario_entrada,"horario_salida":emp.horario_salida,"estatus":emp.estatus,"vacaciones_totales":emp.vacaciones_totales,"vacaciones_tomadas":emp.vacaciones_tomadas,"faltas":emp.faltas,"retardos":emp.retardos,"promedio_eval":emp.promedio_eval,"foto_url":emp.foto_url}
    db.close()
    return {"empleado":emp_dict,"hoy":hoy_data,"empresa_nombre":empresa_id}

@app.get("/empleados")
def list_emp(empresa_id: str="DEFAULT"):
    db=SessionLocal(); r=db.query(EmpleadoDB).filter(EmpleadoDB.empresa_id==empresa_id).all(); db.close(); return r

@app.post("/empleados")
def create_emp(emp: EmpleadoCreate):
    db=SessionLocal()
    ex=db.query(EmpleadoDB).filter(EmpleadoDB.id==emp.id, EmpleadoDB.empresa_id==emp.empresa_id).first()
    if ex: db.delete(ex); db.commit()
    n=EmpleadoDB(**emp.dict()); db.add(n); db.commit(); db.refresh(n); db.close(); return n

@app.delete("/empleados/{empleado_id}")
def del_emp(empleado_id: str, empresa_id: str="DEFAULT"):
    db=SessionLocal()
    ex=db.query(EmpleadoDB).filter(EmpleadoDB.id==empleado_id, EmpleadoDB.empresa_id==empresa_id).first()
    if ex: db.delete(ex); db.commit()
    db.close(); return {"ok":True}

@app.get("/sucursales")
def list_suc(empresa_id: str="DEFAULT"):
    db=SessionLocal(); r=db.query(SucursalDB).filter(SucursalDB.empresa_id==empresa_id).all(); db.close(); return r

@app.post("/sucursales")
def create_suc(s: SucursalCreate):
    db=SessionLocal()
    ex=db.query(SucursalDB).filter(SucursalDB.id==s.id, SucursalDB.empresa_id==s.empresa_id).first()
    if ex: db.delete(ex); db.commit()
    n=SucursalDB(**s.dict()); db.add(n); db.commit(); db.refresh(n); db.close(); return n

@app.post("/asignaciones/dia")
def asig_dia(a: AsigDia):
    db=SessionLocal()
    ex=db.query(AsignacionDB).filter(AsignacionDB.empresa_id==a.empresa_id, AsignacionDB.empleado_id==a.empleado_id, AsignacionDB.tipo=="dia", AsignacionDB.fecha==a.fecha).first()
    if ex: db.delete(ex); db.commit()
    n=AsignacionDB(empresa_id=a.empresa_id, empleado_id=a.empleado_id, tipo="dia", fecha=a.fecha, sucursal_dia=a.sucursal_id)
    db.add(n); db.commit(); db.refresh(n); db.close(); return n

@app.post("/asignaciones/semana")
def asig_semana(a: AsigSemana):
    db=SessionLocal()
    ex=db.query(AsignacionDB).filter(AsignacionDB.empresa_id==a.empresa_id, AsignacionDB.empleado_id==a.empleado_id, AsignacionDB.tipo=="semana", AsignacionDB.semana==a.semana).first()
    if ex: db.delete(ex); db.commit()
    n=AsignacionDB(empresa_id=a.empresa_id, empleado_id=a.empleado_id, tipo="semana", semana=a.semana, lunes=a.lunes, martes=a.martes, miercoles=a.miercoles, jueves=a.jueves, viernes=a.viernes, sabado=a.sabado, domingo=a.domingo)
    db.add(n); db.commit(); db.refresh(n); db.close(); return n

@app.post("/asignaciones/mes")
def asig_mes(a: AsigMes):
    db=SessionLocal()
    ex=db.query(AsignacionDB).filter(AsignacionDB.empresa_id==a.empresa_id, AsignacionDB.empleado_id==a.empleado_id, AsignacionDB.tipo=="mes", AsignacionDB.mes==a.mes).first()
    if ex: db.delete(ex); db.commit()
    n=AsignacionDB(empresa_id=a.empresa_id, empleado_id=a.empleado_id, tipo="mes", mes=a.mes, sucursal_mes=a.sucursal_id)
    db.add(n); db.commit(); db.refresh(n); db.close(); return n

@app.get("/asignaciones")
def list_asig(empresa_id: str="DEFAULT", tipo: str=""):
    db=SessionLocal(); q=db.query(AsignacionDB).filter(AsignacionDB.empresa_id==empresa_id)
    if tipo: q=q.filter(AsignacionDB.tipo==tipo)
    r=q.order_by(AsignacionDB.created_at.desc()).all(); db.close(); return r

@app.get("/empleado/{empleado_id}/hoy")
def hoy(empleado_id: str, empresa_id: str="DEFAULT"):
    db=SessionLocal()
    emp=db.query(EmpleadoDB).filter(EmpleadoDB.id==empleado_id, EmpleadoDB.empresa_id==empresa_id).first()
    if not emp: db.close(); return {"error":"Empleado no existe"}
    hoy_dt=datetime.now()
    fecha_str=hoy_dt.strftime("%Y-%m-%d"); semana_str=f"{hoy_dt.isocalendar()[0]}-W{hoy_dt.isocalendar()[1]:02d}"; mes_str=hoy_dt.strftime("%Y-%m")
    dias=["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]; dia_nombre=dias[hoy_dt.weekday()]
    asig_dia=db.query(AsignacionDB).filter(AsignacionDB.empresa_id==empresa_id, AsignacionDB.empleado_id==empleado_id, AsignacionDB.tipo=="dia", AsignacionDB.fecha==fecha_str).first()
    if asig_dia:
        suc_id=asig_dia.sucursal_dia; origen="dia"; semana_completa={}
    else:
        asig_sem=db.query(AsignacionDB).filter(AsignacionDB.empresa_id==empresa_id, AsignacionDB.empleado_id==empleado_id, AsignacionDB.tipo=="semana", AsignacionDB.semana==semana_str).first()
        if asig_sem:
            suc_id=getattr(asig_sem, dia_nombre, "") or ""; origen="semana"; semana_completa={d:getattr(asig_sem,d,"") for d in dias}
        else:
            asig_mes=db.query(AsignacionDB).filter(AsignacionDB.empresa_id==empresa_id, AsignacionDB.empleado_id==empleado_id, AsignacionDB.tipo=="mes", AsignacionDB.mes==mes_str).first()
            if asig_mes:
                suc_id=asig_mes.sucursal_mes; origen="mes"; semana_completa={}
            else:
                suc_id=emp.sucursal; origen="base"; semana_completa={d: emp.sucursal for d in dias[:5]}
    suc_nombre=suc_id
    sdb=db.query(SucursalDB).filter(SucursalDB.id==suc_id, SucursalDB.empresa_id==empresa_id).first()
    if sdb: suc_nombre=sdb.nombre
    db.close()
    return {"empleado_id":empleado_id,"fecha":fecha_str,"dia_nombre":dia_nombre.capitalize(),"semana":semana_str,"mes":mes_str,"sucursal_id":suc_id,"sucursal_nombre":suc_nombre,"origen":origen,"semana_completa":semana_completa}

@app.post("/visitas/checkin")
def checkin(v: VisitaCreate, empresa_id: str="DEFAULT"):
    db=SessionLocal()
    emp=db.query(EmpleadoDB).filter(EmpleadoDB.id==v.empleado_id, EmpleadoDB.empresa_id==empresa_id).first()
    es_retardo=False
    if emp:
        try:
            hora_actual=datetime.now().strftime("%H:%M")
            h_ent = emp.horario_entrada or "09:00"
            if hora_actual > h_ent:
                es_retardo=True
                emp.retardos = (emp.retardos or 0) + 1
        except:
            pass
    visita=VisitaDB(empresa_id=empresa_id, empleado_id=v.empleado_id, sucursal_id=v.sucursal_id, sucursal_nombre=v.sucursal_nombre, es_retardo=es_retardo, notas=v.notas + (" - RETARDO" if es_retardo else " - A TIEMPO"))
    db.add(visita); db.commit(); db.refresh(visita); db.commit(); db.close()
    return {"ok":True,"es_retardo":es_retardo,"mensaje": "Check-In con retardo" if es_retardo else "Check-In a tiempo"}

@app.get("/visitas")
def list_visitas(empresa_id: str="DEFAULT"):
    db=SessionLocal(); r=db.query(VisitaDB).filter(VisitaDB.empresa_id==empresa_id).order_by(VisitaDB.created_at.desc()).limit(300).all(); db.close(); return r

@app.post("/vacaciones")
def crear_vac(v: VacacionCreate):
    db=SessionLocal()
    n=VacacionDB(**v.dict()); db.add(n); db.commit(); db.refresh(n); db.close(); return n

@app.get("/vacaciones")
def list_vac(empresa_id: str="DEFAULT", empleado_id: str=""):
    db=SessionLocal()
    q=db.query(VacacionDB).filter(VacacionDB.empresa_id==empresa_id)
    if empleado_id: q=q.filter(VacacionDB.empleado_id==empleado_id)
    r=q.order_by(VacacionDB.created_at.desc()).all(); db.close(); return r

@app.post("/vacaciones/{vac_id}/estatus")
def estatus_vac(vac_id: int, data: dict, empresa_id: str="DEFAULT"):
    db=SessionLocal()
    vac=db.query(VacacionDB).filter(VacacionDB.id==vac_id, VacacionDB.empresa_id==empresa_id).first()
    if not vac: db.close(); return {"error":"No existe"}
    vac.estatus=data.get("estatus","aprobada")
    if vac.estatus=="aprobada":
        emp=db.query(EmpleadoDB).filter(EmpleadoDB.id==vac.empleado_id, EmpleadoDB.empresa_id==empresa_id).first()
        if emp: emp.vacaciones_tomadas = (emp.vacaciones_tomadas or 0) + vac.dias
    db.commit(); db.refresh(vac); db.close(); return vac

@app.post("/evaluaciones")
def crear_eval(e: EvaluacionCreate):
    db=SessionLocal()
    n=EvaluacionDB(**e.dict()); db.add(n)
    evals=db.query(EvaluacionDB).filter(EvaluacionDB.empleado_id==e.empleado_id, EvaluacionDB.empresa_id==e.empresa_id).all()
    total=sum([x.calificacion for x in evals]) + e.calificacion
    prom=total / (len(evals)+1) if evals else e.calificacion
    emp=db.query(EmpleadoDB).filter(EmpleadoDB.id==e.empleado_id, EmpleadoDB.empresa_id==e.empresa_id).first()
    if emp: emp.promedio_eval=round(prom,1)
    db.commit(); db.refresh(n); db.close(); return n

@app.get("/evaluaciones")
def list_eval(empresa_id: str="DEFAULT", empleado_id: str=""):
    db=SessionLocal()
    q=db.query(EvaluacionDB).filter(EvaluacionDB.empresa_id==empresa_id)
    if empleado_id: q=q.filter(EvaluacionDB.empleado_id==empleado_id)
    r=q.order_by(EvaluacionDB.created_at.desc()).all(); db.close(); return r

@app.get("/reporte")
def reporte(empresa_id: str="DEFAULT"):
    db=SessionLocal(); r=db.query(EmpleadoDB).filter(EmpleadoDB.empresa_id==empresa_id).all(); db.close(); return r

@app.get("/reporte/csv")
def reporte_csv(empresa_id: str="DEFAULT"):
    from fastapi.responses import PlainTextResponse
    db=SessionLocal(); emps=db.query(EmpleadoDB).filter(EmpleadoDB.empresa_id==empresa_id).all(); db.close()
    csv="ID,Nombre,Puesto,Sucursal,SueldoTipo,Monto,Estatus,Faltas,Retardos,VacTomadas,VacTotales,Eval\n"
    for e in emps:
        csv+=f"{e.id},{e.nombre},{e.puesto},{e.sucursal},{e.sueldo_tipo},{e.sueldo_monto},{e.estatus},{e.faltas},{e.retardos},{e.vacaciones_tomadas},{e.vacaciones_totales},{e.promedio_eval}\n"
    return PlainTextResponse(csv, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=reporte_{empresa_id}.csv"})

@app.post("/empleado/{empleado_id}/cambiar-pass")
def cambiar_pass(empleado_id: str, data: dict, empresa_id: str="DEFAULT"):
    db=SessionLocal()
    emp=db.query(EmpleadoDB).filter(EmpleadoDB.id==empleado_id, EmpleadoDB.empresa_id==empresa_id).first()
    if not emp: db.close(); return {"error":"Empleado no existe"}
    nueva=data.get("nueva","")
    if not nueva: db.close(); return {"error":"Vacía"}
    emp.password=nueva; db.commit(); db.close(); return {"ok":True,"mensaje":"Contraseña cambiada ✅"}

