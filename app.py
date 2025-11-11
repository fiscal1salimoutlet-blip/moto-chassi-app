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
import requests

st.set_page_config(
    page_title="Controle de Chassi", 
    layout="wide",
    initial_sidebar_state="collapsed"
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
    
    # Sidebar
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
    
    if not st.session_state.loja:
        st.warning("📝 Digite o nome da loja na sidebar para começar")
        return
    
    # Formulário
    st.subheader("📦 Registrar Chassi")
    
    chassi = st.text_input(
        "Número do Chassi", 
        placeholder="Digite ou toque para escanear QR Code 📷",
        key="chassi_input",
        label_visibility="collapsed"
    )
    
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

    # Lista de chassis
    if st.session_state.chassis:
        with st.expander(f"📋 Chassis Registrados ({len(st.session_state.chassis)})", expanded=True):
            df = pd.DataFrame(st.session_state.chassis)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Botões de ação
            st.subheader("🚀 Ações")
            
            if st.button("💾 Salvar no Banco", use_container_width=True):
                salvar_contagem_banco()
            
            if st.button("📊 Gerar Excel", use_container_width=True, type="primary"):
                finalizar_contagem()
            
            # Opções de Email
            st.subheader("📧 Enviar Relatório")
            
            col_email1, col_email2 = st.columns(2)
            
            with col_email1:
                if st.button("📧 Enviar Email Automático", use_container_width=True):
                    enviar_email_automatico()
            
            with col_email2:
                # Botão de Email Manual
                link_email = gerar_link_email()
                if link_email:
                    st.markdown(
                        f'<a href="{link_email}" target="_blank">'
                        f'<button style="width: 100%; background-color: #4CAF50; color: white; padding: 10px; border: none; border-radius: 4px; cursor: pointer;">'
                        f'📧 Abrir Email Pré-preenchido</button></a>',
                        unsafe_allow_html=True
                    )
                    
    else:
        st.info("👆 Use o campo acima para adicionar chassis")

def registrar_chassi(chassi_numero):
    """Registra um chassi"""
    if not chassi_numero:
        return
        
    if any(c['chassi'] == chassi_numero for c in st.session_state.chassis):
        st.warning(f"⚠️ {chassi_numero} já registrado!")
        return
    
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

def finalizar_contagem():
    """Gera e disponibiliza o Excel"""
    try:
        df = pd.DataFrame(st.session_state.chassis)
        filename = f"contagem_{st.session_state.loja}_{datetime.now(fuso_brasilia).strftime('%Y%m%d_%H%M')}.xlsx"
        df.to_excel(filename, index=False)
        
        st.success("📊 Excel gerado com sucesso!")
        
        with open(filename, "rb") as f:
            st.download_button(
                "📥 Baixar Excel",
                f,
                filename,
                "application/vnd.ms-excel",
                use_container_width=True
            )
            
    except Exception as e:
        st.error(f"❌ Erro: {str(e)}")

def enviar_email_automatico():
    """Tenta enviar email automaticamente"""
    try:
        df = pd.DataFrame(st.session_state.chassis)
        filename = f"contagem_{st.session_state.loja}_{datetime.now(fuso_brasilia).strftime('%Y%m%d_%H%M')}.xlsx"
        df.to_excel(filename, index=False)
        
        # Verificar configurações
        required_secrets = ["EMAIL_FROM", "EMAIL_PASSWORD", "EMAIL_TO", "SMTP_SERVER", "SMTP_PORT"]
        missing_secrets = [secret for secret in required_secrets if secret not in st.secrets]
        
        if missing_secrets:
            st.warning(f"⚠️ Email não configurado. Faltando: {', '.join(missing_secrets)}")
            st.info("📧 Use o botão 'Abrir Email Pré-preenchido' abaixo")
            return False
        
        # Tentar enviar
        msg = MIMEMultipart()
        msg['From'] = st.secrets["EMAIL_FROM"]
        msg['To'] = st.secrets["EMAIL_TO"]
        msg['Subject'] = f"Relatório Contagem - {st.session_state.loja}"
        
        body = f"""
        Relatório de Contagem de Chassi
        
        Loja: {st.session_state.loja}
        Data: {datetime.now(fuso_brasilia).strftime('%d/%m/%Y %H:%M')}
        Total: {len(st.session_state.chassis)}
        """
        msg.attach(MIMEText(body, 'plain'))
        
        with open(filename, "rb") as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
        msg.attach(part)
        
        # Tentar com SSL
        try:
            server = smtplib.SMTP_SSL(st.secrets["SMTP_SERVER"], int(st.secrets["SMTP_PORT"]))
            server.login(st.secrets["EMAIL_FROM"], st.secrets["EMAIL_PASSWORD"])
            server.send_message(msg)
            server.quit()
            st.success("✅ Email enviado com sucesso!")
            return True
        except:
            # Tentar com TLS
            server = smtplib.SMTP(st.secrets["SMTP_SERVER"], int(st.secrets["SMTP_PORT"]))
            server.starttls()
            server.login(st.secrets["EMAIL_FROM"], st.secrets["EMAIL_PASSWORD"])
            server.send_message(msg)
            server.quit()
            st.success("✅ Email enviado com sucesso!")
            return True
            
    except Exception as e:
        st.error(f"❌ Erro no email automático: {str(e)}")
        st.info("📧 Use o botão 'Abrir Email Pré-preenchido' abaixo")
        return False

def gerar_link_email():
    """Gera link para email pré-preenchido"""
    if not st.session_state.chassis:
        return None
    
    encontrados = len([c for c in st.session_state.chassis if c['status'] == 'Encontrado'])
    nao_encontrados = len([c for c in st.session_state.chassis if c['status'] == 'Não encontrado'])
    
    assunto = f"Relatório Contagem - {st.session_state.loja}"
    corpo = f"""Relatório de Contagem de Chassi

Loja: {st.session_state.loja}
Data: {datetime.now(fuso_brasilia).strftime('%d/%m/%Y %H:%M')}
Total de Chassis: {len(st.session_state.chassis)}
- Encontrados: {encontrados}
- Não encontrados: {nao_encontrados}

O arquivo Excel está em anexo.
"""
    
    assunto_encoded = requests.utils.quote(assunto)
    corpo_encoded = requests.utils.quote(corpo)
    
    return f"mailto:?subject={assunto_encoded}&body={corpo_encoded}"

if __name__ == "__main__":
    main()