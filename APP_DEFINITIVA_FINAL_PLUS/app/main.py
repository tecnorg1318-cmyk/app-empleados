from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import uuid, math

app = FastAPI(title="Control con GPS Geocerca 2h editable")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

sucursales_db = {}
empleados_db = {
    "EMP0001": {"id":"EMP0001","nombre":"Empleado Prueba","puesto":"Botarga","password":"0001","sucursales_ids":[],"horario":{},"activo":True,"tiempo_comida":120,"telefono":"","direccion":""}
}
evaluaciones_db = []
asistencias_db = []
alertas_db = []
gps_logs_db = []

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
    # Haversine
    try:
        R=6371000
        phi1=math.radians(lat1); phi2=math.radians(lat2)
        dphi=math.radians(lat2-lat1); dlambda=math.radians(lon2-lon1)
        a=math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        c=2*math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R*c
    except: return 0

@app.post("/api/login")
def login(d: dict):
    u=d.get("usuario"); p=d.get("password")
    if u=="admin" and p=="admin123": return {"rol":"admin","usuario":u}
    if u in empleados_db:
        emp=empleados_db[u]
        if not emp.get("activo",True): raise HTTPException(403, "DESACTIVADO")
        if p==emp.get("password",u): return {"rol":"empleado","usuario":u,"nombre":emp["nombre"]}
        else: raise HTTPException(401, "Contraseña incorrecta")
    raise HTTPException(401, "No existe")

@app.get("/empleados/next-id")
def next_id(): return {"next_id": get_next_id()}
@app.get("/sucursales")
def ls(): return list(sucursales_db.values())
@app.post("/sucursales")
def cs(s: dict): sucursales_db[s["id"]]=s; return s
@app.put("/sucursales/{sid}")
def upd_suc(sid: str, data: dict):
    if sid not in sucursales_db: raise HTTPException(404)
    sucursales_db[sid].update(data)
    return sucursales_db[sid]
@app.get("/empleados")
def le(): return list(empleados_db.values())
@app.post("/empleados")
def ce(e: dict):
    if not e.get("id") or e["id"]=="": e["id"]=get_next_id()
    if e["id"] in empleados_db: e["id"]=get_next_id()
    if not e.get("password"): e["password"]=e["id"]
    e["activo"]=e.get("activo",True)
    if "tiempo_comida" not in e: e["tiempo_comida"]=120
    empleados_db[e["id"]]=e
    return e
@app.put("/empleados/{eid}")
def upd(eid: str, data: dict):
    if eid not in empleados_db: raise HTTPException(404)
    empleados_db[eid].update(data)
    return empleados_db[eid]
@app.put("/empleados/{eid}/toggle")
def toggle(eid: str):
    if eid not in empleados_db: raise HTTPException(404)
    empleados_db[eid]["activo"]=not empleados_db[eid].get("activo",True)
    return empleados_db[eid]
@app.delete("/empleados/{eid}")
def delete_emp(eid: str):
    if eid in empleados_db: del empleados_db[eid]
    return {"ok":True}

@app.get("/asistencia/hoy/{eid}")
def asistencia_hoy(eid: str):
    hoy=datetime.now().strftime("%Y-%m-%d")
    reg = next((a for a in asistencias_db if a["empleado_id"]==eid and a["fecha_dia"]==hoy), None)
    tiempo = empleados_db.get(eid,{}).get("tiempo_comida",120)
    dias=["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]
    suc_id=empleados_db.get(eid,{}).get("horario",{}).get(dias[datetime.now().weekday()],"")
    suc=sucursales_db.get(suc_id, {})
    if not reg:
        return {"empleado_id":eid,"fecha_dia":hoy,"estado":"sin_entrada","siguiente":"entrada","texto_boton":"📍 Registrar ENTRADA (Activa GPS)","color":"#10b981","tiempo_permitido":tiempo,"sucursal":suc,"gps_activo":False}
    if not reg.get("entrada"):
        return {**reg,"estado":"sin_entrada","siguiente":"entrada","texto_boton":"📍 Registrar ENTRADA (Activa GPS)","color":"#10b981","tiempo_permitido":tiempo,"sucursal":suc,"gps_activo":False}
    if not reg.get("salida_comida"):
        return {**reg,"estado":"trabajando","siguiente":"salida_comida","texto_boton":"🍔 Salida a COMER (Desactiva GPS)","color":"#f59e0b","tiempo_permitido":tiempo,"sucursal":suc,"gps_activo":True}
    if not reg.get("regreso_comida"):
        return {**reg,"estado":"comiendo","siguiente":"regreso_comida","texto_boton":"↩️ Regreso de COMIDA (Reactiva GPS)","color":"#6366f1","tiempo_permitido":tiempo,"sucursal":suc,"gps_activo":False}
    if not reg.get("salida_final"):
        return {**reg,"estado":"trabajando_tarde","siguiente":"salida_final","texto_boton":"🏠 Registrar SALIDA FINAL (Desactiva GPS)","color":"#ef4444","tiempo_permitido":tiempo,"sucursal":suc,"gps_activo":True}
    return {**reg,"estado":"completo","siguiente":"completo","texto_boton":"✅ Jornada COMPLETADA - GPS Desactivado","color":"#64748b","tiempo_permitido":tiempo,"sucursal":suc,"gps_activo":False}

@app.post("/asistencia/registrar")
def registrar(data: dict):
    eid=data.get("empleado_id")
    tipo=data.get("tipo")
    lat=data.get("lat"); lng=data.get("lng"); accuracy=data.get("accuracy")
    if eid not in empleados_db: raise HTTPException(404)
    TIEMPO_COMIDA_MAX = empleados_db[eid].get("tiempo_comida", 120)
    ahora=datetime.now()
    hoy=ahora.strftime("%Y-%m-%d")
    hora=ahora.strftime("%H:%M:%S")
    reg = next((a for a in asistencias_db if a["empleado_id"]==eid and a["fecha_dia"]==hoy), None)
    if not reg:
        reg={"empleado_id":eid,"fecha":ahora.strftime("%Y-%m"),"fecha_dia":hoy,"entrada":None,"salida_comida":None,"regreso_comida":None,"salida_final":None,"retardo_entrada":0,"retardo_comida":0,"horas_trabajadas":0,"min_comida":0,"tiempo_permitido":TIEMPO_COMIDA_MAX,"gps_entrada":None,"gps_salida_comida":None,"gps_regreso_comida":None,"gps_salida_final":None}
        asistencias_db.append(reg)
    else:
        reg["tiempo_permitido"]=TIEMPO_COMIDA_MAX

    dias=["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]
    suc_id=empleados_db[eid].get("horario",{}).get(dias[ahora.weekday()],"")
    suc=sucursales_db.get(suc_id)

    def check_geocerca(lat_emp, lng_emp):
        if not suc: return True, 0
        s_lat=suc.get("lat"); s_lng=suc.get("lng"); radio=suc.get("radio",200)
        if s_lat is None or s_lng is None: return True, 0
        try:
            d=distancia_m(float(lat_emp), float(lng_emp), float(s_lat), float(s_lng))
            return d <= float(radio), d
        except: return True,0

    if tipo=="entrada":
        if reg["entrada"]: raise HTTPException(400, "Ya entrada")
        retardo=0
        if suc:
            try:
                h,m=map(int,suc.get("hora_entrada","08:00").split(":"))
                ent=ahora.replace(hour=h,minute=m,second=0,microsecond=0)
                retardo=max(0, round((ahora-ent).total_seconds()/60,1))
            except: pass
        # validar GPS si hay sucursal con lat/lng
        if lat and lng and suc and suc.get("lat"):
            ok, dist = check_geocerca(lat,lng)
            if not ok:
                # Alerta pero si deja registrar? lo dejamos registrar con alerta
                alertas_db.append({"id":str(uuid.uuid4())[:6],"empleado_id":eid,"mensaje":f"🚨 Entrada FUERA de sucursal {suc.get('nombre')} - a {int(dist)}m de distancia. GPS: {lat},{lng}","fecha":ahora.strftime("%Y-%m-%d %H:%M"),"tipo":"gps_fuera","distancia":dist})
        reg["entrada"]=hora
        reg["retardo_entrada"]=retardo
        reg["sucursal_id"]=suc_id
        reg["gps_entrada"]={"lat":lat,"lng":lng,"accuracy":accuracy,"fecha":ahora.strftime("%Y-%m-%d %H:%M:%S")}
    elif tipo=="salida_comida":
        if not reg["entrada"]: raise HTTPException(400, "Primero entrada")
        if reg["salida_comida"]: raise HTTPException(400, "Ya salida comida")
        reg["salida_comida"]=hora
        reg["gps_salida_comida"]={"lat":lat,"lng":lng,"fecha":ahora.strftime("%Y-%m-%d %H:%M:%S")}
    elif tipo=="regreso_comida":
        if not reg["salida_comida"]: raise HTTPException(400, "Primero salida comida")
        if reg["regreso_comida"]: raise HTTPException(400, "Ya regreso")
        reg["regreso_comida"]=hora
        reg["gps_regreso_comida"]={"lat":lat,"lng":lng,"fecha":ahora.strftime("%Y-%m-%d %H:%M:%S")}
        try:
            from datetime import datetime as dt
            sc = dt.strptime(reg["salida_comida"], "%H:%M:%S")
            rc = dt.strptime(hora, "%H:%M:%S")
            diff_min = (rc - sc).total_seconds()/60
            if diff_min < 0: diff_min += 1440
            reg["min_comida"]=round(diff_min,1)
            reg["retardo_comida"]=round(diff_min - TIEMPO_COMIDA_MAX,1) if diff_min > TIEMPO_COMIDA_MAX else 0
        except: pass
        # al regresar verificar que esté de nuevo en sucursal
        if lat and lng and suc and suc.get("lat"):
            ok, dist = check_geocerca(lat,lng)
            if not ok:
                alertas_db.append({"id":str(uuid.uuid4())[:6],"empleado_id":eid,"mensaje":f"🚨 Regreso de comida FUERA de sucursal {suc.get('nombre')} - a {int(dist)}m","fecha":ahora.strftime("%Y-%m-%d %H:%M"),"tipo":"gps_fuera","distancia":dist})
    elif tipo=="salida_final":
        if not reg["regreso_comida"] and reg["salida_comida"]:
            raise HTTPException(400, "Primero regreso")
        if not reg["entrada"]: raise HTTPException(400, "Primero entrada")
        if reg["salida_final"]: raise HTTPException(400, "Ya salida final")
        reg["salida_final"]=hora
        reg["gps_salida_final"]={"lat":lat,"lng":lng,"fecha":ahora.strftime("%Y-%m-%d %H:%M:%S")}
        try:
            from datetime import datetime as dt
            e = dt.strptime(reg["entrada"], "%H:%M:%S")
            s = dt.strptime(hora, "%H:%M:%S")
            diff = (s - e).total_seconds()/3600
            if diff < 0: diff += 24
            if reg["salida_comida"] and reg["regreso_comida"]:
                sc = dt.strptime(reg["salida_comida"], "%H:%M:%S")
                rc = dt.strptime(reg["regreso_comida"], "%H:%M:%S")
                comida = (rc - sc).total_seconds()/3600
                if comida < 0: comida += 24
                diff -= comida
            reg["horas_trabajadas"]=round(diff,2)
        except: pass
    else:
        raise HTTPException(400, "Tipo invalido")
    return reg

DIAS_RETENCION = 60  # 2 meses

def limpiar_gps_antiguo():
    # Borra logs y alertas GPS de mas de 60 dias (2 meses) - se ejecuta en cada update
    from datetime import timedelta
    limite = datetime.now() - timedelta(days=DIAS_RETENCION)
    global gps_logs_db, alertas_db
    def es_reciente(fecha_str):
        try:
            f = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M:%S")
            return f >= limite
        except:
            return True
    gps_logs_db[:] = [g for g in gps_logs_db if es_reciente(g.get("fecha",""))]
    alertas_db[:] = [a for a in alertas_db if a.get("tipo")!="gps_fuera" or es_reciente(a.get("fecha",""))]

@app.get("/gps/config")
def gps_config():
    return {"retencion_dias":DIAS_RETENCION,"retencion_meses":2,"auto_borrado":f"Cada dia borra lo de hace {DIAS_RETENCION} dias","drive_backup":True}

@app.post("/gps/update")
def gps_update(data: dict):
    limpiar_gps_antiguo()
    eid=data.get("empleado_id")
    lat=data.get("lat"); lng=data.get("lng"); accuracy=data.get("accuracy")
    if eid not in empleados_db: raise HTTPException(404)
    ahora=datetime.now()
    hoy=ahora.strftime("%Y-%m-%d")
    reg = next((a for a in asistencias_db if a["empleado_id"]==eid and a["fecha_dia"]==hoy), None)
    if not reg or not reg.get("entrada") or reg.get("salida_final"):
        return {"ok":True,"msg":"No trabajando - GPS desactivado"}
    if reg.get("salida_comida") and not reg.get("regreso_comida"):
        return {"ok":True,"msg":"En comida - GPS desactivado"}
    dias=["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]
    suc_id=empleados_db[eid].get("horario",{}).get(dias[ahora.weekday()],"")
    suc=sucursales_db.get(suc_id)
    if not suc or not suc.get("lat"): 
        gps_logs_db.append({"empleado_id":eid,"lat":lat,"lng":lng,"fecha":ahora.strftime("%Y-%m-%d %H:%M:%S"),"sucursal_id":suc_id,"fecha_dia":hoy,"hora":ahora.strftime("%H:%M:%S")})
        return {"ok":True,"dentro":True}
    try:
        dist=distancia_m(float(lat),float(lng),float(suc["lat"]),float(suc["lng"]))
        dentro=dist <= float(suc.get("radio",200))
        gps_logs_db.append({"empleado_id":eid,"lat":lat,"lng":lng,"distancia":round(dist,1),"dentro":dentro,"fecha":ahora.strftime("%Y-%m-%d %H:%M:%S"),"fecha_dia":hoy,"hora":ahora.strftime("%H:%M:%S"),"sucursal_id":suc_id,"empleado_nombre":empleados_db[eid]["nombre"]})
        if not dentro:
            alertas_db.append({"id":str(uuid.uuid4())[:6],"empleado_id":eid,"mensaje":f"🚨 ALERTA GPS: {empleados_db[eid]['nombre']} se alejó {int(dist)}m de {suc.get('nombre')} (permitido {suc.get('radio',200)}m). Ubicación: {lat},{lng}","fecha":ahora.strftime("%Y-%m-%d %H:%M:%S"),"tipo":"gps_fuera","distancia":dist,"lat":lat,"lng":lng})
            return {"ok":True,"dentro":False,"distancia":dist,"alerta":"Se movió de sucursal"}
        return {"ok":True,"dentro":True,"distancia":dist}
    except Exception as e:
        return {"ok":False,"error":str(e)}

@app.get("/gps/ruta/{eid}")
def gps_ruta(eid: str, dias: int = 60):
    limpiar_gps_antiguo()
    # devuelve ruta de ultimos 60 dias (2 meses) agrupada por dia
    from datetime import timedelta
    limite = datetime.now() - timedelta(days=dias)
    logs = [g for g in gps_logs_db if g["empleado_id"]==eid]
    # filtrar por fecha
    def f_reciente(f_str):
        try: return datetime.strptime(f_str, "%Y-%m-%d %H:%M:%S") >= limite
        except: return True
    logs = [l for l in logs if f_reciente(l.get("fecha",""))]
    # agrupar por fecha_dia
    por_dia={}
    for l in logs:
        d=l.get("fecha_dia","sin_fecha")
        if d not in por_dia: por_dia[d]=[]
        por_dia[d].append(l)
    return {"empleado_id":eid,"dias_guardados":dias,"meses":2,"total_puntos":len(logs),"ruta_por_dia":por_dia,"logs":logs[::-1][:500]}

@app.get("/gps/ruta-todos")
def gps_ruta_todos(dias: int = 60):
    limpiar_gps_antiguo()
    from datetime import timedelta
    limite = datetime.now() - timedelta(days=dias)
    def f_reciente(f_str):
        try: return datetime.strptime(f_str, "%Y-%m-%d %H:%M:%S") >= limite
        except: return True
    logs=[l for l in gps_logs_db if f_reciente(l.get("fecha",""))]
    return {"dias_guardados":dias,"meses":2,"total_puntos":len(logs),"logs":logs[::-1][:500]}

@app.get("/gps/export-csv/{eid}")
def export_csv(eid: str, dias: int = 60):
    # Genera CSV para guardar en Drive - 2 meses
    limpiar_gps_antiguo()
    from datetime import timedelta
    import csv, io
    limite = datetime.now() - timedelta(days=dias)
    logs=[g for g in gps_logs_db if g["empleado_id"]==eid and datetime.strptime(g.get("fecha","2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S") >= limite]
    output=io.StringIO()
    writer=csv.writer(output)
    writer.writerow(["empleado_id","nombre","fecha","hora","fecha_dia","lat","lng","distancia_m","dentro_geocerca","sucursal"])
    for l in logs:
        writer.writerow([l.get("empleado_id"),l.get("empleado_nombre",""),l.get("fecha"),l.get("hora",""),l.get("fecha_dia"),l.get("lat"),l.get("lng"),l.get("distancia",""),l.get("dentro",""),l.get("sucursal_id","")])
    csv_data=output.getvalue()
    # Retornar como texto para que frontend lo suba a Drive
    return {"empleado_id":eid,"dias":dias,"csv":csv_data,"filename":f"ruta_{eid}_ultimos_{dias}dias_{datetime.now().strftime('%Y-%m-%d')}.csv","instrucciones":"Sube este CSV a tu carpeta de Google Drive 'Rutas GPS' - Se guarda 2 meses y se borra auto"}

@app.get("/gps/export-todos-csv")
def export_todos_csv(dias: int = 60):
    limpiar_gps_antiguo()
    from datetime import timedelta
    import csv, io
    limite = datetime.now() - timedelta(days=dias)
    logs=[g for g in gps_logs_db if datetime.strptime(g.get("fecha","2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S") >= limite]
    output=io.StringIO()
    writer=csv.writer(output)
    writer.writerow(["empleado_id","nombre","fecha","fecha_dia","lat","lng","distancia_m","dentro","sucursal"])
    for l in logs:
        writer.writerow([l.get("empleado_id"),l.get("empleado_nombre",""),l.get("fecha"),l.get("fecha_dia"),l.get("lat"),l.get("lng"),l.get("distancia",""),l.get("dentro",""),l.get("sucursal_id","")])
    return {"dias":dias,"total":len(logs),"csv":output.getvalue(),"filename":f"rutas_todos_{dias}dias_{datetime.now().strftime('%Y-%m-%d')}.csv"}

@app.get("/gps/logs/{eid}")
def gps_logs(eid: str):
    return [g for g in gps_logs_db if g["empleado_id"]==eid][::-1][:50]
@app.get("/gps/alertas")
def gps_alertas(): return [a for a in alertas_db if a.get("tipo")=="gps_fuera"][::-1]

# Resto endpoints
@app.post("/evaluaciones")
def crear_eval(data: dict):
    hoy=datetime.now()
    eid=data.get("empleado_id")
    cals=data.get("calificaciones",{})
    total=0; detalle={}
    for q in PREGUNTAS:
        if q["tipo"]=="cal":
            try: v=int(cals.get(str(q["id"]),0))
            except: v=0
            total+=v; detalle[q["txt"]]=v
    mes=hoy.strftime("%Y-%m")
    if any(ev["empleado_id"]==eid and ev["mes"]==mes for ev in evaluaciones_db):
        raise HTTPException(400, "Ya evaluado")
    nivel="Necesita Mejorar"
    if total==100: nivel="EXCELENTE 🌟"
    elif total>=90: nivel="Muy Bueno"
    elif total>=80: nivel="Bueno"
    nueva={"id":len(evaluaciones_db)+1,"empleado_id":eid,"empleado_nombre":empleados_db[eid]["nombre"],"fecha":hoy.strftime("%Y-%m-%d %H:%M"),"mes":mes,"calificaciones":cals,"detalle":detalle,"total":total,"nivel":nivel}
    evaluaciones_db.append(nueva)
    alertas_db.append({"id":str(uuid.uuid4())[:6],"empleado_id":eid,"mensaje":f"📊 EVALUACIÓN {mes}: {total}/100 - {nivel}","fecha":hoy.strftime("%Y-%m-%d %H:%M"),"total":total,"nivel":nivel,"tipo":"evaluacion"})
    return nueva

@app.get("/evaluaciones")
def list_ev(): return evaluaciones_db
@app.get("/empleado/{eid}/historial")
def hist(eid: str): return [e for e in evaluaciones_db if e["empleado_id"]==eid]
@app.get("/alertas/{eid}")
def al(eid: str): return [a for a in alertas_db if a["empleado_id"]==eid][::-1]
@app.get("/asistencias/{eid}")
def asis(eid: str): return [a for a in asistencias_db if a["empleado_id"]==eid][::-1]

HTML = """
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Control GPS Geocerca 2h</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Inter',sans-serif}
body{background:#0f172a;color:#e2e8f0}
.hero{background:linear-gradient(135deg,#6366f1,#8b5cf6,#ec4899);padding:24px 20px 50px;text-align:center}
.container{max-width:1300px;margin:-30px auto;padding:20px}
.card{background:#1e293b;border:1px solid #334155;border-radius:16px;padding:18px;margin-top:14px}
.input{width:100%;padding:10px;border-radius:10px;border:1px solid #334155;background:#0f172a;color:white;margin-top:6px}
.btn{padding:12px 16px;border-radius:10px;border:none;background:#6366f1;color:white;font-weight:800;cursor:pointer;margin-top:8px;width:100%}
.login{background:#1e293b;border:1px solid #334155;border-radius:20px;padding:28px;max-width:380px;margin:80px auto}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:900px){.grid2{grid-template-columns:1fr}}
.paso{display:flex;align-items:center;gap:12px;padding:12px;background:#0f172a;border-radius:12px;margin-top:8px;border-left:4px solid #334155}
.paso.completo{border-left-color:#10b981;background:#10b98115}
.paso.activo{border-left-color:#f59e0b;background:#f59e0b15}
.gps-on{background:#10b981;color:white;padding:8px 12px;border-radius:20px;font-size:12px;font-weight:800;display:inline-block;animation:pulse 1s infinite}
.gps-off{background:#64748b;color:white;padding:8px 12px;border-radius:20px;font-size:12px;font-weight:800;display:inline-block}
@keyframes pulse{0%{transform:scale(1)}50%{transform:scale(1.05)}100%{transform:scale(1)}}
.modal{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.8);display:none;align-items:center;justify-content:center;z-index:1000;padding:20px}
.modal-content{background:#1e293b;border-radius:16px;padding:20px;max-width:500px;width:100%;max-height:90vh;overflow:auto;border:1px solid #334155}
</style></head><body>
<div id="login" class="login"><h2 style="text-align:center">Control GPS</h2><p style="text-align:center;color:#94a3b8;font-size:11px">GPS Activo en trabajo • Desactivo en comida</p><input id="u" class="input" placeholder="admin o EMP0001"><input id="p" class="input" type="password" placeholder="admin123 o 0001"><button class="btn" onclick="login()">Ingresar</button><p id="msg" style="text-align:center;color:#f87171;font-size:12px;margin-top:8px"></p></div>

<div id="app" style="display:none">
<div class="hero"><h1 style="color:white">Control GPS Geocerca + 2h Comida Editable</h1><p style="color:white;opacity:.9;font-size:12px">📍 Entrada Activa GPS • 🍔 Comida Desactiva GPS • ↩️ Regreso Reactiva • 🏠 Salida Desactiva • 🚨 Alerta si se aleja</p></div>
<div class="container">
<div id="admin-area" style="display:none">
<div class="grid2">
<div class="card"><h3>🏢 Crear Sucursal con GPS Geocerca</h3><input id="suc_id" class="input" placeholder="ID: SUC001"><input id="suc_nombre" class="input" placeholder="Nombre: Centro"><input id="suc_dir" class="input" placeholder="Dirección"><div style="display:flex;gap:8px"><input id="suc_he" class="input" type="time" value="08:00"><input id="suc_hs" class="input" type="time" value="18:00"></div>
<div style="background:#6366f115;border:1px solid #6366f140;border-radius:10px;padding:10px;margin-top:8px">
<small style="color:#a5b4fc;font-weight:700">📍 GPS Geocerca (obligatorio para rastreo)</small><br>
<div style="display:flex;gap:8px;margin-top:6px"><input id="suc_lat" class="input" placeholder="Latitud: 19.4326" style="margin-top:0"><input id="suc_lng" class="input" placeholder="Longitud: -99.1332" style="margin-top:0"></div>
<div style="display:flex;gap:8px;margin-top:6px;align-items:center"><label style="font-size:12px;min-width:100px">Radio permitido:</label><input id="suc_radio" class="input" type="number" value="200" style="margin-top:0"><span style="font-size:12px">metros</span></div>
<button class="btn" style="background:#10b981;margin-top:6px;padding:8px" onclick="obtenerGPS()">📍 Usar mi ubicación actual para sucursal</button>
<small style="color:#94a3b8;display:block;margin-top:4px">Ve a la sucursal, dale al botón y te pone lat/lng automático. O busca en Google Maps click derecho.</small>
</div>
<button class="btn" onclick="crearSuc()">+ Crear Sucursal con GPS</button><div id="list-suc" style="margin-top:8px"></div></div>

<div class="card"><h3>👤 Nuevo Empleado</h3><div style="background:#6366f115;padding:8px;border-radius:8px"><small>Próximo: <b id="next-id" style="color:#10b981">...</b> | 120 min = 2h</small></div><div style="display:flex;gap:8px"><input id="emp_id" class="input" readonly><button class="btn" style="width:auto;margin-top:6px" onclick="generarID()">🔄</button></div><input id="emp_nombre" class="input" placeholder="Nombre *"><input id="emp_puesto" class="input" placeholder="Puesto"><input id="emp_pass" class="input" placeholder="Contraseña *"><input id="emp_tel" class="input" placeholder="Teléfono"><div style="display:flex;gap:8px;align-items:center;margin-top:8px"><label style="font-size:12px;min-width:120px">⏱️ Comida:</label><input id="emp_comida" class="input" type="number" value="120" style="margin-top:0"><span style="font-size:12px">min</span></div><div id="check-suc" style="background:#0f172a;border-radius:8px;padding:6px;margin-top:6px;max-height:80px;overflow:auto"></div><div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-top:6px"><select id="d-lunes" class="input"></select><select id="d-martes" class="input"></select><select id="d-miercoles" class="input"></select><select id="d-jueves" class="input"></select><select id="d-viernes" class="input"></select><select id="d-sabado" class="input"></select><select id="d-domingo" class="input"></select></div><button class="btn" style="background:#10b981" onclick="crearEmp()">💾 Guardar Empleado</button></div>
</div>

<div class="card"><h3>📋 Empleados - Editar TODO + GPS</h3><div id="tabla-emp"></div></div>
<div class="card" style="border:2px solid #ef4444"><h3>🚨 Alertas GPS - Fuera de sucursal (60 días / 2 meses, se borra automático)</h3><div id="gps-alertas"></div><button class="btn" style="background:#334155;margin-top:8px" onclick="cargarGPSAlertas()">🔄 Actualizar alertas GPS</button></div>
<div class="card" style="border:2px solid #10b981"><h3>🗺️ Ruta GPS Últimos 60 Días / 2 Meses - Se borra automático + Guardar en Drive</h3>
<p style="font-size:11px;color:#94a3b8">Guarda 60 días (2 meses). Al día 61 borra el día 1 automático. Puedes exportar a CSV y guardar en Google Drive en carpeta "Rutas GPS"</p>
<select id="ruta_emp" class="input"></select>
<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;margin-top:8px"><button class="btn" style="background:#10b981" onclick="verRuta()">🗺️ Ver Ruta 60 Días</button><button class="btn" style="background:#6366f1" onclick="verRutaTodos()">👁️ Ver Todos</button><button class="btn" style="background:#f59e0b" onclick="exportarDrive()">💾 Guardar en Drive</button></div>
<div style="display:flex;gap:6px;margin-top:8px"><button class="btn" style="background:#0ea5e9" onclick="exportarCSV()">📥 Descargar CSV para Drive</button><button class="btn" style="background:#334155" onclick="limpiarManual()">🗑️ Borrar rutas antiguas manual</button></div>
<div id="ruta-result" style="margin-top:10px;max-height:400px;overflow:auto;background:#0f172a;border-radius:10px;padding:10px;font-size:11px"></div>
<div id="drive-status" style="margin-top:8px;background:#10b98115;border:1px solid #10b98140;border-radius:8px;padding:8px;font-size:11px;display:none"></div>
</div>
<div class="card"><h3>⭐ Evaluación 100 pts</h3><select id="eval_emp" class="input"></select><div id="eval_preguntas"></div><div id="total-preview" style="background:linear-gradient(135deg,#10b981,#059669);border-radius:12px;padding:12px;text-align:center;color:white;margin-top:10px;display:none"><div id="total-num" style="font-size:28px;font-weight:800">0</div></div><button class="btn" style="background:#10b981" onclick="evaluar()">Guardar y Notificar</button><p id="msg-eval"></p></div>
<div class="card"><h3>📚 Historiales</h3><div id="historial-admin"></div></div>
</div>

<div id="emp-area" style="display:none">
<div class="card"><h3>⏰ Mi Jornada + GPS Geocerca <span id="gps-status" class="gps-off">GPS Desactivado</span></h3>
<p style="font-size:12px;color:#94a3b8">Comida permitida: <b id="mi-tiempo-comida">120 min (2h)</b> | Radio: <b id="mi-radio">200m</b> de sucursal</p>
<div id="gps-info" style="background:#0f172a;border-radius:10px;padding:10px;margin-top:8px;font-size:12px;display:none"><b>📍 Mi ubicación:</b> <span id="mi-ubicacion">Obteniendo...</span><br><b>Distancia a sucursal:</b> <span id="mi-distancia">--</span></div>
<div style="background:#0f172a;border-radius:12px;padding:14px;margin-top:10px">
<div id="paso-entrada" class="paso"><span>📍</span><div><b>Entrada (Activa GPS)</b><br><small id="hora-entrada">Pendiente</small></div></div>
<div id="paso-salida-comida" class="paso"><span>🍔</span><div><b>Salida a comer (Desactiva GPS)</b><br><small id="hora-salida-comida">Pendiente</small></div></div>
<div id="paso-regreso-comida" class="paso"><span>↩️</span><div><b>Regreso de comida (Reactiva GPS)</b><br><small id="hora-regreso-comida">Pendiente</small></div></div>
<div id="paso-salida-final" class="paso"><span>🏠</span><div><b>Salida final (Desactiva GPS)</b><br><small id="hora-salida-final">Pendiente</small></div></div>
</div>
<button id="btn-accion" class="btn" style="font-size:18px;padding:18px;margin-top:14px" onclick="registrar()">📍 Registrar ENTRADA</button>
<p id="msg-check" style="font-size:12px;margin-top:8px;text-align:center;color:#10b981"></p>
<div style="margin-top:12px;background:#0f172a;border-radius:10px;padding:10px;font-size:12px"><b>Resumen hoy:</b><br><span id="resumen-hoy">Sin registros</span></div>
<div id="mapa" style="margin-top:12px;background:#0f172a;border-radius:10px;padding:10px;font-size:11px;display:none"><b>Logs GPS hoy:</b><div id="gps-logs"></div></div>
</div>
<div class="card"><h3>Mis Notificaciones</h3><div id="mis-notifs"></div></div>
<div class="card"><h3>Mi Historial</h3><div id="mi-historial"></div></div>
</div>
</div></div>

<div id="modal-edit" class="modal"><div class="modal-content">
<h3>✏️ Editar Empleado - TODO</h3><input id="edit_id" class="input" readonly><input id="edit_nombre" class="input" placeholder="Nombre"><input id="edit_puesto" class="input" placeholder="Puesto"><input id="edit_password" class="input" placeholder="Contraseña"><input id="edit_telefono" class="input" placeholder="Tel"><div style="display:flex;gap:8px;align-items:center;margin-top:8px"><label style="font-size:12px;min-width:120px">Comida min:</label><input id="edit_comida" class="input" type="number" style="margin-top:0"></div><div style="display:flex;gap:8px;margin-top:8px"><label style="font-size:12px">Activo:</label><select id="edit_activo" class="input" style="margin-top:0"><option value="true">Activo</option><option value="false">Desactivado</option></select></div><button class="btn" style="background:#10b981;margin-top:12px" onclick="guardarEdicion()">💾 Guardar</button><button class="btn" style="background:#334155;margin-top:6px" onclick="cerrarModal()">Cancelar</button><button class="btn" style="background:#ef4444;margin-top:6px" onclick="eliminarEmpleado()">🗑️ Eliminar</button>
</div></div>

<script>
let USER_ID=''; let EDITANDO_ID=''; let watchId=null; let gpsActivo=false; let miPos={lat:null,lng:null};
const PREG=[
 {id:1,txt:"¿Limpieza de botarga? (1-10)",tipo:"cal"},
 {id:2,txt:"¿Limpieza de ropa? (1-10)",tipo:"cal"},
 {id:3,txt:"¿Limpieza de guantes? (1-10)",tipo:"cal"},
 {id:4,txt:"¿Limpieza de zapatos? (1-10)",tipo:"cal"},
 {id:5,txt:"¿Baile? (1-10)",tipo:"cal"},
 {id:6,txt:"¿Comentario de baile? (texto)",tipo:"texto"},
 {id:7,txt:"¿Actitud? (1-10)",tipo:"cal"},
 {id:8,txt:"¿Cumple con políticas y valores? (1-10)",tipo:"cal"},
 {id:9,txt:"¿Ambiente positivo? (1-10)",tipo:"cal"},
 {id:10,txt:"¿Disponibilidad para apoyar? (1-10)",tipo:"cal"},
 {id:11,txt:"¿Cumplimiento de horarios? (1-10)",tipo:"cal"},
 {id:12,txt:"¿Área por mejorar? (texto)",tipo:"texto"},
];
async function api(p,m='GET',b=null){const o={method:m,headers:{'Content-Type':'application/json'}}; if(b)o.body=JSON.stringify(b); const r=await fetch(p,o); if(!r.ok){const e=await r.json(); throw e;} return r.json();}
async function login(){const u=document.getElementById('u').value; const p=document.getElementById('p').value; try{const d=await api('/api/login','POST',{usuario:u,password:p}); document.getElementById('login').style.display='none'; document.getElementById('app').style.display='block'; USER_ID=u; if(d.rol==='admin'){document.getElementById('admin-area').style.display='block'; cargarTodo(); cargarGPSAlertas();} else{document.getElementById('emp-area').style.display='block'; cargarEmpleado();} }catch(e){document.getElementById('msg').innerText=e.detail||'Error';}}
async function generarID(){const d=await api('/empleados/next-id'); document.getElementById('emp_id').value=d.next_id; document.getElementById('next-id').innerText=d.next_id;}
function obtenerGPS(){if(!navigator.geolocation) return alert('GPS no soportado'); navigator.geolocation.getCurrentPosition(pos=>{document.getElementById('suc_lat').value=pos.coords.latitude; document.getElementById('suc_lng').value=pos.coords.longitude; alert('📍 GPS capturado: '+pos.coords.latitude+', '+pos.coords.longitude);}, err=>alert('Error GPS: '+err.message), {enableHighAccuracy:true});}
async function crearSuc(){const id=document.getElementById('suc_id').value; const nombre=document.getElementById('suc_nombre').value; const dir=document.getElementById('suc_dir').value; const he=document.getElementById('suc_he').value; const hs=document.getElementById('suc_hs').value; const lat=parseFloat(document.getElementById('suc_lat').value); const lng=parseFloat(document.getElementById('suc_lng').value); const radio=parseInt(document.getElementById('suc_radio').value)||200; if(!id||!nombre) return alert('ID y nombre'); if(!lat||!lng) {if(!confirm('Sin GPS no habrá geocerca. ¿Continuar?')) return;} await api('/sucursales','POST',{id,nombre,direccion:dir,hora_entrada:he,hora_salida:hs,lat:lat||null,lng:lng||null,radio:radio}); document.getElementById('suc_id').value=''; document.getElementById('suc_nombre').value=''; cargarSucs();}
async function cargarSucs(){const sucs=await api('/sucursales'); document.getElementById('list-suc').innerHTML=sucs.map(s=>`<div style="background:#0f172a;padding:8px;border-radius:8px;margin-top:6px;font-size:11px"><b>${s.id} ${s.nombre}</b> ${s.lat?`📍 ${s.lat.toFixed(5)},${s.lng.toFixed(5)} - ${s.radio}m`: '⚠️ Sin GPS'}<br>${s.direccion||''} ${s.hora_entrada||''}-${s.hora_salida||''}</div>`).join('') || 'Sin sucursales'; document.getElementById('check-suc').innerHTML=sucs.map(s=>`<label style="display:flex;gap:6px"><input type="checkbox" value="${s.id}" class="chk"> ${s.nombre}</label>`).join(''); ['lunes','martes','miercoles','jueves','viernes','sabado','domingo'].forEach(d=>{const sel=document.getElementById('d-'+d); if(sel) sel.innerHTML='<option value="">Libre</option>'+sucs.map(s=>`<option value="${s.id}">${s.nombre}</option>`).join('');});}
async function crearEmp(){const id=document.getElementById('emp_id').value; const nombre=document.getElementById('emp_nombre').value; const puesto=document.getElementById('emp_puesto').value; const pass=document.getElementById('emp_pass').value; const tel=document.getElementById('emp_tel').value; const comida=parseInt(document.getElementById('emp_comida').value)||120; if(!nombre||!pass) return alert('Nombre y contraseña'); const suc=[...document.querySelectorAll('.chk:checked')].map(c=>c.value); const hor={lunes:document.getElementById('d-lunes').value,martes:document.getElementById('d-martes').value,miercoles:document.getElementById('d-miercoles').value,jueves:document.getElementById('d-jueves').value,viernes:document.getElementById('d-viernes').value,sabado:document.getElementById('d-sabado').value,domingo:document.getElementById('d-domingo').value}; const r=await api('/empleados','POST',{id,nombre,puesto,password:pass,telefono:tel,tiempo_comida:comida,sucursales_ids:suc,horario:hor,activo:true}); alert(`✅ ${r.id} - ${r.tiempo_comida} min comida`); document.getElementById('emp_nombre').value=''; document.getElementById('emp_pass').value=''; generarID(); cargarEmps();}
async function cargarEmps(){const emps=await api('/empleados'); document.getElementById('tabla-emp').innerHTML=emps.map(e=>`<div style="display:flex;justify-content:space-between;align-items:center;background:#0f172a;padding:12px;border-radius:10px;margin-top:8px;border-left:4px solid ${e.activo?'#10b981':'#ef4444'}"><div style="font-size:12px"><b style="color:#10b981">${e.id}</b> - <b>${e.nombre}</b><br>🔑 ${e.password} | ⏱️ ${e.tiempo_comida||120} min | ${e.activo?'✅':'❌'}</div><div style="display:flex;gap:6px"><button onclick="abrirEditar('${e.id}')" style="padding:6px 10px;border-radius:8px;border:none;background:#6366f1;color:white;font-size:12px">✏️ Editar TODO</button><button onclick="toggleEmp('${e.id}')" style="padding:6px 10px;border-radius:8px;border:none;background:${e.activo?'#ef4444':'#10b981'};color:white;font-size:12px">${e.activo?'Desactivar':'Activar'}</button></div></div>`).join(''); document.getElementById('eval_emp').innerHTML=emps.filter(e=>e.activo).map(e=>`<option value="${e.id}">${e.id} - ${e.nombre} (${e.tiempo_comida||120}min)</option>`).join(''); document.getElementById('ruta_emp').innerHTML=emps.map(e=>`<option value="${e.id}">${e.id} - ${e.nombre}</option>`).join('');}
async function verRuta(){const eid=document.getElementById('ruta_emp').value; const data=await api('/gps/ruta/'+eid+'?dias=60'); let html=`<b>📍 Ruta ${eid} - Últimos 60 días (2 meses) - Total puntos: ${data.total_puntos}</b><br><small>Se borra automático después de 60 días. Guardado también en Drive si activas respaldo.</small><br><br>`; for(const dia in data.ruta_por_dia){html+=`<div style="background:#1e293b;border-radius:8px;padding:8px;margin-top:8px"><b>${dia} - ${data.ruta_por_dia[dia].length} puntos</b><br>`+data.ruta_por_dia[dia].map(p=>`${p.hora} - ${p.lat.toFixed(5)},${p.lng.toFixed(5)} - ${p.distancia?Math.round(p.distancia)+'m':''} ${p.dentro?'✅':'❌'} - <a href="https://www.google.com/maps?q=${p.lat},${p.lng}" target="_blank" style="color:#60a5fa">Maps</a>`).join('<br>')+`</div>`;} if(!Object.keys(data.ruta_por_dia).length) html+='Sin ruta últimos 60 días'; document.getElementById('ruta-result').innerHTML=html;}
async function verRutaTodos(){const data=await api('/gps/ruta-todos?dias=60'); document.getElementById('ruta-result').innerHTML=`<b>🗺️ Todos - Últimos 60 días (2 meses) - ${data.total_puntos} puntos (se borra auto después de 60 días)</b><br><br>`+data.logs.slice(0,100).map(l=>`${l.fecha} - ${l.empleado_id} ${l.empleado_nombre||''} - ${l.lat.toFixed(5)},${l.lng.toFixed(5)} - ${l.distancia?Math.round(l.distancia)+'m':''} ${l.dentro?'✅':'❌'} - <a href="https://www.google.com/maps?q=${l.lat},${l.lng}" target="_blank" style="color:#60a5fa">Maps</a>`).join('<br>') || 'Sin logs';}
async function exportarCSV(){const eid=document.getElementById('ruta_emp').value; if(!eid) return alert('Selecciona empleado'); const data=await api('/gps/export-csv/'+eid+'?dias=60'); const blob=new Blob([data.csv],{type:'text/csv'}); const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download=data.filename; a.click(); document.getElementById('drive-status').style.display='block'; document.getElementById('drive-status').innerHTML=`✅ CSV descargado: ${data.filename}<br>📁 Súbelo a tu Google Drive > Carpeta "Rutas GPS" > Subcarpeta ${eid}<br>💡 Tip: Crea en Drive carpeta "Rutas GPS" y guarda ahí, así guardas 2 meses`;}
async function exportarDrive(){
 const eid=document.getElementById('ruta_emp').value;
 document.getElementById('drive-status').style.display='block';
 document.getElementById('drive-status').innerHTML=`⏳ Preparando guardado en Drive para ${eid} últimos 60 días...<br>📂 Carpeta: Rutas GPS/${eid}/<br>Para guardado automático real en Drive necesitas conectar tu Google Drive:<br><br>1. Ve a drive.google.com<br>2. Crea carpeta "Rutas GPS"<br>3. Dentro crea subcarpetas por empleado: EMP0001, EMP0002, etc.<br>4. Cada que descargues CSV, súbelo ahí<br><br>🔄 Futuro: puedo conectarlo directo a tu Drive con API si me das acceso. Por ahora descarga CSV y súbelo manual. Los datos se guardan 60 días en la app y se borran auto al día 61.`;
 // Intentar guardar en localStorage como simulación de Drive
 try{
  const data=await api('/gps/export-csv/'+eid+'?dias=60');
  localStorage.setItem('drive_backup_'+eid+'_'+new Date().toISOString().split('T')[0], data.csv);
  document.getElementById('drive-status').innerHTML+=`<br><br>✅ Respaldo local guardado también en navegador (simula Drive) - ${data.filename} - ${data.csv.split('\\n').length} lineas`;
 }catch(e){}
}
async function limpiarManual(){if(!confirm('¿Borrar rutas más antiguas de 60 días ahora?')) return; const r=await api('/gps/ruta-todos?dias=60'); alert('Limpieza hecha. Se mantienen solo últimos 60 días. Total puntos: '+r.total_puntos); cargarGPSAlertas();}
function abrirEditar(id){EDITANDO_ID=id; api('/empleados').then(emps=>{const e=emps.find(x=>x.id===id); if(!e) return; document.getElementById('edit_id').value=e.id; document.getElementById('edit_nombre').value=e.nombre||''; document.getElementById('edit_puesto').value=e.puesto||''; document.getElementById('edit_password').value=e.password||''; document.getElementById('edit_telefono').value=e.telefono||''; document.getElementById('edit_comida').value=e.tiempo_comida||120; document.getElementById('edit_activo').value=e.activo?'true':'false'; document.getElementById('modal-edit').style.display='flex';});}
function cerrarModal(){document.getElementById('modal-edit').style.display='none';}
async function guardarEdicion(){const data={nombre:document.getElementById('edit_nombre').value,puesto:document.getElementById('edit_puesto').value,password:document.getElementById('edit_password').value,telefono:document.getElementById('edit_telefono').value,tiempo_comida:parseInt(document.getElementById('edit_comida').value)||120,activo:document.getElementById('edit_activo').value==='true'}; await api('/empleados/'+EDITANDO_ID,'PUT',data); alert('✅ Guardado - '+data.tiempo_comida+' min'); cerrarModal(); cargarEmps();}
async function eliminarEmpleado(){if(!confirm('¿Eliminar '+EDITANDO_ID+'?')) return; await fetch('/empleados/'+EDITANDO_ID,{method:'DELETE'}); cerrarModal(); cargarEmps();}
async function toggleEmp(id){await api('/empleados/'+id+'/toggle','PUT'); cargarEmps();}
async function cargarTodo(){await cargarSucs(); await generarID(); await cargarEmps(); renderPreguntas(); verHistorialAdmin();}
function renderPreguntas(){const div=document.getElementById('eval_preguntas'); div.innerHTML=PREG.map(q=>{if(q.tipo==='cal') return `<div style="background:#0f172a;padding:10px;border-radius:8px;margin-top:8px"><label>${q.id}. ${q.txt}</label><select data-id="${q.id}" class="input sel-cal" onchange="calcTotal()"><option value="0">0</option><option>1</option><option>2</option><option>3</option><option>4</option><option>5</option><option>6</option><option>7</option><option>8</option><option>9</option><option selected>10</option></select></div>`; else return `<div style="background:#0f172a;padding:10px;border-radius:8px;margin-top:8px"><label>${q.id}. ${q.txt}</label><textarea data-id="${q.id}" class="input" rows="2"></textarea></div>`;}).join(''); calcTotal();}
function calcTotal(){let t=0; document.querySelectorAll('.sel-cal').forEach(s=>t+=parseInt(s.value||0)); const b=document.getElementById('total-preview'); b.style.display='block'; document.getElementById('total-num').innerText=t+'/100';}
async function evaluar(){const eid=document.getElementById('eval_emp').value; const cals={}; document.querySelectorAll('[data-id]').forEach(el=>cals[el.dataset.id]=el.value); try{const r=await api('/evaluaciones','POST',{empleado_id:eid,calificaciones:cals}); document.getElementById('msg-eval').innerText=`✅ ${r.total}/100`; verHistorialAdmin();}catch(e){document.getElementById('msg-eval').innerText='❌ '+(e.detail||'Error');}}
async function verHistorialAdmin(){try{const evals=await api('/evaluaciones'); document.getElementById('historial-admin').innerHTML=evals.map(e=>`<div style="background:#0f172a;padding:8px;border-radius:8px;margin-top:6px"><b>${e.empleado_id}</b> - ${e.total}/100 - ${e.fecha}</div>`).join('') || 'Sin';}catch(e){}}
async function cargarGPSAlertas(){try{const alertas=await api('/gps/alertas'); document.getElementById('gps-alertas').innerHTML=alertas.slice(0,20).map(a=>`<div style="background:#ef444415;border:1px solid #ef4444;border-radius:8px;padding:8px;margin-top:6px;font-size:11px"><b style="color:#ef4444">🚨 ${a.empleado_id}</b> - ${a.mensaje}<br><small>${a.fecha} - Dist: ${a.distancia?Math.round(a.distancia)+'m':''}</small><br><a href="https://www.google.com/maps?q=${a.lat},${a.lng}" target="_blank" style="color:#60a5fa">Ver en Maps</a></div>`).join('') || 'Sin alertas GPS';}catch(e){document.getElementById('gps-alertas').innerText='Error cargando';}}

function activarGPS(){if(gpsActivo) return; if(!navigator.geolocation) return alert('GPS no soportado'); document.getElementById('gps-status').innerText='🟢 GPS ACTIVO - Rastreando'; document.getElementById('gps-status').className='gps-on'; document.getElementById('gps-info').style.display='block'; gpsActivo=true; watchId=navigator.geolocation.watchPosition(pos=>{miPos={lat:pos.coords.latitude,lng:pos.coords.longitude,acc:pos.coords.accuracy}; document.getElementById('mi-ubicacion').innerText=`${miPos.lat.toFixed(6)}, ${miPos.lng.toFixed(6)} (±${Math.round(miPos.acc)}m)`; // enviar al backend cada 30s
  api('/gps/update','POST',{empleado_id:USER_ID,lat:miPos.lat,lng:miPos.lng,accuracy:miPos.acc}).then(r=>{if(r.distancia!=null){document.getElementById('mi-distancia').innerText=`${Math.round(r.distancia)}m ${r.dentro?'✅ Dentro':'❌ FUERA'} - Permitido ${document.getElementById('mi-radio')?document.getElementById('mi-radio').innerText:''}`; if(!r.dentro){document.getElementById('mi-distancia').style.color='#ef4444';} else {document.getElementById('mi-distancia').style.color='#10b981';}}}).catch(()=>{});}, err=>{document.getElementById('mi-ubicacion').innerText='Error GPS: '+err.message;}, {enableHighAccuracy:true, maximumAge:10000, timeout:10000});}
function desactivarGPS(){if(watchId!==null){navigator.geolocation.clearWatch(watchId); watchId=null;} gpsActivo=false; document.getElementById('gps-status').innerText='⚪ GPS Desactivado (en comida/descanso)'; document.getElementById('gps-status').className='gps-off';}

async function cargarEmpleado(){
 try{
  const hoy=await api('/asistencia/hoy/'+USER_ID);
  actualizarUI(hoy);
  document.getElementById('mi-tiempo-comida').innerText=hoy.tiempo_permitido+' min ('+(hoy.tiempo_permitido/60)+'h)';
  if(hoy.sucursal) document.getElementById('mi-radio').innerText= (hoy.sucursal.radio||200)+'m de '+ (hoy.sucursal.nombre||'sucursal');
  const hist=await api('/empleado/'+USER_ID+'/historial');
  document.getElementById('mi-historial').innerHTML=hist.map(e=>`<div style="background:#0f172a;padding:10px;border-radius:8px;margin-top:6px;text-align:center"><div style="font-size:28px;font-weight:800;color:${e.total==100?'#f59e0b':'#10b981'}">${e.total}/100</div></div>`).join('') || 'Sin';
  const notifs=await api('/alertas/'+USER_ID);
  document.getElementById('mis-notifs').innerHTML=notifs.map(n=>`<div style="background:#0f172a;padding:8px;border-radius:8px;margin-top:6px">${n.mensaje}<br><small>${n.fecha}</small></div>`).join('') || 'Sin';
  const logs=await api('/gps/logs/'+USER_ID).catch(()=>[]);
  if(logs.length){document.getElementById('mapa').style.display='block'; document.getElementById('gps-logs').innerHTML=logs.slice(0,5).map(l=>`${l.fecha} - ${l.distancia?Math.round(l.distancia)+'m':''} ${l.dentro?'✅': '❌'} - <a href="https://www.google.com/maps?q=${l.lat},${l.lng}" target="_blank" style="color:#60a5fa">Maps</a>`).join('<br>');}
  // auto activar/desactivar GPS segun estado
  if(hoy.gps_activo){activarGPS();} else {desactivarGPS();}
 }catch(e){console.log(e)}
}
function actualizarUI(data){
 const btn=document.getElementById('btn-accion');
 btn.innerText=data.texto_boton;
 btn.style.background=data.color;
 if(data.siguiente==='completo'){btn.disabled=true; desactivarGPS();} else {btn.disabled=false;}
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
 if(data.salida_comida) resumen+=`Salida comida: ${data.salida_comida} (GPS Desactivado)<br>`;
 if(data.regreso_comida) {resumen+=`Regreso: ${data.regreso_comida} - Comida: ${data.min_comida||0}/${data.tiempo_permitido} min `; if(data.retardo_comida>0) resumen+=`<span style="color:#ef4444">⚠️ +${data.retardo_comida} MIN</span>`; else resumen+=`<span style="color:#10b981">✅</span>`; resumen+='<br>';}
 if(data.salida_final) resumen+=`Salida: ${data.salida_final} - GPS Desactivado<br><b>Horas: ${data.horas_trabajadas||0}h</b><br>`;
 if(!resumen) resumen='Sin registros';
 document.getElementById('resumen-hoy').innerHTML=resumen;
 window.estadoActual=data.siguiente;
 // gestionar GPS
 if(data.gps_activo){activarGPS();} else if(data.siguiente!=='entrada'){desactivarGPS();}
}
async function registrar(){
 try{
  // obtener GPS actual para registrar
  let lat=null,lng=null,acc=null;
  if(navigator.geolocation){
    try{
      const pos=await new Promise((res,rej)=>navigator.geolocation.getCurrentPosition(res,rej,{enableHighAccuracy:true,timeout:8000}));
      lat=pos.coords.latitude; lng=pos.coords.longitude; acc=pos.coords.accuracy;
    }catch(e){console.log('GPS no disponible, registrando sin GPS');}
  }
  const tipo=window.estadoActual;
  const r=await api('/asistencia/registrar','POST',{empleado_id:USER_ID,tipo:tipo,lat:lat,lng:lng,accuracy:acc});
  document.getElementById('msg-check').innerText=`✅ ${tipo} registrado ${lat?`con GPS ${lat.toFixed(5)},${lng.toFixed(5)}`: 'sin GPS'}`;
  const hoy=await api('/asistencia/hoy/'+USER_ID);
  actualizarUI(hoy);
  if(tipo==='entrada'){activarGPS();} else if(tipo==='salida_comida'){desactivarGPS();} else if(tipo==='regreso_comida'){activarGPS();} else if(tipo==='salida_final'){desactivarGPS();}
 }catch(e){document.getElementById('msg-check').innerText='❌ '+(e.detail||'Error');}
}
</script></body></html>
"""

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home(): return HTML
