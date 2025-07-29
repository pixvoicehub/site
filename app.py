import os
import base64
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
# Importa a nova SDK do Google Generative AI
# Certifique-se de que seu requirements.txt inclui 'google-genai'
from google.generativeai import GenerativeModel, configure
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env (útil para rodar localmente).
# No Render, as variáveis são configuradas diretamente na plataforma.
load_dotenv()

app = Flask(__name__)

# --- Configuração CORS ---
# Permite requisições de outras origens (ex: Hostinger para o Render).
# Para maior segurança, restrinja a origem para a URL específica da sua Hostinger.
# Ex: CORS(app, resources={r"/generate-narration": {"origins": "https://seu-dominio-hostinger.com"}})
CORS(app)

# --- Configuração da API do Gemini ---
# Obtém a chave da API das variáveis de ambiente. O nome da variável deve ser GEMINI_API_KEY.
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    # Se a chave não for encontrada, exibe um erro crítico.
    # Em produção, um log mais robusto seria ideal.
    print("ERRO CRÍTICO: A chave da API do Gemini (GEMINI_API_KEY) não está definida nas variáveis de ambiente.")
    # A API não funcionará sem a chave.

# Configura a SDK do Google Generative AI com a chave obtida.
# Se a API key for nula, esta linha pode lançar um erro ou simplesmente não configurar.
# É uma boa prática verificar se a chave existe antes de configurar.
if api_key:
    try:
        configure(api_key=api_key)
    except Exception as e:
        print(f"ERRO ao configurar a API do Gemini: {e}")
        # Em um cenário real, você poderia querer parar a execução aqui se a API não puder ser configurada.

# Define o nome do modelo a ser utilizado.
# Para TTS, o modelo pode ser específico. "gemini-2.5-pro-preview-tts" é uma tentativa.
# Você DEVE CONFIRMAR qual modelo exato no Google AI Studio/Vertex AI é o recomendado para TTS
# com a nova SDK 'google-genai'.
model_name = "gemini-2.5-pro-preview-tts"

# --- Rotas da Aplicação ---

@app.route('/')
def index():
    """
    Renderiza o arquivo index.html. Este arquivo é responsável por carregar
    dinamicamente os dados dos locutores a partir de um arquivo JavaScript externo (voices.js).
    """
    # O Render.com serve arquivos HTML do diretório 'templates'.
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """
    Serve arquivos estáticos (CSS, JavaScript, imagens) localizados na pasta 'static'.
    Essencial para carregar o voices.js.
    """
    return send_from_directory('static', filename)


@app.route('/generate-narration', methods=['POST'])
def generate_narration():
    """
    Endpoint para receber requisições POST do frontend.
    Recebe: texto a ser narrado e o ID do locutor.
    Processa: Chama a API do Gemini Text-to-Speech.
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
        # --- Especificação da Voz e Configuração de TTS (NOVA SDK) ---
        # A forma de especificar a voz pode variar. Consulte a documentação oficial
        # do 'google-genai' para TTS. Uma estrutura comum é usar 'generation_config'.
        # Se o modelo específico não suportar TTS ou a voz, isso pode falhar.

        # Tenta a estrutura mais provável com base na documentação mais recente:
        generation_config = {
            "voice": {
                "name": voice_id # Tenta passar o voice_id aqui.
                # Pode ser necessário adicionar 'language_code' dependendo da voz/API.
                # Ex: "language_code": "pt-BR"
            }
        }

        # Instancia o modelo Gemini (ou um modelo TTS específico se houver).
        # O nome do modelo pode precisar de ajuste se "gemini-2.5-pro-preview-tts" não for o correto.
        model = GenerativeModel(model_name)

        # Chama o método para gerar conteúdo, especificando o texto e a configuração de voz.
        response = model.generate_content(
            text=text_to_speak,
            generation_config=generation_config
        )

        # --- Extração do Áudio ---
        # A forma de obter o áudio da resposta pode ter mudado.
        # A documentação do 'google-genai' para TTS sugere acessar `response.audio.get_wav_data()`.
        if hasattr(response, 'audio') and hasattr(response.audio, 'get_wav_data'):
             audio_content = response.audio.get_wav_data()
        else:
             # Se a estrutura da resposta for diferente, precisamos investigar.
             raise ValueError("Formato de áudio inesperado na resposta da API com a nova SDK.")

        # Codifica o conteúdo de áudio em base64 para transmissão via JSON.
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')

        # Retorna o áudio em base64.
        return jsonify({"audioContent": audio_base64})

    except AttributeError as ae:
        # Erro comum se a estrutura da SDK (ex: genai.tts) não for encontrada.
        print(f"ERRO DE ATRIBUTO: {ae}")
        print("Causa provável: Versão incompatível da SDK 'google-genai' ou API mudou.")
        print("Verifique a documentação oficial do 'google-genai' para TTS.")
        return jsonify({"error": f"Erro interno do servidor: Atributo não encontrado no módulo Gemini ({ae})."}), 500
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

    # Para rodar localmente:
    # 1. Certifique-se de ter um arquivo .env com GEMINI_API_KEY=SUA_CHAVE_SECRETA.
    # 2. Crie as pastas 'templates/' e 'static/js/' com os arquivos 'index.html' e 'voices.js'.
    # 3. Execute `python app.py`. A aplicação estará disponível em http://127.0.0.1:5000/.

    app.run(debug=False, port=5000) # Correto: indentado sob o if __name__ == '__main__':