import os
import base64
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS # Importa CORS
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# --- Função Auxiliar para Formatar Exibição do Locutor ---
def format_voice_display(voice):
    """Formata o nome do locutor, gênero e especialidade para exibição no HTML."""
    gender_text = 'Feminino' if voice.get('gender') == 'F' else 'Masculino'
    specialty = voice.get('specialty', 'N/A') # Usa 'N/A' se specialty não estiver presente
    return f"{voice.get('name', 'Nome Inválido')} ({gender_text} - {specialty})"

# --- Configuração CORS ---
# Se você está hospedando o HTML na Hostinger e o backend no Render,
# é necessário permitir requisições da sua Hostinger.
# Substitua 'URL_DA_SUA_HOSTINGER_AQUI' pela URL real do seu site na Hostinger.
# Ex: CORS(app, resources={r"/generate-narration": {"origins": "https://seu-site-hostinger.com"}})
# Para teste inicial, pode usar:
CORS(app) # Permite requisições de qualquer origem. Ajuste para maior segurança se necessário.

# --- Configuração da API do Gemini ---
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    # Se a chave não estiver nas variáveis de ambiente (ex: no Render), retorna um erro.
    # Em um ambiente de produção, este erro deve ser tratado de forma mais robusta.
    print("ERRO: A chave da API do Google Gemini (GOOGLE_API_KEY) não está definida nas variáveis de ambiente.")
    # Para rodar localmente, crie um arquivo .env com GOOGLE_API_KEY=SUA_CHAVE_AQUI

genai.configure(api_key=api_key)

# Modelo de TTS (Text-to-Speech)
model_name = "gemini-2.5-pro-preview-tts"

# --- Dados dos Locutores ---
# Lista de locutores fornecida no seu arquivo voices.js.txt.
# Certifique-se que estes IDs são válidos para a API do Gemini TTS.
VOICES_DATA = [
    {'id': 'aoede', 'name': 'Laura', 'gender': 'F', 'specialty': 'Ideal para narração e leitura de textos longos'},
    {'id': 'autonoe', 'name': 'Beatriz', 'gender': 'F', 'specialty': 'Ótima para personagens e vozes de assistente'},
    {'id': 'callirrhoe', 'name': 'Vanessa', 'gender': 'F', 'specialty': 'Excelente para vozes de personagens diversos'},
    {'id': 'sulafat', 'name': 'Diana', 'gender': 'F', 'specialty': 'Voz de assistente, clara e conversacional'},
    {'id': 'despina', 'name': 'Helena', 'gender': 'F', 'specialty': 'Perfeita para narração informativa e didática'},
    {'id': 'vindemiatrix', 'name': 'Júlia', 'gender': 'F', 'specialty': 'Versátil para assistentes e personagens'},
    {'id': 'achernar', 'name': 'Patrícia', 'gender': 'F', 'specialty': 'Boa para leitura de textos e narração'},
    {'id': 'pulcherrima', 'name': 'Camila', 'gender': 'F', 'specialty': 'Ideal para voz de assistente e tutoriais'},
    {'id': 'zephyr', 'name': 'Mariana', 'gender': 'F', 'specialty': 'Voz de personagem, energética e expressiva'},
    {'id': 'kore', 'name': 'Amanda', 'gender': 'F', 'specialty': 'Excelente para narração de conteúdo'},
    {'id': 'achird', 'name': 'Lucas', 'gender': 'M', 'specialty': 'Perfeito para narração e leitura'},
    {'id': 'charon', 'name': 'André', 'gender': 'M', 'specialty': 'Voz de assistente, clara e objetiva'},
    {'id': 'algenib', 'name': 'Fábio', 'gender': 'M', 'specialty': 'Ótimo para personagens e vozes criativas'},
    {'id': 'alnilam', 'name': 'Bruno', 'gender': 'M', 'specialty': 'Excelente para vozes de personagens'},
    {'id': 'algieba', 'name': 'Gustavo', 'gender': 'M', 'specialty': 'Ideal para narração de documentários'},
    {'id': 'sadaltager', 'name': 'Rafael', 'gender': 'M', 'specialty': 'Voz de assistente, confiável e direta'},
    {'id': 'zubenelgenubi', 'name': 'Sérgio', 'gender': 'M', 'specialty': 'Voz de personagem, versátil e adaptável'},
    {'id': 'umbriel', 'name': 'Thiago', 'gender': 'M', 'specialty': 'Perfeito para assistentes virtuais'},
    {'id': 'fenrir', 'name': 'Eduardo', 'gender': 'M', 'specialty': 'Bom para narração de textos e e-learning'},
    {'id': 'sadachbia', 'name': 'Leandro', 'gender': 'M', 'specialty': 'Ótimo para leitura e narração de conteúdo'},
    {'id': 'iapetus', 'name': 'Ricardo', 'gender': 'M', 'specialty': 'Voz de assistente e conversacional'},
    {'id': 'enceladus', 'name': 'Vitor', 'gender': 'M', 'specialty': 'Ideal para vozes de personagens e jogos'},
    {'id': 'schedar', 'name': 'Rodrigo', 'gender': 'M', 'specialty': 'Voz de narração, clara e profissional'},
    {'id': 'rasalgethi', 'name': 'Felipe', 'gender': 'M', 'specialty': 'Excelente para assistente e aplicações'},
    {'id': 'orus', 'name': 'Fernando', 'gender': 'M', 'specialty': 'Ótimo para narração de documentários e vídeos'},
    {'id': 'puck', 'name': 'Paulo', 'gender': 'M', 'specialty': 'Voz de personagem, expressiva e criativa'}
]

# --- Rotas da Aplicação ---

@app.route('/')
def index():
    """Renderiza o arquivo index.html.
    Formata a lista de locutores antes de passá-la para o template.
    """
    formatted_voices = []
    for voice in VOICES_DATA:
        formatted_voices.append({
            'id': voice['id'],
            'display_text': format_voice_display(voice) # Usa a função formatadora
        })
    # Passa a lista formatada para o template Jinja.
    return render_template('index.html', voices=formatted_voices)

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve arquivos estáticos (CSS, JS, imagens) localizados na pasta 'static'.
    Isso é útil se você também hospeda os arquivos estáticos no mesmo servidor Flask/Render.
    """
    # O Render.com geralmente lida com isso se a pasta 'static' estiver na raiz.
    # Esta rota é mais para garantir que funciona se você servir tudo do Render.
    return send_from_directory('static', filename)


@app.route('/generate-narration', methods=['POST'])
def generate_narration():
    """Recebe o texto e o locutor via POST, chama a API do Gemini e retorna o áudio."""
    data = request.get_json()
    text_to_speak = data.get('text')
    voice_id = data.get('voiceId') # Recebe o ID do locutor selecionado pelo usuário

    if not text_to_speak or not voice_id:
        return jsonify({"error": "Texto e ID do locutor são obrigatórios."}), 400

    # Verifica se a chave da API foi carregada corretamente
    if not api_key:
        return jsonify({"error": "Chave da API do Gemini não configurada."}), 500

    try:
        # Cria o objeto de voz com o ID fornecido.
        # É fundamental que o voice_id corresponda a um nome de voz suportado pela API do Gemini TTS.
        voice_selection = genai.Voice(name=voice_id)

        # Chama a API do Gemini para gerar o áudio.
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

        # O Gemini TTS retorna o áudio em bytes.
        # Convertemos para base64 para facilitar o envio via JSON e manipulação no JavaScript.
        audio_content = response.candidates[0].content.audio.get_wav_data()
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')

        # Retorna o áudio em base64 para o frontend.
        return jsonify({"audioContent": audio_base64})

    except Exception as e:
        print(f"Erro ao gerar narração: {e}")
        # Retorna um erro genérico para o usuário, mas loga o erro detalhado no console.
        return jsonify({"error": f"Ocorreu um erro ao gerar a narração: {e}"}), 500

# --- Bloco Principal para Execução Local ---
if __name__ == '__main__':
    # Esta seção é para rodar a aplicação localmente para testes.
    # Ao fazer deploy no Render, o Render gerencia o servidor WSGI (como Gunicorn).

    # Certifique-se de que você tem um arquivo .env na mesma pasta do app.py
    # com o seguinte conteúdo:
    # GOOGLE_API_KEY=SUA_CHAVE_SECRETA_AQUI

    # Cria a pasta 'templates' e o arquivo 'index.html' se não existirem
    # (apenas para conveniência de teste local, o deploy no Render/GitHub usa o que já está lá)
    if not os.path.exists('templates'):
        os.makedirs('templates')
    if not os.path.exists('templates/index.html'):
        # Cria um index.html básico se ele não existir
        with open('templates/index.html', 'w', encoding='utf-8') as f:
            f.write("""
            <!DOCTYPE html>
            <html lang="pt-BR">
            <head><meta charset="UTF-8"><title>Teste</title></head>
            <body><h1>Página de Teste</h1><p>Se este arquivo foi criado, ele é um placeholder.</p><p>Copie o conteúdo completo do index.html que fornecemos anteriormente.</p></body>
            </html>
            """)

    # Executa o servidor Flask localmente.
    # debug=True é útil para desenvolvimento, mas deve ser False em produção.
    app.run(debug=False, port=5000) # Use a porta 5000 por padrão.