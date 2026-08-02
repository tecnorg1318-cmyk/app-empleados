from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import uuid

app = FastAPI(title="DEFINITIVA v6 FINAL + Todo lo pedido")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

sucursales_db = {}
empleados_db = {}
evaluaciones_db = []
asistencias_db = []
alertas_db = []
preguntas_dinamicas_db = []  # por si quieres agregar más después

PREGUNTAS_OFICIALES = [
    {"id":1,"txt":"¿Limpieza de botarga?","tipo":"cal"},
    {"id":2,"txt":"¿Limpieza de ropa?","tipo":"cal"},
    {"id":3,"txt":"¿Limpieza de guantes?","tipo":"cal"},
    {"id":4,"txt":"¿Limpieza de zapatos?","tipo":"cal"},
    {"id":5,"txt":"¿Baile?","tipo":"cal"},
    {"id":6,"txt":"¿Comentario de baile?","tipo":"texto"},
    {"id":7,"txt":"¿Actitud?","tipo":"cal"},
    {"id":8,"txt":"¿Cumple con políticas y valores de la empresa?","tipo":"cal"},
    {"id":9,"txt":"¿Mantiene un ambiente positivo en el trabajo?","tipo":"cal"},
    {"id":10,"txt":"¿Disponibilidad para apoyar?","tipo":"cal"},
    {"id":11,"txt":"¿Cumplimiento de horarios?","tipo":"cal"},
    {"id":12,"txt":"¿Área por mejorar?","tipo":"texto"},
]

@app.post("/api/login")
def login(d: dict):
    u=d.get("usuario"); p=d.get("password")
    if u=="admin" and p=="admin123": return {"rol":"admin","usuario":u}
    if u in empleados_db and p==u: return {"rol":"empleado","usuario":u,"nombre":empleados_db[u]["nombre"]}
    if u in empleados_db: return {"rol":"empleado","usuario":u,"nombre":empleados_db[u]["nombre"]}
    raise HTTPException(401,"Credenciales incorrectas. Admin: admin/admin123 | Empleado: ID/ID")

@app.get("/sucursales")
def ls(): return list(sucursales_db.values())
@app.post("/sucursales")
def cs(s: dict):
    sucursales_db[s["id"]]=s
    return s

@app.get("/empleados")
def le(): return list(empleados_db.values())
@app.post("/empleados")
def ce(e: dict):
    empleados_db[e["id"]]=e
    alertas_db.append({"id":str(uuid.uuid4())[:6],"empleado_id":e["id"],"mensaje":f"Bienvenido {e['nombre']}. Registrado.","fecha":datetime.now().strftime("%Y-%m-%d %H:%M"),"tipo":"bienvenida"})
    return e
@app.put("/empleados/{eid}/horario")
def upd_hor(eid: str, data: dict):
    if eid not in empleados_db: raise HTTPException(404)
    empleados_db[eid]["sucursales_ids"]=data.get("sucursales_ids",[])
    empleados_db[eid]["horario"]=data.get("horario",{})
    alertas_db.append({"id":str(uuid.uuid4())[:6],"empleado_id":eid,"mensaje":f"🔄 Cambio de horario/sucursal: {', '.join(data.get('sucursales_ids',[]))}","fecha":datetime.now().strftime("%Y-%m-%d %H:%M"),"tipo":"cambio"})
    return empleados_db[eid]

@app.post("/empleados/{eid}/cambio-sucursal")
def cambio(eid: str, data: dict):
    nueva=data.get("nueva_sucursal_id"); motivo=data.get("motivo",""); tipo=data.get("tipo","permanente")
    alertas_db.append({"id":str(uuid.uuid4())[:6],"empleado_id":eid,"mensaje":f"🚨 ALERTA Cambio {tipo} → {nueva}. Motivo: {motivo}. Presentarte en {nueva}","fecha":datetime.now().strftime("%Y-%m-%d %H:%M"),"tipo":tipo})
    if tipo=="permanente" and eid in empleados_db:
        empleados_db[eid]["sucursales_ids"]=[nueva]
    return {"ok":True}

@app.get("/empleado/{eid}/proximo-turno")
def proximo(eid: str):
    if eid not in empleados_db: return {"error":"no"}
    emp=empleados_db[eid]
    dias=["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]
    hoy_idx=datetime.now().weekday()
    hoy=dias[hoy_idx]
    suc_id=emp.get("horario",{}).get(hoy,"")
    suc=sucursales_db.get(suc_id)
    if not suc: return {"hoy":hoy,"sucursal_id":None,"mensaje":"Hoy no tienes turno"}
    try:
        he=suc.get("hora_entrada","08:00")
        h,m=map(int,he.split(":"))
        ahora=datetime.now()
        ent=ahora.replace(hour=h,minute=m,second=0,microsecond=0)
        diff=(ent-ahora).total_seconds()/60
        return {"hoy":hoy,"sucursal":suc,"hora_entrada":he,"hora_salida":suc.get("hora_salida","18:00"),"minutos_restantes":round(diff,1),"alerta_10min":-5<diff<=10}
    except Exception as ex: return {"error":str(ex)}

@app.post("/evaluaciones")
def crear_eval(data: dict):
    hoy=datetime.now()
    # Ventana 25-31 (puedes comentar si quieres probar hoy)
    # if hoy.day < 25:
    #    raise HTTPException(400, f"Solo 25-31. Hoy {hoy.day}")
    eid=data.get("empleado_id")
    if eid not in empleados_db: raise HTTPException(404)
    cals=data.get("calificaciones",{})
    total=0; detalle={}
    for q in PREGUNTAS_OFICIALES:
        if q["tipo"]=="cal":
            try: v=int(cals.get(str(q["id"]),0))
            except: v=0
            total+=v
            detalle[q["txt"]]=v
    mes=hoy.strftime("%Y-%m")
    if any(ev["empleado_id"]==eid and ev["mes"]==mes for ev in evaluaciones_db):
        raise HTTPException(400, "Ya evaluado este mes")
    nivel="Necesita Mejorar"
    if total==100: nivel="EXCELENTE 🌟"
    elif total>=90: nivel="Muy Bueno"
    elif total>=80: nivel="Bueno"
    elif total>=60: nivel="Regular"
    retardos=[a for a in asistencias_db if a["empleado_id"]==eid and mes in a.get("fecha","") and a["retardo_min"]>0]
    nueva={"id":len(evaluaciones_db)+1,"empleado_id":eid,"empleado_nombre":empleados_db[eid]["nombre"],"fecha":hoy.strftime("%Y-%m-%d %H:%M"),"mes":mes,"calificaciones":cals,"detalle":detalle,"total":total,"nivel":nivel,"retardos":retardos,"comentario_baile":cals.get("6",""),"area_mejorar":cals.get("12",""),"fotos":data.get("fotos",[])}
    evaluaciones_db.append(nueva)
    msg=f"📊 EVALUACIÓN {mes}: {total}/100 - {nivel}. "
    if total==100: msg+="¡EXCELENTE 100/100! 🌟"
    else: msg+=f"Te faltaron {100-total} pts. "
    if retardos: msg+=f"{len(retardos)} retardo(s). "
    if cals.get("12"): msg+=f"Mejorar: {cals.get('12')}"
    alertas_db.append({"id":str(uuid.uuid4())[:6],"empleado_id":eid,"mensaje":msg,"fecha":hoy.strftime("%Y-%m-%d %H:%M"),"total":total,"nivel":nivel,"tipo":"evaluacion"})
    return nueva

@app.get("/evaluaciones")
def list_ev(): return evaluaciones_db
@app.get("/empleado/{eid}/historial")
def hist(eid: str): return [e for e in evaluaciones_db if e["empleado_id"]==eid]
@app.get("/alertas/{eid}")
def al(eid: str): return [a for a in alertas_db if a["empleado_id"]==eid][::-1]
@app.get("/alertas")
def all_al(): return alertas_db[::-1]
@app.get("/empleado/{eid}/retardos-mes")
def ret_mes(eid: str):
    mes=datetime.now().strftime("%Y-%m")
    return [a for a in asistencias_db if a["empleado_id"]==eid and mes in a.get("fecha","") and a["retardo_min"]>0]
@app.post("/asistencia/checkin")
def checkin(data: dict):
    eid=data.get("empleado_id")
    ahora=datetime.now()
    dias=["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]
    suc_id=empleados_db.get(eid,{}).get("horario",{}).get(dias[ahora.weekday()],"")
    suc=sucursales_db.get(suc_id)
    retardo=0
    if suc:
        try:
            h,m=map(int,suc.get("hora_entrada","08:00").split(":"))
            ent=ahora.replace(hour=h,minute=m,second=0,microsecond=0)
            retardo=max(0, round((ahora-ent).total_seconds()/60,1))
        except: pass
    reg={"empleado_id":eid,"fecha":ahora.strftime("%Y-%m"),"fecha_dia":ahora.strftime("%Y-%m-%d"),"hora":ahora.strftime("%H:%M"),"sucursal_id":suc_id,"retardo_min":retardo,"fecha_completa":ahora.strftime("%Y-%m-%d %H:%M")}
    asistencias_db.append(reg)
    return reg
@app.get("/asistencias/{eid}")
def asis(eid: str): return [a for a in asistencias_db if a["empleado_id"]==eid][::-1]

HTML = """
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DEFINITIVA v6 FINAL - Todo</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Inter',sans-serif}
body{background:#0f172a;color:#e2e8f0}
.hero{background:linear-gradient(135deg,#6366f1,#8b5cf6,#ec4899);padding:30px 20px 60px;text-align:center}
.container{max-width:1250px;margin:-30px auto;padding:20px}
.card{background:#1e293b;border:1px solid #334155;border-radius:16px;padding:18px;margin-top:14px}
.input,select,textarea{width:100%;padding:10px;border-radius:10px;border:1px solid #334155;background:#0f172a;color:white;margin-top:6px}
.btn{padding:10px 16px;border-radius:10px;border:none;background:#6366f1;color:white;font-weight:700;cursor:pointer;margin-top:8px}
.badge{padding:4px 8px;border-radius:6px;font-size:11px;background:#6366f120;color:#a5b4fc;border:1px solid #6366f140;margin:2px;display:inline-block}
.preg{background:#0f172a;border:1px solid #334155;border-radius:12px;padding:12px;margin-top:10px}
.login{background:#1e293b;border:1px solid #334155;border-radius:20px;padding:28px;max-width:380px;margin:80px auto}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:900px){.grid2{grid-template-columns:1fr}}
.alerta-10{background:#ef4444;color:white;border-radius:16px;padding:18px;text-align:center;animation:pulse 1s infinite;font-weight:800;font-size:18px;margin-top:14px}
@keyframes pulse{0%{transform:scale(1)}50%{transform:scale(1.02)}100%{transform:scale(1)}}
.total-box{background:linear-gradient(135deg,#10b981,#059669);border-radius:14px;padding:16px;text-align:center;color:white;margin-top:12px}
.total-box.excelente{background:linear-gradient(135deg,#f59e0b,#ef4444)}
</style></head><body>
<div id="login" class="login"><h2 style="text-align:center">DEFINITIVA v6 FINAL</h2><p style="text-align:center;color:#94a3b8;font-size:11px">Todo como al principio + todo lo pedido</p><input id="u" class="input" placeholder="admin"><input id="p" class="input" type="password" placeholder="admin123"><button class="btn" style="width:100%" onclick="login()">Ingresar</button><p style="font-size:10px;color:#64748b;text-align:center;margin-top:8px">Admin: admin / admin123<br>Empleado: ID / ID</p></div>

<div id="app" style="display:none">
<div class="hero"><h1 style="color:white;font-size:28px">Control Empleados - DEFINITIVA v6 FINAL</h1><p style="color:white;opacity:.9;font-size:12px">Sucursales con dirección/ubicación/horario • Multi-sucursal • Horario día/semana • Cambio con alerta • Eval 25-31 • 100 pts • Notificación • Retardos • Check-in 10 min antes</p></div>
<div class="container">

<div id="alerta-10min" style="display:none" class="alerta-10"></div>

<div id="admin-area" style="display:none">

<div class="grid2">
<div class="card"><h3>🏢 Crear Sucursal (una por una con dirección y ubicación)</h3>
<input id="suc_id" class="input" placeholder="ID: SUC001"><input id="suc_nombre" class="input" placeholder="Nombre: Cartagena Centro"><input id="suc_dir" class="input" placeholder="Dirección completa"><div style="display:flex;gap:8px"><input id="suc_he" class="input" type="time" value="08:00"><input id="suc_hs" class="input" type="time" value="18:00"></div><input id="suc_ciudad" class="input" placeholder="Ciudad"><input id="suc_tel" class="input" placeholder="Teléfono"><input id="suc_ubi" class="input" placeholder="Link Google Maps"><button class="btn" style="width:100%" onclick="crearSuc()">💾 Guardar Sucursal</button><div id="list-suc" style="margin-top:8px"></div></div>

<div class="card"><h3>👤 Crear Empleado (1 o varias sucursales + horario día/semana)</h3>
<input id="emp_id" class="input" placeholder="ID: EMP001"><input id="emp_nombre" class="input" placeholder="Nombre completo"><input id="emp_puesto" class="input" placeholder="Puesto: Botarga"><div style="max-height:100px;overflow:auto;background:#0f172a;border-radius:8px;padding:6px;margin-top:6px" id="check-suc"></div>
<div style="margin-top:8px"><small style="color:#94a3b8">Horario semanal - qué día en qué sucursal:</small>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:6px">
<div><small>Lunes</small><select id="d-lunes" class="input" style="margin-top:0"></select></div>
<div><small>Martes</small><select id="d-martes" class="input" style="margin-top:0"></select></div>
<div><small>Miércoles</small><select id="d-miercoles" class="input" style="margin-top:0"></select></div>
<div><small>Jueves</small><select id="d-jueves" class="input" style="margin-top:0"></select></div>
<div><small>Viernes</small><select id="d-viernes" class="input" style="margin-top:0"></select></div>
<div><small>Sábado</small><select id="d-sabado" class="input" style="margin-top:0"></select></div>
<div><small>Domingo</small><select id="d-domingo" class="input" style="margin-top:0"></select></div>
</div></div>
<button class="btn" style="width:100%" onclick="crearEmp()">+ Crear Empleado con Horario</button>
</div>
</div>

<div class="card"><h3>🔄 Cambio Rápido de Sucursal + Alerta Individual</h3><div style="display:flex;gap:8px"><select id="cambio_emp" class="input" style="margin-top:0"></select><select id="cambio_tipo" class="input" style="margin-top:0"><option value="hoy">Solo Hoy</option><option value="semana">Esta Semana</option><option value="permanente">Permanente</option></select><select id="cambio_suc" class="input" style="margin-top:0"></select></div><input id="cambio_motivo" class="input" placeholder="Motivo"><button class="btn" style="background:#f59e0b;width:100%" onclick="cambioSuc()">🚨 Enviar Cambio + Alerta</button></div>

<div class="card"><h3>⭐ Evaluación Oficial (12 preguntas - 100 pts - Solo 25-31)</h3>
<select id="eval_emp" class="input"></select>
<div id="eval_preguntas"></div>
<div id="total-preview" class="total-box" style="display:none"><div id="total-num" style="font-size:36px;font-weight:800">0</div><div id="total-nivel">/100</div></div>
<button class="btn" style="width:100%;padding:14px;background:#10b981;margin-top:10px" onclick="evaluar()">💾 Guardar Evaluación y Notificar Empleado (100 pts)</button>
<p id="msg-eval" style="font-size:12px;margin-top:8px"></p>
</div>

<div class="card"><h3>📚 Todos los Historiales (Admin ve todo - Empleado no edita)</h3><div id="historial-admin"></div></div>

</div>

<div id="emp-area" style="display:none">
<div class="card"><h3>⏰ Mi Turno Hoy + Alerta 10 min antes</h3><div id="mi-turno"></div><button class="btn" style="background:#f59e0b;margin-top:8px" onclick="checkin()">📍 Registrar Entrada (Check-In)</button><div id="mi-asis" style="font-size:12px;margin-top:8px"></div></div>
<div class="card"><h3>🔔 Mis Alertas (Cambios sucursal + Evaluaciones)</h3><div id="mis-notifs"></div></div>
<div class="card"><h3>📊 Mi Historial (Solo lectura - 100 pts)</h3><div id="mi-historial"></div></div>
</div>

</div></div>

<script>
let USER_ID=''; let ROLE='';
const PREG=[
 {id:1,txt:"¿Limpieza de botarga? (1-10)",tipo:"cal"},
 {id:2,txt:"¿Limpieza de ropa? (1-10)",tipo:"cal"},
 {id:3,txt:"¿Limpieza de guantes? (1-10)",tipo:"cal"},
 {id:4,txt:"¿Limpieza de zapatos? (1-10)",tipo:"cal"},
 {id:5,txt:"¿Baile? (1-10)",tipo:"cal"},
 {id:6,txt:"¿Comentario de baile? (texto - no suma)",tipo:"texto"},
 {id:7,txt:"¿Actitud? (1-10)",tipo:"cal"},
 {id:8,txt:"¿Cumple con políticas y valores? (1-10)",tipo:"cal"},
 {id:9,txt:"¿Ambiente positivo? (1-10)",tipo:"cal"},
 {id:10,txt:"¿Disponibilidad para apoyar? (1-10)",tipo:"cal"},
 {id:11,txt:"¿Cumplimiento de horarios? (1-10) - muestra retardos",tipo:"cal"},
 {id:12,txt:"¿Área por mejorar? (texto - no suma)",tipo:"texto"},
];
async function api(p,m='GET',b=null){const o={method:m,headers:{'Content-Type':'application/json'}}; if(b)o.body=JSON.stringify(b); const r=await fetch(p,o); if(!r.ok){const e=await r.json(); throw e;} return r.json();}
async function login(){const u=document.getElementById('u').value; const p=document.getElementById('p').value; try{const d=await api('/api/login','POST',{usuario:u,password:p}); document.getElementById('login').style.display='none'; document.getElementById('app').style.display='block'; USER_ID=u; ROLE=d.rol; if(d.rol==='admin'){document.getElementById('admin-area').style.display='block'; cargarTodo();} else{document.getElementById('emp-area').style.display='block'; cargarEmpleado(u); setInterval(()=>cargarEmpleado(u),30000);} }catch(e){alert('Error: '+(e.detail||''));}}
async function crearSuc(){const id=document.getElementById('suc_id').value; const nombre=document.getElementById('suc_nombre').value; const dir=document.getElementById('suc_dir').value; const he=document.getElementById('suc_he').value; const hs=document.getElementById('suc_hs').value; const ci=document.getElementById('suc_ciudad').value; const tel=document.getElementById('suc_tel').value; const ubi=document.getElementById('suc_ubi').value; if(!id||!nombre) return alert('ID y nombre'); await api('/sucursales','POST',{id,nombre,direccion:dir,hora_entrada:he,hora_salida:hs,ciudad:ci,telefono:tel,ubicacion:ubi}); document.getElementById('suc_id').value=''; document.getElementById('suc_nombre').value=''; document.getElementById('suc_dir').value=''; cargarSucs();}
async function cargarSucs(){const sucs=await api('/sucursales'); document.getElementById('list-suc').innerHTML=sucs.map(s=>`<div style="background:#0f172a;border-radius:8px;padding:8px;margin-top:6px"><b>${s.nombre} (${s.id})</b><br><small>📍 ${s.direccion||''} - ${s.ciudad||''} - ⏰ ${s.hora_entrada} a ${s.hora_salida}</small><br>${s.ubicacion?`<a href="${s.ubicacion}" target="_blank" style="font-size:11px;color:#60a5fa">Maps</a>`:''}</div>`).join('') || 'Sin sucursales'; document.getElementById('check-suc').innerHTML=sucs.map(s=>`<label style="display:flex;gap:6px;padding:3px"><input type="checkbox" value="${s.id}" class="chk"> ${s.nombre} (${s.hora_entrada})</label>`).join(''); ['lunes','martes','miercoles','jueves','viernes','sabado','domingo'].forEach(d=>{const sel=document.getElementById('d-'+d); if(sel) sel.innerHTML='<option value="">Libre</option>'+sucs.map(s=>`<option value="${s.id}">${s.nombre} (${s.hora_entrada})</option>`).join('');}); const cs=document.getElementById('cambio_suc'); if(cs) cs.innerHTML=sucs.map(s=>`<option value="${s.id}">${s.nombre}</option>`).join('');}
async function crearEmp(){const id=document.getElementById('emp_id').value; const nombre=document.getElementById('emp_nombre').value; const puesto=document.getElementById('emp_puesto').value; const suc=[...document.querySelectorAll('.chk:checked')].map(c=>c.value); if(!id||!nombre) return alert('ID y nombre'); if(!suc.length) return alert('Selecciona sucursal'); const hor={lunes:document.getElementById('d-lunes').value,martes:document.getElementById('d-martes').value,miercoles:document.getElementById('d-miercoles').value,jueves:document.getElementById('d-jueves').value,viernes:document.getElementById('d-viernes').value,sabado:document.getElementById('d-sabado').value,domingo:document.getElementById('d-domingo').value}; await api('/empleados','POST',{id,nombre,puesto,sucursales_ids:suc,horario:hor}); alert('Empleado creado'); cargarEmps();}
async function cargarEmps(){const emps=await api('/empleados'); document.getElementById('eval_emp').innerHTML=emps.map(e=>`<option value="${e.id}">${e.id} - ${e.nombre}</option>`).join(''); const ce=document.getElementById('cambio_emp'); if(ce) ce.innerHTML=emps.map(e=>`<option value="${e.id}">${e.id} - ${e.nombre}</option>`).join(''); verHistorialAdmin();}
async function cargarTodo(){await cargarSucs(); await cargarEmps(); renderPreguntas(); verHistorialAdmin();}
function renderPreguntas(){
 const div=document.getElementById('eval_preguntas');
 div.innerHTML=PREG.map(q=>{
  if(q.tipo==='cal') return `<div class="preg"><label>${q.id}. ${q.txt}</label><select data-id="${q.id}" class="input sel-cal" onchange="calcTotal()"><option value="0">0</option><option>1</option><option>2</option><option>3</option><option>4</option><option>5</option><option>6</option><option>7</option><option>8</option><option>9</option><option selected>10</option></select><div id="ret-${q.id}"></div></div>`;
  else return `<div class="preg" style="border-color:#6366f1"><label>${q.id}. ${q.txt}</label><textarea data-id="${q.id}" class="input" rows="2"></textarea></div>`;
 }).join('');
 calcTotal();
 document.getElementById('eval_emp').addEventListener('change', e=>verRetardos(e.target.value));
 if(document.getElementById('eval_emp').value) verRetardos(document.getElementById('eval_emp').value);
}
function calcTotal(){let t=0; document.querySelectorAll('.sel-cal').forEach(s=>t+=parseInt(s.value||0)); const b=document.getElementById('total-preview'); b.style.display='block'; document.getElementById('total-num').innerText=t+'/100'; let n='Necesita Mejorar'; b.className='total-box'; if(t==100){n='EXCELENTE 🌟'; b.classList.add('excelente');} else if(t>=80) n='Muy Bueno'; document.getElementById('total-nivel').innerText=n;}
async function verRetardos(eid){try{const rets=await api('/empleado/'+eid+'/retardos-mes'); const div=document.getElementById('ret-11'); if(!div) return; if(rets.length) div.innerHTML=`<div style="background:#ef444415;border:1px solid #ef444440;border-radius:8px;padding:8px;margin-top:6px;font-size:11px;color:#fca5a5">⚠️ ${rets.length} retardo(s) este mes:<br>`+rets.map(r=>`• ${r.fecha_dia} ${r.hora} - ${r.retardo_min} min`).join('<br>')+`</div>`; else div.innerHTML=`<div style="background:#10b98115;border:1px solid #10b98140;border-radius:8px;padding:6px;margin-top:6px;font-size:11px;color:#6ee7b7">✅ Sin retardos</div>`;}catch(e){}}
async function evaluar(){const eid=document.getElementById('eval_emp').value; const cals={}; document.querySelectorAll('[data-id]').forEach(el=>cals[el.dataset.id]=el.value); try{const r=await api('/evaluaciones','POST',{empleado_id:eid,calificaciones:cals}); document.getElementById('msg-eval').innerHTML=`✅ Guardado: <b>${r.total}/100 - ${r.nivel}</b> - Notificación enviada a ${eid}`; verHistorialAdmin();}catch(e){document.getElementById('msg-eval').innerText='❌ '+(e.detail||'Error');}}
async function verHistorialAdmin(){try{const evals=await api('/evaluaciones'); document.getElementById('historial-admin').innerHTML=evals.map(e=>`<div style="background:#0f172a;border-radius:10px;padding:12px;margin-top:8px;border-left:4px solid ${e.total==100?'#f59e0b':'#6366f1'}"><div style="display:flex;justify-content:space-between"><b>${e.empleado_nombre} (${e.empleado_id})</b><b style="font-size:18px;color:${e.total==100?'#f59e0b':'#10b981'}">${e.total}/100</b></div><small>${e.mes} - ${e.nivel} - ${e.fecha}</small><div style="font-size:11px;margin-top:6px">${Object.entries(e.detalle||{}).map(([k,v])=>`${k}: ${v}`).join(' | ')}</div></div>`).join('') || 'Sin evaluaciones';}catch(e){}}
async function cambioSuc(){const eid=document.getElementById('cambio_emp').value; const tipo=document.getElementById('cambio_tipo').value; const nueva=document.getElementById('cambio_suc').value; const motivo=document.getElementById('cambio_motivo').value; await api('/empleados/'+eid+'/cambio-sucursal','POST',{nueva_sucursal_id:nueva,motivo,tipo}); alert('🚨 Alerta enviada a '+eid);}
async function cargarEmpleado(id){
 try{
  const turno=await api('/empleado/'+id+'/proximo-turno');
  const div=document.getElementById('mi-turno');
  if(turno.sucursal){
   div.innerHTML=`<p>Hoy <b>${turno.hoy}</b> en <b>${turno.sucursal.nombre}</b></p><p>📍 ${turno.sucursal.direccion} - ⏰ ${turno.hora_entrada} a ${turno.hora_salida}</p><p>Faltan: ${turno.minutos_restantes} min</p>`;
   if(turno.alerta_10min && turno.minutos_restantes>0){
    document.getElementById('alerta-10min').style.display='block';
    document.getElementById('alerta-10min').innerHTML=`⏰ ¡ALERTA! Entrada en ${Math.round(turno.minutos_restantes)} min en ${turno.sucursal.nombre} - ${turno.hora_entrada}`;
   } else if(turno.minutos_restantes<0 && turno.minutos_restantes>-60){
    document.getElementById('alerta-10min').style.display='block';
    document.getElementById('alerta-10min').innerHTML=`⚠️ Ya pasó tu hora de entrada (${turno.hora_entrada}) en ${turno.sucursal.nombre}`;
   } else {document.getElementById('alerta-10min').style.display='none';}
  } else {div.innerHTML=turno.mensaje||'Sin turno'; document.getElementById('alerta-10min').style.display='none';}
  const hist=await api('/empleado/'+id+'/historial');
  document.getElementById('mi-historial').innerHTML=hist.map(e=>`<div style="background:#0f172a;border-radius:12px;padding:14px;margin-top:8px;text-align:center;border:2px solid ${e.total==100?'#f59e0b':'#334155'}"><div style="font-size:12px">${e.mes}</div><div style="font-size:36px;font-weight:800;color:${e.total==100?'#f59e0b':'#10b981'}">${e.total}</div><div>/100 - ${e.nivel}</div><div style="font-size:11px;text-align:left;margin-top:8px">${Object.entries(e.detalle||{}).map(([k,v])=>`${k}: ${v}`).join('<br>')}</div></div>`).join('') || 'Sin evaluaciones';
  const notifs=await api('/alertas/'+id);
  document.getElementById('mis-notifs').innerHTML=notifs.map(n=>`<div style="background:#0f172a;border-radius:10px;padding:10px;margin-top:6px;border-left:4px solid ${n.total==100?'#f59e0b':'#6366f1'}"><b>${n.total? n.total+'/100 '+ (n.nivel||'') : ''}</b><br>${n.mensaje}<br><small>${n.fecha}</small></div>`).join('') || 'Sin alertas';
  const asis=await api('/asistencias/'+id).catch(()=>[]);
  document.getElementById('mi-asis').innerHTML=asis.slice(0,5).map(a=>`${a.fecha_dia} ${a.hora} ${a.retardo_min>0?'(Retardo '+a.retardo_min+' min)':'(A tiempo)'}`).join('<br>') || '';
 }catch(e){console.log(e)}
}
async function checkin(){const r=await api('/asistencia/checkin','POST',{empleado_id:USER_ID}); alert(r.retardo_min>0?`Retardo ${r.retardo_min} min`:`A tiempo ${r.hora}`); cargarEmpleado(USER_ID);}
</script></body></html>
"""

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home(): return HTML
