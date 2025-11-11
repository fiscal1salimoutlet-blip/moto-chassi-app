import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime
import os

# Configuração MÍNIMA
st.set_page_config(page_title="Controle Chassi", layout="wide")

# Título simples
st.title("🏍️ Controle de Chassi")

# Estado da sessão
if 'chassis' not in st.session_state:
    st.session_state.chassis = []
if 'loja' not in st.session_state:
    st.session_state.loja = ""

# Input da loja
loja = st.text_input("Nome da Loja", st.session_state.loja)
if loja != st.session_state.loja:
    st.session_state.loja = loja

if not st.session_state.loja:
    st.stop()

# Formulário simples
st.subheader("Registrar Chassi")
chassi_input = st.text_input("Número do Chassi")

def conectar_banco():
    """Conecta ao banco Neon usando Secrets"""
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

if st.button("Adicionar Chassi"):
    if chassi_input:
        # Verificar duplicado
        if any(c[0] == chassi_input for c in st.session_state.chassis):
            st.warning("Chassi já existe!")
        else:
            # Consultar banco
            conn = conectar_banco()
            if conn:
                try:
                    cur = conn.cursor()
                    cur.execute("SELECT descricao, sku, montador FROM producao WHERE chassi = %s", (chassi_input,))
                    resultado = cur.fetchone()
                    
                    if resultado:
                        descricao, modelo, montador = resultado
                        st.session_state.chassis.append([
                            chassi_input,
                            datetime.now().strftime("%d/%m/%Y %H:%M"),
                            descricao,
                            modelo,
                            montador,
                            "Encontrado"
                        ])
                        st.success(f"✅ {chassi_input} - {descricao}")
                    else:
                        st.session_state.chassis.append([
                            chassi_input,
                            datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Não encontrado",
                            "N/A",
                            "N/A",
                            "Não encontrado"
                        ])
                        st.error(f"❌ {chassi_input} não encontrado")
                    
                    cur.close()
                    conn.close()
                    
                except Exception as e:
                    st.session_state.chassis.append([
                        chassi_input,
                        datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Erro na consulta",
                        "N/A",
                        "N/A",
                        f"Erro: {str(e)}"
                    ])
                    st.error(f"Erro na consulta: {str(e)}")
            else:
                st.session_state.chassis.append([
                    chassi_input,
                    datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Sem conexão",
                    "N/A",
                    "N/A",
                    "Erro de conexão"
                ])
                st.error("Não foi possível conectar ao banco")
    else:
        st.warning("Digite um chassi")

# Lista de chassis
if st.session_state.chassis:
    st.subheader("Chassis Registrados")
    df = pd.DataFrame(
        st.session_state.chassis,
        columns=["Chassi", "Data", "Descrição", "Modelo", "Montador", "Status"]
    )
    st.dataframe(df, use_container_width=True)
    
    # Botão finalizar
    if st.button("Finalizar Contagem", type="primary"):
        # Gerar Excel simples
        filename = f"contagem_{st.session_state.loja}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        df.to_excel(filename, index=False)
        
        with open(filename, "rb") as f:
            st.download_button(
                "📥 Baixar Excel",
                f,
                filename,
                "application/vnd.ms-excel"
            )
else:
    st.info("Nenhum chassi registrado")

# Sidebar simples
st.sidebar.write(f"**Loja:** {st.session_state.loja}")
st.sidebar.write(f"**Chassis:** {len(st.session_state.chassis)}")

if st.sidebar.button("🔄 Nova Contagem"):
    st.session_state.chassis = []
    st.rerun()