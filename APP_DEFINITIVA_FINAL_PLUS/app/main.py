
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import uuid, math, json, os, hashlib, random

app = FastAPI(title="Control BONITA 100% FINAL - NEON MULTI-EMPRESA COMPLETO")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
DB_FILE = "database.json"
DB_SQLITE = "clockrd.db"
DATABASE_URL = os.environ.get("DATABASE_URL", "")
def hash_pass(p): return hashlib.sha256(p.encode()).hexdigest()[:16]

import sqlite3
try:
    from sqlalchemy import create_engine, Column, String, Text, Boolean, Integer, DateTime, Float, text
    from sqlalchemy.orm import declarative_base, sessionmaker
    HAS_SQLALCHEMY = True
except:
    HAS_SQLALCHEMY = False

def get_db_engine():
    if DATABASE_URL:
        url = DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return create_engine(url, pool_pre_ping=True)
    else:
        return create_engine(f"sqlite:///{DB_SQLITE}", connect_args={"check_same_thread": False})

if HAS_SQLALCHEMY:
    engine = get_db_engine()
    Base = declarative_base()
    class Empresa(Base):
        __tablename__ = "empresas"
        id = Column(String, primary_key=True)
        nombre_admin = Column(String)
        usuario = Column(String, unique=True)
        empresa = Column(String)
        direccion = Column(String)
        correo = Column(String)
        telefono = Column(String)
        password = Column(String)
        logo = Column(Text)
        slogan = Column(String)
        color = Column(String)
        created_at = Column(String)
        data = Column(Text)
    class EmpleadoDB(Base):
        __tablename__ = "empleados"
        id = Column(String, primary_key=True)
        empresa_id = Column(String, index=True)
        nombre = Column(String)
        puesto = Column(String)
        password = Column(String)
        data = Column(Text) # JSON con todo el perfil completo
    class SucursalDB(Base):
        __tablename__ = "sucursales"
        id = Column(String, primary_key=True)
        empresa_id = Column(String, index=True)
        data = Column(Text)
    class AsistenciaDB(Base):
        __tablename__ = "asistencias"
        id = Column(String, primary_key=True)
        empleado_id = Column(String, index=True)
        empresa_id = Column(String, index=True)
        fecha = Column(String)
        fecha_dia = Column(String)
        data = Column(Text)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
else:
    engine = None

# MEMORIA
sucursales_db = {}
empleados_db = {}
empresa_db = {"empresas": {}}
admins_db = {"admin": {"password": hash_pass("admin123"), "rol": "superadmin", "nombre": "Admin Principal", "empresa_id": "GLOBAL"}}
evaluaciones_db=[]; asistencias_db=[]; alertas_db=[]; gps_logs_db=[]; vacaciones_db=[]; justificantes_db=[]; audit_db=[]; chat_db=[]; panico_db=[]; reportes_volanteo_db=[]; verificaciones_db={}; bonos_db={}; metas_db={}; nomina_db={}; notificaciones_db=[]; turnos_rotativos_db={}; config_admin_db={"telefono_admin":"","whatsapp_activo":True,"bono_puntualidad":500,"sueldo_default":50}; perfil_fotos_db={}
permisos_db = {"empleado":{"ver":["propia_jornada"],"editar":[]},"supervisor":{"ver":["dashboard","empleados","sucursales","retardos"],"editar":[]},"rh":{"ver":["dashboard","empleados","retardos","nomina","vacaciones"],"editar":["empleados","vacaciones"]},"gerente":{"ver":["dashboard","sucursales","empleados","retardos","ruta_gps","vacaciones"],"editar":["sucursales","empleados"]},"admin":{"ver":["todo"],"editar":["todo"]}}

# FUNCIONES DB
def db_save_empresa(empresa_id, info):
    if not HAS_SQLALCHEMY: return
    s=SessionLocal()
    try:
        ex=s.query(Empresa).filter_by(id=empresa_id).first()
        if ex:
            ex.data=json.dumps(info)
            ex.nombre_admin=info.get("nombre_admin"); ex.usuario=info.get("usuario"); ex.empresa=info.get("empresa")
            ex.correo=info.get("correo"); ex.telefono=info.get("telefono")
        else:
            s.add(Empresa(id=empresa_id, nombre_admin=info.get("nombre_admin"), usuario=info.get("usuario"), empresa=info.get("empresa"), direccion=info.get("direccion"), correo=info.get("correo"), telefono=info.get("telefono"), password=info.get("password",""), created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), data=json.dumps(info)))
        s.commit()
    finally: s.close()

def db_save_empleado(emp):
    if not HAS_SQLALCHEMY: return
    s=SessionLocal()
    try:
        ex=s.query(EmpleadoDB).filter_by(id=emp["id"]).first()
        if ex:
            ex.empresa_id=emp.get("empresa_id",""); ex.nombre=emp.get("nombre"); ex.puesto=emp.get("puesto"); ex.password=emp.get("password"); ex.data=json.dumps(emp)
        else:
            s.add(EmpleadoDB(id=emp["id"], empresa_id=emp.get("empresa_id",""), nombre=emp.get("nombre"), puesto=emp.get("puesto"), password=emp.get("password"), data=json.dumps(emp)))
        s.commit()
    finally: s.close()

def db_save_sucursal(suc):
    if not HAS_SQLALCHEMY: return
    s=SessionLocal()
    try:
        ex=s.query(SucursalDB).filter_by(id=suc["id"]).first()
        if ex: ex.data=json.dumps(suc)
        else: s.add(SucursalDB(id=suc["id"], empresa_id=suc.get("empresa_id",""), data=json.dumps(suc)))
        s.commit()
    finally: s.close()

def db_load_all():
    if not HAS_SQLALCHEMY or not DATABASE_URL: return
    s=SessionLocal()
    try:
        for e in s.query(Empresa).all():
            try: data=json.loads(e.data) if e.data else {}
            except: data={}
            data["id"]=e.id
            empresa_db["empresas"][e.id]=data
            if e.usuario:
                admins_db[e.usuario]={"password":e.password, "rol":"superadmin", "nombre":e.nombre_admin, "empresa_id":e.id, "empresa":e.empresa}
                if e.correo: admins_db[e.correo]={"password":e.password, "rol":"superadmin", "nombre":e.nombre_admin, "empresa_id":e.id, "empresa":e.empresa}
        for em in s.query(EmpleadoDB).all():
            try: d=json.loads(em.data)
            except: d={"id":em.id,"nombre":em.nombre,"puesto":em.puesto,"password":em.password,"empresa_id":em.empresa_id}
            empleados_db[em.id]=d
        for su in s.query(SucursalDB).all():
            try: d=json.loads(su.data)
            except: d={}
            sucursales_db[su.id]=d
    finally: s.close()

db_load_all()

def save_db():
    if DATABASE_URL and HAS_SQLALCHEMY: return
    try:
        with open(DB_FILE,'w', encoding='utf-8') as f: json.dump({"sucursales":sucursales_db,"empleados":empleados_db,"empresa":empresa_db}, f, ensure_ascii=False, indent=2)
    except: pass

def get_next_id(empresa_id=None):
    max_num=0
    for eid, emp in empleados_db.items():
        if empresa_id and emp.get("empresa_id")!=empresa_id: continue
        try:
            if eid.startswith("EMP"): num=int(eid.replace("EMP","")); max_num=max(max_num,num)
        except: pass
    return f"EMP{max_num+1:04d}"

def distancia_m(lat1, lon1, lat2, lon2):
    try:
        R=6371000; phi1=math.radians(lat1); phi2=math.radians(lat2); dphi=math.radians(lat2-lat1); dlambda=math.radians(lon2-lon1); a=math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2; c=2*math.atan2(math.sqrt(a), math.sqrt(1-a)); return R*c
    except: return 0

def audit_log(usuario, accion, detalle):
    audit_db.append({"fecha":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"usuario":usuario,"accion":accion,"detalle":detalle})
    if len(audit_db)>500: audit_db.pop(0)


@app.get("/api/empleado/{eid}/turnos-semanales")
def get_turnos_semanales(eid: str):
    emp = empleados_db.get(eid)
    if not emp: raise HTTPException(404)
    return emp.get("turnos_semanales", {})

@app.post("/api/empleado/{eid}/turnos-semanales")
def save_turno_semanal(eid: str, data: dict):
    if eid not in empleados_db: raise HTTPException(404)
    semana = data.get("semana") # formato 2026-W32
    horario = data.get("horario") # {lunes: suc_id, ...}
    if not semana or not horario: raise HTTPException(400, "Falta semana u horario")
    if "turnos_semanales" not in empleados_db[eid]:
        empleados_db[eid]["turnos_semanales"] = {}
    empleados_db[eid]["turnos_semanales"][semana] = horario
    # Si es la semana actual, actualizar horario principal también
    from datetime import datetime
    hoy = datetime.now()
    anio_actual, semana_actual, _ = hoy.isocalendar()
    semana_str = f"{anio_actual}-W{semana_actual:02d}"
    if semana == semana_str:
        empleados_db[eid]["horario"] = horario
    db_save_empleado(empleados_db[eid])
    return {"ok": True, "semana": semana, "horario": horario}

@app.delete("/api/empleado/{eid}/turnos-semanales/{semana}")
def delete_turno_semanal(eid: str, semana: str):
    if eid in empleados_db and "turnos_semanales" in empleados_db[eid]:
        if semana in empleados_db[eid]["turnos_semanales"]:
            del empleados_db[eid]["turnos_semanales"][semana]
            db_save_empleado(empleados_db[eid])
    return {"ok": True}

DIAS_RETENCION=60
def limpiar_gps_antiguo():
    limite = datetime.now() - timedelta(days=DIAS_RETENCION)
    def es_reciente(f):
        try: return datetime.strptime(f, "%Y-%m-%d %H:%M:%S") >= limite
        except: return True
    gps_logs_db[:] = [g for g in gps_logs_db if es_reciente(g.get("fecha",""))]
    alertas_db[:] = [a for a in alertas_db if a.get("tipo")!="gps_fuera" or es_reciente(a.get("fecha",""))]

# === ENDPOINTS CORE ===
@app.get("/api/db-status")
def db_status():
    return {
        "tipo": "PostgreSQL-Neon" if DATABASE_URL else "JSON-Temporal",
        "conectado_neon": bool(DATABASE_URL),
        "total_empresas": len(empresa_db.get("empresas",{})),
        "total_empleados": len(empleados_db),
        "por_empresa": {eid: len([e for e in empleados_db.values() if e.get("empresa_id")==eid]) for eid in empresa_db.get("empresas",{})}
    }

@app.post("/api/registro-empresa")
def registro_empresa(data: dict):
    nombre=data.get("nombre"); usuario=data.get("usuario"); empresa=data.get("empresa")
    direccion=data.get("direccion"); correo=data.get("correo"); telefono=data.get("telefono")
    password=data.get("password"); confirm=data.get("confirm_password")
    if not all([nombre,usuario,empresa,direccion,correo,telefono,password,confirm]): raise HTTPException(400,"Faltan campos")
    if password!=confirm: raise HTTPException(400,"Contraseñas no coinciden")
    if usuario in admins_db: raise HTTPException(400,"Usuario ya existe")
    empresa_id = str(uuid.uuid4())[:8].upper()
    info={"id":empresa_id,"nombre_admin":nombre,"usuario":usuario.lower().strip(),"empresa":empresa,"direccion":direccion,"correo":correo,"telefono":telefono,"password":hash_pass(password),"fecha_registro":datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    empresa_db["empresas"][empresa_id]=info
    admins_db[usuario.lower()]={"password":hash_pass(password),"rol":"superadmin","nombre":nombre,"empresa_id":empresa_id,"empresa":empresa}
    admins_db[correo]={"password":hash_pass(password),"rol":"superadmin","nombre":nombre,"empresa_id":empresa_id,"empresa":empresa}
    db_save_empresa(empresa_id, info)
    save_db()
    return {"ok":True,"empresa_id":empresa_id,"usuario":usuario.lower()}

@app.post("/api/login")
def login(d: dict):
    u=d.get("usuario"); p=d.get("password"); hp=hash_pass(p)
    if u in admins_db and (admins_db[u]["password"]==hp or admins_db[u]["password"]==p):
        return {"rol":"admin","subrol":admins_db[u]["rol"],"usuario":u,"nombre":admins_db[u]["nombre"],"empresa_id":admins_db[u].get("empresa_id"),"empresa":admins_db[u].get("empresa")}
    if u in empleados_db:
        emp=empleados_db[u]
        if not emp.get("activo",True): raise HTTPException(403, "DESACTIVADO")
        if emp.get("password")==p or emp.get("password")==hp:
            return {"rol":"empleado","usuario":u,"nombre":emp["nombre"],"empresa_id":emp.get("empresa_id")}
        raise HTTPException(401, "Contraseña incorrecta")
    raise HTTPException(401, "No existe")

@app.get("/empleados/next-id")
def next_id(empresa_id: str = None, x_empresa_id: str = Header(None)):
    eid = empresa_id or x_empresa_id
    return {"next_id": get_next_id(eid)}

@app.get("/sucursales")
def ls(empresa_id: str = None, x_empresa_id: str = Header(None)):
    f = empresa_id or x_empresa_id
    if f: return [s for s in sucursales_db.values() if s.get("empresa_id")==f]
    return list(sucursales_db.values())

@app.post("/sucursales")
def cs(s: dict, x_empresa_id: str = Header(None)):
    empresa_id = s.get("empresa_id") or x_empresa_id
    s["empresa_id"]=empresa_id
    sucursales_db[s["id"]]=s
    db_save_sucursal(s)
    save_db()
    return s

@app.put("/sucursales/{sid}")
def upd_suc(sid: str, data: dict):
    if sid not in sucursales_db: raise HTTPException(404)
    sucursales_db[sid].update(data); db_save_sucursal(sucursales_db[sid]); save_db(); return sucursales_db[sid]

@app.delete("/sucursales/{sid}")
def del_suc(sid: str):
    if sid in sucursales_db: del sucursales_db[sid]; save_db()
    return {"ok":True}

@app.get("/empleados")
def le(empresa_id: str = None, x_empresa_id: str = Header(None)):
    f = empresa_id or x_empresa_id
    if f: return [e for e in empleados_db.values() if e.get("empresa_id")==f and not e.get("eliminado")]
    return [e for e in empleados_db.values() if not e.get("eliminado")]

# MODELO EMPLEADO COMPLETO - CAMPOS FALTANTES AGREGADOS
@app.post("/empleados")
def ce(e: dict, x_empresa_id: str = Header(None)):
    empresa_id = e.get("empresa_id") or x_empresa_id
    if not empresa_id:
        # toma primera empresa disponible
        if empresa_db["empresas"]:
            empresa_id = list(empresa_db["empresas"].keys())[0]
    if not e.get("id") or e["id"]=="": e["id"]=get_next_id(empresa_id)
    if e["id"] in empleados_db: e["id"]=get_next_id(empresa_id)
    # Campos obligatorios completos
    empleado_completo = {
        # Identificación
        "id": e["id"],
        "empresa_id": empresa_id,
        "nombre": e.get("nombre",""),
        "apellido_paterno": e.get("apellido_paterno",""),
        "apellido_materno": e.get("apellido_materno",""),
        "puesto": e.get("puesto",""),
        "departamento": e.get("departamento",""),
        "rol": e.get("rol","empleado"),
        "password": hash_pass(e.get("password","")) if e.get("password") else hash_pass(e["id"]),
        "foto": e.get("foto",""),
        # Datos personales (FALTABAN)
        "curp": e.get("curp",""),
        "rfc": e.get("rfc",""),
        "nss": e.get("nss",""),
        "fecha_nacimiento": e.get("fecha_nacimiento",""),
        "genero": e.get("genero",""),
        "estado_civil": e.get("estado_civil",""),
        "telefono": e.get("telefono",""),
        "telefono_emergencia": e.get("telefono_emergencia",""),
        "contacto_emergencia_nombre": e.get("contacto_emergencia_nombre",""),
        "email_personal": e.get("email_personal",""),
        "direccion_completa": e.get("direccion_completa",""),
        "tipo_sangre": e.get("tipo_sangre",""),
        # Datos laborales (FALTABAN)
        "fecha_ingreso": e.get("fecha_ingreso", datetime.now().strftime("%Y-%m-%d")),
        "tipo_contrato": e.get("tipo_contrato","planta"), # planta, temporal, honorarios
        "sueldo_hora": float(e.get("sueldo_hora", config_admin_db.get("sueldo_default",50))),
        "sueldo_mensual": float(e.get("sueldo_mensual",0)),
        "banco": e.get("banco",""),
        "clabe": e.get("clabe",""),
        "cuenta": e.get("cuenta",""),
        # Operativos
        "sucursales_ids": e.get("sucursales_ids",[]),
        "horario": e.get("horario",{}),
        "dias_descanso": e.get("dias_descanso",[]),
        "tiempo_comida": int(e.get("tiempo_comida",120)),
        "turno": e.get("turno","matutino"),
        "activo": e.get("activo",True),
        "eliminado": False,
        "fecha_creacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        # Documentos
        "documentos": e.get("documentos", {"ine": False, "comprobante_domicilio": False, "curp_doc": False, "contrato_firmado": False})
    }
    empleados_db[empleado_completo["id"]]=empleado_completo
    db_save_empleado(empleado_completo)
    save_db()
    return empleado_completo

@app.put("/empleados/{eid}")
def upd(eid: str, data: dict):
    if eid not in empleados_db: raise HTTPException(404)
    if "password" in data and data["password"]: data["password"]=hash_pass(data["password"])
    empleados_db[eid].update(data)
    db_save_empleado(empleados_db[eid])
    save_db()
    return empleados_db[eid]

@app.put("/empleados/{eid}/toggle")
def toggle(eid: str):
    if eid not in empleados_db: raise HTTPException(404)
    empleados_db[eid]["activo"]=not empleados_db[eid].get("activo",True)
    db_save_empleado(empleados_db[eid]); save_db(); return empleados_db[eid]

@app.delete("/empleados/{eid}")
def delete_emp(eid: str):
    if eid in empleados_db:
        empleados_db[eid]["activo"]=False; empleados_db[eid]["eliminado"]=True; empleados_db[eid]["fecha_eliminado"]=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db_save_empleado(empleados_db[eid]); save_db()
    return {"ok":True}

# Resto de endpoints originales (asistencia, gps, etc) se mantienen igual, usando empleados_db ya filtrado
@app.get("/asistencia/hoy/{eid}")
def asistencia_hoy(eid: str):
    hoy=datetime.now().strftime("%Y-%m-%d")
    reg = next((a for a in asistencias_db if a["empleado_id"]==eid and a["fecha_dia"]==hoy), None)
    tiempo = empleados_db.get(eid,{}).get("tiempo_comida",120)
    dias=["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]
    suc_id=empleados_db.get(eid,{}).get("horario",{}).get(dias[datetime.now().weekday()],"")
    suc=sucursales_db.get(suc_id, {})
    base={"empleado_id":eid,"fecha_dia":hoy,"tiempo_permitido":tiempo,"sucursal":suc}
    if not reg: return {**base,"estado":"sin_entrada","siguiente":"entrada","texto_boton":"📍 Registrar ENTRADA","color":"#10b981","gps_activo":False}
    if not reg.get("entrada"): return {**reg,**base,"estado":"sin_entrada","siguiente":"entrada","texto_boton":"📍 Registrar ENTRADA","color":"#10b981","gps_activo":False}
    if not reg.get("salida_comida"): return {**reg,**base,"estado":"trabajando","siguiente":"salida_comida","texto_boton":"🍔 Salida a COMER","color":"#f59e0b","gps_activo":True}
    if not reg.get("regreso_comida"): return {**reg,**base,"estado":"comiendo","siguiente":"regreso_comida","texto_boton":"↩️ Regreso de COMIDA","color":"#6366f1","gps_activo":False}
    if not reg.get("salida_final"): return {**reg,**base,"estado":"trabajando_tarde","siguiente":"salida_final","texto_boton":"🏠 SALIDA FINAL","color":"#ef4444","gps_activo":True}
    return {**reg,**base,"estado":"completo","siguiente":"completo","texto_boton":"✅ COMPLETADA","color":"#64748b","gps_activo":False}

@app.post("/asistencia/registrar")
def registrar(data: dict):
    eid=data.get("empleado_id"); tipo=data.get("tipo")
    if eid not in empleados_db: raise HTTPException(404)
    ahora=datetime.now(); hoy=ahora.strftime("%Y-%m-%d"); hora=ahora.strftime("%H:%M:%S")
    reg = next((a for a in asistencias_db if a["empleado_id"]==eid and a["fecha_dia"]==hoy), None)
    if not reg:
        reg={"id":str(uuid.uuid4())[:8],"empleado_id":eid,"empresa_id":empleados_db[eid].get("empresa_id"),"fecha":ahora.strftime("%Y-%m"),"fecha_dia":hoy,"entrada":None,"salida_comida":None,"regreso_comida":None,"salida_final":None,"retardo_entrada":0,"retardo_comida":0,"horas_trabajadas":0}
        asistencias_db.append(reg)
    if tipo=="entrada":
        if reg["entrada"]: raise HTTPException(400, "Ya entrada")
        reg["entrada"]=hora
    elif tipo=="salida_comida":
        reg["salida_comida"]=hora
    elif tipo=="regreso_comida":
        reg["regreso_comida"]=hora
    elif tipo=="salida_final":
        reg["salida_final"]=hora
        try:
            from datetime import datetime as dt
            e = dt.strptime(reg["entrada"], "%H:%M:%S"); s = dt.strptime(hora, "%H:%M:%S")
            diff = (s - e).total_seconds()/3600
            if diff<0: diff+=24
            reg["horas_trabajadas"]=round(diff,2)
        except: pass
    save_db(); return reg

# --- resto de endpoints minimizados para no romper ---
@app.get("/admin/dashboard")
def dashboard():
    hoy=datetime.now().strftime("%Y-%m-%d"); mes=datetime.now().strftime("%Y-%m")
    total_emp=len([e for e in empleados_db.values() if e.get("activo") and not e.get("eliminado")])
    return {"fecha":hoy,"mes":mes,"total_empleados":total_emp}

@app.get("/api/config-admin")
def get_config_admin(): return config_admin_db
@app.post("/api/config-admin")
def save_config_admin(data: dict):
    config_admin_db.update(data); save_db(); return config_admin_db

# === FIN BACKEND, INICIO HTML ===
HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Clock RD PRO</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--primary:#6366f1;--success:#10b981;--warning:#f59e0b;--danger:#ef4444;--bg:#0a0e1a;--card:#151a2a;--border:#1e293b;--text:#e2e8f0;--muted:#94a3b8}
body{font-family:'Inter',-apple-system,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;overflow-x:hidden}
/* LOGIN */
.login-box{max-width:420px;margin:60px auto;background:var(--card);border-radius:24px;padding:32px;border:1px solid var(--border);box-shadow:0 20px 60px rgba(0,0,0,.5)}
.hero{padding:20px;background:linear-gradient(135deg,#6366f1,#8b5cf6,#ec4899);border-radius:20px;margin:12px;text-align:center;color:white}
.card{background:var(--card);border:1px solid var(--border);border-radius:20px;padding:18px;margin-top:14px;transition:.25s}
.card:hover{border-color:#6366f1;transform:translateY(-2px);box-shadow:0 12px 30px rgba(99,102,241,.12)}
.btn{padding:12px 18px;border-radius:14px;border:none;font-weight:700;cursor:pointer;width:100%;margin-top:10px;transition:.2s;font-size:13px}
.btn:hover{transform:translateY(-1px);filter:brightness(1.1)}
.btn-primary{background:linear-gradient(135deg,#6366f1,#8b5cf6);color:white}
.btn-success{background:linear-gradient(135deg,#10b981,#06b6d4);color:white}
.btn-warning{background:#f59e0b;color:white}.btn-danger{background:#ef4444;color:white}.btn-dark{background:#0f172a;color:white;border:1px solid #334155}
.input{width:100%;padding:12px 14px;border-radius:12px;border:1px solid #334155;background:#0f172a;color:white;margin-top:8px;font-size:13px}
.input:focus{outline:none;border-color:var(--primary);box-shadow:0 0 0 3px rgba(99,102,241,.2)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.kpi{background:var(--card);border-radius:18px;padding:18px;text-align:center;border:1px solid var(--border);position:relative;overflow:hidden}
.kpi::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,var(--primary),#ec4899)}
.kpi b{font-size:26px;display:block}.kpi small{color:var(--muted);font-size:11px}
.paso{display:flex;align-items:center;gap:12px;padding:14px;background:var(--card);border-radius:14px;margin-top:10px;border-left:4px solid #334155}
.paso.completo{border-left-color:var(--success);background:rgba(16,185,129,.08)}
.paso.activo{border-left-color:var(--warning);background:rgba(245,158,11,.08)}
.gps-on{background:var(--success);color:white;padding:6px 14px;border-radius:20px;font-size:11px;font-weight:800;animation:pulse 1.5s infinite}
.gps-off{background:#334155;color:white;padding:6px 14px;border-radius:20px;font-size:11px}
@keyframes pulse{0%,100%{transform:scale(1)}50%{transform:scale(1.05)}}
.modal{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.85);backdrop-filter:blur(8px);display:none;align-items:center;justify-content:center;z-index:1000;padding:20px}
.modal-content{background:var(--card);border-radius:24px;padding:24px;max-width:520px;width:100%;max-height:92vh;overflow:auto;border:1px solid var(--border)}
/* NEW LAYOUT */
.app-layout{display:flex;min-height:100vh}
.sidebar{width:260px;background:var(--card);border-right:1px solid var(--border);padding:20px;display:flex;flex-direction:column;gap:6px;position:sticky;top:0;height:100vh;overflow-y:auto}
.sidebar-brand{display:flex;align-items:center;gap:12px;padding:12px 8px;margin-bottom:12px}
.sidebar-brand .logo{width:44px;height:44px;background:linear-gradient(135deg,#6366f1,#ec4899);border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:22px}
.sidebar-item{padding:12px 14px;border-radius:12px;display:flex;align-items:center;gap:10px;cursor:pointer;font-size:13px;font-weight:600;color:var(--muted);transition:.2s}
.sidebar-item:hover{background:#0f172a;color:white}
.sidebar-item.active{background:linear-gradient(135deg,#6366f1,#8b5cf6);color:white;box-shadow:0 4px 12px rgba(99,102,241,.3)}
.sidebar-section{font-size:10px;font-weight:800;color:#475569;letter-spacing:1px;margin-top:16px;padding:0 10px}
.main-content{flex:1;padding:20px;max-width:1400px;margin:0 auto;width:100%}
.topbar{display:flex;justify-content:space-between;align-items:center;padding:14px 20px;background:var(--card);border-bottom:1px solid var(--border);position:sticky;top:0;z-index:50;backdrop-filter:blur(10px)}
.tab-content{display:none;animation:fadeIn .3s}
.tab-content.active{display:block}
@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
/* BOTTOM NAV MOBILE */
.bottom-nav{display:none;position:fixed;bottom:0;left:0;right:0;background:rgba(21,26,42,.95);backdrop-filter:blur(20px);border-top:1px solid var(--border);padding:8px 6px;z-index:90;justify-content:space-around}
.bottom-nav-item{display:flex;flex-direction:column;align-items:center;gap:4px;padding:8px 12px;border-radius:14px;cursor:pointer;font-size:10px;color:var(--muted);transition:.2s;min-width:56px}
.bottom-nav-item.active{background:var(--primary);color:white}
.bottom-nav-item .icon{font-size:20px}
.badge{background:var(--danger);color:white;font-size:10px;padding:2px 6px;border-radius:10px;position:absolute;top:-4px;right:-4px}
/* Responsive */
@media(max-width:900px){
  .sidebar{display:none}
  .bottom-nav{display:flex}
  .main-content{padding:12px;padding-bottom:90px}
  .grid2,.grid4{grid-template-columns:1fr}
  .topbar{padding:12px 14px}
  .topbar h2{font-size:16px}
  .hero{margin:8px;border-radius:16px;padding:16px}
}
@media(min-width:901px){
  .bottom-nav{display:none !important}
}
.chip{display:inline-flex;align-items:center;gap:6px;padding:6px 12px;border-radius:20px;font-size:11px;font-weight:700;background:#0f172a;border:1px solid #334155}
</style>
<style id="dynamic-theme"></style>
</head><body>

<!-- REGISTRO MODAL -->
<div id="registro-empresa-modal" style="display:none;min-height:100vh;align-items:center;justify-content:center;padding:16px;background:var(--bg)">
<div style="background:var(--card);border:1px solid var(--border);border-radius:24px;padding:24px;max-width:440px;width:100%">
<div style="text-align:center;margin-bottom:16px"><div style="width:64px;height:64px;background:linear-gradient(135deg,#6366f1,#ec4899);border-radius:18px;display:inline-flex;align-items:center;justify-content:center;font-size:30px">🏢</div><h2 style="font-size:22px;margin-top:10px">Crear Empresa</h2><p style="font-size:12px;color:var(--muted)">Administrador principal</p></div>
<input id="reg_nombre" class="input" placeholder="Tu nombre completo *">
<input id="reg_usuario" class="input" placeholder="Usuario * Ej: admin_juan">
<input id="reg_empresa" class="input" placeholder="Empresa *">
<input id="reg_direccion" class="input" placeholder="Dirección *">
<div style="display:flex;gap:6px"><input id="reg_correo" class="input" placeholder="Correo Gmail *"><button class="btn btn-dark" onclick="enviarCodigoEmail()" style="width:auto;white-space:nowrap;font-size:10px;margin-top:8px">📧 Código</button></div>
<div id="correo-verif-area" style="display:none;background:#0f172a;padding:10px;border-radius:10px;margin-top:6px"><input id="reg_codigo_email" class="input" placeholder="Código 6 dígitos"><button class="btn btn-success" onclick="verificarEmail()" style="font-size:11px;padding:8px">✅ Verificar</button><p id="msg-email" style="font-size:10px;margin-top:4px"></p></div>
<div id="email-ok" style="display:none;color:#10b981;font-size:11px">✅ Correo verificado</div>
<input id="reg_password" type="password" class="input" placeholder="Contraseña *">
<input id="reg_confirm" type="password" class="input" placeholder="Confirmar contraseña *">
<div style="display:flex;gap:6px"><input id="reg_telefono" class="input" placeholder="WhatsApp ej 521... *"><button class="btn btn-dark" onclick="enviarCodigoWhatsApp()" style="width:auto;white-space:nowrap;font-size:10px;margin-top:8px">📱 Código</button></div>
<div id="whats-verif-area" style="display:none;background:#0f172a;padding:10px;border-radius:10px;margin-top:6px"><input id="reg_codigo_whats" class="input" placeholder="Código WhatsApp"><button class="btn btn-success" onclick="verificarWhatsApp()" style="font-size:11px;padding:8px">✅ Verificar</button><p id="msg-whats" style="font-size:10px;margin-top:4px"></p></div>
<div id="whats-ok" style="display:none;color:#10b981;font-size:11px">✅ WhatsApp verificado</div>
<button class="btn btn-primary" onclick="registrarEmpresa()" style="margin-top:12px">🚀 Crear Cuenta</button>
<p id="msg-registro" style="font-size:11px;margin-top:8px;text-align:center"></p>
<button class="btn btn-dark" onclick="mostrarLogin()" style="margin-top:6px">⬅️ Ya tengo cuenta</button>
</div></div>

<div id="login" class="login-box">
<div style="text-align:center"><div style="width:72px;height:72px;background:linear-gradient(135deg,#6366f1,#ec4899);border-radius:20px;display:inline-flex;align-items:center;justify-content:center;font-size:36px;margin-bottom:12px">⏰</div><h1 style="font-size:24px">Clock RD PRO</h1><p id="banner-nombre" style="font-size:12px;color:var(--muted);margin-top:4px">Control de asistencia inteligente</p></div>
<div style="background:linear-gradient(135deg,#6366f115,#8b5cf615);border:1px solid #6366f133;border-radius:14px;padding:12px;margin-top:16px"><small style="color:var(--muted)">✨ Nuevo: Diseño responsive • Móvil abajo, PC lateral</small></div>
<input id="u" class="input" placeholder="Usuario">
<input id="p" class="input" type="password" placeholder="Contraseña">
<button class="btn btn-primary" style="padding:16px" onclick="login()">INGRESAR →</button>
<div style="display:flex;gap:8px;margin-top:10px"><button class="btn btn-dark" style="margin-top:0" onclick="mostrarRecuperar()">🔑 Recuperar</button></div>
<button class="btn btn-success" onclick="mostrarRegistro()" style="margin-top:10px;background:linear-gradient(135deg,#10b981,#06b6d4);padding:14px;font-weight:bold;border:2px solid #10b981">🏢 Crear empresa por primera vez</button>
<div id="empresa-info-login" style="font-size:10px;color:var(--muted);margin-top:8px;text-align:center"></div>
<p id="msg" style="text-align:center;color:#ef4444;font-size:12px;margin-top:8px"></p>
<p style="text-align:center;color:var(--muted);font-size:10px;margin-top:12px">📱 En celular: menú abajo • 💻 En PC: menú lateral</p>
</div>

<!-- APP -->
<div id="app" style="display:none">
<div class="app-layout">
<!-- SIDEBAR DESKTOP -->
<div class="sidebar" id="sidebar">
<div class="sidebar-brand"><div class="logo">⏰</div><div><div style="font-weight:800;font-size:15px">Clock RD PRO</div><div id="user-display" style="font-size:11px;color:var(--muted)">Admin</div></div></div>
<div id="sidebar-admin" style="display:none">
<div class="sidebar-section">PRINCIPAL</div>
<div class="sidebar-item active" onclick="switchTab('tab-dashboard')"><span>📊</span> Dashboard</div>
<div class="sidebar-item" onclick="switchTab('tab-empleados')"><span>👥</span> Empleados</div>
<div class="sidebar-item" onclick="switchTab('tab-sucursales')"><span>🏢</span> Sucursales</div>
<div class="sidebar-section">CONTROL</div>
<div class="sidebar-item" onclick="switchTab('tab-retardos')"><span>⏱️</span> Retardos</div>
<div class="sidebar-item" onclick="switchTab('tab-gps')"><span>🗺️</span> GPS & Ruta</div>
<div class="sidebar-item" onclick="switchTab('tab-evaluaciones')"><span>⭐</span> Evaluaciones</div>
<div class="sidebar-section">FINANZAS</div>
<div class="sidebar-item" onclick="switchTab('tab-nomina')"><span>💰</span> Nómina</div>
<div class="sidebar-item" onclick="switchTab('tab-reportes')"><span>📈</span> Reportes</div>
<div class="sidebar-section">GESTIÓN</div>
<div class="sidebar-item" onclick="switchTab('tab-vacaciones')"><span>🏖️</span> Vacaciones</div>
<div class="sidebar-item" onclick="switchTab('tab-chat')"><span>💬</span> Chat</div>
<div class="sidebar-item" onclick="switchTab('tab-panico')"><span>🆘</span> Pánico SOS</div>
<div class="sidebar-section">SISTEMA</div>
<div class="sidebar-item" onclick="switchTab('tab-config')"><span>⚙️</span> Config & Backup</div>
<div class="sidebar-item" onclick="switchTab('tab-audit')"><span>📋</span> Auditoría</div>
<div style="margin-top:auto;padding-top:16px;border-top:1px solid var(--border)"><div class="sidebar-item" onclick="logout()"><span>🚪</span> Salir</div></div>
</div>
<div id="sidebar-emp" style="display:none">
<div class="sidebar-section">MI TRABAJO</div>
<div class="sidebar-item active" onclick="switchTabEmp('tab-emp-jornada')"><span>⏰</span> Mi Jornada</div>
<div class="sidebar-item" onclick="switchTabEmp('tab-emp-calendario')"><span>🗓️</span> Calendario</div>
<div class="sidebar-item" onclick="switchTabEmp('tab-emp-ranking')"><span>🏆</span> Ranking & Bono</div>
<div class="sidebar-item" onclick="switchTabEmp('tab-emp-historial')"><span>📊</span> Historial</div>
<div class="sidebar-section">GESTIÓN</div>
<div class="sidebar-item" onclick="switchTabEmp('tab-emp-vacaciones')"><span>🏖️</span> Vacaciones</div>
<div class="sidebar-item" onclick="switchTabEmp('tab-emp-perfil')"><span>👤</span> Mi Perfil</div>
<div class="sidebar-item" onclick="switchTabEmp('tab-emp-notif')"><span>🔔</span> Notificaciones</div>
<div style="margin-top:auto;padding-top:16px;border-top:1px solid var(--border)"><div class="sidebar-item" onclick="logout()"><span>🚪</span> Salir</div></div>
</div>
</div>

<div class="main-content">
<div class="topbar"><h2 id="topbar-title">📊 Dashboard</h2><div style="display:flex;align-items:center;gap:8px"><div class="chip">🟢 <span id="online-dot">Online</span></div><img id="topbar-foto" src="" style="width:36px;height:36px;border-radius:50%;background:#334155;display:none"></div></div>

<!-- ADMIN TABS -->
<div id="admin-area" style="display:none">
<div id="tab-dashboard" class="tab-content active">
<div class="hero"><div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px"><div style="display:flex;gap:12px;align-items:center"><div style="width:56px;height:56px;background:rgba(255,255,255,.2);border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:28px">⏰</div><div style="text-align:left"><h1 style="font-size:22px">Clock RD PRO</h1><p id="banner-nombre2" style="font-size:12px;opacity:.9">Panel Admin</p></div></div><div style="display:flex;gap:8px"><button class="btn btn-dark" onclick="exportarExcel()" style="width:auto;margin:0;padding:8px 14px;font-size:11px">📥 Excel</button><button class="btn btn-dark" onclick="exportarPDF()" style="width:auto;margin:0;padding:8px 14px;font-size:11px">📄 PDF</button></div></div></div>
<div class="grid4" id="kpi-row"></div>
<div id="card-memoria" class="card"><h3>💾 Almacenamiento Neon</h3><div style="display:flex;gap:12px;align-items:center;margin-top:12px"><div style="flex:1;background:#0f172a;border-radius:10px;height:12px;overflow:hidden"><div id="db-progress-bar" style="height:100%;background:linear-gradient(90deg,#6366f1,#ec4899);width:1%"></div></div><span id="mem-porcentaje" style="font-size:11px">0%</span></div><div style="display:flex;justify-content:space-between;margin-top:8px;font-size:11px;color:var(--muted)"><span id="db-usado-text">Usado: 0 MB</span><span id="db-libre-text">Libre: 3072 MB</span></div></div>
<div class="grid2"><div class="card"><h3>📊 Gráfica Retardos</h3><canvas id="chart-retardos"></canvas></div><div class="card"><h3>🕒 Horas por Empleado</h3><canvas id="chart-horas"></canvas></div></div>
<div class="card" id="card-ranking"><h3>🏆 Ranking Puntualidad</h3><div id="ranking-puntual" style="margin-top:10px"></div></div>
<div id="admin-pro-cards"></div>
</div>

<div id="tab-empleados" class="tab-content">
<div class="card" id="card-crear-empleado" style="border:2px solid #6366f1"><h3>👤 Nuevo Empleado COMPLETO (RH)</h3>
<div style="background:#10b98115;padding:8px;border-radius:10px;display:flex;justify-content:space-between"><small>Próximo: <b id="next-id" style="color:#10b981">...</b></small><small id="emp_empresa_badge" style="color:#6366f1"></small></div>

<div style="margin-top:12px"><b style="font-size:11px;color:#6366f1">📋 IDENTIFICACIÓN</b></div>
<div style="display:flex;gap:8px"><input id="emp_id" class="input" readonly style="flex:1"><button class="btn btn-dark" style="width:auto;margin-top:8px" onclick="generarID()">🔄</button></div>
<input id="emp_nombre" class="input" placeholder="Nombre(s) *">
<div style="display:flex;gap:8px"><input id="emp_ap_paterno" class="input" placeholder="Apellido Paterno *"><input id="emp_ap_materno" class="input" placeholder="Apellido Materno"></div>
<input id="emp_puesto" class="input" placeholder="Puesto * Ej: Vendedor, Botarga">
<div style="display:flex;gap:8px"><input id="emp_depto" class="input" placeholder="Departamento"><select id="emp_rol" class="input"><option value="empleado">👷 Empleado</option><option value="supervisor">👁️ Supervisor</option><option value="rh">📋 RH</option><option value="gerente">🏢 Gerente</option><option value="admin">👑 Admin</option></select></div>

<div style="margin-top:10px"><b style="font-size:11px;color:#ec4899">🪪 DATOS PERSONALES (lo que te faltaba)</b></div>
<div style="display:flex;gap:8px"><input id="emp_curp" class="input" placeholder="CURP"><input id="emp_rfc" class="input" placeholder="RFC"></div>
<div style="display:flex;gap:8px"><input id="emp_nss" class="input" placeholder="NSS (IMSS)"><input id="emp_fecha_nac" class="input" type="date" placeholder="Fecha Nacimiento"></div>
<div style="display:flex;gap:8px"><select id="emp_genero" class="input"><option value="">Género</option><option value="M">Masculino</option><option value="F">Femenino</option><option value="Otro">Otro</option></select><select id="emp_civil" class="input"><option value="">Estado Civil</option><option value="Soltero">Soltero</option><option value="Casado">Casado</option><option value="Union">Unión Libre</option><option value="Divorciado">Divorciado</option></select><input id="emp_sangre" class="input" placeholder="Tipo Sangre Ej O+"></div>
<input id="emp_direccion" class="input" placeholder="Dirección completa">
<input id="emp_email_personal" class="input" placeholder="Email personal">
<div style="display:flex;gap:8px"><input id="emp_telefono" class="input" placeholder="WhatsApp personal * Ej 521..."><input id="emp_tel_emergencia" class="input" placeholder="Tel Emergencia *"></div>
<input id="emp_contacto_emergencia" class="input" placeholder="Nombre contacto emergencia *">

<div style="margin-top:10px"><b style="font-size:11px;color:#10b981">💼 DATOS LABORALES</b></div>
<div style="display:flex;gap:8px"><input id="emp_fecha_ingreso" class="input" type="date"><select id="emp_tipo_contrato" class="input"><option value="planta">Planta</option><option value="temporal">Temporal</option><option value="honorarios">Honorarios</option><option value="practicas">Prácticas</option></select></div>
<div style="display:flex;gap:8px"><select id="emp_turno" class="input"><option value="matutino">🌅 Matutino</option><option value="vespertino">🌇 Vespertino</option><option value="nocturno">🌙 Nocturno</option><option value="mixto">🔄 Mixto</option></select><input id="emp_descansos" class="input" placeholder="Días descanso Ej: domingo"></div>
<div style="display:flex;gap:8px"><input id="emp_sueldo" class="input" type="number" placeholder="Sueldo x hora $" value="50"><input id="emp_sueldo_mensual" class="input" type="number" placeholder="Sueldo mensual $"></div>
<div style="display:flex;gap:8px"><input id="emp_banco" class="input" placeholder="Banco Ej BBVA"><input id="emp_cuenta" class="input" placeholder="Cuenta"><input id="emp_clabe" class="input" placeholder="CLABE"></div>

<div style="margin-top:10px"><b style="font-size:11px;color:#f59e0b">⚙️ OPERATIVO</b></div>
<div style="display:flex;gap:8px"><input id="emp_pass" class="input" placeholder="Contraseña *"><div style="display:flex;gap:8px;align-items:center;flex:1"><label style="font-size:11px">Comida:</label><input id="emp_comida" class="input" type="number" value="120" style="margin-top:0"><span style="font-size:11px">min</span></div></div>
<div id="check-suc" style="background:#0f172a;border-radius:10px;padding:8px;margin-top:8px;max-height:80px;overflow:auto"></div>

<div style="margin-top:12px;background:#6366f115;border:1px solid #6366f133;border-radius:12px;padding:12px">
<b style="font-size:11px;color:#6366f1">📅 ASIGNACIÓN POR SEMANA (Nuevo - Rota sucursales cada semana)</b>
<p style="font-size:10px;color:var(--muted)">Asigna diferente sucursal cada semana. Ej: Semana 32 en Sucursal Centro, Semana 33 en Sucursal Norte</p>
<div style="display:flex;gap:8px;margin-top:8px">
<input id="turno_semana" class="input" type="week" style="margin-top:0;flex:1">
<button class="btn btn-dark" onclick="cargarTurnoSemana()" style="width:auto;margin-top:0;font-size:11px">📥 Cargar</button>
</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px">
<div><label style="font-size:10px">Lunes</label><select id="sem_lunes" class="input"></select></div>
<div><label style="font-size:10px">Martes</label><select id="sem_martes" class="input"></select></div>
<div><label style="font-size:10px">Miércoles</label><select id="sem_miercoles" class="input"></select></div>
<div><label style="font-size:10px">Jueves</label><select id="sem_jueves" class="input"></select></div>
<div><label style="font-size:10px">Viernes</label><select id="sem_viernes" class="input"></select></div>
<div><label style="font-size:10px">Sábado</label><select id="sem_sabado" class="input"></select></div>
<div><label style="font-size:10px">Domingo</label><select id="sem_domingo" class="input"></select></div>
</div>
<button class="btn btn-primary" onclick="guardarTurnoSemanal()" style="margin-top:8px">💾 Guardar Semana</button>
<div id="turnos-semanales-lista" style="margin-top:10px;max-height:150px;overflow:auto;background:#0f172a;border-radius:8px;padding:8px;font-size:11px"></div>
</div>

<div style="margin-top:10px"><b style="font-size:11px">📌 HORARIO BASE (si no hay semana asignada)</b></div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px"><select id="d-lunes" class="input"></select><select id="d-martes" class="input"></select><select id="d-miercoles" class="input"></select><select id="d-jueves" class="input"></select><select id="d-viernes" class="input"></select><select id="d-sabado" class="input"></select><select id="d-domingo" class="input"></select></div>

<div style="margin-top:10px;display:flex;gap:6px"><label style="font-size:11px"><input type="checkbox" id="doc_ine"> INE</label><label style="font-size:11px"><input type="checkbox" id="doc_domicilio"> Comprobante</label><label style="font-size:11px"><input type="checkbox" id="doc_curp"> CURP doc</label><label style="font-size:11px"><input type="checkbox" id="doc_contrato"> Contrato</label></div>

<button class="btn btn-success" onclick="crearEmp()" style="margin-top:14px;padding:16px">💾 Guardar Empleado COMPLETO en Neon</button><button class="btn btn-dark" onclick="cancelarEdicion()" style="margin-top:8px">❌ Cancelar Edición</button>
</div>
<div class="card"><h3>📋 Lista Empleados</h3><div id="list-emp" style="margin-top:10px"></div></div>
</div>

<div id="tab-sucursales" class="tab-content">
<div class="card"><h3>🏢 Nueva Sucursal con GPS</h3><input id="suc_id" class="input" placeholder="ID Sucursal"><input id="suc_nombre" class="input" placeholder="Nombre"><input id="suc_dir" class="input" placeholder="Dirección"><div class="grid2"><input id="suc_he" class="input" type="time" value="08:00"><input id="suc_hs" class="input" type="time" value="18:00"></div><div class="grid2"><input id="suc_lat" class="input" placeholder="Latitud"><input id="suc_lng" class="input" placeholder="Longitud"></div><div style="display:flex;gap:8px;align-items:center"><input id="suc_radio" class="input" type="number" value="200" placeholder="Radio metros"><button class="btn btn-dark" onclick="obtenerGPS()" style="width:auto;margin-top:8px">📍 Mi GPS</button></div><button class="btn btn-primary" onclick="crearSuc()">🏢 Crear Sucursal</button></div>
<div class="card"><h3>📍 Sucursales</h3><div id="list-suc"></div></div>
</div>

<div id="tab-retardos" class="tab-content"><div class="card"><h3>⏱️ Retardos del Mes</h3><div id="retardos-admin"></div></div></div>
<div id="tab-gps" class="tab-content"><div class="card" style="border:2px solid #ef4444"><h3>🚨 Alertas GPS Fuera de Geocerca</h3><div id="gps-alertas"></div></div><div class="card"><h3>🗺️ Ruta GPS 60 días</h3><div style="display:flex;gap:8px"><input id="ruta_emp" class="input" placeholder="ID Empleado" style="margin-top:0"><button class="btn btn-dark" onclick="verRuta()" style="width:auto;margin-top:0">Ver Ruta</button><button class="btn btn-dark" onclick="verRutaTodos()" style="width:auto;margin-top:0">Todos</button><button class="btn btn-dark" onclick="exportarCSV()" style="width:auto;margin-top:0">CSV</button></div><div id="ruta-result" style="margin-top:12px;max-height:400px;overflow:auto;background:#0f172a;border-radius:12px;padding:12px;font-size:11px"></div></div></div>
<div id="tab-evaluaciones" class="tab-content"><div class="card"><h3>⭐ Evaluación 100 puntos</h3><div class="grid2"><select id="eval_emp" class="input"></select><div style="background:#10b98115;padding:10px;border-radius:10px;text-align:center"><div id="total-num" style="font-size:20px;font-weight:800">0/100</div><div id="total-preview" style="display:none;font-size:11px">Preview</div></div></div><div id="eval_preguntas"></div><button class="btn btn-success" onclick="evaluar()">⭐ Guardar Evaluación</button><p id="msg-eval" style="font-size:11px;margin-top:8px"></p></div></div>
<div id="tab-nomina" class="tab-content">
<div class="card" style="border:2px solid #10b981"><h3>💰 Nómina Automática</h3><div style="display:flex;gap:8px"><input id="nomina_mes" class="input" type="month" style="margin-top:0"><button class="btn btn-success" onclick="cargarNomina()" style="width:auto;margin-top:0">💰 Calcular</button></div><div id="nomina-result" style="margin-top:12px"></div></div>
<div class="card" style="border:2px solid #8b5cf6"><h3>🔐 Permisos por Rol</h3><div id="permisos-editor"></div><button class="btn btn-primary" onclick="guardarPermisos()">💾 Guardar Permisos</button><button class="btn btn-dark" onclick="cargarPermisos()">🔄 Cargar</button><p id="msg-permisos" style="font-size:11px;margin-top:8px"></p></div>
</div>
<div id="tab-reportes" class="tab-content">
<div class="card"><h3>📈 Productividad por Sucursal</h3><div style="display:flex;gap:8px"><input id="rep_suc_mes" class="input" type="month" style="margin-top:0"><button class="btn btn-warning" onclick="cargarReporteSucursales()" style="width:auto;margin-top:0">📊 Ver</button></div><div id="reporte-suc-result" style="margin-top:12px"></div></div>
<div class="card"><h3>🎯 Bonos y Metas</h3><p style="font-size:11px;color:var(--muted)">Bono automático si 0 retardos y 20+ días</p><div id="bonos-result" style="margin-top:10px"></div></div>
<div class="card" style="border:2px solid #ef4444"><h3>🛡️ Anti-Trampa</h3><div id="antitrampa-result"></div><button class="btn btn-danger" onclick="cargarAntiTrampa()">🔍 Escanear</button></div>
</div>
<div id="tab-vacaciones" class="tab-content"><div class="card"><h3>🏖️ Vacaciones</h3><div id="vac-admin"></div></div><div class="card"><h3>📄 Justificantes</h3><div id="just-admin"></div></div></div>
<div id="tab-chat" class="tab-content"><div class="card"><h3>💬 Chat Admin</h3><div style="display:flex;gap:8px"><input id="chat_para" class="input" placeholder="Para ID" style="margin-top:0"><input id="chat_msg" class="input" placeholder="Mensaje" style="margin-top:0"><button class="btn btn-primary" onclick="enviarChatAdmin()" style="width:auto;margin-top:0">Enviar</button></div><div id="chat-admin-list" style="margin-top:12px;max-height:300px;overflow:auto;background:#0f172a;border-radius:12px;padding:12px"></div></div></div>
<div id="tab-panico" class="tab-content"><div class="card" style="border:2px solid #ef4444"><h3>🆘 Pánico SOS</h3><div id="panico-admin"></div></div></div>
<div id="tab-config" class="tab-content">

<div class="card" style="border:2px solid #6366f1;background:linear-gradient(135deg,#6366f115,#8b5cf615)">
<h3>🎨 Elige tu Estilo de Vista (Solo Admin)</h3>
<p style="font-size:11px;color:var(--muted);margin-top:4px">Tú como admin puedes cambiar entre 6 diseños. El empleado siempre ve el estilo 1 (App Móvil simple).</p>
<p style="font-size:12px;margin-top:10px">Actual: <b id="tema-actual-txt">📱 App Móvil</b></p>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px">
<div id="tema-opt-1" class="tema-option card" onclick="aplicarTema(1)" style="cursor:pointer;text-align:center;padding:16px;margin:0"><div style="font-size:32px">📱</div><b style="font-size:12px">1. App Móvil</b><br><small style="font-size:10px;color:var(--muted)">Celular, tarjetas redondas</small></div>
<div id="tema-opt-2" class="tema-option card" onclick="aplicarTema(2)" style="cursor:pointer;text-align:center;padding:16px;margin:0"><div style="font-size:32px">🖥️</div><b style="font-size:12px">2. Corporativo</b><br><small style="font-size:10px;color:var(--muted)">Notion/Slack, limpio</small></div>
<div id="tema-opt-3" class="tema-option card" onclick="aplicarTema(3)" style="cursor:pointer;text-align:center;padding:16px;margin:0"><div style="font-size:32px">✨</div><b style="font-size:12px">3. Minimalista</b><br><small style="font-size:10px;color:var(--muted)">Apple, blanco y aire</small></div>
<div id="tema-opt-4" class="tema-option card" onclick="aplicarTema(4)" style="cursor:pointer;text-align:center;padding:16px;margin:0;border:2px solid #a855f7"><div style="font-size:32px">🎮</div><b style="font-size:12px">4. Neón Gaming</b><br><small style="font-size:10px;color:var(--muted)">Oscuro con brillos</small></div>
<div id="tema-opt-5" class="tema-option card" onclick="aplicarTema(5)" style="cursor:pointer;text-align:center;padding:16px;margin:0"><div style="font-size:32px">📊</div><b style="font-size:12px">5. Kanban</b><br><small style="font-size:10px;color:var(--muted)">Arrastrable, interactivo</small></div>
<div id="tema-opt-6" class="tema-option card" onclick="aplicarTema(6)" style="cursor:pointer;text-align:center;padding:16px;margin:0"><div style="font-size:32px">🏢</div><b style="font-size:12px">6. Empresa Seria</b><br><small style="font-size:10px;color:var(--muted)">SAP, formal azul</small></div>
</div>
<div style="background:#0f172a;border-radius:12px;padding:12px;margin-top:12px;font-size:11px">
<b>💡 Recomendación:</b><br>
• 📱 Celular → Se ve estilo 1 (menú abajo) automático<br>
• 💻 PC → Se ve estilo lateral + el tema que elijas arriba<br>
• 👷 Empleado → Siempre estilo 1 simple, no puede cambiar<br>
• 👑 Tú como admin → Eliges desde aquí
</div>
</div>

<div class="card" style="border:2px solid #ec4899"><h3>⚙️ Configuración WhatsApp y Bonos</h3><div class="grid2"><input id="conf_tel_admin" class="input" placeholder="Tu WhatsApp admin ej 521..."><input id="conf_bono" class="input" type="number" placeholder="Bono puntualidad $"></div><div class="grid2"><input id="conf_sueldo_default" class="input" type="number" placeholder="Sueldo default $/h"><label style="display:flex;align-items:center;gap:8px;margin-top:10px"><input type="checkbox" id="conf_whatsapp_activo" checked> WhatsApp auto</label></div><button class="btn btn-primary" onclick="guardarConfigAdmin()">💾 Guardar</button><p id="msg-conf-admin" style="font-size:11px;margin-top:8px"></p></div>
<div class="card"><h3>💾 Backup y DB</h3><div class="grid2"><button class="btn btn-dark" onclick="hacerBackup()">💾 Backup JSON</button><button class="btn btn-dark" onclick="cargarAudit()">📋 Ver Auditoría</button></div><div id="backup-result" style="display:none;margin-top:12px;background:#0f172a;border-radius:12px;padding:12px;font-size:11px"></div><div id="audit-result" style="display:none;margin-top:12px;background:#0f172a;border-radius:12px;padding:12px;max-height:200px;overflow:auto;font-size:11px"></div></div>
</div>
<div id="tab-audit" class="tab-content"><div class="card"><h3>📋 Auditoría Completa</h3><button class="btn btn-dark" onclick="cargarAudit()">🔄 Cargar Auditoría</button><div id="audit-result2" style="margin-top:12px"></div></div></div>
</div>

<!-- EMPLEADO TABS -->
<div id="empleado-area" style="display:none">
<div id="tab-emp-jornada" class="tab-content active">
<div class="card" style="border:2px solid #10b981"><h3>⏰ Mi Jornada - <span id="user-display" style="font-size:12px;color:var(--muted)"></span></h3><div id="estado-jornada" style="margin-top:12px"></div><button id="btn-check" class="btn btn-primary" onclick="registrar()" style="padding:18px;font-size:16px">📍 Cargando...</button><p id="msg-check" style="font-size:12px;margin-top:8px;text-align:center"></p><div style="margin-top:12px;display:flex;gap:8px;justify-content:center"><span id="gps-status" class="gps-off">GPS: Off</span><span id="dist-suc" style="font-size:11px;color:var(--muted)"></span></div></div>
<div class="card"><h3>⏱️ Mis Retardos y Horas</h3><div id="mis-retardos"></div><div style="margin-top:10px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px"><div style="background:#ef444415;border:1px solid #ef4444;border-radius:12px;padding:10px;text-align:center"><div style="font-size:18px;font-weight:800;color:#ef4444" id="total-retardo-entrada">0 min</div><small>Entrada</small></div><div style="background:#f59e0b15;border:1px solid #f59e0b;border-radius:12px;padding:10px;text-align:center"><div style="font-size:18px;font-weight:800;color:#f59e0b" id="total-retardo-comida">0 min</div><small>Comida</small></div><div style="background:#10b98115;border:1px solid #10b981;border-radius:12px;padding:10px;text-align:center"><div style="font-size:18px;font-weight:800;color:#10b981" id="total-horas-mes">0h</div><small>Horas Mes</small></div></div></div>
</div>
<div id="tab-emp-calendario" class="tab-content"><div class="card" style="border:2px solid #6366f1"><h3>🗓️ Mi Calendario</h3><div style="display:flex;gap:8px"><input id="emp_cal_mes" class="input" type="month" style="margin-top:0"><button class="btn btn-primary" onclick="cargarMiCalendario()" style="width:auto;margin-top:0">Ver</button></div><div id="emp-calendario-result" style="margin-top:12px;display:grid;grid-template-columns:repeat(7,1fr);gap:6px"></div><div style="display:flex;gap:12px;margin-top:10px;font-size:10px;flex-wrap:wrap"><span style="color:#10b981">● Presente</span><span style="color:#f59e0b">● Retardo</span><span style="color:#ef4444">● Ausente</span><span style="color:#8b5cf6">● Vacaciones</span></div></div></div>
<div id="tab-emp-ranking" class="tab-content"><div class="card" style="border:2px solid #f59e0b"><h3>🏆 Ranking y Bono</h3><div id="emp-ranking-info" style="margin-top:10px"></div></div></div>
<div id="tab-emp-historial" class="tab-content"><div class="card"><h3>📊 Mi Historial</h3><canvas id="chart-horas-emp"></canvas><div id="emp-historial-lista" style="margin-top:12px;max-height:300px;overflow:auto"></div></div></div>
<div id="tab-emp-vacaciones" class="tab-content"><div class="card" style="border:2px solid #6366f1"><h3>🏖️ Vacaciones y Justificantes</h3><div class="grid2"><div><b style="font-size:12px">Vacaciones</b><select id="vac_tipo" class="input"><option value="vacaciones">Vacaciones</option><option value="permiso">Permiso</option><option value="permiso_sin_goce">Sin goce</option><option value="incapacidad">Incapacidad</option></select><div class="grid2"><input id="vac_inicio" class="input" type="date"><input id="vac_fin" class="input" type="date"></div><textarea id="vac_motivo" class="input" placeholder="Motivo..." rows="2"></textarea><button class="btn btn-primary" onclick="solicitarVacaciones()">📅 Solicitar</button></div><div><b style="font-size:12px">Justificante</b><input id="just_fecha" class="input" type="date"><select id="just_tipo" class="input"><option value="enfermedad">Enfermedad</option><option value="medico">Médica</option><option value="familiar">Familiar</option></select><input id="just_foto" class="input" type="file" accept="image/*"><textarea id="just_motivo" class="input" placeholder="Motivo..." rows="2"></textarea><button class="btn btn-warning" onclick="subirJustificante()">📄 Subir</button></div></div><div class="grid2" style="margin-top:12px"><div id="mis-vacaciones" style="max-height:150px;overflow:auto"></div><div id="mis-justificantes" style="max-height:150px;overflow:auto"></div></div></div></div>
<div id="tab-emp-perfil" class="tab-content">
<div class="card" style="border:2px solid #8b5cf6"><h3>👤 Mi Perfil + Foto - Yo puedo editar y guardar</h3>
<div style="display:flex;gap:12px;align-items:center"><img id="emp_foto_preview" src="" style="width:80px;height:80px;border-radius:50%;background:#334155;object-fit:cover;display:none"><div><input type="file" id="emp_foto_input" accept="image/*" class="input" style="font-size:11px"><button class="btn btn-primary" onclick="subirFotoPerfil()" style="width:auto;padding:6px 12px;font-size:11px;margin-top:6px">📸 Subir Foto</button></div></div>

<div id="emp-perfil-info" style="margin-top:12px;font-size:12px;background:#0f172a;border-radius:12px;padding:12px"></div>

<div style="margin-top:14px"><b style="font-size:11px;color:#ec4899">✏️ EDITAR MI INFORMACIÓN (Yo la lleno, Admin la ve)</b></div>
<div style="display:flex;gap:8px"><input id="my_ap_paterno" class="input" placeholder="Apellido Paterno"><input id="my_ap_materno" class="input" placeholder="Apellido Materno"></div>
<div style="display:flex;gap:8px"><input id="my_curp" class="input" placeholder="CURP"><input id="my_rfc" class="input" placeholder="RFC"></div>
<div style="display:flex;gap:8px"><input id="my_nss" class="input" placeholder="NSS"><input id="my_fecha_nac" class="input" type="date"></div>
<div style="display:flex;gap:8px"><select id="my_genero" class="input"><option value="">Género</option><option value="M">Masculino</option><option value="F">Femenino</option></select><select id="my_civil" class="input"><option value="">Estado Civil</option><option value="Soltero">Soltero</option><option value="Casado">Casado</option><option value="Union">Unión Libre</option></select></div>
<input id="my_direccion" class="input" placeholder="Dirección completa">
<input id="my_email_personal" class="input" placeholder="Email personal">
<div style="display:flex;gap:8px"><input id="my_tel_emergencia" class="input" placeholder="Tel Emergencia"><input id="my_contacto_emergencia" class="input" placeholder="Nombre contacto emergencia"></div>
<div style="display:flex;gap:8px"><input id="my_banco" class="input" placeholder="Banco"><input id="my_cuenta" class="input" placeholder="Cuenta"><input id="my_clabe" class="input" placeholder="CLABE"></div>
<div style="display:flex;gap:8px"><input id="my_sangre" class="input" placeholder="Tipo Sangre Ej O+"><input id="my_telefono" class="input" placeholder="Mi WhatsApp"></div>
<button class="btn btn-success" onclick="guardarMiPerfil()" style="margin-top:10px">💾 Guardar Mi Información</button>
<p id="msg-my-perfil" style="font-size:11px;margin-top:6px;color:#10b981"></p>
</div>

<div class="card"><h3>🔑 Seguridad</h3><input id="old_pass" class="input" type="password" placeholder="Actual"><input id="new_pass" class="input" type="password" placeholder="Nueva"><button class="btn btn-primary" onclick="cambiarPassword()">🔑 Cambiar Contraseña</button><p id="msg-pass" style="font-size:11px;margin-top:8px"></p></div>
</div>
<div id="tab-emp-notif" class="tab-content"><div class="card"><h3>🔔 Notificaciones</h3><div id="emp-notificaciones" style="margin-top:10px"></div><div id="mis-notifs" style="margin-top:12px"></div><div id="mi-historial"></div></div></div>
</div>

</div>
</div>

<!-- BOTTOM NAV MOBILE -->
<div class="bottom-nav" id="bottom-nav-admin">
<div class="bottom-nav-item active" onclick="switchTab('tab-dashboard')"><div class="icon">📊</div>Dashboard</div>
<div class="bottom-nav-item" onclick="switchTab('tab-empleados')"><div class="icon">👥</div>Empleados</div>
<div class="bottom-nav-item" onclick="switchTab('tab-sucursales')"><div class="icon">🏢</div>Sucursales</div>
<div class="bottom-nav-item" onclick="switchTab('tab-nomina')"><div class="icon">💰</div>Nómina</div>
<div class="bottom-nav-item" onclick="switchTab('tab-config')"><div class="icon">⚙️</div>Config</div>
</div>
<div class="bottom-nav" id="bottom-nav-emp" style="display:none">
<div class="bottom-nav-item active" onclick="switchTabEmp('tab-emp-jornada')"><div class="icon">⏰</div>Jornada</div>
<div class="bottom-nav-item" onclick="switchTabEmp('tab-emp-calendario')"><div class="icon">🗓️</div>Calendario</div>
<div class="bottom-nav-item" onclick="switchTabEmp('tab-emp-ranking')"><div class="icon">🏆</div>Bono</div>
<div class="bottom-nav-item" onclick="switchTabEmp('tab-emp-vacaciones')"><div class="icon">🏖️</div>Vacaciones</div>
<div class="bottom-nav-item" onclick="switchTabEmp('tab-emp-perfil')"><div class="icon">👤</div>Perfil</div>
</div>

<div id="modal-edit" class="modal"><div class="modal-content"><h3>✏️ Editar Empleado</h3><input id="edit_id" class="input" readonly><input id="edit_nombre" class="input" placeholder="Nombre"><input id="edit_puesto" class="input" placeholder="Puesto"><input id="edit_password" class="input" placeholder="Nueva contraseña"><input id="edit_telefono" class="input" placeholder="Tel"><div style="display:flex;gap:8px;align-items:center;margin-top:8px"><label style="font-size:12px;min-width:60px">Comida:</label><input id="edit_comida" class="input" type="number" style="margin-top:0"></div><div style="display:flex;gap:8px;margin-top:8px"><label style="font-size:12px">Activo:</label><select id="edit_activo" class="input" style="margin-top:0"><option value="true">Activo</option><option value="false">Desactivado</option></select></div><button class="btn btn-success" onclick="guardarEdicion()">💾 Guardar</button><button class="btn btn-dark" onclick="cerrarModal()">Cancelar</button><button class="btn btn-danger" onclick="eliminarEmpleado()">🗑️ Papelera</button></div></div>
<div id="modal-edit-suc" class="modal"><div class="modal-content"><h3>✏️ Editar Sucursal</h3><input id="edit_suc_id" class="input" readonly><input id="edit_suc_nombre" class="input" placeholder="Nombre"><input id="edit_suc_dir" class="input" placeholder="Dirección"><div class="grid2"><input id="edit_suc_he" class="input" type="time"><input id="edit_suc_hs" class="input" type="time"></div><div class="grid2"><input id="edit_suc_lat" class="input" placeholder="Lat"><input id="edit_suc_lng" class="input" placeholder="Lng"></div><div style="display:flex;gap:8px;align-items:center;margin-top:8px"><label style="font-size:12px">Radio:</label><input id="edit_suc_radio" class="input" type="number" style="margin-top:0"><span>m</span></div><button class="btn btn-success" onclick="guardarEdicionSuc()">💾 Guardar</button><button class="btn btn-dark" onclick="document.getElementById('modal-edit-suc').style.display='none'">Cancelar</button><button class="btn btn-danger" onclick="eliminarSucursal()">🗑️ Eliminar</button></div></div>
<div id="modal-recuperar" class="modal"><div class="modal-content"><h3>🔑 Recuperar Contraseña</h3><input id="rec_id" class="input" placeholder="ID Empleado"><button class="btn btn-primary" onclick="recuperarPass()">Recuperar</button><p id="rec-msg" style="font-size:11px;margin-top:8px"></p><button class="btn btn-dark" onclick="document.getElementById('modal-recuperar').style.display='none'">Cerrar</button></div></div>

<script>
let USER_ID=''; let EDITANDO_ID=''; let EDITANDO_SUC_ID=''; let watchId=null; let gpsActivo=false; let miPos={lat:null,lng:null}; let chartRet=null; let chartHoras=null; let ROL='';
const PREG=[{id:1,txt:"¿Limpieza de botarga? (1-10)",tipo:"cal"},{id:2,txt:"¿Limpieza de ropa? (1-10)",tipo:"cal"},{id:3,txt:"¿Limpieza de guantes? (1-10)",tipo:"cal"},{id:4,txt:"¿Limpieza de zapatos? (1-10)",tipo:"cal"},{id:5,txt:"¿Baile? (1-10)",tipo:"cal"},{id:6,txt:"¿Comentario de baile? (texto)",tipo:"texto"},{id:7,txt:"¿Actitud? (1-10)",tipo:"cal"},{id:8,txt:"¿Cumple con políticas? (1-10)",tipo:"cal"},{id:9,txt:"¿Ambiente positivo? (1-10)",tipo:"cal"},{id:10,txt:"¿Disponibilidad? (1-10)",tipo:"cal"},{id:11,txt:"¿Cumple horarios? (1-10)",tipo:"cal"},{id:12,txt:"¿Área por mejorar? (texto)",tipo:"texto"},];
async function api(p,m='GET',b=null){const o={method:m,headers:{'Content-Type':'application/json'}}; if(b)o.body=JSON.stringify(b); const r=await fetch(p,o); if(!r.ok){const e=await r.json(); throw e;} return r.json();}

// === NAVEGACION RESPONSIVE: 1 para celular (bottom), 2 para PC (sidebar) ===
function switchTab(tabId){
  document.querySelectorAll('#admin-area .tab-content').forEach(t=>t.classList.remove('active'));
  document.getElementById(tabId)?.classList.add('active');
  document.querySelectorAll('#bottom-nav-admin .bottom-nav-item').forEach(b=>b.classList.remove('active'));
  document.querySelectorAll('#sidebar-admin .sidebar-item').forEach(s=>s.classList.remove('active'));
  // activar correspondiente
  const mapIcon={'tab-dashboard':0,'tab-empleados':1,'tab-sucursales':2,'tab-nomina':3,'tab-config':4};
  if(mapIcon[tabId]!==undefined) document.querySelectorAll('#bottom-nav-admin .bottom-nav-item')[mapIcon[tabId]]?.classList.add('active');
  // sidebar
  document.querySelectorAll('#sidebar-admin .sidebar-item').forEach(el=>{
    if(el.getAttribute('onclick')?.includes(tabId)) el.classList.add('active');
  });
  const titles={'tab-dashboard':'📊 Dashboard','tab-empleados':'👥 Empleados','tab-sucursales':'🏢 Sucursales','tab-retardos':'⏱️ Retardos','tab-gps':'🗺️ GPS & Ruta','tab-evaluaciones':'⭐ Evaluaciones','tab-nomina':'💰 Nómina','tab-reportes':'📈 Reportes','tab-vacaciones':'🏖️ Vacaciones','tab-chat':'💬 Chat','tab-panico':'🆘 Pánico','tab-config':'⚙️ Configuración','tab-audit':'📋 Auditoría'};
  document.getElementById('topbar-title').innerText=titles[tabId]||'Clock RD';
  window.scrollTo(0,0);
}
function switchTabEmp(tabId){
  document.querySelectorAll('#empleado-area .tab-content').forEach(t=>t.classList.remove('active'));
  document.getElementById(tabId)?.classList.add('active');
  document.querySelectorAll('#bottom-nav-emp .bottom-nav-item').forEach(b=>b.classList.remove('active'));
  document.querySelectorAll('#sidebar-emp .sidebar-item').forEach(s=>s.classList.remove('active'));
  const map={'tab-emp-jornada':0,'tab-emp-calendario':1,'tab-emp-ranking':2,'tab-emp-vacaciones':3,'tab-emp-perfil':4};
  if(map[tabId]!==undefined) document.querySelectorAll('#bottom-nav-emp .bottom-nav-item')[map[tabId]]?.classList.add('active');
  document.querySelectorAll('#sidebar-emp .sidebar-item').forEach(el=>{
    if(el.getAttribute('onclick')?.includes(tabId)) el.classList.add('active');
  });
  const titles={'tab-emp-jornada':'⏰ Mi Jornada','tab-emp-calendario':'🗓️ Calendario','tab-emp-ranking':'🏆 Ranking & Bono','tab-emp-historial':'📊 Historial','tab-emp-vacaciones':'🏖️ Vacaciones','tab-emp-perfil':'👤 Perfil','tab-emp-notif':'🔔 Notificaciones'};
  document.getElementById('topbar-title').innerText=titles[tabId]||'Empleado';
  window.scrollTo(0,0);
}

async function login(){
  const u=document.getElementById('u').value; const p=document.getElementById('p').value;
  try{
    const d=await api('/api/login','POST',{usuario:u,password:p});
    document.getElementById('login').style.display='none';
    document.getElementById('app').style.display='block';
    USER_ID=d.usuario||u; ROL=d.subrol||d.rol; const nombre=d.nombre||u; const empresaNom=d.empresa||'';
    localStorage.setItem('sesion_activa','true'); if(data.empresa_id) localStorage.setItem('empresa_id', data.empresa_id);; localStorage.setItem('user_id',USER_ID); localStorage.setItem('rol',ROL); localStorage.setItem('nombre',nombre); localStorage.setItem('empresa_nombre',empresaNom);
    document.getElementById('banner-nombre').innerText=`👋 Hola, ${nombre}`;
    document.getElementById('banner-nombre2').innerText=`👋 Hola, ${nombre} | ${ROL.toUpperCase()} ${empresaNom? ' - '+empresaNom : ''}`;
    document.getElementById('user-display').innerText=nombre+' ('+ROL+')';
    if(d.rol==='admin' || ROL!=='empleado'){
      document.getElementById('admin-area').style.display='block';
      document.getElementById('empleado-area').style.display='none';
      document.getElementById('sidebar-admin').style.display='block';
      document.getElementById('sidebar-emp').style.display='none';
      document.getElementById('bottom-nav-admin').style.display='flex';
      document.getElementById('bottom-nav-emp').style.display='none';
      cargarTodo();
    }else{
      document.getElementById('admin-area').style.display='none';
      document.getElementById('empleado-area').style.display='block';
      document.getElementById('sidebar-admin').style.display='none';
      document.getElementById('sidebar-emp').style.display='block';
      document.getElementById('bottom-nav-admin').style.display='none';
      document.getElementById('bottom-nav-emp').style.display='flex';
      cargarEmpleadoPro();
    }
  }catch(e){ document.getElementById('msg').innerText=e.detail||'Error'; }
}
function mostrarRecuperar(){document.getElementById('modal-recuperar').style.display='flex';}
async function recuperarPass(){const id=document.getElementById('rec_id').value; if(!id) return alert('ID'); try{const r=await api('/api/recuperar-password','POST',{empleado_id:id}); document.getElementById('rec-msg').innerHTML=`✅ Nueva: <b style="color:#10b981;font-size:18px">${r.nueva_password}</b><br>${r.mensaje}`;}catch(e){document.getElementById('rec-msg').innerText='❌ '+(e.detail||'Error');}}
function mostrarRegistro(){document.getElementById('login').style.display='none'; document.getElementById('registro-empresa-modal').style.display='flex';}
function mostrarLogin(){document.getElementById('registro-empresa-modal').style.display='none'; document.getElementById('login').style.display='block';}
async function enviarCodigoEmail(){const email=document.getElementById('reg_correo').value; if(!email) return alert('Correo'); try{const r=await api('/api/enviar-codigo-email','POST',{email:email}); document.getElementById('correo-verif-area').style.display='block'; document.getElementById('msg-email').innerText=r.mensaje+' Código: '+r.codigo+' (demo)';}catch(e){document.getElementById('msg-email').innerText='❌ '+(e.detail||'Error');}}
async function verificarEmail(){const email=document.getElementById('reg_correo').value; const codigo=document.getElementById('reg_codigo_email').value; try{await api('/api/verificar-codigo','POST',{clave:email,codigo:codigo}); document.getElementById('email-ok').style.display='block'; document.getElementById('correo-verif-area').style.display='none';}catch(e){document.getElementById('msg-email').innerText='❌ '+(e.detail||'Error');}}
async function enviarCodigoWhatsApp(){const tel=document.getElementById('reg_telefono').value; if(!tel) return alert('Telefono'); try{const r=await api('/api/enviar-codigo-whatsapp','POST',{telefono:tel}); document.getElementById('whats-verif-area').style.display='block'; document.getElementById('msg-whats').innerText=r.mensaje+' Código: '+r.codigo+' (demo)';}catch(e){document.getElementById('msg-whats').innerText='❌ '+(e.detail||'Error');}}
async function verificarWhatsApp(){const tel=document.getElementById('reg_telefono').value; const codigo=document.getElementById('reg_codigo_whats').value; try{await api('/api/verificar-codigo','POST',{clave:tel,codigo:codigo}); document.getElementById('whats-ok').style.display='block'; document.getElementById('whats-verif-area').style.display='none';}catch(e){document.getElementById('msg-whats').innerText='❌ '+(e.detail||'Error');}}
async function registrarEmpresa(){const data={nombre:document.getElementById('reg_nombre').value,usuario:document.getElementById('reg_usuario').value,empresa:document.getElementById('reg_empresa').value,direccion:document.getElementById('reg_direccion').value,correo:document.getElementById('reg_correo').value,telefono:document.getElementById('reg_telefono').value,password:document.getElementById('reg_password').value,confirm_password:document.getElementById('reg_confirm').value}; try{const r=await api('/api/registro-empresa','POST',data); document.getElementById('msg-registro').innerText='✅ '+r.mensaje; setTimeout(()=>{mostrarLogin();},1500);}catch(e){document.getElementById('msg-registro').innerText='❌ '+(e.detail||'Error');}}
async function generarID(){const d=await api('/empleados/next-id'); document.getElementById('emp_id').value=d.next_id; document.getElementById('next-id').innerText=d.next_id;}
function obtenerGPS(){if(!navigator.geolocation) return alert('GPS no soportado'); navigator.geolocation.getCurrentPosition(pos=>{document.getElementById('suc_lat').value=pos.coords.latitude; document.getElementById('suc_lng').value=pos.coords.longitude; alert('📍 GPS: '+pos.coords.latitude+', '+pos.coords.longitude);}, err=>alert('Error GPS: '+err.message), {enableHighAccuracy:true});}
async function crearSuc(){const id=document.getElementById('suc_id').value; const nombre=document.getElementById('suc_nombre').value; const dir=document.getElementById('suc_dir').value; const he=document.getElementById('suc_he').value; const hs=document.getElementById('suc_hs').value; const lat=parseFloat(document.getElementById('suc_lat').value); const lng=parseFloat(document.getElementById('suc_lng').value); const radio=parseInt(document.getElementById('suc_radio').value)||200; if(!id||!nombre) return alert('ID y nombre'); await api('/sucursales','POST',{id,nombre,direccion:dir,hora_entrada:he,hora_salida:hs,lat:lat||null,lng:lng||null,radio:radio}); document.getElementById('suc_id').value=''; document.getElementById('suc_nombre').value=''; cargarSucs();}
async function cargarSucs(){const sucs=await api('/sucursales'); document.getElementById('list-suc').innerHTML=sucs.map(s=>`<div style="background:#0f172a;padding:12px;border-radius:12px;margin-top:8px;font-size:11px;display:flex;justify-content:space-between;align-items:center"><div><b>${s.id} ${s.nombre}</b> ${s.lat?`📍 ${s.lat.toFixed(4)},${s.lng.toFixed(4)} - ${s.radio}m`: '⚠️ Sin GPS'}<br><small>${s.direccion||''} - ${s.hora_entrada||''} a ${s.hora_salida||''}</small></div><button onclick="abrirEditarSuc('${s.id}')" style="padding:6px 10px;border-radius:8px;border:none;background:#6366f1;color:white;font-size:11px">✏️ Editar</button></div>`).join('') || 'Sin'; document.getElementById('check-suc').innerHTML=sucs.map(s=>`<label style="display:flex;gap:6px;margin-top:6px"><input type="checkbox" value="${s.id}" class="chk"> ${s.nombre}</label>`).join(''); ['lunes','martes','miercoles','jueves','viernes','sabado','domingo'].forEach(d=>{const sel=document.getElementById('d-'+d); if(sel) sel.innerHTML='<option value="">Libre</option>'+sucs.map(s=>`<option value="${s.id}">${s.nombre}</option>`).join('');});}
function abrirEditarSuc(id){api('/sucursales').then(sucs=>{const s=sucs.find(x=>x.id===id); if(!s) return; EDITANDO_SUC_ID=id; document.getElementById('edit_suc_id').value=s.id; document.getElementById('edit_suc_nombre').value=s.nombre||''; document.getElementById('edit_suc_dir').value=s.direccion||''; document.getElementById('edit_suc_he').value=s.hora_entrada||'08:00'; document.getElementById('edit_suc_hs').value=s.hora_salida||'18:00'; document.getElementById('edit_suc_lat').value=s.lat||''; document.getElementById('edit_suc_lng').value=s.lng||''; document.getElementById('edit_suc_radio').value=s.radio||200; document.getElementById('modal-edit-suc').style.display='flex';});}
async function guardarEdicionSuc(){const data={nombre:document.getElementById('edit_suc_nombre').value,direccion:document.getElementById('edit_suc_dir').value,hora_entrada:document.getElementById('edit_suc_he').value,hora_salida:document.getElementById('edit_suc_hs').value,lat:parseFloat(document.getElementById('edit_suc_lat').value)||null,lng:parseFloat(document.getElementById('edit_suc_lng').value)||null,radio:parseInt(document.getElementById('edit_suc_radio').value)||200}; await api('/sucursales/'+EDITANDO_SUC_ID,'PUT',data); alert('✅ Sucursal actualizada'); document.getElementById('modal-edit-suc').style.display='none'; cargarSucs();}
async function eliminarSucursal(){if(!confirm('¿Eliminar sucursal '+EDITANDO_SUC_ID+'?')) return; await fetch('/sucursales/'+EDITANDO_SUC_ID,{method:'DELETE'}); document.getElementById('modal-edit-suc').style.display='none'; cargarSucs();}
async function crearEmp(){
  const empresa_id = localStorage.getItem('empresa_id') || document.getElementById('emp_empresa_badge')?.innerText || null;
  const data={
    id: document.getElementById('emp_id').value,
    empresa_id: empresa_id,
    nombre: document.getElementById('emp_nombre').value,
    apellido_paterno: document.getElementById('emp_ap_paterno').value,
    apellido_materno: document.getElementById('emp_ap_materno').value,
    puesto: document.getElementById('emp_puesto').value,
    departamento: document.getElementById('emp_depto').value,
    rol: document.getElementById('emp_rol').value,
    curp: document.getElementById('emp_curp').value.toUpperCase(),
    rfc: document.getElementById('emp_rfc').value.toUpperCase(),
    nss: document.getElementById('emp_nss').value,
    fecha_nacimiento: document.getElementById('emp_fecha_nac').value,
    genero: document.getElementById('emp_genero').value,
    estado_civil: document.getElementById('emp_civil').value,
    tipo_sangre: document.getElementById('emp_sangre').value,
    direccion_completa: document.getElementById('emp_direccion').value,
    email_personal: document.getElementById('emp_email_personal').value,
    telefono: document.getElementById('emp_telefono').value,
    telefono_emergencia: document.getElementById('emp_tel_emergencia').value,
    contacto_emergencia_nombre: document.getElementById('emp_contacto_emergencia').value,
    fecha_ingreso: document.getElementById('emp_fecha_ingreso').value,
    tipo_contrato: document.getElementById('emp_tipo_contrato').value,
    turno: document.getElementById('emp_turno').value,
    dias_descanso: document.getElementById('emp_descansos').value.split(',').map(s=>s.trim()).filter(Boolean),
    sueldo_hora: document.getElementById('emp_sueldo').value,
    sueldo_mensual: document.getElementById('emp_sueldo_mensual').value,
    banco: document.getElementById('emp_banco').value,
    cuenta: document.getElementById('emp_cuenta').value,
    clabe: document.getElementById('emp_clabe').value,
    password: document.getElementById('emp_pass').value,
    tiempo_comida: document.getElementById('emp_comida').value,
    sucursales_ids: [...document.querySelectorAll('#check-suc input:checked')].map(c=>c.value),
    horario: {lunes: document.getElementById('d-lunes').value, martes: document.getElementById('d-martes').value, miercoles: document.getElementById('d-miercoles').value, jueves: document.getElementById('d-jueves').value, viernes: document.getElementById('d-viernes').value, sabado: document.getElementById('d-sabado').value, domingo: document.getElementById('d-domingo').value},
    documentos: {ine: document.getElementById('doc_ine').checked, comprobante_domicilio: document.getElementById('doc_domicilio').checked, curp_doc: document.getElementById('doc_curp').checked, contrato_firmado: document.getElementById('doc_contrato').checked}
  };
  if(!data.nombre) return alert('Nombre obligatorio');
  if(!data.telefono) return alert('WhatsApp obligatorio');
  if(!data.apellido_paterno) return alert('Apellido paterno obligatorio');
  const res = await api('/empleados','POST',data, {'X-Empresa-ID': localStorage.getItem('empresa_id')||''});
  alert('✅ Empleado '+res.id+' guardado en Neon con empresa '+res.empresa_id);
  cargarEmpleados();
}
);
function logout(){ if(confirm('¿Cerrar sesión?')){ localStorage.clear(); location.reload(); } }

async function guardarMiPerfil(){
  const data={
    apellido_paterno: document.getElementById('my_ap_paterno').value,
    apellido_materno: document.getElementById('my_ap_materno').value,
    curp: document.getElementById('my_curp').value.toUpperCase(),
    rfc: document.getElementById('my_rfc').value.toUpperCase(),
    nss: document.getElementById('my_nss').value,
    fecha_nacimiento: document.getElementById('my_fecha_nac').value,
    genero: document.getElementById('my_genero').value,
    estado_civil: document.getElementById('my_civil').value,
    direccion_completa: document.getElementById('my_direccion').value,
    email_personal: document.getElementById('my_email_personal').value,
    telefono_emergencia: document.getElementById('my_tel_emergencia').value,
    contacto_emergencia_nombre: document.getElementById('my_contacto_emergencia').value,
    banco: document.getElementById('my_banco').value,
    cuenta: document.getElementById('my_cuenta').value,
    clabe: document.getElementById('my_clabe').value,
    tipo_sangre: document.getElementById('my_sangre').value,
    telefono: document.getElementById('my_telefono').value
  };
  try{
    await api('/empleados/'+USER_ID,'PUT',data);
    document.getElementById('msg-my-perfil').innerText='✅ Información guardada, el Admin ya la puede ver';
    cargarEmpleadoPro();
  }catch(e){ alert('Error guardando'); }
}

async function cargarEmpleadoPro(){
  try{
    const emp = await api('/empleados');
    const yo = emp.find(x=>x.id===USER_ID) || await api('/api/empleado/'+USER_ID+'/perfil').then(r=>r.empleado).catch(()=>null);
    if(!yo) return;
    // Llenar vista
    const info = document.getElementById('emp-perfil-info');
    if(info){
      info.innerHTML = `
        <b>${yo.nombre} ${yo.apellido_paterno||''} ${yo.apellido_materno||''}</b><br>
        Puesto: ${yo.puesto||''} - Depto: ${yo.departamento||''}<br>
        Empresa ID: ${yo.empresa_id||''}<br>
        CURP: ${yo.curp||'❌ falta'} | RFC: ${yo.rfc||'❌ falta'} | NSS: ${yo.nss||'❌ falta'}<br>
        Tel: ${yo.telefono||''} | Emergencia: ${yo.telefono_emergencia||''} (${yo.contacto_emergencia_nombre||''})<br>
        Banco: ${yo.banco||''} - ${yo.cuenta||''}
      `;
    }
    // Llenar inputs editables
    const setVal=(id,val)=>{ const el=document.getElementById(id); if(el) el.value=val||''; };
    setVal('my_ap_paterno', yo.apellido_paterno);
    setVal('my_ap_materno', yo.apellido_materno);
    setVal('my_curp', yo.curp);
    setVal('my_rfc', yo.rfc);
    setVal('my_nss', yo.nss);
    setVal('my_fecha_nac', yo.fecha_nacimiento);
    setVal('my_genero', yo.genero);
    setVal('my_civil', yo.estado_civil);
    setVal('my_direccion', yo.direccion_completa);
    setVal('my_email_personal', yo.email_personal);
    setVal('my_tel_emergencia', yo.telefono_emergencia);
    setVal('my_contacto_emergencia', yo.contacto_emergencia_nombre);
    setVal('my_banco', yo.banco);
    setVal('my_cuenta', yo.cuenta);
    setVal('my_clabe', yo.clabe);
    setVal('my_sangre', yo.tipo_sangre);
    setVal('my_telefono', yo.telefono);
    // foto
    if(yo.foto){ const img=document.getElementById('emp_foto_preview'); if(img){ img.src=yo.foto; img.style.display='block'; } }
  }catch(e){ console.log('cargarEmpleadoPro error',e); }
}

// Mejorar lista admin para ver todo

// Funciones turnos semanales
function getWeekString(date){
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNum = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(),0,1));
  const weekNo = Math.ceil(( ( (d - yearStart) / 86400000) + 1)/7);
  return `${d.getUTCFullYear()}-W${String(weekNo).padStart(2,'0')}`;
}

async function cargarTurnoSemana(){
  const empId = document.getElementById('emp_id').value || EDITANDO_ID;
  if(!empId) return alert('Selecciona o guarda primero al empleado');
  const semana = document.getElementById('turno_semana').value;
  if(!semana) return alert('Selecciona semana');
  try{
    const turnos = await api('/api/empleado/'+empId+'/turnos-semanales');
    const horario = turnos[semana];
    if(horario){
      document.getElementById('sem_lunes').value = horario.lunes||'';
      document.getElementById('sem_martes').value = horario.martes||'';
      document.getElementById('sem_miercoles').value = horario.miercoles||'';
      document.getElementById('sem_jueves').value = horario.jueves||'';
      document.getElementById('sem_viernes').value = horario.viernes||'';
      document.getElementById('sem_sabado').value = horario.sabado||'';
      document.getElementById('sem_domingo').value = horario.domingo||'';
      alert('✅ Horario de '+semana+' cargado');
    } else {
      alert('No hay horario para '+semana+' - crea uno nuevo');
    }
    mostrarListaTurnosSemanales(turnos);
  }catch(e){ console.log(e); }
}

async function guardarTurnoSemanal(){
  const empId = document.getElementById('emp_id').value || EDITANDO_ID;
  if(!empId) return alert('Primero guarda el empleado o selecciona uno para editar');
  const semana = document.getElementById('turno_semana').value;
  if(!semana) return alert('Selecciona la semana (ej: 2026-W32)');
  const horario = {
    lunes: document.getElementById('sem_lunes').value,
    martes: document.getElementById('sem_martes').value,
    miercoles: document.getElementById('sem_miercoles').value,
    jueves: document.getElementById('sem_jueves').value,
    viernes: document.getElementById('sem_viernes').value,
    sabado: document.getElementById('sem_sabado').value,
    domingo: document.getElementById('sem_domingo').value
  };
  try{
    await api('/api/empleado/'+empId+'/turnos-semanales','POST',{semana: semana, horario: horario});
    alert('✅ Turno de '+semana+' guardado para '+empId);
    const turnos = await api('/api/empleado/'+empId+'/turnos-semanales');
    mostrarListaTurnosSemanales(turnos);
  }catch(e){ alert('Error guardando turno'); }
}

function mostrarListaTurnosSemanales(turnos){
  const div = document.getElementById('turnos-semanales-lista');
  if(!div) return;
  if(!turnos || Object.keys(turnos).length===0){ div.innerHTML='Sin turnos semanales aún'; return; }
  div.innerHTML = Object.keys(turnos).sort().reverse().map(sem=>`
    <div style="display:flex;justify-content:space-between;align-items:center;padding:6px;background:#1e293b;border-radius:6px;margin-top:4px">
      <div><b>${sem}</b><br><span style="font-size:10px">${Object.values(turnos[sem]).filter(Boolean).length} días asignados</span></div>
      <button onclick="eliminarTurnoSemanal('${sem}')" style="padding:4px 8px;border-radius:6px;border:none;background:#ef4444;color:white;font-size:10px">🗑️</button>
    </div>
  `).join('');
}

async function eliminarTurnoSemanal(semana){
  const empId = document.getElementById('emp_id').value || EDITANDO_ID;
  if(!confirm('¿Borrar turno de '+semana+'?')) return;
  await api('/api/empleado/'+empId+'/turnos-semanales/'+semana,'DELETE');
  const turnos = await api('/api/empleado/'+empId+'/turnos-semanales');
  mostrarListaTurnosSemanales(turnos);
}

// Cuando editas empleado, cargar sus turnos
const editarEmpOriginal = window.editarEmp;
const editarEmpConTurnos = async function(id){
  await editarEmpOriginal(id);
  // cargar semanas
  try{
    const turnos = await api('/api/empleado/'+id+'/turnos-semanales');
    mostrarListaTurnosSemanales(turnos);
    // poner semana actual por defecto
    const hoy = new Date();
    document.getElementById('turno_semana').value = getWeekString(hoy).replace('-W','-W'); // input week espera YYYY-Www
    // Truco: input type=week quiere YYYY-Www
    const year = hoy.getFullYear();
    const week = getWeekString(hoy).split('-W')[1];
    document.getElementById('turno_semana').value = `${year}-W${week}`;
  }catch(e){}
};
window.editarEmp = editarEmpConTurnos;

// Llenar selects semanales igual que los normales cuando se cargan sucursales
function llenarSelectsSemanales(){
  const sucursales = window.sucursalesCache || [];
  const ids = ['sem_lunes','sem_martes','sem_miercoles','sem_jueves','sem_viernes','sem_sabado','sem_domingo'];
  ids.forEach(id=>{
    const sel = document.getElementById(id);
    if(!sel) return;
    const val = sel.value;
    sel.innerHTML = '<option value="">Sin asignar / Descanso</option>' + sucursales.map(s=>`<option value="${s.id}">${s.nombre}</option>`).join('');
    sel.value = val;
  });
}

// Hook a cargarSucursales para tambien llenar semanales
const originalCargarSuc = window.cargarSucursales;
window.cargarSucursales = async function(){
  if(originalCargarSuc) await originalCargarSuc();
  try{
    const sucs = await api('/sucursales?empresa_id='+(localStorage.getItem('empresa_id')||''));
    window.sucursalesCache = sucs;
    llenarSelectsSemanales();
  }catch(e){}
};

const originalCargarEmpleados = window.cargarEmpleados;

let EDITANDO_ID = null;

async function editarEmp(id){
  try{
    const emps = await api('/empleados');
    const e = emps.find(x=>x.id===id);
    if(!e) return alert('No encontrado');
    EDITANDO_ID = id;
    // Llenar formulario admin
    document.getElementById('emp_id').value = e.id;
    document.getElementById('emp_nombre').value = e.nombre||'';
    document.getElementById('emp_ap_paterno').value = e.apellido_paterno||'';
    document.getElementById('emp_ap_materno').value = e.apellido_materno||'';
    document.getElementById('emp_puesto').value = e.puesto||'';
    document.getElementById('emp_depto').value = e.departamento||'';
    document.getElementById('emp_rol').value = e.rol||'empleado';
    document.getElementById('emp_curp').value = e.curp||'';
    document.getElementById('emp_rfc').value = e.rfc||'';
    document.getElementById('emp_nss').value = e.nss||'';
    document.getElementById('emp_fecha_nac').value = e.fecha_nacimiento||'';
    document.getElementById('emp_genero').value = e.genero||'';
    document.getElementById('emp_civil').value = e.estado_civil||'';
    document.getElementById('emp_sangre').value = e.tipo_sangre||'';
    document.getElementById('emp_direccion').value = e.direccion_completa||'';
    document.getElementById('emp_email_personal').value = e.email_personal||'';
    document.getElementById('emp_telefono').value = e.telefono||'';
    document.getElementById('emp_tel_emergencia').value = e.telefono_emergencia||'';
    document.getElementById('emp_contacto_emergencia').value = e.contacto_emergencia_nombre||'';
    document.getElementById('emp_fecha_ingreso').value = e.fecha_ingreso||'';
    document.getElementById('emp_tipo_contrato').value = e.tipo_contrato||'planta';
    document.getElementById('emp_turno').value = e.turno||'matutino';
    document.getElementById('emp_descansos').value = (e.dias_descanso||[]).join(', ');
    document.getElementById('emp_sueldo').value = e.sueldo_hora||50;
    document.getElementById('emp_sueldo_mensual').value = e.sueldo_mensual||0;
    document.getElementById('emp_banco').value = e.banco||'';
    document.getElementById('emp_cuenta').value = e.cuenta||'';
    document.getElementById('emp_clabe').value = e.clabe||'';
    document.getElementById('emp_comida').value = e.tiempo_comida||120;
    document.getElementById('emp_pass').value = '';
    document.getElementById('emp_pass').placeholder = 'Dejar vacío para no cambiar contraseña';
    // docs
    document.getElementById('doc_ine').checked = e.documentos?.ine||false;
    document.getElementById('doc_domicilio').checked = e.documentos?.comprobante_domicilio||false;
    document.getElementById('doc_curp').checked = e.documentos?.curp_doc||false;
    document.getElementById('doc_contrato').checked = e.documentos?.contrato_firmado||false;
    
    // Cambiar boton
    const btn = document.querySelector('#card-crear-empleado .btn-success');
    if(btn){ btn.innerText = '✏️ Actualizar Empleado ' + id; btn.style.background = '#f59e0b'; }
    
    // Scroll arriba
    document.getElementById('card-crear-empleado').scrollIntoView({behavior:'smooth'});
    
    alert('✏️ Editando a '+e.nombre+' - Modifica lo que necesites y dale Actualizar');
  }catch(err){ console.log(err); alert('Error editando'); }
}

function cancelarEdicion(){
  EDITANDO_ID = null;
  document.getElementById('emp_id').value = '';
  document.getElementById('emp_nombre').value = '';
  document.getElementById('emp_ap_paterno').value = '';
  document.getElementById('emp_ap_materno').value = '';
  document.getElementById('emp_puesto').value = '';
  document.getElementById('emp_telefono').value = '';
  document.getElementById('emp_pass').value = '';
  document.getElementById('emp_pass').placeholder = 'Contraseña *';
  const btn = document.querySelector('#card-crear-empleado .btn-success');
  if(btn){ btn.innerText = '💾 Guardar Empleado COMPLETO en Neon'; btn.style.background = ''; }
  generarID();
}

// Sobrescribir crearEmp para que haga PUT si esta editando
const crearEmpOriginal = window.crearEmp;
async function crearEmp(){
  if(EDITANDO_ID){
    // MODO EDICION - PUT
    const data={
      nombre: document.getElementById('emp_nombre').value,
      apellido_paterno: document.getElementById('emp_ap_paterno').value,
      apellido_materno: document.getElementById('emp_ap_materno').value,
      puesto: document.getElementById('emp_puesto').value,
      departamento: document.getElementById('emp_depto').value,
      rol: document.getElementById('emp_rol').value,
      curp: document.getElementById('emp_curp').value.toUpperCase(),
      rfc: document.getElementById('emp_rfc').value.toUpperCase(),
      nss: document.getElementById('emp_nss').value,
      fecha_nacimiento: document.getElementById('emp_fecha_nac').value,
      genero: document.getElementById('emp_genero').value,
      estado_civil: document.getElementById('emp_civil').value,
      tipo_sangre: document.getElementById('emp_sangre').value,
      direccion_completa: document.getElementById('emp_direccion').value,
      email_personal: document.getElementById('emp_email_personal').value,
      telefono: document.getElementById('emp_telefono').value,
      telefono_emergencia: document.getElementById('emp_tel_emergencia').value,
      contacto_emergencia_nombre: document.getElementById('emp_contacto_emergencia').value,
      fecha_ingreso: document.getElementById('emp_fecha_ingreso').value,
      tipo_contrato: document.getElementById('emp_tipo_contrato').value,
      turno: document.getElementById('emp_turno').value,
      dias_descanso: document.getElementById('emp_descansos').value.split(',').map(s=>s.trim()).filter(Boolean),
      sueldo_hora: document.getElementById('emp_sueldo').value,
      sueldo_mensual: document.getElementById('emp_sueldo_mensual').value,
      banco: document.getElementById('emp_banco').value,
      cuenta: document.getElementById('emp_cuenta').value,
      clabe: document.getElementById('emp_clabe').value,
      tiempo_comida: document.getElementById('emp_comida').value,
      sucursales_ids: [...document.querySelectorAll('#check-suc input:checked')].map(c=>c.value),
      horario: {lunes: document.getElementById('d-lunes').value, martes: document.getElementById('d-martes').value, miercoles: document.getElementById('d-miercoles').value, jueves: document.getElementById('d-jueves').value, viernes: document.getElementById('d-viernes').value, sabado: document.getElementById('d-sabado').value, domingo: document.getElementById('d-domingo').value},
      documentos: {ine: document.getElementById('doc_ine').checked, comprobante_domicilio: document.getElementById('doc_domicilio').checked, curp_doc: document.getElementById('doc_curp').checked, contrato_firmado: document.getElementById('doc_contrato').checked}
    };
    const pass = document.getElementById('emp_pass').value;
    if(pass) data.password = pass;
    try{
      await api('/empleados/'+EDITANDO_ID,'PUT',data);
      alert('✅ Empleado '+EDITANDO_ID+' actualizado');
      cancelarEdicion();
      cargarEmpleados();
    }catch(e){ alert('Error actualizando'); }
    return;
  }
  // MODO CREAR - llama al original logic
  const empresa_id = localStorage.getItem('empresa_id') || null;
  const data={
    id: document.getElementById('emp_id').value,
    empresa_id: empresa_id,
    nombre: document.getElementById('emp_nombre').value,
    apellido_paterno: document.getElementById('emp_ap_paterno').value,
    apellido_materno: document.getElementById('emp_ap_materno').value,
    puesto: document.getElementById('emp_puesto').value,
    departamento: document.getElementById('emp_depto').value,
    rol: document.getElementById('emp_rol').value,
    curp: document.getElementById('emp_curp').value.toUpperCase(),
    rfc: document.getElementById('emp_rfc').value.toUpperCase(),
    nss: document.getElementById('emp_nss').value,
    fecha_nacimiento: document.getElementById('emp_fecha_nac').value,
    genero: document.getElementById('emp_genero').value,
    estado_civil: document.getElementById('emp_civil').value,
    tipo_sangre: document.getElementById('emp_sangre').value,
    direccion_completa: document.getElementById('emp_direccion').value,
    email_personal: document.getElementById('emp_email_personal').value,
    telefono: document.getElementById('emp_telefono').value,
    telefono_emergencia: document.getElementById('emp_tel_emergencia').value,
    contacto_emergencia_nombre: document.getElementById('emp_contacto_emergencia').value,
    fecha_ingreso: document.getElementById('emp_fecha_ingreso').value,
    tipo_contrato: document.getElementById('emp_tipo_contrato').value,
    turno: document.getElementById('emp_turno').value,
    dias_descanso: document.getElementById('emp_descansos').value.split(',').map(s=>s.trim()).filter(Boolean),
    sueldo_hora: document.getElementById('emp_sueldo').value,
    sueldo_mensual: document.getElementById('emp_sueldo_mensual').value,
    banco: document.getElementById('emp_banco').value,
    cuenta: document.getElementById('emp_cuenta').value,
    clabe: document.getElementById('emp_clabe').value,
    password: document.getElementById('emp_pass').value,
    tiempo_comida: document.getElementById('emp_comida').value,
    sucursales_ids: [...document.querySelectorAll('#check-suc input:checked')].map(c=>c.value),
    horario: {lunes: document.getElementById('d-lunes').value, martes: document.getElementById('d-martes').value, miercoles: document.getElementById('d-miercoles').value, jueves: document.getElementById('d-jueves').value, viernes: document.getElementById('d-viernes').value, sabado: document.getElementById('d-sabado').value, domingo: document.getElementById('d-domingo').value},
    documentos: {ine: document.getElementById('doc_ine').checked, comprobante_domicilio: document.getElementById('doc_domicilio').checked, curp_doc: document.getElementById('doc_curp').checked, contrato_firmado: document.getElementById('doc_contrato').checked}
  };
  if(!data.nombre) return alert('Nombre obligatorio');
  const res = await api('/empleados','POST',data, {'X-Empresa-ID': localStorage.getItem('empresa_id')||''});
  alert('✅ Empleado '+res.id+' guardado en Neon');
  cargarEmpleados();
}

async function cargarEmpleados_ORIG(){
  try{
    const emps = await api('/empleados?empresa_id='+ (localStorage.getItem('empresa_id')||''));
    document.getElementById('list-emp').innerHTML = emps.map(e=>`
      <div style="background:#0f172a;padding:12px;border-radius:12px;margin-top:8px;border-left:4px solid ${e.activo?'#10b981':'#ef4444'}">
        <div style="display:flex;justify-content:space-between"><b>${e.id} - ${e.nombre} ${e.apellido_paterno||''} ${e.apellido_materno||''}</b><span style="font-size:10px;background:#6366f1;padding:2px 6px;border-radius:6px">${e.empresa_id||''}</span></div>
        <div style="font-size:11px;color:#94a3b8;margin-top:4px">
          Puesto: ${e.puesto||''} | Depto: ${e.departamento||''} | Rol: ${e.rol||''}<br>
          📱 ${e.telefono||''} | 🚨 Emerg: ${e.telefono_emergencia||'❌'} ${e.contacto_emergencia_nombre||''}<br>
          🪪 CURP: ${e.curp||'❌'} | RFC: ${e.rfc||'❌'} | NSS: ${e.nss||'❌'}<br>
          🏦 ${e.banco||''} ${e.cuenta||''} | Sueldo: $${e.sueldo_hora||0}/h $${e.sueldo_mensual||0}/mes<br>
          📍 ${e.direccion_completa||''} | 🩸 ${e.tipo_sangre||''}
        </div>
        <div style="display:flex;gap:6px;margin-top:8px"><button onclick="toggleEmp('${e.id}')" style="padding:4px 8px;border-radius:6px;border:none;background:${e.activo?'#ef4444':'#10b981'};color:white;font-size:10px">${e.activo?'Desactivar':'Activar'}</button><button onclick="eliminarEmp('${e.id}')" style="padding:4px 8px;border-radius:6px;border:none;background:#334155;color:white;font-size:10px">Eliminar</button></div>
      </div>
    `).join('') || 'Sin empleados';
  }catch(e){ console.log(e); if(typeof originalCargarEmpleados==='function') originalCargarEmpleados(); }
}

</script>
<script>
const THEMES = {
  1: {name:'📱 App Móvil', css:':root{--primary:#6366f1;--bg:#0a0e1a;--card:#151a2a} .card{border-radius:24px} .btn{border-radius:16px;padding:16px}'},
  2: {name:'🖥️ Dashboard Corporativo', css:':root{--primary:#2563eb;--bg:#f8fafc;--card:#ffffff;--text:#0f172a;--border:#e2e8f0;--muted:#64748b} body{background:var(--bg);color:var(--text)} .sidebar{background:white;border-right:1px solid #e2e8f0} .card{background:white;box-shadow:0 1px 3px rgba(0,0,0,.1);border:1px solid #e2e8f0} .input{background:white;color:#0f172a;border:1px solid #e2e8f0}'},
  3: {name:'✨ Minimalista Apple', css:':root{--primary:#000000;--bg:#ffffff;--card:#f5f5f7;--text:#1d1d1f;--border:#d2d2d7;--muted:#86868b} body{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont} .sidebar{background:#f5f5f7} .card{background:var(--card);border:none;box-shadow:none;border-radius:18px} .btn{border-radius:12px;font-weight:600}'},
  4: {name:'🎮 Neón Gaming', css:':root{--primary:#a855f7;--bg:#050510;--card:#0f0f1e;--border:#1e1e3a;--text:#e0e0ff} body{background:var(--bg);background-image:radial-gradient(circle at 20% 50%, rgba(120,0,255,.15), transparent 50%), radial-gradient(circle at 80% 80%, rgba(255,0,128,.15), transparent 50%)} .card{border:1px solid #2a2a4a;box-shadow:0 0 20px rgba(168,85,247,.15)} .btn-primary{background:linear-gradient(135deg,#a855f7,#ec4899);box-shadow:0 0 20px rgba(168,85,247,.5)} .sidebar-item.active{background:linear-gradient(135deg,#a855f7,#ec4899);box-shadow:0 0 15px rgba(168,85,247,.5)}'},
  5: {name:'📊 Kanban Interactivo', css:':root{--primary:#0ea5e9;--bg:#f0f9ff;--card:#ffffff} .card{border-left:4px solid var(--primary);cursor:grab;transition:.2s} .card:active{cursor:grabbing;transform:rotate(2deg) scale(1.02);box-shadow:0 10px 30px rgba(0,0,0,.2)} .grid2{grid-template-columns:1fr} @media(min-width:900px){.grid2{grid-template-columns:1fr 1fr}}'},
  6: {name:'🏢 Empresa Seria', css:':root{--primary:#1e40af;--bg:#f1f5f9;--card:#ffffff;--text:#1e293b;--border:#cbd5e1} .sidebar{background:#1e293b} .sidebar-item{color:#94a3b8} .sidebar-item.active{background:#1e40af} .card{border:1px solid #cbd5e1;border-radius:8px} .btn{border-radius:6px;font-weight:600} .topbar{background:white;border-bottom:2px solid #1e40af}'}
};
function aplicarTema(num){
  const theme = THEMES[num];
  if(!theme) return;
  document.getElementById('dynamic-theme').innerHTML = theme.css;
  localStorage.setItem('tema_admin', num);
  document.getElementById('tema-actual-txt').innerText = theme.name;
  // Marcar activo en selector
  document.querySelectorAll('.tema-option').forEach(o=>o.classList.remove('active'));
  document.getElementById('tema-opt-'+num)?.classList.add('active');
}
function cargarTemaGuardado(){
  const rol = localStorage.getItem('rol');
  if(rol==='empleado'){
    // Empleado siempre tema 1
    document.getElementById('dynamic-theme').innerHTML = THEMES[1].css;
    return;
  }
  const guardado = localStorage.getItem('tema_admin') || '1';
  aplicarTema(guardado);
}
window.addEventListener('load', cargarTemaGuardado);
</script>
</body></html>
"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home(): return HTML

