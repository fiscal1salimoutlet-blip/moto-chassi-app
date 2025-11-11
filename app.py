import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, timezone, timedelta
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

st.set_page_config(
    page_title="Controle de Chassi", 
    layout="wide",
    initial_sidebar_state="collapsed"  # Sidebar fechada no mobile
)

# Fuso horário de Brasília
fuso_brasilia = timezone(timedelta(hours=-3))

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
    st.title("🏍️ Controle de Chassi")
    
    # Sidebar simplificada para mobile
    with st.sidebar:
        st.header("⚙️ Configurações")
        loja = st.text_input("Nome da Loja", st.session_state.loja)
        if loja != st.session_state.loja:
            st.session_state.loja = loja
            st.rerun()
        
        st.divider()
        st.write(f"**Loja:** {st.session_state.loja}")
        st.write(f"**Chassis:** {len(st.session_state.chassis)}")
        
        if st.button("🔄 Nova Contagem", use_container_width=True):
            st.session_state.chassis = []
            st.rerun()
    
    # Se não tem loja definida
    if not st.session_state.loja:
        st.warning("📝 Digite o nome da loja na sidebar para começar")
        return
    
    # 🎯 FORMULÁRIO OTIMIZADO PARA MOBILE
    st.subheader("📦 Registrar Chassi")
    
    # Input com sugestão de câmera para mobile
    chassi = st.text_input(
        "Número do Chassi", 
        placeholder="Digite ou toque para escanear QR Code 📷",
        key="chassi_input",
        label_visibility="collapsed"  # Esconde label para economizar espaço
    )
    
    # Instruções para mobile
    st.caption("📱 **Dica:** Toque no campo acima e selecione 'Scan QR Code' para usar a câmera")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("➕ Adicionar", type="primary", use_container_width=True):
            if chassi:
                registrar_chassi(chassi.strip())
            else:
                st.warning("Digite ou escaneie um chassi")
    
    with col2:
        if st.session_state.chassis:
            if st.button("📊 Ver Lista", use_container_width=True):
                st.rerun()

    # Lista de chassis (oculta por padrão no mobile para economizar espaço)
    if st.session_state.chassis:
        with st.expander(f"📋 Chassis Registrados ({len(st.session_state.chassis)})", expanded=True):
            df = pd.DataFrame(st.session_state.chassis)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Botões de ação
            st.subheader("🚀 Ações")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("💾 Salvar BD", use_container_width=True):
                    salvar_contagem_banco()
                    
            with col2:
                if st.button("📧 Enviar Email", use_container_width=True):
                    finalizar_contagem(enviar_email=True)
                    
            with col3:
                if st.button("✅ Finalizar", type="primary", use_container_width=True):
                    finalizar_contagem(enviar_email=True, salvar_banco=True)
    else:
        st.info("👆 Use o campo acima para adicionar chassis")

def registrar_chassi(chassi_numero):
    """Registra um chassi"""
    if not chassi_numero:
        return
        
    # Verificar duplicado
    if any(c['chassi'] == chassi_numero for c in st.session_state.chassis):
        st.warning(f"⚠️ {chassi_numero} já registrado!")
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
                    'data': datetime.now(fuso_brasilia).strftime("%d/%m/%Y %H:%M"),
                    'descricao': descricao,
                    'modelo': modelo,
                    'montador': montador,
                    'status': 'Encontrado'
                }
                st.success(f"✅ {chassi_numero}")
                st.caption(f"{descricao}")
            else:
                registro = {
                    'chassi': chassi_numero,
                    'data': datetime.now(fuso_brasilia).strftime("%d/%m/%Y %H:%M"),
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
        st.error("❌ Erro de conexão com o banco")

def salvar_contagem_banco():
    """Salva a contagem no banco de dados"""
    try:
        conn = conectar_banco()
        if conn:
            cur = conn.cursor()
            
            # Criar tabela se não existir
            cur.execute("""
                CREATE TABLE IF NOT EXISTS contagens_chassi (
                    id SERIAL PRIMARY KEY,
                    loja_nome VARCHAR(255),
                    chassi VARCHAR(100),
                    data_registro TIMESTAMP,
                    descricao TEXT,
                    modelo VARCHAR(100),
                    montador VARCHAR(100),
                    status VARCHAR(50),
                    data_contagem TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Inserir cada chassi
            for chassi in st.session_state.chassis:
                cur.execute("""
                    INSERT INTO contagens_chassi 
                    (loja_nome, chassi, data_registro, descricao, modelo, montador, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    st.session_state.loja,
                    chassi['chassi'],
                    datetime.now(fuso_brasilia),
                    chassi['descricao'],
                    chassi['modelo'],
                    chassi['montador'],
                    chassi['status']
                ))
            
            conn.commit()
            cur.close()
            conn.close()
            st.success("✅ Contagem salva no banco!")
            
    except Exception as e:
        st.error(f"❌ Erro ao salvar: {str(e)}")

def finalizar_contagem(enviar_email=False, salvar_banco=False):
    """Finaliza a contagem"""
    try:
        df = pd.DataFrame(st.session_state.chassis)
        filename = f"contagem_{st.session_state.loja}_{datetime.now(fuso_brasilia).strftime('%Y%m%d_%H%M')}.xlsx"
        df.to_excel(filename, index=False)
        
        st.success("📊 Contagem finalizada!")
        
        # Download
        with open(filename, "rb") as f:
            st.download_button(
                "📥 Baixar Excel",
                f,
                filename,
                "application/vnd.ms-excel",
                use_container_width=True
            )
        
        if salvar_banco:
            salvar_contagem_banco()
        
        if enviar_email:
            enviar_email_func(filename)
            
    except Exception as e:
        st.error(f"❌ Erro: {str(e)}")

def enviar_email_func(arquivo):
    """Envia o arquivo por email"""
    try:
        if not all(key in st.secrets for key in ["EMAIL_FROM", "EMAIL_PASSWORD", "EMAIL_TO"]):
            st.warning("⚠️ Email não configurado")
            return
            
        msg = MIMEMultipart()
        msg['From'] = st.secrets["EMAIL_FROM"]
        msg['To'] = st.secrets["EMAIL_TO"]
        msg['Subject'] = f"Contagem Chassi - {st.session_state.loja}"
        
        body = f"""
        Contagem: {st.session_state.loja}
        Data: {datetime.now(fuso_brasilia).strftime('%d/%m/%Y %H:%M')}
        Total: {len(st.session_state.chassis)}
        """
        msg.attach(MIMEText(body, 'plain'))
        
        with open(arquivo, "rb") as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename={arquivo}')
        msg.attach(part)
        
        server = smtplib.SMTP(st.secrets["SMTP_SERVER"], int(st.secrets["SMTP_PORT"]))
        server.starttls()
        server.login(st.secrets["EMAIL_FROM"], st.secrets["EMAIL_PASSWORD"])
        server.send_message(msg)
        server.quit()
        
        st.success("✅ Email enviado!")
        
    except Exception as e:
        st.error(f"❌ Erro email: {str(e)}")

if __name__ == "__main__":
    main()