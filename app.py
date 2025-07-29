import os
from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()  # Carrega as variáveis de ambiente do arquivo .env

app = Flask(__name__)

# Configura a chave da API do Google Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Modelo de TTS (Text-to-Speech)
# Use a versão preview para garantir acesso aos recursos mais recentes
model_name = "gemini-2.5-pro-preview-tts"

# Lista de locutores fornecida no seu arquivo voices.js.txt
# Você pode carregar isso de um arquivo separado se preferir.
VOICES_DATA = [
    {'id': 'aoede', 'name': 'Laura', 'gender': 'F', 'specialty': 'Ideal para narração e leitura de textos longos'},
    {'id': 'autonoe', 'name': 'Beatriz', 'gender': 'F', 'specialty': 'Ótima para personagens e vozes de assistente'},
    {'id': 'callirrhoe', 'name': 'Vanessa', 'gender': 'F', 'specialty': 'Excelente para vozes de personagens diversos'},
    {'id': 'sulafat', 'name': 'Diana', 'gender': 'F', 'specialty': 'Voz de assistente, clara e conversacional'},
    {'id': 'despina', 'name': 'Helena', 'gender': 'F', 'specialty': 'Perfeita para narração informativa e didática'},
    {'id': 'vindemiatrix', 'name': 'Júlia', 'gender:': 'F', 'specialty': 'Versátil para assistentes e personagens'},
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

@app.route('/')
def index():
    """Renderiza a página principal com a lista de locutores."""
    return render_template('index.html', voices=VOICES_DATA)

@app.route('/generate-narration', methods=['POST'])
def generate_narration():
    """Recebe o texto e o locutor, e retorna o áudio gerado."""
    data = request.get_json()
    text_to_speak = data.get('text')
    voice_id = data.get('voiceId') # O ID do locutor selecionado

    if not text_to_speak or not voice_id:
        return jsonify({"error": "Texto e ID do locutor são obrigatórios."}), 400

    try:
        # Chama a API do Gemini para gerar o áudio
        # O Gemini TTS espera que o locutor seja especificado pelo seu ID (identificador único)
        # O modelo "gemini-2.5-pro-preview-tts" já está otimizado para isso.
        response = genai.generate_content(
            model=model_name,
            contents=[
                genai.Candidate(
                    content=genai.Part(
                        text=text_to_speak,
                        voice=genai.Voice(name=voice_id) # Passa o ID do locutor aqui
                    )
                )
            ]
        )

        # O Gemini TTS retorna o áudio diretamente em bytes.
        # Precisamos convertê-lo para um formato que o navegador possa reproduzir,
        # como um arquivo .wav ou .mp3. O Gemini retorna .wav por padrão.
        audio_content = response.candidates[0].content.audio.get_wav_data()

        # Em um aplicativo real, você precisaria salvar esse áudio em algum lugar (ex: S3, Google Cloud Storage)
        # e retornar uma URL para ele. Para este exemplo simples, vamos apenas retornar os bytes brutos
        # e o JavaScript no frontend lidará com a reprodução.
        # Ou, podemos tentar base64 encode para facilitar o envio pela resposta JSON.

        import base64
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')

        return jsonify({"audioContent": audio_base64})

    except Exception as e:
        print(f"Erro ao gerar narração: {e}")
        return jsonify({"error": f"Ocorreu um erro ao gerar a narração: {e}"}), 500

if __name__ == '__main__':
    # Para rodar localmente
    # Certifique-se de que seu arquivo .env está configurado
    app.run(debug=True)