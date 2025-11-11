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

chassis_registrados = []
loja_nome = ""

def conectar_banco():
    return psycopg2.connect(**DB_CONFIG)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/registrar_chassi', methods=['POST'])
def registrar_chassi():
    global chassis_registrados
    
    data = request.json
    chassi = data.get('chassi')
    loja = data.get('loja')
    
    if not chassi or not loja:
        return jsonify({'error': 'Chassi e loja são obrigatórios'}), 400
    
    # Verificar duplicado
    if any(c['chassi'] == chassi for c in chassis_registrados):
        return jsonify({'error': 'Chassi já registrado'}), 400
    
    # Consultar banco
    try:
        conn = conectar_banco()
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
                'status': 'Encontrado'
            }
            chassis_registrados.append(registro)
            return jsonify({'success': True, 'registro': registro})
        else:
            registro = {
                'chassi': chassi,
                'data': datetime.now().strftime("%d/%m/%Y %H:%M"),
                'descricao': 'Não encontrado',
                'modelo': 'N/A',
                'montador': 'N/A',
                'status': 'Não encontrado'
            }
            chassis_registrados.append(registro)
            return jsonify({'success': True, 'registro': registro})
            
    except Exception as e:
        return jsonify({'error': f'Erro no banco: {str(e)}'}), 500

@app.route('/api/exportar_excel')
def exportar_excel():
    global chassis_registrados, loja_nome
    
    if not chassis_registrados:
        return jsonify({'error': 'Nenhum chassi registrado'}), 400
    
    df = pd.DataFrame(chassis_registrados)
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
    global chassis_registrados
    chassis_registrados = []
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True)