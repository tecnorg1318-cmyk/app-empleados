
# APP DEFINITIVA FINAL PLUS - TODO INCLUIDO

## ZIP ANTERIOR + ESTO NUEVO:

### 1. Legales (para Play Store)
- legales/AVISO_PRIVACIDAD.md -> Pegalo en tu web y en la app
- legales/TERMINOS_CONDICIONES.md

### 2. Onboarding 3 pasos (obligatorio para Apple)
- onboarding/onboarding_3_pasos.html -> Este diseño usalo en Flutter
- Explica por que pides GPS y que solo es en jornada activa
- Sin esto Apple te rechaza por background location

### 3. Firebase Push
- firebase/GUIA_FIREBASE_PUSH.md -> Como enviar "Se te olvido marcar"
- Backend ya tiene funcion enviar_push_fcm() lista
- En el robot de faltas ya manda WhatsApp + Push

## ESTRUCTURA FINAL COMPLETA:

- app/main.py -> Backend TODO (multi-empresa, GPS 60m, evaluaciones dinamicas, etc)
- admin_panel/evaluaciones.html -> Panel para crear preguntas y evaluar
- onboarding/ -> 3 pantallas para aprobacion Apple
- legales/ -> Textos legales
- firebase/ -> Guia push

## Para publicar en Play Store necesitas:

1. Icono 512x512
2. Capturas onboarding
3. Texto de por que usas ubicacion en segundo plano:
"Esta app usa ubicacion en segundo plano solo durante la jornada laboral activa (entre ENTRADA y SALIDA). Se usa para validar presencia dentro de 60m de sucursal asignada y se apaga automaticamente en descanso/comida. El empleado controla inicio y fin."

4. Link a aviso de privacidad (sube AVISO_PRIVACIDAD.md a tu web)

## WhatsApp Admin: 5212711566031 configurado

## Siguiente paso:
1. Descomprime
2. uvicorn app.main:app --reload
3. Abre /docs y /admin_panel/evaluaciones.html
4. Compila Flutter con la guia
