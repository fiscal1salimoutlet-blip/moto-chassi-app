import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

print("🔍 Verificando variáveis de ambiente:")
print(f"Host: {os.getenv('NEON_HOST')}")
print(f"Database: {os.getenv('NEON_DATABASE')}")
print(f"User: {os.getenv('NEON_USER')}")
print(f"Password: {'*' * len(os.getenv('NEON_PASSWORD', ''))}")

try:
    conn = psycopg2.connect(
        host=os.getenv('NEON_HOST'),
        database=os.getenv('NEON_DATABASE'),
        user=os.getenv('NEON_USER'),
        password=os.getenv('NEON_PASSWORD'),
        port=os.getenv('NEON_PORT'),
        sslmode='require'
    )
    print("✅ Conexão bem sucedida!")
    conn.close()
except Exception as e:
    print(f"❌ Erro: {e}")