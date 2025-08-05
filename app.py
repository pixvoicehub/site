# app.py - VERSÃO OTIMIZADA PARA 512MB RAM (Render.com Free)

import os
import base64
import struct
import io
import re
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
    raise ValueError("ERRO: GEMINI_API_KEY não definida.")

# Limites seguros para baixa memória
MAX_CHARS_PER_CHUNK = 350  # Evita chunks muito grandes
MAX_RETRIES = 2

def sanitize_and_normalize_text(text):
    if not isinstance(text, str): text = str(text)
    text = re.sub(r'R\$\s*([\d,.]+)', r'\1 reais', text)
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
            # Quebra frases muito longas
            while len(sentence) > max_chars:
                chunks.append(sentence[:max_chars].strip())
                sentence = sentence[max_chars:]
            current_chunk = sentence + " " if sentence else ""
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
    return "TTS Online (v7.3 - Low Memory)"

@app.route('/health')
def health():
    return "OK", 200

@app.route('/generate-narration', methods=['POST'])
def generate_narration():
    data = request.get_json()
    if not  return jsonify({"error": "JSON inválido."}), 400
    text = data.get('text')
    voice_id = data.get('voiceId')
    if not text or not voice_id: return jsonify({"error": "text e voiceId obrigatórios."}), 400

    try:
        normalized_text = sanitize_and_normalize_text(text)
        chunks = split_text_into_chunks(normalized_text)
        print(f"[INFO] Texto: {len(normalized_text)} chars | {len(chunks)} chunks")

        client = genai.Client(api_key=API_KEY)
        model = "gemini-2.5-pro-preview-tts"
        final_audio = None

        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) == 0: continue
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

            full_data = bytearray()
            success = False
            for attempt in range(MAX_RETRIES):
                try:
                    stream = client.models.generate_content_stream(model=model, contents=contents, config=config)
                    for response in stream:
                        if response.candidates and response.candidates[0].content.parts:
                            part = response.candidates[0].content.parts[0]
                            if part.inline_data and part.inline_data.
                                full_data.extend(part.inline_data.data)
                    if full_data:
                        success = True
                        break
                except Exception as e:
                    print(f"[TENTATIVA {attempt+1}] Erro no stream: {e}")
                    if attempt < MAX_RETRIES - 1: gc.collect()

            if not success or not full_data:
                print(f"[FALHA] Chunk {i+1} não gerou áudio.")
                continue

            try:
                wav_data = convert_to_wav(bytes(full_data), "audio/L16;rate=24000")
               