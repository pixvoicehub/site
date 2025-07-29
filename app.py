import os
import base64
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# --- Configuração CORS ---
# Ajuste a origem para a URL específica da sua Hostinger se desejar maior segurança.
# Ex: CORS(app, resources={r"/generate-narration": {"origins": "https://seu-dominio.com"}})
CORS(app)

# --- Configuração da API do Gemini ---
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("ERRO: A chave da API do Google Gemini (GOOGLE_API_KEY) não está definida nas variáveis de ambiente.")
    # Em produção, um erro mais robusto seria ideal.

genai.configure(api_key=api_key)

# Modelo de TTS (Text-to-Speech)
model_name = "gemini-2.5-pro-preview-tts"

# --- Rotas da Aplicação ---

@app.route('/')
def index():
    """Renderiza o arquivo index.html.
    Não precisa mais passar os dados das vozes, pois o JS externo os carregará.
    """
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve arquivos estáticos (CSS, JS, imagens) localizados na pasta 'static'.
    Isso é crucial para que o index.html possa carregar o voices.js.
    """
    return send_from_directory('static', filename)


@app.route('/generate-narration', methods=['POST'])
def generate_narration():
    """Recebe o texto e o locutor via POST, chama a API do Gemini e retorna o áudio."""
    data = request.get_json()
    text_to_speak = data.get('text')
    voice_id = data.get('voiceId')

    if not text_to_speak or not voice_id:
        return jsonify({"error": "Texto e ID do locutor são obrigatórios."}), 400

    if not api_key:
        return jsonify({"error": "Chave da API do Gemini não configurada."}), 500

    try:
        voice_selection = genai.Voice(name=voice_id)

        response = genai.generate_content(
            model=model_name,
            contents=[
                genai.Candidate(
                    content=genai.Part(
                        text=text_to_speak,
                        voice=voice_selection
                    )
                )
            ]
        )

        audio_content = response.candidates[0].content.audio.get_wav_data()
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')

        return jsonify({"audioContent": audio_base64})

    except Exception as e:
        print(f"Erro ao gerar narração: {e}")
        return jsonify({"error": f"Ocorreu um erro ao gerar a narração: {e}"}), 500

# --- Bloco Principal para Execução Local ---
if __name__ == '__main__':
    # O Render.com usa um servidor WSGI como Gunicorn. Para rodar localmente:
    # 1. Certifique-se de ter o arquivo .env com GOOGLE_API_KEY=SUA_CHAVE
    # 2. Crie as pastas 'templates' e 'static/js' e coloque os arquivos 'index.html' e 'voices.js' nelas.
    app.run(debug=False, port=5000)