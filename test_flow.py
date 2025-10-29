# test_flow.py
import asyncio
import websockets
import json
import base64
import numpy as np
import sounddevice as sd
import soundfile as sf

# -----------------------------
# μ-law → PCM decoder
# -----------------------------
def mulaw_to_linear_float(mulaw_bytes: bytes) -> np.ndarray:
    """Convert μ-law bytes to float32 PCM in range [-1.0, 1.0]."""
    mu_law = np.frombuffer(mulaw_bytes, dtype=np.uint8)
    mu_law = np.bitwise_xor(mu_law, 0xFF)
    sign = np.bitwise_and(mu_law, 0x80)
    exponent = np.bitwise_and(mu_law, 0x70) >> 4
    mantissa = np.bitwise_and(mu_law, 0x0F)
    magnitude = ((mantissa << 4) + 8) << (exponent + 2)
    pcm = magnitude.astype(np.int16)
    pcm[sign != 0] = -pcm[sign != 0]

    # Convert to float32 in [-1.0, 1.0]
    pcm_float = pcm.astype(np.float32) / 32768.0
    return pcm_float

# -----------------------------
# WebSocket test flow
# -----------------------------
async def test_flow():
    ws_url = "wss://uncatenated-sherrell-diminishingly.ngrok-free.dev/api/twilio/media-stream"  

    async with websockets.connect(ws_url) as websocket:
        print("🔌 Connected to WebSocket")

        # Send fake START event to simulate Twilio call
        start_event = {
            "event": "start",
            "start": {
                "callSid": "TESTCALL123",
                "streamSid": "STREAM123",
                "from": "+1234567890",
                "to": "+13614507995",
                "customParameters": {
                    "caller_email": "test@example.com"
                }
            }
        }
        await websocket.send(json.dumps(start_event))
        print("📨 Sent START event")

        # Wait for greeting audio from AI
        while True:
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=15)
            except asyncio.TimeoutError:
                print("⏱️ Timeout waiting for audio")
                break

            data = json.loads(message)
            if data.get("event") == "media":
                payload = data.get("media", {}).get("payload")
                if payload:
                    audio_bytes = base64.b64decode(payload)
                    pcm_float = mulaw_to_linear_float(audio_bytes)

                    # Play audio
                    sd.play(pcm_float, samplerate=8000)
                    sd.wait()
                    print("🔊 Greeting played!")

                    # Save to WAV file
                    sf.write("ai_greeting.wav", pcm_float, 8000, subtype="PCM_16")
                    print("💾 Greeting saved as 'ai_greeting.wav'")
                    break

        print("✅ Test flow complete")

# -----------------------------
# Run the test
# -----------------------------
if __name__ == "__main__":
    asyncio.run(test_flow())
