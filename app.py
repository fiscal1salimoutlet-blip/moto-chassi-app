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
    page_title="Salim Outlet - Controle de Motos", 
    layout="wide",
    initial_sidebar_state="expanded"  # Sidebar sempre visível
)

# Fuso horário de Brasília
fuso_brasilia = timezone(timedelta(hours=-3))

# Inicializar sessão
if 'chassis' not in st.session_state:
    st.session_state.chassis = []
if 'auto_register' not in st.session_state:
    st.session_state.auto_register = False
if 'last_chassi' not in st.session_state:
    st.session_state.last_chassi = ""

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
    # Cabeçalho com cor AMARELO OURO, CONTORNO PRETO e TAMANHO DOBRADO
    st.markdown(
        """
        <h1 style='
            color: #FFD700; 
            margin-bottom: 20px; 
            font-size: 5rem;
            text-shadow: 
                -2px -2px 0 #000,
                2px -2px 0 #000,
                -2px 2px 0 #000,
                2px 2px 0 #000,
                -3px 0px 0 #000,
                3px 0px 0 #000,
                0px -3px 0 #000,
                0px 3px 0 #000;
            font-weight: bold;
            text-align: center;
        '>Salim Outlet - Controle de Scooters</h1>
        """,
        unsafe_allow_html=True
    )
    
    st.divider()
    
    # Sidebar FIXA
    with st.sidebar:
        # Logo na sidebar (MANTIDO)
        st.image("salimoutlet.jpg", width=100)
        
        st.divider()
        
        # Campo para nome da loja
        operador = st.text_input(
            "🏪 Loja:",
            placeholder="Digite o nome da loja",
            key="operador_input"
        )
        
        # Contador
        st.metric("📋 Chassis Registrados", len(st.session_state.chassis))
        
        st.divider()
        
        # Modo de leitura automática - AGORA VISÍVEL NA SIDEBAR
        st.session_state.auto_register = st.checkbox(
            "🔴 Modo Leitor de Código de Barras", 
            value=st.session_state.auto_register,
            help="Ative para gravação automática ao ler código de barras"
        )
        
        # Botão de nova contagem
        if st.button("🔄 Nova Contagem", use_container_width=True, type="secondary"):
            st.session_state.chassis = []
            st.session_state.last_chassi = ""
            st.rerun()
        
        st.divider()
        
        # Botão finalizar (só aparece se tiver chassis)
        if st.session_state.chassis:
            if st.button("✅ FINALIZAR CONTAGEM", use_container_width=True, type="primary"):
                if operador:
                    finalizar_automático(operador)
                else:
                    st.warning("⚠️ Digite o nome da loja")

    # Área principal - Formulário de chassis
    st.header("📝 Registrar Chassi")
    
    # Container para o campo de chassi
    chassi_container = st.container()
    
    with chassi_container:
        # Campo de chassi com key única para forçar limpeza
        chassi = st.text_input(
            "Digite o número do chassi ou use leitor de código de barras:",
            placeholder="Posicione o leitor aqui...",
            key=f"chassi_input_{len(st.session_state.chassis)}",  # Key dinâmica para forçar limpeza
            label_visibility="visible"
        )
    
    # Verifica se há um novo chassi para registrar (modo automático)
    if (st.session_state.auto_register and 
        chassi and 
        chassi.strip() and 
        chassi != st.session_state.last_chassi):
        
        st.session_state.last_chassi = chassi
        registrar_chassi(chassi.strip())
        # Força o rerun para limpar o campo
        st.rerun()
    
    # Botão adicionar manual (só aparece se o modo automático estiver desativado)
    if not st.session_state.auto_register:
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("➕ ADICIONAR CHASSI", type="primary", use_container_width=True):
                if chassi:
                    registrar_chassi(chassi.strip())
                    # Força o rerun para limpar o campo
                    st.rerun()
                else:
                    st.warning("⚠️ Digite um número de chassi")

    # Instruções para uso com leitor de código de barras
    if st.session_state.auto_register:
        st.success("""
        **🎯 Modo Leitor de Código de Barras ATIVADO**
        - Posicione o leitor no campo acima
        - A gravação será **automática** a cada leitura
        - O campo será **limpo automaticamente** após cada registro
        - Continue lendo os próximos códigos
        """)
    else:
        st.info("""
        **📋 Modo Manual:**
        - Digite o chassi no campo acima
        - Clique em **ADICIONAR CHASSI**
        - Ou **ative o modo leitor de código de barras** na sidebar para leitura automática
        """)

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
        if not st.session_state.get('operador_input'):
            st.warning("👆 **Digite o nome da loja na sidebar para finalizar**")

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
                st.error(f"❌ **{chassi_numero}** - Não encontrado")
            
            st.session_state.chassis.append(registro)
            cur.close()
            conn.close()
            
        except Exception as e:
            st.error(f"Erro na consulta: {str(e)}")
    else:
        st.error("❌ Erro de conexão com o banco")

def finalizar_automático(operador):
    """Finaliza automaticamente - gera Excel e envia email"""
    try:
        # Gerar Excel
        df = pd.DataFrame(st.session_state.chassis)
        filename = f"contagem_salim_outlet_{datetime.now(fuso_brasilia).strftime('%Y%m%d_%H%M')}.xlsx"
        df.to_excel(filename, index=False)
        
        # Enviar email automático
        enviar_email_automatico(filename, operador)
        
        # Mostrar sucesso
        st.balloons()
        st.success("🎉 **CONTAGEM FINALIZADA COM SUCESSO!**")
        
        # Estatísticas finais
        encontrados = len([c for c in st.session_state.chassis if c['status'] == 'Encontrado'])
        nao_encontrados = len([c for c in st.session_state.chassis if c['status'] == 'Não encontrado'])
        
        st.info(f"""
        **📊 Relatório enviado:**
        - **📧 Email:** Enviado automaticamente
        - **🏪 Loja:** {operador}
        - **📦 Total de chassis:** {len(st.session_state.chassis)}
        - **✅ Encontrados:** {encontrados}
        - **❌ Não encontrados:** {nao_encontrados}
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

def enviar_email_automatico(arquivo, operador):
    """Envia email automaticamente"""
    try:
        # Verificar se as configurações de email existem
        required_secrets = ["EMAIL_FROM", "EMAIL_PASSWORD", "SMTP_SERVER", "SMTP_PORT"]
        missing_secrets = [secret for secret in required_secrets if secret not in st.secrets]
        
        if missing_secrets:
            st.warning(f"⚠️ Email não configurado. Faltando: {', '.join(missing_secrets)}")
            return False
        
        # Lista de emails fixa
        emails_destino = st.secrets.get("EMAIL_TO", "contagem.salimoutlet@gmail.com").split(",")
        emails_destino = [email.strip() for email in emails_destino if email.strip()]
        
        # Preparar email - ASSUNTO DINÂMICO COM NOME DA LOJA
        msg = MIMEMultipart()
        msg['From'] = st.secrets["EMAIL_FROM"]
        msg['To'] = ", ".join(emails_destino)
        msg['Subject'] = f"Relatório de Contagem - {operador} - {datetime.now(fuso_brasilia).strftime('%d/%m/%Y')}"
        
        # Estatísticas
        encontrados = len([c for c in st.session_state.chassis if c['status'] == 'Encontrado'])
        nao_encontrados = len([c for c in st.session_state.chassis if c['status'] == 'Não encontrado'])
        
        # Corpo do email
        body = f"""
        RELATÓRIO DE CONTAGEM DE CHASSI - SALIM OUTLET
        
        Data: {datetime.now(fuso_brasilia).strftime('%d/%m/%Y %H:%M')}
        Loja: {operador}
        
        RESUMO:
        • Total de chassis: {len(st.session_state.chassis)}
        • Encontrados: {encontrados}
        • Não encontrados: {nao_encontrados}
        
        O arquivo Excel em anexo contém a lista completa.
        
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