import os
import base64
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import google.generativeai as genai
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env (se existir).
# Isso é útil para rodar localmente. No Render, as variáveis são configuradas diretamente na plataforma.
load_dotenv()

app = Flask(__name__)

# --- Configuração CORS ---
# Permite requisições de outras origens (ex: sua Hostinger para o Render).
# Para um ambiente de produção mais seguro, restrinja a origem para a URL específica da sua Hostinger.
# Ex: CORS(app, resources={r"/generate-narration": {"origins": "https://lightskyblue-goldfish-583784.hostingersite.com"}})
CORS(app)

# --- Configuração da API do Gemini ---
# Obtém a chave da API das variáveis de ambiente. O nome da variável deve ser GEMINI_API_KEY.
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    # Se a chave não for encontrada, exibe um erro crítico.
    # Em produção, seria melhor usar um sistema de logging mais robusto.
    print("ERRO CRÍTICO: A chave da API do Gemini (GEMINI_API_KEY) não está definida nas variáveis de ambiente.")
    # O script continuará, mas chamadas à API falharão.

# Configura a SDK do Google Generative AI com a chave obtida.
genai.configure(api_key=api_key)

# Define o nome do modelo de Text-to-Speech a ser utilizado.
# "gemini-2.5-pro-preview-tts" é uma versão preview que pode ter recursos TTS.
model_name = "gemini-2.5-pro-preview-tts"

# --- Rotas da Aplicação ---

@app.route('/')
def index():
    """
    Renderiza o arquivo index.html.
    Este arquivo HTML é responsável por carregar dinamicamente os dados dos locutores
    através de um arquivo JavaScript externo (voices.js).
    """
    # O Render.com serve arquivos HTML do diretório 'templates' por padrão.
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """
    Serve arquivos estáticos como CSS, JavaScript e imagens.
    Esses arquivos devem estar localizados na pasta 'static' na raiz do seu projeto.
    Esta rota é essencial para que o index.html possa carregar o voices.js.
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
    voice_id = data.get('voiceId') # Recebe o ID do locutor selecionado (ex: 'aoede', 'achird').

    # Validações básicas para garantir que os dados necessários foram enviados.
    if not text_to_speak or not voice_id:
        return jsonify({"error": "Texto e ID do locutor são obrigatórios."}), 400

    # Verifica novamente se a chave da API está disponível.
    if not api_key:
        return jsonify({"error": "Chave da API do Gemini não configurada."}), 500

    try:
        # --- Especificação da Voz para o Gemini TTS ---
        # A forma de especificar a voz mudou. Agora usamos genai.tts.VoiceConfig.
        # O 'name' deve corresponder a um ID de voz válido.
        voice_config = genai.tts.VoiceConfig(name=voice_id)

        # Chama o modelo Gemini para gerar o conteúdo de áudio.
        response = genai.generate_content(
            model=model_name,
            contents=[
                genai.Candidate(
                    content=genai.Part(
                        text=text_to_speak,
                        # Especifica a configuração de TTS, incluindo a voz selecionada.
                        tts_config=genai.TtsConfig(voice=voice_config)
                    )
                )
            ]
        )

        # Extrai os dados de áudio da resposta.
        # A API do Gemini TTS retorna o áudio em formato WAV.
        audio_content = response.candidates[0].content.audio.get_wav_data()

        # Codifica o conteúdo de áudio em base64 para facilitar a transmissão via JSON.
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')

        # Retorna o áudio codificado em base64 junto com um status de sucesso.
        return jsonify({"audioContent": audio_base64})

    except AttributeError as ae:
        # Captura especificamente o erro quando um atributo esperado não é encontrado.
        # Isso é comum se a versão da SDK for antiga ou se a API foi atualizada.
        print(f"ERRO DE ATRIBUTO: {ae}")
        print("Possível causa: Versão desatualizada da biblioteca 'google-generativeai' ou mudança na API.")
        print("Tente atualizar a biblioteca com: pip install --upgrade google-generativeai")
        return jsonify({"error": f"Erro interno do servidor: Atributo não encontrado no módulo Gemini ({ae})."}), 500
    except Exception as e:
        # Captura quaisquer outros erros inesperados que possam ocorrer.
        print(f"ERRO GERAL ao gerar narração: {e}")
        # Retorna uma mensagem de erro genérica para o frontend.
        return jsonify({"error": f"Ocorreu um erro ao gerar a narração: {e}"}), 500

# --- Bloco Principal para Execução Local ---
if __name__ == '__main__':
    # Este bloco é executado apenas quando você roda o script Python diretamente (`python app.py`).
    # Ele NÃO é usado pelo Render.com, que utiliza um servidor WSGI (como Gunicorn).

    # Para rodar localmente:
    # 1. Certifique-se de ter um arquivo `.env` com `GEMINI_API_KEY=SUA_CHAVE_SECRETA`.
    # 2. Crie as pastas `templates/` e `static/js/`.
    # 3. Coloque `index.html` em `templates/` e `voices.js` em `static/js/`.
    # 4. Execute `python app.py`.
    # A aplicação estará disponível em http://127.0.0.1:5000/

    # Executa o servidor Flask localmente.
    # `debug=False` é recomendado para produção. Use `debug=True` para desenvolvimento.
    app.run(debug=False, port=5000)