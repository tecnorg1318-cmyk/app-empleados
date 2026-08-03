from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import uuid, math, json, os, hashlib

app = FastAPI(title="Control ULTRA DEFINITIVA - Todo menos QR/Facial")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DB_FILE = "database.json"

def hash_pass(p): return hashlib.sha256(p.encode()).hexdigest()[:16]

def load_db():
    global sucursales_db, empleados_db, evaluaciones_db, asistencias_db, alertas_db, gps_logs_db, vacaciones_db, justificantes_db, audit_db, chat_db, panico_db
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE,'r', encoding='utf-8') as f:
                data=json.load(f)
                sucursales_db=data.get("sucursales",{})
                empleados_db=data.get("empleados",{"EMP0001": {"id":"EMP0001","nombre":"Empleado Prueba","puesto":"Botarga","password":hash_pass("0001"),"sucursales_ids":[],"horario":{},"activo":True,"tiempo_comida":120,"telefono":"","foto_perfil":""}})
                evaluaciones_db=data.get("evaluaciones",[])
                asistencias_db=data.get("asistencias",[])
                alertas_db=data.get("alertas",[])
                gps_logs_db=data.get("gps_logs",[])
                vacaciones_db=data.get("vacaciones",[])
                justificantes_db=data.get("justificantes",[])
                audit_db=data.get("audit",[])
                chat_db=data.get("chat",[])
                panico_db=data.get("panico",[])
                return
        except: pass
    sucursales_db = {}
    empleados_db = {"EMP0001": {"id":"EMP0001","nombre":"Empleado Prueba","puesto":"Botarga","password":hash_pass("0001"),"sucursales_ids":[],"horario":{},"activo":True,"tiempo_comida":120,"telefono":"","foto_perfil":""}}
    evaluaciones_db = []; asistencias_db=[]; alertas_db=[]; gps_logs_db=[]; vacaciones_db=[]; justificantes_db=[]; audit_db=[]; chat_db=[]; panico_db=[]

def save_db():
    try:
        with open(DB_FILE,'w', encoding='utf-8') as f:
            json.dump({"sucursales":sucursales_db,"empleados":empleados_db,"evaluaciones":evaluaciones_db,"asistencias":asistencias_db,"alertas":alertas_db,"gps_logs":gps_logs_db,"vacaciones":vacaciones_db,"justificantes":justificantes_db,"audit":audit_db,"chat":chat_db,"panico":panico_db}, f, ensure_ascii=False, indent=2)
    except Exception as e: print("save error",e)

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
            if eid.startswith("EMP"):
                num=int(eid.replace("EMP",""))
                if num>max_num: max_num=num
        except: pass
    return f"EMP{max_num+1:04d}"

def distancia_m(lat1, lon1, lat2, lon2):
    try:
        R=6371000
        phi1=math.radians(lat1); phi2=math.radians(lat2)
        dphi=math.radians(lat2-lat1); dlambda=math.radians(lon2-lon1)
        a=math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        c=2*math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R*c
    except: return 0

def limpiar_gps_antiguo():
    limite = datetime.now() - timedelta(days=DIAS_RETENCION)
    def es_reciente(fecha_str):
        try: f = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M:%S"); return f >= limite
        except: return True
    gps_logs_db[:] = [g for g in gps_logs_db if es_reciente(g.get("fecha",""))]
    alertas_db[:] = [a for a in alertas_db if a.get("tipo")!="gps_fuera" or es_reciente(a.get("fecha",""))]

@app.post("/api/login")
def login(d: dict):
    u=d.get("usuario"); p=d.get("password")
    hp=hash_pass(p)
    if u=="admin" and (p=="admin123" or hp==hash_pass("admin123")): audit_log(u,"login","admin login"); return {"rol":"admin","usuario":u}
    if u in empleados_db:
        emp=empleados_db[u]
        if not emp.get("activo",True): raise HTTPException(403, "DESACTIVADO")
        if emp.get("password")==p or emp.get("password")==hp or emp.get("password")==hash_pass("0001") and p=="0001":
            audit_log(u,"login",f"empleado {u} login"); return {"rol":"empleado","usuario":u,"nombre":emp["nombre"]}
        # compatibilidad con viejas contraseñas sin hash
        if emp.get("password")==p or emp.get("password")==hp:
            return {"rol":"empleado","usuario":u,"nombre":emp["nombre"]}
        raise HTTPException(401, "Contraseña incorrecta")
    raise HTTPException(401, "No existe")

@app.post("/api/cambiar-password")
def cambiar_pass(d: dict):
    eid=d.get("empleado_id"); old=d.get("old_password"); new=d.get("new_password")
    if eid not in empleados_db: raise HTTPException(404)
    stored=empleados_db[eid]["password"]
    if stored!=old and stored!=hash_pass(old): raise HTTPException(400, "Contraseña actual incorrecta")
    empleados_db[eid]["password"]=hash_pass(new)
    audit_log(eid,"cambiar_password","cambio password"); save_db()
    return {"ok":True}

@app.get("/empleados/next-id")
def next_id(): return {"next_id": get_next_id()}
@app.get("/sucursales")
def ls(): return list(sucursales_db.values())
@app.post("/sucursales")
def cs(s: dict): sucursales_db[s["id"]]=s; audit_log("admin","crear_sucursal",s["id"]); save_db(); return s
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
    empleados_db[e["id"]]=e; audit_log("admin","crear_empleado",e["id"]); save_db(); return e
@app.put("/empleados/{eid}")
def upd(eid: str, data: dict):
    if eid not in empleados_db: raise HTTPException(404)
    if "password" in data and data["password"]: data["password"]=hash_pass(data["password"])
    empleados_db[eid].update(data); audit_log("admin","editar_empleado",eid); save_db(); return empleados_db[eid]
@app.put("/empleados/{eid}/toggle")
def toggle(eid: str):
    if eid not in empleados_db: raise HTTPException(404)
    empleados_db[eid]["activo"]=not empleados_db[eid].get("activo",True)
    audit_log("admin","toggle_empleado",f"{eid} -> {empleados_db[eid]['activo']}"); save_db(); return empleados_db[eid]
@app.delete("/empleados/{eid}")
def delete_emp(eid: str):
    if eid in empleados_db: 
        audit_log("admin","eliminar_empleado",eid)
        # papelera
        empleados_db[eid]["activo"]=False
        empleados_db[eid]["eliminado"]=True
        empleados_db[eid]["fecha_eliminado"]=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_db()
    return {"ok":True}

# VACACIONES
@app.post("/vacaciones/solicitar")
def solicitar_vac(data: dict):
    vac={"id":str(uuid.uuid4())[:8],"empleado_id":data.get("empleado_id"),"tipo":data.get("tipo","vacaciones"),"fecha_inicio":data.get("fecha_inicio"),"fecha_fin":data.get("fecha_fin"),"motivo":data.get("motivo",""),"estado":"pendiente","fecha_solicitud":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"nombre":empleados_db.get(data.get("empleado_id"),{}).get("nombre","")}
    vacaciones_db.append(vac)
    alertas_db.append({"id":str(uuid.uuid4())[:6],"empleado_id":vac["empleado_id"],"mensaje":f"📅 Solicitud {vac['tipo']} {vac['fecha_inicio']} al {vac['fecha_fin']} - Pendiente","fecha":vac["fecha_solicitud"],"tipo":"vacaciones"})
    save_db(); return vac
@app.get("/vacaciones/{eid}")
def vac_emp(eid: str): return [v for v in vacaciones_db if v["empleado_id"]==eid][::-1]
@app.get("/vacaciones")
def vac_todos(): return vacaciones_db[::-1]
@app.put("/vacaciones/{vid}/estado")
def vac_estado(vid: str, data: dict):
    v=next((x for x in vacaciones_db if x["id"]==vid), None)
    if not v: raise HTTPException(404)
    v["estado"]=data.get("estado","pendiente")
    v["respuesta_admin"]=data.get("comentario","")
    alertas_db.append({"id":str(uuid.uuid4())[:6],"empleado_id":v["empleado_id"],"mensaje":f"📅 Tu solicitud {v['tipo']} {v['fecha_inicio']} fue {v['estado'].upper()}","fecha":datetime.now().strftime("%Y-%m-%d %H:%M"),"tipo":"vacaciones"})
    save_db(); return v

# JUSTIFICANTES
@app.post("/justificantes/subir")
def subir_just(data: dict):
    j={"id":str(uuid.uuid4())[:8],"empleado_id":data.get("empleado_id"),"fecha":data.get("fecha"),"tipo":data.get("tipo","enfermedad"),"motivo":data.get("motivo",""),"foto":data.get("foto",""),"estado":"pendiente","fecha_subida":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"nombre":empleados_db.get(data.get("empleado_id"),{}).get("nombre","")}
    justificantes_db.append(j)
    alertas_db.append({"id":str(uuid.uuid4())[:6],"empleado_id":j["empleado_id"],"mensaje":f"📄 Justificante {j['tipo']} {j['fecha']} subido - Pendiente revisión","fecha":j["fecha_subida"],"tipo":"justificante"})
    save_db(); return j
@app.get("/justificantes/{eid}")
def just_emp(eid: str): return [j for j in justificantes_db if j["empleado_id"]==eid][::-1]
@app.get("/justificantes")
def just_todos(): return justificantes_db[::-1]
@app.put("/justificantes/{jid}/estado")
def just_estado(jid: str, data: dict):
    j=next((x for x in justificantes_db if x["id"]==jid), None)
    if not j: raise HTTPException(404)
    j["estado"]=data.get("estado","pendiente")
    save_db(); return j

# CHAT
@app.post("/chat/enviar")
def chat_enviar(data: dict):
    msg={"id":str(uuid.uuid4())[:8],"de":data.get("de"),"para":data.get("para"),"mensaje":data.get("mensaje"),"fecha":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"leido":False}
    chat_db.append(msg)
    if data.get("para")!="admin":
        alertas_db.append({"id":str(uuid.uuid4())[:6],"empleado_id":data.get("para"),"mensaje":f"💬 Nuevo mensaje de {data.get('de')}: {data.get('mensaje')[:30]}...","fecha":msg["fecha"],"tipo":"chat"})
    else:
        alertas_db.append({"id":str(uuid.uuid4())[:6],"empleado_id":"admin","mensaje":f"💬 Mensaje de {data.get('de')}: {data.get('mensaje')[:30]}...","fecha":msg["fecha"],"tipo":"chat","de":data.get("de")})
    save_db(); return msg

@app.get("/chat/{eid}")
def chat_get(eid: str):
    # chat entre eid y admin o entre empleados
    msgs=[m for m in chat_db if m["de"]==eid or m["para"]==eid or (m["de"]=="admin" and m["para"]==eid) or (eid=="admin")]
    return msgs[-100:]

@app.get("/chat")
def chat_all(): return chat_db[-100:]

# PANICO
@app.post("/panico/sos")
def sos(data: dict):
    alerta={"id":str(uuid.uuid4())[:6],"empleado_id":data.get("empleado_id"),"nombre":empleados_db.get(data.get("empleado_id"),{}).get("nombre",""),"lat":data.get("lat"),"lng":data.get("lng"),"mensaje":data.get("mensaje","¡EMERGENCIA SOS!"),"fecha":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"tipo":"panico"}
    panico_db.append(alerta)
    alertas_db.append({"id":alerta["id"],"empleado_id":alerta["empleado_id"],"mensaje":f"🆘 SOS PÁNICO de {alerta['nombre']} - {alerta['mensaje']} - Ubicación: {alerta['lat']},{alerta['lng']}","fecha":alerta["fecha"],"tipo":"panico","lat":alerta["lat"],"lng":alerta["lng"]})
    save_db(); return {"ok":True,"alerta":alerta}
@app.get("/panico/todos")
def panico_todos(): return panico_db[::-1]

# DASHBOARD
@app.get("/admin/dashboard")
def dashboard():
    hoy=datetime.now().strftime("%Y-%m-%d")
    mes=datetime.now().strftime("%Y-%m")
    hoy_asist=[a for a in asistencias_db if a["fecha_dia"]==hoy]
    mes_asist=[a for a in asistencias_db if a.get("fecha")==mes]
    total_emp=len([e for e in empleados_db.values() if e.get("activo") and not e.get("eliminado")])
    presentes_hoy=len([a for a in hoy_asist if a.get("entrada")])
    retardos_hoy=len([a for a in hoy_asist if a.get("retardo_entrada",0)>0])
    retardo_comida_hoy=len([a for a in hoy_asist if a.get("retardo_comida",0)>0])
    horas_mes=round(sum([a.get("horas_trabajadas",0) for a in mes_asist]),1)
    retardo_entrada_mes=round(sum([a.get("retardo_entrada",0) for a in mes_asist]),1)
    retardo_comida_mes=round(sum([a.get("retardo_comida",0) for a in mes_asist]),1)
    gps_alertas=len([a for a in alertas_db if a.get("tipo")=="gps_fuera" and hoy in a.get("fecha","")])
    vacaciones_pend=len([v for v in vacaciones_db if v["estado"]=="pendiente"])
    panico_hoy=len([p for p in panico_db if hoy in p.get("fecha","")])
    justificantes_pend=len([j for j in justificantes_db if j["estado"]=="pendiente"])
    # ranking puntualidad
    ranking=[]
    for eid, emp in empleados_db.items():
        if not emp.get("activo") or emp.get("eliminado"): continue
        asist=[a for a in asistencias_db if a["empleado_id"]==eid and a.get("fecha")==mes]
        total_ret=sum([a.get("retardo_entrada",0)+a.get("retardo_comida",0) for a in asist])
        ranking.append({"id":eid,"nombre":emp.get("nombre"),"retardos":total_ret,"dias":len(asist),"horas":round(sum([a.get("horas_trabajadas",0) for a in asist]),1)})
    ranking=sorted(ranking, key=lambda x: x["retardos"])
    return {"fecha":hoy,"mes":mes,"total_empleados":total_emp,"presentes_hoy":presentes_hoy,"ausentes_hoy":total_emp-presentes_hoy,"retardos_hoy":retardos_hoy,"retardo_comida_hoy":retardo_comida_hoy,"horas_mes":horas_mes,"retardo_entrada_mes":retardo_entrada_mes,"retardo_comida_mes":retardo_comida_mes,"gps_alertas_hoy":gps_alertas,"vacaciones_pendientes":vacaciones_pend,"panico_hoy":panico_hoy,"justificantes_pend":justificantes_pend,"ranking":ranking[:10]}

@app.get("/admin/compañeros-hoy/{suc_id}")
def companeros_hoy(suc_id: str):
    hoy=datetime.now().strftime("%Y-%m-%d")
    dias=["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]
    dia_hoy=dias[datetime.now().weekday()]
    trabajando=[]
    for eid, emp in empleados_db.items():
        if not emp.get("activo") or emp.get("eliminado"): continue
        hor=emp.get("horario",{}).get(dia_hoy,"")
        if hor==suc_id or suc_id in emp.get("sucursales_ids",[]):
            asist=next((a for a in asistencias_db if a["empleado_id"]==eid and a["fecha_dia"]==hoy), None)
            trabajando.append({"id":eid,"nombre":emp.get("nombre"),"puesto":emp.get("puesto"),"entrada":asist.get("entrada") if asist else None,"estado":"presente" if asist and asist.get("entrada") else "ausente"})
    return trabajando

@app.get("/asistencia/hoy/{eid}")
def asistencia_hoy(eid: str):
    hoy=datetime.now().strftime("%Y-%m-%d")
    reg = next((a for a in asistencias_db if a["empleado_id"]==eid and a["fecha_dia"]==hoy), None)
    tiempo = empleados_db.get(eid,{}).get("tiempo_comida",120)
    dias=["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]
    suc_id=empleados_db.get(eid,{}).get("horario",{}).get(dias[datetime.now().weekday()],"")
    suc=sucursales_db.get(suc_id, {})
    base={"empleado_id":eid,"fecha_dia":hoy,"tiempo_permitido":tiempo,"sucursal":suc}
    if not reg:
        return {**base,"estado":"sin_entrada","siguiente":"entrada","texto_boton":"📍 ENTRADA + Foto","color":"#10b981","gps_activo":False}
    if not reg.get("entrada"):
        return {**reg,**base,"estado":"sin_entrada","siguiente":"entrada","texto_boton":"📍 ENTRADA + Foto","color":"#10b981","gps_activo":False}
    if not reg.get("salida_comida"):
        return {**reg,**base,"estado":"trabajando","siguiente":"salida_comida","texto_boton":"🍔 SALIDA COMER + Foto","color":"#f59e0b","gps_activo":True}
    if not reg.get("regreso_comida"):
        return {**reg,**base,"estado":"comiendo","siguiente":"regreso_comida","texto_boton":"↩️ REGRESO COMIDA + Foto","color":"#6366f1","gps_activo":False}
    if not reg.get("salida_final"):
        return {**reg,**base,"estado":"trabajando_tarde","siguiente":"salida_final","texto_boton":"🏠 SALIDA FINAL + Foto","color":"#ef4444","gps_activo":True}
    return {**reg,**base,"estado":"completo","siguiente":"completo","texto_boton":"✅ COMPLETADA","color":"#64748b","gps_activo":False}

@app.post("/asistencia/registrar")
def registrar(data: dict):
    eid=data.get("empleado_id"); tipo=data.get("tipo"); lat=data.get("lat"); lng=data.get("lng"); foto=data.get("foto")
    if eid not in empleados_db: raise HTTPException(404)
    TIEMPO_COMIDA_MAX = empleados_db[eid].get("tiempo_comida", 120)
    ahora=datetime.now(); hoy=ahora.strftime("%Y-%m-%d"); hora=ahora.strftime("%H:%M:%S")
    reg = next((a for a in asistencias_db if a["empleado_id"]==eid and a["fecha_dia"]==hoy), None)
    if not reg:
        reg={"empleado_id":eid,"fecha":ahora.strftime("%Y-%m"),"fecha_dia":hoy,"entrada":None,"salida_comida":None,"regreso_comida":None,"salida_final":None,"retardo_entrada":0,"retardo_comida":0,"horas_trabajadas":0,"min_comida":0,"tiempo_permitido":TIEMPO_COMIDA_MAX,"foto_entrada":None,"foto_salida_comida":None,"foto_regreso_comida":None,"foto_salida_final":None,"firma":None}
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
        reg["entrada"]=hora; reg["retardo_entrada"]=retardo; reg["sucursal_id"]=suc_id; reg["foto_entrada"]=foto
    elif tipo=="salida_comida":
        if not reg["entrada"]: raise HTTPException(400, "Primero entrada")
        if reg["salida_comida"]: raise HTTPException(400, "Ya salida comida")
        reg["salida_comida"]=hora; reg["foto_salida_comida"]=foto
    elif tipo=="regreso_comida":
        if not reg["salida_comida"]: raise HTTPException(400, "Primero salida comida")
        if reg["regreso_comida"]: raise HTTPException(400, "Ya regreso")
        reg["regreso_comida"]=hora; reg["foto_regreso_comida"]=foto
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
        reg["salida_final"]=hora; reg["foto_salida_final"]=foto
        reg["firma"]=data.get("firma")
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
    limpiar_gps_antiguo()
    eid=data.get("empleado_id"); lat=data.get("lat"); lng=data.get("lng")
    if eid not in empleados_db: raise HTTPException(404)
    ahora=datetime.now(); hoy=ahora.strftime("%Y-%m-%d")
    reg = next((a for a in asistencias_db if a["empleado_id"]==eid and a["fecha_dia"]==hoy), None)
    if not reg or not reg.get("entrada") or reg.get("salida_final"): return {"ok":True,"msg":"No trabajando"}
    if reg.get("salida_comida") and not reg.get("regreso_comida"): return {"ok":True,"msg":"En comida"}
    dias=["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]
    suc_id=empleados_db[eid].get("horario",{}).get(dias[ahora.weekday()],""); suc=sucursales_db.get(suc_id)
    if not suc or not suc.get("lat"): 
        gps_logs_db.append({"empleado_id":eid,"lat":lat,"lng":lng,"fecha":ahora.strftime("%Y-%m-%d %H:%M:%S"),"fecha_dia":hoy,"hora":ahora.strftime("%H:%M:%S"),"sucursal_id":suc_id})
        save_db(); return {"ok":True,"dentro":True}
    try:
        dist=distancia_m(float(lat),float(lng),float(suc["lat"]),float(suc["lng"]))
        dentro=dist <= float(suc.get("radio",200))
        gps_logs_db.append({"empleado_id":eid,"lat":lat,"lng":lng,"distancia":round(dist,1),"dentro":dentro,"fecha":ahora.strftime("%Y-%m-%d %H:%M:%S"),"fecha_dia":hoy,"hora":ahora.strftime("%H:%M:%S"),"sucursal_id":suc_id,"empleado_nombre":empleados_db[eid]["nombre"]})
        if not dentro:
            alertas_db.append({"id":str(uuid.uuid4())[:6],"empleado_id":eid,"mensaje":f"🚨 GPS: {empleados_db[eid]['nombre']} se alejó {int(dist)}m de {suc.get('nombre')}","fecha":ahora.strftime("%Y-%m-%d %H:%M:%S"),"tipo":"gps_fuera","distancia":dist,"lat":lat,"lng":lng})
            save_db(); return {"ok":True,"dentro":False,"distancia":dist}
        save_db(); return {"ok":True,"dentro":True,"distancia":dist}
    except Exception as e: return {"ok":False,"error":str(e)}

@app.get("/gps/ruta/{eid}")
def gps_ruta(eid: str, dias: int = 60):
    limpiar_gps_antiguo()
    limite = datetime.now() - timedelta(days=dias)
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
    limpiar_gps_antiguo()
    limite = datetime.now() - timedelta(days=dias)
    def f_reciente(f_str):
        try: return datetime.strptime(f_str, "%Y-%m-%d %H:%M:%S") >= limite
        except: return True
    logs=[l for l in gps_logs_db if f_reciente(l.get("fecha",""))]
    return {"dias_guardados":dias,"total_puntos":len(logs),"logs":logs[::-1][:500]}

@app.get("/gps/export-csv/{eid}")
def export_csv(eid: str, dias: int = 60):
    limpiar_gps_antiguo()
    import csv, io
    limite = datetime.now() - timedelta(days=dias)
    logs=[g for g in gps_logs_db if g["empleado_id"]==eid and datetime.strptime(g.get("fecha","2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S") >= limite]
    output=io.StringIO()
    writer=csv.writer(output)
    writer.writerow(["empleado_id","nombre","fecha","hora","fecha_dia","lat","lng","distancia_m","dentro_geocerca","sucursal"])
    for l in logs:
        writer.writerow([l.get("empleado_id"),l.get("empleado_nombre",""),l.get("fecha"),l.get("hora",""),l.get("fecha_dia"),l.get("lat"),l.get("lng"),l.get("distancia",""),l.get("dentro",""),l.get("sucursal_id","")])
    return {"empleado_id":eid,"dias":dias,"csv":output.getvalue(),"filename":f"ruta_{eid}_ultimos_{dias}dias_{datetime.now().strftime('%Y-%m-%d')}.csv"}

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
    evaluaciones_db.append(nueva)
    alertas_db.append({"id":str(uuid.uuid4())[:6],"empleado_id":eid,"mensaje":f"📊 EVALUACIÓN {mes}: {total}/100 - {nivel}","fecha":hoy.strftime("%Y-%m-%d %H:%M"),"total":total,"nivel":nivel,"tipo":"evaluacion"})
    save_db(); return nueva
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
    total_entrada=sum([a.get("retardo_entrada",0) for a in asist])
    total_comida=sum([a.get("retardo_comida",0) for a in asist])
    retardos=[]
    for a in asist:
        if a.get("retardo_entrada",0)>0 or a.get("retardo_comida",0)>0:
            retardos.append({"fecha_dia":a.get("fecha_dia"),"entrada":a.get("entrada"),"retardo_entrada":a.get("retardo_entrada",0),"salida_comida":a.get("salida_comida"),"regreso_comida":a.get("regreso_comida"),"min_comida":a.get("min_comida",0),"tiempo_permitido":a.get("tiempo_permitido",120),"retardo_comida":a.get("retardo_comida",0),"horas":a.get("horas_trabajadas",0)})
    total_horas=round(sum([a.get("horas_trabajadas",0) for a in asist]),2)
    return {"empleado_id":eid,"mes":mes,"total_retardo_entrada":round(total_entrada,1),"total_retardo_comida":round(total_comida,1),"total_retardos":round(total_entrada+total_comida,1),"total_horas":total_horas,"detalles":retardos,"asistencias":asist}
@app.get("/admin/retardos-todos")
def retardos_todos():
    mes=datetime.now().strftime("%Y-%m")
    result=[]
    for eid, emp in empleados_db.items():
        if emp.get("eliminado"): continue
        asist=[a for a in asistencias_db if a["empleado_id"]==eid and a.get("fecha","")==mes]
        total_e=sum([a.get("retardo_entrada",0) for a in asist])
        total_c=sum([a.get("retardo_comida",0) for a in asist])
        if len(asist)>0 or total_e>0 or total_c>0:
            result.append({"empleado_id":eid,"nombre":emp.get("nombre"),"total_entrada":round(total_e,1),"total_comida":round(total_c,1),"total":round(total_e+total_c,1),"dias_trabajados":len(asist),"horas_mes":round(sum([a.get("horas_trabajadas",0) for a in asist]),1)})
    return sorted(result, key=lambda x: x["total"], reverse=True)

@app.get("/admin/export-excel")
def export_excel():
    import csv, io
    output=io.StringIO()
    writer=csv.writer(output)
    writer.writerow(["empleado_id","nombre","mes","fecha_dia","entrada","retardo_entrada","salida_comida","regreso_comida","min_comida","retardo_comida","salida_final","horas_trabajadas","horas_extra","sucursal"])
    mes=datetime.now().strftime("%Y-%m")
    for a in asistencias_db:
        if mes in a.get("fecha",""):
            emp=empleados_db.get(a["empleado_id"],{})
            horas=a.get("horas_trabajadas",0)
            extra=round(horas-8,2) if horas>8 else 0
            writer.writerow([a["empleado_id"],emp.get("nombre",""),a.get("fecha"),a.get("fecha_dia"),a.get("entrada"),a.get("retardo_entrada"),a.get("salida_comida"),a.get("regreso_comida"),a.get("min_comida"),a.get("retardo_comida"),a.get("salida_final"),a.get("horas_trabajadas"),extra,a.get("sucursal_id")])
    return {"csv":output.getvalue(),"filename":f"nomina_{mes}_{datetime.now().strftime('%Y-%m-%d')}.csv"}

@app.get("/admin/audit")
def audit_get(): return audit_db[::-1][:100]
@app.get("/admin/papelera")
def papelera(): return [e for e in empleados_db.values() if e.get("eliminado")]

HTML = """
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ULTRA DEFINITIVA - Todo</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Inter',sans-serif}
body{background:#0f172a;color:white;min-height:100vh}
.hero{background:linear-gradient(135deg,#6366f1 0%,#8b5cf6 50%,#ec4899 100%);padding:50px 20px 70px;text-align:center}
.hero h1{font-size:38px;font-weight:800}
.container{max-width:1200px;margin:-40px auto 40px;padding:0 20px}
.card{background:#1e293b;border:1px solid #334155;border-radius:20px;padding:22px;margin-top:16px}
.btn{padding:12px 16px;border-radius:12px;border:none;font-weight:700;cursor:pointer;width:100%;margin-top:8px}
.btn-primary{background:#6366f1;color:white}.btn-success{background:#10b981;color:white}.btn-warning{background:#f59e0b;color:white}.btn-danger{background:#ef4444;color:white}.btn-dark{background:#0f172a;color:white;border:1px solid #334155}
.input{width:100%;padding:12px;border-radius:12px;border:1px solid #334155;background:#0f172a;color:white;margin-top:8px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
@media(max-width:800px){.grid2,.grid4{grid-template-columns:1fr}}
.kpi{background:#0f172a;border-radius:14px;padding:14px;text-align:center;border:1px solid #334155}
.kpi b{font-size:22px;display:block}
.paso{display:flex;align-items:center;gap:10px;padding:12px;background:#0f172a;border-radius:12px;margin-top:8px;border-left:4px solid #334155}
.paso.completo{border-left-color:#10b981;background:#10b98115}
.paso.activo{border-left-color:#f59e0b;background:#f59e0b15}
.gps-on{background:#10b981;color:white;padding:5px 10px;border-radius:20px;font-size:11px;font-weight:800;animation:pulse 1s infinite}
.gps-off{background:#64748b;color:white;padding:5px 10px;border-radius:20px;font-size:11px}
@keyframes pulse{0%{transform:scale(1)}50%{transform:scale(1.05)}100%{transform:scale(1)}}
.login-box{max-width:400px;margin:60px auto;background:#1e293b;border-radius:20px;padding:28px;border:1px solid #334155}
.modal{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.85);display:none;align-items:center;justify-content:center;z-index:1000;padding:20px}
.modal-content{background:#1e293b;border-radius:20px;padding:22px;max-width:520px;width:100%;max-height:92vh;overflow:auto;border:1px solid #334155}
#video{width:100%;border-radius:12px;background:#000}
canvas{width:100%;border-radius:12px}
</style></head><body>

<div id="login" class="login-box">
<h2 style="text-align:center">ULTRA DEFINITIVA</h2>
<p style="text-align:center;color:#94a3b8;font-size:11px;margin-top:4px">Todo menos QR/Facial - Persistente + Nómina + Justificantes + Chat + Calendario + Firma</p>
<input id="u" class="input" placeholder="admin o EMP0001">
<input id="p" class="input" type="password" placeholder="admin123 o 0001">
<button class="btn btn-primary" style="padding:16px" onclick="login()">INGRESAR →</button>
<p id="msg" style="text-align:center;color:#f87171;font-size:12px;margin-top:8px"></p>
<div style="margin-top:12px;background:#0f172a;border-radius:12px;padding:10px;font-size:10px;color:#94a3b8">
✅ Base datos persistente (no se borra)<br>✅ Contraseñas encriptadas<br>✅ Modo offline<br>✅ Nómina horas extra + Excel<br>✅ Justificantes con foto<br>✅ Papelera + Auditoría<br>✅ Ranking puntualidad<br>✅ Calendario turnos<br>✅ Ver compañeros<br>✅ Chat admin-empleado<br>✅ Firma digital<br>✅ Recordatorios<br>✅ Notificaciones push<br>✅ Botón pánico SOS<br>✅ Vacaciones<br>✅ Foto check<br>✅ GPS 60 días Drive<br>❌ Sin QR ❌ Sin facial (como pediste)
</div>
</div>

<div id="app" style="display:none">
<div class="hero"><h1>ULTRA DEFINITIVA PRO</h1><p>Todo integrado - Persistente - Nómina - Justificantes - Chat - Firma</p></div>
<div class="container">

<div id="admin-area" style="display:none">

<div class="card" style="border:2px solid #6366f1;background:linear-gradient(135deg,#1e293b,#6366f115)">
<h3>📊 Dashboard Admin PRO</h3>
<div class="grid4" style="margin-top:12px">
<div class="kpi"><b id="kpi-presentes">0</b><small>Presentes Hoy</small></div>
<div class="kpi"><b id="kpi-ausentes">0</b><small>Ausentes</small></div>
<div class="kpi"><b id="kpi-retardos" style="color:#ef4444">0</b><small>Retardos Hoy</small></div>
<div class="kpi"><b id="kpi-horas">0h</b><small>Horas Mes</small></div>
</div>
<div class="grid4" style="margin-top:8px">
<div class="kpi"><b id="kpi-gps" style="color:#ef4444">0</b><small>GPS Alertas Hoy</small></div>
<div class="kpi"><b id="kpi-vac" style="color:#f59e0b">0</b><small>Vac Pend</small></div>
<div class="kpi"><b id="kpi-just" style="color:#f59e0b">0</b><small>Just Pend</small></div>
<div class="kpi"><b id="kpi-panico" style="color:#ef4444">0</b><small>SOS Hoy</small></div>
</div>
<div style="margin-top:12px;background:#0f172a;border-radius:12px;padding:12px">
<b>🏆 Ranking Puntualidad (Menos retardos = mejor) - Mes</b>
<div id="ranking-puntual" style="margin-top:8px;font-size:11px"></div>
</div>
<div style="display:flex;gap:8px;margin-top:12px;flex-wrap:wrap"><button class="btn btn-success" onclick="exportarExcel()" style="width:auto">📥 Excel Nómina + Horas Extra</button><button class="btn btn-dark" onclick="cargarDashboard()" style="width:auto">🔄 Actualizar</button><button class="btn btn-dark" onclick="cargarAudit()" style="width:auto">📋 Auditoría</button><button class="btn btn-dark" onclick="cargarPapelera()" style="width:auto">🗑️ Papelera</button></div>
<div id="audit-result" style="margin-top:10px;max-height:200px;overflow:auto;background:#0f172a;border-radius:12px;padding:10px;font-size:10px;display:none"></div>
</div>

<div class="grid2">
<div class="card"><h3>🏢 Sucursal GPS</h3><input id="suc_id" class="input" placeholder="ID: SUC001"><input id="suc_nombre" class="input" placeholder="Nombre"><input id="suc_dir" class="input" placeholder="Dirección"><div class="grid2"><input id="suc_he" class="input" type="time" value="08:00"><input id="suc_hs" class="input" type="time" value="18:00"></div><div style="background:#6366f115;border-radius:12px;padding:10px;margin-top:8px"><div class="grid2"><input id="suc_lat" class="input" placeholder="Lat"><input id="suc_lng" class="input" placeholder="Lng"></div><div style="display:flex;gap:8px;align-items:center;margin-top:6px"><label style="font-size:11px">Radio:</label><input id="suc_radio" class="input" type="number" value="200" style="margin-top:0"><span>m</span></div><button class="btn btn-success" onclick="obtenerGPS()">📍 Mi ubicación</button></div><button class="btn btn-primary" onclick="crearSuc()">+ Crear</button><div id="list-suc" style="margin-top:8px"></div></div>

<div class="card"><h3>👤 Nuevo Empleado</h3><div style="background:#10b98115;padding:6px;border-radius:8px"><small>Próximo: <b id="next-id" style="color:#10b981">...</b></small></div><div style="display:flex;gap:8px"><input id="emp_id" class="input" readonly><button class="btn btn-dark" style="width:auto;margin-top:8px" onclick="generarID()">🔄</button></div><input id="emp_nombre" class="input" placeholder="Nombre *"><input id="emp_puesto" class="input" placeholder="Puesto"><input id="emp_pass" class="input" placeholder="Contraseña *"><div style="display:flex;gap:8px;align-items:center;margin-top:6px"><label style="font-size:11px;min-width:60px">Comida:</label><input id="emp_comida" class="input" type="number" value="120" style="margin-top:0"><span>min</span></div><div id="check-suc" style="background:#0f172a;border-radius:8px;padding:6px;margin-top:6px;max-height:50px;overflow:auto"></div><div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-top:6px"><select id="d-lunes" class="input"></select><select id="d-martes" class="input"></select><select id="d-miercoles" class="input"></select><select id="d-jueves" class="input"></select><select id="d-viernes" class="input"></select><select id="d-sabado" class="input"></select><select id="d-domingo" class="input"></select></div><button class="btn btn-success" onclick="crearEmp()">💾 Guardar</button></div>
</div>

<div class="card"><h3>📋 Empleados + Papelera</h3><div id="tabla-emp" style="margin-top:10px"></div></div>

<div class="card" style="border:2px solid #ef4444"><h3>🆘 SOS Pánico - Emergencias</h3><div id="panico-admin" style="margin-top:10px"></div><button class="btn btn-dark" onclick="cargarPanico()">🔄 Actualizar SOS</button></div>

<div class="card"><h3>💬 Chat Admin ↔ Empleados</h3><div style="display:flex;gap:8px"><select id="chat_para" class="input" style="margin-top:0"></select><input id="chat_msg" class="input" placeholder="Mensaje..." style="margin-top:0"></div><button class="btn btn-primary" onclick="enviarChatAdmin()">📤 Enviar Mensaje</button><div id="chat-admin-list" style="margin-top:10px;max-height:200px;overflow:auto;background:#0f172a;border-radius:12px;padding:10px;font-size:11px"></div></div>

<div class="card" style="border:2px solid #f59e0b"><h3>🏖️ Vacaciones + 📄 Justificantes</h3><div class="grid2"><div><b>Vacaciones Pendientes</b><div id="vac-admin" style="margin-top:8px"></div></div><div><b>Justificantes con Foto Pendientes</b><div id="just-admin" style="margin-top:8px"></div></div></div><div style="display:flex;gap:8px;margin-top:8px"><button class="btn btn-dark" onclick="cargarVacacionesAdmin()" style="width:auto">🔄 Vacaciones</button><button class="btn btn-dark" onclick="cargarJustificantesAdmin()" style="width:auto">🔄 Justificantes</button></div></div>

<div class="card" style="border:2px solid #f59e0b"><h3>⏱️ Retardos Todos + Horas Extra Nómina</h3><div id="retardos-admin" style="margin-top:10px"></div><button class="btn btn-dark" onclick="cargarRetardosAdmin()">🔄 Actualizar</button></div>

<div class="card" style="border:2px solid #ef4444"><h3>🚨 GPS Alertas (60 días Solo Admin)</h3><div id="gps-alertas" style="margin-top:10px"></div><button class="btn btn-dark" onclick="cargarGPSAlertas()">🔄 Actualizar</button></div>

<div class="card" style="border:2px solid #10b981"><h3>🗺️ Ruta GPS 60 Días Solo Admin + Drive</h3><select id="ruta_emp" class="input"></select><div class="grid2" style="margin-top:8px"><button class="btn btn-success" onclick="verRuta()">🗺️ Ver Ruta</button><button class="btn btn-primary" onclick="verRutaTodos()">👁️ Todos</button></div><div class="grid2"><button class="btn btn-warning" onclick="exportarDrive()">💾 Drive</button><button class="btn btn-dark" style="background:#0ea5e9;border:none" onclick="exportarCSV()">📥 CSV</button></div><div id="ruta-result" style="margin-top:10px;max-height:300px;overflow:auto;background:#0f172a;border-radius:12px;padding:10px;font-size:11px"></div><div id="drive-status" style="margin-top:8px;background:#10b98115;border-radius:8px;padding:8px;font-size:11px;display:none"></div></div>

<div class="card"><h3>⭐ Evaluación 100 pts + Firma Digital</h3><select id="eval_emp" class="input"></select><div id="eval_preguntas" style="margin-top:8px"></div><div style="background:#0f172a;border-radius:12px;padding:10px;margin-top:10px"><p style="font-size:11px">✍️ Firma del evaluador (admin)</p><canvas id="firma-canvas" width="400" height="150" style="background:white;border-radius:8px;width:100%;margin-top:6px"></canvas><button class="btn btn-dark" onclick="limpiarFirma()">🧹 Limpiar Firma</button></div><div id="total-preview" style="background:linear-gradient(135deg,#10b981,#059669);border-radius:12px;padding:12px;text-align:center;color:white;margin-top:10px;display:none"><div id="total-num" style="font-size:26px;font-weight:800">0</div></div><button class="btn btn-success" onclick="evaluar()">Guardar Evaluación + Firma</button><p id="msg-eval"></p></div>

</div>

<div id="emp-area" style="display:none">

<div class="card" style="border:2px solid #10b981">
<h3>⏰ Mi Jornada + Foto + GPS <span id="gps-status" class="gps-off">Off</span></h3>
<p style="font-size:11px;color:#94a3b8">Comida: <b id="mi-tiempo-comida">120 min</b> | Radio: <b id="mi-radio">200m</b> | <span id="recordatorio-text" style="color:#f59e0b"></span></p>
<div id="gps-info" style="background:#0f172a;border-radius:10px;padding:8px;margin-top:8px;font-size:11px;display:none"><b>📍</b> <span id="mi-ubicacion">...</span><br><b>Dist:</b> <span id="mi-distancia">--</span></div>

<div id="foto-section" style="background:#0f172a;border-radius:12px;padding:10px;margin-top:10px;display:none">
<p style="font-size:11px;font-weight:700">📸 Foto obligatoria para check</p>
<video id="video" autoplay playsinline style="margin-top:6px"></video>
<canvas id="canvas" style="display:none"></canvas>
<img id="foto-preview" style="width:100%;border-radius:12px;margin-top:6px;display:none">
<div style="display:flex;gap:6px;margin-top:6px"><button class="btn btn-warning" onclick="tomarFoto()" style="margin-top:0">📸 Tomar</button><button class="btn btn-dark" onclick="repetirFoto()" style="margin-top:0">🔄 Repetir</button></div>
</div>

<div style="background:#0f172a;border-radius:12px;padding:12px;margin-top:10px">
<div id="paso-entrada" class="paso"><span>📍</span><div><b>Entrada + Foto</b><br><small id="hora-entrada">Pendiente</small></div></div>
<div id="paso-salida-comida" class="paso"><span>🍔</span><div><b>Salida Comer + Foto</b><br><small id="hora-salida-comida">Pendiente</small></div></div>
<div id="paso-regreso-comida" class="paso"><span>↩️</span><div><b>Regreso + Foto</b><br><small id="hora-regreso-comida">Pendiente</small></div></div>
<div id="paso-salida-final" class="paso"><span>🏠</span><div><b>Salida Final + Foto + Firma</b><br><small id="hora-salida-final">Pendiente</small></div></div>
</div>

<div id="firma-empleado-section" style="background:#0f172a;border-radius:12px;padding:10px;margin-top:10px;display:none">
<p style="font-size:11px">✍️ Firma de salida</p>
<canvas id="firma-emp-canvas" width="400" height="120" style="background:white;border-radius:8px;width:100%;margin-top:6px"></canvas>
<button class="btn btn-dark" onclick="limpiarFirmaEmp()">🧹 Limpiar</button>
</div>

<button id="btn-accion" class="btn btn-primary" style="font-size:16px;padding:16px;margin-top:12px" onclick="registrar()">📍 Registrar</button>
<p id="msg-check" style="font-size:11px;margin-top:8px;text-align:center;color:#10b981"></p>
<div style="margin-top:10px;background:#0f172a;border-radius:10px;padding:10px;font-size:11px"><b>Resumen hoy:</b><br><span id="resumen-hoy">Sin registros</span></div>
</div>

<div class="card" style="border:2px solid #ef4444"><h3>🆘 Botón Pánico SOS</h3><button class="btn btn-danger" style="font-size:18px;padding:18px" onclick="activarPanico()">🆘 SOS PÁNICO - Enviar GPS a Admin</button><p id="msg-panico" style="font-size:11px;margin-top:6px;text-align:center"></p></div>

<div class="card"><h3>👥 Compañeros Hoy en mi Sucursal</h3><div id="companeros-hoy" style="margin-top:8px"></div><button class="btn btn-dark" onclick="cargarCompaneros()">🔄 Ver Compañeros</button></div>

<div class="card"><h3>💬 Chat con Admin</h3><input id="chat_msg_emp" class="input" placeholder="Escribe mensaje a admin..."><button class="btn btn-primary" onclick="enviarChatEmpleado()">📤 Enviar a Admin</button><div id="chat-emp-list" style="margin-top:10px;max-height:200px;overflow:auto;background:#0f172a;border-radius:12px;padding:10px;font-size:11px"></div></div>

<div class="card"><h3>📅 Mi Calendario Turnos - Próximos 7 días</h3><div id="calendario-turnos" style="margin-top:8px"></div></div>

<div class="card" style="border:2px solid #6366f1"><h3>🏖️ Solicitar Vacaciones / Permiso + 📄 Justificante con Foto</h3>
<div class="grid2"><div><b>Vacaciones</b><select id="vac_tipo" class="input"><option value="vacaciones">Vacaciones</option><option value="permiso">Permiso con goce</option><option value="permiso_sin_goce">Sin goce</option><option value="incapacidad">Incapacidad</option><option value="personal">Personal</option></select><div class="grid2"><input id="vac_inicio" class="input" type="date"><input id="vac_fin" class="input" type="date"></div><textarea id="vac_motivo" class="input" placeholder="Motivo..." rows="2"></textarea><button class="btn btn-primary" onclick="solicitarVacaciones()">📅 Solicitar</button></div><div><b>Justificante con Foto</b><input id="just_fecha" class="input" type="date"><select id="just_tipo" class="input"><option value="enfermedad">Enfermedad</option><option value="medico">Cita médica</option><option value="familiar">Familiar</option><option value="otro">Otro</option></select><input id="just_foto" class="input" type="file" accept="image/*"><textarea id="just_motivo" class="input" placeholder="Motivo..." rows="2"></textarea><button class="btn btn-warning" onclick="subirJustificante()">📄 Subir Justificante con Foto</button></div></div>
<div class="grid2" style="margin-top:10px"><div><div id="mis-vacaciones" style="max-height:150px;overflow:auto"></div></div><div><div id="mis-justificantes" style="max-height:150px;overflow:auto"></div></div></div>
</div>

<div class="card" style="border:2px solid #f59e0b"><h3>⏱️ Mis Retardos + Horas Mes (Nómina)</h3><div id="mis-retardos" style="margin-top:8px"></div><div style="margin-top:8px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px"><div style="background:#ef444415;border:1px solid #ef4444;border-radius:12px;padding:8px;text-align:center"><div style="font-size:18px;font-weight:800;color:#ef4444" id="total-retardo-entrada">0 min</div><small>Entrada</small></div><div style="background:#f59e0b15;border:1px solid #f59e0b;border-radius:12px;padding:8px;text-align:center"><div style="font-size:18px;font-weight:800;color:#f59e0b" id="total-retardo-comida">0 min</div><small>Comida</small></div><div style="background:#10b98115;border:1px solid #10b981;border-radius:12px;padding:8px;text-align:center"><div style="font-size:18px;font-weight:800;color:#10b981" id="total-horas-mes">0h</div><small>Horas Mes</small></div></div></div>

<div class="card"><h3>🔑 Cambiar Contraseña + Perfil</h3><input id="old_pass" class="input" type="password" placeholder="Actual"><input id="new_pass" class="input" type="password" placeholder="Nueva"><button class="btn btn-primary" onclick="cambiarPassword()">🔑 Cambiar</button><p id="msg-pass" style="font-size:11px;margin-top:6px;text-align:center"></p><div style="margin-top:10px;background:#0f172a;border-radius:10px;padding:8px;font-size:10px"><b>Modo Offline:</b> <span id="offline-status">✅ Online</span> - Si te quedas sin datos, la app guarda offline y sincroniza después<br><b>Recordatorios:</b> <span id="recordatorio-emp">Activados</span> - Te avisa 10 min antes de entrada y regreso comida</div></div>

<div class="card"><h3>📊 Mi Historial y Notificaciones Push</h3><div id="mi-historial" style="margin-top:8px"></div><div id="mis-notifs" style="margin-top:10px"></div><button class="btn btn-dark" onclick="activarNotificaciones()">🔔 Activar Notificaciones Push</button></div>
</div>

</div></div>

<div id="modal-edit" class="modal"><div class="modal-content"><h3>✏️ Editar Empleado</h3><input id="edit_id" class="input" readonly><input id="edit_nombre" class="input" placeholder="Nombre"><input id="edit_puesto" class="input" placeholder="Puesto"><input id="edit_password" class="input" placeholder="Nueva contraseña (deja vacío para no cambiar)"><input id="edit_telefono" class="input" placeholder="Tel"><div style="display:flex;gap:8px;align-items:center;margin-top:8px"><label style="font-size:11px;min-width:60px">Comida:</label><input id="edit_comida" class="input" type="number" style="margin-top:0"></div><div style="display:flex;gap:8px;margin-top:8px"><label style="font-size:11px">Activo:</label><select id="edit_activo" class="input" style="margin-top:0"><option value="true">Activo</option><option value="false">Desactivado</option></select></div><button class="btn btn-success" onclick="guardarEdicion()">💾 Guardar</button><button class="btn btn-dark" onclick="cerrarModal()">Cancelar</button><button class="btn btn-danger" onclick="eliminarEmpleado()">🗑️ Enviar a Papelera</button></div></div>

<script>
let USER_ID=''; let EDITANDO_ID=''; let watchId=null; let gpsActivo=false; let miPos={lat:null,lng:null}; let fotoBase64=null; let stream=null; let firmaData=null; let firmaEmpData=null;
const PREG=[{id:1,txt:"¿Limpieza de botarga? (1-10)",tipo:"cal"},{id:2,txt:"¿Limpieza de ropa? (1-10)",tipo:"cal"},{id:3,txt:"¿Limpieza de guantes? (1-10)",tipo:"cal"},{id:4,txt:"¿Limpieza de zapatos? (1-10)",tipo:"cal"},{id:5,txt:"¿Baile? (1-10)",tipo:"cal"},{id:6,txt:"¿Comentario de baile? (texto)",tipo:"texto"},{id:7,txt:"¿Actitud? (1-10)",tipo:"cal"},{id:8,txt:"¿Cumple con políticas? (1-10)",tipo:"cal"},{id:9,txt:"¿Ambiente positivo? (1-10)",tipo:"cal"},{id:10,txt:"¿Disponibilidad? (1-10)",tipo:"cal"},{id:11,txt:"¿Cumple horarios? (1-10)",tipo:"cal"},{id:12,txt:"¿Área por mejorar? (texto)",tipo:"texto"},];

// OFFLINE MODE
let offlineQueue=[];
if('serviceWorker' in navigator){/* offline via localStorage */}
window.addEventListener('online',()=>{document.getElementById('offline-status')&&(document.getElementById('offline-status').innerText='✅ Online'); syncOffline();});
window.addEventListener('offline',()=>{document.getElementById('offline-status')&&(document.getElementById('offline-status').innerText='📴 Offline - Guardando local');});

async function syncOffline(){
 if(offlineQueue.length==0){ offlineQueue=JSON.parse(localStorage.getItem('offlineQueue')||'[]'); }
 for(let item of offlineQueue){
  try{ await api(item.url,item.method,item.body); }catch(e){}
 }
 offlineQueue=[]; localStorage.setItem('offlineQueue','[]');
}

async function api(p,m='GET',b=null){
 const o={method:m,headers:{'Content-Type':'application/json'}}; if(b)o.body=JSON.stringify(b);
 try{
  const r=await fetch(p,o); if(!r.ok){const e=await r.json(); throw e;} return r.json();
 }catch(e){
  if(!navigator.onLine && m=='POST' && p.includes('/asistencia/registrar')){
   offlineQueue.push({url:p,method:m,body:b}); localStorage.setItem('offlineQueue',JSON.stringify(offlineQueue));
   return {offline:true,msg:'Guardado offline, se sincronizará'};
  }
  throw e;
 }
}
async function login(){const u=document.getElementById('u').value; const p=document.getElementById('p').value; try{const d=await api('/api/login','POST',{usuario:u,password:p}); document.getElementById('login').style.display='none'; document.getElementById('app').style.display='block'; USER_ID=u; if(d.rol==='admin'){document.getElementById('admin-area').style.display='block'; cargarTodo();} else{document.getElementById('emp-area').style.display='block'; cargarEmpleado(); iniciarRecordatorios();} }catch(e){document.getElementById('msg').innerText=e.detail||'Error';}}
async function generarID(){const d=await api('/empleados/next-id'); document.getElementById('emp_id').value=d.next_id; document.getElementById('next-id').innerText=d.next_id;}
function obtenerGPS(){if(!navigator.geolocation) return alert('GPS no soportado'); navigator.geolocation.getCurrentPosition(pos=>{document.getElementById('suc_lat').value=pos.coords.latitude; document.getElementById('suc_lng').value=pos.coords.longitude; alert('📍 GPS: '+pos.coords.latitude+', '+pos.coords.longitude);}, err=>alert('Error GPS: '+err.message), {enableHighAccuracy:true});}
async function crearSuc(){const id=document.getElementById('suc_id').value; const nombre=document.getElementById('suc_nombre').value; const dir=document.getElementById('suc_dir').value; const he=document.getElementById('suc_he').value; const hs=document.getElementById('suc_hs').value; const lat=parseFloat(document.getElementById('suc_lat').value); const lng=parseFloat(document.getElementById('suc_lng').value); const radio=parseInt(document.getElementById('suc_radio').value)||200; if(!id||!nombre) return alert('ID y nombre'); await api('/sucursales','POST',{id,nombre,direccion:dir,hora_entrada:he,hora_salida:hs,lat:lat||null,lng:lng||null,radio:radio}); document.getElementById('suc_id').value=''; document.getElementById('suc_nombre').value=''; cargarSucs();}
async function cargarSucs(){const sucs=await api('/sucursales'); document.getElementById('list-suc').innerHTML=sucs.map(s=>`<div style="background:#0f172a;padding:8px;border-radius:10px;margin-top:6px;font-size:11px"><b>${s.id} ${s.nombre}</b> ${s.lat?`📍 ${s.lat.toFixed(5)},${s.lng.toFixed(5)} - ${s.radio}m`: '⚠️ Sin GPS'}</div>`).join('') || 'Sin'; document.getElementById('check-suc').innerHTML=sucs.map(s=>`<label style="display:flex;gap:6px;margin-top:4px"><input type="checkbox" value="${s.id}" class="chk"> ${s.nombre}</label>`).join(''); ['lunes','martes','miercoles','jueves','viernes','sabado','domingo'].forEach(d=>{const sel=document.getElementById('d-'+d); if(sel) sel.innerHTML='<option value="">Libre</option>'+sucs.map(s=>`<option value="${s.id}">${s.nombre}</option>`).join('');});}
async function crearEmp(){const id=document.getElementById('emp_id').value; const nombre=document.getElementById('emp_nombre').value; const puesto=document.getElementById('emp_puesto').value; const pass=document.getElementById('emp_pass').value; const comida=parseInt(document.getElementById('emp_comida').value)||120; if(!nombre||!pass) return alert('Nombre y contraseña'); const suc=[...document.querySelectorAll('.chk:checked')].map(c=>c.value); const hor={lunes:document.getElementById('d-lunes').value,martes:document.getElementById('d-martes').value,miercoles:document.getElementById('d-miercoles').value,jueves:document.getElementById('d-jueves').value,viernes:document.getElementById('d-viernes').value,sabado:document.getElementById('d-sabado').value,domingo:document.getElementById('d-domingo').value}; const r=await api('/empleados','POST',{id,nombre,puesto,password:pass,tiempo_comida:comida,sucursales_ids:suc,horario:hor,activo:true}); alert(`✅ ${r.id}`); document.getElementById('emp_nombre').value=''; document.getElementById('emp_pass').value=''; generarID(); cargarEmps();}
async function cargarEmps(){const emps=await api('/empleados'); const activos=emps.filter(e=>!e.eliminado); document.getElementById('tabla-emp').innerHTML=activos.map(e=>`<div style="display:flex;justify-content:space-between;align-items:center;background:#0f172a;padding:10px;border-radius:10px;margin-top:6px;border-left:4px solid ${e.activo?'#10b981':'#ef4444'}"><div style="font-size:11px"><b style="color:#10b981">${e.id}</b> - <b>${e.nombre}</b><br>🔑 •••• | ⏱️ ${e.tiempo_comida||120} min | ${e.activo?'✅':'❌'}</div><div style="display:flex;gap:4px"><button onclick="abrirEditar('${e.id}')" style="padding:6px 8px;border-radius:6px;border:none;background:#6366f1;color:white;font-size:10px">✏️</button><button onclick="toggleEmp('${e.id}')" style="padding:6px 8px;border-radius:6px;border:none;background:${e.activo?'#ef4444':'#10b981'};color:white;font-size:10px">${e.activo?'Off':'On'}</button></div></div>`).join(''); document.getElementById('eval_emp').innerHTML=activos.filter(e=>e.activo).map(e=>`<option value="${e.id}">${e.id} - ${e.nombre}</option>`).join(''); document.getElementById('ruta_emp').innerHTML=activos.map(e=>`<option value="${e.id}">${e.id} - ${e.nombre}</option>`).join(''); document.getElementById('chat_para').innerHTML=activos.map(e=>`<option value="${e.id}">${e.id} - ${e.nombre}</option>`).join('');}
function abrirEditar(id){EDITANDO_ID=id; api('/empleados').then(emps=>{const e=emps.find(x=>x.id===id); if(!e) return; document.getElementById('edit_id').value=e.id; document.getElementById('edit_nombre').value=e.nombre||''; document.getElementById('edit_puesto').value=e.puesto||''; document.getElementById('edit_telefono').value=e.telefono||''; document.getElementById('edit_comida').value=e.tiempo_comida||120; document.getElementById('edit_activo').value=e.activo?'true':'false'; document.getElementById('modal-edit').style.display='flex';});}
function cerrarModal(){document.getElementById('modal-edit').style.display='none';}
async function guardarEdicion(){const pw=document.getElementById('edit_password').value; const data={nombre:document.getElementById('edit_nombre').value,puesto:document.getElementById('edit_puesto').value,telefono:document.getElementById('edit_telefono').value,tiempo_comida:parseInt(document.getElementById('edit_comida').value)||120,activo:document.getElementById('edit_activo').value==='true'}; if(pw) data.password=pw; await api('/empleados/'+EDITANDO_ID,'PUT',data); alert('✅ Guardado'); cerrarModal(); cargarEmps();}
async function eliminarEmpleado(){if(!confirm('¿Enviar a papelera? Se puede recuperar')) return; await fetch('/empleados/'+EDITANDO_ID,{method:'DELETE'}); cerrarModal(); cargarEmps();}
async function toggleEmp(id){await api('/empleados/'+id+'/toggle','PUT'); cargarEmps();}
async function cargarTodo(){await cargarSucs(); await generarID(); await cargarEmps(); renderPreguntas(); cargarDashboard(); cargarRetardosAdmin(); cargarGPSAlertas(); cargarVacacionesAdmin(); cargarJustificantesAdmin(); cargarPanico(); cargarChatAdmin(); initFirma();}
function renderPreguntas(){const div=document.getElementById('eval_preguntas'); div.innerHTML=PREG.map(q=>{if(q.tipo==='cal') return `<div style="background:#0f172a;padding:8px;border-radius:10px;margin-top:6px"><label style="font-size:11px">${q.id}. ${q.txt}</label><select data-id="${q.id}" class="input sel-cal" onchange="calcTotal()" style="padding:8px"><option value="0">0</option><option>1</option><option>2</option><option>3</option><option>4</option><option>5</option><option>6</option><option>7</option><option>8</option><option>9</option><option selected>10</option></select></div>`; else return `<div style="background:#0f172a;padding:8px;border-radius:10px;margin-top:6px"><label style="font-size:11px">${q.id}. ${q.txt}</label><textarea data-id="${q.id}" class="input" rows="2" style="padding:8px"></textarea></div>`;}).join(''); calcTotal();}
function calcTotal(){let t=0; document.querySelectorAll('.sel-cal').forEach(s=>t+=parseInt(s.value||0)); const b=document.getElementById('total-preview'); b.style.display='block'; document.getElementById('total-num').innerText=t+'/100';}
async function evaluar(){const eid=document.getElementById('eval_emp').value; const cals={}; document.querySelectorAll('[data-id]').forEach(el=>cals[el.dataset.id]=el.value); try{const r=await api('/evaluaciones','POST',{empleado_id:eid,calificaciones:cals,firma:firmaData}); document.getElementById('msg-eval').innerText=`✅ ${r.total}/100 con firma`; limpiarFirma();}catch(e){document.getElementById('msg-eval').innerText='❌ '+(e.detail||'Error');}}
async function cargarDashboard(){try{const d=await api('/admin/dashboard'); document.getElementById('kpi-presentes').innerText=d.presentes_hoy; document.getElementById('kpi-ausentes').innerText=d.ausentes_hoy; document.getElementById('kpi-retardos').innerText=d.retardos_hoy; document.getElementById('kpi-horas').innerText=d.horas_mes+'h'; document.getElementById('kpi-gps').innerText=d.gps_alertas_hoy; document.getElementById('kpi-vac').innerText=d.vacaciones_pendientes; document.getElementById('kpi-just').innerText=d.justificantes_pend; document.getElementById('kpi-panico').innerText=d.panico_hoy; document.getElementById('ranking-puntual').innerHTML=d.ranking.map((r,i)=>`<div style="display:flex;justify-content:space-between;background:#0f172a;padding:6px;border-radius:6px;margin-top:4px"><span>${i+1}. ${r.nombre} - ${r.id}</span><span style="color:${r.retardos>0?'#ef4444':'#10b981'}">${r.retardos} min ret | ${r.dias} días | ${r.horas}h</span></div>`).join('') || 'Sin datos';}catch(e){}}
async function exportarExcel(){const data=await api('/admin/export-excel'); const blob=new Blob([data.csv],{type:'text/csv'}); const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download=data.filename; a.click();}
async function cargarAudit(){const data=await api('/admin/audit'); document.getElementById('audit-result').style.display='block'; document.getElementById('audit-result').innerHTML=data.map(a=>`${a.fecha} - ${a.usuario} - ${a.accion} - ${a.detalle}`).join('<br>');}
async function cargarPapelera(){const data=await api('/admin/papelera'); alert('Papelera: '+data.map(e=>e.id+' '+e.nombre).join(', ') || 'Vacía');}
async function cargarGPSAlertas(){try{const alertas=await api('/gps/alertas'); document.getElementById('gps-alertas').innerHTML=alertas.slice(0,20).map(a=>`<div style="background:#ef444415;border:1px solid #ef4444;border-radius:10px;padding:8px;margin-top:6px;font-size:11px"><b style="color:#ef4444">🚨 ${a.empleado_id}</b> - ${a.mensaje}<br><small>${a.fecha}</small> - <a href="https://www.google.com/maps?q=${a.lat},${a.lng}" target="_blank" style="color:#60a5fa">Maps</a></div>`).join('') || 'Sin alertas';}catch(e){}}
async function cargarRetardosAdmin(){try{const data=await api('/admin/retardos-todos'); document.getElementById('retardos-admin').innerHTML=data.map(r=>`<div style="background:#0f172a;padding:10px;border-radius:10px;margin-top:6px;display:flex;justify-content:space-between;align-items:center;border-left:4px solid ${r.total>0?'#ef4444':'#10b981'}"><div style="font-size:11px"><b style="color:#10b981">${r.empleado_id}</b> - <b>${r.nombre}</b><br>Entrada: <span style="color:${r.total_entrada>0?'#ef4444':'#10b981'}">${r.total_entrada} min</span> | Comida: <span style="color:${r.total_comida>0?'#f59e0b':'#10b981'}">${r.total_comida} min</span> | Total: <b style="color:#ef4444">${r.total} min</b> | Horas: ${r.horas_mes}h</div></div>`).join('') || 'Sin';}catch(e){}}
async function cargarVacacionesAdmin(){try{const vac=await api('/vacaciones'); document.getElementById('vac-admin').innerHTML=vac.slice(0,10).map(v=>`<div style="background:#0f172a;padding:8px;border-radius:8px;margin-top:6px;font-size:10px;border-left:4px solid ${v.estado=='pendiente'?'#f59e0b':v.estado=='aprobado'?'#10b981':'#ef4444'}"><b>${v.empleado_id} ${v.nombre||''}</b> - ${v.tipo}<br>${v.fecha_inicio} al ${v.fecha_fin} - ${v.motivo}<br>Estado: <b>${v.estado.toUpperCase()}</b><br><div style="display:flex;gap:4px;margin-top:4px"><button onclick="responderVac('${v.id}','aprobado')" style="padding:4px 8px;border-radius:6px;border:none;background:#10b981;color:white;font-size:10px">✅ Aprobar</button><button onclick="responderVac('${v.id}','rechazado')" style="padding:4px 8px;border-radius:6px;border:none;background:#ef4444;color:white;font-size:10px">❌ Rechazar</button></div></div>`).join('') || 'Sin';}catch(e){}}
async function responderVac(id,estado){const com=prompt(`Comentario para ${estado}?`)||''; await api('/vacaciones/'+id+'/estado','PUT',{estado:estado,comentario:com}); cargarVacacionesAdmin();}
async function cargarJustificantesAdmin(){try{const just=await api('/justificantes'); document.getElementById('just-admin').innerHTML=just.slice(0,10).map(j=>`<div style="background:#0f172a;padding:8px;border-radius:8px;margin-top:6px;font-size:10px;border-left:4px solid ${j.estado=='pendiente'?'#f59e0b':j.estado=='aprobado'?'#10b981':'#ef4444'}"><b>${j.empleado_id} ${j.nombre||''}</b> - ${j.tipo} - ${j.fecha}<br>${j.motivo}<br>Estado: <b>${j.estado.toUpperCase()}</b><br><div style="display:flex;gap:4px;margin-top:4px"><button onclick="responderJust('${j.id}','aprobado')" style="padding:4px 8px;border-radius:6px;border:none;background:#10b981;color:white;font-size:10px">✅ Aprobar</button><button onclick="responderJust('${j.id}','rechazado')" style="padding:4px 8px;border-radius:6px;border:none;background:#ef4444;color:white;font-size:10px">❌ Rechazar</button></div></div>`).join('') || 'Sin';}catch(e){}}
async function responderJust(id,estado){await api('/justificantes/'+id+'/estado','PUT',{estado:estado}); cargarJustificantesAdmin();}
async function cargarPanico(){try{const p=await api('/panico/todos'); document.getElementById('panico-admin').innerHTML=p.slice(0,10).map(a=>`<div style="background:#ef4444;color:white;border-radius:10px;padding:10px;margin-top:6px;font-size:11px"><b>🆘 SOS ${a.empleado_id} ${a.nombre}</b><br>${a.mensaje}<br>${a.fecha}<br><a href="https://www.google.com/maps?q=${a.lat},${a.lng}" target="_blank" style="color:white;text-decoration:underline">📍 Maps ${a.lat},${a.lng}</a></div>`).join('') || 'Sin SOS ✅';}catch(e){}}
async function cargarChatAdmin(){try{const c=await api('/chat'); document.getElementById('chat-admin-list').innerHTML=c.slice(-20).map(m=>`<div style="margin-top:6px"><b>${m.de} → ${m.para}:</b> ${m.mensaje} <small style="color:#94a3b8">${m.fecha}</small></div>`).join('') || 'Sin mensajes';}catch(e){}}
async function enviarChatAdmin(){const para=document.getElementById('chat_para').value; const msg=document.getElementById('chat_msg').value; if(!para||!msg) return alert('Selecciona y escribe'); await api('/chat/enviar','POST',{de:'admin',para:para,mensaje:msg}); document.getElementById('chat_msg').value=''; cargarChatAdmin();}
async function verRuta(){const eid=document.getElementById('ruta_emp').value; const data=await api('/gps/ruta/'+eid+'?dias=60'); let html=`<b>📍 Ruta ${eid} - 60 días - ${data.total_puntos} puntos</b><br><br>`; for(const dia in data.ruta_por_dia){html+=`<div style="background:#1e293b;border-radius:10px;padding:8px;margin-top:6px"><b>${dia} - ${data.ruta_por_dia[dia].length} puntos</b><br>`+data.ruta_por_dia[dia].map(p=>`${p.hora} - ${p.lat.toFixed(5)},${p.lng.toFixed(5)} - ${p.distancia?Math.round(p.distancia)+'m':''} ${p.dentro?'✅':'❌'} - <a href="https://www.google.com/maps?q=${p.lat},${p.lng}" target="_blank" style="color:#60a5fa">Maps</a>`).join('<br>')+`</div>`;} if(!Object.keys(data.ruta_por_dia).length) html+='Sin ruta'; document.getElementById('ruta-result').innerHTML=html;}
async function verRutaTodos(){const data=await api('/gps/ruta-todos?dias=60'); document.getElementById('ruta-result').innerHTML=`<b>🗺️ Todos - 60 días - ${data.total_puntos} puntos</b><br><br>`+data.logs.slice(0,80).map(l=>`${l.fecha} - ${l.empleado_id} - ${l.lat.toFixed(5)},${l.lng.toFixed(5)} - ${l.distancia?Math.round(l.distancia)+'m':''} ${l.dentro?'✅':'❌'} - <a href="https://www.google.com/maps?q=${l.lat},${l.lng}" target="_blank" style="color:#60a5fa">Maps</a>`).join('<br>') || 'Sin';}
async function exportarCSV(){const eid=document.getElementById('ruta_emp').value; const data=await api('/gps/export-csv/'+eid+'?dias=60'); const blob=new Blob([data.csv],{type:'text/csv'}); const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download=data.filename; a.click();}
async function exportarDrive(){document.getElementById('drive-status').style.display='block'; document.getElementById('drive-status').innerHTML=`📁 Crea carpeta Drive "Rutas GPS" y sube CSV. Se guarda 60 días y borra auto.`;}

function iniciarCamara(){
 const sec=document.getElementById('foto-section'); if(!sec) return;
 sec.style.display='block';
 navigator.mediaDevices.getUserMedia({video:{facingMode:'user'}}).then(s=>{stream=s; document.getElementById('video').srcObject=s;}).catch(e=>{sec.style.display='none';});
}
function tomarFoto(){
 const video=document.getElementById('video'); const canvas=document.getElementById('canvas'); const ctx=canvas.getContext('2d');
 canvas.width=video.videoWidth; canvas.height=video.videoHeight; ctx.drawImage(video,0,0);
 fotoBase64=canvas.toDataURL('image/jpeg',0.5);
 document.getElementById('foto-preview').src=fotoBase64; document.getElementById('foto-preview').style.display='block'; document.getElementById('video').style.display='none';
}
function repetirFoto(){fotoBase64=null; document.getElementById('foto-preview').style.display='none'; document.getElementById('video').style.display='block';}
function detenerCamara(){if(stream){stream.getTracks().forEach(t=>t.stop()); stream=null;}}

async function activarPanico(){
 if(!confirm('¿Enviar SOS PÁNICO al admin con tu ubicación GPS?')) return;
 try{
  const pos=await new Promise((res,rej)=>navigator.geolocation.getCurrentPosition(res,rej,{enableHighAccuracy:true,timeout:8000}));
  const data=await api('/panico/sos','POST',{empleado_id:USER_ID,lat:pos.coords.latitude,lng:pos.coords.longitude,mensaje:'SOS EMERGENCIA'});
  document.getElementById('msg-panico').innerText='✅ SOS enviado con ubicación '+pos.coords.latitude.toFixed(5)+','+pos.coords.longitude.toFixed(5);
  alert('🆘 SOS enviado!');
 }catch(e){document.getElementById('msg-panico').innerText='❌ Error: '+(e.detail||e.message);}
}

async function solicitarVacaciones(){
 const tipo=document.getElementById('vac_tipo').value; const inicio=document.getElementById('vac_inicio').value; const fin=document.getElementById('vac_fin').value; const motivo=document.getElementById('vac_motivo').value;
 if(!inicio||!fin) return alert('Fechas');
 try{await api('/vacaciones/solicitar','POST',{empleado_id:USER_ID,tipo:tipo,fecha_inicio:inicio,fecha_fin:fin,motivo:motivo}); alert('✅ Solicitud enviada'); cargarMisVacaciones();}catch(e){alert('❌ '+(e.detail||'Error'));}
}
async function subirJustificante(){
 const fecha=document.getElementById('just_fecha').value; const tipo=document.getElementById('just_tipo').value; const motivo=document.getElementById('just_motivo').value; const file=document.getElementById('just_foto').files[0];
 if(!fecha) return alert('Fecha');
 let fotoData='';
 if(file){ fotoData=await new Promise(res=>{const r=new FileReader(); r.onload=e=>res(e.target.result); r.readAsDataURL(file);}); }
 try{await api('/justificantes/subir','POST',{empleado_id:USER_ID,fecha:fecha,tipo:tipo,motivo:motivo,foto:fotoData.substring(0,200)+'...'}); alert('✅ Justificante subido'); cargarMisJustificantes();}catch(e){alert('❌ '+(e.detail||'Error'));}
}
async function cargarMisVacaciones(){try{const vac=await api('/vacaciones/'+USER_ID); document.getElementById('mis-vacaciones').innerHTML=vac.map(v=>`<div style="background:#0f172a;padding:8px;border-radius:8px;margin-top:6px;font-size:10px;border-left:4px solid ${v.estado=='pendiente'?'#f59e0b':v.estado=='aprobado'?'#10b981':'#ef4444'}"><b>${v.tipo}</b> ${v.fecha_inicio} al ${v.fecha_fin}<br>${v.motivo}<br>Estado: <b>${v.estado.toUpperCase()}</b></div>`).join('') || 'Sin';}catch(e){}}
async function cargarMisJustificantes(){try{const just=await api('/justificantes/'+USER_ID); document.getElementById('mis-justificantes').innerHTML=just.map(j=>`<div style="background:#0f172a;padding:8px;border-radius:8px;margin-top:6px;font-size:10px;border-left:4px solid ${j.estado=='pendiente'?'#f59e0b':j.estado=='aprobado'?'#10b981':'#ef4444'}"><b>${j.tipo}</b> ${j.fecha}<br>${j.motivo}<br>Estado: <b>${j.estado.toUpperCase()}</b></div>`).join('') || 'Sin';}catch(e){}}
async function cargarCompaneros(){try{const hoy=await api('/asistencia/hoy/'+USER_ID); const suc=hoy.sucursal; if(!suc||!suc.id) return document.getElementById('companeros-hoy').innerHTML='Sin sucursal hoy'; const comp=await api('/admin/compañeros-hoy/'+suc.id); document.getElementById('companeros-hoy').innerHTML=comp.map(c=>`<div style="background:#0f172a;padding:8px;border-radius:8px;margin-top:4px;font-size:11px;display:flex;justify-content:space-between"><span><b>${c.nombre}</b> - ${c.puesto}</span><span style="color:${c.estado=='presente'?'#10b981':'#ef4444'}">${c.estado=='presente'?'✅ Presente '+ (c.entrada||''):'❌ Ausente'}</span></div>`).join('') || 'Sin compañeros';}catch(e){}}
async function enviarChatEmpleado(){const msg=document.getElementById('chat_msg_emp').value; if(!msg) return; await api('/chat/enviar','POST',{de:USER_ID,para:'admin',mensaje:msg}); document.getElementById('chat_msg_emp').value=''; cargarChatEmpleado();}
async function cargarChatEmpleado(){try{const c=await api('/chat/'+USER_ID); document.getElementById('chat-emp-list').innerHTML=c.slice(-20).map(m=>`<div style="margin-top:6px"><b>${m.de}:</b> ${m.mensaje} <small style="color:#94a3b8">${m.fecha}</small></div>`).join('') || 'Sin mensajes';}catch(e){}}
function activarNotificaciones(){if('Notification' in window){Notification.requestPermission().then(p=>{if(p=='granted'){new Notification('Notificaciones activadas',{body:'Te avisaremos de retardos y mensajes'}); alert('✅ Notificaciones push activadas');} else alert('❌ Permiso denegado');});} else alert('Navegador no soporta notificaciones');}
function iniciarRecordatorios(){
 setInterval(()=>{
  const ahora=new Date();
  const hora=ahora.getHours()+':'+String(ahora.getMinutes()).padStart(2,'0');
  document.getElementById('recordatorio-text')&&(document.getElementById('recordatorio-text').innerText='⏰ Recordatorio activo - Hora actual: '+hora);
  // Aquí podrías agregar lógica de recordatorio 10 min antes de entrada
 },60000);
}

function activarGPS(){if(gpsActivo) return; if(!navigator.geolocation) return; document.getElementById('gps-status').innerText='🟢 GPS ACTIVO'; document.getElementById('gps-status').className='gps-on'; document.getElementById('gps-info').style.display='block'; gpsActivo=true; watchId=navigator.geolocation.watchPosition(pos=>{miPos={lat:pos.coords.latitude,lng:pos.coords.longitude}; document.getElementById('mi-ubicacion').innerText=`${miPos.lat.toFixed(6)}, ${miPos.lng.toFixed(6)}`; api('/gps/update','POST',{empleado_id:USER_ID,lat:miPos.lat,lng:miPos.lng}).then(r=>{if(r.distancia!=null){document.getElementById('mi-distancia').innerText=`${Math.round(r.distancia)}m ${r.dentro?'✅ Dentro':'❌ FUERA'}`; document.getElementById('mi-distancia').style.color=r.dentro?'#10b981':'#ef4444';}}).catch(()=>{});}, err=>{document.getElementById('mi-ubicacion').innerText='Error: '+err.message;}, {enableHighAccuracy:true, maximumAge:10000, timeout:10000});}
function desactivarGPS(){if(watchId!==null){navigator.geolocation.clearWatch(watchId); watchId=null;} gpsActivo=false; document.getElementById('gps-status').innerText='⚪ GPS Off'; document.getElementById('gps-status').className='gps-off';}

async function cargarEmpleado(){
 try{
  const hoy=await api('/asistencia/hoy/'+USER_ID);
  actualizarUI(hoy);
  document.getElementById('mi-tiempo-comida').innerText=hoy.tiempo_permitido+' min ('+(hoy.tiempo_permitido/60)+'h)';
  if(hoy.sucursal) document.getElementById('mi-radio').innerText= (hoy.sucursal.radio||200)+'m de '+ (hoy.sucursal.nombre||'');
  const hist=await api('/empleado/'+USER_ID+'/historial');
  document.getElementById('mi-historial').innerHTML=hist.map(e=>`<div style="background:#0f172a;padding:8px;border-radius:8px;margin-top:6px;text-align:center"><div style="font-size:20px;font-weight:800">${e.total}/100</div><div style="font-size:10px">${e.nivel}</div></div>`).join('') || 'Sin evaluaciones';
  const notifs=await api('/alertas/'+USER_ID);
  document.getElementById('mis-notifs').innerHTML=notifs.map(n=>`<div style="background:#0f172a;padding:6px;border-radius:8px;margin-top:6px;font-size:10px">${n.mensaje}<br><small>${n.fecha}</small></div>`).join('') || 'Sin alertas';
  const retardos=await api('/empleado/'+USER_ID+'/retardos-mes');
  document.getElementById('total-retardo-entrada').innerText=retardos.total_retardo_entrada+' min';
  document.getElementById('total-retardo-comida').innerText=retardos.total_retardo_comida+' min';
  document.getElementById('total-horas-mes').innerText=(retardos.total_horas||0)+'h';
  document.getElementById('mis-retardos').innerHTML=retardos.detalles.map(r=>`<div style="background:#0f172a;padding:6px;border-radius:8px;margin-top:4px;font-size:10px;border-left:3px solid ${r.retardo_entrada>0||r.retardo_comida>0?'#ef4444':'#10b981'}"><b>${r.fecha_dia}</b><br>Entrada: ${r.entrada||'--'} ${r.retardo_entrada>0?`<span style="color:#ef4444">⚠️ +${r.retardo_entrada} min</span>`:'<span style="color:#10b981">✅</span>'}<br>Comida: ${r.salida_comida||'--'} → ${r.regreso_comida||'--'} (${r.min_comida||0}/${r.tiempo_permitido} min)</div>`).join('') || '<small>Sin retardos ✅</small>';
  cargarMisVacaciones(); cargarMisJustificantes(); cargarChatEmpleado(); cargarCompaneros();
  if(hoy.gps_activo){activarGPS();} else {desactivarGPS();}
  iniciarCamara(); initFirmaEmp();
 }catch(e){console.log(e)}
}
function actualizarUI(data){
 const btn=document.getElementById('btn-accion');
 btn.innerText=data.texto_boton; btn.style.background=data.color;
 if(data.siguiente==='completo'){btn.disabled=true; desactivarGPS(); detenerCamara();} else {btn.disabled=false;}
 document.getElementById('hora-entrada').innerText=data.entrada||'Pendiente';
 document.getElementById('hora-salida-comida').innerText=data.salida_comida||'Pendiente';
 document.getElementById('hora-regreso-comida').innerText=data.regreso_comida ? `${data.regreso_comida} (${data.min_comida||0}/${data.tiempo_permitido} min) ${data.retardo_comida>0?`⚠️ +${data.retardo_comida} min`:''}` : 'Pendiente';
 document.getElementById('hora-salida-final').innerText=data.salida_final||'Pendiente';
 document.getElementById('paso-entrada').className='paso '+(data.entrada?'completo':'activo');
 document.getElementById('paso-salida-comida').className='paso '+(data.salida_comida?'completo':(data.entrada?'activo':'')) ;
 document.getElementById('paso-regreso-comida').className='paso '+(data.regreso_comida?'completo':(data.salida_comida?'activo':''));
 document.getElementById('paso-salida-final').className='paso '+(data.salida_final?'completo':(data.regreso_comida?'activo':''));
 let resumen='';
 if(data.entrada) resumen+=`Entrada: ${data.entrada} ${data.retardo_entrada>0?`<span style="color:#ef4444">(Retardo ${data.retardo_entrada} min)</span>`:'<span style="color:#10b981">(A tiempo)</span>'}<br>`;
 if(data.salida_comida) resumen+=`Salida comida: ${data.salida_comida}<br>`;
 if(data.regreso_comida) {resumen+=`Regreso: ${data.regreso_comida} - ${data.min_comida||0}/${data.tiempo_permitido} min `; if(data.retardo_comida>0) resumen+=`<span style="color:#ef4444">⚠️ +${data.retardo_comida} MIN</span>`; else resumen+=`<span style="color:#10b981">✅</span>`; resumen+='<br>';}
 if(data.salida_final) resumen+=`Salida: ${data.salida_final}<br><b>Horas: ${data.horas_trabajadas||0}h</b><br>`;
 if(!resumen) resumen='Sin registros';
 document.getElementById('resumen-hoy').innerHTML=resumen;
 window.estadoActual=data.siguiente;
 if(data.gps_activo){activarGPS();} else if(data.siguiente!=='entrada'){desactivarGPS();}
 if(data.siguiente=='salida_final'){document.getElementById('firma-empleado-section').style.display='block';} else {document.getElementById('firma-empleado-section').style.display='none';}
}
async function registrar(){
 try{
  if(!fotoBase64){alert('📸 Debes tomar foto obligatoria'); iniciarCamara(); return;}
  let lat=null,lng=null;
  if(navigator.geolocation){try{const pos=await new Promise((res,rej)=>navigator.geolocation.getCurrentPosition(res,rej,{enableHighAccuracy:true,timeout:8000})); lat=pos.coords.latitude; lng=pos.coords.longitude;}catch(e){}}
  const tipo=window.estadoActual;
  let firma=null;
  if(tipo=='salida_final' && firmaEmpData){ firma=firmaEmpData; }
  const r=await api('/asistencia/registrar','POST',{empleado_id:USER_ID,tipo:tipo,lat:lat,lng:lng,foto:fotoBase64.substring(0,50)+'...',firma:firma});
  document.getElementById('msg-check').innerText=`✅ ${tipo} con foto${firma?' + firma':''} y GPS`;
  fotoBase64=null; document.getElementById('foto-preview').style.display='none'; document.getElementById('video').style.display='block';
  const hoy=await api('/asistencia/hoy/'+USER_ID);
  actualizarUI(hoy);
 }catch(e){document.getElementById('msg-check').innerText='❌ '+(e.detail||'Error');}
}
async function cambiarPassword(){
 const old=document.getElementById('old_pass').value; const nw=document.getElementById('new_pass').value;
 if(!old||!nw) return alert('Llena ambos');
 try{await api('/api/cambiar-password','POST',{empleado_id:USER_ID,old_password:old,new_password:nw}); document.getElementById('msg-pass').innerText='✅ Contraseña cambiada'; document.getElementById('old_pass').value=''; document.getElementById('new_pass').value='';}catch(e){document.getElementById('msg-pass').innerText='❌ '+(e.detail||'Error');}
}

// FIRMAS
let isDrawing=false; let ctxFirma=null; let ctxFirmaEmp=null;
function initFirma(){
 const canvas=document.getElementById('firma-canvas'); if(!canvas) return;
 ctxFirma=canvas.getContext('2d'); ctxFirma.lineWidth=2; ctxFirma.lineCap='round'; ctxFirma.strokeStyle='#000';
 canvas.addEventListener('mousedown',e=>{isDrawing=true; ctxFirma.beginPath(); ctxFirma.moveTo(e.offsetX,e.offsetY);});
 canvas.addEventListener('mousemove',e=>{if(!isDrawing) return; ctxFirma.lineTo(e.offsetX,e.offsetY); ctxFirma.stroke();});
 canvas.addEventListener('mouseup',()=>{isDrawing=false; firmaData=document.getElementById('firma-canvas').toDataURL();});
 canvas.addEventListener('touchstart',e=>{isDrawing=true; const rect=canvas.getBoundingClientRect(); const t=e.touches[0]; ctxFirma.beginPath(); ctxFirma.moveTo(t.clientX-rect.left,t.clientY-rect.top);});
 canvas.addEventListener('touchmove',e=>{if(!isDrawing) return; e.preventDefault(); const rect=canvas.getBoundingClientRect(); const t=e.touches[0]; ctxFirma.lineTo(t.clientX-rect.left,t.clientY-rect.top); ctxFirma.stroke();},{passive:false});
 canvas.addEventListener('touchend',()=>{isDrawing=false; firmaData=document.getElementById('firma-canvas').toDataURL();});
}
function limpiarFirma(){if(ctxFirma){ctxFirma.clearRect(0,0,400,150); firmaData=null;}}
function initFirmaEmp(){
 const canvas=document.getElementById('firma-emp-canvas'); if(!canvas) return;
 ctxFirmaEmp=canvas.getContext('2d'); ctxFirmaEmp.lineWidth=2; ctxFirmaEmp.lineCap='round'; ctxFirmaEmp.strokeStyle='#000';
 canvas.addEventListener('mousedown',e=>{isDrawing=true; ctxFirmaEmp.beginPath(); ctxFirmaEmp.moveTo(e.offsetX,e.offsetY);});
 canvas.addEventListener('mousemove',e=>{if(!isDrawing) return; ctxFirmaEmp.lineTo(e.offsetX,e.offsetY); ctxFirmaEmp.stroke();});
 canvas.addEventListener('mouseup',()=>{isDrawing=false; firmaEmpData=document.getElementById('firma-emp-canvas').toDataURL();});
 canvas.addEventListener('touchstart',e=>{isDrawing=true; const rect=canvas.getBoundingClientRect(); const t=e.touches[0]; ctxFirmaEmp.beginPath(); ctxFirmaEmp.moveTo(t.clientX-rect.left,t.clientY-rect.top);});
 canvas.addEventListener('touchmove',e=>{if(!isDrawing) return; e.preventDefault(); const rect=canvas.getBoundingClientRect(); const t=e.touches[0]; ctxFirmaEmp.lineTo(t.clientX-rect.left,t.clientY-rect.top); ctxFirmaEmp.stroke();},{passive:false});
 canvas.addEventListener('touchend',()=>{isDrawing=false; firmaEmpData=document.getElementById('firma-emp-canvas').toDataURL();});
}
function limpiarFirmaEmp(){if(ctxFirmaEmp){ctxFirmaEmp.clearRect(0,0,400,120); firmaEmpData=null;}}
</script></body></html>
"""

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home(): return HTML
