# app.py - Adaptado fielmente ao código oficial do Gemini
import os
import base64
import mimetypes
import struct
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from google.genai import types
from dotenv import load_dotenv

# --- Configuração Inicial ---
load_dotenv()
app = Flask(__name__)
CORS(app)

# A chave da API será usada para criar o cliente dentro da rota, como no código original.
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("ERRO CRÍTICO: A chave da API do Gemini (GEMINI_API_KEY) não está definida.")

# --- Funções de Suporte (do código oficial, sem alterações) ---
# Estas funções são necessárias para processar a resposta de áudio do modelo.

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Gera um cabeçalho WAV para os dados de áudio fornecidos."""
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", chunk_size, b"WAVE", b"fmt ", 16, 1, num_channels,
        sample_rate, byte_rate, block_align, bits_per_sample,
        b"data", data_size
    )
    return header + audio_data

def parse_audio_mime_type(mime_type: str) -> dict[str, int | None]:
    """Extrai bits por amostra e taxa de um tipo MIME de áudio."""
    bits_per_sample = 16
    rate = 24000
    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate = int(param.split("=", 1)[1])
            except (ValueError, IndexError):
                pass
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass
    return {"bits_per_sample": bits_per_sample, "rate": rate}

# --- Rota Principal da API ---

@app.route('/generate-narration', methods=['POST'])
def generate_narration():
    """
    Endpoint que gera a narração usando a estrutura do código oficial.
    """
    data = request.get_json()
    text_to_speak = data.get('text')
    # O código oficial usa um nome de voz fixo ('Zephyr').
    # Vamos usar o voice_id enviado pelo frontend para manter a funcionalidade.
    voice_id = data.get('voiceId')

    if not text_to_speak or not voice_id:
        return jsonify({"error": "Texto e ID do locutor são obrigatórios."}), 400

    try:
        # --- Estrutura do Código Oficial ---
        client = genai.Client(api_key=API_KEY)

        # Usando o nome do modelo que você especificou.
        model = "gemini-2.5-pro-preview-tts"
        
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=text_to_speak)],
            ),
        ]
        
        generate_content_config = types.GenerateContentConfig(
            temperature=1,
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_id  # Usando a voz selecionada no frontend.
                    )
                )
            ),
        )

        # Variável para juntar os pedaços (chunks) de áudio
        audio_chunks = []
        
        # Processa o stream de resposta da API
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if (
                chunk.candidates is None
                or chunk.candidates[0].content is None
                or chunk.candidates[0].content.parts is None
            ):
                continue
            
            part = chunk.candidates[0].content.parts[0]
            if part.inline_data and part.inline_data.data:
                # Em vez de salvar em arquivo, adicionamos o pedaço de áudio à nossa lista
                audio_chunks.append(part.inline_data.data)

        if not audio_chunks:
            return jsonify({"error": "A API não retornou dados de áudio."}), 500

        # Junta todos os pedaços de áudio em um único objeto de bytes
        full_audio_data = b"".join(audio_chunks)
        
        # Codifica o áudio completo em base64 para enviar ao frontend
        audio_base64 = base64.b64encode(full_audio_data).decode('utf-8')

        return jsonify({"audioContent": audio_base64})

    except Exception as e:
        print(f"ERRO ao gerar narração com o SDK: {e}")
        return jsonify({"error": f"Ocorreu um erro no servidor ao gerar a narração. Detalhe: {e}"}), 500

# --- Bloco de Execução Local ---
if __name__ == '__main__':
    app.run(debug=True, port=5000)
