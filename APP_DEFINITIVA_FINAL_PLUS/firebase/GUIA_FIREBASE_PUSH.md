
# FIREBASE PUSH NOTIFICATIONS - Guia rapida

1. Crea proyecto en console.firebase.google.com
2. Activa Cloud Messaging
3. Descarga google-services.json (Android) y GoogleService-Info.plist (iOS)
4. En backend instala: pip install firebase-admin

Codigo Python produccion:

import firebase_admin
from firebase_admin import credentials, messaging

cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred)

def enviar_push_real(token_fcm, titulo, cuerpo):
    message = messaging.Message(
        notification=messaging.Notification(title=titulo, body=cuerpo),
        token=token_fcm
    )
    messaging.send(message)

Usa esto en:
- revisar_faltas(): ademas de WhatsApp, manda push "Olvidaste marcar ENTRADA"
- gps_ping(): si se aleja, push al empleado "Regresa a sucursal"
- evaluaciones: cuando admin evalua, push "Nueva evaluacion recibida"

En Flutter pubspec.yaml:
firebase_core, firebase_messaging

En main.dart:
await FirebaseMessaging.instance.requestPermission();
String? token = await FirebaseMessaging.instance.getToken();
-> Guarda token en backend: POST /api/empleado/guardar_token {token}
