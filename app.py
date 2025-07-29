--- START OF FILE app.py.txt ---

import os
import base64
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
# Importa a nova SDK do Google Generative AI e o módulo TTS
from google.generativeai import configure
# Provavelmente não precisamos mais de GenerativeModel para TTS, mas vamos importar para ter acesso a genai.tts
import google.generativeai as genai # Importa o módulo principal para acessar genai.text_to_speech
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env (útil para rodar localmente).
load_dotenv()

app = Flask(__name__)

# --- Configuração CORS ---
CORS(app)

# --- Configuração da API do Gemini ---
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("ERRO CRÍTICO: A chave da API do Gemini (GEMINI_API_KEY) não está definida nas variáveis de ambiente.")
    # Em um cenário de produção, é crucial que a chave exista.
    # Se a chave não existir, as chamadas de API falharão.

# Configura a SDK do Google Generative AI com a chave obtida.
if api_key:
    try:
        configure(api_key=api_key)
    except Exception as e:
        print(f"ERRO ao configurar a API do Gemini: {e}")
        # Se a configuração falhar, as chamadas de API também falharão.

# --- Define o Modelo Correto para TTS ---
# Conforme o artigo, tts-004 é o modelo recomendado.
model_tts_name = "tts-004"

# --- Rotas da Aplicação ---

@app.route('/')
def index():
    """
    Renderiza o arquivo index.html.
    O carregamento dos locutores é feito pelo JavaScript externo (voices.js).
    """
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """
    Serve arquivos estáticos (CSS, JavaScript, imagens) da pasta 'static'.
    Essencial para carregar o voices.js.
    """
    return send_from_directory('static', filename)


@app.route('/generate-narration', methods=['POST'])
def generate_narration():
    """
    Endpoint para receber requisições do frontend e gerar narração (TTS).
    Recebe: texto a ser narrado e o ID do locutor.
    Processa: Chama o método genai.text_to_speech().
    Retorna: O áudio gerado em formato base64.
    """
    data = request.get_json()
    text_to_speak = data.get('text')
    voice_id = data.get('voiceId') # ID do locutor selecionado (ex: 'aoede', 'achird').

    # Validações básicas.
    if not text_to_speak or not voice_id:
        return jsonify({"error": "Texto e ID do locutor são obrigatórios."}), 400

    # Verifica se a chave da API foi configurada corretamente.
    if not api_key:
        return jsonify({"error": "Chave da API do Gemini não configurada."}), 500

    try:
        # --- GERAÇÃO DE ÁUDIO USANDO genai.text_to_speech() ---
        # Conforme o artigo, o método é mais direto e não usa generation_config como antes.
        # Os parâmetros são model, text e voice.

        # A estrutura para especificar a voz pode ser assim:
        # Precisamos verificar se a classe 'Voice' está em 'genai.tts' ou em outro lugar.
        # Vamos assumir que está em genai.tts.Voice por enquanto.
        voice_config_for_tts = genai.tts.Voice(name=voice_id)

        # Tenta chamar o método text_to_speech()
        response = genai.text_to_speech(
            model=model_tts_name, # Usa o nome do modelo TTS correto
            text=text_to_speak,
            voice=voice_config_for_tts # Passa a configuração de voz diretamente
        )

        # --- Extração do Áudio ---
        # O artigo indica que o áudio está em response.audio_content.
        if hasattr(response, 'audio_content') and response.audio_content:
             audio_content = response.audio_content
        else:
             # Se a estrutura da resposta for diferente, precisamos investigar.
             raise ValueError("Formato de áudio inesperado na resposta da API.")

        # Codifica o conteúdo de áudio em base64 para transmissão via JSON.
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')

        # Retorna o áudio em base64.
        return jsonify({"audioContent": audio_base64})

    except AttributeError as ae:
        # Erro comum se a estrutura da SDK (ex: genai.tts.Voice) não for encontrada.
        print(f"ERRO DE ATRIBUTO: {ae}")
        print("Causa provável: Versão incompatível da SDK 'google-genai' ou API mudou.")
        print("Verifique a documentação oficial do 'google-genai' para TTS.")
        return jsonify({"error": f"Erro interno do servidor: Atributo não encontrado na SDK Gemini ({ae})."}), 500
    except ValueError as ve:
        # Erro específico para formato de áudio inesperado.
        print(f"ERRO DE VALOR: {ve}")
        return jsonify({"error": f"Erro ao processar a resposta de áudio: {ve}"}), 500
    except Exception as e:
        # Captura quaisquer outros erros inesperados.
        print(f"ERRO GERAL ao gerar narração: {e}")
        return jsonify({"error": f"Ocorreu um erro ao gerar a narração: {e}"}), 500

# --- Bloco Principal para Execução Local ---
if __name__ == '__main__':
    # Este bloco é executado APENAS quando você roda o script Python diretamente (ex: `python app.py`).
    # Ele NÃO é executado pelo Gunicorn no Render.com.
    # É fundamental que a linha app.run() esteja indentada sob este bloco.

    app.run(debug=False, port=5000)