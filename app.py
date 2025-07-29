import os
import base64
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
# Importa a nova SDK do Google Generative AI e o módulo TTS
# Com a nova SDK, o acesso a text_to_speech e às configs de voz pode ser direto no módulo genai
import google.generativeai as genai
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env (útil para rodar localmente).
load_dotenv()

app = Flask(__name__)

# --- Configuração CORS ---
# Permite requisições de qualquer origem. Em produção, restrinja para seu domínio.
# Ex: CORS(app, resources={r"/generate-narration": {"origins": "https://seu-dominio.com"}} )
CORS(app)

# --- Configuração da API do Gemini ---
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    # Erro crítico se a chave não for encontrada. A aplicação não pode funcionar.
    # Levanta um erro que será capturado pelo Gunicorn/Render e exibido nos logs.
    raise ValueError("ERRO CRÍTICO: A chave da API do Gemini (GEMINI_API_KEY) não está definida.")

try:
    genai.configure(api_key=api_key)
except Exception as e:
    # Levanta um erro em tempo de execução se a configuração falhar.
    raise RuntimeError(f"ERRO ao configurar a API do Gemini: {e}")

# --- Define o Modelo Correto para TTS ---
# Conforme o artigo, tts-004 é o modelo recomendado.
model_tts_name = "tts-004"

# --- Rotas da Aplicação ---

@app.route('/')
def index():
    """Renderiza a página principal."""
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve arquivos estáticos (CSS, JS)."""
    return send_from_directory('static', filename)

@app.route('/generate-narration', methods=['POST'])
def generate_narration():
    """
    Endpoint para gerar narração usando a API de Text-to-Speech do Google.
    """
    data = request.get_json()
    text_to_speak = data.get('text')
    voice_id = data.get('voiceId')  # ID do locutor (ex: 'aoede')

    if not text_to_speak or not voice_id:
        return jsonify({"error": "Texto e ID do locutor são obrigatórios."}), 400

    try:
        # --- GERAÇÃO DE ÁUDIO COM A NOVA SDK (MÉTODO CORRETO) ---
        # 1. Define o modelo de TTS. 'tts-004' é o recomendado para vozes padrão.
        #    O nome do modelo é passado como parâmetro na chamada.

        # 2. Chama a função genai.text_to_speech() com os parâmetros corretos.
        #    O artigo sugere que a voz é passada diretamente como um parâmetro 'voice'.
        response = genai.text_to_speech(
            model=model_tts_name,
            text=text_to_speak,
            voice=voice_id  # O ID da voz é passado diretamente aqui.
        )

        # 3. Extrai o conteúdo de áudio binário da resposta.
        #    O artigo indica que o áudio está em response.audio_content.
        audio_content = response.audio_content

        # 4. Codifica o áudio em base64 para enviar via JSON.
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')

        return jsonify({"audioContent": audio_base64})

    except Exception as e:
        # Captura erros da API do Google ou outros problemas.
        print(f"ERRO ao gerar narração: {e}")
        # Retorna uma mensagem de erro genérica e informativa para o frontend.
        # O detalhe do erro 'e' pode ajudar na depuração.
        return jsonify({"error": f"Ocorreu um erro no servidor ao gerar a narração. Detalhe: {e}"}), 500

# --- Bloco Principal para Execução Local ---
if __name__ == '__main__':
    # Roda o servidor de desenvolvimento do Flask.
    # Para produção no Render, use Gunicorn.
    # A indentação de app.run() sob este bloco é crucial para evitar erros de sintaxe no deploy.
    app.run(debug=True, port=5000)