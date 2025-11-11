import streamlit as st
import pandas as pd
from datetime import datetime
import os
from database import Database
from export import ExportManager

# Configuração simples da página
st.set_page_config(page_title="Controle de Chassi", layout="wide")

class ChassiApp:
    def __init__(self):
        self.db = Database()
        self.export_manager = ExportManager()
        self.init_session_state()
    
    def init_session_state(self):
        if 'loja_nome' not in st.session_state:
            st.session_state.loja_nome = ""
        if 'chassis_registrados' not in st.session_state:
            st.session_state.chassis_registrados = []
    
    def run(self):
        # Sidebar
        with st.sidebar:
            st.title("🏍️ Configurações")
            loja_nome = st.text_input("Nome da Loja", value=st.session_state.loja_nome)
            if loja_nome != st.session_state.loja_nome:
                st.session_state.loja_nome = loja_nome
                st.rerun()
            
            st.divider()
            st.write(f"**Loja:** {st.session_state.loja_nome}")
            st.write(f"**Chassis registrados:** {len(st.session_state.chassis_registrados)}")
            
            if st.button("🔄 Nova Contagem"):
                st.session_state.chassis_registrados = []
                st.rerun()
            
            if st.session_state.chassis_registrados:
                if st.button("✅ Finalizar Contagem", type="primary"):
                    self.finalizar_contagem()
        
        # Main content
        if not st.session_state.loja_nome:
            st.title("🏍️ Controle de Chassi de Motos")
            st.warning("⚠️ Defina o nome da loja na barra lateral para começar.")
            return
        
        st.title(f"🏍️ Controle de Chassi - {st.session_state.loja_nome}")
        
        # Formulário de chassi
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.header("📝 Registrar Chassi")
            chassi = st.text_input("Número do Chassi", key="chassi_input")
            
            if st.button("➕ Adicionar Chassi", type="primary"):
                if chassi:
                    self.adicionar_chassi(chassi)
                else:
                    st.warning("Digite um número de chassi")
        
        # Lista de chassis
        if st.session_state.chassis_registrados:
            st.header("📋 Chassis Registrados")
            df = pd.DataFrame(st.session_state.chassis_registrados)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Nenhum chassi registrado. Use o formulário acima para adicionar.")
    
    def adicionar_chassi(self, chassi):
        """Adiciona um chassi à lista"""
        # Verificar duplicado
        if any(c['chassi'] == chassi for c in st.session_state.chassis_registrados):
            st.warning(f"Chassi {chassi} já registrado!")
            return
        
        # Consultar banco
        info_moto = self.db.consultar_chassi(chassi)
        
        if info_moto:
            registro = {
                'chassi': chassi,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'descricao': info_moto.get('descricao', 'N/A'),
                'modelo': info_moto.get('modelo', 'N/A'),
                'montador': info_moto.get('montador', 'N/A'),
                'status': info_moto.get('status', 'N/A')
            }
            st.success(f"✅ Chassi {chassi} registrado!")
        else:
            registro = {
                'chassi': chassi,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'descricao': 'Não encontrado',
                'modelo': 'N/A',
                'montador': 'N/A',
                'status': 'Não encontrado'
            }
            st.error(f"❌ Chassi {chassi} não encontrado!")
        
        st.session_state.chassis_registrados.append(registro)
        st.rerun()
    
    def finalizar_contagem(self):
        """Finaliza a contagem"""
        try:
            filename = self.export_manager.gerar_excel(
                st.session_state.chassis_registrados, 
                st.session_state.loja_nome
            )
            
            st.success("✅ Contagem finalizada! Relatório gerado.")
            
            # Download
            with open(filename, "rb") as file:
                st.download_button(
                    "📥 Baixar Excel",
                    file,
                    filename,
                    "application/vnd.ms-excel"
                )
                
        except Exception as e:
            st.error(f"Erro: {str(e)}")

if __name__ == "__main__":
    app = ChassiApp()
    app.run()