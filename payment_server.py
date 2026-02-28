"""
Simple Flask server to serve payment success/cancel pages
This server provides the HTML pages that auto-close the Telegram webview
Also handles Stripe webhooks for subscription events
"""
from flask import Flask, render_template, request, jsonify
import os
import stripe
import asyncio
import logging
from datetime import datetime
from bot_database_postgres import BotDatabase
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize
app = Flask(__name__, static_folder='static', template_folder='static')
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
PAYMENT_SERVER_URL = os.getenv('PAYMENT_SERVER_URL', 'http://localhost:5000')

if not STRIPE_WEBHOOK_SECRET or STRIPE_WEBHOOK_SECRET.startswith('whsec_REPLACE'):
    logger.warning("STRIPE_WEBHOOK_SECRET is not configured! Webhook signature verification will fail.")
    logger.warning("Get your webhook secret from: Stripe Dashboard → Developers → Webhooks")

db = BotDatabase()

@app.route('/payment/success')
def payment_success():
    """Success page that auto-closes the webview"""
    bot_username = request.args.get('bot', '')
    return render_template('payment_success.html'), 200, {
        'Content-Type': 'text/html; charset=utf-8'
    }

@app.route('/payment/cancel')
def payment_cancel():
    """Cancel page that auto-closes the webview"""
    bot_username = request.args.get('bot', '')
    return render_template('payment_cancel.html'), 200, {
        'Content-Type': 'text/html; charset=utf-8'
    }

@app.route('/payment/cancel-complete')
def cancel_complete():
    """Page shown after user returns from Stripe portal — auto-redirects to Telegram"""
    telegram_id = request.args.get('telegram_id', '')
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    # Extract bot username from token (first part is bot ID)
    bot_username = ''
    try:
        import requests as req
        resp = req.get(f'https://api.telegram.org/bot{bot_token}/getMe', timeout=5)
        if resp.status_code == 200:
            bot_username = resp.json().get('result', {}).get('username', '')
    except Exception:
        pass

    telegram_url = f'https://t.me/{bot_username}' if bot_username else '#'

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Cancellation Processing</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                display: flex; justify-content: center; align-items: center;
                min-height: 100vh; margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; padding: 20px;
            }}
            .container {{
                text-align: center; padding: 40px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 20px; backdrop-filter: blur(10px);
                max-width: 400px; width: 100%;
            }}
            h1 {{ font-size: 48px; margin: 20px 0; }}
            p {{ font-size: 18px; line-height: 1.6; margin: 15px 0; }}
            .btn {{
                display: inline-block; background: white; color: #667eea;
                padding: 14px 32px; border-radius: 12px; text-decoration: none;
                font-size: 18px; font-weight: bold; margin-top: 20px;
            }}
            .countdown {{ font-size: 16px; opacity: 0.8; margin-top: 15px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>&#10003;</h1>
            <p><strong>Cancellation processed</strong></p>
            <p>Check your Telegram bot for confirmation details.</p>
            <a class="btn" href="{telegram_url}">Return to Telegram Bot</a>
            <p class="countdown" id="countdown">Redirecting in 3...</p>
        </div>
        <script>
            var seconds = 3;
            var url = "{telegram_url}";
            var el = document.getElementById('countdown');
            var t = setInterval(function() {{
                seconds--;
                if (seconds > 0) {{ el.textContent = 'Redirecting in ' + seconds + '...'; }}
                else {{ el.textContent = 'Redirecting now...'; clearInterval(t); if (url !== '#') window.location.href = url; }}
            }}, 1000);
        </script>
    </body>
    </html>
    """, 200, {'Content-Type': 'text/html; charset=utf-8'}

@app.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')

    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        return jsonify({'error': 'Invalid signature'}), 400

    # Handle the event
    event_type = event['type']
    logger.info(f"Received Stripe event: {event_type}")

    if event_type == 'customer.subscription.updated':
        subscription = event['data']['object']
        handle_subscription_updated(subscription)

    elif event_type == 'customer.subscription.deleted':
        subscription = event['data']['object']
        handle_subscription_deleted(subscription)

    elif event_type == 'invoice.payment_failed':
        invoice = event['data']['object']
        handle_invoice_payment_failed(invoice)

    return jsonify({'status': 'success'}), 200

def handle_subscription_updated(subscription):
    """Handle subscription update events (including cancellations)"""
    try:
        customer_id = subscription['customer']
        subscription_id = subscription['id']
        cancel_at_period_end = subscription['cancel_at_period_end']
        status = subscription['status']
        current_period_end = subscription['current_period_end']

        logger.info(f"Subscription updated: {subscription_id}, cancel_at_period_end={cancel_at_period_end}")

        # Find user by Stripe customer ID
        user = db.execute_query("""
            SELECT telegram_id, username, first_name
            FROM users
            WHERE stripe_customer_id = %s OR stripe_subscription_id = %s
        """, (customer_id, subscription_id), fetch='one')

        if not user:
            logger.warning(f"User not found for customer {customer_id}")
            return

        telegram_id = user['telegram_id']

        # Check if this is a cancellation
        if cancel_at_period_end:
            # Subscription is marked for cancellation — keep active until period end
            logger.info(f"Subscription {subscription_id} marked for cancellation for user {telegram_id}")
            cancel_date_ts = datetime.fromtimestamp(current_period_end)

            # Keep subscription_active=true, set expiry to period end
            # Stripe will fire customer.subscription.deleted when period actually ends
            db.execute_query("""
                UPDATE users
                SET subscription_expires = %s,
                    metadata = jsonb_set(
                        COALESCE(metadata, '{}'::jsonb),
                        '{cancellation_pending}',
                        'true'::jsonb
                    )
                WHERE telegram_id = %s
            """, (cancel_date_ts, telegram_id,))

            cancel_date = cancel_date_ts.strftime('%B %d, %Y')
            send_telegram_notification(
                telegram_id,
                f"✅ Subscription Cancelled Successfully\n\n"
                f"Your subscription has been cancelled in Stripe.\n\n"
                f"📅 Access continues until: {cancel_date}\n\n"
                f"You won't be charged again.\n\n"
                f"Changed your mind? You can resubscribe anytime with /start\n\n"
                f"Thank you for using LinkedInGrowthBot! 💙"
            )

        elif status == 'active' and not cancel_at_period_end:
            # Subscription reactivated (user uncancelled)
            logger.info(f"Subscription {subscription_id} reactivated for user {telegram_id}")

            db.execute_query("""
                UPDATE users
                SET subscription_active = true
                WHERE telegram_id = %s
            """, (telegram_id,))

            send_telegram_notification(
                telegram_id,
                "🎉 Subscription Reactivated!\n\n"
                "Your subscription is now active again.\n\n"
                "Welcome back! Use /autopilot to start automating."
            )

    except Exception as e:
        logger.error(f"Error handling subscription update: {e}")

def handle_subscription_deleted(subscription):
    """Handle subscription deletion (immediate cancellation)"""
    try:
        customer_id = subscription['customer']
        subscription_id = subscription['id']

        logger.info(f"Subscription deleted: {subscription_id}")

        # Find user
        user = db.execute_query("""
            SELECT telegram_id
            FROM users
            WHERE stripe_customer_id = %s OR stripe_subscription_id = %s
        """, (customer_id, subscription_id), fetch='one')

        if not user:
            logger.warning(f"User not found for deleted subscription {subscription_id}")
            return

        telegram_id = user['telegram_id']

        # Deactivate subscription
        db.deactivate_subscription(telegram_id)

        # Notify user
        send_telegram_notification(
            telegram_id,
            "❌ Subscription Ended\n\n"
            "Your subscription has been cancelled and is no longer active.\n\n"
            "To regain access, subscribe again with /start"
        )

    except Exception as e:
        logger.error(f"Error handling subscription deletion: {e}")

def handle_invoice_payment_failed(invoice):
    """Handle failed payment — notify user and deactivate after final attempt"""
    try:
        customer_id = invoice.get('customer')
        subscription_id = invoice.get('subscription')
        attempt_count = invoice.get('attempt_count', 0)
        next_attempt = invoice.get('next_payment_attempt')

        logger.warning(f"Payment failed for customer {customer_id}, attempt {attempt_count}")

        # Find user
        user = db.execute_query("""
            SELECT telegram_id
            FROM users
            WHERE stripe_customer_id = %s OR stripe_subscription_id = %s
        """, (customer_id, subscription_id), fetch='one')

        if not user:
            logger.warning(f"User not found for failed payment customer {customer_id}")
            return

        telegram_id = user['telegram_id']

        if next_attempt:
            # Stripe will retry — warn the user
            from datetime import datetime
            retry_date = datetime.fromtimestamp(next_attempt).strftime('%B %d, %Y')
            send_telegram_notification(
                telegram_id,
                f"⚠️ Payment Failed (Attempt {attempt_count})\n\n"
                f"Your payment for the LinkedIn Bot subscription could not be processed.\n\n"
                f"Please update your payment method to avoid losing access:\n"
                f"• Use /cancelsubscription → Stripe Portal → Update Payment Method\n\n"
                f"Stripe will retry on: {retry_date}\n\n"
                f"If payment continues to fail, your subscription will be cancelled automatically."
            )
        else:
            # Final attempt failed — deactivate subscription
            logger.info(f"Final payment attempt failed for user {telegram_id}, deactivating")
            db.deactivate_subscription(telegram_id)
            send_telegram_notification(
                telegram_id,
                "❌ Subscription Cancelled — Payment Failed\n\n"
                "Your subscription has been cancelled because payment could not be processed "
                "after multiple attempts.\n\n"
                "To regain access, subscribe again with /start\n\n"
                "If this was an error, please update your payment method and resubscribe."
            )

    except Exception as e:
        logger.error(f"Error handling payment failure: {e}")

def send_telegram_notification(telegram_id: int, message: str):
    """Send notification to user via Telegram bot"""
    try:
        import requests

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': telegram_id,
            'text': message,
            'parse_mode': 'Markdown'
        }

        response = requests.post(url, json=data, timeout=10)

        if response.status_code == 200:
            logger.info(f"Notification sent to user {telegram_id}")
        else:
            logger.error(f"Failed to send notification: {response.text}")

    except Exception as e:
        logger.error(f"Error sending Telegram notification: {e}")

@app.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'ok'}, 200

if __name__ == '__main__':
    port = int(os.getenv('PAYMENT_SERVER_PORT', 5000))
    print(f"Payment server starting on port {port}...")
    print(f"Success URL: {PAYMENT_SERVER_URL}/payment/success")
    print(f"Cancel URL: {PAYMENT_SERVER_URL}/payment/cancel")
    print(f"Webhook URL: {PAYMENT_SERVER_URL}/webhook/stripe")
    app.run(host='0.0.0.0', port=port, debug=False)
