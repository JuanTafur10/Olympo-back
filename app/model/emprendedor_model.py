from .usuario_model import Usuario
from ..controller.usuario_controller import Usuario_controller
from ..core.firebase_conection import admin_auth

class Emprendedor(Usuario):

    def __init__(self, name: str, last_name: str, email: str, password, biografia: str, licencias_certificaciones: list[str], reputacion: int = 0, rol: str = "Emprendedor"):
        super().__init__(name, last_name, email, password)
        self.rol: str = rol
        self.biografia: str = biografia
        self.licencias_certificaciones: list[str] = licencias_certificaciones
        self.reputacion: int = reputacion

    def register(self):
        # 1. Crear usuario en Firebase
        nuevo_usuario = admin_auth.create_user(
            email=self.email,
            password=self.password,
            display_name=f"{self.name} {self.last_name}"
        )
        firebase_uid = nuevo_usuario.uid

        # 2. Insertar en tabla usuarios
        usuario_creado = Usuario_controller.insertar_usuario(
            self.rol.lower(), 
            self.name, 
            self.last_name, 
            self.email,
            firebase_uid
        )
        usuario_id = usuario_creado[0]
        
        # 3. Insertar en tabla emprendedores con datos específicos
        Usuario_controller.insertar_emprendedor(
            usuario_id,
            self.biografia,
            self.licencias_certificaciones
        )