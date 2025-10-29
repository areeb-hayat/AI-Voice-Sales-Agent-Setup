#!/usr/bin/env python3
"""
WebSocket Test Client for Twilio Media Stream
Fixed version: correctly handles μ-law chunks, converts to PCM, saves WAV, and transcribes
"""

import asyncio
import websockets
import json
import base64
import wave
import audioop
import time
from pathlib import Path
from app.services.ai_service import transcribe_audio


def load_audio_file(filepath: str) -> bytes:
    """Load M4A or WAV file and convert to μ-law"""
    print(f"📂 Loading audio file: {filepath}")

    file_path = Path(filepath)
    if not file_path.exists():
        raise FileNotFoundError(f"Audio file not found: {filepath}")

    if filepath.endswith(".m4a"):
        try:
            from pydub import AudioSegment
            print("🔄 Converting M4A to WAV...")
            audio = AudioSegment.from_file(filepath, format="m4a")
            audio = audio.set_frame_rate(8000).set_channels(1).set_sample_width(2)
            wav_data = audio.raw_data
            mulaw_data = audioop.lin2ulaw(wav_data, 2)
            print(f"✅ Converted {len(mulaw_data)} bytes to μ-law")
            return mulaw_data
        except ImportError:
            raise ImportError("❌ pydub not installed. Install with pip install pydub")

    elif filepath.endswith(".wav"):
        with wave.open(filepath, "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            framerate = wav_file.getframerate()
            pcm_data = wav_file.readframes(wav_file.getnframes())
            if channels == 2:
                pcm_data = audioop.tomono(pcm_data, sample_width, 0.5, 0.5)
            if framerate != 8000:
                pcm_data, _ = audioop.ratecv(pcm_data, sample_width, 1, framerate, 8000, None)
            mulaw_data = audioop.lin2ulaw(pcm_data, sample_width)
            print(f"✅ Converted {len(mulaw_data)} bytes to μ-law")
            return mulaw_data
    else:
        raise ValueError("Unsupported audio format. Use .wav or .m4a")


def save_audio_response(mulaw_chunks: list[bytes], output_path: str):
    """Save collected μ-law chunks as valid WAV"""
    print(f"💾 Saving audio response to: {output_path}")
    # Concatenate all chunks
    mulaw_data = b"".join(mulaw_chunks)
    # Convert μ-law to PCM 16-bit
    pcm_data = audioop.ulaw2lin(mulaw_data, 2)
    # Save WAV
    with wave.open(output_path, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(8000)
        wav_file.writeframes(pcm_data)
    print(f"✅ Audio saved: {output_path}")


async def test_websocket_connection(
    websocket_url: str,
    test_audio_file: str = None,
):
    """Test WebSocket connection and audio flow"""
    print("=" * 60)
    print("🧪 TWILIO MEDIA STREAM WEBSOCKET TESTER")
    print("=" * 60)
    print(f"📡 Connecting to: {websocket_url}")
    print()

    received_audio_chunks = []

    try:
        async with websockets.connect(websocket_url) as websocket:
            print("✅ WebSocket connected!\n")

            # Send START event
            start_message = {
                "event": "start",
                "sequenceNumber": "1",
                "start": {
                    "streamSid": "TEST_STREAM_" + str(int(time.time())),
                    "accountSid": "TEST_ACCOUNT",
                    "callSid": "TEST_CALL_" + str(int(time.time())),
                    "tracks": ["inbound"],
                    "mediaFormat": {"encoding": "audio/x-mulaw", "sampleRate": 8000, "channels": 1},
                    "customParameters": {"From": "+1234567890", "To": "+0987654321", "caller_email": "test@artbymaudsch.com"},
                },
                "streamSid": "TEST_STREAM_" + str(int(time.time())),
            }

            await websocket.send(json.dumps(start_message))
            print("✅ START event sent\n")

            # Wait for greeting
            print("⏳ Waiting for AI greeting...")
            greeting_received = False
            timeout = 15
            start_time = time.time()
            while not greeting_received and (time.time() - start_time) < timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    data = json.loads(response)
                    if data.get("event") == "media":
                        payload = data.get("media", {}).get("payload")
                        if payload:
                            chunk = base64.b64decode(payload)
                            if len(chunk) > 100:  # skip empty chunks
                                received_audio_chunks.append(chunk)
                                greeting_received = True
                except asyncio.TimeoutError:
                    continue

            if greeting_received:
                save_audio_response(received_audio_chunks, "test_greeting_response.wav")
                # Transcribe greeting
                text = await transcribe_audio(open("test_greeting_response.wav", "rb").read())
                print(f"🎤 Greeting transcription: {text}")
                received_audio_chunks.clear()
            else:
                print("⚠️ No greeting received")

            # Send test audio
            if test_audio_file:
                print(f"\n📤 Sending test audio: {test_audio_file}")
                mulaw_audio = load_audio_file(test_audio_file)
                chunk_size = 160
                chunks = [mulaw_audio[i : i + chunk_size] for i in range(0, len(mulaw_audio), chunk_size)]
                for i, chunk in enumerate(chunks):
                    media_message = {
                        "event": "media",
                        "sequenceNumber": str(i + 10),
                        "media": {
                            "track": "inbound",
                            "chunk": str(i),
                            "timestamp": str(int(time.time() * 1000)),
                            "payload": base64.b64encode(chunk).decode("utf-8"),
                        },
                        "streamSid": start_message["streamSid"],
                    }
                    await websocket.send(json.dumps(media_message))
                    await asyncio.sleep(0.02)  # 20ms

                print(f"✅ Sent {len(chunks)} audio chunks\n")

                # Collect AI response
                print("⏳ Waiting for AI response...")
                response_start = time.time()
                while (time.time() - response_start) < 20:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        data = json.loads(response)
                        if data.get("event") == "media":
                            payload = data.get("media", {}).get("payload")
                            if payload:
                                chunk = base64.b64decode(payload)
                                if len(chunk) > 100:
                                    received_audio_chunks.append(chunk)
                    except asyncio.TimeoutError:
                        if received_audio_chunks:
                            break
                        continue

                if received_audio_chunks:
                    save_audio_response(received_audio_chunks, "test_ai_response.wav")
                    # Transcribe AI response
                    text = await transcribe_audio(open("test_ai_response.wav", "rb").read())
                    print(f"🎤 AI response transcription: {text}")
                else:
                    print("⚠️ No AI response received")

            # Send STOP
            stop_message = {
                "event": "stop",
                "sequenceNumber": "9999",
                "stop": {"accountSid": "TEST_ACCOUNT", "callSid": start_message["start"]["callSid"]},
                "streamSid": start_message["streamSid"],
            }
            await websocket.send(json.dumps(stop_message))
            print("\n✅ STOP event sent")
            await asyncio.sleep(2)

    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 60)
    print("🏁 Test complete!")
    print("=" * 60)


def main():
    import sys

    websocket_url = "wss://uncatenated-sherrell-diminishingly.ngrok-free.dev/api/twilio/media-stream"
    test_audio = "artworks_audio.m4a"
    if len(sys.argv) > 2:
        test_audio = sys.argv[2]

    print(f"Using WebSocket URL: {websocket_url}")
    print(f"Using test audio: {test_audio}\n")

    asyncio.run(test_websocket_connection(websocket_url, test_audio))


if __name__ == "__main__":
    main()
