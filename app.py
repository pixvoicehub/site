import os
import base64
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
# A biblioteca 'requests' é usada para fazer a chamada direta à API.
import requests
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env (para testes locais)
load_dotenv()

app = Flask(__name__)

# --- Configuração CORS ---
# Permite requisições de outras origens.
CORS(app)

# --- Configuração da API ---
# Obtém a chave da API das variáveis de ambiente.
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    # Lança um erro e impede a aplicação de iniciar se a chave não for encontrada.
    raise ValueError("ERRO CRÍTICO: A chave da API do Gemini (GEMINI_API_KEY) não está definida nas variáveis de ambiente.")

# --- Rotas da Aplicação ---

@app.route('/')
def index():
    """
    Renderiza a página principal (index.html).
    """
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """
    Serve os arquivos estáticos (como CSS e o voices.js) da pasta 'static'.
    """
    return send_from_directory('static', filename)


@app.route('/generate-narration', methods=['POST'])
def generate_narration():
    """
    Endpoint para receber o texto e o ID da voz, chamar a API do Google
    diretamente via HTTP e retornar o áudio gerado.
    """
    data = request.get_json()
    text_to_speak = data.get('text')
    voice_id = data.get('voiceId')

    # Validação da entrada
    if not text_to_speak or not voice_id:
        return jsonify({"error": "Texto e ID do locutor são obrigatórios."}), 400

    # --- CHAMADA DIRETA À API REST DE TEXT-TO-SPEECH ---
    
    # URL do endpoint da API de TTS do Google AI.
    # Usamos um f-string para incluir a chave da API diretamente na URL.
    tts_url = f"https://generativelanguage.googleapis.com/v1beta/text:synthesizeSpeech?key={api_key}"

    # Corpo da requisição (payload ) no formato JSON que a API espera.
    payload = {
        "text": text_to_speak,
        "voice": {
            "name": voice_id
        },
        "audioConfig": {
            # 'LINEAR16' é o formato para áudio WAV não comprimido.
            "audioEncoding": "LINEAR16" 
        }
    }

    try:
        # Faz a requisição POST para a API do Google com o payload JSON.
        response = requests.post(tts_url, json=payload)

        # Lança uma exceção para respostas de erro (status 4xx ou 5xx).
        # Isso ajuda a capturar problemas como chave de API inválida, voz não encontrada, etc.
        response.raise_for_status()

        # Converte a resposta JSON da API em um dicionário Python.
        response_data = response.json()
        
        # Extrai o conteúdo de áudio, que vem codificado em base64.
        audio_base64 = response_data.get('audioContent')

        if not audio_base64:
            # Caso a resposta seja bem-sucedida mas não contenha o áudio.
            return jsonify({"error": "A resposta da API não continha conteúdo de áudio."}), 500

        # Retorna o áudio em base64 para o frontend.
        return jsonify({"audioContent": audio_base64})

    except requests.exceptions.HTTPError as http_err:
        # Captura erros específicos da API e mostra uma mensagem mais clara.
        print(f"Erro HTTP da API: {http_err}" )
        print(f"Resposta da API: {response.text}")
        # Tenta retornar a mensagem de erro específica da API do Google para o frontend.
        error_message = f"Erro na API do Google: {response.json().get('error', {}).get('message', 'Erro desconhecido')}"
        return jsonify({"error": error_message}), response.status_code
    
    except Exception as e:
        # Captura quaisquer outros erros (ex: problemas de rede).
        print(f"ERRO GERAL ao gerar narração: {e}")
        return jsonify({"error": f"Ocorreu um erro inesperado no servidor: {e}"}), 500

# --- Bloco Principal para Execução Local ---
if __name__ == '__main__':
    # Este bloco só é executado quando você roda 'python app.py' localmente.
    # O Gunicorn no Render não executa esta parte.
    app.run(debug=True, port=5000)
