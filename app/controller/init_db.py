"""
Initialize the database in Neon by executing the SQL schema
Run from backend directory: python init_db.py
"""
import os
import psycopg2
from app.core.neon_conection import PGHOST, PGDATABASE, PGUSER, PGPASSWORD, PGPORT, PGSSLMODE

def init_db():
    """Execute the schema SQL file in Neon database"""
    # Get the SQL file path relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sql_path = os.path.join(script_dir, '..', 'sql', 'crear_db.sql')
    sql_path = os.path.normpath(sql_path)
    
    try:
        # Read the SQL file
        with open(sql_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Connect to Neon
        conn = psycopg2.connect(
            host=PGHOST,
            database=PGDATABASE,
            user=PGUSER,
            password=PGPASSWORD,
            port=PGPORT,
            sslmode=PGSSLMODE
        )
        
        cursor = conn.cursor()
        
        # Execute the SQL
        cursor.execute(sql_content)
        conn.commit()
        
        print("✓ Database initialized successfully in Neon!")
        
        cursor.close()
        conn.close()
        
    except FileNotFoundError:
        print(f"✗ Error: SQL file not found at {sql_path}")
    except psycopg2.Error as e:
        print(f"✗ Database error: {e}")
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    init_db()
