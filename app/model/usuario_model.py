import random

import requests

from ..controller.usuario_controller import Usuario_controller
from ..core.firebase_conection import firebase_config

class Usuario:
    
    def __init__(self, name: str, last_name: str, email: str, password):
        self.id_usuario = random.randint(1000, 9999)
        self.name: str = name
        self.last_name: str = last_name
        self.email: str = email
        self.password: str = password

    @staticmethod
    def login(email: str, password: str):
        url = (
            "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
            f"?key={firebase_config['apiKey']}"
        )

        respuesta = requests.post(
            url,
            json={
                "email": email,
                "password": password,
                "returnSecureToken": True,
            },
            timeout=10,
        )

        datos = respuesta.json()

        if respuesta.status_code != 200:
            mensaje_error = datos.get("error", {}).get("message", "LOGIN_FAILED")
            raise ValueError(f"No se pudo iniciar sesión: {mensaje_error}")

        usuario_bd = Usuario_controller.obtener_usuario_por_email(email)

        return {
            "id_token": datos.get("idToken"),
            "refresh_token": datos.get("refreshToken"),
            "local_id": datos.get("localId"),
            "email": datos.get("email", email),
            "usuario": usuario_bd,
        }
