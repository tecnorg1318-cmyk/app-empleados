
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Text, Boolean, text
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

class EmpresaDB(Base):
    __tablename__ = "empresas"
    id = Column(String, primary_key=True)
    nombre = Column(String, nullable=False)
    rfc = Column(String, default="")
    telefono = Column(String, default="")
    direccion = Column(String, default="")
    admin_user = Column(String, default="admin")
    admin_pass = Column(String, default="admin123")
    created_at = Column(DateTime, default=datetime.now)

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
    estatus = Column(String, default="activo")
    foto_url = Column(Text, default="")
    usuario = Column(String, default="")
    password = Column(String, default="1234")
    vacaciones_totales = Column(Integer, default=12)
    vacaciones_tomadas = Column(Integer, default=0)
    faltas = Column(Integer, default=0)
    retardos = Column(Integer, default=0)
    promedio_eval = Column(Float, default=0.0)
    empresa_id = Column(String, default="DEFAULT")
    created_at = Column(DateTime, default=datetime.now)

class SucursalDB(Base):
    __tablename__ = "sucursales"
    id = Column(String, primary_key=True)
    nombre = Column(String, nullable=False)
    direccion = Column(String, default="")
    empresa_id = Column(String, default="DEFAULT")

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
    empresa_id = Column(String, default="DEFAULT")
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
    empresa_id = Column(String, default="DEFAULT")
    created_at = Column(DateTime, default=datetime.now)

class JornadaDB(Base):
    __tablename__ = "jornadas"
    id = Column(Integer, primary_key=True, autoincrement=True)
    empleado_id = Column(String, nullable=False)
    empresa_id = Column(String, default="DEFAULT")
    fecha = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d"))
    entrada = Column(String, default="")
    entrada_lat = Column(Float, default=0.0)
    entrada_lon = Column(Float, default=0.0)
    entrada_gps = Column(String, default="")
    salida_comida = Column(String, default="")
    salida_comida_lat = Column(Float, default=0.0)
    salida_comida_lon = Column(Float, default=0.0)
    salida_comida_gps = Column(String, default="")
    regreso_comida = Column(String, default="")
    regreso_comida_lat = Column(Float, default=0.0)
    regreso_comida_lon = Column(Float, default=0.0)
    regreso_comida_gps = Column(String, default="")
    salida_final = Column(String, default="")
    salida_final_lat = Column(Float, default=0.0)
    salida_final_lon = Column(Float, default=0.0)
    salida_final_gps = Column(String, default="")
    horas_trabajadas = Column(Float, default=0.0)
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
    estatus = Column(String, default="pendiente")
    empresa_id = Column(String, default="DEFAULT")
    created_at = Column(DateTime, default=datetime.now)

class EvaluacionDB(Base):
    __tablename__ = "evaluaciones"
    id = Column(Integer, primary_key=True, autoincrement=True)
    empleado_id = Column(String, nullable=False)
    fecha = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d"))
    calificacion = Column(Float, default=0.0)
    comentario = Column(Text, default="")
    evaluador = Column(String, default="admin")
    empresa_id = Column(String, default="DEFAULT")
    created_at = Column(DateTime, default=datetime.now)

Base.metadata.create_all(bind=engine)
# Intentar agregar columnas nuevas si DB ya existia sin ellas
try:
    with engine.connect() as conn:
        for tbl, col in [("empleados","empresa_id"), ("sucursales","empresa_id"), ("asignaciones_flexibles","empresa_id"), ("historial_visitas","empresa_id"), ("vacaciones","empresa_id"), ("evaluaciones","empresa_id")]:
            try:
                conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN empresa_id VARCHAR DEFAULT 'DEFAULT'"))
            except:
                pass
        conn.commit()
except:
    pass

print(f"✅ v11 COMPLETO lista")

app = FastAPI(title="Control v11 COMPLETO sin quitar")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class EmpleadoCreate(BaseModel):
    id: str; nombre: str; puesto: str=""; telefono: str=""; horario_entrada: str="09:00"; horario_salida: str="18:00"; sucursal: str="Matriz"; nss: str=""; sueldo_tipo: str="mes"; sueldo_monto: float=0; usuario: str=""; password: str="1234"; estatus: str="activo"; vacaciones_totales: int=12; empresa_id: str="DEFAULT"; foto_url: str=""
class SucursalCreate(BaseModel):
    id: str; nombre: str; direccion: str=""; empresa_id: str="DEFAULT"
class EmpresaCreate(BaseModel):
    id: str; nombre: str; rfc: str=""; telefono: str=""; direccion: str=""; admin_user: str="admin"; admin_pass: str="admin123"
class AsigDia(BaseModel):
    empleado_id: str; fecha: str; sucursal_id: str; empresa_id: str="DEFAULT"
class AsigSemana(BaseModel):
    empleado_id: str; semana: str; lunes: str=""; martes: str=""; miercoles: str=""; jueves: str=""; viernes: str=""; sabado: str=""; domingo: str=""; empresa_id: str="DEFAULT"
class AsigMes(BaseModel):
    empleado_id: str; mes: str; sucursal_id: str; empresa_id: str="DEFAULT"
class VisitaCreate(BaseModel):
    empleado_id: str; sucursal_id: str; sucursal_nombre: str=""; notas: str=""; empresa_id: str="DEFAULT"; lat: float=0; lon: float=0; gps: str=""
class JornadaMarcar(BaseModel):
    empleado_id: str; tipo: str; empresa_id: str="DEFAULT"; sucursal_id: str=""; sucursal_nombre: str=""; lat: float=0; lon: float=0; gps: str=""
class VacacionCreate(BaseModel):
    empleado_id: str; fecha_inicio: str; fecha_fin: str; dias: int=1; motivo: str=""; empresa_id: str="DEFAULT"
class EvaluacionCreate(BaseModel):
    empleado_id: str; calificacion: float; comentario: str=""; empresa_id: str="DEFAULT"

HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>v11 - Tu archivo + Empresa + Dashboard + Sin quitar nada</title>
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
.login-overlay{position:fixed;top:0;left:0;width:100%;height:100%;background:#0f172a;z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px}
.login-box{max-width:420px;width:100%;background:#1e293b;border-radius:20px;padding:24px;border:1px solid #334155}
.kpi{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:10px;margin-bottom:12px}
@media(max-width:800px){.kpi{grid-template-columns:1fr 1fr}}
.kpi h2{font-size:22px;color:white}
</style>
</head>
<body>
<!-- LOGIN ADMIN OVERLAY - NUEVO SIN QUITAR LO TUYO -->
<div id="admin-login" class="login-overlay" style="display:none">
<div class="login-box">
<h2 style="color:white;text-align:center">🔐 Login Admin</h2>
<p style="font-size:11px;text-align:center;color:#94a3b8;margin-top:4px">Tu archivo original no tenía login, ahora agregado sin quitar nada</p>
<div style="margin-top:14px">
<label>Empresa ID</label><input id="adm_emp" class="input" value="DEMO" placeholder="DEMO o tu empresa">
<label>Usuario Admin</label><input id="adm_user" class="input" value="admin">
<label>Pass Admin</label><input id="adm_pass" class="input" type="password" value="admin123">
<button class="btn btn-p" onclick="loginAdmin()">Entrar Admin</button>
<button class="btn btn-d" onclick="crearDemoRapido()">⚡ Crear DEMO automático (DEMO/admin/admin123)</button>
<button class="btn btn-d" onclick="entrarSinLogin()">Entrar sin login (como antes)</button>
<p id="msg_adm" style="font-size:11px;color:#f87171;margin-top:6px"></p>
</div>
<div style="margin-top:16px;background:#0f172a;padding:10px;border-radius:10px">
<h4 style="font-size:11px">🏢 Crear Empresa (NUEVO)</h4>
<label>ID Empresa</label><input id="c_id" class="input" placeholder="EMPRESA001">
<label>Nombre</label><input id="c_nom" class="input" placeholder="Mi Empresa SA">
<label>Usuario Admin</label><input id="c_user" class="input" value="admin">
<label>Pass</label><input id="c_pass" class="input" value="admin123">
<button class="btn btn-p" onclick="crearEmpresa()">Crear Empresa</button>
<p id="msg_emp" style="font-size:11px;color:#34d399;margin-top:4px"></p>
</div>
</div>
</div>

<div class="hero">
<h1>v10 + v11 - Tu archivo intacto + Empresa + Dashboard</h1>
<p style="color:white;opacity:.9;font-size:11px">✅ Tu v10 original (2,3,4,5,6,7) + 🏢 Empresa + 📊 Dashboard + 📥 Reporte + ✏️ Editar/Eliminar</p>
<div style="margin-top:10px"><button class="btn btn-d" style="width:auto;padding:6px 12px" onclick="logoutAdmin()">Salir / Cambiar empresa</button> <span id="emp_actual_lbl" style="font-size:11px;margin-left:10px;color:white"></span></div>
</div>

<div class="tabs">
<div class="tab active" onclick="show('dash')">📊 Dashboard (NUEVO)</div>
<div class="tab" onclick="show('asig')">🗓️ Asignar</div>
<div class="tab" onclick="show('emp')">👥 Empleados + Foto + Estatus</div>
<div class="tab" onclick="show('vac')">🏖️ Vacaciones</div>
<div class="tab" onclick="show('eval')">⭐ Evaluaciones</div>
<div class="tab" onclick="show('suc')">🏪 Sucursales</div>
<div class="tab" onclick="show('mi')" style="background:#10b981;color:white">📱 Mi Día (Login Empleado)</div>
<div class="tab" onclick="show('hist')">🔒 Historial + Faltas + Reporte (ADMIN)</div>
<div class="tab" onclick="show('empresa')" style="background:#f59e0b;color:white">🏢 Empresas (NUEVO)</div>
</div>

<div class="container">

<div id="sec-dash" class="grid" style="display:grid">
<div class="card" style="grid-column:1 / -1">
<div class="kpi">
<div class="card" style="margin:0"><h2 id="kpi_total">0</h2><p style="font-size:10px">Total Empleados</p></div>
<div class="card" style="margin:0"><h2 id="kpi_act">0</h2><p style="font-size:10px">Activos</p></div>
<div class="card" style="margin:0"><h2 id="kpi_falta">0</h2><p style="font-size:10px">Faltas hoy</p></div>
<div class="card" style="margin:0"><h2 id="kpi_vac">0</h2><p style="font-size:10px">Vac pendientes</p></div>
</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px">
<div class="card"><h3>🔴 Quién faltó hoy (sin check-in)</h3><div id="dash_faltas" style="font-size:11px;margin-top:8px"></div><button class="btn btn-d" onclick="cargarDashboard()">Actualizar</button></div>
<div class="card"><h3>🔔 Notificaciones</h3><div id="dash_notis" style="font-size:11px;margin-top:8px"></div></div>
</div>
</div>
</div>

<!-- ASIGNAR - TU ORIGINAL INTACTO -->
<div id="sec-asig" class="grid" style="display:none">
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

<!-- EMPLEADOS - TU ORIGINAL + EDITAR/ELIMINAR AGREGADO -->
<div id="sec-emp" class="grid" style="display:none">
<div class="card">
<h3>👥 Crear empleado con TODO 2-7 (tu original)</h3>
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
<button class="btn btn-d" onclick="limpiarEmp()">Limpiar / Nuevo</button>
<p id="msg_e" style="font-size:10px;color:#34d399"></p>
</div>
<div class="card"><h3>Lista empleados (con foto, estatus, faltas) - AHORA con ✏️ Editar / 🗑️ Eliminar</h3><table class="table"><thead><tr><th>Foto</th><th>ID/Nombre</th><th>Estatus</th><th>Faltas/Ret</th><th>Eval</th><th>Acción</th></tr></thead><tbody id="tab_emp"></tbody></table></div>
</div>

<!-- VACACIONES - TU ORIGINAL -->
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

<!-- EVALUACION - TU ORIGINAL -->
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
<div class="card" style="border:2px solid #10b981"><h3>📱 Login Empleado - Mi Día + GPS obligatorio</h3>
<label>Usuario</label><input id="my_user" class="input" placeholder="tu usuario">
<label>Password</label><input id="my_pass" class="input" type="password" placeholder="1234">
<label>ó ID directo</label><input id="my_id" class="input" placeholder="EMP001">
<button class="btn btn-g" onclick="loginEmpleado()">Entrar y ver dónde me toca hoy</button>
<div id="mi_box" style="margin-top:12px"></div>
</div>
<div class="card"><h3>Mi info + 4 marcajes con GPS 📍</h3><div id="mi_info"></div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px">
<button class="btn btn-p" onclick="marcar('entrada')">🟢 1. Entrada GPS</button>
<button class="btn btn-o" onclick="marcar('salida_comida')">🍔 2. Salida comer GPS</button>
<button class="btn btn-o" onclick="marcar('regreso_comida')">↩️ 3. Regreso GPS</button>
<button class="btn btn-g" onclick="marcar('salida_final')">🔴 4. Salida GPS</button>
</div>
<div id="jornada_box" style="margin-top:12px;background:#0f172a;padding:10px;border-radius:10px;font-size:12px"></div>
<p style="font-size:10px;color:#94a3b8;margin-top:6px">📡 Cada marcaje pide GPS obligatorio. Activa ubicación en el celular. Admin ve tu ubicación en mapa.</p>
</div>
</div>
</div>

<div id="sec-hist" style="display:none">
<div class="card" style="border:1px dashed #f59e0b"><h3>🔒 Historial + Jornadas GPS 4 marcajes</h3>
<div style="display:flex;gap:6px;flex-wrap:wrap;margin:10px 0">
<button class="btn btn-d" style="width:auto" onclick="cargarHist()">🔄 Check-ins</button>
<button class="btn btn-d" style="width:auto;background:#6366f1;color:white" onclick="cargarJornadasAdmin()">📅 Jornadas GPS</button>
<button class="btn btn-o" style="width:auto" onclick="descargarReporte()">📥 Reporte Nómina</button>
</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:8px"><div><label>Filtrar empleado</label><input id="filt_hist_emp" class="input" placeholder="EMP001" onkeyup="filtrarHist()"></div><div><label>Filtrar fecha</label><input id="filt_hist_fecha" class="input" type="date" onchange="filtrarHist()"></div></div>
<table class="table"><thead><tr><th>Fecha</th><th>Hora</th><th>Emp</th><th>Sucursal</th><th>Retardo?</th><th>Nota</th></tr></thead><tbody id="tab_hist"></tbody></table>
<div id="tab_jornadas_admin" style="margin-top:12px"></div>
<div id="reporte_box" style="margin-top:12px;background:#0f172a;padding:10px;border-radius:10px;font-size:11px"><h4>💰 Nómina</h4></div>
</div>
</div>

<div id="sec-empresa" class="grid" style="display:none">
<div class="card"><h3>🏢 Empresas creadas</h3><table class="table"><thead><tr><th>ID</th><th>Nombre</th><th>Admin</th><th>Creada</th></tr></thead><tbody id="tab_empresa"></tbody></table><button class="btn btn-d" onclick="cargarEmpresas()">Actualizar</button></div>
<div class="card"><h3>Crear nueva empresa</h3><label>ID</label><input id="ce_id" class="input" placeholder="EMPRESA001"><label>Nombre</label><input id="ce_nom" class="input"><label>Admin user</label><input id="ce_user" class="input" value="admin"><label>Admin pass</label><input id="ce_pass" class="input" value="admin123"><button class="btn btn-p" onclick="crearEmpresa2()">Crear</button><p id="msg_ce" style="font-size:11px;color:#34d399"></p></div>
</div>

</div>
<datalist id="list_suc_nom"></datalist>
<script>
const API="";
let EMPRESA_ID = localStorage.getItem('empresa_id') || 'DEFAULT';
let miActual=null; let miEmpleado=null;
async function api(p,m="GET",b=null){const o={method:m,headers:{"Content-Type":"application/json"}}; if(b) o.body=JSON.stringify(b); const r=await fetch(API+p,o); return r.json();}

function show(s){
 document.querySelectorAll('[id^=sec-]').forEach(d=>d.style.display='none');
 document.getElementById('sec-'+s).style.display=s==='dash'||s==='empresa'?'grid':'grid';
 if(s==='dash') cargarDashboard();
 if(s==='asig'){cargarEmps(); cargarSucs(); cargarAsig('');}
 if(s==='emp') cargarEmps();
 if(s==='suc') cargarSucs();
 if(s==='vac'){cargarEmps(); cargarVac();}
 if(s==='eval'){cargarEmps(); cargarEval();}
 if(s==='hist') {cargarHist(); cargarReporte();}
 if(s==='empresa') cargarEmpresas();
 document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
 event?.target?.classList.add('active');
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
   let estCls='st-activo'; if(e.estatus==='baja') estCls='st-baja'; if(e.estatus==='vacaciones') estCls='st-vac'; if(e.estatus==='incapacidad') estCls='st-inc';
   let foto=e.foto_url?`<img src="${e.foto_url}" class="img-emp">`:`<div class="img-emp" style="display:flex;align-items:center;justify-content:center;font-size:10px">${e.nombre.charAt(0)}</div>`;
   return `<tr><td>${foto}</td><td><b>${e.id}</b><br>${e.nombre}<br><small>${e.puesto}</small></td><td><span class="badge ${estCls}">${e.estatus}</span><br><small>Vac:${e.vacaciones_tomadas}/${e.vacaciones_totales}</small></td><td>F:${e.faltas} R:${e.retardos}</td><td>⭐ ${e.promedio_eval||0}</td><td><button onclick="editarEmp('${e.id}')" class="btn btn-d" style="padding:4px;width:auto">✏️</button> <button onclick="eliminarEmp('${e.id}')" class="btn btn-d" style="padding:4px;width:auto;color:#f87171">🗑️</button></td></tr>`;
 }).join('');
 document.getElementById('as_emp').innerHTML=emps.map(e=>`<option value="${e.id}">${e.nombre}</option>`).join('');
 document.getElementById('vac_emp').innerHTML=document.getElementById('as_emp').innerHTML;
 document.getElementById('eval_emp').innerHTML=document.getElementById('as_emp').innerHTML;
}
async function cargarSucs(){
 const sucs=await api('/sucursales?empresa_id='+EMPRESA_ID);
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
 const d={id:document.getElementById('e_id').value,nombre:document.getElementById('e_nom').value,puesto:document.getElementById('e_pue').value,telefono:document.getElementById('e_tel').value,horario_entrada:document.getElementById('e_he').value,horario_salida:document.getElementById('e_hs').value,sucursal:document.getElementById('e_suc').value,estatus:document.getElementById('e_est').value,usuario:document.getElementById('e_user').value,password:document.getElementById('e_pass').value,sueldo_tipo:document.getElementById('e_tipo').value,sueldo_monto:parseFloat(document.getElementById('e_monto').value)||0,vacaciones_totales:parseInt(document.getElementById('e_vactot').value)||12,foto_url:fotoB64,empresa_id:EMPRESA_ID};
 if(!d.id||!d.nombre) return alert('ID y nombre');
 await api('/empleados','POST',d); document.getElementById('msg_e').innerText='Guardado ✅'; cargarEmps(); cargarDashboard();
}
function limpiarEmp(){ document.getElementById('e_id').value=''; document.getElementById('e_nom').value=''; }
async function editarEmp(id){
 const emps=await api('/empleados?empresa_id='+EMPRESA_ID);
 const e=emps.find(x=>x.id===id); if(!e) return;
 document.getElementById('e_id').value=e.id; document.getElementById('e_nom').value=e.nombre; document.getElementById('e_pue').value=e.puesto; document.getElementById('e_tel').value=e.telefono; document.getElementById('e_he').value=e.horario_entrada; document.getElementById('e_hs').value=e.horario_salida; document.getElementById('e_suc').value=e.sucursal; document.getElementById('e_est').value=e.estatus; document.getElementById('e_user').value=e.usuario; document.getElementById('e_pass').value=e.password; document.getElementById('e_tipo').value=e.sueldo_tipo; document.getElementById('e_monto').value=e.sueldo_monto; document.getElementById('e_vactot').value=e.vacaciones_totales;
 show('emp');
 window.scrollTo(0,0);
}
async function eliminarEmp(id){
 if(!confirm('¿Eliminar '+id+'?')) return;
 await api('/empleados/'+id+'?empresa_id='+EMPRESA_ID,'DELETE'); cargarEmps(); cargarDashboard();
}
async function crearSuc(){
 const d={id:document.getElementById('suc_id').value,nombre:document.getElementById('suc_nom').value,empresa_id:EMPRESA_ID};
 await api('/sucursales','POST',d); cargarSucs();
}
async function guardarDia(){
 const d={empleado_id:document.getElementById('as_emp').value,fecha:document.getElementById('as_fecha').value,sucursal_id:document.getElementById('as_suc_dia').value,empresa_id:EMPRESA_ID};
 await api('/asignaciones/dia','POST',d); document.getElementById('msg_as').innerText='Día guardado'; cargarAsig('dia');
}
async function guardarSemana(){
 const d={empleado_id:document.getElementById('as_emp').value,semana:document.getElementById('as_semana').value,lunes:document.getElementById('s_lun').value,martes:document.getElementById('s_mar').value,miercoles:document.getElementById('s_mie').value,jueves:document.getElementById('s_jue').value,viernes:document.getElementById('s_vie').value,sabado:document.getElementById('s_sab').value,domingo:document.getElementById('s_dom').value,empresa_id:EMPRESA_ID};
 await api('/asignaciones/semana','POST',d); document.getElementById('msg_as').innerText='Semana guardada'; cargarAsig('semana');
}
async function guardarMes(){
 const d={empleado_id:document.getElementById('as_emp').value,mes:document.getElementById('as_mes').value,sucursal_id:document.getElementById('as_suc_mes').value,empresa_id:EMPRESA_ID};
 await api('/asignaciones/mes','POST',d); document.getElementById('msg_as').innerText='Mes guardado'; cargarAsig('mes');
}
async function cargarAsig(f){
 let url='/asignaciones?empresa_id='+EMPRESA_ID; if(f) url+='&tipo='+f;
 const list=await api(url);
 document.getElementById('lista_asig').innerHTML=list.map(a=>{
   if(a.tipo==='dia') return `<div class="card" style="padding:8px;margin-top:6px;border-left:4px solid #38bdf8">📅 ${a.fecha} (${a.empleado_id}) → ${a.sucursal_dia}</div>`;
   if(a.tipo==='semana') return `<div class="card" style="padding:8px;margin-top:6px;border-left:4px solid #a78bfa">🗓️ ${a.semana} (${a.empleado_id}) L:${a.lunes||'-'} M:${a.martes||'-'} X:${a.miercoles||'-'} J:${a.jueves||'-'} V:${a.viernes||'-'}</div>`;
   if(a.tipo==='mes') return `<div class="card" style="padding:8px;margin-top:6px;border-left:4px solid #fb923c">📆 ${a.mes} (${a.empleado_id}) → ${a.sucursal_mes}</div>`;
 }).join('');
}
async function crearVac(){
 const d={empleado_id:document.getElementById('vac_emp').value,fecha_inicio:document.getElementById('vac_ini').value,fecha_fin:document.getElementById('vac_fin').value,dias:parseInt(document.getElementById('vac_dias').value)||1,motivo:document.getElementById('vac_mot').value,empresa_id:EMPRESA_ID};
 await api('/vacaciones','POST',d); cargarVac();
}
async function cargarVac(){
 const v=await api('/vacaciones?empresa_id='+EMPRESA_ID);
 document.getElementById('tab_vac').innerHTML=v.map(x=>`<tr><td>${x.empleado_id}</td><td>${x.fecha_inicio} al ${x.fecha_fin}</td><td>${x.dias}</td><td>${x.estatus}</td><td><button onclick="aprobarVac(${x.id},'aprobada')" class="btn btn-g" style="padding:4px 6px;width:auto">✔</button> <button onclick="aprobarVac(${x.id},'rechazada')" class="btn btn-p" style="padding:4px 6px;width:auto">✖</button></td></tr>`).join('');
}
async function aprobarVac(id,est){
 await api('/vacaciones/'+id+'/estatus?empresa_id='+EMPRESA_ID,'POST',{estatus:est}); cargarVac(); cargarEmps(); cargarDashboard();
}
async function crearEval(){
 const d={empleado_id:document.getElementById('eval_emp').value,calificacion:parseFloat(document.getElementById('eval_cal').value)||0,comentario:document.getElementById('eval_com').value,empresa_id:EMPRESA_ID};
 await api('/evaluaciones','POST',d); cargarEval(); cargarEmps();
}
async function cargarEval(){
 const e=await api('/evaluaciones?empresa_id='+EMPRESA_ID);
 document.getElementById('tab_eval').innerHTML=e.map(x=>`<tr><td>${x.fecha}</td><td>${x.empleado_id}</td><td>⭐ ${x.calificacion}</td><td>${x.comentario}</td></tr>`).join('');
}
let miActual=null; let miEmpleado=null;
async function loginEmpleado(){
 let user=document.getElementById('my_user').value;
 let pass=document.getElementById('my_pass').value;
 let id=document.getElementById('my_id').value;
 let url='';
 if(user){url=`/login?usuario=${user}&password=${pass}&empresa_id=${EMPRESA_ID}`;}
 else if(id){url=`/empleado/${id}/hoy?empresa_id=${EMPRESA_ID}`;}
 else return alert('Pon usuario/pass o ID');
 let data=await api(url);
 if(data.error){document.getElementById('mi_box').innerHTML=`<p style="color:#f87171">${data.error}</p>`; return;}
 if(data.empleado) {miEmpleado=data.empleado; miActual=data.hoy; }
 else {miActual=data;
   let emps=await api('/empleados?empresa_id='+EMPRESA_ID);
   miEmpleado=emps.find(e=>e.id===data.empleado_id);
 }
 document.getElementById('mi_box').innerHTML=`<div style="background:#0f172a;padding:12px;border-radius:10px;border:1px solid #10b981">
 <p style="color:#10b981;font-weight:800">${miActual.dia_nombre} ${miActual.fecha} - ${miActual.origen}</p>
 <h3 style="color:white">${miActual.sucursal_nombre||'Descanso'}</h3>
 <p style="font-size:11px;color:#94a3b8">Horario: ${miEmpleado?miEmpleado.horario_entrada+' - '+miEmpleado.horario_salida:''}</p>
 <div style="margin-top:8px;font-size:11px;background:#1e293b;padding:8px;border-radius:8px"><b>Semana completa:</b><br>${Object.entries(miActual.semana_completa||{}).map(([k,v])=>`${k}: ${v||'Descanso'}`).join('<br>')||'No asignada'}</div>
 </div>`;
 let info=`<p><b>${miEmpleado.nombre}</b> - ${miEmpleado.puesto}<br>
 Estatus: ${miEmpleado.estatus}<br>
 💰 Sueldo: $${miEmpleado.sueldo_monto||0} / ${miEmpleado.sueldo_tipo||'mes'}<br>
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
 <h4 style="font-size:11px;color:#a78bfa">⭐ Mis evaluaciones (4) + Sueldo</h4>
 <div id="my_eval_list"></div>
 <div id="my_hist_list" style="margin-top:10px"><h4 style="font-size:11px">📅 Mi historial check-ins (NUEVO)</h4><div id="my_hist"></div></div>
 </div>`;
 document.getElementById('mi_info').innerHTML=info;
 cargarMisVacEval();
}
async function cambiarPass(){
 let actual=document.getElementById('cp_actual').value;
 let nueva=document.getElementById('cp_nueva').value;
 if(!nueva) return alert('Pon nueva pass');
 let r=await api(`/empleado/${miEmpleado.id}/cambiar-pass?empresa_id=${EMPRESA_ID}`,'POST',{actual:actual,nueva:nueva});
 document.getElementById('msg_pass').innerText=r.mensaje || r.error;
}
async function solicitarMisVac(){
 let d={empleado_id:miEmpleado.id,fecha_inicio:document.getElementById('my_vac_ini').value,fecha_fin:document.getElementById('my_vac_fin').value,dias:parseInt(document.getElementById('my_vac_dias').value)||1,motivo:document.getElementById('my_vac_mot').value,empresa_id:EMPRESA_ID};
 if(!d.fecha_inicio||!d.fecha_fin) return alert('Fechas');
 await api('/vacaciones','POST',d);
 document.getElementById('msg_my_vac').innerText='Solicitud enviada, espera aprobación del admin';
 cargarMisVacEval();
}
async function cargarMisVacEval(){
 if(!miEmpleado) return;
 let vacs=await api('/vacaciones?empresa_id='+EMPRESA_ID+'&empleado_id='+miEmpleado.id);
 document.getElementById('my_vac_list').innerHTML=vacs.map(v=>`<div style="font-size:10px;padding:4px;border-bottom:1px solid #1e293b">${v.fecha_inicio} al ${v.fecha_fin} - ${v.dias} días - <b>${v.estatus}</b></div>`).join('');
 let evals=await api('/evaluaciones?empresa_id='+EMPRESA_ID+'&empleado_id='+miEmpleado.id);
 document.getElementById('my_eval_list').innerHTML=evals.map(e=>`<div style="font-size:11px;padding:6px;border-bottom:1px solid #1e293b">📅 ${e.fecha} - ⭐ ${e.calificacion}/10<br><span style="color:#94a3b8">${e.comentario}</span></div>`).join('') || '<p style="font-size:10px;color:#64748b">Sin evaluaciones aún</p>';
 let hist=await api('/visitas?empresa_id='+EMPRESA_ID+'&empleado_id='+miEmpleado.id);
 document.getElementById('my_hist').innerHTML=hist.slice(0,15).map(h=>`<div style="font-size:10px;padding:4px;border-bottom:1px solid #1e293b">${h.fecha} ${h.hora_entrada} - ${h.sucursal_nombre} ${h.es_retardo?'🔴':'🟢'}</div>`).join('') || 'Sin check-ins';
 cargarJornadaHoy();
}
async function getGPS(){
 return new Promise((resolve, reject)=>{
   if(!navigator.geolocation){ resolve({lat:0, lon:0, gps:''}); return; }
   navigator.geolocation.getCurrentPosition(pos=>{
     resolve({lat: pos.coords.latitude, lon: pos.coords.longitude, gps: pos.coords.latitude+','+pos.coords.longitude});
   }, err=>{
     alert('⚠️ No se pudo obtener GPS, debes activar ubicación. Error:'+err.message);
     resolve({lat:0, lon:0, gps:''});
   }, {enableHighAccuracy:true, timeout:10000});
 });
}
async function marcar(tipo){
 if(!miEmpleado) return alert('Haz login primero');
 let btnMsg = document.getElementById('gps_status');
 if(btnMsg) btnMsg.innerText='📡 Obteniendo GPS...';
 let gps = await getGPS();
 if(btnMsg) btnMsg.innerText='GPS: '+gps.gps;
 let r=await api('/jornada/marcar','POST',{empleado_id:miEmpleado.id, tipo:tipo, empresa_id:EMPRESA_ID, sucursal_id:miActual?.sucursal_id||'', sucursal_nombre:miActual?.sucursal_nombre||'', lat:gps.lat, lon:gps.lon, gps:gps.gps});
 if(r.error){ alert(r.error); return; }
 alert('✅ '+tipo+' marcado a las '+(r.jornada.entrada||r.jornada.salida_comida||r.jornada.regreso_comida||r.jornada.salida_final)+' con GPS '+gps.gps);
 cargarJornadaHoy(); cargarEmps();
}
async function cargarJornadaHoy(){
 if(!miEmpleado) return;
 let j=await api('/jornada/hoy?empleado_id='+miEmpleado.id+'&empresa_id='+EMPRESA_ID);
 let link = (g)=> g ? `<a href="https://maps.google.com/?q=${g}" target="_blank" style="color:#38bdf8">📍${g}</a>` : '--';
 let html=`<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px">
 <div>🟢 Entrada:<br><b style="color:${j.entrada?'#10b981':'#64748b'}">${j.entrada||'--:--'}</b><br><small>${link(j.entrada_gps)}</small></div>
 <div>🍔 Salida comida:<br><b style="color:${j.salida_comida?'#f59e0b':'#64748b'}">${j.salida_comida||'--:--'}</b><br><small>${link(j.salida_comida_gps)}</small></div>
 <div>↩️ Regreso:<br><b style="color:${j.regreso_comida?'#f59e0b':'#64748b'}">${j.regreso_comida||'--:--'}</b><br><small>${link(j.regreso_comida_gps)}</small></div>
 <div>🔴 Salida:<br><b style="color:${j.salida_final?'#ef4444':'#64748b'}">${j.salida_final||'--:--'}</b><br><small>${link(j.salida_final_gps)}</small></div>
 </div>
 <div style="margin-top:8px;padding:8px;background:#1e293b;border-radius:8px;text-align:center">⏱️ Horas: <b style="font-size:16px;color:#10b981">${j.horas||0}h</b><br><small id="gps_status">GPS listo</small></div>`;
 document.getElementById('jornada_box').innerHTML=html;
 cargarMisJornadas();
}
async function cargarMisJornadas(){
 let js=await api('/jornadas?empresa_id='+EMPRESA_ID+'&empleado_id='+miEmpleado.id);
 let box=document.getElementById('my_jornadas_hist');
 if(!box){ let cont=document.createElement('div'); cont.id='my_jornadas_hist'; cont.style.marginTop='10px'; document.getElementById('jornada_box').parentNode.appendChild(cont); box=cont; }
 box.innerHTML='<h4 style="font-size:11px;margin-top:10px">📅 Mis jornadas GPS (últimas 10)</h4>'+js.slice(0,10).map(j=>`<div style="font-size:10px;padding:6px;border-bottom:1px solid #1e293b">${j.fecha}: ${j.entrada||'--'} (${j.entrada_gps||''}) → ${j.salida_comida||'--'} → ${j.regreso_comida||'--'} → ${j.salida_final||'--'} | <b>${j.horas_trabajadas||0}h</b></div>`).join('');
}
async function checkIn(){
 if(!miActual||!miActual.sucursal_id) return alert('Hoy es descanso');
 let id=miEmpleado?miEmpleado.id:document.getElementById('my_id').value;
 let r=await api('/visitas/checkin?empresa_id='+EMPRESA_ID,'POST',{empleado_id:id,sucursal_id:miActual.sucursal_id,sucursal_nombre:miActual.sucursal_nombre});
 alert(r.mensaje || 'Check-In registrado. Retardo: '+(r.es_retardo?'SI':'NO'));
 cargarEmps();
}
async function cargarHist(){
 const v=await api('/visitas?empresa_id='+EMPRESA_ID);
 window._visitasCache=v;
 renderHist(v);
}
function renderHist(list){
 document.getElementById('tab_hist').innerHTML=list.slice(0,200).map(x=>`<tr><td>${x.fecha}</td><td>${x.hora_entrada}</td><td>${x.empleado_id}</td><td>${x.sucursal_nombre}</td><td>${x.es_retardo?'🔴 SI':'🟢 NO'}</td><td>${x.notas||''}</td></tr>`).join('');
}
function filtrarHist(){
 let fEmp=document.getElementById('filt_hist_emp')?.value.toLowerCase()||'';
 let fFecha=document.getElementById('filt_hist_fecha')?.value||'';
 let v=window._visitasCache||[];
 let fil=v.filter(x=>{ let ok=true; if(fEmp) ok=ok && (x.empleado_id.toLowerCase().includes(fEmp) || x.sucursal_nombre.toLowerCase().includes(fEmp)); if(fFecha) ok=ok && x.fecha===fFecha; return ok; });
 renderHist(fil);
}
async function cargarJornadasAdmin(){
 let js=await api('/jornadas?empresa_id='+EMPRESA_ID);
 document.getElementById('tab_jornadas_admin').innerHTML=`<h3>📅 Jornadas con GPS (50)</h3><table class="table"><thead><tr><th>Fecha</th><th>Emp</th><th>Entrada GPS</th><th>Sal.Comida GPS</th><th>Reg.Comida GPS</th><th>Salida GPS</th><th>Horas</th></tr></thead><tbody>${js.slice(0,50).map(j=>{
   let link=(g)=> g ? `<a href="https://maps.google.com/?q=${g}" target="_blank" style="color:#38bdf8">📍 Ver</a> ${g}` : '--';
   return `<tr><td>${j.fecha}</td><td>${j.empleado_id}</td><td>${j.entrada||'--'}<br><small>${link(j.entrada_gps)}</small></td><td>${j.salida_comida||'--'}<br><small>${link(j.salida_comida_gps)}</small></td><td>${j.regreso_comida||'--'}<br><small>${link(j.regreso_comida_gps)}</small></td><td>${j.salida_final||'--'}<br><small>${link(j.salida_final_gps)}</small></td><td><b>${j.horas_trabajadas||0}h</b></td></tr>`;
 }).join('')}</tbody></table>`;
}

async function cargarReporte(){
 const emps=await api('/empleados?empresa_id='+EMPRESA_ID);
 document.getElementById('reporte_box').innerHTML=emps.map(e=>`<div style="padding:6px;border-bottom:1px solid #1e293b"><b>${e.nombre}</b> (${e.id}) - $${e.sueldo_monto} ${e.sueldo_tipo} - F:${e.faltas} R:${e.retardos} - Vac:${e.vacaciones_tomadas}/${e.vacaciones_totales} - ⭐${e.promedio_eval}</div>`).join('');
}
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

async function cargarEmpresas(){
 const emps=await api('/empresas');
 document.getElementById('tab_empresa').innerHTML=emps.map(e=>`<tr><td>${e.id}</td><td>${e.nombre}</td><td>${e.admin_user}</td><td>${e.created_at||''}</td></tr>`).join('');
}
async function crearEmpresa(){
 const d={id:document.getElementById('c_id').value,nombre:document.getElementById('c_nom').value,admin_user:document.getElementById('c_user').value,admin_pass:document.getElementById('c_pass').value};
 if(!d.id||!d.nombre) return alert('ID y nombre');
 let r=await api('/empresas','POST',d);
 if(r.error){ document.getElementById('msg_emp').innerText=r.error; return; }
 document.getElementById('msg_emp').innerText='Empresa creada ✅ usa ID: '+d.id;
 document.getElementById('adm_emp').value=d.id;
 cargarEmpresas();
}
async function crearEmpresa2(){
 const d={id:document.getElementById('ce_id').value,nombre:document.getElementById('ce_nom').value,admin_user:document.getElementById('ce_user').value,admin_pass:document.getElementById('ce_pass').value};
 let r=await api('/empresas','POST',d);
 document.getElementById('msg_ce').innerText=r.error || 'Empresa creada ✅';
 cargarEmpresas();
}
async function crearDemoRapido(){
 await api('/init-demo');
 document.getElementById('msg_adm').innerText='DEMO creado, ahora entra con DEMO / admin / admin123';
 document.getElementById('adm_emp').value='DEMO';
 document.getElementById('adm_user').value='admin';
 document.getElementById('adm_pass').value='admin123';
}
async function loginAdmin(){
 let emp_id=document.getElementById('adm_emp').value;
 let user=document.getElementById('adm_user').value;
 let pass=document.getElementById('adm_pass').value;
 let r=await api(`/login-empresa?empresa_id=${emp_id}&usuario=${user}&password=${pass}`);
 if(r.error){ document.getElementById('msg_adm').innerText=r.error; return; }
 localStorage.setItem('empresa_id', emp_id);
 localStorage.setItem('empresa_nombre', r.nombre);
 localStorage.setItem('admin_logged','true');
 EMPRESA_ID=emp_id;
 document.getElementById('admin-login').style.display='none';
 document.getElementById('emp_actual_lbl').innerText='Empresa: '+emp_id+' - '+r.nombre;
 cargarTodo();
}
function entrarSinLogin(){
 document.getElementById('admin-login').style.display='none';
 EMPRESA_ID='DEFAULT';
 localStorage.setItem('empresa_id','DEFAULT');
 document.getElementById('emp_actual_lbl').innerText='Modo sin empresa (DEFAULT)';
 cargarTodo();
}
function logoutAdmin(){ localStorage.clear(); location.reload(); }
function checkAuth(){
 let logged=localStorage.getItem('admin_logged');
 let eid=localStorage.getItem('empresa_id');
 if(eid){ EMPRESA_ID=eid; document.getElementById('emp_actual_lbl').innerText='Empresa: '+eid; }
 if(!logged){
   // si quieres que pida login siempre, descomenta:
   // document.getElementById('admin-login').style.display='flex';
   document.getElementById('admin-login').style.display='flex';
 } else {
   document.getElementById('admin-login').style.display='none';
 }
}
function cargarTodo(){ cargarEmps(); cargarSucs(); cargarAsig(''); cargarDashboard(); cargarReporte(); cargarEmpresas(); }
checkAuth(); cargarTodo(); cambiarTipo();
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home(): return HTML

@app.get("/empresas")
def list_empresas():
    db=SessionLocal(); r=db.query(EmpresaDB).all(); db.close(); return r

@app.post("/empresas")
def crear_empresa(e: EmpresaCreate):
    db=SessionLocal()
    ex=db.query(EmpresaDB).filter(EmpresaDB.id==e.id).first()
    if ex:
        db.close()
        return {"error":"Empresa ID ya existe"}
    n=EmpresaDB(**e.dict()); db.add(n); db.commit(); db.refresh(n); db.close(); return n

@app.get("/init-demo")
def init_demo():
    db=SessionLocal()
    emp_id="DEMO"
    ex=db.query(EmpresaDB).filter(EmpresaDB.id==emp_id).first()
    if not ex:
        n=EmpresaDB(id=emp_id, nombre="Empresa DEMO", admin_user="admin", admin_pass="admin123")
        db.add(n); db.commit()
        s1=SucursalDB(id="SUC001", nombre="Matriz", empresa_id=emp_id)
        s2=SucursalDB(id="SUC002", nombre="Sucursal Norte", empresa_id=emp_id)
        db.add_all([s1,s2]); db.commit()
        e1=EmpleadoDB(id="EMP001", nombre="Juan Demo", puesto="Vendedor", sucursal="SUC001", usuario="juan", password="1234", sueldo_monto=15000, empresa_id=emp_id)
        db.add(e1); db.commit()
    db.close()
    return {"ok":True,"empresa_id":"DEMO","admin_user":"admin","admin_pass":"admin123","empleado_user":"juan","empleado_pass":"1234"}

@app.get("/login-empresa")
def login_empresa(empresa_id: str, usuario: str, password: str):
    db=SessionLocal()
    if empresa_id.upper()=="DEMO":
        ex=db.query(EmpresaDB).filter(EmpresaDB.id=="DEMO").first()
        if not ex:
            db.close()
            init_demo()
            db=SessionLocal()
    emp=db.query(EmpresaDB).filter(EmpresaDB.id==empresa_id, EmpresaDB.admin_user==usuario, EmpresaDB.admin_pass==password).first()
    if not emp:
        existe=db.query(EmpresaDB).filter(EmpresaDB.id==empresa_id).first()
        db.close()
        if not existe:
            return {"error":f"Empresa {empresa_id} no existe. Crea empresa o usa DEMO / admin / admin123"}
        return {"error":"Usuario o pass incorrecto"}
    db.close()
    return {"ok":True,"nombre":emp.nombre,"id":emp.id}

@app.get("/empleados")
def list_emp(empresa_id: str="DEFAULT"):
    db=SessionLocal()
    # si es DEFAULT, mostrar todos para no romper tu v10
    if empresa_id=="DEFAULT":
        r=db.query(EmpleadoDB).all()
    else:
        r=db.query(EmpleadoDB).filter((EmpleadoDB.empresa_id==empresa_id) | (EmpleadoDB.empresa_id=="DEFAULT")).all()
    db.close(); return r

@app.post("/empleados")
def create_emp(emp: EmpleadoCreate):
    db=SessionLocal()
    ex=db.query(EmpleadoDB).filter(EmpleadoDB.id==emp.id).first()
    if ex: db.delete(ex); db.commit()
    n=EmpleadoDB(**emp.dict())
    # limitar foto
    if n.foto_url and len(n.foto_url)>500000:
        n.foto_url=n.foto_url[:500000]
    db.add(n); db.commit(); db.refresh(n); db.close(); return n

@app.delete("/empleados/{empleado_id}")
def del_emp(empleado_id: str, empresa_id: str="DEFAULT"):
    db=SessionLocal()
    ex=db.query(EmpleadoDB).filter(EmpleadoDB.id==empleado_id).first()
    if ex: db.delete(ex); db.commit()
    db.close(); return {"ok":True}

@app.get("/sucursales")
def list_suc(empresa_id: str="DEFAULT"):
    db=SessionLocal()
    if empresa_id=="DEFAULT":
        r=db.query(SucursalDB).all()
    else:
        r=db.query(SucursalDB).filter((SucursalDB.empresa_id==empresa_id) | (SucursalDB.empresa_id=="DEFAULT")).all()
    db.close(); return r

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
    n=AsignacionDB(empleado_id=a.empleado_id, tipo="dia", fecha=a.fecha, sucursal_dia=a.sucursal_id, empresa_id=a.empresa_id)
    db.add(n); db.commit(); db.refresh(n); db.close(); return n
@app.post("/asignaciones/semana")
def asig_semana(a: AsigSemana):
    db=SessionLocal()
    ex=db.query(AsignacionDB).filter(AsignacionDB.empleado_id==a.empleado_id, AsignacionDB.tipo=="semana", AsignacionDB.semana==a.semana).first()
    if ex: db.delete(ex); db.commit()
    n=AsignacionDB(empleado_id=a.empleado_id, tipo="semana", semana=a.semana, lunes=a.lunes, martes=a.martes, miercoles=a.miercoles, jueves=a.jueves, viernes=a.viernes, sabado=a.sabado, domingo=a.domingo, empresa_id=a.empresa_id)
    db.add(n); db.commit(); db.refresh(n); db.close(); return n
@app.post("/asignaciones/mes")
def asig_mes(a: AsigMes):
    db=SessionLocal()
    ex=db.query(AsignacionDB).filter(AsignacionDB.empleado_id==a.empleado_id, AsignacionDB.tipo=="mes", AsignacionDB.mes==a.mes).first()
    if ex: db.delete(ex); db.commit()
    n=AsignacionDB(empleado_id=a.empleado_id, tipo="mes", mes=a.mes, sucursal_mes=a.sucursal_id, empresa_id=a.empresa_id)
    db.add(n); db.commit(); db.refresh(n); db.close(); return n
@app.get("/asignaciones")
def list_asig(empresa_id: str="DEFAULT", tipo: str=""):
    db=SessionLocal(); 
    if empresa_id=="DEFAULT":
        q=db.query(AsignacionDB)
    else:
        q=db.query(AsignacionDB).filter((AsignacionDB.empresa_id==empresa_id) | (AsignacionDB.empresa_id=="DEFAULT"))
    if tipo: q=q.filter(AsignacionDB.tipo==tipo)
    r=q.order_by(AsignacionDB.created_at.desc()).all(); db.close(); return r

@app.get("/empleado/{empleado_id}/hoy")
def hoy(empleado_id: str, empresa_id: str="DEFAULT"):
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
def login(usuario: str, password: str, empresa_id: str="DEFAULT"):
    db=SessionLocal()
    if empresa_id=="DEFAULT":
        emp=db.query(EmpleadoDB).filter(EmpleadoDB.usuario==usuario, EmpleadoDB.password==password).first()
    else:
        emp=db.query(EmpleadoDB).filter(EmpleadoDB.usuario==usuario, EmpleadoDB.password==password).filter((EmpleadoDB.empresa_id==empresa_id) | (EmpleadoDB.empresa_id=="DEFAULT")).first()
    if not emp:
        db.close()
        return {"error":"Usuario o pass incorrecto"}
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
    emp_dict={"id":emp.id,"nombre":emp.nombre,"puesto":emp.puesto,"horario_entrada":emp.horario_entrada,"horario_salida":emp.horario_salida,"estatus":emp.estatus,"vacaciones_totales":emp.vacaciones_totales,"vacaciones_tomadas":emp.vacaciones_tomadas,"faltas":emp.faltas,"retardos":emp.retardos,"promedio_eval":emp.promedio_eval,"foto_url":emp.foto_url,"sueldo_tipo":emp.sueldo_tipo,"sueldo_monto":emp.sueldo_monto}
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
            h_ent = emp.horario_entrada or "09:00"
            if hora_actual > h_ent:
                es_retardo=True
                emp.retardos = (emp.retardos or 0) + 1
        except:
            pass
    visita=VisitaDB(empleado_id=v.empleado_id, sucursal_id=v.sucursal_id, sucursal_nombre=v.sucursal_nombre, es_retardo=es_retardo, notas=v.notas + (" - RETARDO" if es_retardo else " - A TIEMPO") + f" GPS:{v.lat},{v.lon}", empresa_id=v.empresa_id)
    db.add(visita); db.commit(); db.refresh(visita)
    db.commit()
    db.close()
    return {"ok":True,"es_retardo":es_retardo,"mensaje": "Check-In con retardo" if es_retardo else "Check-In a tiempo"}

@app.post("/jornada/marcar")
def marcar_jornada(m: JornadaMarcar):
    db=SessionLocal()
    hoy=datetime.now().strftime("%Y-%m-%d")
    hora=datetime.now().strftime("%H:%M:%S")
    gps_txt = m.gps or f"{m.lat},{m.lon}" if m.lat else ""
    jornada=db.query(JornadaDB).filter(JornadaDB.empleado_id==m.empleado_id, JornadaDB.fecha==hoy).first()
    if not jornada:
        jornada=JornadaDB(empleado_id=m.empleado_id, empresa_id=m.empresa_id, fecha=hoy)
        db.add(jornada); db.commit(); db.refresh(jornada)
    if m.tipo=="entrada":
        if jornada.entrada: db.close(); return {"error":"Ya marcaste entrada hoy a las "+jornada.entrada}
        jornada.entrada=hora; jornada.entrada_lat=m.lat; jornada.entrada_lon=m.lon; jornada.entrada_gps=gps_txt
        emp=db.query(EmpleadoDB).filter(EmpleadoDB.id==m.empleado_id).first()
        if emp and emp.horario_entrada:
            try:
                if hora[:5] > emp.horario_entrada:
                    emp.retardos=(emp.retardos or 0)+1
            except: pass
    elif m.tipo=="salida_comida":
        if not jornada.entrada: db.close(); return {"error":"Primero marca entrada"}
        if jornada.salida_comida: db.close(); return {"error":"Ya marcaste salida a comer"}
        jornada.salida_comida=hora; jornada.salida_comida_lat=m.lat; jornada.salida_comida_lon=m.lon; jornada.salida_comida_gps=gps_txt
    elif m.tipo=="regreso_comida":
        if not jornada.salida_comida: db.close(); return {"error":"Primero marca salida a comer"}
        if jornada.regreso_comida: db.close(); return {"error":"Ya marcaste regreso"}
        jornada.regreso_comida=hora; jornada.regreso_comida_lat=m.lat; jornada.regreso_comida_lon=m.lon; jornada.regreso_comida_gps=gps_txt
    elif m.tipo=="salida_final":
        if not jornada.entrada: db.close(); return {"error":"No marcaste entrada"}
        if jornada.salida_final: db.close(); return {"error":"Ya marcaste salida final"}
        jornada.salida_final=hora; jornada.salida_final_lat=m.lat; jornada.salida_final_lon=m.lon; jornada.salida_final_gps=gps_txt
        try:
            from datetime import datetime as dt
            fmt="%H:%M:%S"
            e=dt.strptime(jornada.entrada, fmt); s=dt.strptime(jornada.salida_final, fmt)
            diff=(s-e).seconds/3600
            if jornada.salida_comida and jornada.regreso_comida:
                sc=dt.strptime(jornada.salida_comida, fmt); rc=dt.strptime(jornada.regreso_comida, fmt)
                diff-=(rc-sc).seconds/3600
            jornada.horas_trabajadas=round(diff,2)
        except: pass
    else:
        db.close(); return {"error":"Tipo invalido"}
    db.commit(); db.refresh(jornada); db.close()
    return {"ok":True, "jornada": {"fecha":jornada.fecha, "entrada":jornada.entrada, "entrada_gps":jornada.entrada_gps, "salida_comida":jornada.salida_comida, "salida_comida_gps":jornada.salida_comida_gps, "regreso_comida":jornada.regreso_comida, "regreso_comida_gps":jornada.regreso_comida_gps, "salida_final":jornada.salida_final, "salida_final_gps":jornada.salida_final_gps, "horas":jornada.horas_trabajadas}}

@app.get("/jornada/hoy")
def jornada_hoy(empleado_id: str, empresa_id: str="DEFAULT"):
    db=SessionLocal()
    hoy=datetime.now().strftime("%Y-%m-%d")
    j=db.query(JornadaDB).filter(JornadaDB.empleado_id==empleado_id, JornadaDB.fecha==hoy).first()
    db.close()
    if not j: return {"fecha":hoy, "entrada":"", "salida_comida":"", "regreso_comida":"", "salida_final":"", "horas":0}
    return {"fecha":j.fecha, "entrada":j.entrada, "entrada_lat":j.entrada_lat, "entrada_lon":j.entrada_lon, "entrada_gps":j.entrada_gps, "salida_comida":j.salida_comida, "salida_comida_gps":j.salida_comida_gps, "regreso_comida":j.regreso_comida, "regreso_comida_gps":j.regreso_comida_gps, "salida_final":j.salida_final, "salida_final_gps":j.salida_final_gps, "horas":j.horas_trabajadas}

@app.get("/jornadas")
def list_jornadas(empresa_id: str="DEFAULT", empleado_id: str=""):
    db=SessionLocal()
    q=db.query(JornadaDB)
    if empresa_id!="DEFAULT":
        q=q.filter((JornadaDB.empresa_id==empresa_id) | (JornadaDB.empresa_id=="DEFAULT"))
    if empleado_id:
        q=q.filter(JornadaDB.empleado_id==empleado_id)
    r=q.order_by(JornadaDB.fecha.desc()).limit(300).all()
    db.close(); return r

@app.get("/visitas")
def list_visitas(empresa_id: str="DEFAULT", empleado_id: str=""):
    db=SessionLocal()
    q=db.query(VisitaDB)
    if empresa_id!="DEFAULT":
        q=q.filter((VisitaDB.empresa_id==empresa_id) | (VisitaDB.empresa_id=="DEFAULT"))
    if empleado_id:
        q=q.filter(VisitaDB.empleado_id==empleado_id)
    r=q.order_by(VisitaDB.created_at.desc()).limit(300).all()
    db.close(); return r

@app.post("/vacaciones")
def crear_vac(v: VacacionCreate):
    db=SessionLocal()
    n=VacacionDB(**v.dict())
    db.add(n); db.commit(); db.refresh(n); db.close(); return n

@app.get("/vacaciones")
def list_vac(empresa_id: str="DEFAULT", empleado_id: str=""):
    db=SessionLocal()
    q=db.query(VacacionDB)
    if empresa_id!="DEFAULT":
        q=q.filter((VacacionDB.empresa_id==empresa_id) | (VacacionDB.empresa_id=="DEFAULT"))
    if empleado_id:
        q=q.filter(VacacionDB.empleado_id==empleado_id)
    r=q.order_by(VacacionDB.created_at.desc()).all()
    db.close()
    return r

@app.post("/vacaciones/{vac_id}/estatus")
def estatus_vac(vac_id: int, data: dict, empresa_id: str="DEFAULT"):
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
    n=EvaluacionDB(empleado_id=e.empleado_id, calificacion=e.calificacion, comentario=e.comentario, empresa_id=e.empresa_id)
    db.add(n)
    evals=db.query(EvaluacionDB).filter(EvaluacionDB.empleado_id==e.empleado_id).all()
    total=sum([x.calificacion for x in evals]) + e.calificacion
    prom=total / (len(evals)+1) if evals else e.calificacion
    emp=db.query(EmpleadoDB).filter(EmpleadoDB.id==e.empleado_id).first()
    if emp:
        emp.promedio_eval=round(prom,1)
    db.commit(); db.refresh(n); db.close(); return n

@app.get("/evaluaciones")
def list_eval(empresa_id: str="DEFAULT", empleado_id: str=""):
    db=SessionLocal()
    q=db.query(EvaluacionDB)
    if empresa_id!="DEFAULT":
        q=q.filter((EvaluacionDB.empresa_id==empresa_id) | (EvaluacionDB.empresa_id=="DEFAULT"))
    if empleado_id:
        q=q.filter(EvaluacionDB.empleado_id==empleado_id)
    r=q.order_by(EvaluacionDB.created_at.desc()).all()
    db.close()
    return r

@app.post("/empleado/{empleado_id}/cambiar-pass")
def cambiar_pass(empleado_id: str, data: dict, empresa_id: str="DEFAULT"):
    db=SessionLocal()
    emp=db.query(EmpleadoDB).filter(EmpleadoDB.id==empleado_id).first()
    if not emp:
        db.close()
        return {"error":"Empleado no existe"}
    actual=data.get("actual","")
    nueva=data.get("nueva","")
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

@app.get("/reporte/csv")
def reporte_csv(empresa_id: str="DEFAULT"):
    db=SessionLocal()
    if empresa_id=="DEFAULT":
        emps=db.query(EmpleadoDB).all()
    else:
        emps=db.query(EmpleadoDB).filter((EmpleadoDB.empresa_id==empresa_id) | (EmpleadoDB.empresa_id=="DEFAULT")).all()
    db.close()
    csv="ID,Nombre,Puesto,Sucursal,SueldoTipo,Monto,Estatus,Faltas,Retardos,VacTomadas,VacTotales,Eval,Empresa\n"
    for e in emps:
        csv+=f"{e.id},{e.nombre},{e.puesto},{e.sucursal},{e.sueldo_tipo},{e.sueldo_monto},{e.estatus},{e.faltas},{e.retardos},{e.vacaciones_tomadas},{e.vacaciones_totales},{e.promedio_eval},{e.empresa_id}\n"
    return PlainTextResponse(csv, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=reporte_{empresa_id}.csv"})

