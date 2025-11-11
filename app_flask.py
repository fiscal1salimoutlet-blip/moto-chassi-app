from flask import Flask, render_template, request, jsonify, send_file
import psycopg2
import pandas as pd
from datetime import datetime
import os
import io

app = Flask(__name__)

# Configurações do banco
DB_CONFIG = {
    'host': os.getenv('NEON_HOST'),
    'database': os.getenv('NEON_DATABASE'),
    'user': os.getenv('NEON_USER'),
    'password': os.getenv('NEON_PASSWORD'),
    'port': os.getenv('NEON_PORT'),
    'sslmode': 'require'
}

# Armazenamento em memória (em produção use Redis)
chassis_registrados = []

def conectar_banco():
    """Conecta ao banco Neon"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Erro de conexão: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/registrar_chassi', methods=['POST'])
def registrar_chassi():
    data = request.json
    chassi = data.get('chassi', '').strip()
    loja = data.get('loja', '').strip()
    
    if not chassi or not loja:
        return jsonify({'error': 'Chassi e loja são obrigatórios'}), 400
    
    # Verificar duplicado
    if any(c['chassi'] == chassi for c in chassis_registrados):
        return jsonify({'error': 'Chassi já registrado'}), 400
    
    # Consultar banco
    conn = conectar_banco()
    if not conn:
        return jsonify({'error': 'Erro de conexão com o banco'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT descricao, sku, montador FROM producao WHERE chassi = %s", (chassi,))
        resultado = cur.fetchone()
        cur.close()
        conn.close()
        
        if resultado:
            descricao, modelo, montador = resultado
            registro = {
                'chassi': chassi,
                'data': datetime.now().strftime("%d/%m/%Y %H:%M"),
                'descricao': descricao,
                'modelo': modelo,
                'montador': montador,
                'status': 'Encontrado',
                'loja': loja
            }
        else:
            registro = {
                'chassi': chassi,
                'data': datetime.now().strftime("%d/%m/%Y %H:%M"),
                'descricao': 'Não encontrado',
                'modelo': 'N/A',
                'montador': 'N/A',
                'status': 'Não encontrado',
                'loja': loja
            }
        
        chassis_registrados.append(registro)
        return jsonify({'success': True, 'registro': registro})
            
    except Exception as e:
        return jsonify({'error': f'Erro na consulta: {str(e)}'}), 500

@app.route('/api/chassis')
def listar_chassis():
    return jsonify({'chassis': chassis_registrados})

@app.route('/api/exportar_excel')
def exportar_excel():
    if not chassis_registrados:
        return jsonify({'error': 'Nenhum chassi registrado'}), 400
    
    # Criar DataFrame
    df = pd.DataFrame(chassis_registrados)
    
    # Gerar Excel em memória
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Contagem')
    
    output.seek(0)
    filename = f"contagem_chassi_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

@app.route('/api/limpar_contagem')
def limpar_contagem():
    chassis_registrados.clear()
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True)