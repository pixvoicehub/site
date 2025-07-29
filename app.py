import os
import base64
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# --- Configuração CORS ---
CORS(app)

# --- Configuração da API do Gemini ---
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("ERRO CRÍTICO: A chave da API do Gemini (GEMINI_API_KEY) não está definida nas variáveis de ambiente.")

genai.configure(api_key=api_key)

# O modelo TTS pode ser diferente dependendo da versão da SDK e da disponibilidade
# "gemini-1.5-pro-latest" ou modelos específicos de TTS podem ser necessários.
# Para TTS, modelos como "text-bison" ou modelos do Vertex AI podem ser mais adequados se o Gemini não tiver TTS direto.
# Vamos manter o seu modelo por enquanto, mas saiba que pode ser necessário alterá-lo se não for o correto para TTS.
model_name = "gemini-2.5-pro-preview-tts" # MANTENHA O SEU MODELO POR ENQUANTO

# --- Rotas da Aplicação ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

@app.route('/generate-narration', methods=['POST'])
def generate_narration():
    data = request.get_json()
    text_to_speak = data.get('text')
    voice_id = data.get('voiceId')

    if not text_to_speak or not voice_id:
        return jsonify({"error": "Texto e ID do locutor são obrigatórios."}), 400

    if not api_key:
        return jsonify({"error": "Chave da API do Gemini não configurada."}), 500

    try:
        # --- TENTATIVA DE ESPECIFICAÇÃO DA VOZ (SEM genai.tts) ---
        # A forma de especificar a voz para TTS pode ser através de um objeto de configuração
        # ou um argumento direto no 'generate_content'.
        # Vamos tentar passar um argumento 'generation_config' com a voz.
        # É CRUCIAL VERIFICAR NA DOCUMENTAÇÃO COMO FAZER ISSO CORRETAMENTE.

        # Exemplo genérico (PODE SER QUE NÃO FUNCIONE, VOCÊ PRECISA CONFIRMAR NA DOC)
        # O Google AI Studio e a API podem ter formas diferentes de especificar vozes.
        # Uma forma comum é usar um dicionário de configuração.
        generation_config = {
            "voice": {
                "name": voice_id # Tenta passar o voice_id diretamente aqui
                # Dependendo da API, pode precisar de mais campos como 'language_code'
            }
            # Outra possibilidade é que o argumento seja 'tts_config'
            # tts_config={"voice": {"name": voice_id}}
        }


        response = genai.generate_content(
            model=model_name,
            contents=[
                genai.Candidate(
                    content=genai.Part(
                        text=text_to_speak
                        # A voz não é passada aqui diretamente no 'Part' se for por config.
                    )
                )
            ],
            generation_config=generation_config # Tenta passar a configuração aqui
            # OU se a doc indicar, pode ser um argumento diferente:
            # tts_config=genai.TtsConfig(...) # (mas genai.tts.TtsConfig não existe)
            # O mais provável é que generation_config seja o caminho.
        )

        # --- EXTRAÇÃO DE ÁUDIO ---
        # A forma de obter o áudio da resposta pode ter mudado.
        # Se o response.candidates[0].content.audio.get_wav_data() der erro,
        # você precisará verificar como a API retorna o áudio.
        # Pode ser que o response.audio.get_wav_data() seja o correto.

        # Tenta obter o áudio usando a estrutura que parece mais comum após a atualização:
        if hasattr(response.candidates[0].content, 'audio') and hasattr(response.candidates[0].content.audio, 'get_wav_data'):
             audio_content = response.candidates[0].content.audio.get_wav_data()
        elif hasattr(response, 'audio') and hasattr(response.audio, 'get_wav_data'): # Outra possibilidade
             audio_content = response.audio.get_wav_data()
        else:
             # Se nenhuma das formas funcionar, precisamos de mais informações sobre a resposta da API.
             raise ValueError("Formato de áudio inesperado na resposta da API.")

        audio_base64 = base64.b64encode(audio_content).decode('utf-8')

        return jsonify({"audioContent": audio_base64})

    except AttributeError as ae:
        print(f"ERRO DE ATRIBUTO: {ae}")
        print("A estrutura da SDK do Google Gemini pode ter mudado ou a versão é incompatível.")
        print("Recomendação: Verifique a documentação oficial mais recente para APIs de TTS.")
        return jsonify({"error": f"Erro interno: Atributo não encontrado no módulo Gemini ({ae}). Verifique a versão da SDK."}), 500
    except ValueError as ve: # Captura o erro de formato de áudio inesperado
        print(f"ERRO DE VALOR: {ve}")
        return jsonify({"error": f"Erro ao processar a resposta de áudio: {ve}"}), 500
    except Exception as e:
        print(f"ERRO GERAL ao gerar narração: {e}")
        return jsonify({"error": f"Ocorreu um erro ao gerar a narração: {e}"}), 500

# --- Bloco Principal para Execução Local ---
if __name__ == '__main__':
    # Para rodar localmente, garanta que seu arquivo .env tenha a chave correta
    # e que as pastas 'templates' e 'static/js' estejam com os arquivos 'index.html' e 'voices.js'.
    app.run(debug=False, port=5000)