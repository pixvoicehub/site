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
# Certifique-se de que a variável de ambiente configurada no Render (e localmente via .env)
# seja GEMINI_API_KEY.
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    # Se a chave não estiver definida, não podemos prosseguir.
    # Em um ambiente de produção, um log mais detalhado seria útil.
    print("ERRO CRÍTICO: A chave da API do Gemini (GEMINI_API_KEY) não está definida nas variáveis de ambiente.")
    # Para rodar localmente, crie um arquivo .env na mesma pasta do app.py com:
    # GEMINI_API_KEY=SUA_CHAVE_SECRETA_AQUI
    # Se você rodar isso sem a chave, a API não funcionará.

genai.configure(api_key=api_key)

# Modelo de TTS (Text-to-Speech) que estamos utilizando.
model_name = "gemini-2.5-pro-preview-tts"

# --- Rotas da Aplicação ---

@app.route('/')
def index():
    """
    Renderiza o arquivo index.html.
    Este arquivo HTML foi projetado para ser populado dinamicamente pelo JavaScript
    carregado de um arquivo externo (voices.js).
    """
    # Não precisamos mais passar os dados das vozes via render_template,
    # pois o JavaScript cuidará disso.
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """
    Serve arquivos estáticos (como CSS, JavaScript, imagens)
    que estão localizados na pasta 'static' do seu projeto.
    Isso é essencial para que o index.html possa carregar o voices.js.
    """
    # O Render.com geralmente é capaz de servir arquivos estáticos se a pasta 'static'
    # estiver na raiz do projeto que você está deployando.
    return send_from_directory('static', filename)


@app.route('/generate-narration', methods=['POST'])
def generate_narration():
    """
    Endpoint que recebe as requisições do frontend (POST) contendo o texto a ser narrado
    e o ID do locutor selecionado.
    Em seguida, chama a API do Gemini Text-to-Speech e retorna o áudio gerado.
    """
    data = request.get_json()
    text_to_speak = data.get('text')
    voice_id = data.get('voiceId') # Recebe o ID do locutor selecionado pelo usuário

    # Validação básica dos dados recebidos.
    if not text_to_speak or not voice_id:
        return jsonify({"error": "Texto e ID do locutor são obrigatórios."}), 400

    # Verifica se a chave da API foi carregada corretamente.
    if not api_key:
        # Se api_key for None ou vazio, significa que GEMINI_API_KEY não foi configurada.
        return jsonify({"error": "Chave da API do Gemini não configurada."}), 500

    try:
        # Cria o objeto de voz com o ID fornecido.
        # É crucial que o voice_id (ex: 'aoede', 'achird') corresponda a um nome de voz
        # suportado pela API do Gemini TTS.
        voice_selection = genai.Voice(name=voice_id)

        # Chama a API do Gemini para gerar o áudio a partir do texto e da voz selecionada.
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

        # A resposta da API contém o áudio em formato de bytes.
        # Precisamos converter esses bytes para uma string base64 para enviá-la
        # facilmente através de uma resposta JSON e manipulá-la no JavaScript do frontend.
        audio_content = response.candidates[0].content.audio.get_wav_data()
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')

        # Retorna o áudio em base64 e um status de sucesso.
        return jsonify({"audioContent": audio_base64})

    except Exception as e:
        # Captura qualquer exceção que possa ocorrer durante a chamada à API do Gemini
        # ou durante o processamento da resposta.
        print(f"ERRO ao gerar narração: {e}") # Log do erro detalhado no console do servidor.
        # Retorna uma mensagem de erro genérica para o usuário no frontend.
        return jsonify({"error": f"Ocorreu um erro ao gerar a narração: {e}"}), 500

# --- Bloco Principal para Execução Local ---
if __name__ == '__main__':
    # Este bloco é executado apenas quando você roda o script Python diretamente
    # (ex: `python app.py`).
    # Ele não é usado pelo Render.com, que gerencia o servidor WSGI (como Gunicorn)
    # separadamente com base nos comandos de build e start configurados.

    # Para rodar localmente e testar:
    # 1. Certifique-se de que você tem um arquivo `.env` na mesma pasta do `app.py`
    #    contendo a sua chave: `GEMINI_API_KEY=SUA_CHAVE_SECRETA_AQUI`.
    # 2. Crie a estrutura de pastas: `templates/` e `static/js/`.
    # 3. Coloque o `index.html` dentro de `templates/`.
    # 4. Coloque o `voices.js` dentro de `static/js/`.
    # 5. Execute o script: `python app.py`

    # Executa o servidor Flask localmente.
    # `debug=False` é recomendado para produção. Para desenvolvimento, você pode usar `debug=True`.
    # `port=5000` é uma porta comum para aplicações Flask locais.
    app.run(debug=False, port=5000)