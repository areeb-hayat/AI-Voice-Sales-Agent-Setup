#!/usr/bin/env python3
"""
Enhanced Fake Call Simulator for AI Voice Agent
Simulates a live call over WebSocket with your Twilio media-stream endpoint.
Prints AI responses in real-time.

IMPORTANT: This uses synthetic audio. For realistic testing:
1. Record actual speech samples
2. Use a real phone call via Twilio
3. Test with longer audio chunks (increase PROCESS_INTERVAL to 7-10 seconds)
"""

import asyncio
import websockets
import json
import base64
import numpy as np
import time
import wave
import io

# -------------------------------
# CONFIGURATION
# -------------------------------
WEBSOCKET_URL = "wss://uncatenated-sherrell-diminishingly.ngrok-free.dev/api/twilio/media-stream"
CALL_SID = f"SIM_TEST_{int(time.time())}"
STREAM_SID = "SIM_STREAM_001"
FROM_NUMBER = "+1234567890"
TO_NUMBER = "+13614507995"
TEST_EMAIL = "customer@example.com"  # Use real customer email for testing
SAMPLE_RATE = 8000
MU = 255

# Longer audio chunks for better transcription
CHUNK_DURATION = 8.0  # seconds (increased from 6.0)

# -------------------------------
# AUDIO UTILS
# -------------------------------
def linear_to_mulaw(pcm_bytes: bytes, mu: int = MU) -> bytes:
    """Convert 16-bit PCM to μ-law - Production quality"""
    try:
        if len(pcm_bytes) == 0:
            return b""
        
        if len(pcm_bytes) % 2 != 0:
            pcm_bytes = pcm_bytes[:-1]
        
        pcm = np.frombuffer(pcm_bytes, dtype=np.int16)
        BIAS = 0x84
        CLIP = 32635

        sign = (pcm < 0)
        magnitude = np.abs(pcm).astype(np.int32)
        magnitude = np.minimum(magnitude, CLIP)
        magnitude = magnitude + BIAS

        exponent = np.zeros(len(magnitude), dtype=np.int32)
        temp = magnitude.copy()
        for exp_val in range(7, -1, -1):
            mask = (temp >= (256 << exp_val)) & (exponent == 0)
            exponent[mask] = exp_val

        mantissa = (magnitude >> (exponent + 3)) & 0x0F
        mulaw = ~((sign.astype(np.int32) << 7) | (exponent << 4) | mantissa)
        mulaw = mulaw & 0xFF
        return mulaw.astype(np.uint8).tobytes()

    except Exception as e:
        print(f"❌ μ-law encode error: {e}")
        return b''

def generate_silence(duration_sec: float = 2.0, sample_rate: int = SAMPLE_RATE) -> bytes:
    """Generate silent PCM bytes for realistic pauses"""
    samples = int(duration_sec * sample_rate)
    silence = np.zeros(samples, dtype=np.int16)
    return silence.tobytes()

def text_to_fake_pcm(text: str, duration_sec: float = 8.0, sample_rate: int = SAMPLE_RATE) -> bytes:
    """
    Convert text to fake PCM waveform with multiple frequencies.
    
    NOTE: This is still synthetic and Whisper will likely hallucinate.
    For real testing, use actual recorded audio or make a live call.
    """
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    
    # Mix multiple frequencies to simulate speech patterns
    audio = (
        0.05 * np.sin(2 * np.pi * 440 * t) +  # Base tone
        0.03 * np.sin(2 * np.pi * 880 * t) +  # Harmonic
        0.02 * np.sin(2 * np.pi * 220 * t) +  # Lower frequency
        0.01 * np.random.randn(len(t))        # Noise
    )
    
    # Add amplitude modulation to simulate speech cadence
    modulation = 0.5 + 0.5 * np.sin(2 * np.pi * 3 * t)
    audio = audio * modulation
    
    pcm = (audio * 8000).astype(np.int16)  # Lower amplitude
    return pcm.tobytes()

# -------------------------------
# MAIN SIMULATOR
# -------------------------------
async def fake_call():
    print(f"🔗 Connecting to: {WEBSOCKET_URL}")
    print(f"⚠️  NOTE: Using synthetic audio - expect hallucinations!")
    print(f"⚠️  For real testing: Use actual phone call or recorded audio\n")
    
    async with websockets.connect(WEBSOCKET_URL) as ws:
        print("🔌 Connected to media-stream WebSocket\n")

        ai_response_count = 0
        
        # Listener for AI responses
        async def listen():
            nonlocal ai_response_count
            try:
                while True:
                    data = await ws.recv()
                    obj = json.loads(data)
                    if obj.get("event") == "media" and "media" in obj:
                        ai_response_count += 1
                        payload_len = len(obj["media"]["payload"])
                        print(f"🤖 AI Response #{ai_response_count} received ({payload_len} bytes)")
            except websockets.exceptions.ConnectionClosed:
                print("🔌 Listener closed")
            except Exception as e:
                print(f"⚠️ Listener error: {e}")

        listener_task = asyncio.create_task(listen())

        # 1. Send START event
        print("📤 Sending START event...")
        await ws.send(json.dumps({
            "event": "start",
            "start": {
                "callSid": CALL_SID,
                "streamSid": STREAM_SID,
                "from": FROM_NUMBER,
                "to": TO_NUMBER,
                "customParameters": {"caller_email": TEST_EMAIL}
            }
        }))
        print("✅ Start event sent\n")
        
        await asyncio.sleep(3)  # Wait for greeting

        # 2. Simulate user phrases with longer duration
        user_phrases = [
            ("Hello, I'm calling about my recent order", CHUNK_DURATION),
            ("Can you check the status of my shipment please?", CHUNK_DURATION),
            ("Thank you so much for your help today", CHUNK_DURATION)
        ]

        for i, (phrase, wait_time) in enumerate(user_phrases, 1):
            print(f"\n👤 User utterance #{i}: '{phrase}'")
            print(f"   ⚠️  Sending {wait_time}s of synthetic audio (will likely be misunderstood)")
            
            pcm_audio = text_to_fake_pcm(phrase, duration_sec=wait_time)
            mulaw_audio = linear_to_mulaw(pcm_audio)

            # Send audio chunks (simulate streaming)
            chunk_size = 640  # 80ms chunks at 8kHz
            for j in range(0, len(mulaw_audio), chunk_size):
                chunk = mulaw_audio[j:j+chunk_size]
                await ws.send(json.dumps({
                    "event": "media",
                    "streamSid": STREAM_SID,
                    "media": {"payload": base64.b64encode(chunk).decode("utf-8")}
                }))
                await asyncio.sleep(0.02)  # 20ms between chunks
            
            print(f"📤 Sent {len(mulaw_audio)} bytes of audio")
            print(f"⏳ Waiting {wait_time + 2}s for AI response...")
            await asyncio.sleep(wait_time + 2)

        # 3. Final wait before stopping
        print("\n⏳ Waiting for final AI response...")
        await asyncio.sleep(4)

        # 4. Send STOP event
        print("\n📤 Sending STOP event...")
        await ws.send(json.dumps({
            "event": "stop",
            "stop": {"callSid": CALL_SID}
        }))
        print("✅ Stop event sent")

        await asyncio.sleep(2)
        listener_task.cancel()
        
        print(f"\n🏁 Call simulation complete")
        print(f"📊 Total AI responses received: {ai_response_count}")
        print(f"\n💡 TIP: For accurate testing:")
        print(f"   1. Make a real phone call to your Twilio number")
        print(f"   2. Or record actual speech and modify this script to send it")
        print(f"   3. Check your database for the conversation transcript")

if __name__ == "__main__":
    asyncio.run(fake_call())