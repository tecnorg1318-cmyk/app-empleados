from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import uuid

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

sucursales_db = {}
empleados_db = {}
evaluaciones_db = []
asistencias_db = []
alertas_db = []

PREGUNTAS = [
    {"id":1,"txt":"¿Limpieza de botarga?","tipo":"cal","puntos":10},
    {"id":2,"txt":"¿Limpieza de ropa?","tipo":"cal","puntos":10},
    {"id":3,"txt":"¿Limpieza de guantes?","tipo":"cal","puntos":10},
    {"id":4,"txt":"¿Limpieza de zapatos?","tipo":"cal","puntos":10},
    {"id":5,"txt":"¿Baile?","tipo":"cal","puntos":10},
    {"id":6,"txt":"¿Comentario de baile?","tipo":"texto","puntos":0},
    {"id":7,"txt":"¿Actitud?","tipo":"cal","puntos":10},
    {"id":8,"txt":"¿Cumple con políticas y valores de la empresa?","tipo":"cal","puntos":10},
    {"id":9,"txt":"¿Mantiene un ambiente positivo en el trabajo?","tipo":"cal","puntos":10},
    {"id":10,"txt":"¿Disponibilidad para apoyar?","tipo":"cal","puntos":10},
    {"id":11,"txt":"¿Cumplimiento de horarios?","tipo":"cal","puntos":10},
    {"id":12,"txt":"¿Área por mejorar?","tipo":"texto","puntos":0},
]

@app.post("/api/login")
def login(d: dict):
    u=d.get("usuario")
    if u=="admin" and d.get("password")=="admin123": return {"rol":"admin","usuario":u}
    if u in empleados_db: return {"rol":"empleado","usuario":u,"nombre":empleados_db[u]["nombre"]}
    raise HTTPException(401, "No existe")

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
    return e

@app.post("/evaluaciones")
def crear_eval(data: dict):
    hoy=datetime.now()
    # Para prueba, permitir siempre pero avisar si no es 25-31
    # Si quieres bloquear, descomenta:
    # if hoy.day < 25:
    #    raise HTTPException(400, f"Solo del 25 al 31. Hoy es {hoy.day}")
    eid=data.get("empleado_id")
    if eid not in empleados_db: raise HTTPException(404)
    cals=data.get("calificaciones",{})
    # Calcular total de 100 (solo 10 preguntas)
    total=0
    detalle={}
    for q in PREGUNTAS:
        if q["tipo"]=="cal":
            v=cals.get(str(q["id"]),0)
            try: v=int(v)
            except: v=0
            total+=v
            detalle[q["txt"]]=v
    mes=hoy.strftime("%Y-%m")
    # Evitar duplicado mismo mes
    if any(ev["empleado_id"]==eid and ev["mes"]==mes for ev in evaluaciones_db):
        raise HTTPException(400, "Ya evaluado este mes")
    nivel="Necesita Mejorar"
    if total>=90: nivel="EXCELENTE 🌟"
    elif total>=80: nivel="Muy Bueno"
    elif total>=70: nivel="Bueno"
    elif total>=60: nivel="Regular"
    # retardos
    retardos=[a for a in asistencias_db if a["empleado_id"]==eid and mes in a["fecha"] and a["retardo_min"]>0]
    nueva={
        "id":len(evaluaciones_db)+1,
        "empleado_id":eid,
        "empleado_nombre":empleados_db[eid]["nombre"],
        "fecha":hoy.strftime("%Y-%m-%d %H:%M"),
        "mes":mes,
        "calificaciones":cals,
        "detalle_calificaciones":detalle,
        "total":total,  # de 100
        "nivel":nivel,
        "retardos":retardos,
        "comentario_baile":cals.get("6",""),
        "area_mejorar":cals.get("12","")
    }
    evaluaciones_db.append(nueva)
    # NOTIFICACIÓN AUTOMÁTICA AL EMPLEADO
    msg=f"📊 EVALUACIÓN {mes}: Calificación {total}/100 - {nivel}. "
    if total==100: msg+= "¡FELICIDADES! Eres EXCELENTE, 100/100 🌟"
    else: msg+= f"Te faltaron {100-total} puntos para el 100. "
    if retardos: msg+= f"Tuviste {len(retardos)} retardo(s) este mes. "
    if cals.get("12"): msg+= f"Área por mejorar: {cals.get('12')}"
    alertas_db.append({"id":str(uuid.uuid4())[:6],"empleado_id":eid,"mensaje":msg,"fecha":hoy.strftime("%Y-%m-%d %H:%M"),"total":total,"nivel":nivel,"tipo":"evaluacion"})
    return nueva

@app.get("/evaluaciones")
def list_ev(): return evaluaciones_db
@app.get("/empleado/{eid}/historial")
def hist(eid: str): return [e for e in evaluaciones_db if e["empleado_id"]==eid]
@app.get("/alertas/{eid}")
def al(eid: str): return [a for a in alertas_db if a["empleado_id"]==eid][::-1]
@app.get("/empleado/{eid}/retardos-mes")
def ret(eid: str):
    mes=datetime.now().strftime("%Y-%m")
    return [a for a in asistencias_db if a["empleado_id"]==eid and mes in a["fecha"] and a["retardo_min"]>0]
@app.post("/asistencia/checkin")
def checkin(data: dict):
    eid=data.get("empleado_id")
    ahora=datetime.now()
    dias=["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]
    hoy=dias[ahora.weekday()]
    suc_id=empleados_db.get(eid,{}).get("horario",{}).get(hoy,"")
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
<title>Evaluación 100 puntos</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Inter',sans-serif}
body{background:#0f172a;color:#e2e8f0}
.hero{background:linear-gradient(135deg,#6366f1,#8b5cf6,#ec4899);padding:30px 20px 50px;text-align:center}
.container{max-width:1100px;margin:-30px auto;padding:20px}
.card{background:#1e293b;border:1px solid #334155;border-radius:16px;padding:18px;margin-top:14px}
.input,select,textarea{width:100%;padding:10px;border-radius:10px;border:1px solid #334155;background:#0f172a;color:white;margin-top:6px}
.btn{padding:10px 16px;border-radius:10px;border:none;background:#6366f1;color:white;font-weight:700;cursor:pointer;margin-top:8px}
.badge{padding:4px 8px;border-radius:6px;font-size:11px;background:#6366f120;color:#a5b4fc;border:1px solid #6366f140;margin:2px;display:inline-block}
.preg{background:#0f172a;border:1px solid #334155;border-radius:12px;padding:12px;margin-top:10px}
.login{background:#1e293b;border:1px solid #334155;border-radius:20px;padding:28px;max-width:380px;margin:80px auto}
.total-box{background:linear-gradient(135deg,#10b981,#059669);border-radius:16px;padding:20px;text-align:center;color:white;margin-top:16px}
.total-box.excelente{background:linear-gradient(135deg,#f59e0b,#ef4444);animation:pulse 1.5s infinite}
@keyframes pulse{0%{transform:scale(1)}50%{transform:scale(1.03)}100%{transform:scale(1)}}
.notif{background:#6366f115;border:1px solid #6366f140;border-radius:12px;padding:14px;margin-top:10px}
</style></head><body>
<div id="login" class="login"><h2 style="text-align:center">Evaluación 100 pts</h2><p style="text-align:center;color:#94a3b8;font-size:11px">10 preguntas x 10 = 100 Excelente</p><input id="u" class="input" placeholder="admin"><input id="p" class="input" type="password" placeholder="admin123"><button class="btn" style="width:100%" onclick="login()">Ingresar</button><p id="msg" style="text-align:center;color:#f87171;font-size:12px;margin-top:8px"></p></div>

<div id="app" style="display:none">
<div class="hero"><h1 style="color:white">📋 Evaluación Oficial 100 Puntos</h1><p style="color:white;opacity:.9;font-size:13px">10 calificaciones 1-10 = 100 • Preg 6 y 12 no suman • Notificación automática</p></div>
<div class="container">

<div id="admin-area" style="display:none">
<div class="card"><h3>🏢 Sucursales</h3><div style="display:flex;gap:8px"><input id="suc_id" class="input" placeholder="SUC001"><input id="suc_nombre" class="input" placeholder="Nombre"><input id="suc_he" class="input" type="time" value="08:00"></div><button class="btn" onclick="crearSuc()">+ Crear</button><div id="list-suc" style="margin-top:8px"></div></div>
<div class="card"><h3>👤 Empleados</h3><input id="emp_id" class="input" placeholder="EMP001"><input id="emp_nombre" class="input" placeholder="Nombre"><div id="check-suc" style="background:#0f172a;border-radius:8px;padding:6px;margin-top:6px;max-height:100px;overflow:auto"></div><button class="btn" onclick="crearEmp()">+ Crear</button></div>

<div class="card"><h3>⭐ Evaluar (100 pts Máx)</h3>
<p style="font-size:11px;color:#94a3b8">10 preguntas de 10 = 100 puntos. Excelente = 100. Preguntas 6 y 12 son solo texto, no suman.</p>
<select id="eval_emp" class="input"></select>
<div id="eval_preguntas"></div>
<div id="total-preview" class="total-box" style="display:none"><div style="font-size:14px">TOTAL ACTUAL</div><div id="total-num" style="font-size:48px;font-weight:800">0</div><div id="total-nivel" style="font-size:14px">/ 100</div></div>
<button id="btn-eval" class="btn" style="width:100%;padding:14px;background:#10b981;margin-top:12px" onclick="evaluar()">💾 Guardar y Notificar a Empleado</button>
<p id="msg-eval" style="font-size:12px;margin-top:8px"></p>
</div>

<div class="card"><h3>📚 Historiales Completos (Admin ve todo)</h3><div id="historial-admin"></div></div>
</div>

<div id="emp-area" style="display:none">
<div class="card"><h3>🔔 Mis Notificaciones de Evaluación</h3><div id="mis-notifs"></div></div>
<div class="card"><h3>📊 Mi Historial (Solo lectura)</h3><div id="mi-historial"></div></div>
<div class="card"><h3>⏰ Mi Check-In</h3><button class="btn" style="background:#f59e0b" onclick="checkin()">Registrar Entrada</button><div id="mi-asis" style="margin-top:8px;font-size:12px"></div></div>
</div>

</div></div>

<script>
let USER_ID='';
const P=[
 {id:1,txt:"¿Limpieza de botarga?",tipo:"cal"},
 {id:2,txt:"¿Limpieza de ropa?",tipo:"cal"},
 {id:3,txt:"¿Limpieza de guantes?",tipo:"cal"},
 {id:4,txt:"¿Limpieza de zapatos?",tipo:"cal"},
 {id:5,txt:"¿Baile?",tipo:"cal"},
 {id:6,txt:"¿Comentario de baile?",tipo:"texto"},
 {id:7,txt:"¿Actitud?",tipo:"cal"},
 {id:8,txt:"¿Cumple con políticas y valores de la empresa?",tipo:"cal"},
 {id:9,txt:"¿Mantiene un ambiente positivo en el trabajo?",tipo:"cal"},
 {id:10,txt:"¿Disponibilidad para apoyar?",tipo:"cal"},
 {id:11,txt:"¿Cumplimiento de horarios? (muestra retardos)",tipo:"cal"},
 {id:12,txt:"¿Área por mejorar?",tipo:"texto"},
];
async function api(p,m='GET',b=null){const o={method:m,headers:{'Content-Type':'application/json'}}; if(b)o.body=JSON.stringify(b); const r=await fetch(p,o); if(!r.ok){const e=await r.json(); throw e;} return r.json();}
async function login(){const u=document.getElementById('u').value; const p=document.getElementById('p').value; try{const d=await api('/api/login','POST',{usuario:u,password:p}); document.getElementById('login').style.display='none'; document.getElementById('app').style.display='block'; USER_ID=u; if(d.rol==='admin'){document.getElementById('admin-area').style.display='block'; cargarTodo();} else{document.getElementById('emp-area').style.display='block'; cargarEmpleado(u);} }catch(e){document.getElementById('msg').innerText=e.detail||'Error';}}
async function crearSuc(){const id=document.getElementById('suc_id').value; const nombre=document.getElementById('suc_nombre').value; const he=document.getElementById('suc_he').value; await api('/sucursales','POST',{id,nombre,hora_entrada:he}); cargarSucs();}
async function cargarSucs(){const sucs=await api('/sucursales'); document.getElementById('list-suc').innerHTML=sucs.map(s=>`<span class="badge">${s.id} ${s.nombre}</span>`).join(' '); document.getElementById('check-suc').innerHTML=sucs.map(s=>`<label><input type="checkbox" value="${s.id}" class="chk"> ${s.nombre}</label>`).join('');}
async function crearEmp(){const id=document.getElementById('emp_id').value; const nombre=document.getElementById('emp_nombre').value; const suc=[...document.querySelectorAll('.chk:checked')].map(c=>c.value); await api('/empleados','POST',{id,nombre,sucursales_ids:suc,horario:{}}); cargarEmps();}
async function cargarEmps(){const emps=await api('/empleados'); document.getElementById('eval_emp').innerHTML=emps.map(e=>`<option value="${e.id}">${e.id} - ${e.nombre}</option>`).join('');}
async function cargarTodo(){await cargarSucs(); await cargarEmps(); renderPreguntas(); verHistorialAdmin();}
function renderPreguntas(){
 const div=document.getElementById('eval_preguntas');
 div.innerHTML=P.map(q=>{
   if(q.tipo==='cal'){
     return `<div class="preg"><label>${q.id}. ${q.txt} <b style="color:#f59e0b">(0-10 pts)</b></label><select data-id="${q.id}" class="input sel-cal" onchange="calcTotal()"><option value="0">0</option><option>1</option><option>2</option><option>3</option><option>4</option><option>5</option><option>6</option><option>7</option><option>8</option><option>9</option><option selected>10</option></select></div>`;
   } else {
     return `<div class="preg" style="border-color:#6366f1"><label>${q.id}. ${q.txt} <span style="color:#94a3b8">(No suma puntos)</span></label><textarea data-id="${q.id}" class="input" rows="2"></textarea></div>`;
   }
 }).join('');
 calcTotal();
}
function calcTotal(){
 let total=0;
 document.querySelectorAll('.sel-cal').forEach(s=>{total+=parseInt(s.value||0)});
 const box=document.getElementById('total-preview'); box.style.display='block';
 document.getElementById('total-num').innerText=total;
 let nivel='Necesita Mejorar'; box.className='total-box';
 if(total===100){nivel='EXCELENTE 🌟 - 100/100'; box.classList.add('excelente');}
 else if(total>=90) nivel='Muy Bueno';
 else if(total>=70) nivel='Bueno';
 document.getElementById('total-nivel').innerText=nivel+' - '+total+'/100';
}
async function evaluar(){
 const eid=document.getElementById('eval_emp').value;
 const cals={}; document.querySelectorAll('[data-id]').forEach(el=>cals[el.dataset.id]=el.value);
 try{
  const r=await api('/evaluaciones','POST',{empleado_id:eid,calificaciones:cals});
  document.getElementById('msg-eval').innerHTML=`✅ Evaluación guardada: <b>${r.total}/100</b> - ${r.nivel} - Notificación enviada a ${eid}`;
  verHistorialAdmin();
 }catch(e){document.getElementById('msg-eval').innerText='❌ '+(e.detail||'Error');}
}
async function verHistorialAdmin(){
 const evals=await api('/evaluaciones');
 document.getElementById('historial-admin').innerHTML=evals.map(e=>`
   <div style="background:#0f172a;border-radius:10px;padding:12px;margin-top:8px;border-left:4px solid ${e.total==100?'#f59e0b':'#6366f1'}">
     <div style="display:flex;justify-content:space-between"><b>${e.empleado_nombre} (${e.empleado_id})</b><b style="color:${e.total==100?'#f59e0b':'#10b981'};font-size:18px">${e.total}/100</b></div>
     <small>${e.mes} - ${e.nivel} - ${e.fecha}</small>
     <div style="font-size:11px;margin-top:6px">${Object.entries(e.detalle_calificaciones||{}).map(([k,v])=>`${k}: ${v}`).join(' | ')}</div>
     ${e.comentario_baile?`<div style="font-size:11px;margin-top:4px;color:#a5b4fc">Baile: ${e.comentario_baile}</div>`:''}
     ${e.area_mejorar?`<div style="font-size:11px;color:#fca5a5">Mejorar: ${e.area_mejorar}</div>`:''}
   </div>
 `).join('') || 'Sin evaluaciones';
}
async function cargarEmpleado(id){
 const hist=await api('/empleado/'+id+'/historial');
 document.getElementById('mi-historial').innerHTML=hist.map(e=>`
   <div style="background:#0f172a;border-radius:12px;padding:14px;margin-top:10px;text-align:center;border:2px solid ${e.total==100?'#f59e0b':'#334155'}">
     <div style="font-size:12px;color:#94a3b8">${e.mes}</div>
     <div style="font-size:42px;font-weight:800;color:${e.total==100?'#f59e0b':'#10b981'}">${e.total}</div><div style="font-size:14px">/ 100 - ${e.nivel}</div>
     ${e.total==100?'<div style="margin-top:6px;color:#f59e0b">🌟 ¡EXCELENTE! 100/100 🌟</div>':`<div style="font-size:11px;margin-top:6px">Te faltaron ${100-e.total} pts para el 100</div>`}
     <div style="text-align:left;font-size:11px;margin-top:10px">${Object.entries(e.detalle_calificaciones||{}).map(([k,v])=>`${k}: ${v}/10`).join('<br>')}</div>
   </div>
 `).join('') || 'Sin evaluaciones';
 const notifs=await api('/alertas/'+id);
 document.getElementById('mis-notifs').innerHTML=notifs.map(n=>`<div class="notif" style="border-left:4px solid ${n.total==100?'#f59e0b':'#6366f1'}"><b>${n.total||''}/100 ${n.nivel||''}</b><br>${n.mensaje}<br><small>${n.fecha}</small></div>`).join('') || 'Sin notificaciones';
 const asis=await api('/asistencias/'+id).catch(()=>[]);
 document.getElementById('mi-asis').innerHTML=(await api('/asistencias/'+id).catch(()=>[])).slice(0,5).map(a=>`${a.fecha_dia} ${a.hora} ${a.retardo_min>0?'(Retardo '+a.retardo_min+' min)':'(A tiempo)'}`).join('<br>') || '';
}
async function checkin(){const r=await api('/asistencia/checkin','POST',{empleado_id:USER_ID}); alert(r.retardo_min>0?`Retardo ${r.retardo_min} min`:`A tiempo ${r.hora}`); cargarEmpleado(USER_ID);}
</script></body></html>
"""

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home(): return HTML
