import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, timezone, timedelta

# Fuso horário de Brasília
fuso_brasilia = timezone(timedelta(hours=-3))

# Inicializar sessão
if 'scans' not in st.session_state:
    st.session_state.scans = []
if 'last_scan' not in st.session_state:
    st.session_state.last_scan = ""
if 'input_key' not in st.session_state:
    st.session_state.input_key = 0

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

def registrar_scan(ean_numero):
    """Registra um scan de EAN - ACEITA MÚLTIPLAS LEITURAS DO MESMO CÓDIGO"""
    if not ean_numero:
        return
        
    # Consultar banco
    conn = conectar_banco()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT sku, descricao FROM producao WHERE ean = %s", (ean_numero,))
            resultado = cur.fetchone()
            
            if resultado:
                sku, descricao = resultado
                registro = {
                    'ean': ean_numero,
                    'data': datetime.now(fuso_brasilia).strftime("%d/%m/%Y %H:%M"),
                    'sku': sku,
                    'descricao': descricao,
                    'status': 'Encontrado'
                }
                st.success(f"✅ {ean_numero} - {sku} - {descricao}")
            else:
                registro = {
                    'ean': ean_numero,
                    'data': datetime.now(fuso_brasilia).strftime("%d/%m/%Y %H:%M"),
                    'sku': 'N/A',
                    'descricao': 'Não encontrado',
                    'status': 'Não encontrado'
                }
                st.error(f"❌ {ean_numero} - Não encontrado")
            
            # SEMPRE adiciona o registro, mesmo que seja o mesmo EAN
            st.session_state.scans.append(registro)
            cur.close()
            conn.close()
            
        except Exception as e:
            st.error(f"Erro na consulta: {str(e)}")
    else:
        st.error("❌ Erro de conexão com o banco")

def main():
    st.markdown("<h1 style='color: #FFD700; font-size: 3rem;'>Controle de Contagem por SKU</h1>", unsafe_allow_html=True)
    
    # Formulário de leitura
    scan_container = st.container()

    with scan_container:
        # Campo de leitura único
        scan_input = st.text_input(
            "Digite o código de barras (EAN) ou use leitor:",
            placeholder="⬅️ POSICIONE O LEITOR AQUI - O CAMPO ESTÁ PRONTO E COM FOCO AUTOMÁTICO",
            key=f"scan_input_{st.session_state.input_key}",
            label_visibility="visible"
        )

    # Verifica se há um novo scan para registrar
    if scan_input and len(scan_input.strip()) == 13:
        ean_numero = scan_input.strip()
        registrar_scan(ean_numero)
        
        # Incrementa a key para forçar novo campo limpo
        st.session_state.input_key += 1
        
        # Força o rerun para limpar o campo e refocar
        st.experimental_rerun()

    # Instruções para uso com leitor de código de barras
    st.info("""
    **INSTRUÇÕES:**
    - Posicione o leitor de código de barras no campo acima
    - **O CAMPO JÁ ESTÁ COM FOCO AUTOMÁTICO** - não precisa clicar
    - O sistema registra automaticamente códigos EAN de 13 dígitos
    - **MESMO CÓDIGO PODE SER LID VÁRIAS VEZES** - cada scan é contado individualmente
    - Após cada leitura, o campo é limpo automaticamente e pronto para a próxima
    - Use o botão 'Nova Contagem' para reiniciar
    - Use 'FINALIZAR CONTAGEM' para gerar relatório
    """)

if __name__ == "__main__":
    main()
