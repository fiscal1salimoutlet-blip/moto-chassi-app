import os
import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

class Database:
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        """Conecta ao banco de dados Neon com SSL"""
        try:
            # Obter configurações do arquivo .env
            host = os.getenv('NEON_HOST')
            database = os.getenv('NEON_DATABASE')
            user = os.getenv('NEON_USER')
            password = os.getenv('NEON_PASSWORD')
            port = os.getenv('NEON_PORT')
            
            # Debug: mostrar informações (sem senha)
            st.info(f"🔗 Conectando em: {host}")
            st.info(f"📁 Banco: {database}, Usuário: {user}")
            
            # Configurações do arquivo .env
            self.connection = psycopg2.connect(
                host=host,
                database=database,
                user=user,
                password=password,
                port=port,
                sslmode='require'
            )
            st.success("✅ Conectado ao banco de dados Neon!")
            return True
            
        except Exception as e:
            st.error(f"❌ Erro ao conectar ao banco: {str(e)}")
            
            # Verificar se as variáveis estão carregadas
            st.error("🔍 Verificando variáveis de ambiente:")
            st.error(f"NEON_HOST: {os.getenv('NEON_HOST')}")
            st.error(f"NEON_DATABASE: {os.getenv('NEON_DATABASE')}")
            st.error(f"NEON_USER: {os.getenv('NEON_USER')}")
            st.error(f"NEON_PASSWORD: {'*' * len(os.getenv('NEON_PASSWORD', ''))}")
            st.error(f"NEON_PORT: {os.getenv('NEON_PORT')}")
            
            st.info("💡 Dica: Verifique se o arquivo .env está na mesma pasta que app.py")
            return False
    
    def consultar_chassi(self, chassi):
        """Consulta informações do chassi na base de dados PRODUCAO"""
        try:
            if not self.connection:
                if not self.connect():
                    return None
            
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            
            # ✅ QUERY CORRETA PARA SUA TABELA
            query = """
            SELECT 
                id,
                ean,
                sku,
                descricao,
                chassi,
                montador,
                data_inicio,
                data_fim,
                status
            FROM producao 
            WHERE chassi = %s
            LIMIT 1
            """
            
            cursor.execute(query, (chassi,))
            resultado = cursor.fetchone()
            cursor.close()
            
            if resultado:
                # Converter para dicionário e retornar informações
                info_moto = dict(resultado)
                
                return {
                    'chassi': info_moto.get('chassi', 'N/A'),
                    'descricao': info_moto.get('descricao', 'N/A'),
                    'modelo': info_moto.get('sku', 'N/A'),  # SKU como modelo
                    'montador': info_moto.get('montador', 'N/A'),
                    'status': info_moto.get('status', 'N/A'),
                    'ean': info_moto.get('ean', 'N/A')
                }
            else:
                st.warning(f"⚠️ Chassi {chassi} não encontrado na tabela 'producao'")
                return None
                
        except Exception as e:
            st.error(f"❌ Erro na consulta do chassi {chassi}: {str(e)}")
            return None
    
    def close(self):
        """Fecha a conexão com o banco"""
        if self.connection:
            self.connection.close()