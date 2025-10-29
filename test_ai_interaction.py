import asyncio
from app.services.ai_service import generate_ai_response_live
from app.services.shopify_client import ShopifyClient


async def test_ai():
    shopify_client = ShopifyClient()

    # Simulated conversation transcript
    transcript_buffer = "Hello, I want to check if the 'Sunset Painting' is available and the shipping time."

    caller_email = "customer@example.com"

    # Generate AI response
    audio_bytes = await generate_ai_response_live(
        transcript_buffer,
        caller_email=caller_email,
        shopify_client=shopify_client
    )

    # Save AI audio to file to listen
    with open("ai_response.wav", "wb") as f:
        f.write(audio_bytes)

    print("AI response audio saved as ai_response.wav")
    print("You can play it to hear how the AI responds.")

if __name__ == "__main__":
    asyncio.run(test_ai())
