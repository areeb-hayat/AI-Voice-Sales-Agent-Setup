#!/usr/bin/env python3
"""
Quick test script to verify your AI Voice Agent setup.
Run this before making actual calls to catch configuration issues.
"""

import os
import sys
from dotenv import load_dotenv
import asyncio
import httpx

load_dotenv()

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.END}")

def print_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.END}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.END}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.END}")

def check_env_vars():
    """Check if all required environment variables are set"""
    print_info("Checking environment variables...")
    
    required_vars = {
        'OPENAI_API_KEY': 'OpenAI API Key',
        'ELEVENLABS_API_KEY': 'ElevenLabs API Key',
        'ELEVENLABS_VOICE_ID': 'ElevenLabs Voice ID',
        'TWILIO_ACCOUNT_SID': 'Twilio Account SID',
        'TWILIO_AUTH_TOKEN': 'Twilio Auth Token',
        'TWILIO_PHONE_NUMBER': 'Twilio Phone Number',
        'WEBSOCKET_URL': 'WebSocket URL',
        'SUPABASE_URL': 'Supabase URL',
        'SUPABASE_KEY': 'Supabase Key',
    }
    
    missing = []
    for var, name in required_vars.items():
        value = os.getenv(var)
        if not value:
            print_error(f"{name} ({var}) is missing")
            missing.append(var)
        else:
            print_success(f"{name}: {value[:20]}...")
    
    if missing:
        print_error(f"Missing {len(missing)} required environment variables")
        return False
    
    print_success("All environment variables present")
    return True

def check_websocket_url():
    """Verify WebSocket URL format"""
    print_info("Checking WebSocket URL format...")
    
    ws_url = os.getenv('WEBSOCKET_URL', '')
    
    if not ws_url.startswith('wss://'):
        print_error("WebSocket URL must start with 'wss://'")
        return False
    
    if '/api/twilio/media-stream' not in ws_url:
        print_error("WebSocket URL must include '/api/twilio/media-stream' path")
        print_warning(f"Current URL: {ws_url}")
        print_info("Should be: wss://your-domain.ngrok-free.dev/api/twilio/media-stream")
        return False
    
    print_success(f"WebSocket URL format correct: {ws_url}")
    return True

def check_python_version():
    """Check Python version for audioop compatibility"""
    print_info("Checking Python version...")
    
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print_error(f"Python {version_str} is too old. Need Python 3.8+")
        return False
    
    if version.major == 3 and version.minor >= 13:
        print_warning(f"Python {version_str} detected - audioop module may not be available")
        print_info("NumPy-based μ-law conversion is used instead.")
    else:
        print_success(f"Python {version_str} is compatible")
    
    return True

def check_imports():
    """Check if required packages are installed"""
    print_info("Checking required packages...")
    
    packages = {
        'fastapi': 'FastAPI',
        'uvicorn': 'Uvicorn',
        'twilio': 'Twilio',
        'openai': 'OpenAI',
        'httpx': 'HTTPX',
        'supabase': 'Supabase',
        'numpy': 'NumPy (for μ-law conversion)',
        'pydub': 'Pydub (optional for audio files)'
    }
    
    missing = []
    for package, name in packages.items():
        try:
            __import__(package)
            print_success(f"{name} installed")
        except ImportError:
            if package == "pydub":
                print_warning(f"{name} NOT installed (optional, can skip if using NumPy audio conversion)")
            else:
                print_error(f"{name} NOT installed")
                missing.append(package)
    
    if missing:
        print_error(f"Missing {len(missing)} required packages")
        print_info(f"Install with: pip install {' '.join(missing)}")
        return False
    
    print_success("All required packages installed (or optional missing)")
    return True

async def check_server_running():
    """Check if the FastAPI server is running"""
    print_info("Checking if server is running...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health", timeout=5.0)
            if response.status_code == 200:
                print_success("Server is running and responding")
                return True
            else:
                print_error(f"Server returned status {response.status_code}")
                return False
    except Exception as e:
        print_error("Server is NOT running")
        print_info("Start server with: python -m uvicorn main:app --reload")
        return False

async def check_webhook_endpoint():
    """Check if webhook endpoint is accessible"""
    print_info("Checking webhook endpoint...")
    
    ws_url = os.getenv('WEBSOCKET_URL', '')
    if not ws_url:
        print_error("WEBSOCKET_URL not set")
        return False
    
    base_url = ws_url.replace('wss://', 'https://').replace('/api/twilio/media-stream', '')
    webhook_url = f"{base_url}/api/twilio/webhook/voice"
    
    print_info(f"Testing: {webhook_url}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                data={
                    "From": "+1234567890",
                    "To": os.getenv('TWILIO_PHONE_NUMBER', '+10000000000'),
                    "CallSid": "TEST123"
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                if '<Response>' in response.text:
                    print_success("Webhook endpoint responding with valid TwiML")
                    return True
                else:
                    print_error("Webhook responded but no TwiML found")
                    return False
            else:
                print_error(f"Webhook returned status {response.status_code}")
                return False
    except Exception as e:
        print_error(f"Cannot reach webhook: {e}")
        print_warning("Make sure ngrok is running and WEBSOCKET_URL is correct")
        return False

def print_summary(results):
    """Print test summary"""
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test}")
    
    print("="*60)
    print(f"Results: {passed}/{total} tests passed")
    print("="*60 + "\n")
    
    if passed == total:
        print_success("🎉 All checks passed! You're ready to make calls.")
        print_info("Next step: Call your Twilio number to test")
    else:
        print_warning("⚠️  Some checks failed or are optional. Fix critical issues before testing.")

async def main():
    """Run all checks"""
    print("\n" + "="*60)
    print("AI VOICE SALES AGENT - PRE-FLIGHT CHECKS")
    print("="*60 + "\n")
    
    results = {}
    
    results['Environment Variables'] = check_env_vars()
    results['WebSocket URL Format'] = check_websocket_url()
    results['Python Version'] = check_python_version()
    results['Required Packages'] = check_imports()
    # audioop check is now only informative
    results['Audioop Module'] = True
    results['Server Running'] = await check_server_running()
    results['Webhook Endpoint'] = await check_webhook_endpoint()
    
    print_summary(results)

if __name__ == "__main__":
    asyncio.run(main())
