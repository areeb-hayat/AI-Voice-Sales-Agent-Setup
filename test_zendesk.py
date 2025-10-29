from app.services.zendesk_client import ZendeskClient

zendesk_client = ZendeskClient()

subject = "Test AI Call Ticket"
description = "This is a test ticket. Transcript: Hello, I want to buy a painting. Summary: Customer is interested in 'Sunset Painting'."
requester_email = "customer@example.com"

ticket = zendesk_client.create_ticket(
    subject=subject,
    description=description,
    requester_email=requester_email,
    tags=["inbound", "ai-call"]
)

print("Zendesk ticket created:", ticket["ticket"]["id"])
