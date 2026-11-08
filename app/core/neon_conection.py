import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

PGHOST = os.getenv('PGHOST')
PGDATABASE = os.getenv('PGDATABASE')
PGUSER = os.getenv('PGUSER')
PGPASSWORD = os.getenv('PGPASSWORD')
PGSSLMODE = os.getenv('PGSSLMODE')
PGCHANNELBINDING = os.getenv('PGCHANNELBINDING')
PGPORT = os.getenv('PGPORT', '5432')

def obtener_conexion():
    return psycopg2.connect(
        database=PGDATABASE,
        user=PGUSER,
        password=PGPASSWORD,
        host=PGHOST,
        port=PGPORT,
        sslmode=PGSSLMODE,
    )