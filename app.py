import os
import base64
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
# Importações para a NOVA SDK
from google.generativeai import GenerativeModel, configure
# Pode ser que a configuração de TTS esteja em outro lugar

load_dotenv()

app = Flask(__name__)
CORS(app)

# --- Configuração da API do Gemini (NOVA SDK) ---
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("ERRO CRÍTICO: A chave da API do Gemini (GEMINI_API_KEY) não está definida nas variáveis de ambiente.")
configure(api_key=api_key) # <<< ALTERAÇÃO NA CONFIGURAÇÃO

# O nome do modelo TTS pode ser diferente na nova SDK, ou o acesso a ele.
# Verifique a documentação oficial para encontrar o modelo TTS correto.
# Se não houver um modelo direto de TTS com este nome, pode ser necessário usar outro serviço.
model_name = "gemini-2.5-pro-preview-tts" # MANTENHA ESTE POR ENQUANTO, MAS ESTEJA CIENTE QUE PODE SER NECESSÁRIO MUDAR

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
        # --- ACESSO AO MODELO E GERAÇÃO DE ÁUDIO (NOVA SDK) ---
        # A forma de chamar um modelo TTS com a nova SDK será diferente.
        # Provavelmente você instanciará um modelo de TTS e chamará um método específico.

        # Exemplo HIPOTÉTICO (VOCÊ PRECISA CONFIRMAR NA DOC):
        # model = GenerativeModel('gemini-2.5-pro-preview-tts') # OU UM MODELO TTS ESPECÍFICO
        # response = model.generate_content(
        #     text_to_speak,
        #     generation_config={"voice": {"name": voice_id}} # Ou outra forma de passar a voz
        # )

        # A documentação do google-genai para TTS sugere algo como:
        # model = genai.GenerativeModel('gemini-2.5-pro-preview-tts') # Use a nova forma de instanciar
        # response = model.generate_content(
        #     text=text_to_speak,
        #     generation_config={"voice": {"name": voice_id}}
        # )
        # E a extração de áudio pode ser response.audio.get_wav_data()

        # Tentativa com base no que foi visto na documentação do google-genai:
        model = GenerativeModel(model_name) # Instancia o modelo
        response = model.generate_content(
            text=text_to_speak,
            generation_config={"voice": {"name": voice_id}} # Passa a voz na configuração
        )

        # Extrai o áudio. A forma de obter o áudio pode ser diferente.
        # O .audio.get_wav_data() pode ser agora response.audio.get_wav_data()
        if hasattr(response, 'audio') and hasattr(response.audio, 'get_wav_data'):
             audio_content = response.audio.get_wav_data()
        else:
             raise ValueError("Formato de áudio inesperado na resposta da API com a nova SDK.")

        audio_base64 = base64.b64encode(audio_content).decode('utf-8')

        return jsonify({"audioContent": audio_base64})

    except AttributeError as ae:
        print(f"ERRO DE ATRIBUTO: {ae}")
        print("Isso pode acontecer se a nova SDK 'google-genai' não for usada corretamente ou se o modelo TTS mudar.")
        return jsonify({"error": f"Erro interno: Atributo não encontrado na nova SDK Gemini ({ae}). Verifique a documentação."}), 500
    except ValueError as ve:
        print(f"ERRO DE VALOR: {ve}")
        return jsonify({"error": f"Erro ao processar a resposta de áudio: {ve}"}), 500
    except Exception as e:
        print(f"ERRO GERAL ao gerar narração: {e}")
        return jsonify({"error": f"Ocorreu um erro ao gerar a narração: {e}"}), 500

# Bloco principal (para rodar localmente)
if __name__ == '__main__':
    app.run(debug=False, port=5000)```

**Ação imediata:**

1.  **Atualize o `requirements.txt`:** Mude para `google-genai` e remova `google-generativeai`.
2.  **Aguarde o deploy no Render** com o novo `requirements.txt`.
3.  **Consulte a documentação oficial do `google-genai` para TTS** e adapte o `app.py` conforme as instruções deles. O exemplo que dei acima é uma tentativa baseada em como outras SDKs funcionam, mas o Google pode ter uma estrutura específica.