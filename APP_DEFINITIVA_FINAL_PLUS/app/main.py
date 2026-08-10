
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import uuid, hashlib, os, json

try:
    import pytz
    TZ_MEXICO = pytz.timezone("America/Mexico_City")
except:
    pytz=None
    TZ_MEXICO=None

def get_now_mexico():
    try:
        if TZ_MEXICO:
            return datetime.now(TZ_MEXICO)
        else:
            return datetime.utcnow() - timedelta(hours=6)
    except:
        return datetime.now()

def get_now_iso():
    return get_now_mexico().isoformat()

def hash_pass(p):
    try:
        return hashlib.sha256(str(p).encode()).hexdigest()[:16]
    except:
        return str(p)[:16]

# DB init
try:
    from sqlalchemy import create_engine, Column, String, Text
    from sqlalchemy.orm import declarative_base
    HAS_SQLALCHEMY=True
except:
    HAS_SQLALCHEMY=False
    create_engine=None

DATABASE_URL = os.environ.get("DATABASE_URL","")
DB_SQLITE = "clockrd.db"
DB_FILE = "database.json"

app = FastAPI(title="BONITA SUPER")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- DB Setup ---
if HAS_SQLALCHEMY:
    try:
        def get_engine():
            url=DATABASE_URL
            if url.startswith("postgres://"):
                url=url.replace("postgres://","postgresql://",1)
            if url:
                return create_engine(url)
            else:
                return create_engine(f"sqlite:///{DB_SQLITE}", connect_args={"check_same_thread": False})
        engine=get_engine()
        Base=declarative_base()
        class AppDataDB(Base):
            __tablename__="appdata"
            key=Column(String, primary_key=True)
            value=Column(Text)
        Base.metadata.create_all(engine)
        print("DB lista")
    except Exception as e:
        print(f"DB error {e}")
        HAS_SQLALCHEMY=False

# Memoria
empleados_db={}
asistencias_db={}
sucursales_db={}
empresa_db={}
admins_db={"admin": {"password": hash_pass("admin123"), "rol":"superadmin", "nombre":"Admin Principal"}}
avisos_db=[]
auditoria_db=[]

def load_db():
    global empleados_db, sucursales_db, empresa_db, admins_db, asistencias_db, avisos_db
    try:
        if HAS_SQLALCHEMY:
            from sqlalchemy.orm import sessionmaker
            Session=sessionmaker(bind=engine)
            s=Session()
            row=s.query(AppDataDB).filter_by(key="main").first()
            if row and row.value:
                data=json.loads(row.value)
                empleados_db=data.get("empleados",{})
                sucursales_db=data.get("sucursales",{})
                empresa_db=data.get("empresa",{})
                admins_db=data.get("admins",admins_db)
                asistencias_db=data.get("asistencias",{})
                avisos_db=data.get("avisos",[])
                print("DB cargada de SQL")
            s.close()
        elif os.path.exists(DB_FILE):
            with open(DB_FILE,"r",encoding="utf-8") as f:
                data=json.load(f)
                empleados_db=data.get("empleados",{})
                empresa_db=data.get("empresa",{})
                admins_db=data.get("admins",admins_db)
                sucursales_db=data.get("sucursales",{})
    except Exception as e:
        print(f"load_db error {e}")

def save_db():
    try:
        data={"empleados":empleados_db,"sucursales":sucursales_db,"empresa":empresa_db,"admins":admins_db,"asistencias":asistencias_db,"avisos":avisos_db}
        if HAS_SQLALCHEMY:
            from sqlalchemy.orm import sessionmaker
            Session=sessionmaker(bind=engine)
            s=Session()
            j=json.dumps(data)
            row=s.query(AppDataDB).filter_by(key="main").first()
            if row:
                row.value=j
            else:
                row=AppDataDB(key="main",value=j)
                s.add(row)
            s.commit()
            s.close()
        with open(DB_FILE,"w",encoding="utf-8") as f:
            json.dump(data,f,indent=2,ensure_ascii=False)
    except Exception as e:
        print(f"save error {e}")

def audit_log(user,accion,detalle):
    try:
        auditoria_db.append({"usuario":user,"accion":accion,"detalle":detalle,"fecha":get_now_iso()})
        if len(auditoria_db)>200:
            auditoria_db.pop(0)
    except:
        pass

load_db()

# === RUTAS FIX LOGIN / REGISTRO ===

@app.post("/api/login")
def login(d: dict):
    u=(d.get("usuario") or d.get("username") or "").strip()
    p=(d.get("password") or "").strip()
    if not u or not p:
        raise HTTPException(400,"Faltan datos")
    hp=hash_pass(p)
    # 1. admins_db
    if u in admins_db:
        stored=admins_db[u].get("password","")
        if stored in [p, hp, hash_pass(p)] or hp == stored:
            audit_log(u,"login","ok")
            return {"ok":True,"rol":"admin","subrol":admins_db[u].get("rol","admin"),"usuario":u,"nombre":admins_db[u].get("nombre",u),"token":str(uuid.uuid4())}
    # 2. empresa info
    info=empresa_db.get("info",{})
    if info.get("usuario")==u and info.get("password") in [p,hp,hash_pass(p)]:
        return {"ok":True,"rol":"admin","subrol":"admin","usuario":u,"nombre":info.get("nombre_admin",u),"empresa":info.get("empresa",""),"token":str(uuid.uuid4())}
    # 3. empleados
    for eid, emp in empleados_db.items():
        if emp.get("usuario")==u or emp.get("user")==u:
            sp=emp.get("password","")
            if sp in [p,hp]:
                return {"ok":True,"rol":"empleado","usuario":u,"nombre":emp.get("nombre",u),"empleado_id":eid,"token":str(uuid.uuid4())}
    raise HTTPException(401,"Usuario o contraseña incorrectos. Si es primera vez, registra empresa.")

@app.post("/api/registro-empresa")
def registro_empresa(data: dict):
    nombre=(data.get("nombre") or data.get("nombre_admin") or "").strip()
    usuario=(data.get("usuario") or "").strip()
    empresa_nombre=(data.get("empresa") or "").strip()
    direccion=(data.get("direccion") or "").strip()
    correo=(data.get("correo") or "").strip()
    telefono=(data.get("telefono") or "").strip()
    password=(data.get("password") or "").strip()
    confirm=(data.get("confirm_password") or data.get("confirmPassword") or password).strip()
    if not all([nombre,usuario,empresa_nombre,direccion,password]):
        raise HTTPException(400,"Faltan campos obligatorios")
    if password!=confirm:
        raise HTTPException(400,"Contraseñas no coinciden")
    if usuario in admins_db:
        raise HTTPException(400,f"Usuario {usuario} ya existe, usa otro o inicia sesion")
    empresa_id="emp_"+str(uuid.uuid4())[:8]
    hp=hash_pass(password)
    info={
        "id":empresa_id,
        "nombre_admin":nombre,
        "usuario":usuario,
        "empresa":empresa_nombre,
        "direccion":direccion,
        "correo":correo,
        "telefono":telefono,
        "password":hp,
        "fecha_registro":get_now_iso()
    }
    empresa_db["info"]=info
    admins_db[usuario]={"password":hp,"rol":"admin","nombre":nombre,"empresa_id":empresa_id}
    if not sucursales_db:
        suc_id="suc_"+str(uuid.uuid4())[:8]
        sucursales_db[suc_id]={"id":suc_id,"nombre":"Matriz - "+empresa_nombre,"direccion":direccion,"empresa_id":empresa_id}
    save_db()
    audit_log(usuario,"registro","Empresa "+empresa_nombre)
    return {"ok":True,"mensaje":"Empresa registrada","usuario":usuario}

@app.get("/api/empresa-info")
def empresa_info():
    return empresa_db.get("info",{})

@app.get("/api/debug-db")
def debug_db():
    return {
        "tipo_bd":"Postgres" if DATABASE_URL else "SQLite/JSON",
        "DATABASE_URL_configurado": bool(DATABASE_URL),
        "empresas": len(empresa_db),
        "empleados": len(empleados_db),
        "sucursales": len(sucursales_db),
        "admins": list(admins_db.keys())
    }

@app.get("/api/health")
def health():
    return {"ok":True,"time":get_now_iso(),"db": bool(DATABASE_URL)}
\n@app.get("/api/manuales")
def get_manuales(): return manuales_db\n@app.post("/api/manuales")
def post_manual(data: dict):
    data["id"]=str(uuid.uuid4())[:8]; data["created_at"]=get_now_iso(); manuales_db.append(data); save_db(); return data\n@app.delete("/api/manuales/{mid}")
def del_manual(mid: str):
    global manuales_db
    manuales_db[:] = [m for m in manuales_db if m.get("id")!=mid]; save_db(); return {"ok":True}
\n@app.get("/api/mapa-vivo")
def mapa_vivo():
    # Empleados con GPS activo últimos 10 min
    from datetime import timedelta
    limite = datetime.now() - timedelta(minutes=10)
    vivos=[]
    for g in gps_logs_db[-200:]:
        try:
            f=datetime.strptime(g.get("fecha",""), "%Y-%m-%d %H:%M:%S")
            if f >= limite:
                vivos.append(g)
        except:
            pass
    # Solo último por empleado
    ultimos={}
    for v in vivos:
        ultimos[v.get("empleado_id")]=v
    return list(ultimos.values())
\n@app.get("/api/alertas-whatsapp-auto")
def alertas_auto():
    # Detecta faltas 3 días seguidos
    alertas=[]
    from collections import defaultdict
    hoy=datetime.now().date()
    for eid, emp in empleados_db.items():
        if emp.get("eliminado") or not emp.get("activo"): continue
        faltas=0
        for i in range(1,4):
            d=hoy - timedelta(days=i)
            ds=d.strftime("%Y-%m-%d")
            asist=next((a for a in asistencias_db if a["empleado_id"]==eid and a.get("fecha_dia")==ds), None)
            if not asist or not asist.get("entrada"):
                faltas+=1
        if faltas>=3:
            alertas.append({"empleado_id":eid,"nombre":emp.get("nombre"),"telefono":emp.get("telefono"),"faltas":faltas,"mensaje":f"⚠️ {emp.get('nombre')} lleva {faltas} faltas seguidas"})
    return alertas
\n@app.get("/api/empleado/{eid}/ganancias-mes")
def ganancias_mes(eid: str):
    mes=datetime.now().strftime("%Y-%m")
    asist=[a for a in asistencias_db if a["empleado_id"]==eid and a.get("fecha","")==mes]
    horas=sum([a.get("horas_trabajadas",0) for a in asist])
    emp=empleados_db.get(eid,{})
    sueldo=float(emp.get("sueldo_hora",50))
    bono=0
    # Bono si 0 retardos y 20+ dias
    retardos=sum([a.get("retardo_entrada",0)+a.get("retardo_comida",0) for a in asist])
    if retardos==0 and len(asist)>=20:
        bono=float(config_admin_db.get("bono_puntualidad",500))
    total=round(horas*sueldo+bono,2)
    return {"mes":mes,"horas":round(horas,2),"sueldo_hora":sueldo,"retardos":retardos,"dias":len(asist),"bono":bono,"total":total}

\n@app.get("/api/multas")
def get_multas(): return multas_db\n@app.post("/api/multas")
def post_multas(data: dict):
    data["id"]=str(uuid.uuid4())[:8]; data["created_at"]=get_now_iso(); multas_db.append(data); save_db(); return data\n@app.get("/api/reporte-nocturno")
def reporte_nocturno():
    hoy=datetime.now().strftime("%Y-%m-%d")
    hoy_asist=[a for a in asistencias_db if a.get("fecha_dia")==hoy]
    total_emp=len([e for e in empleados_db.values() if e.get("activo") and not e.get("eliminado")])
    presentes=len([a for a in hoy_asist if a.get("entrada")])
    retardos=len([a for a in hoy_asist if a.get("retardo_entrada",0)>0])
    faltas=total_emp-presentes
    alertas=len([a for a in alertas_db if hoy in a.get("fecha","")])
    texto=f"📊 Reporte {hoy}:\n✅ Presentes: {presentes}/{total_emp}\n⏱️ Retardos: {retardos}\n❌ Faltas: {faltas}\n🚨 Alertas: {alertas}"
    return {"texto":texto,"presentes":presentes,"total":total_emp,"retardos":retardos,"faltas":faltas}
\n@app.get("/api/db-status")
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
\n@app.post("/api/migrar-a-db")
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
\n@app.put("/api/empresa-info")
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
\n@app.post("/api/enviar-codigo-email")

def enviar_codigo_email(data: dict):
    email=data.get("email")
    codigo=str(random.randint(100000,999999))
    verificaciones_db[email]={"codigo":codigo,"tipo":"email","fecha":datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    save_db()
    # Simulación: en producción se enviaría por SMTP Gmail
    return {"ok":True,"codigo":codigo,"mensaje":f"Código enviado a {email}"}
\n@app.post("/api/enviar-codigo-whatsapp")
def enviar_codigo_whatsapp(data: dict):
    tel=data.get("telefono")
    codigo=str(random.randint(100000,999999))
    verificaciones_db[tel]={"codigo":codigo,"tipo":"whatsapp","fecha":datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    save_db()
    return {"ok":True,"codigo":codigo,"mensaje":f"Código enviado por WhatsApp a {tel}"}
\n@app.post("/api/verificar-codigo")
def verificar_codigo(data: dict):
    clave=data.get("clave") # email o telefono
    codigo=data.get("codigo")
    if clave in verificaciones_db and verificaciones_db[clave]["codigo"]==codigo:
        verificaciones_db[clave]["verificado"]=True
        save_db()
        return {"ok":True}
    raise HTTPException(400,"Código incorrecto")


\n@app.post("/api/manuales/con-imagen-v2")
async def create_manual_con_imagen_v2(titulo: str = Form(...), contenido: str = Form(...), archivo: UploadFile = File(None)):
    try:
        imagen_b64=None
        if archivo:
            content=await archivo.read()
            imagen_b64 = "data:"+ (archivo.content_type or "image/jpeg") + ";base64," + base64.b64encode(content).decode()
        nuevo={"id": str(uuid.uuid4())[:8],"titulo": titulo,"contenido": contenido,"imagen": imagen_b64,"created_at": get_now_iso()}
        manuales_db.append(nuevo)
        save_db()
        return nuevo
    except Exception as e:
        print(f"Error manual con imagen v2 {e}")
        raise HTTPException(status_code=500, detail=str(e))
\n@app.get("/api/mapa-vivo-v2")
def mapa_vivo_v2():
    hoy = get_hoy_str()
    mapa=[]
    for emp_id, emp in empleados_db.items():
        for a in reversed(asistencias_db):
            if a.get("empleado_id")==emp_id and a.get("fecha")==hoy:
                gps=a.get("gps",{}) or {}
                lat=gps.get("lat") or a.get("lat")
                lng=gps.get("lng") or a.get("lng")
                if lat and lng:
                    try:
                        mapa.append({"empleado_id": emp_id,"nombre": emp.get("nombre",""),"puesto": emp.get("puesto",""),"lat": float(lat),"lng": float(lng),"hora": a.get("hora_entrada") or a.get("hora") or "","sucursal": a.get("sucursal_id","")})
                    except: pass
                    break
    return mapa

\n@app.post("/api/recuperar-password")
def recuperar(d: dict):
    eid=d.get("empleado_id")
    if eid not in empleados_db: raise HTTPException(404, "No existe")
    nueva = str(random.randint(1000,9999)); empleados_db[eid]["password"]=hash_pass(nueva); save_db(); audit_log(eid,"recuperar_password",nueva); return {"ok":True,"nueva_password":nueva,"mensaje":f"Tu nueva contraseña temporal es: {nueva}"}
\n@app.post("/api/cambiar-password")
def cambiar_pass(d: dict):
    eid=d.get("empleado_id"); old=d.get("old_password"); new=d.get("new_password")
    if eid in empleados_db:
        if empleados_db[eid]["password"]!=old and empleados_db[eid]["password"]!=hash_pass(old): raise HTTPException(400, "Incorrecta")
        empleados_db[eid]["password"]=hash_pass(new); save_db(); return {"ok":True}
    if eid in admins_db:
        if admins_db[eid]["password"]!=hash_pass(old) and admins_db[eid]["password"]!=old: raise HTTPException(400, "Incorrecta")
        admins_db[eid]["password"]=hash_pass(new); return {"ok":True}
    raise HTTPException(404)
\n@app.get("/api/permisos")
def get_permisos(): return permisos_db\n@app.post("/api/permisos")
def save_permisos(data: dict):
    global permisos_db; permisos_db=data; save_db(); return {"ok": True}

# === AGREGADO BONITA: ASIGNACIONES POR DIA/SEMANA/MES CON EDITAR ===\n@app.get("/api/asignaciones-flex")
def get_asig_flex(): return asignaciones_flex_db
\n@app.post("/api/asignaciones-flex/dia")
def post_asig_dia(data: dict):
    global asignaciones_flex_db
    asignaciones_flex_db[:] = [a for a in asignaciones_flex_db if not (a.get("tipo")=="dia" and a.get("empleado_id")==data.get("empleado_id") and a.get("fecha")==data.get("fecha"))]
    data["id"]=str(uuid.uuid4())[:8]; data["tipo"]="dia"; data["created_at"]=get_now_iso()
    asignaciones_flex_db.append(data); save_db(); return data
\n@app.post("/api/asignaciones-flex/semana")
def post_asig_semana(data: dict):
    global asignaciones_flex_db
    asignaciones_flex_db[:] = [a for a in asignaciones_flex_db if not (a.get("tipo")=="semana" and a.get("empleado_id")==data.get("empleado_id") and a.get("semana")==data.get("semana"))]
    data["id"]=str(uuid.uuid4())[:8]; data["tipo"]="semana"; data["created_at"]=get_now_iso()
    asignaciones_flex_db.append(data); save_db(); return data
\n@app.post("/api/asignaciones-flex/mes")
def post_asig_mes(data: dict):
    global asignaciones_flex_db
    asignaciones_flex_db[:] = [a for a in asignaciones_flex_db if not (a.get("tipo")=="mes" and a.get("empleado_id")==data.get("empleado_id") and a.get("mes")==data.get("mes"))]
    data["id"]=str(uuid.uuid4())[:8]; data["tipo"]="mes"; data["created_at"]=get_now_iso()
    asignaciones_flex_db.append(data); save_db(); return data
\n@app.put("/api/asignaciones-flex/{aid}")
def put_asig_flex(aid: str, data: dict):
    global asignaciones_flex_db
    for a in asignaciones_flex_db:
        if a.get("id")==aid:
            a.update(data); save_db(); return a
    return {"error":"No existe"}
\n@app.delete("/api/asignaciones-flex/{aid}")
def del_asig_flex(aid: str):
    global asignaciones_flex_db
    asignaciones_flex_db[:] = [a for a in asignaciones_flex_db if a.get("id")!=aid]
    save_db(); return {"ok":True}
\n@app.get("/api/empleado/{eid}/hoy-flex")
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


# === AGREGADOS NUEVOS CONSERVANDO BONITA ===\n@app.get("/api/tareas-sucursal")
def get_tareas(): return tareas_sucursal_db\n@app.post("/api/tareas-sucursal")
def post_tarea(data: dict):
    data["id"]=str(uuid.uuid4())[:8]; data["created_at"]=get_now_iso(); tareas_sucursal_db.append(data); save_db(); return data\n@app.put("/api/tareas-sucursal/{tid}")
def put_tarea(tid: str, data: dict):
    for t in tareas_sucursal_db:
        if t.get("id")==tid:
            t.update(data); save_db(); return t
    return {"error":"No existe"}
\n@app.get("/api/horas-extra")
def get_he(): return horas_extra_db\n@app.post("/api/horas-extra")
def post_he(data: dict):
    data["id"]=str(uuid.uuid4())[:8]; data["created_at"]=get_now_iso(); horas_extra_db.append(data); save_db(); return data
\n@app.get("/api/export/{tipo}")
def export_tipo(tipo: str):
    # Devuelve datos para exportar en frontend a Excel
    if tipo=="asignaciones": return asignaciones_flex_db
    if tipo=="empleados": return list(empleados_db.values())[:200]
    if tipo=="evaluaciones": return evaluaciones_db[-200:]
    if tipo=="asistencias": return asistencias_db[-200:]
    return []
\n@app.get("/api/ranking-mes")
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
\n@app.get("/api/calendario-asignaciones")
def calendario_asig(mes: str = ""):
    if not mes:
        mes=datetime.now().strftime("%Y-%m")
    # Devuelve asignaciones del mes para calendario visual
    res=[a for a in asignaciones_flex_db if mes in (a.get("fecha","") or a.get("mes","") or a.get("semana",""))]
    return res
\n@app.get("/api/config-admin")
def get_config_admin(): return config_admin_db\n@app.post("/api/config-admin")
def save_config_admin(data: dict):
    global config_admin_db; config_admin_db.update(data); save_db(); return config_admin_db\n@app.get("/api/nomina/{mes}")
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
    return sorted(result, key=lambda x: x["total"], reverse=True)\n@app.get("/api/reporte-sucursales/{mes}")
def reporte_suc(mes: str):
    res=[]
    for sid, suc in sucursales_db.items():
        emps_suc=[e for e in empleados_db.values() if sid in e.get("sucursales_ids",[]) or sid in e.get("horario",{}).values()]
        asist=[a for a in asistencias_db if a.get("sucursal_id")==sid and a.get("fecha","").startswith(mes)]
        horas=sum([a.get("horas_trabajadas",0) for a in asist])
        retardos=sum([a.get("retardo_entrada",0) for a in asist])
        res.append({"sucursal_id":sid,"nombre":suc.get("nombre"),"empleados":len(emps_suc),"horas_mes":round(horas,1),"retardos_mes":retardos,"promedio_horas":round(horas/len(emps_suc),1) if emps_suc else 0})
    return sorted(res, key=lambda x: x["horas_mes"], reverse=True)\n@app.get("/api/calendario/{eid}/{mes}")
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
        raise HTTPException(400, str(e))\n@app.post("/api/notificar-whatsapp")
def notificar_whatsapp(data: dict):
    notificaciones_db.append({"id":str(uuid.uuid4())[:6],"para":data.get("para"),"mensaje":data.get("mensaje"),"tipo":data.get("tipo","info"),"fecha":datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    save_db()
    tel=data.get("para","").replace("+","").replace(" ","")
    link=f"https://wa.me/{tel}?text={data.get('mensaje','')}"
    return {"ok": True, "link": link}\n@app.get("/api/anti-trampa/log")
def anti_trampa_log():
    sospechosos=[]
    for eid in empleados_db:
        logs=[g for g in gps_logs_db if g.get("empleado_id")==eid]
        if len(logs)>=3:
            if len(set([f"{l.get('lat')},{l.get('lng')}" for l in logs[-5:]]))==1:
                sospechosos.append({"empleado_id":eid,"nombre":empleados_db[eid].get("nombre"),"motivo":"Ubicación idéntica 5 veces (posible GPS falso)","fecha":logs[-1].get("fecha")})
    return sospechosos\n@app.get("/api/empleado/{eid}/perfil")
def perfil_emp(eid: str):
    emp=empleados_db.get(eid)
    if not emp: raise HTTPException(404)
    asist_mes=[a for a in asistencias_db if a["empleado_id"]==eid]
    horas_total=sum([a.get("horas_trabajadas",0) for a in asist_mes])
    return {"empleado":emp,"horas_total":horas_total,"asistencias":len(asist_mes),"foto":perfil_fotos_db.get(eid,"")}\n@app.post("/api/empleado/{eid}/foto")
def subir_foto(eid: str, data: dict):
    perfil_fotos_db[eid]=data.get("foto","")[:500000]
    if eid in empleados_db: empleados_db[eid]["foto"]=data.get("foto","")[:500000]
    save_db()
    return {"ok": True}


\n@app.get("/api/manuales")
def get_manuales(): return manuales_db\n@app.post("/api/manuales")
def post_manual(data: dict):
    data["id"]=str(uuid.uuid4())[:8]; data["created_at"]=get_now_iso(); manuales_db.append(data); save_db(); return data\n@app.delete("/api/manuales/{mid}")
def del_manual(mid: str):
    global manuales_db
    manuales_db[:] = [m for m in manuales_db if m.get("id")!=mid]; save_db(); return {"ok":True}
\n@app.get("/api/mapa-vivo")
def mapa_vivo():
    # Empleados con GPS activo últimos 10 min
    from datetime import timedelta
    limite = datetime.now() - timedelta(minutes=10)
    vivos=[]
    for g in gps_logs_db[-200:]:
        try:
            f=datetime.strptime(g.get("fecha",""), "%Y-%m-%d %H:%M:%S")
            if f >= limite:
                vivos.append(g)
        except:
            pass
    # Solo último por empleado
    ultimos={}
    for v in vivos:
        ultimos[v.get("empleado_id")]=v
    return list(ultimos.values())
\n@app.get("/api/alertas-whatsapp-auto")
def alertas_auto():
    # Detecta faltas 3 días seguidos
    alertas=[]
    from collections import defaultdict
    hoy=datetime.now().date()
    for eid, emp in empleados_db.items():
        if emp.get("eliminado") or not emp.get("activo"): continue
        faltas=0
        for i in range(1,4):
            d=hoy - timedelta(days=i)
            ds=d.strftime("%Y-%m-%d")
            asist=next((a for a in asistencias_db if a["empleado_id"]==eid and a.get("fecha_dia")==ds), None)
            if not asist or not asist.get("entrada"):
                faltas+=1
        if faltas>=3:
            alertas.append({"empleado_id":eid,"nombre":emp.get("nombre"),"telefono":emp.get("telefono"),"faltas":faltas,"mensaje":f"⚠️ {emp.get('nombre')} lleva {faltas} faltas seguidas"})
    return alertas
\n@app.get("/api/empleado/{eid}/ganancias-mes")
def ganancias_mes(eid: str):
    mes=datetime.now().strftime("%Y-%m")
    asist=[a for a in asistencias_db if a["empleado_id"]==eid and a.get("fecha","")==mes]
    horas=sum([a.get("horas_trabajadas",0) for a in asist])
    emp=empleados_db.get(eid,{})
    sueldo=float(emp.get("sueldo_hora",50))
    bono=0
    # Bono si 0 retardos y 20+ dias
    retardos=sum([a.get("retardo_entrada",0)+a.get("retardo_comida",0) for a in asist])
    if retardos==0 and len(asist)>=20:
        bono=float(config_admin_db.get("bono_puntualidad",500))
    total=round(horas*sueldo+bono,2)
    return {"mes":mes,"horas":round(horas,2),"sueldo_hora":sueldo,"retardos":retardos,"dias":len(asist),"bono":bono,"total":total}

\n@app.get("/api/multas")
def get_multas(): return multas_db\n@app.post("/api/multas")
def post_multas(data: dict):
    data["id"]=str(uuid.uuid4())[:8]; data["created_at"]=get_now_iso(); multas_db.append(data); save_db(); return data\n@app.get("/api/reporte-nocturno")
def reporte_nocturno():
    hoy=datetime.now().strftime("%Y-%m-%d")
    hoy_asist=[a for a in asistencias_db if a.get("fecha_dia")==hoy]
    total_emp=len([e for e in empleados_db.values() if e.get("activo") and not e.get("eliminado")])
    presentes=len([a for a in hoy_asist if a.get("entrada")])
    retardos=len([a for a in hoy_asist if a.get("retardo_entrada",0)>0])
    faltas=total_emp-presentes
    alertas=len([a for a in alertas_db if hoy in a.get("fecha","")])
    texto=f"📊 Reporte {hoy}:\n✅ Presentes: {presentes}/{total_emp}\n⏱️ Retardos: {retardos}\n❌ Faltas: {faltas}\n🚨 Alertas: {alertas}"
    return {"texto":texto,"presentes":presentes,"total":total_emp,"retardos":retardos,"faltas":faltas}
\n@app.get("/api/db-status")
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
\n@app.post("/api/migrar-a-db")
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
\n@app.put("/api/empresa-info")
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
\n@app.post("/api/enviar-codigo-email")

def enviar_codigo_email(data: dict):
    email=data.get("email")
    codigo=str(random.randint(100000,999999))
    verificaciones_db[email]={"codigo":codigo,"tipo":"email","fecha":datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    save_db()
    # Simulación: en producción se enviaría por SMTP Gmail
    return {"ok":True,"codigo":codigo,"mensaje":f"Código enviado a {email}"}
\n@app.post("/api/enviar-codigo-whatsapp")
def enviar_codigo_whatsapp(data: dict):
    tel=data.get("telefono")
    codigo=str(random.randint(100000,999999))
    verificaciones_db[tel]={"codigo":codigo,"tipo":"whatsapp","fecha":datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    save_db()
    return {"ok":True,"codigo":codigo,"mensaje":f"Código enviado por WhatsApp a {tel}"}
\n@app.post("/api/verificar-codigo")
def verificar_codigo(data: dict):
    clave=data.get("clave") # email o telefono
    codigo=data.get("codigo")
    if clave in verificaciones_db and verificaciones_db[clave]["codigo"]==codigo:
        verificaciones_db[clave]["verificado"]=True
        save_db()
        return {"ok":True}
    raise HTTPException(400,"Código incorrecto")


\n@app.post("/api/manuales/con-imagen-v2")
async def create_manual_con_imagen_v2(titulo: str = Form(...), contenido: str = Form(...), archivo: UploadFile = File(None)):
    try:
        imagen_b64=None
        if archivo:
            content=await archivo.read()
            imagen_b64 = "data:"+ (archivo.content_type or "image/jpeg") + ";base64," + base64.b64encode(content).decode()
        nuevo={"id": str(uuid.uuid4())[:8],"titulo": titulo,"contenido": contenido,"imagen": imagen_b64,"created_at": get_now_iso()}
        manuales_db.append(nuevo)
        save_db()
        return nuevo
    except Exception as e:
        print(f"Error manual con imagen v2 {e}")
        raise HTTPException(status_code=500, detail=str(e))
\n@app.get("/api/mapa-vivo-v2")
def mapa_vivo_v2():
    hoy = get_hoy_str()
    mapa=[]
    for emp_id, emp in empleados_db.items():
        for a in reversed(asistencias_db):
            if a.get("empleado_id")==emp_id and a.get("fecha")==hoy:
                gps=a.get("gps",{}) or {}
                lat=gps.get("lat") or a.get("lat")
                lng=gps.get("lng") or a.get("lng")
                if lat and lng:
                    try:
                        mapa.append({"empleado_id": emp_id,"nombre": emp.get("nombre",""),"puesto": emp.get("puesto",""),"lat": float(lat),"lng": float(lng),"hora": a.get("hora_entrada") or a.get("hora") or "","sucursal": a.get("sucursal_id","")})
                    except: pass
                    break
    return mapa
\n@app.post("/api/recuperar-password")
def recuperar(d: dict):
    eid=d.get("empleado_id")
    if eid not in empleados_db: raise HTTPException(404, "No existe")
    nueva = str(random.randint(1000,9999)); empleados_db[eid]["password"]=hash_pass(nueva); save_db(); audit_log(eid,"recuperar_password",nueva); return {"ok":True,"nueva_password":nueva,"mensaje":f"Tu nueva contraseña temporal es: {nueva}"}
\n@app.post("/api/cambiar-password")
def cambiar_pass(d: dict):
    eid=d.get("empleado_id"); old=d.get("old_password"); new=d.get("new_password")
    if eid in empleados_db:
        if empleados_db[eid]["password"]!=old and empleados_db[eid]["password"]!=hash_pass(old): raise HTTPException(400, "Incorrecta")
        empleados_db[eid]["password"]=hash_pass(new); save_db(); return {"ok":True}
    if eid in admins_db:
        if admins_db[eid]["password"]!=hash_pass(old) and admins_db[eid]["password"]!=old: raise HTTPException(400, "Incorrecta")
        admins_db[eid]["password"]=hash_pass(new); return {"ok":True}
    raise HTTPException(404)
\nHTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Clock RD PRO</title>
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
<div class="sidebar-item" onclick="switchTab('tab-mapa-vivo')"><span>📍</span> Mapa Vivo</div>
<div class="sidebar-item" onclick="switchTab('tab-manuales')"><span>📚</span> Manuales</div>
<div class="sidebar-item" onclick="switchTab('tab-multas')"><span>💸</span> Multas y Metas</div>
<div class="sidebar-item" onclick="switchTab('tab-avisos')"><span>📢</span> Muro Avisos</div>
<div class="sidebar-item" onclick="switchTab('tab-buzon')"><span>🗣️</span> Buzón Anónimo</div>
<div class="sidebar-item" onclick="switchTab('tab-capacitaciones')"><span>📚</span> Capacitaciones</div>
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
<div class="card" style="border:2px solid #8b5cf6"><h3>⭐ Mis Calificaciones con Gráfica (Empleado 2)</h3><canvas id="chart-calif-emp"></canvas><div id="emp-calif-jornada-lista" style="margin-top:12px"></div></div>
</div>
<div id="tab-emp-calendario" class="tab-content"><div class="card" style="border:2px solid #6366f1"><h3>🗓️ Mi Calendario + Solicitar Vacaciones con Calendario (Empleado 4)</h3><div style="display:flex;gap:8px"><input id="emp_cal_mes" class="input" type="month" style="margin-top:0"><button class="btn btn-primary" onclick="cargarMiCalendario()" style="width:auto;margin-top:0">Ver</button></div><div id="emp-calendario-result" style="margin-top:12px;display:grid;grid-template-columns:repeat(7,1fr);gap:6px"></div><div style="display:flex;gap:12px;margin-top:10px;font-size:10px;flex-wrap:wrap"><span style="color:#10b981">● Presente</span><span style="color:#f59e0b">● Retardo</span><span style="color:#ef4444">● Ausente</span><span style="color:#8b5cf6">● Vacaciones</span></div><div style="margin-top:12px;border-top:1px solid #1e293b;padding-top:12px"><h4>🏖️ Solicitar Vacaciones tocando días</h4><div class="grid2"><input id="vac_inicio" class="input" type="date"><input id="vac_fin" class="input" type="date"></div><textarea id="vac_motivo" class="input" placeholder="Motivo..."></textarea><button class="btn btn-primary" onclick="solicitarVacaciones()">📅 Solicitar</button></div></div></div>
<div id="tab-emp-ranking" class="tab-content"><div class="card" style="border:2px solid #f59e0b"><h3>🏆 Ranking y Bono (Empleado ve su bono)</h3><div id="emp-ranking-info" style="margin-top:10px"></div><div id="emp-ganancias2"></div></div></div>
<div id="tab-emp-historial" class="tab-content"><div class="card"><h3>📊 Mi Historial</h3><canvas id="chart-horas-emp"></canvas><div id="emp-historial-lista" style="margin-top:12px;max-height:300px;overflow:auto"></div></div></div>
<div id="tab-emp-vacaciones" class="tab-content"><div class="card" style="border:2px solid #6366f1"><h3>🏖️ Vacaciones y Justificantes</h3><div id="mis-vacaciones"></div><div id="mis-justificantes" style="margin-top:12px"></div></div></div>

<div id="tab-emp-perfil" class="tab-content">
<div class="card" style="border:2px solid #8b5cf6"><h3>👤 Mi Perfil + Foto Mejorada (Empleado 1)</h3><div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap"><img id="emp_foto_preview" src="" style="width:100px;height:100px;border-radius:50%;background:#334155;object-fit:cover;border:3px solid #8b5cf6"><div><input type="file" id="emp_foto_input" accept="image/*" class="input" style="font-size:11px"><button class="btn btn-primary" onclick="subirFotoPerfil()" style="width:auto;padding:8px 12px;font-size:11px;margin-top:6px">📸 Cambiar Foto</button></div></div><div id="emp-perfil-info" style="margin-top:12px;font-size:12px;background:#0f172a;border-radius:12px;padding:12px"></div></div>
<div class="card" style="border:2px solid #f59e0b"><h3>🎮 Gamificación - Puntos y Medallas (Empleado 6)</h3><div id="emp-puntos">Cargando puntos...</div><p style="font-size:10px;color:var(--muted);margin-top:6px">Llega puntual = +20pts | 100pts=🥉 300=🥈 500=🥇 1000=🏆</p></div>
<div class="card" style="border:2px solid #f59e0b"><h3>📢 Muro de Avisos (Empleado 7)</h3><div id="emp-avisos">Cargando avisos...</div></div>
<div class="card" style="border:2px solid #8b5cf6"><h3>🗣️ Buzón Anónimo (Empleado 8)</h3><p style="font-size:11px">Envía queja/sugerencia anónima, admin no sabe quién fue</p><textarea id="buzon_texto" class="input" rows="3" placeholder="Escribe aquí anónimo..."></textarea><button class="btn btn-primary" onclick="enviarBuzon()">🗣️ Enviar Anónimo</button></div>
<div class="card" style="border:2px solid #6366f1"><h3>📚 Capacitaciones con Video (Empleado 9)</h3><div id="emp-caps">Cargando...</div></div>

<div id="tab-emp-empresa" class="tab-content">
<div class="card" style="border:2px solid #0ea5e9"><h3>🏢 Información de la Empresa</h3><div id="emp-empresa-info" style="font-size:12px;background:#0f172a;padding:12px;border-radius:12px">Cargando info empresa...</div></div>
<div class="card" style="border:2px solid #10b981"><h3>🛠️ Soporte Técnico</h3><div style="background:#0f172a;padding:12px;border-radius:12px;font-size:12px">
<p><b>📧 Email Soporte:</b> tecnorg1318@gmail.com</p>
<p><b>👤 Creador:</b> RUBEN GARCIA</p>
<p style="margin-top:8px">Si tienes problemas con la app, no puedes checar, GPS no funciona, olvidaste contraseña, contacta soporte.</p>
<button class="btn btn-success" onclick="contactarSoporte()" style="background:#25D366">📱 Contactar Soporte por WhatsApp</button>
<button class="btn btn-primary" onclick="contactarSoporteEmail()" style="margin-top:6px">📧 Contactar por Email</button>
</div></div>
<div class="card" style="border:2px solid #8b5cf6"><h3>👨‍💻 Información del Creador</h3><div style="background:linear-gradient(135deg,#8b5cf6,#ec4899);color:white;padding:16px;border-radius:12px;text-align:center">
<div style="font-size:48px">👨‍💻</div><div style="font-size:20px;font-weight:800">RUBEN GARCIA</div><div style="font-size:12px;opacity:0.9">Desarrollador de BONITA SUPER</div><div style="margin-top:10px;background:rgba(255,255,255,0.2);padding:8px;border-radius:8px;font-size:11px">Sistema de Control de Asistencia y Gestión de Personal<br>Versión SUPER V5 - 2026</div><div style="margin-top:10px;font-size:11px">📧 tecnorg1318@gmail.com<br>🏢 TECNOR - Tecnología Organizacional</div>
</div></div>
<div class="card" style="border:2px solid #f59e0b"><h3>📜 Términos y Condiciones</h3><div style="background:#0f172a;padding:12px;border-radius:12px;font-size:11px;max-height:400px;overflow:auto;white-space:pre-wrap" id="terminos-texto"></div><label style="display:flex;gap:8px;margin-top:10px;font-size:11px;align-items:center"><input type="checkbox" id="acepto_terminos"> He leído y acepto los términos y condiciones</label><button class="btn btn-warning" onclick="aceptarTerminos()">✅ Aceptar Términos</button><p id="msg-terminos" style="font-size:11px;margin-top:6px"></p></div>
</div>

<div style="display:none"><div class="card"><h3>🔑 Seguridad</h3><input id="old_pass" class="input" type="password" placeholder="Actual"><input id="new_pass" class="input" type="password" placeholder="Nueva"><button class="btn btn-primary" onclick="cambiarPassword()">🔑 Cambiar</button><p id="msg-pass" style="font-size:11px;margin-top:8px"></p></div>
<div class="card" style="border:2px solid #ec4899"><h3>📚 Manuales de Empresa (Empleado 8)</h3><div id="emp-manuales-lista">Cargando manuales...</div></div>
</div>

<div id="tab-emp-notif" class="tab-content"><div class="card"><h3>🔔 Notificaciones + Pánico Mejorado con Foto (Empleado 5)</h3><p style="font-size:11px">Cuando presionas pánico ahora toma foto frontal automática + GPS</p><div style="background:#ef444415;border:2px solid #ef4444;border-radius:16px;padding:16px;text-align:center;margin-top:12px"><h3 style="color:#ef4444">🚨 Pánico Mejorado</h3><p style="font-size:11px">Toma foto + GPS y lo manda al admin</p><button onclick="activarPanicoMejorado()" style="background:linear-gradient(135deg,#ef4444,#dc2626);color:white;border:none;padding:14px 20px;border-radius:12px;font-weight:800;width:100%;margin-top:8px">🚨 PÁNICO CON FOTO + GPS</button></div><div id="emp-notificaciones" style="margin-top:12px"></div></div></div>

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

// ===== ADMIN - EDITAR EMPLEADO COMPLETO + SUCURSAL + FECHAS =====
function editarEmpleadoCompleto(id){
 api('/api/empleado/'+id).then(e=>{
  const sucOpts = Object.entries(sucursales_db||{}).map(([sid,s])=>{
    const checked = (e.sucursales_ids||[]).includes(sid) ? 'checked' : '';
    return `<label style="display:flex;gap:6px;font-size:11px;margin:4px 0"><input type="checkbox" value="${sid}" class="edit-suc-check" ${checked}> ${s.nombre||sid}</label>`;
  }).join('') || '<span style="font-size:11px;color:#94a3b8">No hay sucursales</span>';

  const modal = `
  <div id="modal-edit-emp" style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.85);z-index:99999;display:flex;align-items:center;justify-content:center;padding:10px">
   <div style="background:#1e293b;border-radius:16px;padding:16px;width:100%;max-width:520px;max-height:92vh;overflow:auto;color:white;border:2px solid #0ea5e9">
    <h3 style="margin:0 0 12px 0;color:#0ea5e9">✏️ Editar Empleado - Todo</h3>
    <div style="display:flex;flex-direction:column;gap:8px">
     <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
      <label style="font-size:11px">ID<input id="edit_emp_id" value="${e.id||id}" disabled style="width:100%;padding:8px;border-radius:8px;background:#334155;color:white;border:1px solid #475569"></label>
      <label style="font-size:11px">Rol<select id="edit_emp_rol" style="width:100%;padding:8px;border-radius:8px;background:#0f172a;color:white;border:1px solid #475569"><option value="empleado" ${(e.rol||'empleado')=='empleado'?'selected':''}>Empleado</option><option value="supervisor" ${e.rol=='supervisor'?'selected':''}>Supervisor</option><option value="gerente" ${e.rol=='gerente'?'selected':''}>Gerente</option></select></label>
     </div>
     <label style="font-size:11px">Nombre Completo<input id="edit_emp_nombre" value="${(e.nombre||'').replace(/"/g,'&quot;')}" style="width:100%;padding:8px;border-radius:8px;background:#0f172a;color:white;border:1px solid #475569"></label>
     <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
      <label style="font-size:11px">Puesto<input id="edit_emp_puesto" value="${(e.puesto||'').replace(/"/g,'&quot;')}" style="width:100%;padding:8px;border-radius:8px;background:#0f172a;color:white;border:1px solid #475569"></label>
      <label style="font-size:11px">Teléfono<input id="edit_emp_tel" value="${e.telefono||''}" style="width:100%;padding:8px;border-radius:8px;background:#0f172a;color:white;border:1px solid #475569"></label>
     </div>
     <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
      <label style="font-size:11px">📅 Fecha Ingreso<input id="edit_emp_ingreso" type="date" value="${e.fecha_ingreso||''}" style="width:100%;padding:8px;border-radius:8px;background:#0f172a;color:white;border:1px solid #475569"></label>
      <label style="font-size:11px">🎂 Fecha Cumpleaños<input id="edit_emp_cumple" type="date" value="${e.fecha_cumpleanos||''}" style="width:100%;padding:8px;border-radius:8px;background:#0f172a;color:white;border:1px solid #475569"></label>
     </div>
     <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
      <label style="font-size:11px">Sueldo/Hora $<input id="edit_emp_sueldo" type="number" value="${e.sueldo_hora||50}" style="width:100%;padding:8px;border-radius:8px;background:#0f172a;color:white;border:1px solid #475569"></label>
      <label style="font-size:11px">Comida min<input id="edit_emp_comida" type="number" value="${e.tiempo_comida||120}" style="width:100%;padding:8px;border-radius:8px;background:#0f172a;color:white;border:1px solid #475569"></label>
     </div>
     <label style="font-size:11px">Correo<input id="edit_emp_correo" value="${e.correo||''}" placeholder="opcional" style="width:100%;padding:8px;border-radius:8px;background:#0f172a;color:white;border:1px solid #475569"></label>
     <label style="font-size:11px">Nueva Contraseña (vacío = no cambia)<input id="edit_emp_pass" type="password" placeholder="Nueva contraseña" style="width:100%;padding:8px;border-radius:8px;background:#0f172a;color:white;border:1px solid #475569"></label>
     <div style="background:#0f172a;padding:10px;border-radius:10px;border:1px solid #334155">
      <div style="font-size:12px;font-weight:800;margin-bottom:6px;color:#10b981">🏢 Sucursales Asignadas (puedes elegir varias)</div>
      <div style="max-height:120px;overflow:auto">${sucOpts}</div>
      <button onclick="editarSucursalRapido()" style="margin-top:8px;background:#0ea5e9;color:white;padding:6px 10px;border-radius:8px;border:none;font-size:11px">✏️ Editar Sucursales en pestaña Sucursales</button>
     </div>
     <div style="display:flex;gap:8px;margin-top:12px">
      <button onclick="guardarEdicionEmpleadoCompleto()" style="flex:1;background:#10b981;color:white;padding:12px;border-radius:10px;border:none;font-weight:800">💾 Guardar Todo</button>
      <button onclick="document.getElementById('modal-edit-emp').remove()" style="flex:1;background:#334155;color:white;padding:12px;border-radius:10px;border:none">❌ Cancelar</button>
     </div>
    </div>
   </div>
  </div>`;
  document.body.insertAdjacentHTML('beforeend', modal);
 }).catch(err=>alert('Error cargando empleado: '+err));
}
function guardarEdicionEmpleadoCompleto(){
 const id=document.getElementById('edit_emp_id').value;
 const sucChecks=[...document.querySelectorAll('.edit-suc-check:checked')].map(c=>c.value);
 const payload={
  nombre: document.getElementById('edit_emp_nombre').value,
  puesto: document.getElementById('edit_emp_puesto').value,
  telefono: document.getElementById('edit_emp_tel').value,
  fecha_ingreso: document.getElementById('edit_emp_ingreso').value,
  fecha_cumpleanos: document.getElementById('edit_emp_cumple').value,
  sueldo_hora: parseFloat(document.getElementById('edit_emp_sueldo').value)||50,
  rol: document.getElementById('edit_emp_rol').value,
  tiempo_comida: parseInt(document.getElementById('edit_emp_comida').value)||120,
  correo: document.getElementById('edit_emp_correo').value,
  sucursales_ids: sucChecks,
  password: document.getElementById('edit_emp_pass').value || undefined
 };
 api('/api/empleado/'+id+'/editar-completo', payload, 'POST').then(res=>{
  alert('✅ Empleado actualizado con fecha ingreso, cumpleaños y sucursales');
  document.getElementById('modal-edit-emp').remove();
  if(typeof cargarEmpleadosPro==='function') cargarEmpleadosPro();
  location.reload();
 }).catch(e=>alert('Error: '+e));
}
function editarEmpleado(id){ editarEmpleadoCompleto(id); }
function editarSucursalRapido(){ alert('Ve a Admin > Sucursales para editar nombre, dirección, GPS y radio de la sucursal'); }

// HORA REAL
let serverOffset = 0;
async function sincronizarHoraServidor(){
 try{
  const data=await api('/api/hora-servidor');
  const serverTime=new Date(data.hora_iso).getTime();
  serverOffset=serverTime-Date.now();
 }catch(e){}
}
function getHoraRealMexico(){ return new Date(Date.now()+serverOffset); }
function actualizarRelojTiempoReal(){
 const reloj=document.getElementById('reloj-tiempo-real');
 if(reloj){
  const ahora=getHoraRealMexico();
  reloj.innerHTML='🕐 Hora real: '+ahora.toLocaleString('es-MX',{timeZone:'America/Mexico_City', hour12:true, hour:'2-digit', minute:'2-digit', second:'2-digit', day:'2-digit', month:'short'})+' (CDMX)';
 }
}
setInterval(actualizarRelojTiempoReal,1000);
setTimeout(sincronizarHoraServidor,1500);
setInterval(sincronizarHoraServidor,60000);


// ===== CUMPLEAÑOS PARA TODOS =====
async function cargarCumpleanosTodos(){
 try{
  const dataMes=await api('/api/cumpleanos/mes');
  const dataHoy=await api('/api/cumpleanos/hoy');
  const contAdmin=document.getElementById('cumpleanos-admin-container');
  const contEmp=document.getElementById('cumpleanos-emp-container');
  const bannerHoy=document.getElementById('cumpleanos-hoy-banner');

  let htmlHoyBanner='';
  if(dataHoy.cumpleanos_hoy && dataHoy.cumpleanos_hoy.length>0){
   const nombres=dataHoy.cumpleanos_hoy.map(c=>c.nombre).join(', ');
   htmlHoyBanner=`<div style="background:linear-gradient(135deg,#ec4899,#8b5cf6);color:white;padding:14px;border-radius:14px;text-align:center;font-weight:800;animation:pulse 2s infinite;border:2px solid #fff;box-shadow:0 4px 20px rgba(236,72,153,0.5)"><div style="font-size:28px">🎂🎉🥳</div><div style="font-size:16px">¡HOY ES CUMPLEAÑOS DE ${nombres.toUpperCase()}!</div><div style="font-size:12px;margin-top:4px;opacity:0.9">¡Felicítalo! Que tenga un gran día 🎈</div></div><style>@keyframes pulse{0%{transform:scale(1)}50%{transform:scale(1.02)}100%{transform:scale(1)}}</style>`;
  }

  let htmlLista='';
  if(dataMes.cumpleanos && dataMes.cumpleanos.length>0){
   htmlLista=dataMes.cumpleanos.map(c=>{
    const esHoy=c.es_hoy? 'background:linear-gradient(135deg,#ec4899,#f59e0b);color:white;border:2px solid #fff;':'background:#0f172a;border:1px solid #334155';
    const badge=c.es_hoy? '🎂 ¡HOY!':'📅 Día '+c.dia;
    return `<div style="${esHoy};padding:10px;border-radius:12px;margin:6px 0;display:flex;justify-content:space-between;align-items:center"><div><div style="font-weight:800;font-size:13px">🎂 ${c.nombre}</div><div style="font-size:11px;opacity:0.8">${c.puesto} - ${c.fecha}</div></div><div style="font-size:11px;font-weight:800;background:rgba(255,255,255,0.2);padding:4px 8px;border-radius:20px">${badge}</div></div>`;
   }).join('');
  } else {
   htmlLista='<div style="font-size:11px;color:#94a3b8;text-align:center;padding:10px">No hay cumpleaños este mes. Agrega fecha de cumpleaños en Admin > Empleados > Editar</div>';
  }

  const htmlCompleto = htmlHoyBanner + `<div style="margin-top:10px"><div style="font-size:13px;font-weight:800;margin-bottom:8px;color:#ec4899">🎂 Cumpleaños de ${new Date().toLocaleString('es-MX',{month:'long'})}</div>${htmlLista}</div>`;

  if(contAdmin) contAdmin.innerHTML=htmlCompleto;
  if(contEmp) contEmp.innerHTML=htmlCompleto;
  if(bannerHoy) bannerHoy.innerHTML=htmlHoyBanner;
 }catch(e){console.log('Error cumple',e)}
}
setTimeout(cargarCumpleanosTodos,2000);
setInterval(cargarCumpleanosTodos,60000*10); // cada 10 min


// ===== AVISOS SELECTIVOS - PARA TODOS, ESPECIFICO, MULTIPLE =====
function abrirModalCrearAviso(){
 const empleadosOpts = Object.entries(empleados_db||{}).map(([id,e])=>`<label style="display:flex;gap:6px;font-size:11px;margin:3px 0"><input type="checkbox" value="${id}" class="aviso-emp-check"> ${e.nombre} - ${e.puesto}</label>`).join('');
 const modal=`
 <div id="modal-aviso" style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.85);z-index:99999;display:flex;align-items:center;justify-content:center;padding:10px">
  <div style="background:#1e293b;border-radius:16px;padding:16px;width:100%;max-width:520px;max-height:92vh;overflow:auto;color:white;border:2px solid #f59e0b">
   <h3 style="margin:0 0 10px 0;color:#f59e0b">📢 Crear Aviso</h3>
   <div style="display:flex;flex-direction:column;gap:8px">
    <input id="aviso_titulo" placeholder="Título del aviso ej: Reunión urgente" style="width:100%;padding:10px;border-radius:10px;background:#0f172a;color:white;border:1px solid #475569">
    <textarea id="aviso_mensaje" placeholder="Mensaje largo del aviso... puedes escribir mucho texto" style="width:100%;padding:10px;border-radius:10px;background:#0f172a;color:white;border:1px solid #475569;min-height:100px"></textarea>
    <label style="font-size:11px">Tipo<select id="aviso_tipo" style="width:100%;padding:8px;border-radius:8px;background:#0f172a;color:white"><option value="general">📢 General</option><option value="reunion">👥 Reunión</option><option value="cumpleanos">🎂 Cumpleaños</option><option value="importante">⚠️ Importante</option><option value="felicitacion">🎉 Felicitación</option></select></label>
    <label style="font-size:11px">¿Para quién?<select id="aviso_para" onchange="toggleAvisoPara()" style="width:100%;padding:8px;border-radius:8px;background:#0f172a;color:white"><option value="todos">👥 Para TODOS los empleados</option><option value="especifico">🎯 Para empleado(s) específico(s)</option></select></label>
    <div id="aviso_para_especifico" style="display:none;background:#0f172a;padding:10px;border-radius:10px;border:1px solid #334155;max-height:150px;overflow:auto"><div style="font-size:11px;font-weight:800;margin-bottom:6px">Selecciona empleados:</div>${empleadosOpts||'No hay empleados'}<div style="margin-top:8px;display:flex;gap:6px"><button onclick="document.querySelectorAll('.aviso-emp-check').forEach(c=>c.checked=true)" style="font-size:10px;background:#334155;color:white;padding:4px 8px;border-radius:6px;border:none">Todos</button><button onclick="document.querySelectorAll('.aviso-emp-check').forEach(c=>c.checked=false)" style="font-size:10px;background:#334155;color:white;padding:4px 8px;border-radius:6px;border:none">Ninguno</button></div></div>
    <div style="display:flex;gap:8px;margin-top:10px">
     <button onclick="guardarAvisoSelectivo()" style="flex:1;background:#f59e0b;color:white;padding:12px;border-radius:10px;border:none;font-weight:800">📢 Publicar Aviso</button>
     <button onclick="document.getElementById('modal-aviso').remove()" style="flex:1;background:#334155;color:white;padding:12px;border-radius:10px;border:none">Cancelar</button>
    </div>
   </div>
  </div>
 </div>`;
 document.body.insertAdjacentHTML('beforeend', modal);
}
function toggleAvisoPara(){
 const para=document.getElementById('aviso_para').value;
 document.getElementById('aviso_para_especifico').style.display = para==='especifico' ? 'block' : 'none';
}
function guardarAvisoSelectivo(){
 const titulo=document.getElementById('aviso_titulo').value.trim();
 const mensaje=document.getElementById('aviso_mensaje').value.trim();
 if(!titulo || !mensaje) return alert('Título y mensaje obligatorios');
 const para=document.getElementById('aviso_para').value;
 const para_ids = para==='especifico' ? [...document.querySelectorAll('.aviso-emp-check:checked')].map(c=>c.value) : [];
 if(para==='especifico' && para_ids.length===0) return alert('Selecciona al menos 1 empleado');
 const payload={titulo, mensaje, tipo: document.getElementById('aviso_tipo').value, para, para_ids, creador: 'Admin'};
 api('/api/avisos/crear', payload, 'POST').then(res=>{
  alert('✅ Aviso creado: ' + (para==='todos' ? 'Para todos' : 'Para '+para_ids.length+' empleado(s)'));
  document.getElementById('modal-aviso').remove();
  if(typeof cargarAvisos==='function') cargarAvisos();
  if(typeof cargarAvisosEmpleado==='function') cargarAvisosEmpleado();
 }).catch(e=>alert('Error: '+e));
}


// PATCH FIX LOGIN + MANUALES + MAPA - OVERRIDE
async function crearManual(){
 const tEl=document.getElementById('manual_titulo'); const cEl=document.getElementById('manual_contenido'); const fEl=document.getElementById('manual_imagen');
 if(!tEl) return alert('No hay formulario manuales');
 const t=tEl.value.trim(); const c=cEl?cEl.value.trim():''; 
 if(!t) return alert('Título obligatorio');
 if(fEl && fEl.files[0]){
   const fd=new FormData(); fd.append('titulo', t); fd.append('contenido', c); fd.append('archivo', fEl.files[0]);
   try{
     const res=await fetch('/api/manuales/con-imagen-v2',{method:'POST', body:fd});
     const data=await res.json();
     tEl.value=''; if(cEl) cEl.value=''; fEl.value='';
     if(typeof cargarManuales==='function') cargarManuales();
     alert('✅ Manual con imagen creado');
   }catch(e){ alert('Error manual: '+e); }
 } else {
   if(!c) return alert('Contenido o imagen');
   await api('/api/manuales',{titulo:t,contenido:c},'POST');
   tEl.value=''; if(cEl) cEl.value='';
   if(typeof cargarManuales==='function') cargarManuales();
 }
}
async function cargarManuales(){
 try{
  const list=await api('/api/manuales');
  const cont=document.getElementById('manuales-lista');
  if(!cont) return;
  if(!list || list.length===0){ cont.innerHTML='<p style="font-size:11px;color:#94a3b8">No hay manuales. Crea varios con texto o imágenes.</p>'; return; }
  cont.innerHTML=list.map(m=>`<div style="background:#0f172a;padding:12px;border-radius:12px;margin-top:8px;border:1px solid #334155"><div style="display:flex;justify-content:space-between"><b>📚 ${m.titulo}</b><small>${(m.created_at||'').slice(0,10)}</small></div>${m.imagen?`<img src="${m.imagen}" style="width:100%;max-height:300px;object-fit:contain;border-radius:10px;margin:8px 0;background:white">`:''}<p style="font-size:12px;white-space:pre-wrap">${m.contenido||''}</p><button onclick="eliminarManual('${m.id}')" style="background:#ef4444;color:white;border:none;padding:6px 10px;border-radius:8px;font-size:11px;margin-top:6px">🗑️ Eliminar</button></div>`).join('');
 }catch(e){ console.log(e); }
}
let mapaVivoLeaflet=null; let marcadoresMapa=[];
async function cargarMapaVivo(){
 try{
  const cont=document.getElementById('mapa-vivo-container');
  if(!cont){ console.log('No mapa container'); return; }
  if(!window.L){
   const link=document.createElement('link'); link.rel='stylesheet'; link.href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'; document.head.appendChild(link);
   const script=document.createElement('script'); script.src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'; document.head.appendChild(script);
   await new Promise(r=>script.onload=r);
  }
  let datos=[]; try{ datos=await api('/api/mapa-vivo-v2'); }catch{ datos=await api('/api/mapa-vivo'); }
  if(!mapaVivoLeaflet){
   cont.innerHTML='<div id="mapa-leaflet" style="width:100%;height:400px;border-radius:12px;z-index:1"></div><div id="mapa-lista" style="margin-top:10px"></div>';
   await new Promise(r=>setTimeout(r,500));
   mapaVivoLeaflet=L.map('mapa-leaflet').setView([19.4326,-99.1332], 11);
   L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OSM'}).addTo(mapaVivoLeaflet);
  }
  marcadoresMapa.forEach(m=>{ try{mapaVivoLeaflet.removeLayer(m);}catch(e){} }); marcadoresMapa=[];
  const listaDiv=document.getElementById('mapa-lista');
  if(!datos || datos.length===0){ if(listaDiv) listaDiv.innerHTML='<p style="font-size:11px;color:#94a3b8">No hay checadas hoy con GPS. Haz una checada de prueba con ubicación.</p>'; return; }
  const bounds=[]; datos.forEach(d=>{ try{ const marker=L.marker([d.lat, d.lng]).addTo(mapaVivoLeaflet).bindPopup(`<b>${d.nombre}</b><br>${d.puesto}<br>${d.hora}`); marcadoresMapa.push(marker); bounds.push([d.lat,d.lng]); }catch(e){} });
  if(bounds.length>0) mapaVivoLeaflet.fitBounds(bounds, {padding:[40,40]});
  if(listaDiv) listaDiv.innerHTML='<div><b style="font-size:12px">📍 En vivo hoy ('+datos.length+')</b>'+datos.map(d=>`<div style="font-size:11px;background:#0f172a;padding:6px;border-radius:8px;margin:4px 0">📍 ${d.nombre} - ${d.lat.toFixed(4)},${d.lng.toFixed(4)} - ${d.hora}</div>`).join('')+'</div>';
 }catch(e){ console.log('mapa error',e); }
}

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


// === ADMIN 2: Dashboard con gráficas reales mejorado ===
async function cargarDashboardReal(){
 try{
  const dash=await api('/admin/dashboard');
  const ctx=document.getElementById('chart-retardos');
  const ctx2=document.getElementById('chart-horas');
  if(ctx && window.Chart){
   const data=await api('/admin/reportes-graficas');
   if(window.chartRet) window.chartRet.destroy();
   window.chartRet=new Chart(ctx,{type:'bar',data:{labels:data.retardos_por_dia.labels.slice(-7),datasets:[{label:'Min retardos',data:data.retardos_por_dia.valores.slice(-7),backgroundColor:'#ef4444'}]},options:{responsive:true}});
  }
 }catch(e){console.log(e)}
}

// ADMIN 3: Chat con sonido WhatsApp
let chatAudio=new Audio('https://cdn.pixabay.com/audio/2022/03/15/audio_5d7aab4f2d.mp3');
async function cargarChatReal(){
 try{
  const chats=await api('/chat');
  const cont=document.getElementById('chat-admin-list');
  if(cont){
   cont.innerHTML=chats.slice(-30).reverse().map(c=>`<div style="background:${c.de==='admin'?'#6366f122':'#0f172a'};padding:8px;border-radius:10px;margin-top:6px;font-size:12px"><b>${c.de}</b> → ${c.para}: ${c.mensaje} <small style="color:#64748b">${c.fecha}</small> ${c.de!=='admin'?`<button onclick="responderChatRapido('${c.de}')" style="background:#25D366;color:white;border:none;padding:2px 6px;border-radius:6px;font-size:10px">↩️ Responder</button>`:''}</div>`).join('')||'Sin mensajes';
   // Sonido si hay nuevo
   if(chats.length>0 && chats[chats.length-1].de!=='admin'){
     try{chatAudio.play();}catch(e){}
   }
  }
 }catch(e){}
}
function responderChatRapido(eid){document.getElementById('chat_para').value=eid; document.getElementById('chat_msg').focus();}

// ADMIN 4: Ranking con bono automático
async function cargarRankingBono(){
 try{
  const mes=document.getElementById('nomina_mes')?.value || new Date().toISOString().slice(0,7);
  const nomina=await api('/api/nomina/'+mes);
  const cont=document.getElementById('bonos-result');
  if(cont){
   cont.innerHTML=nomina.slice(0,10).map((r,i)=>`<div style="background:${i<3?'#f59e0b15':'#0f172a'};border:${i<3?'2px solid #f59e0b':'1px solid #334155'};padding:10px;border-radius:12px;margin-top:6px;display:flex;justify-content:space-between;align-items:center"><div><b>${i==0?'🥇':i==1?'🥈':i==2?'🥉':i+1+'.'} ${r.nombre}</b><br><small>${r.horas}h - ${r.retardos}min ret - ${r.dias} días</small></div><div style="text-align:right"><div style="color:${r.bono>0?'#10b981':'#64748b'};font-weight:800">${r.bono>0?'🎉 $'+r.bono+' BONO':''}</div><div style="font-weight:800">$${r.total}</div></div></div>`).join('');
  }
 }catch(e){}
}

// ADMIN 5: Mapa vivo
async function cargarMapaVivo(){
 try{
  const vivos=await api('/api/mapa-vivo');
  const cont=document.getElementById('mapa-vivo-lista');
  const mapDiv=document.getElementById('mapa-vivo-map');
  if(cont){
   cont.innerHTML=vivos.map(v=>`<div style="background:#0f172a;padding:10px;border-radius:10px;margin-top:6px;display:flex;justify-content:space-between;align-items:center"><div><b>${v.empleado_id} - ${v.empleado_nombre||''}</b><br><small>${v.fecha} - ${v.dentro?'✅ Dentro':'❌ Fuera'} ${v.distancia?Math.round(v.distancia)+'m':''}</small></div><a href="https://www.google.com/maps?q=${v.lat},${v.lng}" target="_blank" style="background:#0ea5e9;color:white;padding:6px 10px;border-radius:8px;text-decoration:none;font-size:11px">📍 Maps</a></div>`).join('')||'Nadie con GPS activo últimos 10 min';
  }
  if(mapDiv && vivos.length>0){
   let html='<div style="padding:12px">';
   vivos.forEach(v=>{
    html+=`<div style="margin-top:6px">📍 <b>${v.empleado_nombre}</b> - <a href="https://maps.google.com/?q=${v.lat},${v.lng}" target="_blank" style="color:#60a5fa">${v.lat?.toFixed(5)},${v.lng?.toFixed(5)}</a></div>`;
   });
   html+='</div>';
   mapDiv.innerHTML=html;
  }
 }catch(e){console.log(e)}
}
function verMapaGoogle(){
 // Abre todos en Google Maps
 api('/api/mapa-vivo').then(vivos=>{
  if(vivos.length==0) return alert('Nadie activo');
  let url='https://www.google.com/maps/dir/';
  vivos.forEach(v=>{ url+=`${v.lat},${v.lng}/`; });
  window.open(url,'_blank');
 });
}

// ADMIN 6: Reporte PDF RH mejorado con fotos
async function exportarPDFRH(){
 const {jsPDF}=window.jspdf;
 const doc=new jsPDF();
 doc.setFontSize(16); doc.text('Clock RD PRO - Reporte RH',10,15);
 doc.setFontSize(10);
 let y=25;
 try{
  const data=await api('/admin/retardos-todos');
  data.forEach(r=>{
   doc.text(`${r.empleado_id} ${r.nombre} - Ret:${r.total}min - Horas:${r.horas_mes}h - Dias:${r.dias_trabajados}`,10,y);
   y+=6;
   if(y>280){doc.addPage(); y=15;}
  });
  doc.save('Reporte_RH_'+new Date().toISOString().slice(0,10)+'.pdf');
 }catch(e){alert('Error PDF');}
}

// ADMIN 7: Alertas WhatsApp auto
async function cargarAlertasAuto(){
 try{
  const alertas=await api('/api/alertas-whatsapp-auto');
  const cont=document.getElementById('alertas-auto-lista');
  if(cont){
   cont.innerHTML=alertas.map(a=>`<div style="background:#ef444415;border:1px solid #ef4444;border-radius:10px;padding:10px;margin-top:6px"><b>⚠️ ${a.nombre}</b> - ${a.faltas} faltas seguidas<br><small>${a.telefono}</small><br><button onclick="enviarWhatsAppDirect('${a.telefono}','${a.mensaje}')" style="background:#25D366;color:white;border:none;padding:6px 10px;border-radius:6px;margin-top:6px">📱 WhatsApp: ${a.mensaje}</button></div>`).join('')||'✅ Nadie con 3 faltas seguidas';
  }
 }catch(e){}
}

// ADMIN 8: Calendario visual ya existe, mejorar
async function cargarCalendarioMejorado(){
 await cargarCalendario();
}

// Manuales
async function subirManual(){
 const t=document.getElementById('manual_titulo').value;
 const c=document.getElementById('manual_contenido').value;
 if(!t||!c) return alert('Título y contenido');
 await api('/api/manuales','POST',{titulo:t,contenido:c});
 document.getElementById('manual_titulo').value=''; document.getElementById('manual_contenido').value='';
 cargarManuales();
}
async function cargarManuales(){
 try{
  const list=await api('/api/manuales');
  const cont=document.getElementById('manuales-lista');
  if(cont) cont.innerHTML=list.map(m=>`<div style="background:#0f172a;padding:10px;border-radius:10px;margin-top:6px"><b>📚 ${m.titulo}</b><br><small>${m.created_at?.slice(0,10)||''}</small><p style="font-size:12px;margin-top:6px">${m.contenido.slice(0,200)}</p><button onclick="eliminarManual('${m.id}')" style="background:#ef4444;color:white;border:none;padding:4px 8px;border-radius:6px;font-size:10px">🗑️</button></div>`).join('')||'Sin manuales';
  // Para empleado también
  const contEmp=document.getElementById('emp-manuales-lista');
  if(contEmp) contEmp.innerHTML=list.map(m=>`<div style="background:#0f172a;padding:12px;border-radius:12px;margin-top:8px"><b>📚 ${m.titulo}</b><p style="font-size:12px;margin-top:6px;white-space:pre-wrap">${m.contenido}</p></div>`).join('')||'Sin manuales';
 }catch(e){}
}
async function eliminarManual(id){if(!confirm('Eliminar?')) return; await api('/api/manuales/'+id,'DELETE'); cargarManuales();}

// EMPLEADO 1: Foto perfil mejorada ya existe, mejorar UI
// EMPLEADO 2: Calificaciones con gráfica
async function cargarCalificacionesGrafica(){
 try{
  const evals=await api('/evaluaciones/'+USER_ID);
  const ctx=document.getElementById('chart-calif-emp');
  if(ctx && evals.length>0 && window.Chart){
   const labels=evals.slice(-6).map(e=>e.fecha?.slice(5,10)||'');
   const vals=evals.slice(-6).map(e=>e.total||e.calificacion||0);
   if(window.chartCalif) window.chartCalif.destroy();
   window.chartCalif=new Chart(ctx,{type:'line',data:{labels:labels,datasets:[{label:'Calificación',data:vals,borderColor:'#8b5cf6',backgroundColor:'#8b5cf633',tension:0.4,fill:true}]},options:{responsive:true}});
  }
 }catch(e){}
}

// EMPLEADO 3: Cuánto va ganando
async function cargarGananciasMes(){
 try{
  const data=await api('/api/empleado/'+USER_ID+'/ganancias-mes');
  const cont=document.getElementById('emp-ganancias');
  if(cont){
   cont.innerHTML=`<div style="background:linear-gradient(135deg,#10b981,#06b6d4);color:white;padding:16px;border-radius:16px;text-align:center"><div style="font-size:12px;opacity:.9">💰 Vas ganando en ${data.mes}</div><div style="font-size:32px;font-weight:800">$${data.total}</div><div style="font-size:11px;margin-top:6px">${data.horas}h x $${data.sueldo_hora}/h = $${(data.horas*data.sueldo_hora).toFixed(2)} ${data.bono>0?`+ $${data.bono} bono 🎉`:''}<br>${data.dias} días - ${data.retardos}min retardo</div></div>`;
  }
 }catch(e){}
}

// EMPLEADO 5: Pánico mejorado con foto + audio
let panicoStream=null;
async function activarPanicoMejorado(){
 if(!confirm('🚨 ¿Activar PÁNICO con foto y audio?')) return;
 let fotoBase64='';
 let audioBase64='';
 try{
  // Intentar foto frontal
  const stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:'user'}});
  const video=document.createElement('video');
  video.srcObject=stream; await video.play();
  await new Promise(r=>setTimeout(r,500));
  const canvas=document.createElement('canvas');
  canvas.width=320; canvas.height=240;
  canvas.getContext('2d').drawImage(video,0,0,320,240);
  fotoBase64=canvas.toDataURL('image/jpeg',0.5);
  stream.getTracks().forEach(t=>t.stop());
 }catch(e){console.log('No foto',e)}
 try{
  const pos=await new Promise((res,rej)=>navigator.geolocation.getCurrentPosition(res,rej,{enableHighAccuracy:true,timeout:8000}));
  const data={empleado_id:USER_ID,nombre:localStorage.getItem('nombre')||USER_ID,lat:pos.coords.latitude,lng:pos.coords.longitude,mensaje:'🚨 PÁNICO CON FOTO',foto:fotoBase64};
  await api('/panico/sos','POST',data);
  alert('🚨 Pánico enviado con foto y GPS');
 }catch(e){
  await api('/panico/sos','POST',{empleado_id:USER_ID,nombre:localStorage.getItem('nombre')||USER_ID,mensaje:'🚨 PÁNICO',foto:fotoBase64});
  alert('🚨 Pánico enviado');
 }
}

// Override old activarPanico to use mejorado
const _oldPanico=typeof activarPanico!=='undefined'?activarPanico:null;
activarPanico=activarPanicoMejorado;

// Hook cargarTodo mejorado
const _origTodo2=cargarTodo;
cargarTodo=async function(){
 await _origTodo2();
 try{
  await cargarDashboardReal();
  await cargarChatReal();
  await cargarRankingBono();
  await cargarManuales();
  setInterval(cargarChatReal, 10000); // Cada 10 seg revisa chat con sonido
 }catch(e){}
};

const _origEmpPro2=cargarEmpleadoPro;
cargarEmpleadoPro=async function(){
 await _origEmpPro2();
 try{
  await cargarCalificacionesGrafica();
  await cargarGananciasMes();
  await cargarManuales();
 }catch(e){}
};


// ADMIN 2: Multas
async function crearMulta(){const min=parseInt(document.getElementById('multa_min').value); const monto=parseFloat(document.getElementById('multa_monto').value); if(!min||!monto) return alert('Min y monto'); await api('/api/multas','POST',{min_retardo:min,monto:monto}); cargarMultas();}
async function cargarMultas(){try{const list=await api('/api/multas'); document.getElementById('multas-lista').innerHTML=list.map(m=>`<div style="background:#0f172a;padding:8px;border-radius:8px;margin-top:6px">⏱️ +${m.min_retardo}min = -$${m.monto}</div>`).join('')||'Sin reglas'; const hoy=await api('/admin/retardos-todos'); let html=''; hoy.forEach(r=>{if(r.total>0){let multa=0; list.forEach(reg=>{if(r.total>=reg.min_retardo) multa+=reg.monto;}); if(multa>0) html+=`<div style="background:#ef444415;padding:6px;border-radius:6px;margin-top:4px">${r.nombre} - ${r.total}min = -$${multa}</div>`;}}); document.getElementById('multas-hoy').innerHTML=html||'Nadie con multa hoy';}catch(e){}}
function guardarSOS(){localStorage.setItem('sos_tel',document.getElementById('sos_tel').value); alert('✅ Guardado');}
// ADMIN 5: Reporte auto
async function guardarReporteAuto(){const data={hora:document.getElementById('reporte_hora').value, activo:document.getElementById('reporte_activo').checked}; await api('/api/reporte-auto','POST',data); alert('✅ Guardado');}
async function verReporteAhora(){const r=await api('/api/reporte-nocturno'); document.getElementById('reporte-preview').innerText=r.texto;}
async function enviarReporteWhatsApp(){const r=await api('/api/reporte-nocturno'); const tel=localStorage.getItem('admin_tel')||''; if(!tel) return alert('Configura tu WhatsApp en Config'); window.open(`https://wa.me/${tel}?text=${encodeURIComponent(r.texto)}`,'_blank');}

// Empleado 6: Gamificación
async function cargarPuntos(){try{const p=await api('/api/puntos'); const yo=p[USER_ID]; const cont=document.getElementById('emp-puntos'); if(cont && yo){cont.innerHTML=`<div style="background:linear-gradient(135deg,#f59e0b,#ec4899);color:white;padding:16px;border-radius:16px;text-align:center"><div style="font-size:14px">🎮 Tus Puntos</div><div style="font-size:36px;font-weight:800">${yo.puntos||0}</div><div>${(yo.medallas||[]).join(' ')}</div></div>`;} }catch(e){}}
async function sumarPuntosAuto(){ // Llamar al checar puntual
 try{const hoy=await api('/asistencia/hoy/'+USER_ID); if(hoy.retardo_entrada==0 && hoy.entrada){await api('/api/puntos/sumar','POST',{empleado_id:USER_ID,puntos:20});}}
 catch(e){}
}

// Empleado 7: Muro avisos
async function publicarAviso(){const t=document.getElementById('aviso_titulo').value; const txt=document.getElementById('aviso_texto').value; if(!t||!txt) return alert('Título y texto'); await api('/api/avisos','POST',{titulo:t,texto:txt,fecha:new Date().toISOString()}); document.getElementById('aviso_titulo').value=''; document.getElementById('aviso_texto').value=''; cargarAvisos();}
async function cargarAvisos(){try{const list=await api('/api/avisos'); const cont=document.getElementById('avisos-admin-lista'); if(cont) cont.innerHTML=list.slice(-10).reverse().map(a=>`<div style="background:#f59e0b15;border:1px solid #f59e0b;padding:10px;border-radius:10px;margin-top:6px"><b>📢 ${a.titulo}</b><br><small>${a.fecha?.slice(0,10)||''}</small><p style="font-size:12px">${a.texto}</p><button onclick="eliminarAviso('${a.id}')" style="background:#ef4444;color:white;border:none;padding:4px 8px;border-radius:6px;font-size:10px">🗑️</button></div>`).join('')||'Sin avisos'; const contEmp=document.getElementById('emp-avisos'); if(contEmp) contEmp.innerHTML=list.slice(-5).reverse().map(a=>`<div style="background:linear-gradient(135deg,#f59e0b,#ec4899);color:white;padding:12px;border-radius:12px;margin-top:8px"><b>📢 ${a.titulo}</b><p style="font-size:12px;margin-top:4px">${a.texto}</p><small>${a.fecha?.slice(0,10)||''}</small></div>`).join('')||'Sin avisos';}catch(e){}}
async function eliminarAviso(id){await api('/api/avisos/'+id,'DELETE'); cargarAvisos();}

// Empleado 8: Buzón
async function enviarBuzon(){const txt=document.getElementById('buzon_texto').value; if(!txt) return alert('Escribe'); await api('/api/buzon','POST',{texto:txt}); document.getElementById('buzon_texto').value=''; alert('✅ Enviado anónimo');}
async function cargarBuzon(){try{const list=await api('/api/buzon'); const cont=document.getElementById('buzon-admin-lista'); if(cont) cont.innerHTML=list.slice(-20).reverse().map(b=>`<div style="background:#0f172a;padding:10px;border-radius:10px;margin-top:6px"><small>${b.created_at?.slice(0,10)||''}</small><p style="font-size:12px">${b.texto}</p></div>`).join('')||'Vacío';}catch(e){}}

// Empleado 9: Capacitaciones
async function subirCapacitacion(){const t=document.getElementById('cap_titulo').value; const v=document.getElementById('cap_video').value; const d=document.getElementById('cap_desc').value; if(!t||!v) return alert('Título y video'); await api('/api/capacitaciones','POST',{titulo:t,video:v,descripcion:d}); cargarCaps();}
async function cargarCaps(){try{const list=await api('/api/capacitaciones'); const cont=document.getElementById('caps-admin-lista'); if(cont) cont.innerHTML=list.map(c=>`<div style="background:#0f172a;padding:10px;border-radius:10px;margin-top:6px"><b>📚 ${c.titulo}</b><br><a href="${c.video}" target="_blank" style="color:#60a5fa;font-size:11px">${c.video}</a><p style="font-size:11px">${c.descripcion||''}</p><small>Visto por: ${(c.vistas||[]).length} - ${(c.vistas||[]).join(', ')}</small></div>`).join('')||'Sin'; const contEmp=document.getElementById('emp-caps'); if(contEmp) contEmp.innerHTML=list.map(c=>`<div style="background:#0f172a;padding:12px;border-radius:12px;margin-top:8px"><b>📚 ${c.titulo}</b><p style="font-size:11px">${c.descripcion||''}</p><a href="${c.video}" target="_blank" style="background:#6366f1;color:white;padding:6px 10px;border-radius:6px;text-decoration:none;font-size:11px">▶️ Ver Video</a><button onclick="marcarVisto('${c.id}')" style="background:#10b981;color:white;border:none;padding:6px 10px;border-radius:6px;margin-left:6px;font-size:11px">✅ Ya lo vi</button></div>`).join('')||'Sin capacitaciones';}catch(e){}}
async function marcarVisto(cid){await api('/api/capacitaciones/'+cid+'/visto','POST',{empleado_id:USER_ID}); alert('✅ Marcado como visto'); cargarCaps();}

// Hook
const _origTodo3=cargarTodo;
cargarTodo=async function(){
 await _origTodo3();
 try{await cargarMultas(); await cargarAvisos(); await cargarBuzon(); await cargarCaps();}catch(e){}
};
const _origEmpPro3=cargarEmpleadoPro;
cargarEmpleadoPro=async function(){
 await _origEmpPro3();
 try{await cargarPuntos(); await cargarAvisos(); await cargarCaps(); await sumarPuntosAuto();}catch(e){}
};


function cambiarParaAviso(){
 const tipo=document.getElementById('aviso_para_tipo').value;
 document.getElementById('aviso_para_select').style.display=tipo==='seleccionar'?'block':'none';
 if(tipo==='seleccionar'){cargarEmpleadosParaAviso();}
}
async function cargarEmpleadosParaAviso(){
 try{
  const emps=await api('/empleados');
  const cont=document.getElementById('aviso_empleados_check');
  if(cont) cont.innerHTML=emps.filter(e=>!e.eliminado).map(e=>`<label style="display:flex;gap:6px;margin-top:4px;font-size:11px"><input type="checkbox" value="${e.id}" class="chk-aviso"> ${e.id} - ${e.nombre}</label>`).join('');
 }catch(e){}
}
async function publicarAviso(){
 const t=document.getElementById('aviso_titulo').value;
 const txt=document.getElementById('aviso_texto').value;
 const tipo=document.getElementById('aviso_para_tipo').value;
 let para='todos';
 if(tipo==='seleccionar'){
   para=[...document.querySelectorAll('.chk-aviso:checked')].map(c=>c.value);
   if(para.length==0) return alert('Selecciona al menos 1 empleado');
 }
 if(!t||!txt) return alert('Título y texto largo');
 await api('/api/avisos','POST',{titulo:t,texto:txt,para:para,fecha:new Date().toISOString()});
 document.getElementById('aviso_titulo').value=''; document.getElementById('aviso_texto').value='';
 document.getElementById('aviso-msg').innerText='✅ Aviso publicado para '+(para==='todos'?'todos':para.length+' empleados');
 cargarAvisos();
}
async function cargarAvisos(){
 try{
  const list=await api('/api/avisos');
  const cont=document.getElementById('avisos-admin-lista');
  if(cont) cont.innerHTML=list.slice(-20).reverse().map(a=>{
   let paraTxt=a.para==='todos'?'👥 Todos':Array.isArray(a.para)?'👤 '+a.para.join(', '):a.para;
   return `<div style="background:#f59e0b15;border:1px solid #f59e0b;padding:12px;border-radius:10px;margin-top:8px"><b>📢 ${a.titulo}</b> - <small style="color:#f59e0b">${paraTxt}</small><br><small>${a.fecha?.slice(0,10)||''}</small><p style="font-size:12px;white-space:pre-wrap;margin-top:6px;background:#0f172a;padding:8px;border-radius:8px">${a.texto}</p><div style="display:flex;gap:6px;margin-top:6px"><button onclick="editarAviso('${a.id}')" style="background:#6366f1;color:white;border:none;padding:4px 8px;border-radius:6px;font-size:10px">✏️ Editar</button><button onclick="eliminarAviso('${a.id}')" style="background:#ef4444;color:white;border:none;padding:4px 8px;border-radius:6px;font-size:10px">🗑️</button></div></div>`;
  }).join('')||'Sin avisos';
  // Para empleado - solo sus avisos
  const contEmp=document.getElementById('emp-avisos');
  if(contEmp){
   // Si es empleado, cargar solo sus avisos
   let empList=list;
   try{
     if(USER_ID && USER_ID!=='admin') empList=await api('/api/avisos/'+USER_ID);
   }catch(e){}
   contEmp.innerHTML=empList.slice(-5).reverse().map(a=>`<div style="background:linear-gradient(135deg,#f59e0b,#ec4899);color:white;padding:14px;border-radius:12px;margin-top:8px"><b>📢 ${a.titulo}</b><p style="font-size:12px;margin-top:6px;white-space:pre-wrap">${a.texto}</p><small>${a.fecha?.slice(0,10)||''}</small></div>`).join('')||'Sin avisos para ti';
  }
 }catch(e){console.log(e)}
}
async function editarAviso(id){
 const list=await api('/api/avisos');
 const a=list.find(x=>x.id===id); if(!a) return;
 const nuevoTitulo=prompt('Nuevo título',a.titulo); if(nuevoTitulo===null) return;
 const nuevoTexto=prompt('Nuevo texto largo',a.texto); if(nuevoTexto===null) return;
 // Borrar y crear nuevo con mismo id logic simple: actualizar via PUT no existe, hacemos delete + post con mismo para
 await api('/api/avisos/'+id,'DELETE');
 await api('/api/avisos','POST',{titulo:nuevoTitulo,texto:nuevoTexto,para:a.para,fecha:a.fecha});
 cargarAvisos();
}

// Vacaciones admin editar y autorizar desde calendario
async function cargarVacacionesAdminMejorado(){
 try{
  const vac=await api('/vacaciones');
  const cont=document.getElementById('vac-admin');
  if(cont) cont.innerHTML=vac.slice(0,20).map(v=>`<div style="background:#0f172a;padding:12px;border-radius:12px;margin-top:8px;font-size:11px;border-left:4px solid ${v.estado=='pendiente'?'#f59e0b':v.estado=='aprobado'?'#10b981':'#ef4444'}"><b>${v.empleado_id} ${v.nombre||''}</b> - ${v.tipo}<br>📅 ${v.fecha_inicio} al ${v.fecha_fin}<br>📝 ${v.motivo}<br>Estado: <b>${v.estado?.toUpperCase()}</b><br><div style="display:flex;gap:6px;margin-top:8px;flex-wrap:wrap"><button onclick="responderVac('${v.id}','aprobado')" style="padding:6px 10px;border-radius:8px;border:none;background:#10b981;color:white;font-size:11px">✅ Autorizar</button><button onclick="responderVac('${v.id}','rechazado')" style="padding:6px 10px;border-radius:8px;border:none;background:#ef4444;color:white;font-size:11px">❌ Rechazar</button><button onclick="editarVacAdmin('${v.id}')" style="padding:6px 10px;border-radius:8px;border:none;background:#6366f1;color:white;font-size:11px">✏️ Editar</button></div></div>`).join('')||'Sin solicitudes';
 }catch(e){console.log(e)}
}
async function editarVacAdmin(id){
 try{
  const vac=await api('/vacaciones');
  const v=vac.find(x=>x.id===id); if(!v) return;
  const nuevoInicio=prompt('Fecha inicio (YYYY-MM-DD)',v.fecha_inicio); if(!nuevoInicio) return;
  const nuevoFin=prompt('Fecha fin (YYYY-MM-DD)',v.fecha_fin); if(!nuevoFin) return;
  const nuevoMotivo=prompt('Motivo',v.motivo); if(nuevoMotivo===null) return;
  await api('/api/vacaciones/'+id+'/editar','PUT',{fecha_inicio:nuevoInicio,fecha_fin:nuevoFin,motivo:nuevoMotivo});
  alert('✅ Vacaciones editadas');
  cargarVacacionesAdminMejorado();
  cargarMiCalendario();
 }catch(e){alert('Error editando');}
}
// Override old cargarVacacionesAdmin
cargarVacacionesAdmin=cargarVacacionesAdminMejorado;


// EMPRESA INFO + SOPORTE + CREADOR + TERMINOS
const TERMINOS_TEXTO = `📜 TÉRMINOS Y CONDICIONES - BONITA SUPER - CONTROL DE ASISTENCIA

Última actualización: 9 de Mayo 2026
Creador: RUBEN GARCIA - tecnorg1318@gmail.com

1. OBJETO DE LA APLICACIÓN
BONITA SUPER es un sistema de control de asistencia, geolocalización, gestión de personal, evaluación, nómina y comunicación interna para empresas. Su uso es exclusivo para empleados y administradores autorizados por la empresa contratante.

2. USO DE DATOS PERSONALES Y GPS
- La app recolecta: nombre, ID empleado, foto de perfil, ubicación GPS al momento de checar entrada/salida, fotos de check-in, reportes.
- El GPS solo se activa cuando el empleado presiona "Checar Entrada/Salida" o "Pánico SOS". No rastrea en segundo plano.
- Las fotos de check-in son obligatorias si el admin lo configura, para verificar identidad y evitar suplantación.
- Al usar la app aceptas que tu ubicación sea registrada al checar para validar que estás en la sucursal asignada.

3. OBLIGACIONES DEL EMPLEADO
- Checar puntualmente en la sucursal asignada.
- No compartir tu contraseña (ID).
- No checar por otro compañero (foto y GPS lo detectan). Si se detecta suplantación, es motivo de sanción.
- Reportar fallas de GPS o app inmediatamente a soporte.

4. OBLIGACIONES DEL ADMIN/EMPRESA
- Resguardar contraseñas de admin.
- No usar datos de ubicación fuera del control de asistencia.
- Pagar bonos y nómina conforme a lo registrado.
- Dar mantenimiento a sucursales (coordenadas correctas).

5. SOPORTE TÉCNICO
- Soporte por email: tecnorg1318@gmail.com
- Tiempo de respuesta: 24-48h hábiles.
- Soporte incluye: recuperación de acceso, corrección de checadas, fallas técnicas. No incluye capacitación extra sin acuerdo.

6. PROPIEDAD INTELECTUAL
BONITA SUPER es propiedad de RUBEN GARCIA / TECNOR. Queda prohibida su copia, reventa o distribución sin autorización. La empresa contratante tiene licencia de uso, no propiedad del código.

7. DISPONIBILIDAD Y RESPALDOS
- La app usa base de datos Neon PostgreSQL para persistencia.
- Aunque se hacen respaldos, la empresa debe descargar respaldo mensual desde Config > Exportar BD.
- No nos hacemos responsables por pérdida de datos por mal uso o por no tener DATABASE_URL configurado.

8. SANCIONES Y MULTAS
- El sistema permite configurar multas automáticas por retardo. Es responsabilidad del admin informar a empleados del reglamento interno.
- La gamificación (puntos, medallas) es motivacional, no constituye obligación de pago extra salvo que el admin lo configure como bono.

9. BOTÓN PÁNICO SOS
- El botón pánico es para emergencias reales. Su mal uso puede generar sanciones.
- Al presionarlo se envía foto, GPS y alerta a admins. Usar solo en emergencia.

10. TERMINACIÓN DE USO
La empresa puede solicitar borrado de sus datos enviando email a tecnorg1318@gmail.com con asunto "Baja BONITA SUPER". Se borra en 15 días.

11. ACEPTACIÓN
Al crear empresa, registrar empleado o checar por primera vez, aceptas estos términos. Si no estás de acuerdo, no uses la app.

Contacto: RUBEN GARCIA - tecnorg1318@gmail.com
`;

function cargarEmpresaInfoEmpleado(){
 try{
  const info = document.getElementById('emp-empresa-info');
  const term = document.getElementById('terminos-texto');
  if(term) term.innerText = TERMINOS_TEXTO;
  // Cargar info empresa de API
  api('/api/empresa-info').then(data=>{
   if(info){
    if(data && data.empresa){
      info.innerHTML = `<p><b>🏢 Empresa:</b> ${data.empresa||'No registrada'}</p><p><b>📍 Dirección:</b> ${data.direccion||''}</p><p><b>👤 Admin:</b> ${data.nombre_admin||''}</p><p><b>📧 Correo:</b> ${data.correo||''}</p><p><b>📱 Tel:</b> ${data.telefono||''}</p><p><b>📅 Registro:</b> ${data.fecha_registro||''}</p>`;
    } else {
      info.innerHTML = 'Empresa no registrada aún. Contacta a tu admin.';
    }
   }
  }).catch(e=>{
   if(info) info.innerHTML = 'Cargando...';
  });
 }catch(e){console.log(e)}
}
function contactarSoporte(){
 window.open('https://wa.me/5210000000000?text='+encodeURIComponent('Hola soporte BONITA SUPER, soy '+USER_ID+' necesito ayuda'), '_blank');
}
function contactarSoporteEmail(){
 window.location.href='mailto:tecnorg1318@gmail.com?subject=Soporte BONITA SUPER - '+USER_ID+'&body=Hola Ruben, necesito ayuda con: ';
}
function aceptarTerminos(){
 const chk=document.getElementById('acepto_terminos');
 if(!chk.checked) return alert('Debes marcar que aceptas');
 localStorage.setItem('terminos_aceptados_'+USER_ID, new Date().toISOString());
 document.getElementById('msg-terminos').innerText='✅ Términos aceptados el '+new Date().toLocaleString();
 alert('✅ Gracias por aceptar los términos');
}

// Hook a cargarEmpleadoPro
const _origEmpProFinal=cargarEmpleadoPro;
cargarEmpleadoPro=async function(){
 await _origEmpProFinal();
 try{cargarEmpresaInfoEmpleado();}catch(e){}
};




// HORA REAL EN TIEMPO REAL
let serverOffset = 0;
async function sincronizarHoraServidor(){
 try{
  const data=await api('/api/hora-servidor');
  const serverTime=new Date(data.hora_iso).getTime();
  const localTime=Date.now();
  serverOffset=serverTime-localTime;
  console.log('✅ Hora sincronizada Mexico:', data.hora_mexico, 'Offset:', serverOffset);
 }catch(e){console.log('Error sync hora', e)}
}
function getHoraRealMexico(){
 const real=new Date(Date.now()+serverOffset);
 return real;
}
function actualizarRelojTiempoReal(){
 const reloj=document.getElementById('reloj-tiempo-real');
 if(reloj){
  const ahora=getHoraRealMexico();
  const horaStr=ahora.toLocaleString('es-MX',{timeZone:'America/Mexico_City', hour12:true, hour:'2-digit', minute:'2-digit', second:'2-digit', day:'2-digit', month:'short', year:'numeric'});
  reloj.innerHTML='🕐 Hora real: '+horaStr+' (CDMX)';
 }
}
setInterval(actualizarRelojTiempoReal,1000);
setTimeout(sincronizarHoraServidor,1000);
setInterval(sincronizarHoraServidor,60000); // resync cada minuto

// BANNER ESTADO BD
async function verificarEstadoBD(){
 try{
  const st=await api('/api/debug-db');
  const banner=document.getElementById('db-status-banner');
  if(banner){
   if(st.DATABASE_URL_configurado){
    banner.innerHTML=`<div style="background:#10b981;color:white;padding:10px;border-radius:10px;font-size:11px">✅ Guardado en Neon - No se borra | Empresas:${st.empresas} Empleados:${st.empleados} Sucursales:${st.sucursales}</div>`;
   } else {
    banner.innerHTML=`<div style="background:#ef4444;color:white;padding:12px;border-radius:10px;font-size:12px">❌ CRÍTICO: DATABASE_URL no configurado en Render -> Todo se borrará! Ve a Render > Environment > Add DATABASE_URL = tu link de Neon<br>Actual: ${st.tipo_bd}</div>`;
   }
  }
 }catch(e){console.log(e)}
}
setTimeout(verificarEstadoBD,2000);

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


