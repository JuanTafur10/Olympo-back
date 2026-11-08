from datetime import date

from ..controller.proyecto_controller import Proyecto_controller

class Proyecto:
    
    def __init__(self, propietario_id, titulo: str, descripcion: str, presupuesto: float, estado: str):
        self.propietario_id = propietario_id
        self.titulo: str = titulo
        self.descripcion: str = descripcion
        self.presupuesto: float = presupuesto
        self.estado: str = self.validar_estado(estado)
        self.fecha_publicacion: str = date.today()

    @staticmethod
    def validar_estado(estado: str) -> str:
        estado_normalizado = str(estado).strip().lower()
        if estado_normalizado not in {"activo", "inactivo"}:
            raise ValueError("Estado invalido. Usa 'activo' o 'inactivo'.")
        return estado_normalizado

    def registrar_proyecto(self):
        nuevo_proyecto = Proyecto_controller.insertar_proyecto(self.propietario_id, self.titulo, self.descripcion, self.presupuesto, self.estado, self.fecha_publicacion)
        print(nuevo_proyecto)