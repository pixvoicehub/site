# app.py - VERSÃO LEVE E OTIMIZADA PARA 512MB (Plano Gratuito do Render)

import os
import base64
import struct
import io
import re
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
    raise ValueError("ERRO: GEMINI_API_KEY não definida.")

# Limites seguros para baixa memória
MAX_CHARS_PER_CHUNK = 350  # Menor para evitar OOM
MAX_TOTAL_DURATION = 60  # Limite de tempo total em segundos

def sanitize_and_normalize_text(text):
    if not isinstance(text, str): text = str(text)
    text = re.sub(r'R\$\s*([\d,.]+)', lambda m: m.group(1).replace('.', '').replace(',', ' vírgula ') + ' reais', text)
    text = re.sub(r'(\d+)\s*[xX](?!\w)', r'\1 vezes ', text)
    text = re.sub(r'\s*[-–—]\s*', ', ', text)
    text = re.sub(r'[^\w\s.,!?áéíóúâêîôûãõàèìòùçÁÉÍÓÚÂÊÎÔÛÃÕÀÈÌÒÙÇ]', '', text)
    return re.sub(r'\s+', ' ', text).strip()

def split_text_into_chunks(text, max_chars=MAX_CHARS_PER_CHUNK):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= max_chars:
            current_chunk += sentence + " "
        else:
            if current_chunk: chunks.append(current_chunk.strip())
            # Força quebra se a frase for muito longa
            while len(sentence) > max_chars:
                chunks.append(sentence[:max_chars].strip())
                sentence = sentence[max_chars:]
            if sentence: current_chunk = sentence + " "
    if current_chunk.strip(): chunks.append(current_chunk.strip())
    return chunks

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    rate = 24000
    if mime_type and "rate=" in mime_type:
        try: rate = int(mime_type.split("rate=")[1].split(";")[0])
        except: pass
    header = struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 36 + len(audio_data), b"WAVE", b"fmt ", 16, 1, 1, rate, rate * 2, 2, 16, b"data", len(audio_data))
    return header + audio_data

@app.route('/')
def home():
    return "TTS Online (v7.2 - Low Memory)"

@app.route('/health')
def health():
    return "OK", 200

@app.route('/generate-narration', methods=['POST'])
def generate_narration():
    data = request.get_json()
    if not data: return jsonify({"error": "JSON inválido."}), 400
    text = data.get('text')
    voice_id = data.get('voiceId')
    if not text or not voice_id: return jsonify({"error": "text e voiceId obrigatórios."}), 400

    try:
        normalized_text = sanitize_and_normalize_text(text)
        chunks = split_text_into_chunks(normalized_text)
        print(f"[INFO] Texto: {len(normalized_text)} chars | {len(chunks)} chunks")

        client = genai.Client(api_key=API_KEY)
        model = "gemini-2.5-pro-preview-tts"
        final_audio = None  # Só cria o objeto no final

        for i, chunk in enumerate(chunks):
            print(f"[CHUNK {i+1}/{len(chunks)}] Gerando... ({len(chunk)} chars)")
            contents = [types.Content(role="user", parts=[types.Part.from_text(text=chunk)])]
            config = types.GenerateContentConfig(
                response_modalities=["audio"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_id)
                    )
                )
            )

            # Gera áudio para o chunk
            full_data = bytearray()
            stream = client.models.generate_content_stream(model=model, contents=contents, config=config)
            for response in stream:
                if response.candidates and response.candidates[0].content.parts:
                    part = response.candidates[0].content.parts[0]
                    if part.inline_data and part.inline_data.data:
                        full_data.extend(part.inline_data.data)

            if not full_data:
                print(f"[AVISO] Chunk {i+1} não gerou áudio.")
                continue

            # Converte para segmento de áudio
            wav_data = convert_to_wav(bytes(full_data), "audio/L16;rate=24000")
            segment = AudioSegment.from_file(io.BytesIO(wav_data), format="wav")
            segment += AudioSegment.silent(100)  # pausa natural

            # Concatena ao áudio final
            if final_audio is None:
                final_audio = segment
            else:
                final_audio += segment  # += é mais leve que sum()

            # Libera memória
            del full_data, wav_data, segment
            import gc; gc.collect()

        if final_audio is None:
            return jsonify({"error": "Nenhum áudio foi gerado."}), 500

        # Exporta para MP3 em memória
        mp3_buffer = io.BytesIO()
        final_audio.export(mp3_buffer, format="mp3", bitrate="128k")  # bitrate menor = menos uso de memória
        mp3_data = mp3_buffer.getvalue()

        # Libera memória
        del final_audio, mp3_buffer
        import gc; gc.collect()

        audio_base64 = base64.b64encode(mp3_data).decode('utf-8')
        return jsonify({"audioContent": audio_base64})

    except Exception as e:
        print(f"ERRO: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)