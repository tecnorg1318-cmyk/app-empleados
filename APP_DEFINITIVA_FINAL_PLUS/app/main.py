from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import uuid

app = FastAPI(title="FINAL con ID Consecutivo + Password + Activo")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

sucursales_db = {}
empleados_db = {
    "EMP0001": {"id":"EMP0001","nombre":"Empleado Prueba","puesto":"Botarga","password":"0001","sucursales_ids":["SUC001"],"horario":{"lunes":"SUC001"},"activo":True,"fecha_ingreso":"2025-01-01"}
}
evaluaciones_db = []
asistencias_db = []
alertas_db = []
contador_empleado = 2  # ya existe EMP0001

def get_next_id():
    global contador_empleado
    # Buscar el max actual
    max_num = 0
    for eid in empleados_db.keys():
        try:
            if eid.startswith("EMP"):
                num = int(eid.replace("EMP",""))
                if num > max_num: max_num = num
        except: pass
    next_num = max_num + 1
    return f"EMP{next_num:04d}"  # EMP0001 formato 4 dígitos

PREGUNTAS = [
    {"id":1,"txt":"¿Limpieza de botarga?","tipo":"cal"},
    {"id":2,"txt":"¿Limpieza de ropa?","tipo":"cal"},
    {"id":3,"txt":"¿Limpieza de guantes?","tipo":"cal"},
    {"id":4,"txt":"¿Limpieza de zapatos?","tipo":"cal"},
    {"id":5,"txt":"¿Baile?","tipo":"cal"},
    {"id":6,"txt":"¿Comentario de baile?","tipo":"texto"},
    {"id":7,"txt":"¿Actitud?","tipo":"cal"},
    {"id":8,"txt":"¿Cumple con políticas y valores?","tipo":"cal"},
    {"id":9,"txt":"¿Ambiente positivo?","tipo":"cal"},
    {"id":10,"txt":"¿Disponibilidad para apoyar?","tipo":"cal"},
    {"id":11,"txt":"¿Cumplimiento de horarios?","tipo":"cal"},
    {"id":12,"txt":"¿Área por mejorar?","tipo":"texto"},
]

@app.post("/api/login")
def login(d: dict):
    u=d.get("usuario"); p=d.get("password")
    if u=="admin" and p=="admin123": return {"rol":"admin","usuario":u}
    if u in empleados_db:
        emp=empleados_db[u]
        if not emp.get("activo",True):
            raise HTTPException(403, "Empleado DESACTIVADO. Contacta al admin.")
        if p==emp.get("password",u):
            return {"rol":"empleado","usuario":u,"nombre":emp["nombre"]}
        else:
            raise HTTPException(401, "Contraseña incorrecta")
    raise HTTPException(401, "Usuario no existe")

@app.get("/empleados/next-id")
def next_id(): return {"next_id": get_next_id()}

@app.get("/sucursales")
def ls(): return list(sucursales_db.values())
@app.post("/sucursales")
def cs(s: dict): sucursales_db[s["id"]]=s; return s
@app.get("/empleados")
def le(): return list(empleados_db.values())
@app.post("/empleados")
def ce(e: dict):
    # Si no trae ID, generar
    if not e.get("id") or e["id"]=="":
        e["id"]=get_next_id()
    # Verificar si ya existe
    if e["id"] in empleados_db:
        # generar siguiente
        e["id"]=get_next_id()
    # Si no trae password, usar ID
    if not e.get("password"): e["password"]=e["id"]
    e["activo"]=e.get("activo",True)
    empleados_db[e["id"]]=e
    alertas_db.append({"id":str(uuid.uuid4())[:6],"empleado_id":e["id"],"mensaje":f"Bienvenido {e['nombre']}. Tu usuario: {e['id']} y contraseña: {e['password']}","fecha":datetime.now().strftime("%Y-%m-%d %H:%M"),"tipo":"bienvenida"})
    return e

@app.put("/empleados/{eid}/toggle")
def toggle(eid: str):
    if eid not in empleados_db: raise HTTPException(404)
    empleados_db[eid]["activo"] = not empleados_db[eid].get("activo",True)
    estado = "ACTIVADO" if empleados_db[eid]["activo"] else "DESACTIVADO"
    alertas_db.append({"id":str(uuid.uuid4())[:6],"empleado_id":eid,"mensaje":f"Tu cuenta ha sido {estado} por el admin.","fecha":datetime.now().strftime("%Y-%m-%d %H:%M"),"tipo":"estado"})
    return empleados_db[eid]

@app.put("/empleados/{eid}")
def update_emp(eid: str, data: dict):
    if eid not in empleados_db: raise HTTPException(404)
    empleados_db[eid].update(data)
    return empleados_db[eid]

# Resto endpoints iguales
@app.get("/empleado/{eid}/proximo-turno")
def proximo(eid: str):
    if eid not in empleados_db: return {"error":"no"}
    emp=empleados_db[eid]
    dias=["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]
    hoy=dias[datetime.now().weekday()]
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
    except: return {"error":"hora"}

@app.post("/evaluaciones")
def crear_eval(data: dict):
    hoy=datetime.now()
    eid=data.get("empleado_id")
    if eid not in empleados_db: raise HTTPException(404)
    cals=data.get("calificaciones",{})
    total=0; detalle={}
    for q in PREGUNTAS:
        if q["tipo"]=="cal":
            try: v=int(cals.get(str(q["id"]),0))
            except: v=0
            total+=v; detalle[q["txt"]]=v
    mes=hoy.strftime("%Y-%m")
    if any(ev["empleado_id"]==eid and ev["mes"]==mes for ev in evaluaciones_db):
        raise HTTPException(400, "Ya evaluado este mes")
    nivel="Necesita Mejorar"
    if total==100: nivel="EXCELENTE 🌟"
    elif total>=90: nivel="Muy Bueno"
    elif total>=80: nivel="Bueno"
    elif total>=60: nivel="Regular"
    retardos=[a for a in asistencias_db if a["empleado_id"]==eid and mes in a.get("fecha","") and a["retardo_min"]>0]
    nueva={"id":len(evaluaciones_db)+1,"empleado_id":eid,"empleado_nombre":empleados_db[eid]["nombre"],"fecha":hoy.strftime("%Y-%m-%d %H:%M"),"mes":mes,"calificaciones":cals,"detalle":detalle,"total":total,"nivel":nivel,"retardos":retardos,"comentario_baile":cals.get("6",""),"area_mejorar":cals.get("12","")}
    evaluaciones_db.append(nueva)
    msg=f"📊 EVALUACIÓN {mes}: {total}/100 - {nivel}. "
    if total==100: msg+="¡100/100 EXCELENTE! 🌟"
    else: msg+=f"Te faltaron {100-total} pts. "
    if cals.get("12"): msg+=f"Mejorar: {cals.get('12')}"
    alertas_db.append({"id":str(uuid.uuid4())[:6],"empleado_id":eid,"mensaje":msg,"fecha":hoy.strftime("%Y-%m-%d %H:%M"),"total":total,"nivel":nivel,"tipo":"evaluacion"})
    return nueva

@app.get("/evaluaciones")
def list_ev(): return evaluaciones_db
@app.get("/empleado/{eid}/historial")
def hist(eid: str): return [e for e in evaluaciones_db if e["empleado_id"]==eid]
@app.get("/alertas/{eid}")
def al(eid: str): return [a for a in alertas_db if a["empleado_id"]==eid][::-1]
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
<title>ID Consecutivo + Password + Activo</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Inter',sans-serif}
body{background:#0f172a;color:#e2e8f0}
.hero{background:linear-gradient(135deg,#6366f1,#8b5cf6,#ec4899);padding:30px 20px 60px;text-align:center}
.container{max-width:1250px;margin:-30px auto;padding:20px}
.card{background:#1e293b;border:1px solid #334155;border-radius:16px;padding:18px;margin-top:14px}
.input{width:100%;padding:10px;border-radius:10px;border:1px solid #334155;background:#0f172a;color:white;margin-top:6px}
.btn{padding:10px 16px;border-radius:10px;border:none;background:#6366f1;color:white;font-weight:700;cursor:pointer;margin-top:8px}
.badge{padding:4px 8px;border-radius:6px;font-size:11px;background:#6366f120;color:#a5b4fc;border:1px solid #6366f140;margin:2px;display:inline-block}
.login{background:#1e293b;border:1px solid #334155;border-radius:20px;padding:28px;max-width:380px;margin:80px auto}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:900px){.grid2{grid-template-columns:1fr}}
.preg{background:#0f172a;border:1px solid #334155;border-radius:12px;padding:12px;margin-top:10px}
.total-box{background:linear-gradient(135deg,#10b981,#059669);border-radius:14px;padding:16px;text-align:center;color:white;margin-top:12px}
.total-box.excelente{background:linear-gradient(135deg,#f59e0b,#ef4444)}
.switch{position:relative;display:inline-block;width:50px;height:24px}
.switch input{opacity:0;width:0;height:0}
.slider{position:absolute;cursor:pointer;top:0;left:0;right:0;bottom:0;background:#334155;transition:.4s;border-radius:24px}
.slider:before{position:absolute;content:"";height:18px;width:18px;left:3px;bottom:3px;background:white;transition:.4s;border-radius:50%}
input:checked + .slider{background:#10b981}
input:checked + .slider:before{transform:translateX(26px)}
</style></head><body>
<div id="login" class="login"><h2 style="text-align:center">Control PRO</h2><p style="text-align:center;color:#94a3b8;font-size:11px">ID Consecutivo + Password + Activo/Desactivo</p><input id="u" class="input" placeholder="admin"><input id="p" class="input" type="password" placeholder="admin123"><button class="btn" style="width:100%" onclick="login()">Ingresar</button><p id="msg" style="text-align:center;color:#f87171;font-size:12px;margin-top:8px"></p></div>

<div id="app" style="display:none">
<div class="hero"><h1 style="color:white">Control FINAL - ID Consecutivo + Password</h1><p style="color:white;opacity:.9;font-size:12px">EMP0001, EMP0002... • Contraseña personal • Activar/Desactivar</p></div>
<div class="container">
<div id="admin-area" style="display:none">

<div class="grid2">
<div class="card"><h3>🏢 Sucursal</h3><input id="suc_id" class="input" placeholder="SUC001"><input id="suc_nombre" class="input" placeholder="Nombre"><input id="suc_dir" class="input" placeholder="Dirección"><div style="display:flex;gap:8px"><input id="suc_he" class="input" type="time" value="08:00"><input id="suc_hs" class="input" type="time" value="18:00"></div><button class="btn" style="width:100%" onclick="crearSuc()">+ Crear Sucursal</button><div id="list-suc" style="margin-top:8px"></div></div>

<div class="card"><h3>👤 Crear Empleado con ID Consecutivo + Contraseña</h3>
<div style="background:#6366f115;border:1px solid #6366f140;border-radius:10px;padding:10px;margin-bottom:10px">
<small style="color:#a5b4fc">Próximo ID disponible: <b id="next-id" style="font-size:14px;color:#10b981">Cargando...</b></small><br><small style="color:#94a3b8">Se genera automáticamente EMP0001, EMP0002...</small>
</div>
<div style="display:flex;gap:8px"><input id="emp_id" class="input" placeholder="ID auto" readonly style="background:#1e293b;color:#10b981;font-weight:800"><button class="btn" style="margin-top:6px" onclick="generarID()">🔄 Generar</button></div>
<input id="emp_nombre" class="input" placeholder="Nombre completo *"><input id="emp_puesto" class="input" placeholder="Puesto: Botarga"><input id="emp_pass" class="input" placeholder="Contraseña * (ej: juan123)" type="text">
<div style="background:#0f172a;border-radius:8px;padding:6px;margin-top:6px;max-height:100px;overflow:auto" id="check-suc"></div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px">
<select id="d-lunes" class="input" style="margin-top:0"></select><select id="d-martes" class="input" style="margin-top:0"></select>
<select id="d-miercoles" class="input" style="margin-top:0"></select><select id="d-jueves" class="input" style="margin-top:0"></select>
<select id="d-viernes" class="input" style="margin-top:0"></select><select id="d-sabado" class="input" style="margin-top:0"></select>
<select id="d-domingo" class="input" style="margin-top:0"></select>
</div>
<button class="btn" style="width:100%;background:#10b981;margin-top:10px" onclick="crearEmp()">💾 Guardar Empleado con Contraseña</button>
<p id="msg-emp" style="font-size:12px;margin-top:6px;color:#10b981"></p>
</div>
</div>

<div class="card"><h3>📋 Empleados - Activar / Desactivar + Consecutivo</h3>
<div style="overflow:auto"><table style="width:100%;font-size:12px;border-collapse:collapse"><thead><tr style="color:#94a3b8"><th>ID</th><th>Nombre</th><th>Contraseña</th><th>Sucursales</th><th>Estado</th><th>Acción</th></tr></thead><tbody id="tbody-emp"></tbody></table></div>
</div>

<div class="card"><h3>⭐ Evaluación 100 pts - Notifica automático</h3><select id="eval_emp" class="input"></select><div id="eval_preguntas"></div><div id="total-preview" class="total-box" style="display:none"><div id="total-num" style="font-size:32px;font-weight:800">0</div><div id="total-nivel">/100</div></div><button class="btn" style="width:100%;background:#10b981;margin-top:10px" onclick="evaluar()">Guardar y Notificar</button><p id="msg-eval" style="font-size:12px;margin-top:6px"></p></div>

<div class="card"><h3>📚 Historiales</h3><div id="historial-admin"></div></div>

</div>

<div id="emp-area" style="display:none">
<div class="card"><h3>Mi Turno Hoy</h3><div id="mi-turno"></div><button class="btn" style="background:#f59e0b" onclick="checkin()">Registrar Entrada</button><div id="mi-asis" style="font-size:12px;margin-top:8px"></div></div>
<div class="card"><h3>Mis Notificaciones</h3><div id="mis-notifs"></div></div>
<div class="card"><h3>Mi Historial 100 pts</h3><div id="mi-historial"></div></div>
</div>

</div></div>

<script>
let USER_ID='';
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
async function login(){const u=document.getElementById('u').value; const p=document.getElementById('p').value; try{const d=await api('/api/login','POST',{usuario:u,password:p}); document.getElementById('login').style.display='none'; document.getElementById('app').style.display='block'; USER_ID=u; if(d.rol==='admin'){document.getElementById('admin-area').style.display='block'; cargarTodo();} else{document.getElementById('emp-area').style.display='block'; cargarEmpleado(u);} }catch(e){document.getElementById('msg').innerText=e.detail||'Error';}}
async function generarID(){const d=await api('/empleados/next-id'); document.getElementById('emp_id').value=d.next_id; document.getElementById('next-id').innerText=d.next_id;}
async function crearSuc(){const id=document.getElementById('suc_id').value; const nombre=document.getElementById('suc_nombre').value; const dir=document.getElementById('suc_dir').value; const he=document.getElementById('suc_he').value; const hs=document.getElementById('suc_hs').value; await api('/sucursales','POST',{id,nombre,direccion:dir,hora_entrada:he,hora_salida:hs}); document.getElementById('suc_id').value=''; document.getElementById('suc_nombre').value=''; cargarSucs();}
async function cargarSucs(){const sucs=await api('/sucursales'); document.getElementById('list-suc').innerHTML=sucs.map(s=>`<span style="background:#6366f120;padding:4px 8px;border-radius:6px;font-size:11px;margin:2px;display:inline-block">${s.id} ${s.nombre} (${s.hora_entrada})</span>`).join(' '); document.getElementById('check-suc').innerHTML=sucs.map(s=>`<label style="display:flex;gap:6px;padding:3px"><input type="checkbox" value="${s.id}" class="chk"> ${s.nombre}</label>`).join(''); ['lunes','martes','miercoles','jueves','viernes','sabado','domingo'].forEach(d=>{const sel=document.getElementById('d-'+d); if(sel) sel.innerHTML='<option value="">Libre</option>'+sucs.map(s=>`<option value="${s.id}">${s.nombre}</option>`).join('');});}
async function crearEmp(){const id=document.getElementById('emp_id').value; const nombre=document.getElementById('emp_nombre').value; const puesto=document.getElementById('emp_puesto').value; const pass=document.getElementById('emp_pass').value; if(!nombre||!pass) return alert('Nombre y contraseña obligatorios'); const suc=[...document.querySelectorAll('.chk:checked')].map(c=>c.value); const hor={lunes:document.getElementById('d-lunes').value,martes:document.getElementById('d-martes').value,miercoles:document.getElementById('d-miercoles').value,jueves:document.getElementById('d-jueves').value,viernes:document.getElementById('d-viernes').value,sabado:document.getElementById('d-sabado').value,domingo:document.getElementById('d-domingo').value}; const r=await api('/empleados','POST',{id,nombre,puesto,password:pass,sucursales_ids:suc,horario:hor,activo:true}); document.getElementById('msg-emp').innerText=`✅ ${r.id} - ${r.nombre} creado. Contraseña: ${r.password}`; document.getElementById('emp_nombre').value=''; document.getElementById('emp_pass').value=''; generarID(); cargarEmps();}
async function cargarEmps(){
 const emps=await api('/empleados');
 document.getElementById('tbody-emp').innerHTML=emps.map(e=>`<tr style="border-bottom:1px solid #334155"><td><b style="color:#10b981">${e.id}</b></td><td>${e.nombre}</td><td><code style="background:#0f172a;padding:2px 6px;border-radius:4px">${e.password}</code></td><td>${(e.sucursales_ids||[]).join(',')}</td><td>${e.activo?'<span style="color:#10b981">● Activo</span>':'<span style="color:#ef4444">● Desactivado</span>'}</td><td><label class="switch"><input type="checkbox" ${e.activo?'checked':''} onchange="toggleEmp('${e.id}')"><span class="slider"></span></label></td></tr>`).join('');
 document.getElementById('eval_emp').innerHTML=emps.filter(e=>e.activo).map(e=>`<option value="${e.id}">${e.id} - ${e.nombre}</option>`).join('');
}
async function toggleEmp(id){await api('/empleados/'+id+'/toggle','PUT'); cargarEmps();}
async function cargarTodo(){await cargarSucs(); await generarID(); await cargarEmps(); renderPreguntas(); verHistorialAdmin();}
function renderPreguntas(){
 const div=document.getElementById('eval_preguntas');
 div.innerHTML=PREG.map(q=>{
  if(q.tipo==='cal') return `<div class="preg"><label>${q.id}. ${q.txt}</label><select data-id="${q.id}" class="input sel-cal" onchange="calcTotal()"><option value="0">0</option><option>1</option><option>2</option><option>3</option><option>4</option><option>5</option><option>6</option><option>7</option><option>8</option><option>9</option><option selected>10</option></select></div>`;
  else return `<div class="preg"><label>${q.id}. ${q.txt}</label><textarea data-id="${q.id}" class="input" rows="2"></textarea></div>`;
 }).join('');
 calcTotal();
}
function calcTotal(){let t=0; document.querySelectorAll('.sel-cal').forEach(s=>t+=parseInt(s.value||0)); const b=document.getElementById('total-preview'); b.style.display='block'; document.getElementById('total-num').innerText=t+'/100'; document.getElementById('total-nivel').innerText=t==100?'EXCELENTE 🌟':t+'/100'; b.className='total-box'+(t==100?' excelente':'');}
async function evaluar(){const eid=document.getElementById('eval_emp').value; const cals={}; document.querySelectorAll('[data-id]').forEach(el=>cals[el.dataset.id]=el.value); try{const r=await api('/evaluaciones','POST',{empleado_id:eid,calificaciones:cals}); document.getElementById('msg-eval').innerText=`✅ ${r.total}/100 - ${r.nivel} - Notificado`; verHistorialAdmin();}catch(e){document.getElementById('msg-eval').innerText='❌ '+(e.detail||'Error');}}
async function verHistorialAdmin(){try{const evals=await api('/evaluaciones'); document.getElementById('historial-admin').innerHTML=evals.map(e=>`<div style="background:#0f172a;padding:10px;border-radius:8px;margin-top:6px;border-left:4px solid ${e.total==100?'#f59e0b':'#6366f1'}"><b>${e.empleado_id} ${e.empleado_nombre}</b> - <b>${e.total}/100</b> - ${e.nivel}<br><small>${e.mes} ${e.fecha}</small></div>`).join('') || 'Sin evaluaciones';}catch(e){}}
async function cargarEmpleado(id){
 try{
  const turno=await api('/empleado/'+id+'/proximo-turno');
  document.getElementById('mi-turno').innerHTML=turno.sucursal? `Hoy ${turno.hoy} en ${turno.sucursal.nombre} - ${turno.hora_entrada}` : 'Sin turno';
  const hist=await api('/empleado/'+id+'/historial');
  document.getElementById('mi-historial').innerHTML=hist.map(e=>`<div style="background:#0f172a;padding:12px;border-radius:10px;margin-top:8px;text-align:center"><div style="font-size:32px;font-weight:800;color:${e.total==100?'#f59e0b':'#10b981'}">${e.total}/100</div><div>${e.nivel}</div></div>`).join('') || 'Sin evaluaciones';
  const notifs=await api('/alertas/'+id);
  document.getElementById('mis-notifs').innerHTML=notifs.map(n=>`<div style="background:#0f172a;padding:8px;border-radius:8px;margin-top:6px"><b>${n.total? n.total+'/100':''} ${n.nivel||''}</b><br>${n.mensaje}<br><small>${n.fecha}</small></div>`).join('') || 'Sin alertas';
  const asis=await api('/asistencias/'+id).catch(()=>[]);
  document.getElementById('mi-asis').innerHTML=asis.slice(0,5).map(a=>`${a.fecha_dia} ${a.hora} ${a.retardo_min>0?'(Retardo '+a.retardo_min+')':''}`).join('<br>') || '';
 }catch(e){}
}
async function checkin(){const r=await api('/asistencia/checkin','POST',{empleado_id:USER_ID}); alert(r.retardo_min>0?`Retardo ${r.retardo_min} min`:`A tiempo ${r.hora}`); cargarEmpleado(USER_ID);}
</script></body></html>
"""

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home(): return HTML
