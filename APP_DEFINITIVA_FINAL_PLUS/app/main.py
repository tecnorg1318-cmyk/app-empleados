
"""
APP DEFINITIVA FINAL v6 - TODO + Evaluaciones Dinamicas Admin->Empleado
Incluye TODO lo anterior + Admin crea preguntas, evalua empleados, empleado ve historial
"""
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from datetime import datetime, date, time, timedelta
from typing import Optional, List, Dict, Any
import math, os, requests, uuid
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

load_dotenv()
app = FastAPI(title="Control Empleados - DEFINITIVA v6", version="6.0")

ADMIN_WHATSAPP = os.getenv("ADMIN_WHATSAPP","5212711566031")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN","")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID","")
RADIO_LIMITE = 60

def enviar_whatsapp(texto):
    if not WHATSAPP_TOKEN:
        print(f"[WA SIM {ADMIN_WHATSAPP}]: {texto}")
        return
    try:
        url=f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_ID}/messages"
        requests.post(url, headers={"Authorization":f"Bearer {WHATSAPP_TOKEN}"}, json={"messaging_product":"whatsapp","to":ADMIN_WHATSAPP,"type":"text","text":{"body":texto}}, timeout=5)
    except: pass

def distancia_m(lat1,lon1,lat2,lon2):
    R=6371000
    dlat=math.radians(lat2-lat1); dlon=math.radians(lon2-lon1)
    a=math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return R*2*math.asin(math.sqrt(a))

# DB
empresas_db = {1: {"id":1,"nombre":"Demo","subdominio":"demo","logo":"","color":"#2ecc71","activo":True}}
usuarios_db = {
    "superadmin": {"username":"superadmin","rol":"SUPER_ADMIN","empresa_id":None,"empleado_id":None,"nombre":"Programador"},
    "admin_demo": {"username":"admin_demo","rol":"COMPANY_ADMIN","empresa_id":1,"empleado_id":None,"nombre":"Admin"},
    "empleado_1": {"username":"empleado_1","rol":"EMPLEADO","empresa_id":1,"empleado_id":1,"nombre":"Ruben Garcia"},
}
empleados_db = {1: {"id":1,"empresa_id":1,"nombre":"Ruben Garcia","sucursales":[1],"horario":{"entrada":time(8,0),"salida_comida":time(14,0),"regreso_comida":time(15,0),"salida_final":time(18,0)},"descanso":6,"tolerancia":10,"consentimiento":True}}
sucursales_db = {1: {"id":1,"empresa_id":1,"nombre":"Centro","lat":19.4326,"lng":-99.1332,"radio":150}}
registros_db = []
evaluaciones_jornada_db = []
# --- NUEVO MODULO: EVALUACIONES DINAMICAS ADMIN ---
preguntas_evaluacion_db = [] # Plantilla de preguntas que crea el admin
# Ejemplo: {"id":1,"empresa_id":1,"texto":"Puntualidad","tipo":"calificacion","obligatoria":True,"max":5}
evaluaciones_admin_db = [] # Evaluaciones hechas por admin a empleados

alertas_enviadas = {}
gps_activo = {}

def get_user(x_user: str = Header(...)):
    u = usuarios_db.get(x_user)
    if not u: raise HTTPException(401,"No autenticado")
    return u

# ========== SUPER ADMIN EMPRESAS ==========
class EmpresaCreate(BaseModel):
    nombre: str
    subdominio: str
    admin_whatsapp: str
    color_primario: str = "#2ecc71"
    logo_url: Optional[str]=None
    plan: str="PRO"

@app.post("/api/super/empresas")
def crear_empresa(data: EmpresaCreate, user=Depends(get_user)):
    if user["rol"]!="SUPER_ADMIN": raise HTTPException(403,"Solo super")
    nid=max(empresas_db.keys())+1 if empresas_db else 1
    empresas_db[nid]=data.dict() | {"id":nid,"activo":True}
    return {"ok":True,"empresa":empresas_db[nid]}

@app.get("/api/app/config/{subdominio}")
def config_app(subdominio: str):
    for e in empresas_db.values():
        if e["subdominio"]==subdominio and e["activo"]:
            return e
    raise HTTPException(404,"Empresa no encontrada")

# ========== MARCAJE Y GPS (RESUMIDO) ==========
class MarcarReq(BaseModel):
    empleado_id: int
    empresa_id: int
    tipo: str
    lat: float
    lng: float
    es_mock: bool=False

@app.post("/api/marcar")
def marcar(req: MarcarReq, user=Depends(get_user)):
    emp=empleados_db.get(req.empleado_id)
    if not emp: raise HTTPException(404,"No emp")
    if req.es_mock: raise HTTPException(403,"Fake GPS")
    d=distancia_m(req.lat,req.lng,sucursales_db[1]["lat"],sucursales_db[1]["lng"])
    if d>150: raise HTTPException(400,f"Fuera rango {int(d)}m")
    registros_db.append({"empleado_id":req.empleado_id,"empresa_id":req.empresa_id,"tipo":req.tipo,"fecha":date.today().isoformat(),"hora":datetime.now().isoformat()})
    gps_activo[req.empleado_id]= req.tipo in ["ENTRADA","REGRESO_COMIDA"]
    return {"ok":True,"gps":"ON" if gps_activo[req.empleado_id] else "OFF"}

class GpsPing(BaseModel):
    empleado_id: int
    empresa_id: int
    lat: float
    lng: float

@app.post("/api/gps_ping")
def gps_ping(p: GpsPing):
    if not gps_activo.get(p.empleado_id, False): return {"tracking":"OFF"}
    suc=sucursales_db[1]
    d=distancia_m(p.lat,p.lng,suc["lat"],suc["lng"])
    if d>RADIO_LIMITE:
        enviar_whatsapp(f"🚨 {p.empleado_id} se alejó {int(d)}m")
    return {"ok":True,"dist":int(d)}

# ========== EVALUACION FINAL JORNADA (LA GORDANA) ==========
class EvalJornadaReq(BaseModel):
    compañeros_perifonearon: str
    sabes_quien_activo: Optional[str]=None
    quienes_fueron: Optional[List[str]]=None
    sucursal_id: int=1

@app.post("/api/evaluacion/jornada")
def eval_jornada(req: EvalJornadaReq, user=Depends(get_user)):
    if user["rol"]!="EMPLEADO": raise HTTPException(403,"Solo empleado")
    ev={"id":len(evaluaciones_jornada_db)+1,"empleado_id":user["empleado_id"],"nombre":user["nombre"],"fecha":date.today().isoformat(),"p1":req.compañeros_perifonearon,"p2":req.sabes_quien_activo,"quienes":req.quienes_fueron or []}
    evaluaciones_jornada_db.append(ev)
    if req.compañeros_perifonearon=="no": return {"ok":True,"mensaje":"Gracias 🙏"}
    if req.sabes_quien_activo=="no": return {"ok":True,"mensaje":"Gracias 🙏"}
    return {"ok":True,"mensaje":f"Gracias, registrado {', '.join(req.quienes_fueron or [])}"}

# ========== NUEVO: ADMIN CREA PREGUNTAS DINAMICAS ==========
class PreguntaCreate(BaseModel):
    texto: str
    tipo: str # calificacion, texto, si_no, foto
    descripcion: Optional[str]=None
    obligatoria: bool=True
    max_calificacion: int=5 # para tipo calificacion
    opciones: Optional[List[str]]=None # para tipo seleccion

@app.post("/api/admin/evaluaciones/preguntas")
def crear_pregunta(req: PreguntaCreate, user=Depends(get_user)):
    if user["rol"] not in ["COMPANY_ADMIN","SUPER_ADMIN"]: raise HTTPException(403,"Solo admin")
    nueva={"id":len(preguntas_evaluacion_db)+1,"empresa_id":user["empresa_id"],"texto":req.texto,"tipo":req.tipo,"descripcion":req.descripcion,"obligatoria":req.obligatoria,"max":req.max_calificacion,"opciones":req.opciones,"creada":datetime.now().isoformat(),"creada_por":user["username"]}
    preguntas_evaluacion_db.append(nueva)
    return {"ok":True,"pregunta":nueva}

@app.get("/api/admin/evaluaciones/preguntas")
def listar_preguntas(user=Depends(get_user)):
    if user["rol"] not in ["COMPANY_ADMIN","SUPER_ADMIN","EMPLEADO"]: raise HTTPException(403,"No auth")
    emp_id = user["empresa_id"]
    if user["rol"]=="SUPER_ADMIN": return preguntas_evaluacion_db
    return [p for p in preguntas_evaluacion_db if p["empresa_id"]==emp_id]

@app.delete("/api/admin/evaluaciones/preguntas/{pregunta_id}")
def eliminar_pregunta(pregunta_id: int, user=Depends(get_user)):
    if user["rol"] not in ["COMPANY_ADMIN","SUPER_ADMIN"]: raise HTTPException(403,"Solo admin")
    global preguntas_evaluacion_db
    preguntas_evaluacion_db = [p for p in preguntas_evaluacion_db if p["id"]!=pregunta_id]
    return {"ok":True,"mensaje":"Pregunta eliminada"}

@app.put("/api/admin/evaluaciones/preguntas/{pregunta_id}")
def editar_pregunta(pregunta_id: int, req: PreguntaCreate, user=Depends(get_user)):
    if user["rol"] not in ["COMPANY_ADMIN","SUPER_ADMIN"]: raise HTTPException(403,"Solo admin")
    for p in preguntas_evaluacion_db:
        if p["id"]==pregunta_id:
            p.update({"texto":req.texto,"tipo":req.tipo,"descripcion":req.descripcion,"max":req.max_calificacion,"opciones":req.opciones})
            return {"ok":True,"pregunta":p}
    raise HTTPException(404,"Pregunta no existe")

# ========== ADMIN EVALUA A EMPLEADO ==========
class RespuestaEvaluacion(BaseModel):
    pregunta_id: int
    calificacion: Optional[int]=None
    texto_respuesta: Optional[str]=None
    foto_url: Optional[str]=None

class EvaluarEmpleadoReq(BaseModel):
    empleado_id: int
    respuestas: List[RespuestaEvaluacion]
    comentario_general: Optional[str]=None
    fotos_evidencia: Optional[List[str]]=None

@app.post("/api/admin/evaluaciones/evaluar")
def evaluar_empleado(req: EvaluarEmpleadoReq, user=Depends(get_user)):
    if user["rol"] not in ["COMPANY_ADMIN","SUPER_ADMIN"]: raise HTTPException(403,"Solo admin evalua")
    # Validar que las preguntas existan
    for r in req.respuestas:
        if not any(p["id"]==r.pregunta_id for p in preguntas_evaluacion_db):
            raise HTTPException(404,f"Pregunta {r.pregunta_id} no existe")
    
    evaluacion={
        "id": str(uuid.uuid4())[:8],
        "empresa_id": user["empresa_id"],
        "empleado_id": req.empleado_id,
        "empleado_nombre": empleados_db.get(req.empleado_id,{}).get("nombre",f"ID {req.empleado_id}"),
        "evaluado_por": user["username"],
        "fecha": date.today().isoformat(),
        "hora": datetime.now().isoformat(),
        "respuestas": [r.dict() for r in req.respuestas],
        "comentario_general": req.comentario_general,
        "fotos": req.fotos_evidencia or [],
        "promedio": sum([r.calificacion for r in req.respuestas if r.calificacion]) / len([r for r in req.respuestas if r.calificacion]) if any(r.calificacion for r in req.respuestas) else 0
    }
    evaluaciones_admin_db.append(evaluacion)
    enviar_whatsapp(f"⭐ Nueva evaluación para {evaluacion['empleado_nombre']}: Promedio {evaluacion['promedio']:.1f}/5 - {req.comentario_general or ''}")
    return {"ok":True,"evaluacion":evaluacion}

# ========== EMPLEADO VE SU HISTORIAL DE EVALUACIONES ==========
@app.get("/api/empleado/mis_evaluaciones")
def mis_evaluaciones(user=Depends(get_user)):
    if user["rol"]=="EMPLEADO":
        return [e for e in evaluaciones_admin_db if e["empleado_id"]==user["empleado_id"]]
    # Si es admin, puede ver todas o filtrar por empleado_id query
    return evaluaciones_admin_db

@app.get("/api/empleado/evaluacion/{eval_id}")
def detalle_evaluacion(eval_id: str, user=Depends(get_user)):
    ev = next((e for e in evaluaciones_admin_db if e["id"]==eval_id), None)
    if not ev: raise HTTPException(404,"Evaluacion no encontrada")
    if user["rol"]=="EMPLEADO" and ev["empleado_id"]!=user["empleado_id"]:
        raise HTTPException(403,"No puedes ver evaluaciones de otros")
    # Enriquecer con texto de preguntas
    detalle=[]
    for r in ev["respuestas"]:
        preg=next((p for p in preguntas_evaluacion_db if p["id"]==r["pregunta_id"]), None)
        detalle.append({"pregunta":preg["texto"] if preg else "Pregunta eliminada","tipo":preg["tipo"] if preg else "","respuesta":r})
    return {"evaluacion":ev,"detalle":detalle}

@app.get("/api/admin/evaluaciones/reporte")
def reporte_evaluaciones(empleado_id: Optional[int]=None, user=Depends(get_user)):
    if user["rol"] not in ["COMPANY_ADMIN","SUPER_ADMIN"]: raise HTTPException(403,"Solo admin")
    data=evaluaciones_admin_db
    if empleado_id:
        data=[e for e in data if e["empleado_id"]==empleado_id]
    # Calcular promedio general por empleado
    from collections import defaultdict
    proms=defaultdict(list)
    for e in data: proms[e["empleado_id"]].append(e["promedio"])
    resumen=[{"empleado_id":k,"nombre":empleados_db.get(k,{}).get("nombre",str(k)),"promedio_general":sum(v)/len(v) if v else 0,"total_evaluaciones":len(v)} for k,v in proms.items()]
    return {"evaluaciones":data,"resumen":resumen}

@app.get("/")
def root():
    return {"version":"DEFINITIVA v6 - TODO","nuevo":"Admin crea preguntas dinamicas + evalua con calificacion/comentario/fotos + empleado ve historial"}

scheduler=BackgroundScheduler()
scheduler.start()
