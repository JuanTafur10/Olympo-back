import os
import json
import tempfile
from pathlib import Path
from dotenv import load_dotenv
import uuid

try:
    import firebase_admin
    from firebase_admin import credentials, firestore, auth as admin_auth
except ImportError:
    firebase_admin = None
    admin_auth = None
    firestore = None
# Fallback dummy implementations when Firebase Admin is unavailable
if admin_auth is None:
    class _DummyAdminAuth:
        class _User:
            def __init__(self, uid=None):
                # Generar un uid dummy único para evitar conflictos de clave única
                self.uid = uid or f"dummy_{uuid.uuid4().hex}"
        def create_user(self, **kwargs):
            # Return a dummy user object with uid attribute
            return self._User()
        def delete_user(self, uid):
            # No-op en entorno de pruebas/local cuando no existe Admin SDK
            return None
    admin_auth = _DummyAdminAuth()

if firestore is None:
    class _DummyFirestore:
        def client(self):
            return None
    firestore = _DummyFirestore()
# Initialize firestore_db lazily after Firebase Admin setup
firestore_db = None
_RUTA_ENV_RAIZ = Path(__file__).resolve().parents[3] / ".env"
if _RUTA_ENV_RAIZ.exists():
    load_dotenv(dotenv_path=_RUTA_ENV_RAIZ)
else:
    load_dotenv()


# Clase de seguridad para servicios no inicializados
class _UnavailableService:
    def __init__(self, service_name, reason):
        self.name = service_name
        self.reason = reason

    def __getattr__(self, _):
        raise RuntimeError(f"Servicio {self.name} no disponible: {self.reason}")


# Construir firebase_config desde variables de entorno (no hardcodear claves)
firebase_config = {
    "apiKey": os.getenv("FIREBASE_API_KEY", ""),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN", ""),
    "projectId": os.getenv("FIREBASE_PROJECT_ID", ""),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET", ""),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID", ""),
    "appId": os.getenv("FIREBASE_APP_ID", ""),
    "measurementId": os.getenv("FIREBASE_MEASUREMENT_ID", ""),
}


if firestore_db is None:
    firestore_db = _UnavailableService("Firestore", "Firebase Admin no inicializado")


def _get_env_value(*names):
    for name in names:
        value = (os.getenv(name) or "").strip()
        if value:
            return value
    return ""


def _resolver_ruta_credenciales():
    admin_json = _get_env_value("FIREBASE_ADMIN_JSON", "firebase_admin_json")
    cred_path = _get_env_value("FIREBASE_ADMIN_CREDENTIALS", "firebase_admin_credentials")

    # Soporta variable tipo File de GitLab (ruta temporal) o JSON inline.
    if admin_json:
        if os.path.exists(admin_json):
            return admin_json
        try:
            parsed = json.loads(admin_json)
            if isinstance(parsed, dict):
                fd, tmp_path = tempfile.mkstemp(prefix="firebase_admin_", suffix=".json")
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(parsed, f)
                return tmp_path
        except json.JSONDecodeError:
            print("FIREBASE_ADMIN_JSON no es JSON valido; se usara FIREBASE_ADMIN_CREDENTIALS.")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    search_names = []

    if cred_path:
        search_names.append(cred_path)
        base_name = os.path.basename(cred_path)
        if base_name and base_name not in search_names:
            search_names.append(base_name)
        if base_name and not base_name.endswith(".json"):
            json_name = f"{base_name}.json"
            if json_name not in search_names:
                search_names.append(json_name)

    if "firebase_admin_credentials.json" not in search_names:
        search_names.append("firebase_admin_credentials.json")

    candidates = []
    for name in search_names:
        candidates.extend(
            [
                name,
                os.path.join(base_dir, name),
                os.path.join(os.getcwd(), name),
                os.path.join(os.getcwd(), "backend", "app", "core", name),
                os.path.join("/app", "app", "core", name),
            ]
        )

    for path in candidates:
        if os.path.exists(path):
            return path

    return None


# Inicializar Admin SDK de forma segura
# Preferimos que la credencial llegue por una RUTA en la variable FIREBASE_ADMIN_CREDENTIALS
# o como contenido en FIREBASE_ADMIN_JSON (por ejemplo, variable de tipo File en CI)
def _init_firebase_admin():
    try:
        if firebase_admin._apps:
            return

        cred_path = _resolver_ruta_credenciales()
        if not cred_path:
            # No credentials provided: no inicializar Admin SDK
            return

        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)

        # obtener cliente Firestore
        global firestore_db
        firestore_db = firestore.client()
        print("Firebase Admin e Firestore conectados.")

    except Exception as e:
        # No exponer stack traces en prod; loguear y continuar con servicio degradado
        print(f"Error inicializando Admin SDK de Firebase: {e}")


# Ejecutar inicialización al importar (si hay credenciales)
_init_firebase_admin()


# Definir exportaciones públicas
__all__ = ["firestore_db", "admin_auth", "firebase_config"]