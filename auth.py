import psycopg2
from dotenv import load_dotenv
import os


def conecta_supabase():
    load_dotenv()
    conn_info = {
            'database': os.getenv('DB_SUPABASE'),
            'user': os.getenv('USER_SUPABASE'),
            'password': os.getenv('PSW_SUPABASE'),
            'host': os.getenv('HOST_SUPABASE'),
            'port': int(os.getenv('PORT_SUPABASE'))
        }
    conn = psycopg2.connect(**conn_info)
    return conn
