
# APP DEFINITIVA FINAL v6 - TODO COMPLETO

## Que incluye:
- Multi-empresa (Super Admin crea empresas con logo/color)
- GPS ON/OFF 60m + WhatsApp a 5212711566031
- Descanso, Vacaciones, Anti-FakeGPS, Offline, Nomina Excel
- Portal empleado solo lectura + Reporte Clima
- Evaluacion final jornada perifoneo/volanteo (La Gordana)
- NUEVO: Admin crea preguntas dinamicas, evalua empleado con calificacion/comentario/fotos, empleado ve historial

## Endpoints Nuevos Evaluacion Admin:

POST /api/admin/evaluaciones/preguntas
Body: {texto: "Puntualidad", tipo: "calificacion", descripcion: "Llega a tiempo", max_calificacion: 5}
Tipos: calificacion, texto, si_no, foto

GET /api/admin/evaluaciones/preguntas -> Listar
DELETE /api/admin/evaluaciones/preguntas/{id} -> Eliminar
PUT /api/admin/evaluaciones/preguntas/{id} -> Editar

POST /api/admin/evaluaciones/evaluar
Body: {
  empleado_id: 1,
  respuestas: [
    {pregunta_id: 1, calificacion: 5},
    {pregunta_id: 2, texto_respuesta: "Muy bueno"},
    {pregunta_id: 3, foto_url: "https://..."}
  ],
  comentario_general: "Excelente mes",
  fotos_evidencia: ["https://foto1.jpg"]
}

GET /api/empleado/mis_evaluaciones -> Empleado ve su historial (Header X-User: empleado_1)
GET /api/empleado/evaluacion/{eval_id} -> Detalle
GET /api/admin/evaluaciones/reporte -> Admin ve promedios por empleado

## Como probar:
uvicorn app.main:app --reload
Abrir:
- http://localhost:8000/docs -> API Docs
- http://localhost:8000/admin_panel/evaluaciones.html -> Panel Evaluaciones

Headers necesarios:
X-User: superadmin (programador)
X-User: admin_demo (admin empresa)
X-User: empleado_1 (empleado)

## WhatsApp: 5212711566031 ya configurado en .env.example
