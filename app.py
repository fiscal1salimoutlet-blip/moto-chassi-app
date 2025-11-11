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
    page_title="Salim Outlet - Controle de Chassi", 
    layout="wide",
    initial_sidebar_state="expanded"  # Sidebar sempre visível
)

# Fuso horário de Brasília
fuso_brasilia = timezone(timedelta(hours=-3))

# Inicializar sessão
if 'chassis' not in st.session_state:
    st.session_state.chassis = []
if 'loja' not in st.session_state:
    st.session_state.loja = "Salim Outlet"  # Nome fixo

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
    # Logo e cabeçalho
    col_logo, col_titulo = st.columns([1, 3])
    
    with col_logo:
        st.image("https://lookaside.fbsbx.com/lookaside/crawler/instagram/salimoutlet/profile_pic.jpg", 
                width=100, caption="Salim Outlet")
    
    with col_titulo:
        st.title("🏍️ Controle de Chassi")
    
    st.divider()
    
    # Sidebar FIXA (não pode ser ocultada)
    with st.sidebar:
        # Logo na sidebar também
        st.image("https://lookaside.fbsbx.com/lookaside/crawler/instagram/salimoutlet/profile_pic.jpg", 
                width=80)
        st.subheader("Salim Outlet")
        
        st.divider()
        
        # Nome da loja FIXO
        st.info("**Loja:** Salim Outlet")
        
        # Contador
        st.metric("Chassis Registrados", len(st.session_state.chassis))
        
        st.divider()
        
        # Botão de nova contagem
        if st.button("🔄 Nova Contagem", use_container_width=True, type="secondary"):
            st.session_state.chassis = []
            st.rerun()
        
        st.divider()
        
        # Botão finalizar (só aparece se tiver chassis)
        if st.session_state.chassis:
            if st.button("✅ FINALIZAR CONTAGEM", use_container_width=True, type="primary"):
                finalizar_automático()

    # Área principal - Formulário de chassis
    st.header("📝 Registrar Chassi")
    
    col_input, col_espaco = st.columns([2, 1])
    
    with col_input:
        chassi = st.text_input(
            "Digite o número do chassi ou escaneie o QR Code:",
            placeholder="Ex: 1, 2, NVESTCASA2025030526...",
            key="chassi_input"
        )
        
        # Botão adicionar
        if st.button("➕ ADICIONAR CHASSI", type="primary", use_container_width=True):
            if chassi:
                registrar_chassi(chassi.strip())
            else:
                st.warning("⚠️ Digite um número de chassi")

    # Lista de chassis registrados
    if st.session_state.chassis:
        st.header("📋 Chassis Registrados")
        
        # DataFrame com formatação
        df = pd.DataFrame(st.session_state.chassis)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Estatísticas rápidas
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total", len(st.session_state.chassis))
        with col2:
            encontrados = len([c for c in st.session_state.chassis if c['status'] == 'Encontrado'])
            st.metric("Encontrados", encontrados)
        with col3:
            nao_encontrados = len([c for c in st.session_state.chassis if c['status'] == 'Não encontrado'])
            st.metric("Não Encontrados", nao_encontrados)
            
        # Aviso sobre finalização
        st.info("💡 **Clique em 'FINALIZAR CONTAGEM' na sidebar para enviar o relatório**")
        
    else:
        # Tela inicial quando não há chassis
        st.info("""
        **Como usar:**
        1. 📝 **Digite o chassi** no campo acima
        2. 🔄 **Clique em ADICIONAR CHASSI**
        3. 📋 **Acompanhe a lista** que vai aparecer aqui
        4. ✅ **Clique em FINALIZAR CONTAGEM** na sidebar quando terminar
        
        **O sistema vai automaticamente:**
        - 📧 Enviar email com o relatório
        - 📊 Gerar arquivo Excel para download
        """)

def registrar_chassi(chassi_numero):
    """Registra um chassi"""
    if not chassi_numero:
        return
        
    # Verificar duplicado
    if any(c['chassi'] == chassi_numero for c in st.session_state.chassis):
        st.warning(f"⚠️ Chassi {chassi_numero} já foi registrado!")
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
                st.success(f"✅ **{chassi_numero}** - {descricao}")
            else:
                registro = {
                    'chassi': chassi_numero,
                    'data': datetime.now(fuso_brasilia).strftime("%d/%m/%Y %H:%M"),
                    'descricao': 'Não encontrado',
                    'modelo': 'N/A',
                    'montador': 'N/A',
                    'status': 'Não encontrado'
                }
                st.error(f"❌ **{chassi_numero}** - Não encontrado na base de dados")
            
            st.session_state.chassis.append(registro)
            cur.close()
            conn.close()
            st.rerun()
            
        except Exception as e:
            st.error(f"Erro na consulta: {str(e)}")
    else:
        st.error("❌ Erro de conexão com o banco de dados")

def finalizar_automático():
    """Finaliza automaticamente - gera Excel e envia email"""
    try:
        # Gerar Excel
        df = pd.DataFrame(st.session_state.chassis)
        filename = f"contagem_salim_outlet_{datetime.now(fuso_brasilia).strftime('%Y%m%d_%H%M')}.xlsx"
        df.to_excel(filename, index=False)
        
        # Enviar email automático
        enviar_email_automatico(filename)
        
        # Mostrar sucesso
        st.balloons()
        st.success("🎉 **CONTAGEM FINALIZADA COM SUCESSO!**")
        
        # Estatísticas finais
        encontrados = len([c for c in st.session_state.chassis if c['status'] == 'Encontrado'])
        nao_encontrados = len([c for c in st.session_state.chassis if c['status'] == 'Não encontrado'])
        
        st.info(f"""
        **Relatório enviado:**
        - 📧 **Email:** Enviado para os destinatários configurados
        - 📊 **Total de chassis:** {len(st.session_state.chassis)}
        - ✅ **Encontrados:** {encontrados}
        - ❌ **Não encontrados:** {nao_encontrados}
        """)
        
        # Botão para baixar Excel
        with open(filename, "rb") as f:
            st.download_button(
                "📥 BAIXAR PLANILHA EXCEL",
                f,
                filename,
                "application/vnd.ms-excel",
                use_container_width=True,
                type="primary"
            )
            
    except Exception as e:
        st.error(f"❌ Erro ao finalizar: {str(e)}")

def enviar_email_automatico(arquivo):
    """Envia email automaticamente para múltiplos destinatários"""
    try:
        # Verificar se as configurações de email existem
        required_secrets = ["EMAIL_FROM", "EMAIL_PASSWORD", "SMTP_SERVER", "SMTP_PORT"]
        missing_secrets = [secret for secret in required_secrets if secret not in st.secrets]
        
        if missing_secrets:
            st.warning(f"⚠️ Email não configurado. Faltando: {', '.join(missing_secrets)}")
            return False
        
        # Lista de emails fixa (configure nas Secrets)
        emails_destino = st.secrets.get("EMAIL_TO", "contagem.salimoutlet@gmail.com").split(",")
        emails_destino = [email.strip() for email in emails_destino if email.strip()]
        
        # Preparar email
        msg = MIMEMultipart()
        msg['From'] = st.secrets["EMAIL_FROM"]
        msg['To'] = ", ".join(emails_destino)
        msg['Subject'] = f"Relatório de Contagem - Salim Outlet - {datetime.now(fuso_brasilia).strftime('%d/%m/%Y')}"
        
        # Estatísticas
        encontrados = len([c for c in st.session_state.chassis if c['status'] == 'Encontrado'])
        nao_encontrados = len([c for c in st.session_state.chassis if c['status'] == 'Não encontrado'])
        
        # Corpo do email
        body = f"""
        RELATÓRIO DE CONTAGEM DE CHASSI - SALIM OUTLET
        
        Data da contagem: {datetime.now(fuso_brasilia).strftime('%d/%m/%Y %H:%M')}
        
        RESUMO:
        • Total de chassis registrados: {len(st.session_state.chassis)}
        • Encontrados na base de dados: {encontrados}
        • Não encontrados: {nao_encontrados}
        
        DETALHES:
        Loja: Salim Outlet
        Responsável: Sistema Automático
        
        O arquivo Excel em anexo contém a lista completa com todos os detalhes.
        
        --
        Sistema de Controle de Chassi
        Salim Outlet
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Anexar arquivo
        with open(arquivo, "rb") as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{arquivo}"')
        msg.attach(part)
        
        # Enviar email
        try:
            server = smtplib.SMTP_SSL(st.secrets["SMTP_SERVER"], int(st.secrets["SMTP_PORT"]))
            server.login(st.secrets["EMAIL_FROM"], st.secrets["EMAIL_PASSWORD"])
            server.send_message(msg)
            server.quit()
        except:
            # Tentar com TLS
            server = smtplib.SMTP(st.secrets["SMTP_SERVER"], int(st.secrets["SMTP_PORT"]))
            server.starttls()
            server.login(st.secrets["EMAIL_FROM"], st.secrets["EMAIL_PASSWORD"])
            server.send_message(msg)
            server.quit()
        
        return True
        
    except Exception as e:
        st.error(f"❌ Erro no envio de email: {str(e)}")
        return False

if __name__ == "__main__":
    main()