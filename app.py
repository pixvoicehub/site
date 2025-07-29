# app.py - VERSÃO DE TESTE PARA VERIFICAR O DEPLOY
import os
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
CORS(app)

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("ERRO CRÍTICO: A chave da API do Gemini não está definida.")

@app.route('/generate-narration', methods=['POST'])
def generate_narration():
    data = request.get_json()
    text_to_speak = data.get('text')
    voice_id = data.get('voiceId')

    if not text_to_speak or not voice_id:
        return jsonify({"error": "Texto e ID do locutor são obrigatórios."}), 400

    # URL CORRETA DA API
    tts_url = f"https://generativelanguage.googleapis.com/v1beta/models/tts-004:synthesizeSpeech?key={api_key}"

    payload = {
        "text": text_to_speak,
        "voice": {"name": voice_id},
        "audioConfig": {"audioEncoding": "LINEAR16"}
    }

    try:
        response = requests.post(tts_url, json=payload )
        response.raise_for_status()
        response_data = response.json()
        audio_base64 = response_data.get('audioContent')
        if not audio_base64:
            return jsonify({"error": "A resposta da API não continha conteúdo de áudio."}), 500
        return jsonify({"audioContent": audio_base64})

    except requests.exceptions.HTTPError as http_err:
        print(f"Erro HTTP da API: {http_err}" )
        print(f"Resposta da API: {response.text}")
        try:
            # MENSAGEM DE TESTE ADICIONADA AQUI
            error_message = f"ERRO VERSÃO 2: A API do Google falhou. Detalhe: {response.json().get('error', {}).get('message', 'Erro desconhecido')}"
            return jsonify({"error": error_message}), response.status_code
        except requests.exceptions.JSONDecodeError:
            # MENSAGEM DE TESTE ADICIONADA AQUI
            return jsonify({"error": f"ERRO VERSÃO 2: A API do Google retornou um erro não-JSON. Resposta: {response.text}"}), response.status_code
    
    except Exception as e:
        print(f"ERRO GERAL ao gerar narração: {e}")
        return jsonify({"error": f"Ocorreu um erro inesperado no servidor: {e}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
