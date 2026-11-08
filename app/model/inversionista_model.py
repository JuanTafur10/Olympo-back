from .usuario_model import Usuario  
from ..controller.usuario_controller import Usuario_controller
from ..core.firebase_conection import admin_auth

class Inversionista(Usuario):
    
    def __init__(self, name: str, last_name: str, email: str, password, biografia: str, intereses_inversion: list[str], reputacion: int = 0, rol: str = "Inversionista"):
        super().__init__(name, last_name, email, password)
        self.rol: str = rol
        self.biografia: str = biografia
        self.intereses_inversion: list[str] = intereses_inversion
        self.reputacion: int = reputacion

    def register(self, monto_disponible: float = 0):
        nuevo_usuario = admin_auth.create_user(
            email=self.email,
            password=self.password,
            display_name=f"{self.name} {self.last_name}"
        )
        firebase_uid = nuevo_usuario.uid

        usuario_creado = Usuario_controller.insertar_usuario(
            self.rol.lower(), 
            self.name, 
            self.last_name, 
            self.email,
            firebase_uid
        )
        usuario_id = usuario_creado[0]
        
        Usuario_controller.insertar_inversionista(
            usuario_id,
            self.biografia,
            self.intereses_inversion,
            monto_disponible
        )
