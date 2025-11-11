import streamlit as st
import pandas as pd
from datetime import datetime
from database import Database
from export import ExportManager

# Configuração básica
st.set_page_config(page_title="Controle Chassi Motos", layout="wide")

# Inicializar sessão
if 'chassis' not in st.session_state:
    st.session_state.chassis = []
if 'loja' not in st.session_state:
    st.session_state.loja = ""

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
        st.write(f"Chassis: {len(st.session_state.chassis)}")
        
        if st.button("🔄 Nova Contagem"):
            st.session_state.chassis = []
            st.rerun()
    
    # Se não tem loja definida
    if not st.session_state.loja:
        st.warning("Digite o nome da loja na sidebar")
        return
    
    # Formulário principal
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("Registrar Chassi")
        chassi = st.text_input("Número do Chassi")
        
        if st.button("Adicionar", type="primary"):
            if chassi:
                registrar_chassi(chassi)
            else:
                st.warning("Digite um chassi")
    
    # Lista de chassis
    if st.session_state.chassis:
        st.subheader("Chassis Registrados")
        df = pd.DataFrame(st.session_state.chassis)
        st.dataframe(df, use_container_width=True)
        
        # Botão finalizar
        if st.button("✅ Finalizar Contagem", type="secondary"):
            finalizar_contagem()
    else:
        st.info("Nenhum chassi registrado")

def registrar_chassi(chassi_numero):
    """Registra um chassi"""
    db = Database()
    
    # Verificar duplicado
    if any(c['chassi'] == chassi_numero for c in st.session_state.chassis):
        st.warning("Chassi já registrado!")
        return
    
    # Consultar banco
    info = db.consultar_chassi(chassi_numero)
    
    registro = {
        'chassi': chassi_numero,
        'data': datetime.now().strftime("%d/%m/%Y %H:%M"),
        'descricao': info['descricao'] if info else 'Não encontrado',
        'modelo': info['modelo'] if info else 'N/A',
        'montador': info['montador'] if info else 'N/A',
        'status': info['status'] if info else 'Não encontrado'
    }
    
    st.session_state.chassis.append(registro)
    
    if info:
        st.success(f"✅ {chassi_numero} - {info['descricao']}")
    else:
        st.error(f"❌ {chassi_numero} não encontrado")
    
    st.rerun()

def finalizar_contagem():
    """Finaliza a contagem"""
    try:
        export = ExportManager()
        filename = export.gerar_excel(st.session_state.chassis, st.session_state.loja)
        
        st.success("Contagem finalizada!")
        
        # Download
        with open(filename, "rb") as f:
            st.download_button(
                "📥 Baixar Excel",
                f,
                filename,
                "application/vnd.ms-excel"
            )
            
    except Exception as e:
        st.error(f"Erro: {e}")

if __name__ == "__main__":
    main()