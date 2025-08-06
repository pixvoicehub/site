# app.py - VERSÃO FINAL CORRIGIDA E OTIMIZADA PARA RENDER GRATUITO

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
    raise ValueError("ERRO CRÍTICO: A chave da API do Gemini (GEMINI_API_KEY) não está definida.")

# --- Funções de Suporte ---

def sanitize_and_normalize_text(text):
    """Limpa e normaliza o texto para melhorar a síntese de fala."""
    if not isinstance(text, str):
        text = str(text)
    # Substitui moedas, X por 'vezes', etc.
    text = re.sub(r'R\$\s*([\d,.]+)', lambda m: m.group(1).replace('.', '').replace(',', ' vírgula ') + ' reais', text)
    text = re.sub(r'(\d+)\s*[xX](?!\w)', r'\1 vezes ', text)
    text = re.sub(r'\s*[-–—]\s*', ', ', text)
    text = re.sub(r'(!+)', '!', text)
    text = re.sub(r'(\?+)', '?', text)
    text = re.sub(r'(\.+)', '.', text)
    text = re.sub(r'[^\w\s.,!?áéíóúâêîôûãõàèìòùçÁÉÍÓÚÂÊÎÔÛÃÕÀÈÌÒÙÇ]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def split_text_into_chunks(text, max_chars=400):
    """
    Divide o texto em chunks menores, respeitando os limites do modelo TTS.
    Prioriza quebras em frases completas.
    """
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        # Se a frase já é muito longa, forçamos a quebra
        if len(sentence) > max_chars:
            while len(sentence) > max_chars:
                chunk_part = sentence[:max_chars]
                # Evita cortar no meio de uma palavra
                last_space = chunk_part.rfind(' ')
                if last_space > 0:
                    chunk_part = sentence[:last_space]
                    sentence = sentence[last_space:].strip()
                else:
                    sentence = sentence[max_chars:].strip()
                chunks.append(chunk_part)
            if sentence:
                current_chunk = sentence + " "
        else:
            if len(current_chunk) + len(sentence) + 1 <= max_chars:
                current_chunk += sentence + " "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + " "
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks


def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Converte dados de áudio cru em formato WAV com cabeçalho válido."""
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
        b"RIFF", chunk_size, b"WAVE", b"fmt ", 16,
        1, num_channels, sample_rate, byte_rate,
        block_align, bits_per_sample, b"data", data_size
    )
    return header + audio_data


def parse_audio_mime_type(mime_type: str) -> dict:
    """Extrai informações de taxa de amostragem e bits do MIME type."""
    rate = 24000
    bits_per_sample = 16
    if mime_type:
        parts = mime_type.split(";")
        for param in parts:
            param = param.strip()
            if param.lower().startswith("rate="):
                try:
                    rate = int(param.split("=", 1)[1])
                except (ValueError, IndexError):
                    pass
    return {"bits_per_sample": bits_per_sample, "rate": rate}


# --- Rota da API ---

@app.route('/')
def home():
    return "Serviço de Narração está online (v8.0 - Corrigido e Otimizado)."


@app.route('/health')
def health_check():
    return "API de Narração está saudável.", 200


@app.route('/generate-narration', methods=['POST'])
def generate_narration():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Requisição JSON inválida."}), 400

    text_to_speak = data.get('text')
    voice_id = data.get('voiceId')

    if not text_to_speak or not voice_id:
        return jsonify({"error": "Os campos 'text' e 'voiceId' são obrigatórios."}), 400

    try:
        # Normaliza o texto
        normalized_text = sanitize_and_normalize_text(text_to_speak)
        print(f"[INFO] Texto recebido: {len(normalized_text)} caracteres")

        # Divide em chunks
        chunks = split_text_into_chunks(normalized_text, max_chars=400)
        print(f"[INFO] Texto dividido em {len(chunks)} partes.")

        if not chunks:
            return jsonify({"error": "Texto processado resultou em nenhum conteúdo válido."}), 400

        # Configuração do modelo
        client = genai.Client(api_key=API_KEY)
        model_name = "gemini-2.5-pro-preview-tts"
        generation_config = types.GenerateContentConfig(
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_id)
                )
            )
        )

        # Armazena todos os áudios gerados
        all_audio_segments = []

        for i, chunk_text in enumerate(chunks):
            print(f"[CHUNK {i+1}/{len(chunks)}] Gerando áudio... ({len(chunk_text)} caracteres)")
            contents = [types.Content(role="user", parts=[types.Part.from_text(text=chunk_text)])]
            try:
                stream = client.models.generate_content_stream(
                    model=model_name,
                    contents=contents,
                    config=generation_config
                )
                full_audio_data = bytearray()
                audio_mime_type = "audio/L16;rate=24000"

                for response in stream:
                    if response.candidates and response.candidates[0].content.parts:
                        part = response.candidates[0].content.parts[0]
                        if part.inline_data and part.inline_data.data:
                            full_audio_data.extend(part.inline_data.data)
                            if part.inline_data.mime_type:
                                audio_mime_type = part.inline_data.mime_type

                if not full_audio_data:
                    print(f"[AVISO] Nenhum áudio gerado para o chunk {i+1}.")
                    continue

                # Converte para WAV e depois para AudioSegment
                wav_data = convert_to_wav(bytes(full_audio_data), audio_mime_type)
                audio_segment = AudioSegment.from_file(io.BytesIO(wav_data), format="wav")
                all_audio_segments.append(audio_segment)

                # Pequeno silêncio entre frases (100ms) para naturalidade
                all_audio_segments.append(AudioSegment.silent(duration=100))

                # Libera memória
                del full_audio_data, wav_data, audio_segment
                gc.collect()

            except Exception as e:
                print(f"[ERRO] Falha ao gerar áudio para chunk {i+1}: {e}")
                return jsonify({"error": f"Erro ao gerar áudio (parte {i+1}): {str(e)}"}), 500

        # Verifica se foi gerado algum áudio
        if not all_audio_segments:
            return jsonify({"error": "Nenhum áudio foi gerado para o texto fornecido."}), 500

        # Concatena todos os segmentos
        final_audio = sum(all_audio_segments)  # concatena todos os segments

        # Exporta para MP3 em memória
        mp3_buffer = io.BytesIO()
        final_audio.export(mp3_buffer, format="mp3", bitrate="128k")  # bitrate menor para economizar memória
        mp3_data = mp3_buffer.getvalue()

        # Libera memória
        del final_audio, mp3_buffer
        gc.collect()

        # Codifica em base64
        audio_base64 = base64.b64encode(mp3_data).decode('utf-8')

        print(f"[SUCESSO] Áudio final gerado com {len(mp3_data)} bytes.")
        return jsonify({"audioContent": audio_base64})

    except Exception as e:
        print(f"ERRO INESPERADO NO SERVIDOR: {e}")
        return jsonify({"error": f"Erro interno: {e}"}), 500


# --- Execução Local ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Render usa a variável PORT
    app.run(debug=False, host='0.0.0.0', port=port)