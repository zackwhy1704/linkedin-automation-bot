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
    """Success page — retrieve Stripe session, save IDs, then show confirmation."""
    bot_username = request.args.get('bot', '')
    session_id = request.args.get('session_id', '')

    # If we have a session_id, retrieve the full session and save Stripe IDs
    if session_id:
        try:
            checkout_session = stripe.checkout.Session.retrieve(session_id)
            customer_id = checkout_session.get('customer')
            subscription_id = checkout_session.get('subscription')
            telegram_id_str = (
                checkout_session.get('client_reference_id')
                or checkout_session.get('metadata', {}).get('telegram_id')
            )

            if telegram_id_str and (customer_id or subscription_id):
                telegram_id = int(telegram_id_str)
                db.activate_subscription(
                    telegram_id,
                    stripe_customer_id=customer_id,
                    stripe_subscription_id=subscription_id,
                    days=30
                )
                logger.info(
                    f"Payment success: saved Stripe IDs for user {telegram_id} "
                    f"(customer={customer_id}, subscription={subscription_id})"
                )
        except Exception as e:
            logger.error(f"Error retrieving checkout session {session_id}: {e}")

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
    bot_username = ''
    try:
        import requests as req
        resp = req.get(f'https://api.telegram.org/bot{bot_token}/getMe', timeout=5)
        if resp.status_code == 200:
            bot_username = resp.json().get('result', {}).get('username', '')
    except Exception:
        pass

    telegram_url = f'https://t.me/{bot_username}' if bot_username else ''

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Cancellation Processing</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
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
            <a class="btn" id="telegram-link" href="{telegram_url or '#'}">Return to Telegram Bot</a>
            <p class="countdown" id="countdown">Closing in 3...</p>
        </div>
        <script>
            var seconds = 3;
            var url = "{telegram_url}";
            var el = document.getElementById('countdown');
            var linkEl = document.getElementById('telegram-link');
            var isTelegramWebApp = !!(window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initData);

            if (!url) {{ linkEl.style.display = 'none'; }}

            var t = setInterval(function() {{
                seconds--;
                if (seconds > 0) {{
                    el.textContent = (isTelegramWebApp ? 'Closing' : 'Redirecting') + ' in ' + seconds + '...';
                }} else {{
                    clearInterval(t);
                    if (isTelegramWebApp) {{
                        el.textContent = 'Returning to bot...';
                        try {{ window.Telegram.WebApp.close(); }} catch(e) {{}}
                    }} else if (url) {{
                        el.textContent = 'Redirecting now...';
                        window.location.href = url;
                    }} else {{
                        el.textContent = 'You can close this page.';
                    }}
                }}
            }}, 1000);

            linkEl.addEventListener('click', function(e) {{
                if (isTelegramWebApp) {{
                    e.preventDefault();
                    try {{ window.Telegram.WebApp.close(); }} catch(err) {{}}
                }}
            }});
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

    if event_type == 'checkout.session.completed':
        session = event['data']['object']
        handle_checkout_session_completed(session)

    elif event_type == 'customer.subscription.updated':
        subscription = event['data']['object']
        handle_subscription_updated(subscription)

    elif event_type == 'customer.subscription.deleted':
        subscription = event['data']['object']
        handle_subscription_deleted(subscription)

    elif event_type == 'invoice.payment_failed':
        invoice = event['data']['object']
        handle_invoice_payment_failed(invoice)

    else:
        # Unhandled events — log and acknowledge so Stripe doesn't retry.
        # Only 4 events need handlers for our single-plan, no-trial, no-pause setup:
        #   checkout.session.completed, customer.subscription.updated,
        #   customer.subscription.deleted, invoice.payment_failed
        # Remove unneeded events from Stripe Dashboard → Developers → Webhooks
        logger.info(f"Unhandled Stripe event type: {event_type} (acknowledged)")

    return jsonify({'status': 'success'}), 200


def handle_checkout_session_completed(session):
    """Handle checkout.session.completed — save Stripe customer_id and subscription_id to user record.
    This is the CRITICAL handler that links a Stripe subscription to a Telegram user."""
    try:
        customer_id = session.get('customer')
        subscription_id = session.get('subscription')
        telegram_id_str = session.get('client_reference_id') or session.get('metadata', {}).get('telegram_id')

        if not telegram_id_str:
            logger.warning(f"checkout.session.completed missing telegram_id: {session.get('id')}")
            return

        telegram_id = int(telegram_id_str)

        logger.info(f"Checkout completed for user {telegram_id}: customer={customer_id}, subscription={subscription_id}")

        # Get actual period end from Stripe subscription instead of hardcoded 30 days
        days = 30  # default fallback
        if subscription_id:
            try:
                sub = stripe.Subscription.retrieve(subscription_id)
                period_end = _get_subscription_period_end(sub)
                if period_end:
                    from datetime import datetime as dt
                    sub_end = dt.fromtimestamp(period_end)
                    days = max(1, (sub_end - dt.now()).days)
            except Exception as e:
                logger.warning(f"Could not fetch subscription period for {subscription_id}: {e}")

        # Activate subscription AND save Stripe IDs
        db.activate_subscription(
            telegram_id,
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
            days=days
        )

        # Tag subscription type based on whether promo/trial coupon was used
        promo_code = session.get('metadata', {}).get('promo_code', '')
        sub_type = 'stripe_trial' if promo_code else 'stripe'
        try:
            db.execute_query("""
                UPDATE users SET metadata = jsonb_set(
                    COALESCE(metadata, '{}'::jsonb),
                    '{subscription_type}', %s::jsonb
                ) WHERE telegram_id = %s
            """, (f'"{sub_type}"', telegram_id))
        except Exception:
            pass

        # Send confirmation
        send_telegram_notification(
            telegram_id,
            "🎉 Payment Successful!\n\n"
            "Your subscription is now ACTIVE!\n\n"
            "You now have full access to all features.\n\n"
            "🚀 Send /autopilot to start automating!"
        )

    except Exception as e:
        logger.error(f"Error handling checkout.session.completed: {e}")

def _get_subscription_period_end(subscription):
    """Get current_period_end from a Stripe subscription object.
    Handles both old API (subscription.current_period_end) and
    new API 2025-03-31+ (subscription.items.data[0].current_period_end)."""
    # Try subscription-level first (old API)
    period_end = getattr(subscription, 'current_period_end', None)
    if period_end is None:
        try:
            period_end = subscription['current_period_end']
        except (KeyError, TypeError):
            pass

    # Try item-level (new API 2025-03-31+)
    if period_end is None:
        try:
            items = getattr(subscription, 'items', None)
            # In Stripe SDK v14+, items may be a method
            if callable(items):
                items_result = items()
                item_list = getattr(items_result, 'data', []) if items_result else []
            elif items and hasattr(items, 'data'):
                item_list = items.data
            else:
                item_list = []

            if item_list:
                period_end = getattr(item_list[0], 'current_period_end', None)
                if period_end is None:
                    try:
                        period_end = item_list[0].get('current_period_end')
                    except (AttributeError, TypeError, KeyError):
                        pass
        except (AttributeError, IndexError, KeyError, TypeError):
            pass

    # Fallback: try cancel_at field if cancelling
    if period_end is None:
        period_end = getattr(subscription, 'cancel_at', None)
        if period_end is None:
            try:
                period_end = subscription.get('cancel_at')
            except (AttributeError, TypeError, KeyError):
                pass

    return period_end


def handle_subscription_updated(subscription):
    """Handle subscription update events (including cancellations)"""
    try:
        customer_id = getattr(subscription, 'customer', None) or subscription.get('customer')
        subscription_id = getattr(subscription, 'id', None) or subscription.get('id')
        cancel_at_period_end = getattr(subscription, 'cancel_at_period_end', None)
        if cancel_at_period_end is None:
            cancel_at_period_end = subscription.get('cancel_at_period_end', False)
        status = getattr(subscription, 'status', None) or subscription.get('status')
        current_period_end = _get_subscription_period_end(subscription)

        # Also check cancel_at (Stripe portal uses this in newer API versions)
        cancel_at = getattr(subscription, 'cancel_at', None)
        if cancel_at is None:
            try:
                cancel_at = subscription.get('cancel_at')
            except (AttributeError, TypeError, KeyError):
                pass

        # Determine if this is a cancellation: either cancel_at_period_end=True
        # or cancel_at is set to a future timestamp
        is_cancelling = cancel_at_period_end or (cancel_at and cancel_at > 0)

        logger.info(f"Subscription updated: {subscription_id}, status={status}, "
                     f"cancel_at_period_end={cancel_at_period_end}, cancel_at={cancel_at}, "
                     f"period_end={current_period_end}")

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
        if is_cancelling:
            # Subscription is marked for cancellation — keep active until period end
            logger.info(f"Subscription {subscription_id} marked for cancellation for user {telegram_id}")

            # Determine the cancel date: prefer current_period_end, fall back to cancel_at
            effective_cancel_ts = current_period_end or cancel_at
            if effective_cancel_ts:
                cancel_date_ts = datetime.fromtimestamp(effective_cancel_ts)
                cancel_date = cancel_date_ts.strftime('%B %d, %Y')
            else:
                cancel_date_ts = None
                cancel_date = "your billing period end"

            # Keep subscription_active=true, set expiry to period end
            # Stripe will fire customer.subscription.deleted when period actually ends
            if cancel_date_ts:
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
            else:
                db.execute_query("""
                    UPDATE users
                    SET metadata = jsonb_set(
                            COALESCE(metadata, '{}'::jsonb),
                            '{cancellation_pending}',
                            'true'::jsonb
                        )
                    WHERE telegram_id = %s
                """, (telegram_id,))

            send_telegram_notification(
                telegram_id,
                f"✅ Subscription Cancelled Successfully\n\n"
                f"Your subscription has been cancelled in Stripe.\n\n"
                f"📅 Access continues until: {cancel_date}\n\n"
                f"You won't be charged again.\n\n"
                f"Changed your mind? You can resubscribe anytime with /start\n\n"
                f"Thank you for using LinkedInGrowthBot! 💙"
            )

        elif status == 'active' and not is_cancelling:
            # Subscription reactivated or renewed — sync expiration from Stripe
            logger.info(f"Subscription {subscription_id} active for user {telegram_id}")

            # Sync subscription_expires with Stripe's actual period end
            update_query = """
                UPDATE users
                SET subscription_active = true,
                    metadata = COALESCE(metadata, '{}'::jsonb) - 'cancellation_pending'
                WHERE telegram_id = %s
            """
            update_params = [telegram_id]

            if current_period_end:
                new_expires = datetime.fromtimestamp(current_period_end)
                update_query = """
                    UPDATE users
                    SET subscription_active = true,
                        subscription_expires = %s,
                        metadata = COALESCE(metadata, '{}'::jsonb) - 'cancellation_pending'
                    WHERE telegram_id = %s
                """
                update_params = [new_expires, telegram_id]

            db.execute_query(update_query, tuple(update_params))

            send_telegram_notification(
                telegram_id,
                "🎉 Subscription Active!\n\n"
                "Your subscription is now active.\n\n"
                "Use /autopilot to start automating."
            )

    except Exception as e:
        logger.error(f"Error handling subscription update: {e}", exc_info=True)

def handle_subscription_deleted(subscription):
    """Handle subscription deletion (immediate cancellation)"""
    try:
        customer_id = getattr(subscription, 'customer', None) or subscription.get('customer')
        subscription_id = getattr(subscription, 'id', None) or subscription.get('id')

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
