# app.py - VERSÃO FINAL OTIMIZADA PARA MEMÓRIA
import os
import base64
import struct
import io
import re
import tempfile
import gc
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from google.genai import types
from dotenv import load_dotenv
from pydub import AudioSegment

# --- Configuração Inicial ---
load_dotenv()
app = Flask(__name__)
CORS(app)

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("ERRO CRÍTICO: A chave da API do Gemini (GEMINI_API_KEY) não está definida.")

# --- Funções de Suporte (sem alterações) ---
def sanitize_and_normalize_text(text):
    if not isinstance(text, str): text = str(text)
    text = re.sub(r'R\$\s*([\d,.]+)', lambda m: m.group(1).replace('.', '').replace(',', ' vírgula ') + ' reais', text)
    text = re.sub(r'(\d+)\s*[xX](?!\w)', r'\1 vezes ', text)
    text = re.sub(r'\s*[-–—]\s*', ', ', text)
    text = re.sub(r'(!+)', '!', text)
    text = re.sub(r'(\?+)', '?', text)
    text = re.sub(r'(\.+)', '.', text)
    text = re.sub(r'[^\w\s.,!?áéíóúâêîôûãõàèìòùçÁÉÍÓÚÂÊÎÔÛÃÕÀÈÌÒÙÇ]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def split_text_into_chunks(text, max_length=4500):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 < max_length:
            current_chunk += sentence + " "
        else:
            if current_chunk: chunks.append(current_chunk.strip())
            current_chunk = sentence + " "
    if current_chunk: chunks.append(current_chunk.strip())
    return chunks

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters.get("bits_per_sample", 16); sample_rate = parameters.get("rate", 24000); num_channels = 1; data_size = len(audio_data); bytes_per_sample = bits_per_sample // 8; block_align = num_channels * bytes_per_sample; byte_rate = sample_rate * block_align; chunk_size = 36 + data_size
    header = struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", chunk_size, b"WAVE", b"fmt ", 16, 1, num_channels, sample_rate, byte_rate, block_align, bits_per_sample, b"data", data_size)
    return header + audio_data

def parse_audio_mime_type(mime_type: str) -> dict[str, int | None]:
    rate = 24000; bits_per_sample = 16
    if mime_type:
        parts = mime_type.split(";")
        for param in parts:
            param = param.strip()
            if param.lower().startswith("rate="):
                try: rate = int(param.split("=", 1)[1])
                except (ValueError, IndexError): pass
    return {"bits_per_sample": bits_per_sample, "rate": rate}

# --- Rotas da API ---
@app.route('/')
def home():
    return "Serviço de Narração está online (v5.0 - Otimizado para Memória)."

@app.route('/health')
def health_check():
    return "API de Narração está saudável.", 200

@app.route('/generate-narration', methods=['POST'])
def generate_narration():
    data = request.get_json()
    if not data: return jsonify({"error": "Requisição JSON inválida."}), 400
    text_to_speak = data.get('text')
    voice_id = data.get('voiceId')
    if not text_to_speak or not voice_id: return jsonify({"error": "Os campos 'text' e 'voiceId' são obrigatórios."}), 400

    temp_files = []
    try:
        normalized_text = sanitize_and_normalize_text(text_to_speak)
        text_chunks = split_text_into_chunks(normalized_text)

        client = genai.Client(api_key=API_KEY)
        model_name = "gemini-2.5-pro-preview-tts"

        for i, chunk_text in enumerate(text_chunks):
            if not chunk_text: continue

            contents = [types.Content(role="user", parts=[types.Part.from_text(text=chunk_text)])]
            generation_config = types.GenerateContentConfig(response_modalities=["audio"], speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_id))))

            full_audio_data = bytearray()
            audio_mime_type = "audio/L16;rate=24000"

            try:
                stream = client.models.generate_content_stream(model=model_name, contents=contents, config=generation_config)
                for chunk in stream:
                    if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                        part = chunk.candidates[0].content.parts[0]
                        if part.inline_data and part.inline_data.data:
                            full_audio_data.extend(part.inline_data.data)
                            if part.inline_data.mime_type: audio_mime_type = part.inline_data.mime_type
            except Exception as api_error:
                return jsonify({"error": f"A API do Gemini falhou ao processar um trecho: {api_error}"}), 422

            if not full_audio_data: continue

            # [OTIMIZAÇÃO] Salva o pedaço em um arquivo temporário no disco em vez de manter na RAM
            wav_data = convert_to_wav(bytes(full_audio_data), audio_mime_type)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                temp_file.write(wav_data)
                temp_files.append(temp_file.name)
            
            # Libera a memória explicitamente
            del full_audio_data
            del wav_data
            gc.collect()

        if not temp_files:
            return jsonify({"error": "Não foi possível gerar áudio para o texto fornecido."}), 500

        # [OTIMIZAÇÃO] Concatena os arquivos do disco, um por um, para manter o uso de RAM baixo
        final_audio = AudioSegment.empty()
        for temp_file_path in temp_files:
            audio_chunk = AudioSegment.from_file(temp_file_path, format="wav")
            final_audio += audio_chunk
            del audio_chunk # Libera a memória do pedaço após a junção
            gc.collect()

        mp3_file_in_memory = io.BytesIO()
        final_audio.export(mp3_file_in_memory, format="mp3", bitrate="320k")
        mp3_data = mp3_file_in_memory.getvalue()
        
        audio_base64 = base64.b64encode(mp3_data).decode('utf-8')
        return jsonify({"audioContent": audio_base64})

    except Exception as e:
        print(f"ERRO INESPERADO NO SERVIDOR: {e}")
        return jsonify({"error": f"Ocorreu um erro interno no servidor Python. Detalhe: {e}"}), 500
    finally:
        # [OTIMIZAÇÃO] Garante que todos os arquivos temporários sejam deletados
        for temp_file_path in temp_files:
            try:
                os.remove(temp_file_path)
            except OSError:
                pass

if __name__ == '__main__':
    app.run(debug=True, port=5000)
