"""
Message Templates for Facebook Messenger
Quick replies, buttons, carousels
"""


class MessageTemplates:
    """Pre-built message templates with interactive elements"""

    def main_menu(self) -> dict:
        """Main menu with quick reply buttons"""
        return {
            "text": "What would you like to do?",
            "quick_replies": [
                {
                    "content_type": "text",
                    "title": "🏠 Find Property",
                    "payload": "PROPERTY_SEARCH"
                },
                {
                    "content_type": "text",
                    "title": "📊 Property Valuation",
                    "payload": "VALUATION_REQUEST"
                },
                {
                    "content_type": "text",
                    "title": "📅 Book Viewing",
                    "payload": "APPOINTMENT_BOOK"
                },
                {
                    "content_type": "text",
                    "title": "💬 Talk to Agent",
                    "payload": "TALK_TO_AGENT"
                }
            ]
        }

    def property_type_selector(self) -> dict:
        """Property type quick replies"""
        return {
            "text": "What type of property are you looking for?",
            "quick_replies": [
                {
                    "content_type": "text",
                    "title": "🏢 HDB",
                    "payload": "TYPE_HDB"
                },
                {
                    "content_type": "text",
                    "title": "🏙️ Condo",
                    "payload": "TYPE_CONDO"
                },
                {
                    "content_type": "text",
                    "title": "🏡 Landed",
                    "payload": "TYPE_LANDED"
                },
                {
                    "content_type": "text",
                    "title": "🏪 Commercial",
                    "payload": "TYPE_COMMERCIAL"
                }
            ]
        }

    def budget_selector(self) -> dict:
        """Budget range quick replies"""
        return {
            "text": "What's your budget range?",
            "quick_replies": [
                {
                    "content_type": "text",
                    "title": "< $600K",
                    "payload": "BUDGET_LOW"
                },
                {
                    "content_type": "text",
                    "title": "$600K - $1.2M",
                    "payload": "BUDGET_MID"
                },
                {
                    "content_type": "text",
                    "title": "$1.2M - $2M",
                    "payload": "BUDGET_HIGH"
                },
                {
                    "content_type": "text",
                    "title": "> $2M",
                    "payload": "BUDGET_LUXURY"
                }
            ]
        }

    def timeline_selector(self) -> dict:
        """Timeline quick replies"""
        return {
            "text": "When are you planning to buy?",
            "quick_replies": [
                {
                    "content_type": "text",
                    "title": "🔥 Urgent (ASAP)",
                    "payload": "TIMELINE_URGENT"
                },
                {
                    "content_type": "text",
                    "title": "3-6 months",
                    "payload": "TIMELINE_3_6MO"
                },
                {
                    "content_type": "text",
                    "title": "6-12 months",
                    "payload": "TIMELINE_6_12MO"
                },
                {
                    "content_type": "text",
                    "title": "Just browsing",
                    "payload": "TIMELINE_BROWSING"
                }
            ]
        }

    def intent_selector(self) -> dict:
        """Intent quick replies"""
        return {
            "text": "Are you looking to buy, sell, or invest?",
            "quick_replies": [
                {
                    "content_type": "text",
                    "title": "🏠 Buy",
                    "payload": "INTENT_BUY"
                },
                {
                    "content_type": "text",
                    "title": "💰 Sell",
                    "payload": "INTENT_SELL"
                },
                {
                    "content_type": "text",
                    "title": "📈 Invest",
                    "payload": "INTENT_INVEST"
                },
                {
                    "content_type": "text",
                    "title": "👀 Just browsing",
                    "payload": "INTENT_BROWSE"
                }
            ]
        }

    def property_carousel(self, listings: list) -> dict:
        """
        Generic template carousel for property listings

        Args:
            listings: List of dicts with keys: title, image_url, subtitle, url
        """
        elements = []
        for listing in listings[:10]:  # Max 10 items in carousel
            element = {
                "title": listing.get("title", "Property Listing"),
                "image_url": listing.get("image_url", ""),
                "subtitle": listing.get("subtitle", ""),
                "buttons": [
                    {
                        "type": "web_url",
                        "url": listing.get("url", ""),
                        "title": "View Details"
                    },
                    {
                        "type": "postback",
                        "title": "Interested",
                        "payload": f"INTERESTED_{listing.get('id')}"
                    }
                ]
            }
            elements.append(element)

        return {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "generic",
                    "elements": elements
                }
            }
        }

    def button_template(self, text: str, buttons: list) -> dict:
        """
        Button template message

        Args:
            text: Message text
            buttons: List of button dicts with type, title, url/payload
        """
        return {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "button",
                    "text": text,
                    "buttons": buttons
                }
            }
        }

    def get_started_button(self) -> dict:
        """Get Started button payload for page setup"""
        return {
            "get_started": {
                "payload": "GET_STARTED"
            }
        }

    def persistent_menu(self) -> dict:
        """Persistent menu configuration"""
        return {
            "persistent_menu": [
                {
                    "locale": "default",
                    "composer_input_disabled": False,
                    "call_to_actions": [
                        {
                            "type": "postback",
                            "title": "🏠 Search Properties",
                            "payload": "PROPERTY_SEARCH"
                        },
                        {
                            "type": "postback",
                            "title": "📊 Get Valuation",
                            "payload": "VALUATION_REQUEST"
                        },
                        {
                            "type": "postback",
                            "title": "🏠 Main Menu",
                            "payload": "MAIN_MENU"
                        }
                    ]
                }
            ]
        }
