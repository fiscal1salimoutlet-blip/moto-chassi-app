import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime
import os

st.set_page_config(page_title="Controle de Chassi", layout="wide")

# Inicializar sessão
if 'chassis' not in st.session_state:
    st.session_state.chassis = []
if 'loja' not in st.session_state:
    st.session_state.loja = ""

def conectar_banco():
    """Conecta ao banco Neon"""
    try:
        conn = psycopg2.connect(
            host=st.secrets["NEON_HOST"],
            database=st.secrets["NEON_DATABASE"],
            user=st.secrets["NEON_USER"],
            password=st.secrets["NEON_PASSWORD"],
            port=st.secrets["NEON_PORT"],
            sslmode='require'
        )
        return conn
    except Exception as e:
        st.error(f"Erro de conexão: {str(e)}")
        return None

def main():
    st.title("🏍️ Controle de Chassi de Motos")
    
    # Sidebar
    with st.sidebar:
        st.header("Configurações")
        loja = st.text_input("Nome da Loja", st.session_state.loja)
        if loja != st.session_state.loja:
            st.session_state.loja = loja
            st.rerun()
        
        st.divider()
        st.write(f"**Loja:** {st.session_state.loja}")
        st.write(f"**Chassis registrados:** {len(st.session_state.chassis)}")
        
        if st.button("🔄 Nova Contagem"):
            st.session_state.chassis = []
            st.rerun()
    
    # Se não tem loja definida
    if not st.session_state.loja:
        st.warning("Digite o nome da loja na sidebar para começar")
        return
    
    # Formulário principal
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("Registrar Chassi")
        chassi = st.text_input("Número do Chassi")
        
        if st.button("Adicionar Chassi", type="primary"):
            if chassi:
                registrar_chassi(chassi)
            else:
                st.warning("Digite um número de chassi")
    
    # Lista de chassis
    if st.session_state.chassis:
        st.subheader("Chassis Registrados")
        df = pd.DataFrame(st.session_state.chassis)
        st.dataframe(df, use_container_width=True)
        
        # Botão finalizar
        if st.button("✅ Finalizar Contagem", type="secondary"):
            finalizar_contagem()
    else:
        st.info("Nenhum chassi registrado. Use o formulário acima para adicionar.")

def registrar_chassi(chassi_numero):
    """Registra um chassi"""
    # Verificar duplicado
    if any(c['chassi'] == chassi_numero for c in st.session_state.chassis):
        st.warning("Chassi já registrado!")
        return
    
    # Consultar banco
    conn = conectar_banco()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT descricao, sku, montador FROM producao WHERE chassi = %s", (chassi_numero,))
            resultado = cur.fetchone()
            
            if resultado:
                descricao, modelo, montador = resultado
                registro = {
                    'chassi': chassi_numero,
                    'data': datetime.now().strftime("%d/%m/%Y %H:%M"),
                    'descricao': descricao,
                    'modelo': modelo,
                    'montador': montador,
                    'status': 'Encontrado'
                }
                st.success(f"✅ {chassi_numero} - {descricao}")
            else:
                registro = {
                    'chassi': chassi_numero,
                    'data': datetime.now().strftime("%d/%m/%Y %H:%M"),
                    'descricao': 'Não encontrado',
                    'modelo': 'N/A',
                    'montador': 'N/A',
                    'status': 'Não encontrado'
                }
                st.error(f"❌ {chassi_numero} não encontrado")
            
            st.session_state.chassis.append(registro)
            cur.close()
            conn.close()
            st.rerun()
            
        except Exception as e:
            st.error(f"Erro na consulta: {str(e)}")
    else:
        st.error("Não foi possível conectar ao banco de dados")

def finalizar_contagem():
    """Finaliza a contagem e exporta Excel"""
    try:
        df = pd.DataFrame(st.session_state.chassis)
        filename = f"contagem_{st.session_state.loja}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        df.to_excel(filename, index=False)
        
        st.success("Contagem finalizada com sucesso!")
        
        # Download
        with open(filename, "rb") as f:
            st.download_button(
                "📥 Baixar Excel",
                f,
                filename,
                "application/vnd.ms-excel"
            )
            
    except Exception as e:
        st.error(f"Erro ao gerar Excel: {str(e)}")

if __name__ == "__main__":
    main()