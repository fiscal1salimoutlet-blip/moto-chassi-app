import os
import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        self.conn = None
        self.connect()
    
    def connect(self):
        try:
            self.conn = psycopg2.connect(
                host=os.getenv('NEON_HOST'),
                database=os.getenv('NEON_DATABASE'),
                user=os.getenv('NEON_USER'),
                password=os.getenv('NEON_PASSWORD'),
                port=os.getenv('NEON_PORT'),
                sslmode='require'
            )
            return True
        except Exception as e:
            st.error(f"Erro DB: {e}")
            return False
    
    def consultar_chassi(self, chassi):
        try:
            if not self.conn:
                return None
                
            cur = self.conn.cursor(cursor_factory=RealDictCursor)
            query = "SELECT * FROM producao WHERE chassi = %s LIMIT 1"
            cur.execute(query, (chassi,))
            result = cur.fetchone()
            cur.close()
            
            if result:
                return {
                    'chassi': result.get('chassi'),
                    'descricao': result.get('descricao'),
                    'modelo': result.get('sku'),
                    'montador': result.get('montador'),
                    'status': result.get('status')
                }
            return None
            
        except Exception as e:
            st.error(f"Erro consulta: {e}")
            return None
    
    def close(self):
        if self.conn:
            self.conn.close()