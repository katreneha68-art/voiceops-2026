# -*- coding: utf-8 -*-
"""
Created on Thu Oct 22 01:35:47 2026

@author: HP
"""

import os
import requests

from voiceops_rag import respond

api_key = os.environ.get("GNANI_API_KEY")

audio_path = r"C:\Users\HP\OneDrive\Documents\Sound Recordings\test_audio.m4a.m4a"
if not api_key:
    print("Gnani API key not found. Restart Spyder and check the environment variable.")

elif not os.path.exists(audio_path):
    print("Audio file not found. Please check the audio file path.")

else:
    url = "https://api.vachana.ai/stt/v3"

    headers = {
        "X-API-Key-ID": api_key
    }

    data = {
        "language_code": "en-IN",
        "format": "transcribe"
    }

    try:
        with open(audio_path, "rb") as audio:
            files = {
                "audio_file": (os.path.basename(audio_path), audio)
            }

            response = requests.post(
                url,
                headers=headers,
                data=data,
                files=files,
                timeout=60
            )

        print("Status code:", response.status_code)
        print("Response:", response.text)

        if response.ok:
            result = response.json()
            transcript = result.get("transcript", "").strip()

            print("\nRecognized text:")
            print(transcript)
          
    except Exception as error:
        print("Error:", error)
        
 # ---------- GNANI TEXT-TO-SPEECH TEST ----------

import os
import requests
import base64
import json

api_key = os.environ.get("GNANI_API_KEY")

# STT se mila customer question
question = transcript

print("Customer:", question)

# Gemini RAG se answer lo
answer, sources = respond(question)

print("Assistant:", answer)

# TTS ko Gemini ka answer do
text_to_speak = answer
url = "https://api.vachana.ai/api/v1/tts/sse"

headers = {
    "X-API-Key-ID": api_key,
    "Content-Type": "application/json",
    "Accept": "text/event-stream"
}

payload = {
    "text": text_to_speak,
    "voice": "Nalini",
    "model": "timbre-v2.5",
    "language": "en-IN",
    "speed": 1.0,
    "audio_config": {
        "sample_rate": 48000,
        "num_channels": 1,
        "sample_width": 2,
        "encoding": "linear_pcm",
        "container": "wav"
    }
}

if not api_key:
    print("Gnani API key not found. Restart Spyder and check the key.")
else:
    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            stream=True,
            timeout=120
        )

        print("TTS Status code:", response.status_code)

        if response.status_code == 200:
            output_path = os.path.join(
                os.path.expanduser("~"),
                "Documents",
                "zentromart_voice.wav"
            )

            audio_chunks = []

            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue

                if isinstance(line, bytes):
                    line = line.decode("utf-8")

                if line.startswith("data:"):
                    data = json.loads(line[5:].strip())

                    if data.get("audio"):
                        audio_chunks.append(
                            base64.b64decode(data["audio"])
                        )

                    if data.get("status") == "error" or data.get("error"):
                        print("TTS error:", data)
                        break

            if audio_chunks:
                with open(output_path, "wb") as audio_file:
                    for chunk in audio_chunks:
                        audio_file.write(chunk)

                print("Audio saved successfully!")
                print("File location:", output_path)
            else:
                print("No audio received. Check the API response.")

        else:
            print("TTS request failed:")
            print(response.text[:1000])

    except Exception as error:
        print("TTS error:", error)       