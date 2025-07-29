# app.py - VERSÃO FINAL COM CONVERSÃO PARA MP3
import os
import base64
import mimetypes
import struct
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Novas importações para a conversão MP3
from pydub import AudioSegment
import io

# --- Configuração Inicial ---
load_dotenv()
app = Flask(__name__)
CORS(app)

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("ERRO CRÍTICO: A chave da API do Gemini (GEMINI_API_KEY) não está definida.")

# --- Funções de Suporte (do código oficial) ---

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Gera um cabeçalho WAV para os dados de áudio fornecidos."""
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters.get("bits_per_sample", 16)
    sample_rate = parameters.get("rate", 24000)
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
    rate = 24000
    bits_per_sample = 16
    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate = int(param.split("=", 1)[1])
            except (ValueError, IndexError):
                pass
    if "audio/L16" in mime_type:
        bits_per_sample = 16
    
    return {"bits_per_sample": bits_per_sample, "rate": rate}

# --- Rota Principal da API ---

@app.route('/generate-narration', methods=['POST'])
def generate_narration():
    data = request.get_json()
    text_to_speak = data.get('text')
    voice_id = data.get('voiceId')

    if not text_to_speak or not voice_id:
        return jsonify({"error": "Texto e ID do locutor são obrigatórios."}), 400

    try:
        client = genai.Client(api_key=API_KEY)
        model = "gemini-2.5-pro-preview-tts"
        
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=text_to_speak)])]
        
        generate_content_config = types.GenerateContentConfig(
            temperature=1,
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_id)
                )
            ),
        )

        full_audio_data = bytearray()
        audio_mime_type = "audio/L16;rate=24000"

        for chunk in client.models.generate_content_stream(
            model=model, contents=contents, config=generate_content_config
        ):
            if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                part = chunk.candidates[0].content.parts[0]
                if part.inline_data and part.inline_data.data:
                    full_audio_data.extend(part.inline_data.data)
                    if part.inline_data.mime_type:
                        audio_mime_type = part.inline_data.mime_type

        if not full_audio_data:
            return jsonify({"error": "A API não retornou dados de áudio."}), 500

        # 1. Converte os dados brutos para o formato WAV em memória
        wav_data = convert_to_wav(bytes(full_audio_data), audio_mime_type)
        
        # 2. Carrega os dados WAV no pydub a partir de um buffer de memória
        wav_file_like = io.BytesIO(wav_data)
        audio_segment = AudioSegment.from_file(wav_file_like, format="wav")

        # 3. Exporta o áudio como MP3 para um novo buffer de memória
        mp3_file_like = io.BytesIO()
        audio_segment.export(mp3_file_like, format="mp3")
        mp3_data = mp3_file_like.getvalue()
        
        # 4. Codifica os dados MP3 em base64 para enviar ao frontend
        audio_baseCom certeza! Excelente ideia. O formato MP3 é muito mais eficiente para a web, resultando em arquivos menores e carregamento mais rápido para o usuário.

Para fazer a conversão de WAV para MP3 no backend, precisaremos de uma biblioteca de manipulação de áudio. A mais popular e robusta para Python é a **`pydub`**. Ela é fácil de usar e se integra bem com o Flask.

O processo será o seguinte:
1.  Receber os dados de áudio brutos do Gemini.
2.  Construir o arquivo WAV em memória (como fizemos antes).
3.  Usar a `pydub` para carregar este áudio WAV.
4.  Exportar o áudio como MP3, também em memória.
5.  Codificar o resultado MP3 em base64 e enviar para o frontend.

### Passo 1: Adicionar a Biblioteca `pydub`

Primeiro, você precisa adicionar a `pydub` ao seu arquivo `requirements.txt`.

**`requirements.txt` (Atualizado):**
