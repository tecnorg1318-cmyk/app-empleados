
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import uuid, math, json, os, hashlib, random

app = FastAPI(title="Control BONITA 100% FINAL")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
DB_FILE = "database.json"
DB_SQLITE = "clockrd.db"
DATABASE_URL = os.environ.get("DATABASE_URL", "") # Render PostgreSQL

def hash_pass(p): return hashlib.sha256(p.encode()).hexdigest()[:16]

# === NUEVA CAPA DE BASE DE DATOS PROFESIONAL ===
import sqlite3
try:
    from sqlalchemy import create_engine, Column, String, Text, Boolean, Integer, DateTime, text
    from sqlalchemy.orm import declarative_base, sessionmaker
    import sqlalchemy
    HAS_SQLALCHEMY = True
except:
    HAS_SQLALCHEMY = False

def get_db_engine():
    if DATABASE_URL:
        # PostgreSQL en Render
        url = DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return create_engine(url)
    else:
        # SQLite local persistente
        return create_engine(f"sqlite:///{DB_SQLITE}", connect_args={"check_same_thread": False})

if HAS_SQLALCHEMY:
    try:
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
        
        class EmpleadoDB(Base):
            __tablename__ = "empleados"
            id = Column(String, primary_key=True)
            empresa_id = Column(String)
            nombre = Column(String)
            puesto = Column(String)
            password = Column(String)
            data = Column(Text) # JSON con todo lo demás
        
        class AsistenciaDB(Base):
            __tablename__ = "asistencias"
            id = Column(String, primary_key=True)
            empleado_id = Column(String)
            empresa_id = Column(String)
            fecha = Column(String)
            data = Column(Text)

        Base.metadata.create_all(engine)
        print(f"✅ Base de datos lista: {DATABASE_URL[:20] if DATABASE_URL else DB_SQLITE}")
    except Exception as e:
        print(f"⚠️ Error DB: {e}")
        HAS_SQLALCHEMY = False

admins_db = {
    "admin": {"password": hash_pass("admin123"), "rol": "superadmin", "nombre": "Admin Principal"},
    "gerente": {"password": hash_pass("gerente123"), "rol": "gerente", "nombre": "Gerente Sucursal"},
    "rh": {"password": hash_pass("rh123"), "rol": "rh", "nombre": "Recursos Humanos"},
    "supervisor": {"password": hash_pass("super123"), "rol": "supervisor", "nombre": "Supervisor"},
    "demo": {"password": hash_pass("demo123"), "rol": "superadmin", "nombre": "Demo Admin"},
}

# === DBS PRO ===
bonos_db = {}
metas_db = {}
nomina_db = {}
notificaciones_db = []
turnos_rotativos_db = {}
config_admin_db = {"telefono_admin": "", "whatsapp_activo": True, "bono_puntualidad": 500, "sueldo_default": 50}
permisos_db = {"empleado":{"ver":["propia_jornada"],"editar":[]},"supervisor":{"ver":["dashboard","empleados","sucursales","retardos"],"editar":[]},"rh":{"ver":["dashboard","empleados","retardos","nomina","vacaciones"],"editar":["empleados","vacaciones"]},"gerente":{"ver":["dashboard","sucursales","empleados","retardos","ruta_gps","vacaciones"],"editar":["sucursales","empleados"]},"admin":{"ver":["todo"],"editar":["todo"]}}
perfil_fotos_db = {}
asignaciones_flex_db = []  # AGREGADO: asignar sucursal por dia/semana/mes sin quitar BONITA
tareas_sucursal_db = []  # AGREGADO: checklist por sucursal
horas_extra_db = []  # AGREGADO: horas extra
fotos_checkin_db = {}  # AGREGADO: foto obligatoria checkin

def load_db():
    global sucursales_db, empleados_db, evaluaciones_db, asistencias_db, alertas_db, gps_logs_db, vacaciones_db, justificantes_db, audit_db, chat_db, panico_db, reportes_volanteo_db, empresa_db, verificaciones_db, permisos_db, bonos_db, metas_db, nomina_db, notificaciones_db, turnos_rotativos_db, config_admin_db, perfil_fotos_db, asignaciones_flex_db, tareas_sucursal_db, horas_extra_db, fotos_checkin_db
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE,'r', encoding='utf-8') as f:
                data=json.load(f)
                sucursales_db=data.get("sucursales",{})
                empleados_db=data.get("empleados",{"EMPDEMO": {"id":"EMPDEMO","nombre":"Empleado Demo","puesto":"Demo","rol":"empleado","password":hash_pass("demo"),"sucursales_ids":[],"horario":{},"activo":True,"tiempo_comida":120,"telefono":"5210000000000","sueldo_hora":50,"foto":""},
        "EMP0001": {"id":"EMP0001","nombre":"Empleado Prueba","puesto":"Botarga","rol":"empleado","password":hash_pass("0001"),"sucursales_ids":[],"horario":{},"activo":True,"tiempo_comida":120,"telefono":"5210000000000","sueldo_hora":50,"foto":""}})
                evaluaciones_db=data.get("evaluaciones",[]); asistencias_db=data.get("asistencias",[]); alertas_db=data.get("alertas",[]); gps_logs_db=data.get("gps_logs",[]); vacaciones_db=data.get("vacaciones",[]); justificantes_db=data.get("justificantes",[]); audit_db=data.get("audit",[]); chat_db=data.get("chat",[]); panico_db=data.get("panico",[]); reportes_volanteo_db=data.get("reportes_volanteo",[]); empresa_db=data.get("empresa",{}); verificaciones_db=data.get("verificaciones",{}); permisos_db=data.get("permisos",{"empleado":{"ver":["propia_jornada"],"editar":[]},"supervisor":{"ver":["dashboard","empleados","sucursales","retardos"],"editar":[]},"rh":{"ver":["dashboard","empleados","retardos","nomina","vacaciones"],"editar":["empleados","vacaciones"]},"gerente":{"ver":["dashboard","sucursales","empleados","retardos","ruta_gps","vacaciones"],"editar":["sucursales","empleados"]},"admin":{"ver":["todo"],"editar":["todo"]}}); bonos_db=data.get("bonos",{}); metas_db=data.get("metas",{}); nomina_db=data.get("nomina",{}); notificaciones_db=data.get("notificaciones",[]); turnos_rotativos_db=data.get("turnos_rotativos",{}); config_admin_db=data.get("config_admin",{"telefono_admin":"","whatsapp_activo":True,"bono_puntualidad":500,"sueldo_default":50}); perfil_fotos_db=data.get("perfil_fotos",{}); asignaciones_flex_db=data.get("asignaciones_flex",[]); tareas_sucursal_db=data.get("tareas_sucursal",[]); horas_extra_db=data.get("horas_extra",[]); fotos_checkin_db=data.get("fotos_checkin",{}); return
        except Exception as e:
            print(f"Load error {e}")
    asignaciones_flex_db = []; tareas_sucursal_db = []; horas_extra_db = []; fotos_checkin_db = {}; sucursales_db = {}; empleados_db = {"EMPDEMO": {"id":"EMPDEMO","nombre":"Empleado Demo","puesto":"Demo","rol":"empleado","password":hash_pass("demo"),"sucursales_ids":[],"horario":{},"activo":True,"tiempo_comida":120,"telefono":"5210000000000","sueldo_hora":50,"foto":""},
        "EMP0001": {"id":"EMP0001","nombre":"Empleado Prueba","puesto":"Botarga","rol":"empleado","password":hash_pass("0001"),"sucursales_ids":[],"horario":{},"activo":True,"tiempo_comida":120,"telefono":"5210000000000","sueldo_hora":50,"foto":""}}; evaluaciones_db = []; asistencias_db=[]; alertas_db=[]; gps_logs_db=[]; vacaciones_db=[]; justificantes_db=[]; audit_db=[]; chat_db=[]; panico_db=[]; reportes_volanteo_db=[]; empresa_db={}; verificaciones_db={}; permisos_db={"empleado":{"ver":["propia_jornada"],"editar":[]},"supervisor":{"ver":["dashboard","empleados","sucursales","retardos"],"editar":[]},"rh":{"ver":["dashboard","empleados","retardos","nomina","vacaciones"],"editar":["empleados","vacaciones"]},"gerente":{"ver":["dashboard","sucursales","empleados","retardos","ruta_gps","vacaciones"],"editar":["sucursales","empleados"]},"admin":{"ver":["todo"],"editar":["todo"]}}; bonos_db={}; metas_db={}; nomina_db={}; notificaciones_db=[]; turnos_rotativos_db={}; config_admin_db={"telefono_admin":"","whatsapp_activo":True,"bono_puntualidad":500,"sueldo_default":50}; perfil_fotos_db={}

def save_db():
    try:
        with open(DB_FILE,'w', encoding='utf-8') as f: json.dump({"sucursales":sucursales_db,"empleados":empleados_db,"evaluaciones":evaluaciones_db,"asistencias":asistencias_db,"alertas":alertas_db,"gps_logs":gps_logs_db,"vacaciones":vacaciones_db,"justificantes":justificantes_db,"audit":audit_db,"chat":chat_db,"panico":panico_db,"reportes_volanteo":reportes_volanteo_db,"empresa":empresa_db,"verificaciones":verificaciones_db,"permisos":permisos_db,"bonos":bonos_db,"metas":metas_db,"nomina":nomina_db,"notificaciones":notificaciones_db,"turnos_rotativos":turnos_rotativos_db,"config_admin":config_admin_db,"perfil_fotos":perfil_fotos_db, "asignaciones_flex":asignaciones_flex_db, "tareas_sucursal":tareas_sucursal_db, "horas_extra":horas_extra_db, "fotos_checkin":fotos_checkin_db}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(e)

load_db()
def audit_log(usuario, accion, detalle):
    audit_db.append({"fecha":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"usuario":usuario,"accion":accion,"detalle":detalle})
    if len(audit_db)>500: audit_db.pop(0)
    save_db()
DIAS_RETENCION=60
def get_next_id():
    max_num=0
    for eid in empleados_db.keys():
        try:
            if eid.startswith("EMP"): num=int(eid.replace("EMP","")); max_num=max(max_num,num)
        except: pass
    return f"EMP{max_num+1:04d}"
def distancia_m(lat1, lon1, lat2, lon2):
    try:
        R=6371000; phi1=math.radians(lat1); phi2=math.radians(lat2); dphi=math.radians(lat2-lat1); dlambda=math.radians(lon2-lon1); a=math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2; c=2*math.atan2(math.sqrt(a), math.sqrt(1-a)); return R*c
    except: return 0
def limpiar_gps_antiguo():
    limite = datetime.now() - timedelta(days=DIAS_RETENCION)
    def es_reciente(f):
        try: return datetime.strptime(f, "%Y-%m-%d %H:%M:%S") >= limite
        except: return True
    gps_logs_db[:] = [g for g in gps_logs_db if es_reciente(g.get("fecha",""))]; alertas_db[:] = [a for a in alertas_db if a.get("tipo")!="gps_fuera" or es_reciente(a.get("fecha",""))]


@app.get("/api/db-status")
def db_status():
    tipo = "PostgreSQL" if DATABASE_URL else "SQLite" if HAS_SQLALCHEMY else "JSON"
    return {
        "tipo": tipo,
        "url": DATABASE_URL[:30]+"..." if DATABASE_URL else DB_SQLITE,
        "sqlite_existe": os.path.exists(DB_SQLITE),
        "json_existe": os.path.exists(DB_FILE),
        "empleados": len(empleados_db),
        "empresas": len(empresa_db) if isinstance(empresa_db, dict) else 1,
        "mensaje": "Base de datos conectada ✅" if tipo!="JSON" else "Usando JSON temporal ⚠️ - Crea PostgreSQL en Render"
    }

@app.post("/api/migrar-a-db")
def migrar_a_db():
    if not HAS_SQLALCHEMY:
        raise HTTPException(400, "SQLAlchemy no instalado")
    try:
        Session = sessionmaker(bind=engine)
        session = Session()
        # Migrar empresas y empleados actuales a DB real
        count=0
        for eid, emp in empleados_db.items():
            exists = session.execute(text(f"SELECT id FROM empleados WHERE id='{eid}'")).fetchone()
            if not exists:
                session.execute(text(f"INSERT INTO empleados (id, data) VALUES (:id, :data)"), {"id": eid, "data": json.dumps(emp)})
                count+=1
        session.commit()
        return {"ok": True, "migrados": count, "mensaje": f"Migrados {count} empleados a {DB_SQLITE if not DATABASE_URL else 'PostgreSQL'}"}
    except Exception as e:
        raise HTTPException(500, f"Error migración: {e}")

@app.put("/api/empresa-info")
def actualizar_empresa(data: dict):
    if "info" not in empresa_db:
        empresa_db["info"]={}
    empresa_db["info"].update({
        "nombre_admin": data.get("nombre_admin", empresa_db["info"].get("nombre_admin","")),
        "usuario": data.get("usuario", empresa_db["info"].get("usuario","")),
        "empresa": data.get("empresa", empresa_db["info"].get("empresa","")),
        "direccion": data.get("direccion", empresa_db["info"].get("direccion","")),
        "correo": data.get("correo", empresa_db["info"].get("correo","")),
        "telefono": data.get("telefono", empresa_db["info"].get("telefono","")),
        "logo": data.get("logo", empresa_db["info"].get("logo","")),
        "slogan": data.get("slogan", empresa_db["info"].get("slogan","")),
        "color": data.get("color", empresa_db["info"].get("color","#6366f1"))
    })
    save_db()
    return empresa_db["info"]

@app.post("/api/enviar-codigo-email")

def enviar_codigo_email(data: dict):
    email=data.get("email")
    codigo=str(random.randint(100000,999999))
    verificaciones_db[email]={"codigo":codigo,"tipo":"email","fecha":datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    save_db()
    # Simulación: en producción se enviaría por SMTP Gmail
    return {"ok":True,"codigo":codigo,"mensaje":f"Código enviado a {email}"}

@app.post("/api/enviar-codigo-whatsapp")
def enviar_codigo_whatsapp(data: dict):
    tel=data.get("telefono")
    codigo=str(random.randint(100000,999999))
    verificaciones_db[tel]={"codigo":codigo,"tipo":"whatsapp","fecha":datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    save_db()
    return {"ok":True,"codigo":codigo,"mensaje":f"Código enviado por WhatsApp a {tel}"}

@app.post("/api/verificar-codigo")
def verificar_codigo(data: dict):
    clave=data.get("clave") # email o telefono
    codigo=data.get("codigo")
    if clave in verificaciones_db and verificaciones_db[clave]["codigo"]==codigo:
        verificaciones_db[clave]["verificado"]=True
        save_db()
        return {"ok":True}
    raise HTTPException(400,"Código incorrecto")

@app.post("/api/registro-empresa")
def registro_empresa(data: dict):
    # Validar
    nombre=data.get("nombre")
    usuario=data.get("usuario")
    empresa=data.get("empresa")
    direccion=data.get("direccion")
    correo=data.get("correo")
    telefono=data.get("telefono")
    password=data.get("password")
    confirm=data.get("confirm_password")
    if not all([nombre,usuario,empresa,direccion,correo,telefono,password,confirm]):
        raise HTTPException(400,"Faltan campos")
    if password!=confirm:
        raise HTTPException(400,"Contraseñas no coinciden")
    if len(password)<4:
        raise HTTPException(400,"Contraseña muy corta")
    if len(usuario)<3:
        raise HTTPException(400,"Usuario muy corto mínimo 3 caracteres")
    if usuario in admins_db:
        raise HTTPException(400,"Usuario ya existe, elige otro")
    # Verificar email y whatsapp verificados
    if correo not in verificaciones_db or not verificaciones_db[correo].get("verificado"):
        raise HTTPException(400,"Correo no verificado")
    if telefono not in verificaciones_db or not verificaciones_db[telefono].get("verificado"):
        raise HTTPException(400,"WhatsApp no verificado")
    # Crear admin con usuario elegido
    admin_user=usuario.lower().strip()
    empresa_db["info"]={"nombre_admin":nombre,"usuario":admin_user,"empresa":empresa,"direccion":direccion,"correo":correo,"telefono":telefono,"fecha_registro":datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    # Crear cuenta admin principal con usuario elegido
    admins_db[admin_user]={"password":hash_pass(password),"rol":"superadmin","nombre":nombre,"empresa":empresa,"correo":correo,"telefono":telefono,"usuario":admin_user}
    # También crear admin con correo como usuario para login con correo
    admins_db[correo]={"password":hash_pass(password),"rol":"superadmin","nombre":nombre,"empresa":empresa,"correo":correo,"telefono":telefono,"usuario":admin_user}
    save_db()
    audit_log(admin_user,"registro_empresa",f"Empresa {empresa} registrada por {nombre}")
    return {"ok":True,"usuario":admin_user,"correo":correo,"empresa":empresa,"mensaje":f"Empresa {empresa} registrada correctamente. Ya puedes iniciar sesión con tu usuario {admin_user} o tu correo"}

@app.get("/api/empresa-info")
def empresa_info():
    return empresa_db.get("info",{})

@app.post("/api/login")

def login(d: dict):
    u=d.get("usuario"); p=d.get("password"); hp=hash_pass(p)
    if u in admins_db and (admins_db[u]["password"]==hp or admins_db[u]["password"]==p): audit_log(u,"login",f"rol {admins_db[u]['rol']}"); return {"rol":"admin","subrol":admins_db[u]["rol"],"usuario":u,"nombre":admins_db[u]["nombre"]}
    if u=="admin" and (p=="admin123" or hp==hash_pass("admin123")): return {"rol":"admin","subrol":"superadmin","usuario":u}
    if u in empleados_db:
        emp=empleados_db[u]
        if not emp.get("activo",True): raise HTTPException(403, "DESACTIVADO")
        if emp.get("password")==p or emp.get("password")==hp: audit_log(u,"login","empleado"); return {"rol":"empleado","usuario":u,"nombre":emp["nombre"]}
        raise HTTPException(401, "Contraseña incorrecta")
    raise HTTPException(401, "No existe")

@app.post("/api/recuperar-password")
def recuperar(d: dict):
    eid=d.get("empleado_id")
    if eid not in empleados_db: raise HTTPException(404, "No existe")
    nueva = str(random.randint(1000,9999)); empleados_db[eid]["password"]=hash_pass(nueva); save_db(); audit_log(eid,"recuperar_password",nueva); return {"ok":True,"nueva_password":nueva,"mensaje":f"Tu nueva contraseña temporal es: {nueva}"}

@app.post("/api/cambiar-password")
def cambiar_pass(d: dict):
    eid=d.get("empleado_id"); old=d.get("old_password"); new=d.get("new_password")
    if eid in empleados_db:
        if empleados_db[eid]["password"]!=old and empleados_db[eid]["password"]!=hash_pass(old): raise HTTPException(400, "Incorrecta")
        empleados_db[eid]["password"]=hash_pass(new); save_db(); return {"ok":True}
    if eid in admins_db:
        if admins_db[eid]["password"]!=hash_pass(old) and admins_db[eid]["password"]!=old: raise HTTPException(400, "Incorrecta")
        admins_db[eid]["password"]=hash_pass(new); return {"ok":True}
    raise HTTPException(404)

@app.get("/empleados/next-id")
def next_id(): return {"next_id": get_next_id()}
@app.get("/sucursales")
def ls(): return list(sucursales_db.values())
@app.post("/sucursales")
def cs(s: dict): sucursales_db[s["id"]]=s; audit_log("admin","crear_sucursal",s["id"]); save_db(); return s
@app.put("/sucursales/{sid}")
def upd_suc(sid: str, data: dict):
    if sid not in sucursales_db: raise HTTPException(404)
    sucursales_db[sid].update(data); save_db(); return sucursales_db[sid]
@app.delete("/sucursales/{sid}")
def del_suc(sid: str):
    if sid in sucursales_db: del sucursales_db[sid]; save_db()
    return {"ok":True}
@app.get("/empleados")
def le(): return list(empleados_db.values())
@app.post("/empleados")
def ce(e: dict):
    if not e.get("id") or e["id"]=="": e["id"]=get_next_id()
    if e["id"] in empleados_db: e["id"]=get_next_id()
    if not e.get("password"): e["password"]=hash_pass(e["id"])
    else: e["password"]=hash_pass(e["password"])
    e["activo"]=e.get("activo",True)
    if "tiempo_comida" not in e: e["tiempo_comida"]=120
    empleados_db[e["id"]]=e; save_db(); return e
@app.put("/empleados/{eid}")
def upd(eid: str, data: dict):
    if eid not in empleados_db: raise HTTPException(404)
    if "password" in data and data["password"]: data["password"]=hash_pass(data["password"])
    empleados_db[eid].update(data); save_db(); return empleados_db[eid]
@app.put("/empleados/{eid}/toggle")
def toggle(eid: str):
    if eid not in empleados_db: raise HTTPException(404)
    empleados_db[eid]["activo"]=not empleados_db[eid].get("activo",True); save_db(); return empleados_db[eid]
@app.delete("/empleados/{eid}")
def delete_emp(eid: str):
    if eid in empleados_db: empleados_db[eid]["activo"]=False; empleados_db[eid]["eliminado"]=True; empleados_db[eid]["fecha_eliminado"]=datetime.now().strftime("%Y-%m-%d %H:%M:%S"); save_db()
    return {"ok":True}
@app.post("/vacaciones/solicitar")
def solicitar_vac(data: dict):
    vac={"id":str(uuid.uuid4())[:8],"empleado_id":data.get("empleado_id"),"tipo":data.get("tipo","vacaciones"),"fecha_inicio":data.get("fecha_inicio"),"fecha_fin":data.get("fecha_fin"),"motivo":data.get("motivo",""),"estado":"pendiente","fecha_solicitud":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"nombre":empleados_db.get(data.get("empleado_id"),{}).get("nombre","")}
    vacaciones_db.append(vac); save_db(); return vac
@app.get("/vacaciones/{eid}")
def vac_emp(eid: str): return [v for v in vacaciones_db if v["empleado_id"]==eid][::-1]
@app.get("/vacaciones")
def vac_todos(): return vacaciones_db[::-1]
@app.put("/vacaciones/{vid}/estado")
def vac_estado(vid: str, data: dict):
    v=next((x for x in vacaciones_db if x["id"]==vid), None)
    if not v: raise HTTPException(404)
    v["estado"]=data.get("estado","pendiente"); save_db(); return v
@app.post("/justificantes/subir")
def subir_just(data: dict):
    j={"id":str(uuid.uuid4())[:8],"empleado_id":data.get("empleado_id"),"fecha":data.get("fecha"),"tipo":data.get("tipo","enfermedad"),"motivo":data.get("motivo",""),"foto":data.get("foto",""),"estado":"pendiente","fecha_subida":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"nombre":empleados_db.get(data.get("empleado_id"),{}).get("nombre","")}
    justificantes_db.append(j); save_db(); return j
@app.get("/justificantes/{eid}")
def just_emp(eid: str): return [j for j in justificantes_db if j["empleado_id"]==eid][::-1]
@app.get("/justificantes")
def just_todos(): return justificantes_db[::-1]
@app.put("/justificantes/{jid}/estado")
def just_estado(jid: str, data: dict):
    j=next((x for x in justificantes_db if x["id"]==jid), None)
    if not j: raise HTTPException(404)
    j["estado"]=data.get("estado","pendiente"); save_db(); return j
@app.post("/chat/enviar")
def chat_enviar(data: dict):
    msg={"id":str(uuid.uuid4())[:8],"de":data.get("de"),"para":data.get("para"),"mensaje":data.get("mensaje"),"fecha":datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    chat_db.append(msg); save_db(); return msg
@app.get("/chat/{eid}")
def chat_get(eid: str): return [m for m in chat_db if m["de"]==eid or m["para"]==eid or eid=="admin"][-100:]
@app.get("/chat")
def chat_all(): return chat_db[-100:]
@app.post("/panico/sos")
def sos(data: dict):
    alerta={"id":str(uuid.uuid4())[:6],"empleado_id":data.get("empleado_id"),"nombre":empleados_db.get(data.get("empleado_id"),{}).get("nombre",""),"lat":data.get("lat"),"lng":data.get("lng"),"mensaje":data.get("mensaje","¡EMERGENCIA SOS!"),"fecha":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"tipo":"panico"}
    panico_db.append(alerta); save_db(); return {"ok":True}
@app.get("/panico/todos")
def panico_todos(): return panico_db[::-1]
@app.get("/admin/dashboard")
def dashboard():
    hoy=datetime.now().strftime("%Y-%m-%d"); mes=datetime.now().strftime("%Y-%m")
    hoy_asist=[a for a in asistencias_db if a["fecha_dia"]==hoy]; mes_asist=[a for a in asistencias_db if a.get("fecha")==mes]
    total_emp=len([e for e in empleados_db.values() if e.get("activo") and not e.get("eliminado")])
    presentes_hoy=len([a for a in hoy_asist if a.get("entrada")])
    ranking=[]
    for eid, emp in empleados_db.items():
        if not emp.get("activo") or emp.get("eliminado"): continue
        asist=[a for a in asistencias_db if a["empleado_id"]==eid and a.get("fecha")==mes]
        total_ret=sum([a.get("retardo_entrada",0)+a.get("retardo_comida",0) for a in asist])
        ranking.append({"id":eid,"nombre":emp.get("nombre"),"retardos":total_ret,"dias":len(asist),"horas":round(sum([a.get("horas_trabajadas",0) for a in asist]),1)})
    ranking=sorted(ranking, key=lambda x: x["retardos"])
    return {"fecha":hoy,"mes":mes,"total_empleados":total_emp,"presentes_hoy":presentes_hoy,"ausentes_hoy":total_emp-presentes_hoy,"retardos_hoy":len([a for a in hoy_asist if a.get("retardo_entrada",0)>0]),"horas_mes":round(sum([a.get("horas_trabajadas",0) for a in mes_asist]),1),"ranking":ranking[:10],"gps_alertas_hoy":len([a for a in alertas_db if a.get("tipo")=="gps_fuera" and hoy in a.get("fecha","")]),"vacaciones_pendientes":len([v for v in vacaciones_db if v["estado"]=="pendiente"]),"justificantes_pend":len([j for j in justificantes_db if j["estado"]=="pendiente"]),"panico_hoy":len([p for p in panico_db if hoy in p.get("fecha","")])}
@app.get("/admin/reportes-graficas")
def reportes():
    from collections import defaultdict
    mes=datetime.now().strftime("%Y-%m")
    por_dia=defaultdict(int); por_empleado=defaultdict(float)
    for a in asistencias_db:
        if a.get("fecha")==mes:
            por_dia[a.get("fecha_dia")] += a.get("retardo_entrada",0)+a.get("retardo_comida",0)
            por_empleado[a["empleado_id"]] += a.get("horas_trabajadas",0)
    return {"retardos_por_dia":{"labels":list(por_dia.keys())[-7:], "valores":list(por_dia.values())[-7:]}, "horas_por_empleado":{"labels":[empleados_db.get(k,{}).get("nombre",k) for k in por_empleado.keys()], "valores":list(por_empleado.values())}, "total_asistencias_mes":len([a for a in asistencias_db if a.get("fecha")==mes])}
@app.get("/admin/backup")
def backup():
    return {"fecha":datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "database": {"sucursales":sucursales_db,"empleados":empleados_db,"asistencias":asistencias_db,"evaluaciones":evaluaciones_db,"vacaciones":vacaciones_db,"justificantes":justificantes_db,"gps_logs":gps_logs_db,"alertas":alertas_db}, "total_empleados":len(empleados_db),"total_asistencias":len(asistencias_db)}
@app.get("/asistencia/hoy/{eid}")
def asistencia_hoy(eid: str):
    hoy=datetime.now().strftime("%Y-%m-%d")
    reg = next((a for a in asistencias_db if a["empleado_id"]==eid and a["fecha_dia"]==hoy), None)
    tiempo = empleados_db.get(eid,{}).get("tiempo_comida",120)
    dias=["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]
    suc_id=empleados_db.get(eid,{}).get("horario",{}).get(dias[datetime.now().weekday()],"")
    suc=sucursales_db.get(suc_id, {})
    base={"empleado_id":eid,"fecha_dia":hoy,"tiempo_permitido":tiempo,"sucursal":suc}
    if not reg: return {**base,"estado":"sin_entrada","siguiente":"entrada","texto_boton":"📍 Registrar ENTRADA (Activa GPS)","color":"#10b981","gps_activo":False}
    if not reg.get("entrada"): return {**reg,**base,"estado":"sin_entrada","siguiente":"entrada","texto_boton":"📍 Registrar ENTRADA (Activa GPS)","color":"#10b981","gps_activo":False}
    if not reg.get("salida_comida"): return {**reg,**base,"estado":"trabajando","siguiente":"salida_comida","texto_boton":"🍔 Salida a COMER (Desactiva GPS)","color":"#f59e0b","gps_activo":True}
    if not reg.get("regreso_comida"): return {**reg,**base,"estado":"comiendo","siguiente":"regreso_comida","texto_boton":"↩️ Regreso de COMIDA (Reactiva GPS)","color":"#6366f1","gps_activo":False}
    if not reg.get("salida_final"): return {**reg,**base,"estado":"trabajando_tarde","siguiente":"salida_final","texto_boton":"🏠 SALIDA FINAL (Desactiva GPS)","color":"#ef4444","gps_activo":True}
    return {**reg,**base,"estado":"completo","siguiente":"completo","texto_boton":"✅ Jornada COMPLETADA","color":"#64748b","gps_activo":False}
@app.post("/asistencia/registrar")
def registrar(data: dict):
    eid=data.get("empleado_id"); tipo=data.get("tipo"); lat=data.get("lat"); lng=data.get("lng")
    if eid not in empleados_db: raise HTTPException(404)
    TIEMPO_COMIDA_MAX = empleados_db[eid].get("tiempo_comida", 120)
    ahora=datetime.now(); hoy=ahora.strftime("%Y-%m-%d"); hora=ahora.strftime("%H:%M:%S")
    reg = next((a for a in asistencias_db if a["empleado_id"]==eid and a["fecha_dia"]==hoy), None)
    if not reg:
        reg={"empleado_id":eid,"fecha":ahora.strftime("%Y-%m"),"fecha_dia":hoy,"entrada":None,"salida_comida":None,"regreso_comida":None,"salida_final":None,"retardo_entrada":0,"retardo_comida":0,"horas_trabajadas":0,"min_comida":0,"tiempo_permitido":TIEMPO_COMIDA_MAX}
        asistencias_db.append(reg)
    else: reg["tiempo_permitido"]=TIEMPO_COMIDA_MAX
    dias=["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]
    suc_id=empleados_db[eid].get("horario",{}).get(dias[ahora.weekday()],""); suc=sucursales_db.get(suc_id)
    def check_geocerca(lat_emp, lng_emp):
        if not suc: return True, 0
        s_lat=suc.get("lat"); s_lng=suc.get("lng"); radio=suc.get("radio",200)
        if s_lat is None or s_lng is None: return True, 0
        try: d=distancia_m(float(lat_emp), float(lng_emp), float(s_lat), float(s_lng)); return d <= float(radio), d
        except: return True,0
    if tipo=="entrada":
        if reg["entrada"]: raise HTTPException(400, "Ya entrada")
        retardo=0
        if suc:
            try: h,m=map(int,suc.get("hora_entrada","08:00").split(":")); ent=ahora.replace(hour=h,minute=m,second=0,microsecond=0); retardo=max(0, round((ahora-ent).total_seconds()/60,1))
            except: pass
        if lat and lng and suc and suc.get("lat"):
            ok, dist = check_geocerca(lat,lng)
            if not ok: alertas_db.append({"id":str(uuid.uuid4())[:6],"empleado_id":eid,"mensaje":f"🚨 Entrada FUERA de {suc.get('nombre')} - a {int(dist)}m","fecha":ahora.strftime("%Y-%m-%d %H:%M"),"tipo":"gps_fuera","distancia":dist,"lat":lat,"lng":lng})
        reg["entrada"]=hora; reg["retardo_entrada"]=retardo; reg["sucursal_id"]=suc_id
    elif tipo=="salida_comida":
        if not reg["entrada"]: raise HTTPException(400, "Primero entrada")
        if reg["salida_comida"]: raise HTTPException(400, "Ya salida comida")
        reg["salida_comida"]=hora
    elif tipo=="regreso_comida":
        if not reg["salida_comida"]: raise HTTPException(400, "Primero salida comida")
        if reg["regreso_comida"]: raise HTTPException(400, "Ya regreso")
        reg["regreso_comida"]=hora
        try:
            from datetime import datetime as dt
            sc = dt.strptime(reg["salida_comida"], "%H:%M:%S"); rc = dt.strptime(hora, "%H:%M:%S")
            diff_min = (rc - sc).total_seconds()/60
            if diff_min < 0: diff_min += 1440
            reg["min_comida"]=round(diff_min,1); reg["retardo_comida"]=round(diff_min - TIEMPO_COMIDA_MAX,1) if diff_min > TIEMPO_COMIDA_MAX else 0
        except: pass
    elif tipo=="salida_final":
        if not reg["regreso_comida"] and reg["salida_comida"]: raise HTTPException(400, "Primero regreso")
        if not reg["entrada"]: raise HTTPException(400, "Primero entrada")
        if reg["salida_final"]: raise HTTPException(400, "Ya salida final")
        reg["salida_final"]=hora; reg["firma"]=data.get("firma")
        try:
            from datetime import datetime as dt
            e = dt.strptime(reg["entrada"], "%H:%M:%S"); s = dt.strptime(hora, "%H:%M:%S")
            diff = (s - e).total_seconds()/3600
            if diff < 0: diff += 24
            if reg["salida_comida"] and reg["regreso_comida"]:
                sc = dt.strptime(reg["salida_comida"], "%H:%M:%S"); rc = dt.strptime(reg["regreso_comida"], "%H:%M:%S")
                comida = (rc - sc).total_seconds()/3600
                if comida < 0: comida += 24
                diff -= comida
            reg["horas_trabajadas"]=round(diff,2)
        except: pass
    else: raise HTTPException(400, "Tipo invalido")
    save_db(); return reg
@app.post("/gps/update")
def gps_update(data: dict):
    limpiar_gps_antiguo(); eid=data.get("empleado_id"); lat=data.get("lat"); lng=data.get("lng")
    if eid not in empleados_db: raise HTTPException(404)
    ahora=datetime.now(); hoy=ahora.strftime("%Y-%m-%d")
    reg = next((a for a in asistencias_db if a["empleado_id"]==eid and a["fecha_dia"]==hoy), None)
    if not reg or not reg.get("entrada") or reg.get("salida_final"): return {"ok":True}
    if reg.get("salida_comida") and not reg.get("regreso_comida"): return {"ok":True}
    dias=["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]
    suc_id=empleados_db[eid].get("horario",{}).get(dias[ahora.weekday()],""); suc=sucursales_db.get(suc_id)
    if not suc or not suc.get("lat"):
        gps_logs_db.append({"empleado_id":eid,"lat":lat,"lng":lng,"fecha":ahora.strftime("%Y-%m-%d %H:%M:%S"),"fecha_dia":hoy,"hora":ahora.strftime("%H:%M:%S"),"sucursal_id":suc_id}); save_db(); return {"ok":True,"dentro":True}
    try:
        dist=distancia_m(float(lat),float(lng),float(suc["lat"]),float(suc["lng"])); dentro=dist <= float(suc.get("radio",200))
        gps_logs_db.append({"empleado_id":eid,"lat":lat,"lng":lng,"distancia":round(dist,1),"dentro":dentro,"fecha":ahora.strftime("%Y-%m-%d %H:%M:%S"),"fecha_dia":hoy,"hora":ahora.strftime("%H:%M:%S"),"sucursal_id":suc_id,"empleado_nombre":empleados_db[eid]["nombre"]})
        if not dentro: alertas_db.append({"id":str(uuid.uuid4())[:6],"empleado_id":eid,"mensaje":f"🚨 GPS: {empleados_db[eid]['nombre']} se alejó {int(dist)}m de {suc.get('nombre')}","fecha":ahora.strftime("%Y-%m-%d %H:%M:%S"),"tipo":"gps_fuera","distancia":dist,"lat":lat,"lng":lng})
        save_db(); return {"ok":True,"dentro":dentro,"distancia":dist}
    except: return {"ok":False}
@app.get("/gps/ruta/{eid}")
def gps_ruta(eid: str, dias: int = 60):
    limpiar_gps_antiguo(); limite = datetime.now() - timedelta(days=dias)
    logs = [g for g in gps_logs_db if g["empleado_id"]==eid]
    def f_reciente(f_str):
        try: return datetime.strptime(f_str, "%Y-%m-%d %H:%M:%S") >= limite
        except: return True
    logs = [l for l in logs if f_reciente(l.get("fecha",""))]
    por_dia={}
    for l in logs:
        d=l.get("fecha_dia","sin_fecha")
        if d not in por_dia: por_dia[d]=[]
        por_dia[d].append(l)
    return {"empleado_id":eid,"dias_guardados":dias,"total_puntos":len(logs),"ruta_por_dia":por_dia,"logs":logs[::-1][:500]}
@app.get("/gps/ruta-todos")
def gps_ruta_todos(dias: int = 60):
    limpiar_gps_antiguo(); limite = datetime.now() - timedelta(days=dias)
    def f_reciente(f_str):
        try: return datetime.strptime(f_str, "%Y-%m-%d %H:%M:%S") >= limite
        except: return True
    logs=[l for l in gps_logs_db if f_reciente(l.get("fecha",""))]
    return {"dias_guardados":dias,"total_puntos":len(logs),"logs":logs[::-1][:500]}
@app.get("/gps/export-csv/{eid}")
def export_csv(eid: str, dias: int = 60):
    import csv, io; limite = datetime.now() - timedelta(days=dias)
    logs=[g for g in gps_logs_db if g["empleado_id"]==eid and datetime.strptime(g.get("fecha","2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S") >= limite]
    output=io.StringIO(); writer=csv.writer(output); writer.writerow(["empleado_id","nombre","fecha","hora","fecha_dia","lat","lng","distancia_m","dentro_geocerca","sucursal"])
    for l in logs: writer.writerow([l.get("empleado_id"),l.get("empleado_nombre",""),l.get("fecha"),l.get("hora",""),l.get("fecha_dia"),l.get("lat"),l.get("lng"),l.get("distancia",""),l.get("dentro",""),l.get("sucursal_id","")])
    return {"empleado_id":eid,"dias":dias,"csv":output.getvalue(),"filename":f"ruta_{eid}_{dias}dias.csv"}
@app.get("/gps/alertas")
def gps_alertas(): return [a for a in alertas_db if a.get("tipo")=="gps_fuera"][::-1]
@app.post("/evaluaciones")
def crear_eval(data: dict):
    hoy=datetime.now(); eid=data.get("empleado_id"); cals=data.get("calificaciones",{}); total=0
    for i in range(1,12):
        if i in [6,12]: continue
        try: v=int(cals.get(str(i),0))
        except: v=0
        total+=v
    mes=hoy.strftime("%Y-%m")
    if any(ev["empleado_id"]==eid and ev["mes"]==mes for ev in evaluaciones_db): raise HTTPException(400, "Ya evaluado")
    nivel="Necesita Mejorar"
    if total==100: nivel="EXCELENTE 🌟"
    elif total>=90: nivel="Muy Bueno"
    elif total>=80: nivel="Bueno"
    nueva={"id":len(evaluaciones_db)+1,"empleado_id":eid,"empleado_nombre":empleados_db[eid]["nombre"],"fecha":hoy.strftime("%Y-%m-%d %H:%M"),"mes":mes,"calificaciones":cals,"total":total,"nivel":nivel,"firma":data.get("firma")}
    evaluaciones_db.append(nueva); save_db(); return nueva
@app.get("/evaluaciones")
def list_ev(): return evaluaciones_db
@app.get("/empleado/{eid}/historial")
def hist(eid: str): return [e for e in evaluaciones_db if e["empleado_id"]==eid]
@app.get("/alertas/{eid}")
def al(eid: str): return [a for a in alertas_db if a["empleado_id"]==eid or eid=="admin"][::-1][:50]
@app.get("/asistencias/{eid}")
def asis(eid: str): return [a for a in asistencias_db if a["empleado_id"]==eid][::-1]
@app.get("/empleado/{eid}/retardos-mes")
def retardos_mes(eid: str):
    mes=datetime.now().strftime("%Y-%m")
    asist=[a for a in asistencias_db if a["empleado_id"]==eid and a.get("fecha","")==mes]
    total_entrada=sum([a.get("retardo_entrada",0) for a in asist]); total_comida=sum([a.get("retardo_comida",0) for a in asist]); total_horas=round(sum([a.get("horas_trabajadas",0) for a in asist]),2)
    retardos=[]
    for a in asist:
        if a.get("retardo_entrada",0)>0 or a.get("retardo_comida",0)>0:
            retardos.append({"fecha_dia":a.get("fecha_dia"),"entrada":a.get("entrada"),"retardo_entrada":a.get("retardo_entrada",0),"salida_comida":a.get("salida_comida"),"regreso_comida":a.get("regreso_comida"),"min_comida":a.get("min_comida",0),"tiempo_permitido":a.get("tiempo_permitido",120),"retardo_comida":a.get("retardo_comida",0)})
    return {"empleado_id":eid,"mes":mes,"total_retardo_entrada":round(total_entrada,1),"total_retardo_comida":round(total_comida,1),"total_retardos":round(total_entrada+total_comida,1),"total_horas":total_horas,"detalles":retardos,"asistencias":asist}
@app.get("/admin/retardos-todos")
def retardos_todos():
    mes=datetime.now().strftime("%Y-%m"); result=[]
    for eid, emp in empleados_db.items():
        if emp.get("eliminado"): continue
        asist=[a for a in asistencias_db if a["empleado_id"]==eid and a.get("fecha","")==mes]
        if len(asist)>0:
            total_e=sum([a.get("retardo_entrada",0) for a in asist]); total_c=sum([a.get("retardo_comida",0) for a in asist])
            result.append({"empleado_id":eid,"nombre":emp.get("nombre"),"total_entrada":round(total_e,1),"total_comida":round(total_c,1),"total":round(total_e+total_c,1),"dias_trabajados":len(asist),"horas_mes":round(sum([a.get("horas_trabajadas",0) for a in asist]),1)})
    return sorted(result, key=lambda x: x["total"], reverse=True)
@app.get("/admin/export-excel")
def export_excel():
    import csv, io; output=io.StringIO(); writer=csv.writer(output); writer.writerow(["empleado_id","nombre","mes","fecha_dia","entrada","retardo_entrada","salida_comida","regreso_comida","min_comida","retardo_comida","salida_final","horas_trabajadas","horas_extra","sucursal"])
    mes=datetime.now().strftime("%Y-%m")
    for a in asistencias_db:
        if mes in a.get("fecha",""):
            emp=empleados_db.get(a["empleado_id"],{}); horas=a.get("horas_trabajadas",0); extra=round(horas-8,2) if horas>8 else 0
            writer.writerow([a["empleado_id"],emp.get("nombre",""),a.get("fecha"),a.get("fecha_dia"),a.get("entrada"),a.get("retardo_entrada"),a.get("salida_comida"),a.get("regreso_comida"),a.get("min_comida"),a.get("retardo_comida"),a.get("salida_final"),a.get("horas_trabajadas"),extra,a.get("sucursal_id")])
    return {"csv":output.getvalue(),"filename":f"nomina_{mes}.csv"}
@app.get("/admin/audit")
def audit_get(): return audit_db[::-1][:100]
@app.get("/admin/papelera")
def papelera(): return [e for e in empleados_db.values() if e.get("eliminado")]

@app.post("/reportes-volanteo")
def crear_reporte_volanteo(data: dict):
    rep={
        "id": str(uuid.uuid4())[:8],
        "empleado_id": data.get("empleado_id"),
        "nombre": empleados_db.get(data.get("empleado_id"),{}).get("nombre",""),
        "sucursal_id": data.get("sucursal_id"),
        "sucursal_nombre": sucursales_db.get(data.get("sucursal_id"),{}).get("nombre", data.get("sucursal_id","")),
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fecha_dia": datetime.now().strftime("%Y-%m-%d"),
        "manana_volantearon": data.get("manana_volantearon",""),
        "manana_quien": data.get("manana_quien",""),
        "manana_nombre": data.get("manana_nombre",""),
        "tarde_volantearon": data.get("tarde_volantearon",""),
        "tarde_quien": data.get("tarde_quien",""),
        "tarde_nombre": data.get("tarde_nombre",""),
        "comentario": data.get("comentario","")
    }
    reportes_volanteo_db.append(rep)
    save_db()
    return rep

@app.get("/reportes-volanteo")
def list_reportes_volanteo():
    return reportes_volanteo_db[::-1]

@app.get("/reportes-volanteo/{eid}")
def list_reportes_volanteo_emp(eid: str):
    return [r for r in reportes_volanteo_db if r["empleado_id"]==eid][::-1]

@app.get("/admin/compañeros-hoy/{suc_id}")

def companeros_hoy(suc_id: str):
    hoy=datetime.now().strftime("%Y-%m-%d"); dias=["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]; dia_hoy=dias[datetime.now().weekday()]; trabajando=[]
    for eid, emp in empleados_db.items():
        if not emp.get("activo") or emp.get("eliminado"): continue
        hor=emp.get("horario",{}).get(dia_hoy,"")
        if hor==suc_id or suc_id in emp.get("sucursales_ids",[]):
            asist=next((a for a in asistencias_db if a["empleado_id"]==eid and a["fecha_dia"]==hoy), None)
            trabajando.append({"id":eid,"nombre":emp.get("nombre"),"puesto":emp.get("puesto"),"entrada":asist.get("entrada") if asist else None,"estado":"presente" if asist and asist.get("entrada") else "ausente"})
    return trabajando

def audit_log(usuario, accion, detalle):
    audit_db.append({"fecha":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"usuario":usuario,"accion":accion,"detalle":detalle})
    if len(audit_db)>500: audit_db.pop(0)
    save_db()
DIAS_RETENCION=60
def get_next_id():
    max_num=0
    for eid in empleados_db.keys():
        try:
            if eid.startswith("EMP"): num=int(eid.replace("EMP","")); max_num=max(max_num,num)
        except: pass
    return f"EMP{max_num+1:04d}"
def distancia_m(lat1, lon1, lat2, lon2):
    try:
        R=6371000; phi1=math.radians(lat1); phi2=math.radians(lat2); dphi=math.radians(lat2-lat1); dlambda=math.radians(lon2-lon1); a=math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2; c=2*math.atan2(math.sqrt(a), math.sqrt(1-a)); return R*c
    except: return 0
def limpiar_gps_antiguo():
    limite = datetime.now() - timedelta(days=DIAS_RETENCION)
    def es_reciente(f):
        try: return datetime.strptime(f, "%Y-%m-%d %H:%M:%S") >= limite
        except: return True
    gps_logs_db[:] = [g for g in gps_logs_db if es_reciente(g.get("fecha",""))]; alertas_db[:] = [a for a in alertas_db if a.get("tipo")!="gps_fuera" or es_reciente(a.get("fecha",""))]



@app.get("/api/permisos")
def get_permisos(): return permisos_db
@app.post("/api/permisos")
def save_permisos(data: dict):
    global permisos_db; permisos_db=data; save_db(); return {"ok": True}

# === AGREGADO BONITA: ASIGNACIONES POR DIA/SEMANA/MES CON EDITAR ===
@app.get("/api/asignaciones-flex")
def get_asig_flex(): return asignaciones_flex_db

@app.post("/api/asignaciones-flex/dia")
def post_asig_dia(data: dict):
    global asignaciones_flex_db
    asignaciones_flex_db[:] = [a for a in asignaciones_flex_db if not (a.get("tipo")=="dia" and a.get("empleado_id")==data.get("empleado_id") and a.get("fecha")==data.get("fecha"))]
    data["id"]=str(uuid.uuid4())[:8]; data["tipo"]="dia"; data["created_at"]=datetime.now().isoformat()
    asignaciones_flex_db.append(data); save_db(); return data

@app.post("/api/asignaciones-flex/semana")
def post_asig_semana(data: dict):
    global asignaciones_flex_db
    asignaciones_flex_db[:] = [a for a in asignaciones_flex_db if not (a.get("tipo")=="semana" and a.get("empleado_id")==data.get("empleado_id") and a.get("semana")==data.get("semana"))]
    data["id"]=str(uuid.uuid4())[:8]; data["tipo"]="semana"; data["created_at"]=datetime.now().isoformat()
    asignaciones_flex_db.append(data); save_db(); return data

@app.post("/api/asignaciones-flex/mes")
def post_asig_mes(data: dict):
    global asignaciones_flex_db
    asignaciones_flex_db[:] = [a for a in asignaciones_flex_db if not (a.get("tipo")=="mes" and a.get("empleado_id")==data.get("empleado_id") and a.get("mes")==data.get("mes"))]
    data["id"]=str(uuid.uuid4())[:8]; data["tipo"]="mes"; data["created_at"]=datetime.now().isoformat()
    asignaciones_flex_db.append(data); save_db(); return data

@app.put("/api/asignaciones-flex/{aid}")
def put_asig_flex(aid: str, data: dict):
    global asignaciones_flex_db
    for a in asignaciones_flex_db:
        if a.get("id")==aid:
            a.update(data); save_db(); return a
    return {"error":"No existe"}

@app.delete("/api/asignaciones-flex/{aid}")
def del_asig_flex(aid: str):
    global asignaciones_flex_db
    asignaciones_flex_db[:] = [a for a in asignaciones_flex_db if a.get("id")!=aid]
    save_db(); return {"ok":True}

@app.get("/api/empleado/{eid}/hoy-flex")
def get_hoy_flex(eid: str):
    from datetime import datetime as dt
    hoy = dt.now(); fecha_str = hoy.strftime("%Y-%m-%d")
    semana_str = f"{hoy.isocalendar()[0]}-W{hoy.isocalendar()[1]:02d}"
    mes_str = hoy.strftime("%Y-%m")
    dias = ["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]
    dia_nombre = dias[hoy.weekday()]
    asig_dia = next((a for a in asignaciones_flex_db if a.get("tipo")=="dia" and a.get("empleado_id")==eid and a.get("fecha")==fecha_str), None)
    if asig_dia:
        sid=asig_dia.get("sucursal_id"); return {"sucursal_id":sid,"sucursal_nombre":sucursales_db.get(sid,{}).get("nombre",sid),"origen":"dia","fecha":fecha_str,"dia_nombre":dia_nombre.capitalize(),"semana":semana_str,"mes":mes_str,"semana_completa":{}}
    asig_sem = next((a for a in asignaciones_flex_db if a.get("tipo")=="semana" and a.get("empleado_id")==eid and a.get("semana")==semana_str), None)
    if asig_sem:
        sid=asig_sem.get(dia_nombre,""); return {"sucursal_id":sid,"sucursal_nombre":sucursales_db.get(sid,{}).get("nombre",sid),"origen":"semana","fecha":fecha_str,"dia_nombre":dia_nombre.capitalize(),"semana":semana_str,"mes":mes_str,"semana_completa":{d:asig_sem.get(d,"") for d in dias}}
    asig_mes = next((a for a in asignaciones_flex_db if a.get("tipo")=="mes" and a.get("empleado_id")==eid and a.get("mes")==mes_str), None)
    if asig_mes:
        sid=asig_mes.get("sucursal_id",""); return {"sucursal_id":sid,"sucursal_nombre":sucursales_db.get(sid,{}).get("nombre",sid),"origen":"mes","fecha":fecha_str,"dia_nombre":dia_nombre.capitalize(),"semana":semana_str,"mes":mes_str,"semana_completa":{}}
    emp=empleados_db.get(eid,{}); sid=(emp.get("sucursales_ids") or [""])[0] if emp.get("sucursales_ids") else ""
    return {"sucursal_id":sid,"sucursal_nombre":sucursales_db.get(sid,{}).get("nombre",sid),"origen":"base","fecha":fecha_str,"dia_nombre":dia_nombre.capitalize(),"semana":semana_str,"mes":mes_str,"semana_completa":{}}


# === AGREGADOS NUEVOS CONSERVANDO BONITA ===
@app.get("/api/tareas-sucursal")
def get_tareas(): return tareas_sucursal_db
@app.post("/api/tareas-sucursal")
def post_tarea(data: dict):
    data["id"]=str(uuid.uuid4())[:8]; data["created_at"]=datetime.now().isoformat(); tareas_sucursal_db.append(data); save_db(); return data
@app.put("/api/tareas-sucursal/{tid}")
def put_tarea(tid: str, data: dict):
    for t in tareas_sucursal_db:
        if t.get("id")==tid:
            t.update(data); save_db(); return t
    return {"error":"No existe"}

@app.get("/api/horas-extra")
def get_he(): return horas_extra_db
@app.post("/api/horas-extra")
def post_he(data: dict):
    data["id"]=str(uuid.uuid4())[:8]; data["created_at"]=datetime.now().isoformat(); horas_extra_db.append(data); save_db(); return data

@app.get("/api/export/{tipo}")
def export_tipo(tipo: str):
    # Devuelve datos para exportar en frontend a Excel
    if tipo=="asignaciones": return asignaciones_flex_db
    if tipo=="empleados": return list(empleados_db.values())[:200]
    if tipo=="evaluaciones": return evaluaciones_db[-200:]
    if tipo=="asistencias": return asistencias_db[-200:]
    return []

@app.get("/api/ranking-mes")
def ranking_mes():
    # Top 3 por promedio evaluaciones del mes
    from collections import defaultdict
    scores=defaultdict(list)
    for ev in evaluaciones_db[-200:]:
        scores[ev.get("empleado_id","")].append(ev.get("total",0) or ev.get("calificacion",0) or 0)
    ranking=[]
    for eid, vals in scores.items():
        if vals:
            emp=empleados_db.get(eid,{})
            ranking.append({"empleado_id":eid,"nombre":emp.get("nombre",eid),"prom": round(sum(vals)/len(vals),1),"total":len(vals)})
    ranking=sorted(ranking, key=lambda x: x["prom"], reverse=True)[:10]
    return ranking

@app.get("/api/calendario-asignaciones")
def calendario_asig(mes: str = ""):
    if not mes:
        mes=datetime.now().strftime("%Y-%m")
    # Devuelve asignaciones del mes para calendario visual
    res=[a for a in asignaciones_flex_db if mes in (a.get("fecha","") or a.get("mes","") or a.get("semana",""))]
    return res

@app.get("/api/config-admin")
def get_config_admin(): return config_admin_db
@app.post("/api/config-admin")
def save_config_admin(data: dict):
    global config_admin_db; config_admin_db.update(data); save_db(); return config_admin_db
@app.get("/api/nomina/{mes}")
def calcular_nomina(mes: str):
    result=[]
    for eid, emp in empleados_db.items():
        if not emp.get("activo") or emp.get("eliminado"): continue
        sueldo=float(emp.get("sueldo_hora", config_admin_db.get("sueldo_default",50)))
        asist_mes=[a for a in asistencias_db if a["empleado_id"]==eid and a.get("fecha","").startswith(mes)]
        horas=sum([a.get("horas_trabajadas",0) for a in asist_mes])
        retardos=sum([a.get("retardo_entrada",0)+a.get("retardo_comida",0) for a in asist_mes])
        dias=len(asist_mes)
        bono=0
        if retardos==0 and dias>=20: bono=float(config_admin_db.get("bono_puntualidad",500))
        total=round(horas*sueldo+bono,2)
        result.append({"empleado_id":eid,"nombre":emp.get("nombre"),"horas":round(horas,2),"retardos":retardos,"dias":dias,"sueldo_hora":sueldo,"bono":bono,"total":total,"telefono":emp.get("telefono","")})
    return sorted(result, key=lambda x: x["total"], reverse=True)
@app.get("/api/reporte-sucursales/{mes}")
def reporte_suc(mes: str):
    res=[]
    for sid, suc in sucursales_db.items():
        emps_suc=[e for e in empleados_db.values() if sid in e.get("sucursales_ids",[]) or sid in e.get("horario",{}).values()]
        asist=[a for a in asistencias_db if a.get("sucursal_id")==sid and a.get("fecha","").startswith(mes)]
        horas=sum([a.get("horas_trabajadas",0) for a in asist])
        retardos=sum([a.get("retardo_entrada",0) for a in asist])
        res.append({"sucursal_id":sid,"nombre":suc.get("nombre"),"empleados":len(emps_suc),"horas_mes":round(horas,1),"retardos_mes":retardos,"promedio_horas":round(horas/len(emps_suc),1) if emps_suc else 0})
    return sorted(res, key=lambda x: x["horas_mes"], reverse=True)
@app.get("/api/calendario/{eid}/{mes}")
def calendario_emp(eid: str, mes: str):
    import calendar
    try:
        year, m = map(int, mes.split("-"))
        _, last_day = calendar.monthrange(year, m)
        dias=[]
        for d in range(1, last_day+1):
            fecha=f"{year}-{m:02d}-{d:02d}"
            asist=next((a for a in asistencias_db if a["empleado_id"]==eid and a.get("fecha_dia")==fecha), None)
            vac=next((v for v in vacaciones_db if v["empleado_id"]==eid and v["fecha_inicio"]<=fecha<=v["fecha_fin"] and v["estado"]=="aprobado"), None)
            if vac: dias.append({"dia":d,"fecha":fecha,"estado":"vacaciones","color":"#8b5cf6","entrada":None})
            elif asist:
                if asist.get("retardo_entrada",0)>0 or asist.get("retardo_comida",0)>0: dias.append({"dia":d,"fecha":fecha,"estado":"retardo","entrada":asist.get("entrada"),"color":"#f59e0b"})
                else: dias.append({"dia":d,"fecha":fecha,"estado":"presente","entrada":asist.get("entrada"),"color":"#10b981"})
            else: dias.append({"dia":d,"fecha":fecha,"estado":"ausente","color":"#1e293b"})
        return dias
    except Exception as e:
        raise HTTPException(400, str(e))
@app.post("/api/notificar-whatsapp")
def notificar_whatsapp(data: dict):
    notificaciones_db.append({"id":str(uuid.uuid4())[:6],"para":data.get("para"),"mensaje":data.get("mensaje"),"tipo":data.get("tipo","info"),"fecha":datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    save_db()
    tel=data.get("para","").replace("+","").replace(" ","")
    link=f"https://wa.me/{tel}?text={data.get('mensaje','')}"
    return {"ok": True, "link": link}
@app.get("/api/anti-trampa/log")
def anti_trampa_log():
    sospechosos=[]
    for eid in empleados_db:
        logs=[g for g in gps_logs_db if g.get("empleado_id")==eid]
        if len(logs)>=3:
            if len(set([f"{l.get('lat')},{l.get('lng')}" for l in logs[-5:]]))==1:
                sospechosos.append({"empleado_id":eid,"nombre":empleados_db[eid].get("nombre"),"motivo":"Ubicación idéntica 5 veces (posible GPS falso)","fecha":logs[-1].get("fecha")})
    return sospechosos
@app.get("/api/empleado/{eid}/perfil")
def perfil_emp(eid: str):
    emp=empleados_db.get(eid)
    if not emp: raise HTTPException(404)
    asist_mes=[a for a in asistencias_db if a["empleado_id"]==eid]
    horas_total=sum([a.get("horas_trabajadas",0) for a in asist_mes])
    return {"empleado":emp,"horas_total":horas_total,"asistencias":len(asist_mes),"foto":perfil_fotos_db.get(eid,"")}
@app.post("/api/empleado/{eid}/foto")
def subir_foto(eid: str, data: dict):
    perfil_fotos_db[eid]=data.get("foto","")[:500000]
    if eid in empleados_db: empleados_db[eid]["foto"]=data.get("foto","")[:500000]
    save_db()
    return {"ok": True}


@app.get("/api/db-status")
def db_status():
    tipo = "PostgreSQL" if DATABASE_URL else "SQLite" if HAS_SQLALCHEMY else "JSON"
    return {
        "tipo": tipo,
        "url": DATABASE_URL[:30]+"..." if DATABASE_URL else DB_SQLITE,
        "sqlite_existe": os.path.exists(DB_SQLITE),
        "json_existe": os.path.exists(DB_FILE),
        "empleados": len(empleados_db),
        "empresas": len(empresa_db) if isinstance(empresa_db, dict) else 1,
        "mensaje": "Base de datos conectada ✅" if tipo!="JSON" else "Usando JSON temporal ⚠️ - Crea PostgreSQL en Render"
    }

@app.post("/api/migrar-a-db")
def migrar_a_db():
    if not HAS_SQLALCHEMY:
        raise HTTPException(400, "SQLAlchemy no instalado")
    try:
        Session = sessionmaker(bind=engine)
        session = Session()
        # Migrar empresas y empleados actuales a DB real
        count=0
        for eid, emp in empleados_db.items():
            exists = session.execute(text(f"SELECT id FROM empleados WHERE id='{eid}'")).fetchone()
            if not exists:
                session.execute(text(f"INSERT INTO empleados (id, data) VALUES (:id, :data)"), {"id": eid, "data": json.dumps(emp)})
                count+=1
        session.commit()
        return {"ok": True, "migrados": count, "mensaje": f"Migrados {count} empleados a {DB_SQLITE if not DATABASE_URL else 'PostgreSQL'}"}
    except Exception as e:
        raise HTTPException(500, f"Error migración: {e}")

@app.put("/api/empresa-info")
def actualizar_empresa(data: dict):
    if "info" not in empresa_db:
        empresa_db["info"]={}
    empresa_db["info"].update({
        "nombre_admin": data.get("nombre_admin", empresa_db["info"].get("nombre_admin","")),
        "usuario": data.get("usuario", empresa_db["info"].get("usuario","")),
        "empresa": data.get("empresa", empresa_db["info"].get("empresa","")),
        "direccion": data.get("direccion", empresa_db["info"].get("direccion","")),
        "correo": data.get("correo", empresa_db["info"].get("correo","")),
        "telefono": data.get("telefono", empresa_db["info"].get("telefono","")),
        "logo": data.get("logo", empresa_db["info"].get("logo","")),
        "slogan": data.get("slogan", empresa_db["info"].get("slogan","")),
        "color": data.get("color", empresa_db["info"].get("color","#6366f1"))
    })
    save_db()
    return empresa_db["info"]

@app.post("/api/enviar-codigo-email")

def enviar_codigo_email(data: dict):
    email=data.get("email")
    codigo=str(random.randint(100000,999999))
    verificaciones_db[email]={"codigo":codigo,"tipo":"email","fecha":datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    save_db()
    # Simulación: en producción se enviaría por SMTP Gmail
    return {"ok":True,"codigo":codigo,"mensaje":f"Código enviado a {email}"}

@app.post("/api/enviar-codigo-whatsapp")
def enviar_codigo_whatsapp(data: dict):
    tel=data.get("telefono")
    codigo=str(random.randint(100000,999999))
    verificaciones_db[tel]={"codigo":codigo,"tipo":"whatsapp","fecha":datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    save_db()
    return {"ok":True,"codigo":codigo,"mensaje":f"Código enviado por WhatsApp a {tel}"}

@app.post("/api/verificar-codigo")
def verificar_codigo(data: dict):
    clave=data.get("clave") # email o telefono
    codigo=data.get("codigo")
    if clave in verificaciones_db and verificaciones_db[clave]["codigo"]==codigo:
        verificaciones_db[clave]["verificado"]=True
        save_db()
        return {"ok":True}
    raise HTTPException(400,"Código incorrecto")

@app.post("/api/registro-empresa")
def registro_empresa(data: dict):
    # Validar
    nombre=data.get("nombre")
    usuario=data.get("usuario")
    empresa=data.get("empresa")
    direccion=data.get("direccion")
    correo=data.get("correo")
    telefono=data.get("telefono")
    password=data.get("password")
    confirm=data.get("confirm_password")
    if not all([nombre,usuario,empresa,direccion,correo,telefono,password,confirm]):
        raise HTTPException(400,"Faltan campos")
    if password!=confirm:
        raise HTTPException(400,"Contraseñas no coinciden")
    if len(password)<4:
        raise HTTPException(400,"Contraseña muy corta")
    if len(usuario)<3:
        raise HTTPException(400,"Usuario muy corto mínimo 3 caracteres")
    if usuario in admins_db:
        raise HTTPException(400,"Usuario ya existe, elige otro")
    # Verificar email y whatsapp verificados
    if correo not in verificaciones_db or not verificaciones_db[correo].get("verificado"):
        raise HTTPException(400,"Correo no verificado")
    if telefono not in verificaciones_db or not verificaciones_db[telefono].get("verificado"):
        raise HTTPException(400,"WhatsApp no verificado")
    # Crear admin con usuario elegido
    admin_user=usuario.lower().strip()
    empresa_db["info"]={"nombre_admin":nombre,"usuario":admin_user,"empresa":empresa,"direccion":direccion,"correo":correo,"telefono":telefono,"fecha_registro":datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    # Crear cuenta admin principal con usuario elegido
    admins_db[admin_user]={"password":hash_pass(password),"rol":"superadmin","nombre":nombre,"empresa":empresa,"correo":correo,"telefono":telefono,"usuario":admin_user}
    # También crear admin con correo como usuario para login con correo
    admins_db[correo]={"password":hash_pass(password),"rol":"superadmin","nombre":nombre,"empresa":empresa,"correo":correo,"telefono":telefono,"usuario":admin_user}
    save_db()
    audit_log(admin_user,"registro_empresa",f"Empresa {empresa} registrada por {nombre}")
    return {"ok":True,"usuario":admin_user,"correo":correo,"empresa":empresa,"mensaje":f"Empresa {empresa} registrada correctamente. Ya puedes iniciar sesión con tu usuario {admin_user} o tu correo"}

@app.get("/api/empresa-info")
def empresa_info():
    return empresa_db.get("info",{})


@app.post("/api/login")
def login(d: dict):
    u=d.get("usuario"); p=d.get("password"); hp=hash_pass(p)
    if u in admins_db and (admins_db[u]["password"]==hp or admins_db[u]["password"]==p):
        audit_log(u,"login",f"rol {admins_db[u]['rol']}")
        return {"rol":"admin","subrol":admins_db[u]["rol"],"usuario":u,"nombre":admins_db[u]["nombre"],"empresa":empresa_db.get("info",{}).get("empresa","")}
    if u=="admin" and (p=="admin123" or hp==hash_pass("admin123")):
        return {"rol":"admin","subrol":"superadmin","usuario":u,"nombre":"Admin","empresa":empresa_db.get("info",{}).get("empresa","")}
    if u in empleados_db:
        emp=empleados_db[u]
        if not emp.get("activo",True): raise HTTPException(403, "DESACTIVADO")
        if emp.get("password")==p or emp.get("password")==hp:
            audit_log(u,"login","empleado")
            rol_emp=emp.get("rol","empleado")
            if rol_emp in ["admin","gerente","rh","supervisor"]:
                return {"rol":"admin","subrol":rol_emp,"usuario":u,"nombre":emp["nombre"],"empresa":empresa_db.get("info",{}).get("empresa","")}
            else:
                return {"rol":"empleado","subrol":rol_emp,"usuario":u,"nombre":emp["nombre"],"rol_empleado":rol_emp}
        raise HTTPException(401, "Contraseña incorrecta")
    raise HTTPException(401, "No existe")


@app.post("/api/recuperar-password")
def recuperar(d: dict):
    eid=d.get("empleado_id")
    if eid not in empleados_db: raise HTTPException(404, "No existe")
    nueva = str(random.randint(1000,9999)); empleados_db[eid]["password"]=hash_pass(nueva); save_db(); audit_log(eid,"recuperar_password",nueva); return {"ok":True,"nueva_password":nueva,"mensaje":f"Tu nueva contraseña temporal es: {nueva}"}

@app.post("/api/cambiar-password")
def cambiar_pass(d: dict):
    eid=d.get("empleado_id"); old=d.get("old_password"); new=d.get("new_password")
    if eid in empleados_db:
        if empleados_db[eid]["password"]!=old and empleados_db[eid]["password"]!=hash_pass(old): raise HTTPException(400, "Incorrecta")
        empleados_db[eid]["password"]=hash_pass(new); save_db(); return {"ok":True}
    if eid in admins_db:
        if admins_db[eid]["password"]!=hash_pass(old) and admins_db[eid]["password"]!=old: raise HTTPException(400, "Incorrecta")
        admins_db[eid]["password"]=hash_pass(new); return {"ok":True}
    raise HTTPException(404)

@app.get("/empleados/next-id")
def next_id(): return {"next_id": get_next_id()}
@app.get("/sucursales")
def ls(): return list(sucursales_db.values())
@app.post("/sucursales")
def cs(s: dict): sucursales_db[s["id"]]=s; audit_log("admin","crear_sucursal",s["id"]); save_db(); return s
@app.put("/sucursales/{sid}")
def upd_suc(sid: str, data: dict):
    if sid not in sucursales_db: raise HTTPException(404)
    sucursales_db[sid].update(data); save_db(); return sucursales_db[sid]
@app.delete("/sucursales/{sid}")
def del_suc(sid: str):
    if sid in sucursales_db: del sucursales_db[sid]; save_db()
    return {"ok":True}
@app.get("/empleados")
def le(): return list(empleados_db.values())

@app.post("/empleados")
def ce(e: dict):
    if not e.get("id") or e["id"]=="": e["id"]=get_next_id()
    if e["id"] in empleados_db: e["id"]=get_next_id()
    if not e.get("password"): e["password"]=hash_pass(e["id"])
    else: e["password"]=hash_pass(e["password"])
    e["activo"]=e.get("activo",True)
    if "tiempo_comida" not in e: e["tiempo_comida"]=120
    if "telefono" not in e: e["telefono"]=""
    if "sueldo_hora" not in e: e["sueldo_hora"]=config_admin_db.get("sueldo_default",50)
    else:
        try: e["sueldo_hora"]=float(e["sueldo_hora"])
        except: e["sueldo_hora"]=50
    if "rol" not in e: e["rol"]="empleado"
    if e["rol"] not in ["empleado","supervisor","rh","gerente","admin"]: e["rol"]="empleado"
    if "foto" not in e: e["foto"]=""
    empleados_db[e["id"]]=e
    save_db()
    return e

@app.put("/empleados/{eid}")
def upd(eid: str, data: dict):
    if eid not in empleados_db: raise HTTPException(404)
    if "password" in data and data["password"]: data["password"]=hash_pass(data["password"])
    empleados_db[eid].update(data); save_db(); return empleados_db[eid]
@app.put("/empleados/{eid}/toggle")
def toggle(eid: str):
    if eid not in empleados_db: raise HTTPException(404)
    empleados_db[eid]["activo"]=not empleados_db[eid].get("activo",True); save_db(); return empleados_db[eid]
@app.delete("/empleados/{eid}")
def delete_emp(eid: str):
    if eid in empleados_db: empleados_db[eid]["activo"]=False; empleados_db[eid]["eliminado"]=True; empleados_db[eid]["fecha_eliminado"]=datetime.now().strftime("%Y-%m-%d %H:%M:%S"); save_db()
    return {"ok":True}
@app.post("/vacaciones/solicitar")
def solicitar_vac(data: dict):
    vac={"id":str(uuid.uuid4())[:8],"empleado_id":data.get("empleado_id"),"tipo":data.get("tipo","vacaciones"),"fecha_inicio":data.get("fecha_inicio"),"fecha_fin":data.get("fecha_fin"),"motivo":data.get("motivo",""),"estado":"pendiente","fecha_solicitud":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"nombre":empleados_db.get(data.get("empleado_id"),{}).get("nombre","")}
    vacaciones_db.append(vac); save_db(); return vac
@app.get("/vacaciones/{eid}")
def vac_emp(eid: str): return [v for v in vacaciones_db if v["empleado_id"]==eid][::-1]
@app.get("/vacaciones")
def vac_todos(): return vacaciones_db[::-1]
@app.put("/vacaciones/{vid}/estado")
def vac_estado(vid: str, data: dict):
    v=next((x for x in vacaciones_db if x["id"]==vid), None)
    if not v: raise HTTPException(404)
    v["estado"]=data.get("estado","pendiente"); save_db(); return v
@app.post("/justificantes/subir")
def subir_just(data: dict):
    j={"id":str(uuid.uuid4())[:8],"empleado_id":data.get("empleado_id"),"fecha":data.get("fecha"),"tipo":data.get("tipo","enfermedad"),"motivo":data.get("motivo",""),"foto":data.get("foto",""),"estado":"pendiente","fecha_subida":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"nombre":empleados_db.get(data.get("empleado_id"),{}).get("nombre","")}
    justificantes_db.append(j); save_db(); return j
@app.get("/justificantes/{eid}")
def just_emp(eid: str): return [j for j in justificantes_db if j["empleado_id"]==eid][::-1]
@app.get("/justificantes")
def just_todos(): return justificantes_db[::-1]
@app.put("/justificantes/{jid}/estado")
def just_estado(jid: str, data: dict):
    j=next((x for x in justificantes_db if x["id"]==jid), None)
    if not j: raise HTTPException(404)
    j["estado"]=data.get("estado","pendiente"); save_db(); return j
@app.post("/chat/enviar")
def chat_enviar(data: dict):
    msg={"id":str(uuid.uuid4())[:8],"de":data.get("de"),"para":data.get("para"),"mensaje":data.get("mensaje"),"fecha":datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    chat_db.append(msg); save_db(); return msg
@app.get("/chat/{eid}")
def chat_get(eid: str): return [m for m in chat_db if m["de"]==eid or m["para"]==eid or eid=="admin"][-100:]
@app.get("/chat")
def chat_all(): return chat_db[-100:]
@app.post("/panico/sos")
def sos(data: dict):
    alerta={"id":str(uuid.uuid4())[:6],"empleado_id":data.get("empleado_id"),"nombre":empleados_db.get(data.get("empleado_id"),{}).get("nombre",""),"lat":data.get("lat"),"lng":data.get("lng"),"mensaje":data.get("mensaje","¡EMERGENCIA SOS!"),"fecha":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"tipo":"panico"}
    panico_db.append(alerta); save_db(); return {"ok":True}
@app.get("/panico/todos")
def panico_todos(): return panico_db[::-1]
@app.get("/admin/dashboard")
def dashboard():
    hoy=datetime.now().strftime("%Y-%m-%d"); mes=datetime.now().strftime("%Y-%m")
    hoy_asist=[a for a in asistencias_db if a["fecha_dia"]==hoy]; mes_asist=[a for a in asistencias_db if a.get("fecha")==mes]
    total_emp=len([e for e in empleados_db.values() if e.get("activo") and not e.get("eliminado")])
    presentes_hoy=len([a for a in hoy_asist if a.get("entrada")])
    ranking=[]
    for eid, emp in empleados_db.items():
        if not emp.get("activo") or emp.get("eliminado"): continue
        asist=[a for a in asistencias_db if a["empleado_id"]==eid and a.get("fecha")==mes]
        total_ret=sum([a.get("retardo_entrada",0)+a.get("retardo_comida",0) for a in asist])
        ranking.append({"id":eid,"nombre":emp.get("nombre"),"retardos":total_ret,"dias":len(asist),"horas":round(sum([a.get("horas_trabajadas",0) for a in asist]),1)})
    ranking=sorted(ranking, key=lambda x: x["retardos"])
    return {"fecha":hoy,"mes":mes,"total_empleados":total_emp,"presentes_hoy":presentes_hoy,"ausentes_hoy":total_emp-presentes_hoy,"retardos_hoy":len([a for a in hoy_asist if a.get("retardo_entrada",0)>0]),"horas_mes":round(sum([a.get("horas_trabajadas",0) for a in mes_asist]),1),"ranking":ranking[:10],"gps_alertas_hoy":len([a for a in alertas_db if a.get("tipo")=="gps_fuera" and hoy in a.get("fecha","")]),"vacaciones_pendientes":len([v for v in vacaciones_db if v["estado"]=="pendiente"]),"justificantes_pend":len([j for j in justificantes_db if j["estado"]=="pendiente"]),"panico_hoy":len([p for p in panico_db if hoy in p.get("fecha","")])}
@app.get("/admin/reportes-graficas")
def reportes():
    from collections import defaultdict
    mes=datetime.now().strftime("%Y-%m")
    por_dia=defaultdict(int); por_empleado=defaultdict(float)
    for a in asistencias_db:
        if a.get("fecha")==mes:
            por_dia[a.get("fecha_dia")] += a.get("retardo_entrada",0)+a.get("retardo_comida",0)
            por_empleado[a["empleado_id"]] += a.get("horas_trabajadas",0)
    return {"retardos_por_dia":{"labels":list(por_dia.keys())[-7:], "valores":list(por_dia.values())[-7:]}, "horas_por_empleado":{"labels":[empleados_db.get(k,{}).get("nombre",k) for k in por_empleado.keys()], "valores":list(por_empleado.values())}, "total_asistencias_mes":len([a for a in asistencias_db if a.get("fecha")==mes])}
@app.get("/admin/backup")
def backup():
    return {"fecha":datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "database": {"sucursales":sucursales_db,"empleados":empleados_db,"asistencias":asistencias_db,"evaluaciones":evaluaciones_db,"vacaciones":vacaciones_db,"justificantes":justificantes_db,"gps_logs":gps_logs_db,"alertas":alertas_db}, "total_empleados":len(empleados_db),"total_asistencias":len(asistencias_db)}
@app.get("/asistencia/hoy/{eid}")
def asistencia_hoy(eid: str):
    hoy=datetime.now().strftime("%Y-%m-%d")
    reg = next((a for a in asistencias_db if a["empleado_id"]==eid and a["fecha_dia"]==hoy), None)
    tiempo = empleados_db.get(eid,{}).get("tiempo_comida",120)
    dias=["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]
    suc_id=empleados_db.get(eid,{}).get("horario",{}).get(dias[datetime.now().weekday()],"")
    suc=sucursales_db.get(suc_id, {})
    base={"empleado_id":eid,"fecha_dia":hoy,"tiempo_permitido":tiempo,"sucursal":suc}
    if not reg: return {**base,"estado":"sin_entrada","siguiente":"entrada","texto_boton":"📍 Registrar ENTRADA (Activa GPS)","color":"#10b981","gps_activo":False}
    if not reg.get("entrada"): return {**reg,**base,"estado":"sin_entrada","siguiente":"entrada","texto_boton":"📍 Registrar ENTRADA (Activa GPS)","color":"#10b981","gps_activo":False}
    if not reg.get("salida_comida"): return {**reg,**base,"estado":"trabajando","siguiente":"salida_comida","texto_boton":"🍔 Salida a COMER (Desactiva GPS)","color":"#f59e0b","gps_activo":True}
    if not reg.get("regreso_comida"): return {**reg,**base,"estado":"comiendo","siguiente":"regreso_comida","texto_boton":"↩️ Regreso de COMIDA (Reactiva GPS)","color":"#6366f1","gps_activo":False}
    if not reg.get("salida_final"): return {**reg,**base,"estado":"trabajando_tarde","siguiente":"salida_final","texto_boton":"🏠 SALIDA FINAL (Desactiva GPS)","color":"#ef4444","gps_activo":True}
    return {**reg,**base,"estado":"completo","siguiente":"completo","texto_boton":"✅ Jornada COMPLETADA","color":"#64748b","gps_activo":False}
@app.post("/asistencia/registrar")
def registrar(data: dict):
    eid=data.get("empleado_id"); tipo=data.get("tipo"); lat=data.get("lat"); lng=data.get("lng")
    if eid not in empleados_db: raise HTTPException(404)
    TIEMPO_COMIDA_MAX = empleados_db[eid].get("tiempo_comida", 120)
    ahora=datetime.now(); hoy=ahora.strftime("%Y-%m-%d"); hora=ahora.strftime("%H:%M:%S")
    reg = next((a for a in asistencias_db if a["empleado_id"]==eid and a["fecha_dia"]==hoy), None)
    if not reg:
        reg={"empleado_id":eid,"fecha":ahora.strftime("%Y-%m"),"fecha_dia":hoy,"entrada":None,"salida_comida":None,"regreso_comida":None,"salida_final":None,"retardo_entrada":0,"retardo_comida":0,"horas_trabajadas":0,"min_comida":0,"tiempo_permitido":TIEMPO_COMIDA_MAX}
        asistencias_db.append(reg)
    else: reg["tiempo_permitido"]=TIEMPO_COMIDA_MAX
    dias=["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]
    suc_id=empleados_db[eid].get("horario",{}).get(dias[ahora.weekday()],""); suc=sucursales_db.get(suc_id)
    def check_geocerca(lat_emp, lng_emp):
        if not suc: return True, 0
        s_lat=suc.get("lat"); s_lng=suc.get("lng"); radio=suc.get("radio",200)
        if s_lat is None or s_lng is None: return True, 0
        try: d=distancia_m(float(lat_emp), float(lng_emp), float(s_lat), float(s_lng)); return d <= float(radio), d
        except: return True,0
    if tipo=="entrada":
        if reg["entrada"]: raise HTTPException(400, "Ya entrada")
        retardo=0
        if suc:
            try: h,m=map(int,suc.get("hora_entrada","08:00").split(":")); ent=ahora.replace(hour=h,minute=m,second=0,microsecond=0); retardo=max(0, round((ahora-ent).total_seconds()/60,1))
            except: pass
        if lat and lng and suc and suc.get("lat"):
            ok, dist = check_geocerca(lat,lng)
            if not ok: alertas_db.append({"id":str(uuid.uuid4())[:6],"empleado_id":eid,"mensaje":f"🚨 Entrada FUERA de {suc.get('nombre')} - a {int(dist)}m","fecha":ahora.strftime("%Y-%m-%d %H:%M"),"tipo":"gps_fuera","distancia":dist,"lat":lat,"lng":lng})
        reg["entrada"]=hora; reg["retardo_entrada"]=retardo; reg["sucursal_id"]=suc_id
    elif tipo=="salida_comida":
        if not reg["entrada"]: raise HTTPException(400, "Primero entrada")
        if reg["salida_comida"]: raise HTTPException(400, "Ya salida comida")
        reg["salida_comida"]=hora
    elif tipo=="regreso_comida":
        if not reg["salida_comida"]: raise HTTPException(400, "Primero salida comida")
        if reg["regreso_comida"]: raise HTTPException(400, "Ya regreso")
        reg["regreso_comida"]=hora
        try:
            from datetime import datetime as dt
            sc = dt.strptime(reg["salida_comida"], "%H:%M:%S"); rc = dt.strptime(hora, "%H:%M:%S")
            diff_min = (rc - sc).total_seconds()/60
            if diff_min < 0: diff_min += 1440
            reg["min_comida"]=round(diff_min,1); reg["retardo_comida"]=round(diff_min - TIEMPO_COMIDA_MAX,1) if diff_min > TIEMPO_COMIDA_MAX else 0
        except: pass
    elif tipo=="salida_final":
        if not reg["regreso_comida"] and reg["salida_comida"]: raise HTTPException(400, "Primero regreso")
        if not reg["entrada"]: raise HTTPException(400, "Primero entrada")
        if reg["salida_final"]: raise HTTPException(400, "Ya salida final")
        reg["salida_final"]=hora; reg["firma"]=data.get("firma")
        try:
            from datetime import datetime as dt
            e = dt.strptime(reg["entrada"], "%H:%M:%S"); s = dt.strptime(hora, "%H:%M:%S")
            diff = (s - e).total_seconds()/3600
            if diff < 0: diff += 24
            if reg["salida_comida"] and reg["regreso_comida"]:
                sc = dt.strptime(reg["salida_comida"], "%H:%M:%S"); rc = dt.strptime(reg["regreso_comida"], "%H:%M:%S")
                comida = (rc - sc).total_seconds()/3600
                if comida < 0: comida += 24
                diff -= comida
            reg["horas_trabajadas"]=round(diff,2)
        except: pass
    else: raise HTTPException(400, "Tipo invalido")
    save_db(); return reg
@app.post("/gps/update")
def gps_update(data: dict):
    limpiar_gps_antiguo(); eid=data.get("empleado_id"); lat=data.get("lat"); lng=data.get("lng")
    if eid not in empleados_db: raise HTTPException(404)
    ahora=datetime.now(); hoy=ahora.strftime("%Y-%m-%d")
    reg = next((a for a in asistencias_db if a["empleado_id"]==eid and a["fecha_dia"]==hoy), None)
    if not reg or not reg.get("entrada") or reg.get("salida_final"): return {"ok":True}
    if reg.get("salida_comida") and not reg.get("regreso_comida"): return {"ok":True}
    dias=["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]
    suc_id=empleados_db[eid].get("horario",{}).get(dias[ahora.weekday()],""); suc=sucursales_db.get(suc_id)
    if not suc or not suc.get("lat"):
        gps_logs_db.append({"empleado_id":eid,"lat":lat,"lng":lng,"fecha":ahora.strftime("%Y-%m-%d %H:%M:%S"),"fecha_dia":hoy,"hora":ahora.strftime("%H:%M:%S"),"sucursal_id":suc_id}); save_db(); return {"ok":True,"dentro":True}
    try:
        dist=distancia_m(float(lat),float(lng),float(suc["lat"]),float(suc["lng"])); dentro=dist <= float(suc.get("radio",200))
        gps_logs_db.append({"empleado_id":eid,"lat":lat,"lng":lng,"distancia":round(dist,1),"dentro":dentro,"fecha":ahora.strftime("%Y-%m-%d %H:%M:%S"),"fecha_dia":hoy,"hora":ahora.strftime("%H:%M:%S"),"sucursal_id":suc_id,"empleado_nombre":empleados_db[eid]["nombre"]})
        if not dentro: alertas_db.append({"id":str(uuid.uuid4())[:6],"empleado_id":eid,"mensaje":f"🚨 GPS: {empleados_db[eid]['nombre']} se alejó {int(dist)}m de {suc.get('nombre')}","fecha":ahora.strftime("%Y-%m-%d %H:%M:%S"),"tipo":"gps_fuera","distancia":dist,"lat":lat,"lng":lng})
        save_db(); return {"ok":True,"dentro":dentro,"distancia":dist}
    except: return {"ok":False}
@app.get("/gps/ruta/{eid}")
def gps_ruta(eid: str, dias: int = 60):
    limpiar_gps_antiguo(); limite = datetime.now() - timedelta(days=dias)
    logs = [g for g in gps_logs_db if g["empleado_id"]==eid]
    def f_reciente(f_str):
        try: return datetime.strptime(f_str, "%Y-%m-%d %H:%M:%S") >= limite
        except: return True
    logs = [l for l in logs if f_reciente(l.get("fecha",""))]
    por_dia={}
    for l in logs:
        d=l.get("fecha_dia","sin_fecha")
        if d not in por_dia: por_dia[d]=[]
        por_dia[d].append(l)
    return {"empleado_id":eid,"dias_guardados":dias,"total_puntos":len(logs),"ruta_por_dia":por_dia,"logs":logs[::-1][:500]}
@app.get("/gps/ruta-todos")
def gps_ruta_todos(dias: int = 60):
    limpiar_gps_antiguo(); limite = datetime.now() - timedelta(days=dias)
    def f_reciente(f_str):
        try: return datetime.strptime(f_str, "%Y-%m-%d %H:%M:%S") >= limite
        except: return True
    logs=[l for l in gps_logs_db if f_reciente(l.get("fecha",""))]
    return {"dias_guardados":dias,"total_puntos":len(logs),"logs":logs[::-1][:500]}
@app.get("/gps/export-csv/{eid}")
def export_csv(eid: str, dias: int = 60):
    import csv, io; limite = datetime.now() - timedelta(days=dias)
    logs=[g for g in gps_logs_db if g["empleado_id"]==eid and datetime.strptime(g.get("fecha","2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S") >= limite]
    output=io.StringIO(); writer=csv.writer(output); writer.writerow(["empleado_id","nombre","fecha","hora","fecha_dia","lat","lng","distancia_m","dentro_geocerca","sucursal"])
    for l in logs: writer.writerow([l.get("empleado_id"),l.get("empleado_nombre",""),l.get("fecha"),l.get("hora",""),l.get("fecha_dia"),l.get("lat"),l.get("lng"),l.get("distancia",""),l.get("dentro",""),l.get("sucursal_id","")])
    return {"empleado_id":eid,"dias":dias,"csv":output.getvalue(),"filename":f"ruta_{eid}_{dias}dias.csv"}
@app.get("/gps/alertas")
def gps_alertas(): return [a for a in alertas_db if a.get("tipo")=="gps_fuera"][::-1]
@app.post("/evaluaciones")
def crear_eval(data: dict):
    hoy=datetime.now(); eid=data.get("empleado_id"); cals=data.get("calificaciones",{}); total=0
    for i in range(1,12):
        if i in [6,12]: continue
        try: v=int(cals.get(str(i),0))
        except: v=0
        total+=v
    mes=hoy.strftime("%Y-%m")
    if any(ev["empleado_id"]==eid and ev["mes"]==mes for ev in evaluaciones_db): raise HTTPException(400, "Ya evaluado")
    nivel="Necesita Mejorar"
    if total==100: nivel="EXCELENTE 🌟"
    elif total>=90: nivel="Muy Bueno"
    elif total>=80: nivel="Bueno"
    nueva={"id":len(evaluaciones_db)+1,"empleado_id":eid,"empleado_nombre":empleados_db[eid]["nombre"],"fecha":hoy.strftime("%Y-%m-%d %H:%M"),"mes":mes,"calificaciones":cals,"total":total,"nivel":nivel,"firma":data.get("firma")}
    evaluaciones_db.append(nueva); save_db(); return nueva
@app.get("/evaluaciones")
def list_ev(): return evaluaciones_db
@app.get("/empleado/{eid}/historial")
def hist(eid: str): return [e for e in evaluaciones_db if e["empleado_id"]==eid]
@app.get("/alertas/{eid}")
def al(eid: str): return [a for a in alertas_db if a["empleado_id"]==eid or eid=="admin"][::-1][:50]
@app.get("/asistencias/{eid}")
def asis(eid: str): return [a for a in asistencias_db if a["empleado_id"]==eid][::-1]
@app.get("/empleado/{eid}/retardos-mes")
def retardos_mes(eid: str):
    mes=datetime.now().strftime("%Y-%m")
    asist=[a for a in asistencias_db if a["empleado_id"]==eid and a.get("fecha","")==mes]
    total_entrada=sum([a.get("retardo_entrada",0) for a in asist]); total_comida=sum([a.get("retardo_comida",0) for a in asist]); total_horas=round(sum([a.get("horas_trabajadas",0) for a in asist]),2)
    retardos=[]
    for a in asist:
        if a.get("retardo_entrada",0)>0 or a.get("retardo_comida",0)>0:
            retardos.append({"fecha_dia":a.get("fecha_dia"),"entrada":a.get("entrada"),"retardo_entrada":a.get("retardo_entrada",0),"salida_comida":a.get("salida_comida"),"regreso_comida":a.get("regreso_comida"),"min_comida":a.get("min_comida",0),"tiempo_permitido":a.get("tiempo_permitido",120),"retardo_comida":a.get("retardo_comida",0)})
    return {"empleado_id":eid,"mes":mes,"total_retardo_entrada":round(total_entrada,1),"total_retardo_comida":round(total_comida,1),"total_retardos":round(total_entrada+total_comida,1),"total_horas":total_horas,"detalles":retardos,"asistencias":asist}
@app.get("/admin/retardos-todos")
def retardos_todos():
    mes=datetime.now().strftime("%Y-%m"); result=[]
    for eid, emp in empleados_db.items():
        if emp.get("eliminado"): continue
        asist=[a for a in asistencias_db if a["empleado_id"]==eid and a.get("fecha","")==mes]
        if len(asist)>0:
            total_e=sum([a.get("retardo_entrada",0) for a in asist]); total_c=sum([a.get("retardo_comida",0) for a in asist])
            result.append({"empleado_id":eid,"nombre":emp.get("nombre"),"total_entrada":round(total_e,1),"total_comida":round(total_c,1),"total":round(total_e+total_c,1),"dias_trabajados":len(asist),"horas_mes":round(sum([a.get("horas_trabajadas",0) for a in asist]),1)})
    return sorted(result, key=lambda x: x["total"], reverse=True)
@app.get("/admin/export-excel")
def export_excel():
    import csv, io; output=io.StringIO(); writer=csv.writer(output); writer.writerow(["empleado_id","nombre","mes","fecha_dia","entrada","retardo_entrada","salida_comida","regreso_comida","min_comida","retardo_comida","salida_final","horas_trabajadas","horas_extra","sucursal"])
    mes=datetime.now().strftime("%Y-%m")
    for a in asistencias_db:
        if mes in a.get("fecha",""):
            emp=empleados_db.get(a["empleado_id"],{}); horas=a.get("horas_trabajadas",0); extra=round(horas-8,2) if horas>8 else 0
            writer.writerow([a["empleado_id"],emp.get("nombre",""),a.get("fecha"),a.get("fecha_dia"),a.get("entrada"),a.get("retardo_entrada"),a.get("salida_comida"),a.get("regreso_comida"),a.get("min_comida"),a.get("retardo_comida"),a.get("salida_final"),a.get("horas_trabajadas"),extra,a.get("sucursal_id")])
    return {"csv":output.getvalue(),"filename":f"nomina_{mes}.csv"}
@app.get("/admin/audit")
def audit_get(): return audit_db[::-1][:100]
@app.get("/admin/papelera")
def papelera(): return [e for e in empleados_db.values() if e.get("eliminado")]

@app.post("/reportes-volanteo")
def crear_reporte_volanteo(data: dict):
    rep={
        "id": str(uuid.uuid4())[:8],
        "empleado_id": data.get("empleado_id"),
        "nombre": empleados_db.get(data.get("empleado_id"),{}).get("nombre",""),
        "sucursal_id": data.get("sucursal_id"),
        "sucursal_nombre": sucursales_db.get(data.get("sucursal_id"),{}).get("nombre", data.get("sucursal_id","")),
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fecha_dia": datetime.now().strftime("%Y-%m-%d"),
        "manana_volantearon": data.get("manana_volantearon",""),
        "manana_quien": data.get("manana_quien",""),
        "manana_nombre": data.get("manana_nombre",""),
        "tarde_volantearon": data.get("tarde_volantearon",""),
        "tarde_quien": data.get("tarde_quien",""),
        "tarde_nombre": data.get("tarde_nombre",""),
        "comentario": data.get("comentario","")
    }
    reportes_volanteo_db.append(rep)
    save_db()
    return rep

@app.get("/reportes-volanteo")
def list_reportes_volanteo():
    return reportes_volanteo_db[::-1]

@app.get("/reportes-volanteo/{eid}")
def list_reportes_volanteo_emp(eid: str):
    return [r for r in reportes_volanteo_db if r["empleado_id"]==eid][::-1]

@app.get("/admin/compañeros-hoy/{suc_id}")

def companeros_hoy(suc_id: str):
    hoy=datetime.now().strftime("%Y-%m-%d"); dias=["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]; dia_hoy=dias[datetime.now().weekday()]; trabajando=[]
    for eid, emp in empleados_db.items():
        if not emp.get("activo") or emp.get("eliminado"): continue
        hor=emp.get("horario",{}).get(dia_hoy,"")
        if hor==suc_id or suc_id in emp.get("sucursales_ids",[]):
            asist=next((a for a in asistencias_db if a["empleado_id"]==eid and a["fecha_dia"]==hoy), None)
            trabajando.append({"id":eid,"nombre":emp.get("nombre"),"puesto":emp.get("puesto"),"entrada":asist.get("entrada") if asist else None,"estado":"presente" if asist and asist.get("entrada") else "ausente"})
    return trabajando

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
<div class="sidebar-item" onclick="switchTab('tab-asignaciones-flex')"><span>🗓️</span> Asignar Día/Sem/Mes</div>
<div class="sidebar-item" onclick="switchTab('tab-tareas')"><span>✅</span> Tareas por Sucursal</div>
<div class="sidebar-item" onclick="switchTab('tab-horas-extra')"><span>⏰</span> Horas Extra</div>
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
<div class="card" id="card-crear-empleado"><h3>👤 Nuevo Empleado + Rol + WhatsApp</h3><div style="background:#10b98115;padding:8px;border-radius:10px"><small>Próximo: <b id="next-id" style="color:#10b981">...</b></small></div><div style="display:flex;gap:8px"><input id="emp_id" class="input" readonly><button class="btn btn-dark" style="width:auto;margin-top:8px" onclick="generarID()">🔄</button></div><input id="emp_nombre" class="input" placeholder="Nombre *"><input id="emp_puesto" class="input" placeholder="Puesto"><select id="emp_rol" class="input"><option value="empleado">👷 Empleado</option><option value="supervisor">👁️ Supervisor</option><option value="rh">📋 RH</option><option value="gerente">🏢 Gerente</option><option value="admin">👑 Admin</option></select><input id="emp_telefono" class="input" placeholder="WhatsApp con código país ej 521... *"><div style="display:flex;gap:8px"><input id="emp_sueldo" class="input" type="number" placeholder="Sueldo por hora $" value="50"><input id="emp_pass" class="input" placeholder="Contraseña *"></div><div style="display:flex;gap:8px;align-items:center;margin-top:8px"><label style="font-size:12px;min-width:80px">Comida:</label><input id="emp_comida" class="input" type="number" value="120" style="margin-top:0"><span>min</span></div><div id="check-suc" style="background:#0f172a;border-radius:10px;padding:8px;margin-top:8px;max-height:80px;overflow:auto"></div><div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px"><select id="d-lunes" class="input"></select><select id="d-martes" class="input"></select><select id="d-miercoles" class="input"></select><select id="d-jueves" class="input"></select><select id="d-viernes" class="input"></select><select id="d-sabado" class="input"></select><select id="d-domingo" class="input"></select></div><button class="btn btn-success" onclick="crearEmp()">💾 Guardar Empleado</button></div>
<div class="card"><h3>📋 Lista Empleados</h3><div id="list-emp" style="margin-top:10px"></div></div>
</div>

<div id="tab-sucursales" class="tab-content">
<div class="card"><h3>🏢 Nueva Sucursal con GPS</h3><input id="suc_id" class="input" placeholder="ID Sucursal"><input id="suc_nombre" class="input" placeholder="Nombre"><input id="suc_dir" class="input" placeholder="Dirección"><div class="grid2"><input id="suc_he" class="input" type="time" value="08:00"><input id="suc_hs" class="input" type="time" value="18:00"></div><div class="grid2"><input id="suc_lat" class="input" placeholder="Latitud"><input id="suc_lng" class="input" placeholder="Longitud"></div><div style="display:flex;gap:8px;align-items:center"><input id="suc_radio" class="input" type="number" value="200" placeholder="Radio metros"><button class="btn btn-dark" onclick="obtenerGPS()" style="width:auto;margin-top:8px">📍 Mi GPS</button></div><button class="btn btn-primary" onclick="crearSuc()">🏢 Crear Sucursal</button></div>
<div class="card"><h3>📍 Sucursales</h3><div id="list-suc"></div></div>
</div>

<div id="tab-asignaciones-flex" class="tab-content">
<div class="card" style="border:1px solid #6366f1"><h3>🗓️ Admin asigna sucursal por DÍA / SEMANA / MES (BONITA + agregado)</h3><p style="font-size:11px;color:var(--muted)">BONITA conservada 100%. Asigna dónde le toca al empleado. Prioridad: DÍA > SEMANA > MES > Base.</p>
<label>Tipo</label><select id="flex_tipo" class="input" onchange="cambiarFlexTipo()"><option value="dia">📅 DÍA específico</option><option value="semana" selected>🗓️ SEMANA (lun-dom diferente)</option><option value="mes">📆 MES completo</option></select>
<label>Empleado *</label><select id="flex_emp" class="input"><option value="">Cargando empleados...</option></select>
<button class="btn btn-dark" style="width:auto;padding:6px 10px;margin-top:6px" onclick="cargarFlexEmpsSucs()">🔄 Recargar empleados y sucursales</button>
<div id="flex-box-dia" style="display:none;background:var(--bg);padding:12px;border-radius:12px;margin-top:8px"><label>Fecha</label><input id="flex_fecha" class="input" type="date"><label>Sucursal</label><select id="flex_suc_dia" class="input"></select><button class="btn btn-primary" onclick="guardarFlexDia()">💾 Guardar DÍA</button><button id="btn_edit_dia" class="btn" style="display:none;margin-top:6px;background:#f59e0b" onclick="actualizarFlexDia()">✏️ Actualizar DÍA</button><button id="btn_cancel_dia" class="btn btn-dark" style="display:none;margin-top:6px" onclick="cancelarFlexEdicion()">❌ Cancelar</button></div>
<div id="flex-box-semana" style="background:var(--bg);padding:12px;border-radius:12px;margin-top:8px"><label>Semana (año-semana)</label><input id="flex_semana" class="input" type="week"><div style="display:grid;grid-template-columns:1fr 1fr;gap:6px"><div><label>Lun</label><select id="flex_lun" class="input"></select></div><div><label>Mar</label><select id="flex_mar" class="input"></select></div><div><label>Mié</label><select id="flex_mie" class="input"></select></div><div><label>Jue</label><select id="flex_jue" class="input"></select></div><div><label>Vie</label><select id="flex_vie" class="input"></select></div><div><label>Sáb</label><select id="flex_sab" class="input"></select></div><div><label>Dom</label><select id="flex_dom" class="input"></select></div></div><button class="btn btn-primary" onclick="guardarFlexSemana()">💾 Guardar SEMANA</button><button id="btn_edit_sem" class="btn" style="display:none;margin-top:6px;background:#f59e0b" onclick="actualizarFlexSemana()">✏️ Actualizar SEMANA</button><button id="btn_cancel_sem" class="btn btn-dark" style="display:none;margin-top:6px" onclick="cancelarFlexEdicion()">❌ Cancelar</button></div>
<div id="flex-box-mes" style="display:none;background:var(--bg);padding:12px;border-radius:12px;margin-top:8px"><label>Mes</label><input id="flex_mes" class="input" type="month"><label>Sucursal mes</label><select id="flex_suc_mes" class="input"></select><button class="btn btn-primary" onclick="guardarFlexMes()">💾 Guardar MES</button><button id="btn_edit_mes" class="btn" style="display:none;margin-top:6px;background:#f59e0b" onclick="actualizarFlexMes()">✏️ Actualizar MES</button><button id="btn_cancel_mes" class="btn btn-dark" style="display:none;margin-top:6px" onclick="cancelarFlexEdicion()">❌ Cancelar</button></div>
<p id="flex-msg" style="font-size:11px;color:#10b981;margin-top:8px"></p>
<input type="hidden" id="flex_edit_id">
</div>
<div class="card"><h3>📋 Asignaciones actuales (editar / eliminar)</h3><div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px"><button class="btn btn-dark" style="width:auto" onclick="cargarFlexAsignaciones('')">TODO</button><button class="btn btn-dark" style="width:auto" onclick="cargarFlexAsignaciones('dia')">DÍA</button><button class="btn btn-dark" style="width:auto" onclick="cargarFlexAsignaciones('semana')">SEMANA</button><button class="btn btn-dark" style="width:auto" onclick="cargarFlexAsignaciones('mes')">MES</button><select id="filtro_flex_emp" class="input" style="width:auto" onchange="filtrarFlex()"><option value="">Filtrar empleado</option></select></div><div id="flex-lista" style="margin-top:12px;max-height:700px;overflow:auto"></div></div>
</div>

<div id="tab-retardos" class="tab-content"><div class="card"><h3>⏱️ Retardos del Mes</h3><div id="retardos-admin"></div></div></div>
<div id="tab-tareas" class="tab-content">
<div class="card" style="border:2px solid #f59e0b"><h3>✅ Check-list de tareas por sucursal (NUEVO BONITA+)</h3><p style="font-size:11px;color:var(--muted)">Cada sucursal tiene sus tareas del día, empleado las palomea al hacer check.</p>
<label>Sucursal</label><select id="tarea_suc" class="input"></select><label>Tarea</label><input id="tarea_txt" class="input" placeholder="Ej: Abrir caja, limpiar, inventario"><button class="btn btn-primary" onclick="crearTarea()">➕ Agregar tarea</button><div id="tareas-lista" style="margin-top:12px"></div></div>
</div>
<div id="tab-horas-extra" class="tab-content"><div class="card" style="border:2px solid #ec4899"><h3>⏰ Horas extra automáticas (NUEVO)</h3><p style="font-size:11px">Si checa salida después de horario, se calcula solo como hora extra.</p><div id="horas-extra-lista"></div><button class="btn btn-dark" onclick="cargarHorasExtra()">🔄 Cargar horas extra</button></div></div>

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
<div class="card" style="border:2px solid #8b5cf6"><h3>👤 Mi Perfil + Foto</h3><div style="display:flex;gap:12px;align-items:center"><img id="emp_foto_preview" src="" style="width:80px;height:80px;border-radius:50%;background:#334155;object-fit:cover;display:none"><div><input type="file" id="emp_foto_input" accept="image/*" class="input" style="font-size:11px"><button class="btn btn-primary" onclick="subirFotoPerfil()" style="width:auto;padding:6px 12px;font-size:11px;margin-top:6px">📸 Subir</button></div></div><div id="emp-perfil-info" style="margin-top:12px;font-size:12px;background:#0f172a;border-radius:12px;padding:12px"></div></div>
<div class="card"><h3>🔑 Seguridad</h3><input id="old_pass" class="input" type="password" placeholder="Actual"><input id="new_pass" class="input" type="password" placeholder="Nueva"><button class="btn btn-primary" onclick="cambiarPassword()">🔑 Cambiar</button><p id="msg-pass" style="font-size:11px;margin-top:8px"></p></div>
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
    localStorage.setItem('sesion_activa','true'); localStorage.setItem('user_id',USER_ID); localStorage.setItem('rol',ROL); localStorage.setItem('nombre',nombre); localStorage.setItem('empresa_nombre',empresaNom);
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
async function crearEmp(){const id=document.getElementById('emp_id').value; const nombre=document.getElementById('emp_nombre').value; const puesto=document.getElementById('emp_puesto').value; const rol=document.getElementById('emp_rol')?.value||'empleado'; const pass=document.getElementById('emp_pass').value; const telefono=document.getElementById('emp_telefono')?.value||''; const sueldo=parseFloat(document.getElementById('emp_sueldo')?.value)||50; const comida=parseInt(document.getElementById('emp_comida').value)||120; if(!nombre||!pass) return alert('Nombre y contraseña'); if(!telefono) return alert('Telefono obligatorio'); const suc=[...document.querySelectorAll('.chk:checked')].map(c=>c.value); const hor={lunes:document.getElementById('d-lunes').value,martes:document.getElementById('d-martes').value,miercoles:document.getElementById('d-miercoles').value,jueves:document.getElementById('d-jueves').value,viernes:document.getElementById('d-viernes').value,sabado:document.getElementById('d-sabado').value,domingo:document.getElementById('d-domingo').value}; const r=await api('/empleados','POST',{id,nombre,puesto,rol,password:pass,telefono,sueldo_hora:sueldo,tiempo_comida:comida,sucursales_ids:suc,horario:hor,activo:true}); alert(`✅ ${r.id} ${nombre} rol ${rol}`); document.getElementById('emp_nombre').value=''; document.getElementById('emp_pass').value=''; document.getElementById('emp_telefono').value=''; generarID(); cargarEmps();}
async function cargarEmps(){const emps=await api('/empleados'); const activos=emps.filter(e=>!e.eliminado); document.getElementById('list-emp').innerHTML=activos.map(e=>`<div style="background:#0f172a;padding:12px;border-radius:12px;margin-top:8px;font-size:11px;display:flex;justify-content:space-between;align-items:center;border-left:4px solid ${e.activo?'#10b981':'#ef4444'}"><div><b>${e.id} - ${e.nombre}</b> - ${e.puesto||''} - ${e.rol||'empleado'}<br>📱 ${e.telefono||''} - 💰 $${e.sueldo_hora||50}/h - ${e.activo?'✅ Activo':'❌ Inactivo'}</div><div style="display:flex;gap:6px"><button onclick="abrirEditar('${e.id}')" style="padding:6px 10px;border-radius:8px;border:none;background:#6366f1;color:white;font-size:11px">✏️</button><button onclick="toggleEmp('${e.id}')" style="padding:6px 10px;border-radius:8px;border:none;background:${e.activo?'#ef4444':'#10b981'};color:white;font-size:11px">${e.activo?'Desactivar':'Activar'}</button></div></div>`).join('')||'Sin empleados'; document.getElementById('eval_emp').innerHTML=activos.map(e=>`<option value="${e.id}">${e.id} - ${e.nombre}</option>`).join(''); document.getElementById('chat_para').innerHTML=activos.map(e=>`<option value="${e.id}">${e.id} - ${e.nombre}</option>`).join(''); document.getElementById('ruta_emp').innerHTML=activos.map(e=>`<option value="${e.id}">${e.id} - ${e.nombre}</option>`).join('');}
function abrirEditar(id){api('/empleados').then(emps=>{const e=emps.find(x=>x.id===id); if(!e) return; EDITANDO_ID=id; document.getElementById('edit_id').value=e.id; document.getElementById('edit_nombre').value=e.nombre||''; document.getElementById('edit_puesto').value=e.puesto||''; document.getElementById('edit_telefono').value=e.telefono||''; document.getElementById('edit_comida').value=e.tiempo_comida||120; document.getElementById('edit_activo').value=e.activo?'true':'false'; document.getElementById('modal-edit').style.display='flex';});}
function cerrarModal(){document.getElementById('modal-edit').style.display='none';}
async function guardarEdicion(){const data={nombre:document.getElementById('edit_nombre').value,puesto:document.getElementById('edit_puesto').value,telefono:document.getElementById('edit_telefono').value,tiempo_comida:parseInt(document.getElementById('edit_comida').value)||120,activo:document.getElementById('edit_activo').value==='true'}; const pass=document.getElementById('edit_password').value; if(pass) data.password=pass; await api('/empleados/'+EDITANDO_ID,'PUT',data); alert('✅ Actualizado'); cerrarModal(); cargarEmps();}
async function eliminarEmpleado(){if(!confirm('¿Enviar a papelera?')) return; await fetch('/empleados/'+EDITANDO_ID,{method:'DELETE'}); cerrarModal(); cargarEmps();}
async function toggleEmp(id){await api('/empleados/'+id+'/toggle','PUT'); cargarEmps();}
async function cargarTodo(){await cargarSucs(); await generarID(); await cargarEmps(); renderPreguntas(); cargarDashboard(); cargarRetardosAdmin(); cargarGPSAlertas(); cargarVacacionesAdmin(); cargarJustificantesAdmin(); cargarPanico(); cargarChatAdmin(); cargarGraficas(); cargarConfigAdmin(); cargarAntiTrampa(); cargarPermisos(); const now=new Date().toISOString().slice(0,7); if(document.getElementById('nomina_mes')) document.getElementById('nomina_mes').value=now; if(document.getElementById('rep_suc_mes')) document.getElementById('rep_suc_mes').value=now;}
function renderPreguntas(){const div=document.getElementById('eval_preguntas'); if(!div) return; div.innerHTML=PREG.map(q=>{if(q.tipo==='cal') return `<div style="background:#0f172a;padding:10px;border-radius:12px;margin-top:8px"><label>${q.id}. ${q.txt}</label><select data-id="${q.id}" class="input sel-cal" onchange="calcTotal()"><option value="0">0</option><option>1</option><option>2</option><option>3</option><option>4</option><option>5</option><option>6</option><option>7</option><option>8</option><option>9</option><option selected>10</option></select></div>`; else return `<div style="background:#0f172a;padding:10px;border-radius:12px;margin-top:8px"><label>${q.id}. ${q.txt}</label><textarea data-id="${q.id}" class="input" rows="2"></textarea></div>`;}).join(''); calcTotal();}
function calcTotal(){let t=0; document.querySelectorAll('.sel-cal').forEach(s=>t+=parseInt(s.value||0)); const b=document.getElementById('total-preview'); if(b){b.style.display='block'; document.getElementById('total-num').innerText=t+'/100';}}
async function evaluar(){const eid=document.getElementById('eval_emp').value; const cals={}; document.querySelectorAll('[data-id]').forEach(el=>cals[el.dataset.id]=el.value); try{const r=await api('/evaluaciones','POST',{empleado_id:eid,calificaciones:cals}); document.getElementById('msg-eval').innerText=`✅ ${r.total}/100`; }catch(e){document.getElementById('msg-eval').innerText='❌ '+(e.detail||'Error');}}
async function cargarDashboard(){try{const d=await api('/admin/dashboard'); document.getElementById('kpi-row').innerHTML=`<div class="kpi"><b style="color:#10b981">${d.presentes_hoy}</b><small>Presentes Hoy</small></div><div class="kpi"><b style="color:#ef4444">${d.ausentes_hoy}</b><small>Ausentes</small></div><div class="kpi"><b style="color:#f59e0b">${d.retardos_hoy}</b><small>Retardos Hoy</small></div><div class="kpi"><b style="color:#6366f1">${d.horas_mes}h</b><small>Horas Mes</small></div>`; document.getElementById('ranking-puntual').innerHTML=d.ranking.map((r,i)=>`<div style="display:flex;justify-content:space-between;background:#0f172a;padding:10px;border-radius:10px;margin-top:6px"><span>${i+1}. ${r.nombre} - ${r.id}</span><span style="color:${r.retardos>0?'#ef4444':'#10b981'}">${r.retardos} min | ${r.dias} días | ${r.horas}h</span></div>`).join('') || 'Sin datos'; cargarMemoriaDB();}catch(e){}}
async function cargarMemoriaDB(){try{const db=await api('/api/db-status'); const usado=db.empleados+' empleados'; document.getElementById('db-progress-bar').style.width='10%'; document.getElementById('db-usado-text').innerText='Empleados: '+db.empleados; document.getElementById('db-libre-text').innerText='DB: '+db.tipo; document.getElementById('mem-porcentaje').innerText=db.tipo;}catch(e){}}
async function cargarGraficas(){try{const data=await api('/admin/reportes-graficas'); const ctx1=document.getElementById('chart-retardos'); if(ctx1){ if(chartRet) chartRet.destroy(); chartRet=new Chart(ctx1,{type:'bar',data:{labels:data.retardos_por_dia.labels, datasets:[{label:'Min retardos', data:data.retardos_por_dia.valores, backgroundColor:'#6366f1'}]},options:{responsive:true, plugins:{legend:{display:false}}}});} const ctx2=document.getElementById('chart-horas'); if(ctx2){ if(chartHoras) chartHoras.destroy(); chartHoras=new Chart(ctx2,{type:'doughnut',data:{labels:data.horas_por_empleado.labels, datasets:[{data:data.horas_por_empleado.valores, backgroundColor:['#10b981','#6366f1','#f59e0b','#ef4444','#0ea5e9','#8b5cf6']}]},options:{responsive:true}});} }catch(e){}}
async function exportarExcel(){const data=await api('/admin/export-excel'); const blob=new Blob([data.csv],{type:'text/csv'}); const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download=data.filename; a.click();}
async function exportarPDF(){const {jsPDF}=window.jspdf; const doc=new jsPDF(); doc.setFontSize(16); doc.text('Clock RD - Reporte',10,15); const data=await api('/admin/retardos-todos'); let y=25; data.forEach(r=>{ doc.text(`${r.empleado_id} ${r.nombre} - ${r.total} min - ${r.horas_mes}h`,10,y); y+=7; if(y>270){doc.addPage(); y=15;}}); doc.save('reporte.pdf');}
async function hacerBackup(){try{const data=await api('/admin/backup'); const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'}); const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download='backup_'+data.fecha.replace(/[: ]/g,'-')+'.json'; a.click(); document.getElementById('backup-result').style.display='block'; document.getElementById('backup-result').innerHTML=`✅ Backup ${data.fecha}<br>Empleados: ${data.total_empleados}`;}catch(e){alert('Error backup');}}
async function cargarAudit(){const data=await api('/admin/audit'); const html=data.map(a=>`${a.fecha} - ${a.usuario} - ${a.accion} - ${a.detalle}`).join('<br>'); document.getElementById('audit-result').style.display='block'; document.getElementById('audit-result').innerHTML=html; const el2=document.getElementById('audit-result2'); if(el2){el2.style.display='block'; el2.innerHTML=html;}}
async function cargarGPSAlertas(){try{const alertas=await api('/gps/alertas'); document.getElementById('gps-alertas').innerHTML=alertas.slice(0,20).map(a=>`<div style="background:#ef444415;border:1px solid #ef4444;border-radius:12px;padding:10px;margin-top:8px;font-size:11px"><b style="color:#ef4444">🚨 ${a.empleado_id}</b> - ${a.mensaje}<br><small>${a.fecha}</small> - <a href="https://www.google.com/maps?q=${a.lat},${a.lng}" target="_blank" style="color:#60a5fa">Maps</a></div>`).join('') || 'Sin alertas';}catch(e){}}
async function cargarRetardosAdmin(){try{const data=await api('/admin/retardos-todos'); document.getElementById('retardos-admin').innerHTML=data.map(r=>`<div style="background:#0f172a;padding:12px;border-radius:12px;margin-top:8px;display:flex;justify-content:space-between;align-items:center;border-left:4px solid ${r.total>0?'#ef4444':'#10b981'}"><div style="font-size:12px"><b style="color:#10b981">${r.empleado_id}</b> - <b>${r.nombre}</b><br>Entrada: <span style="color:${r.total_entrada>0?'#ef4444':'#10b981'}">${r.total_entrada} min</span> | Comida: <span style="color:${r.total_comida>0?'#f59e0b':'#10b981'}">${r.total_comida} min</span> | Total: <b style="color:#ef4444">${r.total} min</b> | Horas: ${r.horas_mes}h</div></div>`).join('') || 'Sin';}catch(e){}}
async function cargarVacacionesAdmin(){try{const vac=await api('/vacaciones'); document.getElementById('vac-admin').innerHTML=vac.slice(0,10).map(v=>`<div style="background:#0f172a;padding:10px;border-radius:12px;margin-top:8px;font-size:11px;border-left:4px solid ${v.estado=='pendiente'?'#f59e0b':v.estado=='aprobado'?'#10b981':'#ef4444'}"><b>${v.empleado_id} ${v.nombre||''}</b> - ${v.tipo}<br>${v.fecha_inicio} al ${v.fecha_fin} - ${v.motivo}<br>Estado: <b>${v.estado.toUpperCase()}</b><br><div style="display:flex;gap:6px;margin-top:6px"><button onclick="responderVac('${v.id}','aprobado')" style="padding:6px 10px;border-radius:8px;border:none;background:#10b981;color:white;font-size:11px">✅ Aprobar</button><button onclick="responderVac('${v.id}','rechazado')" style="padding:6px 10px;border-radius:8px;border:none;background:#ef4444;color:white;font-size:11px">❌ Rechazar</button></div></div>`).join('') || 'Sin';}catch(e){}}
async function responderVac(id,estado){await api('/vacaciones/'+id+'/estado','PUT',{estado:estado}); cargarVacacionesAdmin();}
async function cargarJustificantesAdmin(){try{const just=await api('/justificantes'); document.getElementById('just-admin').innerHTML=just.slice(0,10).map(j=>`<div style="background:#0f172a;padding:10px;border-radius:12px;margin-top:8px;font-size:11px;border-left:4px solid ${j.estado=='pendiente'?'#f59e0b':j.estado=='aprobado'?'#10b981':'#ef4444'}"><b>${j.empleado_id} ${j.nombre||''}</b> - ${j.tipo} - ${j.fecha}<br>${j.motivo}<br>Estado: <b>${j.estado.toUpperCase()}</b><br><div style="display:flex;gap:6px;margin-top:6px"><button onclick="responderJust('${j.id}','aprobado')" style="padding:6px 10px;border-radius:8px;border:none;background:#10b981;color:white;font-size:11px">✅ Aprobar</button><button onclick="responderJust('${j.id}','rechazado')" style="padding:6px 10px;border-radius:8px;border:none;background:#ef4444;color:white;font-size:11px">❌ Rechazar</button></div></div>`).join('') || 'Sin';}catch(e){}}
async function responderJust(id,estado){await api('/justificantes/'+id+'/estado','PUT',{estado:estado}); cargarJustificantesAdmin();}
async function cargarPanico(){try{const p=await api('/panico/todos'); document.getElementById('panico-admin').innerHTML=p.slice(0,10).map(a=>`<div style="background:#ef4444;color:white;border-radius:12px;padding:12px;margin-top:8px;font-size:12px"><b>🆘 SOS ${a.empleado_id} ${a.nombre}</b><br>${a.mensaje}<br>${a.fecha}<br><a href="https://www.google.com/maps?q=${a.lat},${a.lng}" target="_blank" style="color:white;text-decoration:underline">📍 Ver ubicación</a></div>`).join('') || 'Sin SOS ✅';}catch(e){}}
async function cargarChatAdmin(){try{const c=await api('/chat'); document.getElementById('chat-admin-list').innerHTML=c.slice(-20).map(m=>`<div style="margin-top:6px"><b>${m.de} → ${m.para}:</b> ${m.mensaje} <small style="color:#94a3b8">${m.fecha}</small></div>`).join('') || 'Sin mensajes';}catch(e){}}
async function enviarChatAdmin(){const para=document.getElementById('chat_para').value; const msg=document.getElementById('chat_msg').value; if(!para||!msg) return alert('Selecciona y escribe'); await api('/chat/enviar','POST',{de:'admin',para:para,mensaje:msg}); document.getElementById('chat_msg').value=''; cargarChatAdmin();}
async function verRuta(){const eid=document.getElementById('ruta_emp').value; const data=await api('/gps/ruta/'+eid+'?dias=60'); let html=`<b>📍 Ruta ${eid} - ${data.total_puntos} puntos</b><br><br>`; for(const dia in data.ruta_por_dia){html+=`<div style="background:#1e293b;border-radius:12px;padding:10px;margin-top:8px"><b>${dia} - ${data.ruta_por_dia[dia].length} puntos</b><br>`+data.ruta_por_dia[dia].map(p=>`${p.hora} - ${p.lat.toFixed(5)},${p.lng.toFixed(5)} - ${p.dentro?'✅':'❌'} - <a href="https://www.google.com/maps?q=${p.lat},${p.lng}" target="_blank" style="color:#60a5fa">Maps</a>`).join('<br>')+`</div>`;} if(!Object.keys(data.ruta_por_dia).length) html+='Sin ruta'; document.getElementById('ruta-result').innerHTML=html;}
async function verRutaTodos(){const data=await api('/gps/ruta-todos?dias=60'); document.getElementById('ruta-result').innerHTML=`<b>🗺️ Todos - ${data.total_puntos} puntos</b><br><br>`+data.logs.slice(0,100).map(l=>`${l.fecha} - ${l.empleado_id} - ${l.lat.toFixed(5)},${l.lng.toFixed(5)} - <a href="https://www.google.com/maps?q=${l.lat},${l.lng}" target="_blank" style="color:#60a5fa">Maps</a>`).join('<br>') || 'Sin';}
async function exportarCSV(){const eid=document.getElementById('ruta_emp').value; const data=await api('/gps/export-csv/'+eid+'?dias=60'); const blob=new Blob([data.csv],{type:'text/csv'}); const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download=data.filename; a.click();}
async function guardarConfigAdmin(){const data={telefono_admin:document.getElementById('conf_tel_admin').value,bono_puntualidad:parseFloat(document.getElementById('conf_bono').value)||500,sueldo_default:parseFloat(document.getElementById('conf_sueldo_default').value)||50,whatsapp_activo:document.getElementById('conf_whatsapp_activo').checked}; try{await api('/api/config-admin','POST',data); document.getElementById('msg-conf-admin').innerText='✅ Guardada'; localStorage.setItem('admin_tel',data.telefono_admin);}catch(e){document.getElementById('msg-conf-admin').innerText='❌ '+(e.detail||'Error');}}
async function cargarConfigAdmin(){try{const c=await api('/api/config-admin'); if(document.getElementById('conf_tel_admin')){document.getElementById('conf_tel_admin').value=c.telefono_admin||''; document.getElementById('conf_bono').value=c.bono_puntualidad||500; document.getElementById('conf_sueldo_default').value=c.sueldo_default||50; document.getElementById('conf_whatsapp_activo').checked=c.whatsapp_activo!==false;}}catch(e){}}
async function cargarNomina(){const mes=document.getElementById('nomina_mes').value || new Date().toISOString().slice(0,7); try{const data=await api('/api/nomina/'+mes); let html='<table style="width:100%;border-collapse:collapse;font-size:11px"><tr><th style="text-align:left;padding:6px">Empleado</th><th>Horas</th><th>Ret</th><th>Bono</th><th>Total</th><th>WA</th></tr>'; data.forEach(r=>{ html+=`<tr style="border-top:1px solid #334155"><td style="padding:6px"><b>${r.empleado_id}</b> ${r.nombre}</td><td>${r.horas}h</td><td style="color:${r.retardos>0?'#ef4444':'#10b981'}">${r.retardos}</td><td>$${r.bono}</td><td><b>$${r.total}</b></td><td><button onclick="enviarWhatsAppDirect('${r.telefono}','Hola ${r.nombre} nómina ${mes}: $${r.total}')" style="padding:4px 8px;border-radius:6px;border:none;background:#25D366;color:white">📱</button></td></tr>`; }); html+='</table>'; document.getElementById('nomina-result').innerHTML=html;}catch(e){document.getElementById('nomina-result').innerText='❌ '+e.detail;}}
function enviarWhatsAppDirect(tel,msg){ if(!tel) return alert('Sin tel'); api('/api/notificar-whatsapp','POST',{para:tel,mensaje:msg}).then(r=>window.open(r.link,'_blank')); }
async function cargarReporteSucursales(){const mes=document.getElementById('rep_suc_mes').value || new Date().toISOString().slice(0,7); try{const data=await api('/api/reporte-sucursales/'+mes); document.getElementById('reporte-suc-result').innerHTML=data.map((s,i)=>`<div style="background:#0f172a;padding:10px;border-radius:10px;margin-top:6px;display:flex;justify-content:space-between"><div><b>${i+1}. ${s.nombre}</b><br><small>${s.empleados} emp - ${s.horas_mes}h</small></div><div style="color:${s.retardos_mes>0?'#ef4444':'#10b981'}">${s.retardos_mes}min</div></div>`).join('');}catch(e){}}
async function cargarAntiTrampa(){try{const data=await api('/api/anti-trampa/log'); document.getElementById('antitrampa-result').innerHTML= data.length? data.map(d=>`<div style="background:#ef444415;border:1px solid #ef4444;border-radius:10px;padding:8px;margin-top:6px;font-size:11px"><b>${d.empleado_id} ${d.nombre}</b> - ${d.motivo}</div>`).join('') : '✅ Sin trampas';}catch(e){}}
async function cargarPermisos(){try{const p=await api('/api/permisos'); const modulos=[{id:"dashboard",nombre:"📊 Dashboard"},{id:"empleados",nombre:"👥 Empleados"},{id:"sucursales",nombre:"🏢 Sucursales"},{id:"retardos",nombre:"⏱️ Retardos"},{id:"nomina",nombre:"💰 Nómina"}]; let html='<div style="font-size:11px">'; modulos.forEach(m=>{html+=`<div style="background:#0f172a;padding:8px;border-radius:8px;margin-top:6px;display:flex;justify-content:space-between"><span>${m.nombre}</span><label><input type="checkbox" checked> Ver</label></div>`;}); html+='</div>'; document.getElementById('permisos-editor').innerHTML=html;}catch(e){}}
async function guardarPermisos(){alert('Permisos guardados (demo)');}
// EMPLEADO PRO
async function cargarEmpleado(){const hoy=await api('/asistencia/hoy/'+USER_ID); actualizarUI(hoy); cargarMisRetardos(); cargarMisVacaciones(); cargarMisJustificantes(); cargarNotifs();}
function actualizarUI(data){const btn=document.getElementById('btn-check'); if(!btn) return; btn.innerText=data.texto_boton; btn.style.background=data.color; window.estadoActual=data.siguiente; document.getElementById('estado-jornada').innerHTML=`<div class="paso ${data.estado==='sin_entrada'?'activo':''}"><b>Estado:</b> ${data.estado} - Suc: ${data.sucursal?.nombre||'Libre'}</div>`; if(data.gps_activo) activarGPS(); else desactivarGPS();}
function activarGPS(){if(gpsActivo) return; gpsActivo=true; document.getElementById('gps-status').innerText='GPS: ON'; document.getElementById('gps-status').className='gps-on'; if(navigator.geolocation){watchId=navigator.geolocation.watchPosition(pos=>{miPos={lat:pos.coords.latitude,lng:pos.coords.longitude}; api('/gps/update','POST',{empleado_id:USER_ID,lat:miPos.lat,lng:miPos.lng}); document.getElementById('dist-suc').innerText=`📍 ${miPos.lat.toFixed(5)},${miPos.lng.toFixed(5)}`;}, err=>{}, {enableHighAccuracy:true, maximumAge:0, timeout:5000});}}
function desactivarGPS(){gpsActivo=false; document.getElementById('gps-status').innerText='GPS: Off'; document.getElementById('gps-status').className='gps-off'; if(watchId!==null){navigator.geolocation.clearWatch(watchId); watchId=null;}}
async function registrar(){try{const lat=miPos.lat; const lng=miPos.lng; const tipo=window.estadoActual; const r=await api('/asistencia/registrar','POST',{empleado_id:USER_ID,tipo:tipo,lat:lat,lng:lng}); document.getElementById('msg-check').innerText=`✅ ${tipo} registrado`; const hoy=await api('/asistencia/hoy/'+USER_ID); actualizarUI(hoy);}catch(e){document.getElementById('msg-check').innerText='❌ '+(e.detail||'Error');}}
async function cargarMisRetardos(){try{const data=await api('/empleado/'+USER_ID+'/retardos-mes'); document.getElementById('total-retardo-entrada').innerText=data.total_retardo_entrada+' min'; document.getElementById('total-retardo-comida').innerText=data.total_retardo_comida+' min'; document.getElementById('total-horas-mes').innerText=data.total_horas+'h'; document.getElementById('mis-retardos').innerHTML=data.detalles.map(d=>`<div style="background:#0f172a;padding:8px;border-radius:8px;margin-top:6px;font-size:11px">${d.fecha_dia} - Entrada ${d.entrada} Ret ${d.retardo_entrada}min</div>`).join('')||'Sin retardos ✅';}catch(e){}}
async function solicitarVacaciones(){const tipo=document.getElementById('vac_tipo').value; const inicio=document.getElementById('vac_inicio').value; const fin=document.getElementById('vac_fin').value; const motivo=document.getElementById('vac_motivo').value; try{await api('/vacaciones/solicitar','POST',{empleado_id:USER_ID,tipo:tipo,fecha_inicio:inicio,fecha_fin:fin,motivo:motivo}); alert('✅ Solicitado'); cargarMisVacaciones();}catch(e){alert(e.detail);}}
async function cargarMisVacaciones(){try{const vac=await api('/vacaciones/'+USER_ID); document.getElementById('mis-vacaciones').innerHTML=vac.map(v=>`<div style="background:#0f172a;padding:8px;border-radius:8px;margin-top:6px;font-size:11px"><b>${v.tipo}</b> ${v.fecha_inicio} al ${v.fecha_fin} - ${v.estado}<br>${v.motivo}</div>`).join('')||'Sin';}catch(e){}}
async function subirJustificante(){const fecha=document.getElementById('just_fecha').value; const tipo=document.getElementById('just_tipo').value; const motivo=document.getElementById('just_motivo').value; try{await api('/justificantes/subir','POST',{empleado_id:USER_ID,fecha:fecha,tipo:tipo,motivo:motivo}); alert('✅ Subido'); cargarMisJustificantes();}catch(e){alert(e.detail);}}
async function cargarMisJustificantes(){try{const just=await api('/justificantes/'+USER_ID); document.getElementById('mis-justificantes').innerHTML=just.map(j=>`<div style="background:#0f172a;padding:8px;border-radius:8px;margin-top:6px;font-size:11px"><b>${j.tipo}</b> ${j.fecha} - ${j.estado}<br>${j.motivo}</div>`).join('')||'Sin';}catch(e){}}
async function cargarNotifs(){try{const n=await api('/alertas/'+USER_ID); document.getElementById('mis-notifs').innerHTML=n.slice(-5).map(a=>`<div style="background:#0f172a;padding:8px;border-radius:8px;margin-top:6px;font-size:11px">${a.mensaje}<br><small>${a.fecha}</small></div>`).join('')||'Sin';}catch(e){}}
async function cambiarPassword(){const old=document.getElementById('old_pass').value; const nw=document.getElementById('new_pass').value; if(!old||!nw) return alert('Llena ambos'); try{await api('/api/cambiar-password','POST',{empleado_id:USER_ID,old_password:old,new_password:nw}); document.getElementById('msg-pass').innerText='✅ Cambiada';}catch(e){document.getElementById('msg-pass').innerText='❌ '+(e.detail||'Error');}}
async function cargarEmpleadoPro(){cargarEmpleado(); cargarMiPerfil(); cargarMiCalendario(); cargarMiRanking(); cargarMiHistorialGrafica(); cargarMisNotificacionesEmp();}
async function cargarMiPerfil(){try{const p=await api('/api/empleado/'+USER_ID+'/perfil'); const emp=p.empleado; if(emp.foto){ document.getElementById('emp_foto_preview').src=emp.foto; document.getElementById('emp_foto_preview').style.display='block'; document.getElementById('topbar-foto').src=emp.foto; document.getElementById('topbar-foto').style.display='block';} document.getElementById('emp-perfil-info').innerHTML=`<b>${emp.nombre}</b> - ${emp.puesto||''} - ${emp.rol||''}<br>📱 ${emp.telefono||''}<br>💰 $${emp.sueldo_hora||50}/h<br>⏰ ${emp.tiempo_comida||120} min comida<br>📍 ${(emp.sucursales_ids||[]).join(', ')}<br>Horas totales: ${p.horas_total}h`; }catch(e){}}
async function subirFotoPerfil(){const file=document.getElementById('emp_foto_input').files[0]; if(!file) return alert('Foto'); const reader=new FileReader(); reader.onload=async e=>{ const foto=e.target.result; await api('/api/empleado/'+USER_ID+'/foto','POST',{foto:foto}); document.getElementById('emp_foto_preview').src=foto; document.getElementById('emp_foto_preview').style.display='block'; document.getElementById('topbar-foto').src=foto; document.getElementById('topbar-foto').style.display='block'; alert('✅ Foto subida'); }; reader.readAsDataURL(file);}
async function cargarMiCalendario(){const mes=document.getElementById('emp_cal_mes')?.value || new Date().toISOString().slice(0,7); try{const dias=await api('/api/calendario/'+USER_ID+'/'+mes); document.getElementById('emp-calendario-result').innerHTML=dias.map(d=>`<div style="background:#0f172a;border-left:4px solid ${d.color};border-radius:8px;padding:6px;text-align:center;font-size:10px"><b>${d.dia}</b><br><small style="color:${d.color}">${d.estado}</small></div>`).join('');}catch(e){}}
async function cargarMiRanking(){try{const mes=new Date().toISOString().slice(0,7); const data=await api('/api/nomina/'+mes); const yo=data.find(x=>x.empleado_id===USER_ID); const pos=data.sort((a,b)=>a.retardos-b.retardos).findIndex(x=>x.empleado_id===USER_ID)+1; if(yo){ document.getElementById('emp-ranking-info').innerHTML=`Posición ${pos} de ${data.length}<br>Horas: ${yo.horas}h - Retardos: ${yo.retardos} min<br><b style="color:#10b981">${yo.bono>0?`🎉 Ganando bono $${yo.bono}`:`⚠️ ${yo.retardos} min retardo`}</b>`; }}catch(e){}}
let chartEmp=null;
async function cargarMiHistorialGrafica(){try{const data=await api('/empleado/'+USER_ID+'/retardos-mes'); document.getElementById('emp-historial-lista').innerHTML=data.detalles?.slice(0,10).map(r=>`<div style="background:#0f172a;padding:6px;border-radius:8px;margin-top:4px;font-size:11px">${r.fecha_dia} - ${r.entrada||'--'} ${r.retardo_entrada>0?`⚠️ +${r.retardo_entrada}min`: '✅'}</div>`).join('')||'Sin datos'; const ctx=document.getElementById('chart-horas-emp'); if(ctx && data.asistencias){ if(chartEmp) chartEmp.destroy(); chartEmp=new Chart(ctx,{type:'bar',data:{labels:data.asistencias.slice(-7).map(d=>d.fecha_dia.slice(5)), datasets:[{label:'Horas', data:data.asistencias.slice(-7).map(d=>d.horas_trabajadas||0), backgroundColor:'#10b981'}]},options:{responsive:true, plugins:{legend:{display:false}}}}); }}catch(e){}}
async function cargarMisNotificacionesEmp(){try{const notifs=await api('/alertas/'+USER_ID); document.getElementById('emp-notificaciones').innerHTML=notifs.slice(-10).map(n=>`<div style="background:#0f172a;padding:8px;border-radius:8px;margin-top:6px;font-size:11px">${n.mensaje}<br><small>${n.fecha}</small></div>`).join('')||'Sin notificaciones';}catch(e){}}

// === AGREGADO BONITA CONSERVADA: ASIGNACIONES FLEX + EDITAR + CALIFICACIONES ABAJO JORNADA/RETARDOS ===
let flexEditId=null; let _flexCache=[];
function cambiarFlexTipo(){
 const t=document.getElementById('flex_tipo').value;
 document.getElementById('flex-box-dia').style.display=t==='dia'?'block':'none';
 document.getElementById('flex-box-semana').style.display=t==='semana'?'block':'none';
 document.getElementById('flex-box-mes').style.display=t==='mes'?'block':'none';
}
async function cargarFlexEmpsSucs(){
 try{
  const emps=await api('/empleados');
  const sucs=await api('/sucursales');
  const empList=Array.isArray(emps)?emps:Object.values(emps);
  const sucList=Array.isArray(sucs)?sucs:Object.values(sucs);
  const empOpts=empList.map(e=>`<option value="${e.id}">${e.id} - ${e.nombre} (${e.puesto||''})</option>`).join('');
  const sucOpts=sucList.map(s=>`<option value="${s.id}">${s.nombre}</option>`).join('');
  const sucOptsDesc='<option value="">Descanso</option>'+sucOpts;
  const fel=document.getElementById('flex_emp');
  if(fel) fel.innerHTML='<option value="">-- Selecciona empleado * --</option>'+empOpts;
  const f=document.getElementById('filtro_flex_emp'); if(f) f.innerHTML='<option value="">Filtrar empleado</option>'+empOpts;
  ['flex_suc_dia','flex_suc_mes'].forEach(id=>{const el=document.getElementById(id); if(el) el.innerHTML=sucOpts;});
  ['flex_lun','flex_mar','flex_mie','flex_jue','flex_vie','flex_sab','flex_dom'].forEach(id=>{const el=document.getElementById(id); if(el) el.innerHTML=sucOptsDesc;});
  console.log('Flex empleados cargados',empList.length);
 }catch(e){console.log('flex load error',e); document.getElementById('flex_emp').innerHTML='<option>Error, dale Recargar</option>';}
}
async function guardarFlexDia(){
 const emp=document.getElementById('flex_emp').value;
 if(!emp) return alert('⚠️ Selecciona un empleado primero - si no ves, dale a Recargar empleados y sucursales');
 const d={empleado_id:emp, fecha:document.getElementById('flex_fecha').value, sucursal_id:document.getElementById('flex_suc_dia').value};
 if(!d.fecha||!d.sucursal_id) return alert('Falta fecha y sucursal');
 const r=await api('/api/asignaciones-flex/dia','POST',d);
 document.getElementById('flex-msg').innerText='✅ DÍA guardado '+emp+' → '+d.sucursal_id+' el '+d.fecha;
 cargarFlexAsignaciones('');
}
async function guardarFlexSemana(){
 const emp=document.getElementById('flex_emp').value;
 if(!emp) return alert('⚠️ Selecciona empleado primero');
 const d={empleado_id:emp, semana:document.getElementById('flex_semana').value, lunes:document.getElementById('flex_lun').value, martes:document.getElementById('flex_mar').value, miercoles:document.getElementById('flex_mie').value, jueves:document.getElementById('flex_jue').value, viernes:document.getElementById('flex_vie').value, sabado:document.getElementById('flex_sab').value, domingo:document.getElementById('flex_dom').value};
 if(!d.semana) return alert('Falta semana');
 await api('/api/asignaciones-flex/semana','POST',d);
 document.getElementById('flex-msg').innerText='✅ SEMANA guardada '+d.semana; cargarFlexAsignaciones('');
}
async function guardarFlexMes(){
 const emp=document.getElementById('flex_emp').value;
 if(!emp) return alert('⚠️ Selecciona empleado primero');
 const d={empleado_id:emp, mes:document.getElementById('flex_mes').value, sucursal_id:document.getElementById('flex_suc_mes').value};
 if(!d.mes||!d.sucursal_id) return alert('Falta mes y sucursal');
 await api('/api/asignaciones-flex/mes','POST',d);
 document.getElementById('flex-msg').innerText='✅ MES guardado '+d.mes; cargarFlexAsignaciones('');
}
async function cargarFlexAsignaciones(filtro){
 const list=await api('/api/asignaciones-flex');
 _flexCache=list;
 let filtered=list;
 if(filtro) filtered=list.filter(a=>a.tipo===filtro);
 renderFlex(filtered);
}
function renderFlex(list){
 document.getElementById('flex-lista').innerHTML=list.map(a=>{
   let edit=`<button onclick="editarFlexById('${a.id}')" style="background:#6366f122;color:#a5b4fc;border:none;padding:4px 8px;border-radius:6px;cursor:pointer;font-size:11px;margin-right:4px">✏️ Editar</button>`;
   let del=`<button onclick="eliminarFlex('${a.id}')" style="background:#ef444422;color:#f87171;border:none;padding:4px 8px;border-radius:6px;cursor:pointer;font-size:11px">🗑️ Eliminar</button>`;
   if(a.tipo==='dia') return `<div style="background:var(--bg);padding:10px;border-radius:10px;margin-top:6px;border-left:4px solid #38bdf8"><div style="display:flex;justify-content:space-between"><span>📅 <b>DÍA</b> ${a.fecha} - <b>${a.empleado_id}</b> → ${a.sucursal_id}</span><span>${edit}${del}</span></div></div>`;
   if(a.tipo==='semana') return `<div style="background:var(--bg);padding:10px;border-radius:10px;margin-top:6px;border-left:4px solid #a78bfa"><div style="display:flex;justify-content:space-between"><span>🗓️ <b>SEMANA</b> ${a.semana} - <b>${a.empleado_id}</b></span><span>${edit}${del}</span></div><div style="font-size:10px;color:var(--muted)">L:${a.lunes||'-'} M:${a.martes||'-'} X:${a.miercoles||'-'} J:${a.jueves||'-'} V:${a.viernes||'-'} S:${a.sabado||'-'} D:${a.domingo||'-'}</div></div>`;
   if(a.tipo==='mes') return `<div style="background:var(--bg);padding:10px;border-radius:10px;margin-top:6px;border-left:4px solid #fb923c"><div style="display:flex;justify-content:space-between"><span>📆 <b>MES</b> ${a.mes} - <b>${a.empleado_id}</b> → ${a.sucursal_id}</span><span>${edit}${del}</span></div></div>`;
 }).join('')||'<p style="font-size:11px;color:var(--muted)">Sin asignaciones</p>';
}
function filtrarFlex(){ const emp=document.getElementById('filtro_flex_emp').value; if(!emp) renderFlex(_flexCache); else renderFlex(_flexCache.filter(a=>a.empleado_id===emp)); }
function editarFlexById(id){ const a=_flexCache.find(x=>x.id===id); if(a) editarFlex(a); }
function editarFlex(a){
 flexEditId=a.id; document.getElementById('flex_edit_id').value=a.id;
 document.getElementById('flex_emp').value=a.empleado_id;
 document.getElementById('flex_tipo').value=a.tipo; cambiarFlexTipo();
 if(a.tipo==='dia'){ document.getElementById('flex_fecha').value=a.fecha; document.getElementById('flex_suc_dia').value=a.sucursal_id; document.getElementById('btn_edit_dia').style.display='block'; document.getElementById('btn_cancel_dia').style.display='block'; document.getElementById('flex-msg').innerText='✏️ Editando DÍA #'+a.id; }
 else if(a.tipo==='semana'){ document.getElementById('flex_semana').value=a.semana; document.getElementById('flex_lun').value=a.lunes||''; document.getElementById('flex_mar').value=a.martes||''; document.getElementById('flex_mie').value=a.miercoles||''; document.getElementById('flex_jue').value=a.jueves||''; document.getElementById('flex_vie').value=a.viernes||''; document.getElementById('flex_sab').value=a.sabado||''; document.getElementById('flex_dom').value=a.domingo||''; document.getElementById('btn_edit_sem').style.display='block'; document.getElementById('btn_cancel_sem').style.display='block'; document.getElementById('flex-msg').innerText='✏️ Editando SEMANA #'+a.id; }
 else if(a.tipo==='mes'){ document.getElementById('flex_mes').value=a.mes; document.getElementById('flex_suc_mes').value=a.sucursal_id; document.getElementById('btn_edit_mes').style.display='block'; document.getElementById('btn_cancel_mes').style.display='block'; document.getElementById('flex-msg').innerText='✏️ Editando MES #'+a.id; }
 window.scrollTo({top:0,behavior:'smooth'});
}
function cancelarFlexEdicion(){ flexEditId=null; document.getElementById('flex_edit_id').value=''; ['btn_edit_dia','btn_cancel_dia','btn_edit_sem','btn_cancel_sem','btn_edit_mes','btn_cancel_mes'].forEach(i=>{let e=document.getElementById(i); if(e) e.style.display='none';}); document.getElementById('flex-msg').innerText='Edición cancelada'; }
async function actualizarFlexDia(){ if(!flexEditId) return; const d={fecha:document.getElementById('flex_fecha').value, sucursal_id:document.getElementById('flex_suc_dia').value}; await api('/api/asignaciones-flex/'+flexEditId,'PUT',d); document.getElementById('flex-msg').innerText='✅ Actualizado DÍA'; cancelarFlexEdicion(); cargarFlexAsignaciones(''); }
async function actualizarFlexSemana(){ if(!flexEditId) return; const d={semana:document.getElementById('flex_semana').value, lunes:document.getElementById('flex_lun').value, martes:document.getElementById('flex_mar').value, miercoles:document.getElementById('flex_mie').value, jueves:document.getElementById('flex_jue').value, viernes:document.getElementById('flex_vie').value, sabado:document.getElementById('flex_sab').value, domingo:document.getElementById('flex_dom').value}; await api('/api/asignaciones-flex/'+flexEditId,'PUT',d); document.getElementById('flex-msg').innerText='✅ Actualizado SEMANA'; cancelarFlexEdicion(); cargarFlexAsignaciones(''); }
async function actualizarFlexMes(){ if(!flexEditId) return; const d={mes:document.getElementById('flex_mes').value, sucursal_id:document.getElementById('flex_suc_mes').value}; await api('/api/asignaciones-flex/'+flexEditId,'PUT',d); document.getElementById('flex-msg').innerText='✅ Actualizado MES'; cancelarFlexEdicion(); cargarFlexAsignaciones(''); }
async function eliminarFlex(id){ if(!confirm('¿Eliminar asignación #'+id+'?')) return; await api('/api/asignaciones-flex/'+id,'DELETE'); cargarFlexAsignaciones(''); }

// === CALIFICACIONES ABAJO DE JORNADA Y RETARDOS - BONITA CONSERVADA ===
async function cargarMiCalificacionesHistorial(){
 try{
  const evals=await api('/evaluaciones/'+USER_ID);
  const evals2=Array.isArray(evals)?evals:[];
  const jornadaDiv=document.getElementById('tab-emp-jornada');
  if(jornadaDiv && !document.getElementById('emp-calif-below-jornada')){
   const box=document.createElement('div');
   box.id='emp-calif-below-jornada'; box.className='card'; box.style.border='1px solid #6366f1';
   box.innerHTML=`<h3>⭐ Mi Historial de Calificaciones (cuando admin me evalúa) - Abajo de jornada</h3><div id="emp-calif-jornada-lista"></div><div id="emp-calif-jornada-prom" style="margin-top:8px"></div>`;
   jornadaDiv.appendChild(box);
  }
  const rankingDiv=document.getElementById('tab-emp-ranking');
  const historialDiv=document.getElementById('tab-emp-historial');
  if(rankingDiv && !document.getElementById('emp-calif-below-retardos')){
   const box2=document.createElement('div');
   box2.id='emp-calif-below-retardos'; box2.className='card'; box2.style.border='1px solid #f59e0b';
   box2.innerHTML=`<h3>⏱️ Mis Retardos + ⭐ Calificaciones abajo de retardos</h3><div id="emp-retardos-detalle"></div><div id="emp-calif-retardos-lista" style="margin-top:12px"></div>`;
   rankingDiv.appendChild(box2);
  }
  if(historialDiv && !document.getElementById('emp-calif-below-historial')){
   const box3=document.createElement('div');
   box3.id='emp-calif-below-historial'; box3.className='card'; box3.style.border='1px solid #10b981';
   box3.innerHTML=`<h3>⭐ Historial completo + Retardos abajo</h3><div id="emp-calif-hist-lista"></div>`;
   historialDiv.appendChild(box3);
  }
  const render = (evals)=>{
   if(evals.length===0) return '<p style="font-size:11px;color:#64748b">Sin calificaciones aún - el admin te evalúa en Evaluaciones</p>';
   evals.sort((a,b)=>new Date(b.fecha||b.created_at)-new Date(a.fecha||a.created_at));
   return evals.map(e=>`<div style="background:#0f172a;padding:8px;border-radius:8px;margin-top:6px;border-left:3px solid ${ (e.total||e.calificacion||0)>=80?'#10b981':(e.total||0)>=60?'#f59e0b':'#ef4444'}"><div style="display:flex;justify-content:space-between"><span style="font-size:11px;color:#94a3b8">📅 ${e.fecha||e.created_at||''}</span><span style="font-weight:800;color:${ (e.total||0)>=80?'#34d399':(e.total||0)>=60?'#fbbf24':'#f87171'}">⭐ ${e.total||e.calificacion||0}/100</span></div><p style="font-size:11px;margin-top:4px">${e.comentario||JSON.stringify(e.calificaciones||{}).slice(0,120)}</p></div>`).join('');
  };
  const prom = evals2.length>0?(evals2.reduce((s,x)=>s+(x.total||x.calificacion||0),0)/evals2.length).toFixed(1):0;
  const html=render(evals2);
  const ids=['emp-calif-jornada-lista','emp-calif-retardos-lista','emp-calif-hist-lista'];
  ids.forEach(id=>{const el=document.getElementById(id); if(el) el.innerHTML=html;});
  const promEl=document.getElementById('emp-calif-jornada-prom'); if(promEl) promEl.innerHTML=`<p style="font-size:12px">Promedio: <b style="font-size:18px;color:#a78bfa">⭐ ${prom}/100</b> de ${evals2.length} evaluaciones</p>`;
  try{
   const retardos=await api('/empleado/'+USER_ID+'/retardos-mes');
   const rd=document.getElementById('emp-retardos-detalle'); if(rd) rd.innerHTML=`<p style="font-size:11px">Faltas: <b>${retardos.faltas||0}</b> | Retardos: <b>${retardos.retardos||0}</b></p><div style="max-height:120px;overflow:auto;margin-top:6px">${(retardos.detalles||[]).slice(0,8).map(r=>`<div style="font-size:10px;padding:3px;border-bottom:1px solid #1e293b">${r.fecha_dia} ${r.entrada||''} ${r.retardo_entrada>0?'🔴 +'+r.retardo_entrada+'min':'🟢'}</div>`).join('')}</div>`;
  }catch(e){}
 }catch(e){console.log('calif hist',e)}
}

// Hook para cargar todo sin quitar BONITA
const _origCargarTodo = cargarTodo;
cargarTodo = async function(){ await _origCargarTodo(); await cargarFlexEmpsSucs(); await cargarFlexAsignaciones(''); };
const _origCargarEmpleadoPro = cargarEmpleadoPro;
cargarEmpleadoPro = async function(){ await _origCargarEmpleadoPro(); await cargarMiCalificacionesHistorial(); };



async function cargarCalendario(){
 const mes=document.getElementById('cal_mes').value || new Date().toISOString().slice(0,7);
 const data=await api('/api/calendario-asignaciones?mes='+mes);
 const cont=document.getElementById('calendario-visual');
 // Crear 31 días
 const [y,m]=mes.split('-').map(Number);
 const days=new Date(y,m,0).getDate();
 let html=`<div style="grid-column:span 7;text-align:center;font-weight:800;padding:8px;background:#6366f1;border-radius:8px">📅 ${mes} - ${data.length} asignaciones</div>`;
 html+=['Lun','Mar','Mié','Jue','Vie','Sáb','Dom'].map(d=>`<div style="text-align:center;font-size:10px;padding:4px;background:var(--bg);border-radius:6px">${d}</div>`).join('');
 for(let d=1;d<=days;d++){
   const fecha=`${mes}-${String(d).padStart(2,'0')}`;
   const asig=data.filter(a=>a.fecha===fecha || a.mes===mes);
   let bg=asig.length?'#6366f133':'var(--bg)';
   let txtAsig=asig.map(a=>`<div style="font-size:8px;background:#6366f1;color:white;border-radius:3px;padding:1px 2px;margin-top:2px">${a.empleado_id}→${a.sucursal_id||''}</div>`).join('');
   html+=`<div style="background:${bg};padding:6px;border-radius:8px;min-height:60px"><b style="font-size:10px">${d}</b>${txtAsig}</div>`;
 }
 cont.innerHTML=html;
}
async function exportExcel(tipo){
 const data=await api('/api/export/'+tipo);
 const ws = JSON.stringify(data, null, 2);
 const blob = new Blob([ws], {type:'application/json'});
 const url=URL.createObjectURL(blob);
 const a=document.createElement('a'); a.href=url; a.download=tipo+'_'+new Date().toISOString().slice(0,10)+'.json'; a.click();
 alert('✅ Exportado '+tipo+' - '+data.length+' registros. Ábrelo en Excel o conviértelo a Excel.');
}
async function cargarRanking(){
 const rank=await api('/api/ranking-mes');
 document.getElementById('ranking-top').innerHTML='<h4>🏆 Top 10 del mes por calificaciones</h4>'+rank.map((r,i)=>`<div style="display:flex;justify-content:space-between;background:${i<3?'#f59e0b22':'var(--bg)'};padding:8px;border-radius:8px;margin-top:4px"><span>${i==0?'🥇':i==1?'🥈':i==2?'🥉':i+1+'.'} <b>${r.nombre}</b> (${r.empleado_id})</span><span>⭐ ${r.prom}/100 (${r.total} eval)</span></div>`).join('');
}
async function crearTarea(){
 const d={sucursal_id:document.getElementById('tarea_suc').value, texto:document.getElementById('tarea_txt').value, completada:false};
 if(!d.sucursal_id||!d.texto) return alert('Sucursal y tarea');
 await api('/api/tareas-sucursal','POST',d); cargarTareas();
}
async function cargarTareas(){
 const list=await api('/api/tareas-sucursal');
 const sucs=await api('/sucursales'); const sucList=Array.isArray(sucs)?sucs:Object.values(sucs);
 document.getElementById('tarea_suc').innerHTML=sucList.map(s=>`<option value="${s.id}">${s.nombre}</option>`).join('');
 document.getElementById('tareas-lista').innerHTML=list.slice(-20).reverse().map(t=>`<div style="display:flex;justify-content:space-between;background:var(--bg);padding:8px;border-radius:8px;margin-top:4px"><span><input type="checkbox" ${t.completada?'checked':''} onchange="toggleTarea('${t.id}',this.checked)"> ${t.texto} - <small>${t.sucursal_id}</small></span><span style="font-size:10px">${t.created_at?.slice(0,10)||''}</span></div>`).join('');
}
async function toggleTarea(id, val){ await api('/api/tareas-sucursal/'+id,'PUT',{completada:val}); }
async function cargarHorasExtra(){ const list=await api('/api/horas-extra'); document.getElementById('horas-extra-lista').innerHTML=list.slice(-20).reverse().map(h=>`<div style="background:var(--bg);padding:8px;border-radius:8px;margin-top:4px">⏰ ${h.empleado_id} - ${h.fecha||''} +${h.minutos||0}min extra - ${h.motivo||''}</div>`).join('')||'Sin horas extra'; }

// Hook para cargar extras
const _origCargarTodo_EXTRA=cargarTodo;
cargarTodo=async function(){ await _origCargarTodo_EXTRA(); try{ await cargarTareas(); await cargarCalendario(); }catch(e){} };

// SESION PERMANENTE
window.addEventListener('load', async ()=>{
  const sesion=localStorage.getItem('sesion_activa'); const uid=localStorage.getItem('user_id'); const rol=localStorage.getItem('rol'); const nombre=localStorage.getItem('nombre'); const empresa=localStorage.getItem('empresa_nombre')||'';
  if(sesion==='true' && uid){
    USER_ID=uid; ROL=rol;
    try{
      document.getElementById('login').style.display='none'; document.getElementById('app').style.display='block';
      document.getElementById('banner-nombre').innerText=`👋 Hola, ${nombre}`; document.getElementById('banner-nombre2').innerText=`👋 Hola, ${nombre} | ${rol?.toUpperCase()} ${empresa? ' - '+empresa : ''}`;
      document.getElementById('user-display').innerText=nombre+' ('+rol+')';
      if(rol==='empleado'){
        document.getElementById('admin-area').style.display='none'; document.getElementById('empleado-area').style.display='block';
        document.getElementById('sidebar-admin').style.display='none'; document.getElementById('sidebar-emp').style.display='block';
        document.getElementById('bottom-nav-admin').style.display='none'; document.getElementById('bottom-nav-emp').style.display='flex';
        cargarEmpleadoPro();
      }else{
        document.getElementById('admin-area').style.display='block'; document.getElementById('empleado-area').style.display='none';
        document.getElementById('sidebar-admin').style.display='block'; document.getElementById('sidebar-emp').style.display='none';
        document.getElementById('bottom-nav-admin').style.display='flex'; document.getElementById('bottom-nav-emp').style.display='none';
        cargarTodo();
      }
    }catch(e){ console.log('Auto login fail',e); }
  }
});
function logout(){ if(confirm('¿Cerrar sesión?')){ localStorage.clear(); location.reload(); } }
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

