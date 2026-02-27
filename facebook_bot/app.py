"""
Facebook Messenger Bot - FastAPI Webhook Server
Receives webhook events from Facebook Messenger Platform
"""
import os
import logging
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import uvicorn
from facebook_bot.config import VERIFY_TOKEN, PAGE_ACCESS_TOKEN
from facebook_bot.messenger_bot import MessengerBot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Facebook Messenger Bot")
messenger_bot = MessengerBot()


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "Facebook Messenger Bot is running", "version": "1.0"}


@app.get("/webhook")
async def verify_webhook(request: Request):
    """
    Facebook webhook verification endpoint.
    Facebook sends GET request with hub.mode, hub.verify_token, hub.challenge
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("Webhook verified successfully!")
        return Response(content=challenge, media_type="text/plain")
    else:
        logger.warning("Webhook verification failed")
        return Response(status_code=403)


@app.post("/webhook")
async def webhook(request: Request):
    """
    Main webhook endpoint for receiving Facebook events.
    Events include: messages, messaging_postbacks, feed comments
    """
    try:
        body = await request.json()

        # Verify it's a page subscription
        if body.get("object") != "page":
            return Response(status_code=404)

        # Process each entry
        for entry in body.get("entry", []):
            # Handle messaging events (DMs)
            if "messaging" in entry:
                for event in entry["messaging"]:
                    await handle_messaging_event(event)

            # Handle feed/comment events
            if "changes" in entry:
                for change in entry["changes"]:
                    await handle_feed_event(change)

        # Always return 200 OK quickly to avoid Facebook retries
        return Response(status_code=200)

    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return Response(status_code=200)  # Still return 200 to avoid retries


async def handle_messaging_event(event: dict):
    """Route messaging events to appropriate handlers"""
    sender_id = event.get("sender", {}).get("id")
    recipient_id = event.get("recipient", {}).get("id")

    # Ignore messages sent by the page itself
    if sender_id == recipient_id:
        return

    # Handle message
    if "message" in event:
        message = event["message"]

        # Handle postback buttons (Get Started, Quick Replies with payload)
        if "quick_reply" in message:
            payload = message["quick_reply"]["payload"]
            await messenger_bot.handle_postback(sender_id, payload)

        # Handle text message
        elif "text" in message:
            text = message["text"]
            await messenger_bot.handle_message(sender_id, text)

        # Handle attachments (images, files, location)
        elif "attachments" in message:
            await messenger_bot.handle_attachment(sender_id, message["attachments"])

    # Handle postback (button clicks)
    elif "postback" in event:
        payload = event["postback"]["payload"]
        await messenger_bot.handle_postback(sender_id, payload)

    # Handle read receipts (optional)
    elif "read" in event:
        logger.debug(f"User {sender_id} read messages")


async def handle_feed_event(change: dict):
    """Handle page feed events (new comments, likes, etc.)"""
    field = change.get("field")
    value = change.get("value")

    if field == "feed" and value:
        item = value.get("item")
        verb = value.get("verb")

        # Handle new comment on post
        if item == "comment" and verb == "add":
            comment_id = value.get("comment_id")
            post_id = value.get("post_id")
            sender_id = value.get("sender_id")
            message = value.get("message", "")

            await messenger_bot.handle_comment(
                post_id=post_id,
                comment_id=comment_id,
                commenter_id=sender_id,
                comment_text=message
            )


@app.on_event("startup")
async def startup_event():
    """Initialize bot on startup"""
    logger.info("Starting Facebook Messenger Bot...")
    logger.info(f"Webhook verify token: {VERIFY_TOKEN[:10]}...")
    logger.info(f"Page access token configured: {bool(PAGE_ACCESS_TOKEN)}")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
