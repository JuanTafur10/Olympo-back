#!/usr/bin/env python3
"""
Script para iniciar el servidor FastAPI de Olympo
Escucha en 0.0.0.0:8000 para permitir conexiones desde otros dispositivos en la red
"""

import uvicorn
import sys
import os

# Asegurar que el backend esté en el path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("Iniciando servidor Olympo Backend...")
    print("   URL: http://0.0.0.0:8000")
    print("   Documentación: http://localhost:8000/docs")
    
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",  # Escuchar en todas las interfaces
        port=8000,
        reload=True,  # Hot-reload automático al detectar cambios en el código
    )
