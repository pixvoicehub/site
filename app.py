import os
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS
# Usamos a biblioteca 'requests' para fazer a chamada HTTP direta para a API do Google.
import requests
from dotenv import load_dotenv

# Carrega as variáveis de ambiente de um arquivo .env (útil para rodar localmente).
load_dotenv()

app = Flask(__name__)

# Configura o CORS para permitir que seu frontend (hospedado no Hostinger)
# possa fazer requisições para este backend no Render.
CORS(app)

# --- Configuração da API ---
# Pega a chave da API das variáveis de ambiente da plataforma (Render).
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    # Se a chave não for encontrada, a aplicação não pode funcionar.
    # Lançamos um erro para interromper a execução imediatamente.
    raise ValueError("ERRO CRÍTICO: A chave da API do Gemini (GEMINI_API_KEY) não está definida nas variáveis de ambiente.")

# --- Rota da API ---
# A única rota necessária é a que gera a narração.
# Ela responde apenas a requisições do tipo POST.
@app.route('/generate-narration', methods=['POST'])
def generate_narration():
    """
    Endpoint principal que gera a narração.
    Recebe um JSON com 'text' e 'voiceId'.
    Retorna um JSON com o áudio em base64.
    """
    data = request.get_json()
    text_to_speak = data.get('text')
    voice_id = data.get('voiceId')

    # Validação para garantir que os dados necessários foram enviados.
    if not text_to_speak or not voice_id:
        return jsonify({"error": "Texto e ID do locutor são obrigatórios."}), 400

    # --- URL CORRETA DA API DE TEXT-TO-SPEECH ---
    # O endpoint correto especifica o modelo a ser usado (tts-004).
    tts_url = f"https://generativelanguage.googleapis.com/v1beta/models/tts-004:synthesizeSpeech?key={api_key}"

    # O corpo (payload ) da requisição, formatado como a API do Google espera.
    payload = {
        "text": text_to_speak,
        "voice": {
            "name": voice_id
        },
        "audioConfig": {
            "audioEncoding": "LINEAR16"  # Formato para áudio WAV.
        }
    }

    try:
        # Executa a chamada POST para a API do Google.
        response = requests.post(tts_url, json=payload)

        # Verifica se a resposta da API indica um erro (ex: 400, 403, 404, 500).
        # Se houver erro, o programa pulará para o bloco 'except'.
        response.raise_for_status()

        # Se a chamada foi bem-sucedida, extrai os dados da resposta JSON.
        response_data = response.json()
        audio_base64 = response_data.get('audioContent')

        if not audio_base64:
            # Segurança extra: caso a API retorne sucesso mas sem o conteúdo de áudio.
            return jsonify({"error": "A resposta da API não continha conteúdo de áudio."}), 500

        # Retorna o áudio em base64 para o frontend.
        return jsonify({"audioContent": audio_base64})

    except requests.exceptions.HTTPError as http_err:
        # Bloco para tratar erros específicos da API (HTTP 4xx, 5xx ).
        print(f"Erro HTTP da API: {http_err}" )
        print(f"Resposta da API: {response.text}")
        try:
            # Tenta extrair a mensagem de erro específica do JSON da API.
            error_message = f"Erro na API do Google: {response.json().get('error', {}).get('message', 'Erro desconhecido')}"
            return jsonify({"error": error_message}), response.status_code
        except requests.exceptions.JSONDecodeError:
            # Se a resposta de erro não for um JSON, retorna o texto bruto.
            return jsonify({"error": f"Erro na API do Google: {response.text}"}), response.status_code
    
    except Exception as e:
        # Bloco para capturar qualquer outro erro inesperado (ex: falha de rede).
        print(f"ERRO GERAL ao gerar narração: {e}")
        return jsonify({"error": f"Ocorreu um erro inesperado no servidor: {e}"}), 500

# --- Bloco Principal para Execução Local ---
if __name__ == '__main__':
    # Este bloco permite rodar a aplicação localmente com o comando 'python app.py'.
    # Não é usado pelo Gunicorn no ambiente de produção (Render).
    app.run(debug=True, port=5000)
