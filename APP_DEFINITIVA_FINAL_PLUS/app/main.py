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
roles_custom_db = {
    "empleado": {"nombre": "Empleado", "descripcion": "Empleado base", "color": "#64748b", "permisos": ["propia_jornada"], "es_sistema": True},
    "supervisor": {"nombre": "Supervisor", "descripcion": "Supervisa empleados", "color": "#0ea5e9", "permisos": ["dashboard","empleados","sucursales","retardos"], "es_sistema": True},
    "rh": {"nombre": "Recursos Humanos", "descripcion": "Gestión de personal", "color": "#8b5cf6", "permisos": ["dashboard","empleados","retardos","nomina","vacaciones"], "es_sistema": True},
    "gerente": {"nombre": "Gerente", "descripcion": "Gerente de sucursal", "color": "#f59e0b", "permisos": ["dashboard","sucursales","empleados","retardos","ruta_gps","vacaciones"], "es_sistema": True},
    "admin": {"nombre": "Admin", "descripcion": "Administrador total", "color": "#ef4444", "permisos": ["todo"], "es_sistema": True},
    "superadmin": {"nombre": "Super Admin", "descripcion": "Acceso total del sistema", "color": "#dc2626", "permisos": ["todo"], "es_sistema": True}
}
creador_info_db = {
    "nombre": "Rubén García",
    "empresa": "Clock RD - Sistema de Control",
    "version": "PRO MAX 2026",
    "fecha_creacion": "2024",
    "contacto": "Soporte exclusivo",
    "licencia": "Exclusiva - Uso privado",
    "descripcion": "Sistema exclusivo desarrollado para control de asistencia, GPS, nómina y gestión de personal. Propiedad intelectual protegida."
}


def load_db():
    global sucursales_db, empleados_db, evaluaciones_db, asistencias_db, alertas_db, gps_logs_db, vacaciones_db, justificantes_db, audit_db, chat_db, panico_db, reportes_volanteo_db, empresa_db, verificaciones_db, permisos_db, bonos_db, metas_db, nomina_db, notificaciones_db, turnos_rotativos_db, config_admin_db, perfil_fotos_db, limpieza_config_db, roles_custom_db, creador_info_db
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE,'r', encoding='utf-8') as f:
                data=json.load(f)
                sucursales_db=data.get("sucursales",{})
                empleados_db=data.get("empleados",{"EMPDEMO": {"id":"EMPDEMO","nombre":"Empleado Demo","puesto":"Demo","rol":"empleado","password":hash_pass("demo"),"sucursales_ids":[],"horario":{},"activo":True,"tiempo_comida":120,"telefono":"5210000000000","sueldo_hora":50,"foto":""},
        "EMP0001": {"id":"EMP0001","nombre":"Empleado Prueba","puesto":"Botarga","rol":"empleado","password":hash_pass("0001"),"sucursales_ids":[],"horario":{},"activo":True,"tiempo_comida":120,"telefono":"5210000000000","sueldo_hora":50,"foto":""}})
                evaluaciones_db=data.get("evaluaciones",[]); asistencias_db=data.get("asistencias",[]); alertas_db=data.get("alertas",[]); gps_logs_db=data.get("gps_logs",[]); vacaciones_db=data.get("vacaciones",[]); justificantes_db=data.get("justificantes",[]); audit_db=data.get("audit",[]); chat_db=data.get("chat",[]); panico_db=data.get("panico",[]); reportes_volanteo_db=data.get("reportes_volanteo",[]); empresa_db=data.get("empresa",{}); verificaciones_db=data.get("verificaciones",{}); permisos_db=data.get("permisos",{"empleado":{"ver":["propia_jornada"],"editar":[]},"supervisor":{"ver":["dashboard","empleados","sucursales","retardos"],"editar":[]},"rh":{"ver":["dashboard","empleados","retardos","nomina","vacaciones"],"editar":["empleados","vacaciones"]},"gerente":{"ver":["dashboard","sucursales","empleados","retardos","ruta_gps","vacaciones"],"editar":["sucursales","empleados"]},"admin":{"ver":["todo"],"editar":["todo"]}}); bonos_db=data.get("bonos",{}); metas_db=data.get("metas",{}); nomina_db=data.get("nomina",{}); notificaciones_db=data.get("notificaciones",[]); turnos_rotativos_db=data.get("turnos_rotativos",{}); config_admin_db=data.get("config_admin",{"telefono_admin":"","whatsapp_activo":True,"bono_puntualidad":500,"sueldo_default":50}); perfil_fotos_db=data.get("perfil_fotos",{}); limpieza_config_db.update(data.get("limpieza_config",{"ultima_limpieza_gps": "", "ultima_limpieza_general": "", "gps_meses": 3, "general_meses": 6, "auto_activo": True})); roles_custom_db.update(data.get("roles_custom",{})); creador_info_db.update(data.get("creador_info",{})); return
        except Exception as e:
            print(f"Load error {e}")
    sucursales_db = {}; empleados_db = {"EMPDEMO": {"id":"EMPDEMO","nombre":"Empleado Demo","puesto":"Demo","rol":"empleado","password":hash_pass("demo"),"sucursales_ids":[],"horario":{},"activo":True,"tiempo_comida":120,"telefono":"5210000000000","sueldo_hora":50,"foto":""},
        "EMP0001": {"id":"EMP0001","nombre":"Empleado Prueba","puesto":"Botarga","rol":"empleado","password":hash_pass("0001"),"sucursales_ids":[],"horario":{},"activo":True,"tiempo_comida":120,"telefono":"5210000000000","sueldo_hora":50,"foto":""}}; evaluaciones_db = []; asistencias_db=[]; alertas_db=[]; gps_logs_db=[]; vacaciones_db=[]; justificantes_db=[]; audit_db=[]; chat_db=[]; panico_db=[]; reportes_volanteo_db=[]; empresa_db={}; verificaciones_db={}; permisos_db={"empleado":{"ver":["propia_jornada"],"editar":[]},"supervisor":{"ver":["dashboard","empleados","sucursales","retardos"],"editar":[]},"rh":{"ver":["dashboard","empleados","retardos","nomina","vacaciones"],"editar":["empleados","vacaciones"]},"gerente":{"ver":["dashboard","sucursales","empleados","retardos","ruta_gps","vacaciones"],"editar":["sucursales","empleados"]},"admin":{"ver":["todo"],"editar":["todo"]}}; bonos_db={}; metas_db={}; nomina_db={}; notificaciones_db=[]; turnos_rotativos_db={}; config_admin_db={"telefono_admin":"","whatsapp_activo":True,"bono_puntualidad":500,"sueldo_default":50}; perfil_fotos_db={}; limpieza_config_db={"ultima_limpieza_gps": "", "ultima_limpieza_general": "", "gps_meses": 3, "general_meses": 6, "auto_activo": True}

def save_db():
    try:
        with open(DB_FILE,'w', encoding='utf-8') as f: json.dump({"sucursales":sucursales_db,"empleados":empleados_db,"evaluaciones":evaluaciones_db,"asistencias":asistencias_db,"alertas":alertas_db,"gps_logs":gps_logs_db,"vacaciones":vacaciones_db,"justificantes":justificantes_db,"audit":audit_db,"chat":chat_db,"panico":panico_db,"reportes_volanteo":reportes_volanteo_db,"empresa":empresa_db,"verificaciones":verificaciones_db,"permisos":permisos_db,"bonos":bonos_db,"metas":metas_db,"nomina":nomina_db,"notificaciones":notificaciones_db,"turnos_rotativos":turnos_rotativos_db,"config_admin":config_admin_db,"perfil_fotos":perfil_fotos_db,"limpieza_config":limpieza_config_db,"roles_custom":roles_custom_db,"creador_info":creador_info_db}, f, ensure_ascii=False, indent=2)
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

# === LIMPIEZA AUTOMATICA INTELIGENTE: GPS 3 meses, resto 6 meses, conserva empresas/empleados/sucursales/roles ===
limpieza_config_db = {"ultima_limpieza_gps": "", "ultima_limpieza_general": "", "gps_meses": 3, "general_meses": 6, "auto_activo": True}

def ejecutar_limpieza_inteligente(forzado=False):
    ahora = datetime.now()
    result = {"gps_borrados": 0, "asistencias_borradas": 0, "alertas_borradas": 0, "chat_borrados": 0, "panico_borrados": 0, "evaluaciones_borradas": 0, "audit_borrados": 0, "espacio_liberado_mb": 0, "conservados": "empresas, empleados, sucursales, roles, permisos, fotos perfil"}
    
    # GPS cada 3 meses
    limite_gps = ahora - timedelta(days=limpieza_config_db.get("gps_meses",3)*30)
    debe_gps = False
    if forzado: debe_gps = True
    else:
        try:
            ultima = datetime.strptime(limpieza_config_db.get("ultima_limpieza_gps","2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S")
            if (ahora - ultima).days >= limpieza_config_db.get("gps_meses",3)*30: debe_gps=True
        except: debe_gps=True
    
    if debe_gps:
        antes = len(gps_logs_db)
        def es_reciente_gps(f):
            try: return datetime.strptime(f, "%Y-%m-%d %H:%M:%S") >= limite_gps
            except: 
                try: return datetime.strptime(f, "%Y-%m-%d") >= limite_gps
                except: return True
        gps_logs_db[:] = [g for g in gps_logs_db if es_reciente_gps(g.get("fecha",""))]
        result["gps_borrados"] = antes - len(gps_logs_db)
        limpieza_config_db["ultima_limpieza_gps"] = ahora.strftime("%Y-%m-%d %H:%M:%S")
    
    # General cada 6 meses
    limite_gen = ahora - timedelta(days=limpieza_config_db.get("general_meses",6)*30)
    debe_gen = False
    if forzado: debe_gen = True
    else:
        try:
            ultima = datetime.strptime(limpieza_config_db.get("ultima_limpieza_general","2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S")
            if (ahora - ultima).days >= limpieza_config_db.get("general_meses",6)*30: debe_gen=True
        except: debe_gen=True
    
    if debe_gen:
        def es_reciente_gen(f):
            try: 
                # intenta ambos formatos
                try: return datetime.strptime(f, "%Y-%m-%d %H:%M:%S") >= limite_gen
                except: return datetime.strptime(f, "%Y-%m-%d") >= limite_gen
            except: return True
        
        # Asistencias >6 meses
        antes = len(asistencias_db)
        asistencias_db[:] = [a for a in asistencias_db if es_reciente_gen(a.get("fecha_dia", a.get("fecha","")))]
        result["asistencias_borradas"] = antes - len(asistencias_db)
        
        # Alertas (no gps ya limpiado, pero resto)
        antes = len(alertas_db)
        alertas_db[:] = [a for a in alertas_db if es_reciente_gen(a.get("fecha",""))]
        result["alertas_borradas"] = antes - len(alertas_db)
        
        # Chat
        antes = len(chat_db)
        chat_db[:] = [c for c in chat_db if es_reciente_gen(c.get("fecha",""))]
        result["chat_borrados"] = antes - len(chat_db)
        
        # Panico
        antes = len(panico_db)
        panico_db[:] = [p for p in panico_db if es_reciente_gen(p.get("fecha",""))]
        result["panico_borrados"] = antes - len(panico_db)
        
        # Evaluaciones
        antes = len(evaluaciones_db)
        evaluaciones_db[:] = [e for e in evaluaciones_db if es_reciente_gen(e.get("fecha",""))]
        result["evaluaciones_borradas"] = antes - len(evaluaciones_db)
        
        # Audit deja últimos 200
        if len(audit_db) > 200:
            result["audit_borrados"] = len(audit_db) - 200
            audit_db[:] = audit_db[-200:]
        
        limpieza_config_db["ultima_limpieza_general"] = ahora.strftime("%Y-%m-%d %H:%M:%S")
    
    # Calcular espacio aprox
    total_borrados = result["gps_borrados"] + result["asistencias_borradas"] + result["alertas_borradas"] + result["chat_borrados"] + result["panico_borrados"] + result["evaluaciones_borradas"]
    result["espacio_liberado_mb"] = round(total_borrados * 0.0005, 2)  # aprox 0.5KB por registro
    
    save_db()
    return result

def check_limpieza_automatica():
    if not limpieza_config_db.get("auto_activo", True):
        return None
    # Solo ejecuta si debe, sino None
    ahora = datetime.now()
    debe = False
    try:
        ultima_gps = datetime.strptime(limpieza_config_db.get("ultima_limpieza_gps","2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S")
        if (ahora - ultima_gps).days >= limpieza_config_db.get("gps_meses",3)*30: debe=True
    except: debe=True
    try:
        ultima_gen = datetime.strptime(limpieza_config_db.get("ultima_limpieza_general","2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S")
        if (ahora - ultima_gen).days >= limpieza_config_db.get("general_meses",6)*30: debe=True
    except: debe=True
    if debe:
        return ejecutar_limpieza_inteligente(forzado=False)
    return None



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
    if "telefono" not in e: e["telefono"]=""
    if "sueldo_hora" not in e: e["sueldo_hora"]=config_admin_db.get("sueldo_default",50)
    else:
        try: e["sueldo_hora"]=float(e["sueldo_hora"])
        except: e["sueldo_hora"]=50
    # Soporte multi-roles
    if "roles" in e and isinstance(e["roles"], list) and len(e["roles"])>0:
        e["roles"] = [r for r in e["roles"] if r in roles_custom_db]
        e["rol"] = e["roles"][0] if e["roles"] else "empleado"
    else:
        if "rol" not in e: e["rol"]="empleado"
        if e["rol"] not in roles_custom_db: e["rol"]="empleado"
        e["roles"] = [e["rol"]]
    if "foto" not in e: e["foto"]=""
    empleados_db[e["id"]]=e
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

@app.get("/api/limpieza/status")
def limpieza_status():
    check = check_limpieza_automatica()
    total_registros = len(gps_logs_db) + len(asistencias_db) + len(alertas_db) + len(chat_db) + len(panico_db) + len(evaluaciones_db)
    # Calcular próxima limpieza
    ahora = datetime.now()
    try:
        ultima_gps = datetime.strptime(limpieza_config_db.get("ultima_limpieza_gps","2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S")
        prox_gps = ultima_gps + timedelta(days=limpieza_config_db.get("gps_meses",3)*30)
    except:
        prox_gps = ahora + timedelta(days=limpieza_config_db.get("gps_meses",3)*30)
    try:
        ultima_gen = datetime.strptime(limpieza_config_db.get("ultima_limpieza_general","2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S")
        prox_gen = ultima_gen + timedelta(days=limpieza_config_db.get("general_meses",6)*30)
    except:
        prox_gen = ahora + timedelta(days=limpieza_config_db.get("general_meses",6)*30)
    
    return {
        "config": limpieza_config_db,
        "total_registros_actual": total_registros,
        "gps_actual": len(gps_logs_db),
        "asistencias_actual": len(asistencias_db),
        "proxima_limpieza_gps": prox_gps.strftime("%Y-%m-%d"),
        "proxima_limpieza_general": prox_gen.strftime("%Y-%m-%d"),
        "ultima_ejecucion_auto": check,
        "conserva_siempre": ["empresas", "empleados", "sucursales", "roles", "permisos", "fotos_perfil", "config_admin"],
        "borra_gps_3_meses": ["gps_logs", "alertas_gps"],
        "borra_general_6_meses": ["asistencias", "alertas", "chat", "panico", "evaluaciones", "audit_exceso"]
    }

@app.post("/api/limpieza/ejecutar")
def limpieza_ejecutar(data: dict = {}):
    forzado = data.get("forzado", True)
    result = ejecutar_limpieza_inteligente(forzado=forzado)
    audit_log("admin", "limpieza_6_meses", f"Borrados GPS:{result['gps_borrados']} Asist:{result['asistencias_borradas']} Total:{result['gps_borrados']+result['asistencias_borradas']}")
    return result

@app.post("/api/limpieza/config")
def limpieza_config(data: dict):
    limpieza_config_db.update(data)
    save_db()
    return limpieza_config_db

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
</style></head><body>

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
<div class="sidebar-item" onclick="switchTab('tab-perfil-admin')" style="border:2px solid #6366f1"><span>👑</span> Mi Perfil Admin</div>
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
<div class="sidebar-item" onclick="switchTabEmp('tab-emp-chat')"><span>💬</span> Chat con Admin</div>
<div class="sidebar-item" onclick="switchTabEmp('tab-emp-panico')"><span>🆘</span> Pánico SOS</div>
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
<div class="card" id="card-crear-empleado"><h3>👤 Nuevo Empleado + Rol + WhatsApp</h3><div style="background:#10b98115;padding:8px;border-radius:10px"><small>Próximo: <b id="next-id" style="color:#10b981">...</b></small></div><div style="display:flex;gap:8px"><input id="emp_id" class="input" readonly><button class="btn btn-dark" style="width:auto;margin-top:8px" onclick="generarID()">🔄</button></div><input id="emp_nombre" class="input" placeholder="Nombre *"><input id="emp_puesto" class="input" placeholder="Puesto"><div style="background:#0f172a;border:1px solid #334155;border-radius:12px;padding:12px;margin-top:8px">
<div style="font-size:11px;font-weight:800;margin-bottom:8px">🎭 ROLES (puedes elegir uno o varios):</div>
<div id="emp_roles_checkboxes" style="display:grid;grid-template-columns:1fr 1fr;gap:6px;max-height:120px;overflow:auto">
Cargando roles...
</div>
<small style="font-size:10px;color:#94a3b8">Si eliges varios, el primero será el principal. Ej: Empleado + Supervisor</small>
</div>
<input type="hidden" id="emp_rol" value="empleado"><input id="emp_telefono" class="input" placeholder="WhatsApp con código país ej 521... *"><div style="display:flex;gap:8px"><input id="emp_sueldo" class="input" type="number" placeholder="Sueldo por hora $" value="50"><input id="emp_pass" class="input" placeholder="Contraseña *"></div><div style="display:flex;gap:8px;align-items:center;margin-top:8px"><label style="font-size:12px;min-width:80px">Comida:</label><input id="emp_comida" class="input" type="number" value="120" style="margin-top:0"><span>min</span></div><div id="check-suc" style="background:#0f172a;border-radius:10px;padding:8px;margin-top:8px;max-height:80px;overflow:auto"></div><div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px"><select id="d-lunes" class="input"></select><select id="d-martes" class="input"></select><select id="d-miercoles" class="input"></select><select id="d-jueves" class="input"></select><select id="d-viernes" class="input"></select><select id="d-sabado" class="input"></select><select id="d-domingo" class="input"></select></div><button class="btn btn-success" onclick="crearEmp()">💾 Guardar Empleado</button></div>
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

<div class="card" style="border:2px solid #f59e0b;background:linear-gradient(135deg,#f59e0b15,#ef444415)">
<h3>🗑️ Limpieza Automática Inteligente</h3>
<p style="font-size:11px;color:var(--muted)">GPS cada 3 meses, todo lo demás cada 6 meses. Siempre conserva: empresas, empleados, sucursales, roles, permisos, fotos.</p>
<div style="background:#0f172a;border-radius:12px;padding:12px;margin-top:10px;font-size:11px" id="limpieza-status">
Cargando estado...
</div>
<div class="grid2" style="margin-top:10px">
<button class="btn btn-warning" onclick="ejecutarLimpieza()" style="font-size:11px">🗑️ Ejecutar Limpieza Ahora</button>
<button class="btn btn-dark" onclick="cargarLimpiezaStatus()" style="font-size:11px">🔄 Actualizar Estado</button>
</div>
<div style="display:flex;gap:8px;margin-top:10px">
<label style="font-size:11px;display:flex;align-items:center;gap:6px"><input type="checkbox" id="auto_limpieza_activo" checked> Auto activo</label>
<input id="gps_meses_cfg" type="number" value="3" style="width:60px" class="input"> <small>meses GPS</small>
<input id="general_meses_cfg" type="number" value="6" style="width:60px" class="input"> <small>meses General</small>
<button class="btn btn-primary" onclick="guardarLimpiezaConfig()" style="width:auto;padding:6px 10px;font-size:10px">💾 Guardar</button>
</div>
<p id="msg-limpieza" style="font-size:11px;margin-top:8px"></p>
</div>

<div class="card" style="border:2px solid #6366f1;background:linear-gradient(135deg,#6366f115,#0ea5e915)">
<h3>👨‍💻 Información del Creador - Solo Lectura</h3>
<div style="display:flex;gap:16px;align-items:center;margin-top:12px">
<img src="data:image/jpeg;base64,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" style="width:90px;height:90px;border-radius:50%;object-fit:cover;border:3px solid #f59e0b;box-shadow:0 0 20px rgba(245,158,11,.5)">
<div style="flex:1">
<div style="font-size:16px;font-weight:800">Rubén García</div>
<div style="font-size:12px;color:#94a3b8">Creador Exclusivo - Clock RD PRO MAX 2026</div>
<div style="margin-top:8px;background:#0f172a;border-radius:10px;padding:10px;font-size:11px" id="creador-info-display">
Cargando info del creador...
</div>
</div>
</div>
<div style="display:flex;gap:8px;margin-top:12px">
<button class="btn btn-primary" onclick="verTerminos()" style="width:auto;padding:10px 16px;font-size:11px">📜 Ver Términos y Condiciones Exclusivos</button>
<button class="btn btn-dark" onclick="cargarCreadorInfo()" style="width:auto;padding:10px 16px;font-size:11px">🔄 Actualizar Info</button>
</div>
</div>

<div class="card" style="border:2px solid #8b5cf6">
<h3>🎭 Gestión de Roles Personalizados</h3>
<p style="font-size:11px;color:#94a3b8">Crea roles nuevos, asigna múltiples roles por empleado. Ej: Alguien puede ser Empleado + Supervisor a la vez.</p>
<div style="background:#0f172a;border-radius:12px;padding:12px;margin-top:10px">
<div class="grid2"><input id="new_rol_id" class="input" placeholder="ID rol ej: cajero, bodega" style="margin-top:0"><input id="new_rol_nombre" class="input" placeholder="Nombre ej: Cajero" style="margin-top:0"></div>
<input id="new_rol_desc" class="input" placeholder="Descripción del rol">
<div style="display:flex;gap:8px;margin-top:8px"><input id="new_rol_color" type="color" value="#6366f1" style="width:50px;height:40px;border-radius:8px;border:none"><input id="new_rol_permisos" class="input" placeholder="Permisos ej: dashboard,empleados,retardos" style="margin-top:0;flex:1"></div>
<button class="btn btn-success" onclick="crearRolCustom()" style="font-size:11px">➕ Crear Rol Nuevo</button>
</div>
<div id="roles-lista" style="margin-top:12px;max-height:200px;overflow:auto"></div>
</div>

<div class="card" style="border:2px solid #ec4899"><h3>⚙️ Configuración WhatsApp y Bonos</h3><div class="grid2"><input id="conf_tel_admin" class="input" placeholder="Tu WhatsApp admin ej 521..."><input id="conf_bono" class="input" type="number" placeholder="Bono puntualidad $"></div><div class="grid2"><input id="conf_sueldo_default" class="input" type="number" placeholder="Sueldo default $/h"><label style="display:flex;align-items:center;gap:8px;margin-top:10px"><input type="checkbox" id="conf_whatsapp_activo" checked> WhatsApp auto</label></div><button class="btn btn-primary" onclick="guardarConfigAdmin()">💾 Guardar</button><p id="msg-conf-admin" style="font-size:11px;margin-top:8px"></p></div>
<div class="card"><h3>💾 Backup y DB</h3><div class="grid2"><button class="btn btn-dark" onclick="hacerBackup()">💾 Backup JSON</button><button class="btn btn-dark" onclick="cargarAudit()">📋 Ver Auditoría</button></div><div id="backup-result" style="display:none;margin-top:12px;background:#0f172a;border-radius:12px;padding:12px;font-size:11px"></div><div id="audit-result" style="display:none;margin-top:12px;background:#0f172a;border-radius:12px;padding:12px;max-height:200px;overflow:auto;font-size:11px"></div></div>
</div>
<div id="tab-audit" class="tab-content"><div class="card"><h3>📋 Auditoría Completa</h3><button class="btn btn-dark" onclick="cargarAudit()">🔄 Cargar Auditoría</button><div id="audit-result2" style="margin-top:12px"></div></div></div>

<div id="tab-perfil-admin" class="tab-content">
<div class="card" style="border:2px solid #6366f1"><h3>👑 Mi Perfil Admin</h3>
<div style="display:flex;gap:16px;align-items:center;margin-top:12px">
<img id="admin_foto_preview" src="" style="width:90px;height:90px;border-radius:50%;background:#1e293b;object-fit:cover;border:3px solid #6366f1;display:none">
<div style="flex:1">
<div id="admin-perfil-info" style="background:#0f172a;border-radius:12px;padding:12px;font-size:12px">Cargando perfil...</div>
<div style="margin-top:10px;display:flex;gap:8px">
<input type="file" id="admin_foto_input" accept="image/*" class="input" style="font-size:11px;margin-top:0">
<button class="btn btn-primary" onclick="subirFotoAdmin()" style="width:auto;padding:8px 12px;margin-top:0;font-size:11px">📸 Subir Foto</button>
</div>
</div>
</div>
<div style="margin-top:16px;display:grid;gap:10px">
<div class="card" style="margin:0;background:#0f172a"><h4 style="font-size:13px">🔑 Cambiar Contraseña Admin</h4><input id="admin_old_pass" class="input" type="password" placeholder="Actual"><input id="admin_new_pass" class="input" type="password" placeholder="Nueva"><button class="btn btn-primary" onclick="cambiarPasswordAdmin()">🔑 Cambiar Contraseña</button><p id="msg-pass-admin" style="font-size:11px;margin-top:8px"></p></div>
<button class="btn btn-danger" onclick="logout()" style="padding:16px;font-size:15px;background:linear-gradient(135deg,#ef4444,#dc2626)">🚪 Cerrar Sesión Admin</button>
<div style="background:linear-gradient(135deg,#6366f115,#8b5cf615);border:1px solid #6366f133;border-radius:12px;padding:12px;font-size:11px">
<b>💡 Info sesión:</b><br>
• Sesión permanente activa<br>
• Al recargar no pide contraseña<br>
• Solo se cierra si presionas Cerrar Sesión<br>
• Foto de perfil visible en topbar
</div>
</div>
</div>
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
<div class="card" style="border:2px solid #8b5cf6"><h3>👤 Mi Perfil + Foto</h3><div style="display:flex;gap:12px;align-items:center"><img id="emp_foto_preview" src="" style="width:80px;height:80px;border-radius:50%;background:#334155;object-fit:cover;display:none"><div><input type="file" id="emp_foto_input" accept="image/*" class="input" style="font-size:11px"><button class="btn btn-primary" onclick="subirFotoPerfil()" style="width:auto;padding:6px 12px;font-size:11px;margin-top:6px">📸 Subir Foto</button></div></div><div id="emp-perfil-info" style="margin-top:12px;font-size:12px;background:#0f172a;border-radius:12px;padding:12px"></div>
<div style="margin-top:16px;display:grid;gap:10px">
<button class="btn btn-danger" onclick="logout()" style="padding:14px;font-size:14px">🚪 Cerrar Sesión</button>
<div style="background:#0f172a;border-radius:12px;padding:10px;font-size:11px;color:#94a3b8;text-align:center">Sesión guardada • No necesitas volver a poner contraseña al recargar</div>
</div>
</div>
<div class="card"><h3>🔑 Seguridad</h3><input id="old_pass" class="input" type="password" placeholder="Actual"><input id="new_pass" class="input" type="password" placeholder="Nueva"><button class="btn btn-primary" onclick="cambiarPassword()">🔑 Cambiar Contraseña</button><p id="msg-pass" style="font-size:11px;margin-top:8px"></p>
<button class="btn btn-dark" onclick="logout()" style="margin-top:12px">🚪 Cerrar Sesión desde aquí también</button>
</div>
</div>
<div id="tab-emp-chat" class="tab-content">
<div class="card" style="border:2px solid #0ea5e9"><h3>💬 Chat con Administrador</h3>
<div id="chat-emp-list" style="margin-top:12px;max-height:300px;overflow:auto;background:#0f172a;border-radius:12px;padding:12px;font-size:11px"></div>
<div style="display:flex;gap:8px;margin-top:12px"><input id="chat_emp_msg" class="input" placeholder="Escribe mensaje al admin..." style="margin-top:0"><button class="btn btn-primary" onclick="enviarChatEmpleado()" style="width:auto;margin-top:0">📤 Enviar</button></div>
</div>
</div>

<div id="tab-emp-panico" class="tab-content">
<div class="card" style="border:2px solid #ef4444;background:linear-gradient(135deg,#ef444415,#f59e0b15)"><h3>🆘 Botón de Pánico SOS</h3>
<p style="font-size:11px;color:var(--muted);margin-top:6px">Si tienes emergencia, presiona el botón. Enviará tu ubicación GPS exacta al administrador.</p>
<button class="btn btn-danger" onclick="activarPanico()" style="padding:20px;font-size:18px;margin-top:16px;background:linear-gradient(135deg,#ef4444,#dc2626);box-shadow:0 8px 20px rgba(239,68,68,.4)">🆘 ENVIAR SOS DE EMERGENCIA</button>
<p id="msg-panico" style="font-size:12px;margin-top:10px;text-align:center"></p>
<div style="background:#0f172a;border-radius:12px;padding:12px;margin-top:12px;font-size:11px"><b>📍 Tu ubicación actual:</b><br><span id="panico-ubicacion">Obteniendo GPS...</span></div>
</div>
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
<div class="bottom-nav-item" onclick="switchTabEmp('tab-emp-calendario')"><div class="icon">🗓️</div>Calen</div>
<div class="bottom-nav-item" onclick="switchTabEmp('tab-emp-chat')"><div class="icon">💬</div>Chat</div>
<div class="bottom-nav-item" onclick="switchTabEmp('tab-emp-panico')"><div class="icon">🆘</div>SOS</div>
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
  if(tabId==='tab-perfil-admin') document.getElementById('topbar-title').innerText='👑 Mi Perfil Admin'; else document.getElementById('topbar-title').innerText=titles[tabId]||'Clock RD';
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
async function cargarLimpiezaStatus(){
  try{
    const s=await api('/api/limpieza/status');
    document.getElementById('limpieza-status').innerHTML=`
      <b>📊 Registros actuales:</b> ${s.total_registros_actual} total<br>
      GPS: ${s.gps_actual} | Asistencias: ${s.asistencias_actual}<br><br>
      <b>🗓️ Próximas limpiezas:</b><br>
      📍 GPS (3 meses): <b style="color:#f59e0b">${s.proxima_limpieza_gps}</b><br>
      🗂️ General (6 meses): <b style="color:#ef4444">${s.proxima_limpieza_general}</b><br><br>
      <b>✅ Siempre conserva:</b> ${s.conserva_siempre.join(', ')}<br>
      <b>🗑️ Borra GPS 3m:</b> ${s.borra_gps_3_meses.join(', ')}<br>
      <b>🗑️ Borra General 6m:</b> ${s.borra_general_6_meses.join(', ')}<br>
      <small style="color:var(--muted)">Última GPS: ${s.config.ultima_limpieza_gps||'Nunca'} | Última General: ${s.config.ultima_limpieza_general||'Nunca'}</small>
    `;
    document.getElementById('auto_limpieza_activo').checked = s.config.auto_activo!==false;
    document.getElementById('gps_meses_cfg').value = s.config.gps_meses||3;
    document.getElementById('general_meses_cfg').value = s.config.general_meses||6;
  }catch(e){ document.getElementById('limpieza-status').innerText='❌ '+e.detail; }
}
async function ejecutarLimpieza(){
  if(!confirm('¿Borrar datos viejos? GPS >3 meses y resto >6 meses. Se conservan empresas, empleados, sucursales.')) return;
  try{
    const r=await api('/api/limpieza/ejecutar','POST',{forzado:true});
    document.getElementById('msg-limpieza').innerHTML=`✅ Limpieza: GPS ${r.gps_borrados} borrados, Asistencias ${r.asistencias_borradas}, Chat ${r.chat_borrados}, Total liberado ~${r.espacio_liberado_mb} MB`;
    cargarLimpiezaStatus();
  }catch(e){ document.getElementById('msg-limpieza').innerText='❌ '+(e.detail||'Error'); }
}
async function guardarLimpiezaConfig(){
  const data={auto_activo: document.getElementById('auto_limpieza_activo').checked, gps_meses: parseInt(document.getElementById('gps_meses_cfg').value)||3, general_meses: parseInt(document.getElementById('general_meses_cfg').value)||6};
  try{ await api('/api/limpieza/config','POST',data); document.getElementById('msg-limpieza').innerText='✅ Config guardada'; cargarLimpiezaStatus(); }catch(e){ document.getElementById('msg-limpieza').innerText='❌ '+e.detail; }
}
const oldCargarTodo2 = cargarTodo;
cargarTodo = async function(){
  await oldCargarTodo2();
  cargarLimpiezaStatus();
};


async function cargarPerfilAdmin(){
  try{
    const info = await api('/api/empresa-info');
    const nombre = localStorage.getItem('nombre')||'Admin';
    const rol = localStorage.getItem('rol')||'superadmin';
    const empresa = localStorage.getItem('empresa_nombre')||info.empresa||'';
    const correo = info.correo||'';
    const telefono = info.telefono||'';
    document.getElementById('admin-perfil-info').innerHTML = `<b>${nombre}</b> - ${rol.toUpperCase()}<br>🏢 ${empresa}<br>📧 ${correo}<br>📱 ${telefono}<br><br><span style="color:#10b981">✅ Sesión activa</span> - ID: ${USER_ID}`;
    // foto si existe en localStorage o perfil_fotos
    const foto = localStorage.getItem('admin_foto') || '';
    if(foto){
      document.getElementById('admin_foto_preview').src=foto;
      document.getElementById('admin_foto_preview').style.display='block';
      document.getElementById('topbar-foto').src=foto;
      document.getElementById('topbar-foto').style.display='block';
    }
  }catch(e){}
}
async function subirFotoAdmin(){
  const file=document.getElementById('admin_foto_input').files[0];
  if(!file) return alert('Selecciona foto');
  const reader=new FileReader();
  reader.onload=async e=>{
    const foto=e.target.result;
    localStorage.setItem('admin_foto', foto);
    document.getElementById('admin_foto_preview').src=foto;
    document.getElementById('admin_foto_preview').style.display='block';
    document.getElementById('topbar-foto').src=foto;
    document.getElementById('topbar-foto').style.display='block';
    // guardar en backend también
    try{ await api('/api/empleado/'+USER_ID+'/foto','POST',{foto:foto}); }catch(e){}
    alert('✅ Foto admin actualizada');
  };
  reader.readAsDataURL(file);
}
async function cambiarPasswordAdmin(){
  const old=document.getElementById('admin_old_pass').value;
  const nw=document.getElementById('admin_new_pass').value;
  if(!old||!nw) return alert('Llena ambos');
  try{
    // intenta como empleado
    await api('/api/cambiar-password','POST',{empleado_id:USER_ID,old_password:old,new_password:nw});
    document.getElementById('msg-pass-admin').innerText='✅ Contraseña cambiada (empleado)';
  }catch(e){
    document.getElementById('msg-pass-admin').innerText='❌ '+(e.detail||'Usa recuperación si eres admin principal');
  }
}
// Hook para cargar perfil admin al cambiar tab
const originalSwitchTab = switchTab;
switchTab = function(tabId){
  originalSwitchTab(tabId);
  if(tabId==='tab-perfil-admin') cargarPerfilAdmin();
  if(tabId==='tab-emp-perfil') cargarMiPerfil();
};


<div id="modal-terminos" class="modal"><div class="modal-content" style="max-width:700px"><h3>📜 Términos y Condiciones Exclusivos</h3><div style="text-align:center;margin:12px 0"><img src="data:image/jpeg;base64,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" style="width:120px;height:120px;border-radius:50%;object-fit:cover;border:3px solid #f59e0b"></div>
<div style="background:#0f172a;border-radius:12px;padding:16px;margin-top:12px;font-size:11px;max-height:400px;overflow:auto;white-space:pre-wrap" id="terminos-contenido">
Cargando términos...
</div>
<div style="background:linear-gradient(135deg,#6366f115,#ec489915);border:1px solid #6366f133;border-radius:12px;padding:12px;margin-top:12px;font-size:11px">
<b>👨‍💻 Creador:</b> Rubén García<br>
<b>📅 Versión:</b> PRO MAX 2026<br>
<b>🔒 Licencia:</b> Exclusiva - Uso privado<br>
<b>⚠️ Nota:</b> Este sistema es propiedad exclusiva y no puede ser copiado, revendido o distribuido sin autorización.
</div>
<button class="btn btn-dark" onclick="document.getElementById('modal-terminos').style.display='none'" style="margin-top:12px">✅ Entendido</button>
</div></div>


async function cargarRolesCheckboxes(){
  try{
    const roles = await api('/api/roles');
    const container = document.getElementById('emp_roles_checkboxes');
    if(!container) return;
    container.innerHTML = Object.entries(roles).map(([id, r])=>`
      <label style="display:flex;align-items:center;gap:6px;background:#1e293b;padding:8px;border-radius:8px;cursor:pointer;font-size:11px;border-left:3px solid ${r.color}">
        <input type="checkbox" value="${id}" class="rol-chk" onchange="actualizarRolPrincipal()"> 
        <span style="color:${r.color}">●</span> ${r.nombre}
      </label>
    `).join('');
  }catch(e){ document.getElementById('emp_roles_checkboxes').innerHTML='Error cargando roles'; }
}
function actualizarRolPrincipal(){
  const checks = [...document.querySelectorAll('.rol-chk:checked')].map(c=>c.value);
  document.getElementById('emp_rol').value = checks[0]||'empleado';
}
async function cargarRolesLista(){
  try{
    const roles = await api('/api/roles');
    document.getElementById('roles-lista').innerHTML = Object.entries(roles).map(([id, r])=>`
      <div style="background:#0f172a;padding:10px;border-radius:10px;margin-top:6px;display:flex;justify-content:space-between;align-items:center;border-left:4px solid ${r.color}">
        <div style="font-size:11px"><b>${r.nombre}</b> (${id}) ${r.es_sistema?'🔒':''}<br><small style="color:#94a3b8">${r.descripcion||''} - Permisos: ${(r.permisos||[]).join(', ')}</small></div>
        ${!r.es_sistema?`<button onclick="eliminarRol('${id}')" style="padding:4px 8px;border-radius:6px;border:none;background:#ef4444;color:white;font-size:10px">🗑️</button>`:''}
      </div>
    `).join('');
  }catch(e){}
}
async function crearRolCustom(){
  const id = document.getElementById('new_rol_id').value.toLowerCase().trim();
  const nombre = document.getElementById('new_rol_nombre').value;
  const desc = document.getElementById('new_rol_desc').value;
  const color = document.getElementById('new_rol_color').value;
  const permisos = document.getElementById('new_rol_permisos').value.split(',').map(s=>s.trim()).filter(s=>s);
  if(!id||!nombre) return alert('ID y nombre obligatorios');
  try{
    await api('/api/roles','POST',{id:id, nombre:nombre, descripcion:desc, color:color, permisos:permisos});
    alert('✅ Rol '+nombre+' creado');
    document.getElementById('new_rol_id').value=''; document.getElementById('new_rol_nombre').value=''; document.getElementById('new_rol_desc').value='';
    cargarRolesCheckboxes(); cargarRolesLista();
  }catch(e){ alert('❌ '+(e.detail||'Error')); }
}
async function eliminarRol(id){
  if(!confirm('¿Eliminar rol '+id+'?')) return;
  try{ await api('/api/roles/'+id,'DELETE'); cargarRolesCheckboxes(); cargarRolesLista(); }catch(e){ alert('❌ '+e.detail); }
}
async function cargarCreadorInfo(){
  try{
    const info = await api('/api/creador-info');
    document.getElementById('creador-info-display').innerHTML = `
      <b>Nombre:</b> ${info.nombre}<br>
      <b>Empresa:</b> ${info.empresa}<br>
      <b>Versión:</b> ${info.version}<br>
      <b>Creación:</b> ${info.fecha_creacion}<br>
      <b>Licencia:</b> <span style="color:#10b981">${info.licencia}</span><br>
      <b>Descripción:</b> ${info.descripcion}
    `;
  }catch(e){}
}
async function verTerminos(){
  try{
    const data = await api('/api/terminos-condiciones');
    document.getElementById('terminos-contenido').innerText = data.terminos;
    document.getElementById('modal-terminos').style.display='flex';
  }catch(e){}
}
// Actualizar crearEmp para multi-roles
const oldCrearEmp = crearEmp;
crearEmp = async function(){
  const id=document.getElementById('emp_id').value; const nombre=document.getElementById('emp_nombre').value; const puesto=document.getElementById('emp_puesto').value; 
  const rolesChecks=[...document.querySelectorAll('.rol-chk:checked')].map(c=>c.value);
  const rolPrincipal=document.getElementById('emp_rol').value||'empleado';
  const pass=document.getElementById('emp_pass').value; const telefono=document.getElementById('emp_telefono')?.value||''; const sueldo=parseFloat(document.getElementById('emp_sueldo')?.value)||50; const comida=parseInt(document.getElementById('emp_comida').value)||120; 
  if(!nombre||!pass) return alert('Nombre y contraseña'); 
  if(!telefono) return alert('Telefono obligatorio'); 
  if(rolesChecks.length===0) return alert('Selecciona al menos 1 rol');
  const suc=[...document.querySelectorAll('.chk:checked')].map(c=>c.value); 
  const hor={lunes:document.getElementById('d-lunes').value,martes:document.getElementById('d-martes').value,miercoles:document.getElementById('d-miercoles').value,jueves:document.getElementById('d-jueves').value,viernes:document.getElementById('d-viernes').value,sabado:document.getElementById('d-sabado').value,domingo:document.getElementById('d-domingo').value}; 
  const r=await api('/empleados','POST',{id,nombre,puesto,rol:rolPrincipal,roles:rolesChecks,password:pass,telefono,sueldo_hora:sueldo,tiempo_comida:comida,sucursales_ids:suc,horario:hor,activo:true}); 
  alert(`✅ ${r.id} ${nombre} con roles: ${rolesChecks.join(', ')}`); 
  document.getElementById('emp_nombre').value=''; document.getElementById('emp_pass').value=''; document.getElementById('emp_telefono').value=''; 
  document.querySelectorAll('.rol-chk').forEach(c=>c.checked=false);
  generarID(); cargarEmps();
};
// Hook para cargar roles y creador al iniciar
const oldCargarTodo3 = cargarTodo;
cargarTodo = async function(){
  await oldCargarTodo3();
  cargarRolesCheckboxes();
  cargarRolesLista();
  cargarCreadorInfo();
  cargarLimpiezaStatus();
};

</body></html>
"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home(): return HTML
