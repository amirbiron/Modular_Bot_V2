# === MongoDB State Helpers (auto-generated) ===
import os
from pymongo import MongoClient

_state_mongo_client = None
_state_mongo_db = None
BOT_ID = "bot_8223920983"

def _get_state_db():
    """מחזיר חיבור ל-MongoDB לשמירת מצב."""
    global _state_mongo_client, _state_mongo_db
    if _state_mongo_db is None:
        mongo_uri = os.environ.get("MONGO_URI")
        if mongo_uri:
            try:
                _state_mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
                _state_mongo_db = _state_mongo_client.get_database("bot_factory")
            except Exception:
                return None
    return _state_mongo_db

def save_state(user_id, key, value):
    """
    שומר מידע ב-MongoDB עבור משתמש ספציפי.
    
    Args:
        user_id: מזהה המשתמש
        key: מפתח לשמירה (כמו "score", "game_state", "preferences")
        value: הערך לשמירה (יכול להיות מספר, מחרוזת, רשימה או מילון)
    
    Returns:
        bool: האם השמירה הצליחה
    """
    db = _get_state_db()
    if db is None:
        return False
    try:
        db.bot_states.update_one(
            {"bot_id": BOT_ID, "user_id": str(user_id), "key": key},
            {"$set": {"value": value}},
            upsert=True
        )
        return True
    except Exception:
        return False

def load_state(user_id, key, default=None):
    """
    טוען מידע מ-MongoDB עבור משתמש ספציפי.
    
    Args:
        user_id: מזהה המשתמש
        key: מפתח לטעינה
        default: ערך ברירת מחדל אם המפתח לא קיים
    
    Returns:
        הערך השמור או ערך ברירת המחדל
    """
    db = _get_state_db()
    if db is None:
        return default
    try:
        doc = db.bot_states.find_one({"bot_id": BOT_ID, "user_id": str(user_id), "key": key})
        return doc.get("value", default) if doc else default
    except Exception:
        return default

# === End of State Helpers ===

import json
import re
from datetime import datetime

def get_dashboard_widget():
    return {
        "title": "בוט מסעדה/תפריט",
        "value": "פעיל",
        "label": "מערכת הזמנות ותשלומים",
        "status": "success",
        "icon": "bi-shop"
    }

def handle_message(text, user_id=None, context=None):
    try:
        if not user_id:
            return "שגיאה: לא ניתן לזהות משתמש"
        
        text = text.strip()
        
        # Menu items with prices in Telegram Stars
        menu = {
            "1": {"name": "המבורגר קלאסי", "price": 50, "category": "עיקריות"},
            "2": {"name": "פיצה מרגריטה", "price": 45, "category": "עיקריות"},
            "3": {"name": "סלט קיסר", "price": 35, "category": "סלטים"},
            "4": {"name": "פסטה אלפרדו", "price": 55, "category": "עיקריות"},
            "5": {"name": "שניצל", "price": 48, "category": "עיקריות"},
            "6": {"name": "פלאפל", "price": 25, "category": "מנות קלות"},
            "7": {"name": "שקשוקה", "price": 30, "category": "ארוחות בוקר"},
            "8": {"name": "קוקה קולה", "price": 10, "category": "משקאות"},
            "9": {"name": "מיץ תפוזים", "price": 12, "category": "משקאות"},
            "10": {"name": "עוגת שוקולד", "price": 28, "category": "קינוחים"}
        }
        
        # Handle /start command
        if text == "/start":
            return """🍽️ ברוכים הבאים למסעדה שלנו!

📱 הפקודות הזמינות:
/menu - צפייה בתפריט המלא
/order - ביצוע הזמנה חדשה
/my_orders - ההזמנות שלי
/review - כתיבת ביקורת
/reviews - צפייה בביקורות
/cart - עגלת הקניות שלי
/clear_cart - ניקוי עגלת הקניות
/checkout - תשלום והשלמת הזמנה
/verify - אימות זהות
/status - סטטוס חשבון
/help - עזרה

🌟 אנחנו מקבלים תשלום בכוכבי טלגרם!"""

        # Show menu
        elif text == "/menu":
            categories = {}
            for item_id, item in menu.items():
                cat = item["category"]
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(f"{item_id}. {item['name']} - ⭐ {item['price']} כוכבים")
            
            menu_text = "📋 **התפריט שלנו:**\n\n"
            for cat, items in categories.items():
                menu_text += f"**{cat}:**\n" + "\n".join(items) + "\n\n"
            
            menu_text += "להוספה לעגלה: /add <מספר מנה>\nלדוגמה: /add 1"
            return menu_text

        # Add item to cart
        elif text.startswith("/add"):
            parts = text.split()
            if len(parts) < 2:
                return "❌ נא לציין מספר מנה. דוגמה: /add 1"
            
            item_id = parts[1]
            if item_id not in menu:
                return "❌ מספר מנה לא קיים. שלח /menu לצפייה בתפריט"
            
            cart = load_state(user_id, "cart", [])
            cart.append(item_id)
            save_state(user_id, "cart", cart)
            
            item = menu[item_id]
            return f"✅ {item['name']} נוסף לעגלה!\n⭐ מחיר: {item['price']} כוכבים\n\nלצפייה בעגלה: /cart\nלתשלום: /checkout"

        # View cart
        elif text == "/cart":
            cart = load_state(user_id, "cart", [])
            if not cart:
                return "🛒 העגלה שלך ריקה\n\nשלח /menu לצפייה בתפריט"
            
            cart_items = {}
            total = 0
            for item_id in cart:
                if item_id in menu:
                    cart_items[item_id] = cart_items.get(item_id, 0) + 1
                    total += menu[item_id]["price"]
            
            cart_text = "🛒 **העגלה שלך:**\n\n"
            for item_id, quantity in cart_items.items():
                item = menu[item_id]
                subtotal = item["price"] * quantity
                cart_text += f"{item['name']} x{quantity} - ⭐ {subtotal} כוכבים\n"
            
            cart_text += f"\n**סה״כ: ⭐ {total} כוכבים**\n\n"
            cart_text += "להסרת פריט: /remove <מספר>\nלניקוי עגלה: /clear_cart\nלתשלום: /checkout"
            return cart_text

        # Clear cart
        elif text == "/clear_cart":
            save_state(user_id, "cart", [])
            return "🗑️ העגלה נוקתה בהצלחה"

        # Remove item from cart
        elif text.startswith("/remove"):
            parts = text.split()
            if len(parts) < 2:
                return "❌ נא לציין מספר מנה להסרה. דוגמה: /remove 1"
            
            item_id = parts[1]
            cart = load_state(user_id, "cart", [])
            
            if item_id in cart:
                cart.remove(item_id)
                save_state(user_id, "cart", cart)
                return f"✅ המנה הוסרה מהעגלה\n\nלצפייה בעגלה: /cart"
            else:
                return "❌ המנה לא נמצאת בעגלה"

        # Checkout
        elif text == "/checkout":
            # Check verification
            verified = load_state(user_id, "verified", False)
            if not verified:
                return "⚠️ נדרש אימות זהות לפני ביצוע הזמנה\n\nשלח /verify <שם מלא> כדי להתאמת"
            
            cart = load_state(user_id, "cart", [])
            if not cart:
                return "🛒 העגלה שלך ריקה\n\nשלח /menu לצפייה בתפריט"
            
            # Calculate total
            total = sum(menu[item_id]["price"] for item_id in cart if item_id in menu)
            
            # Create order
            orders = load_state(user_id, "orders", [])
            order = {
                "id": len(orders) + 1,
                "items": cart,
                "total": total,
                "date": datetime.now().isoformat(),
                "status": "ממתין לתשלום"
            }
            orders.append(order)
            save_state(user_id, "orders", orders)
            
            # Clear cart
            save_state(user_id, "cart", [])
            
            return f"""✅ ההזמנה נוצרה בהצלחה!

🧾 **פרטי הזמנה #{order['id']}:**
סה״כ לתשלום: ⭐ {total} כוכבים

💳 **לביצוע התשלום:**
הזמנה זו מחייבת תשלום ב-{total} כוכבי טלגרם

⚠️ **הערה:** מערכת התשלום בכוכבי טלגרם דורשת אינטגרציה ישירה מול ממשק ה-API של טלגרם. 
הבוט מסמן את ההזמנה כ"ממתין לתשלום".

לאחר התשלום (דרך ממשק טלגרם רשמי), שלח:
/confirm_payment {order['id']}

לצפייה בהזמנות: /my_orders"""

        # Confirm payment
        elif text.startswith("/confirm_payment"):
            parts = text.split()
            if len(parts) < 2:
                return "❌ נא לציין מספר הזמנה. דוגמה: /confirm_payment 1"
            
            try:
                order_id = int(parts[1])
                orders = load_state(user_id, "orders", [])
                
                for order in orders:
                    if order["id"] == order_id:
                        if order["status"] == "שולם":
                            return f"ℹ️ הזמנה #{order_id} כבר שולמה"
                        
                        order["status"] = "שולם"
                        order["paid_date"] = datetime.now().isoformat()
                        save_state(user_id, "orders", orders)
                        return f"✅ תשלום אושר!\n🎉 הזמנה #{order_id} התקבלה ובהכנה\n\nזמן אספקה משוער: 30-45 דקות"
                
                return f"❌ הזמנה #{order_id} לא נמצאה"
            except ValueError:
                return "❌ מספר הזמנה לא תקין"

        # My orders
        elif text == "/my_orders":
            orders = load_state(user_id, "orders", [])
            if not orders:
                return "📦 אין לך הזמנות קודמות\n\nשלח /menu לביצוע הזמנה"
            
            orders_text = "📦 **ההזמנות שלך:**\n\n"
            for order in reversed(orders[-10:]):  # Last 10 orders
                date = datetime.fromisoformat(order["date"]).strftime("%d/%m/%Y %H:%M")
                orders_text += f"**הזמנה #{order['id']}**\n"
                orders_text += f"📅 {date}\n"
                orders_text += f"💰 ⭐ {order['total']} כוכבים\n"
                orders_text += f"📊 סטטוס: {order['status']}\n\n"
            
            return orders_text

        # Verify user
        elif text.startswith("/verify"):
            parts = text.split(maxsplit=1)
            if len(parts) < 2:
                return """🔐 **אימות זהות**

לאימות הזהות שלך, נא לשלוח:
/verify <שם מלא>

דוגמה:
/verify יוסי כהן

אימות נדרש לביצוע הזמנות."""
            
            full_name = parts[1].strip()
            if len(full_name) < 3:
                return "❌ נא להזין שם מלא תקין (לפחות 3 תווים)"
            
            save_state(user_id, "verified", True)
            save_state(user_id, "full_name", full_name)
            save_state(user_id, "verified_date", datetime.now().isoformat())
            
            return f"✅ אימות הושלם בהצלחה!\n👤 שם: {full_name}\n\nכעת תוכל לבצע הזמנות. שלח /menu להתחלה"

        # Status
        elif text == "/status":
            verified = load_state(user_id, "verified", False)
            full_name = load_state(user_id, "full_name", "לא זמין")
            orders_count = len(load_state(user_id, "orders", []))
            reviews_count = len(load_state(user_id, "reviews", []))
            
            status_text = "📊 **סטטוס החשבון שלך:**\n\n"
            status_text += f"👤 שם: {full_name}\n"
            status_text += f"✅ אימות: {'מאומת ✓' if verified else 'לא מאומת ✗'}\n"
            status_text += f"📦 הזמנות: {orders_count}\n"
            status_text += f"⭐ ביקורות: {reviews_count}\n"
            
            if not verified:
                status_text += "\n⚠️ לביצוע הזמנות נדרש אימות. שלח /verify"
            
            return status_text

        # Write review
        elif text.startswith("/review"):
            parts = text.split(maxsplit=1)
            if len(parts) < 2:
                return """⭐ **כתיבת ביקורת**

לכתיבת ביקורת, שלח:
/review <דירוג 1-5> <תוכן הביקורת>

דוגמה:
/review 5 אוכל מעולה ושירות מהיר!

לצפייה בביקורות: /reviews"""
            
            review_text = parts[1].strip()
            match = re.match(r'^([1-5])\s+(.+)$', review_text)
            
            if not match:
                return "❌ פורמט לא תקין. דוגמה: /review 5 אוכל טעים מאוד!"
            
            rating = int(match.group(1))
            content = match.group(2)
            
            if len(content) < 10:
                return "❌ הביקורת חייבת להכיל לפחות 10 תווים"
            
            reviews = load_state(user_id, "reviews", [])
            review = {
                "rating": rating,
                "content": content,
                "date": datetime.now().isoformat(),
                "user_id": user_id
            }
            reviews.append(review)
            save_state(user_id, "reviews", reviews)
            
            # Update global reviews
            all_reviews = load_state("global", "all_reviews", [])
            all_reviews.append(review)
            save_state("global", "all_reviews", all_reviews)
            
            stars = "⭐" * rating
            return f"""✅ תודה על הביקורת!

{stars} ({rating}/5)
"{content}"

הביקורת שלך פורסמה בהצלחה.
לצפייה בכל הביקורות: /reviews"""

        # View reviews
        elif text == "/reviews":
            all_reviews = load_state("global", "all_reviews", [])
            
            if not all_reviews:
                return "📝 אין עדיין ביקורות\n\nהיה הראשון לכתוב ביקורת: /review"
            
            # Calculate average
            avg_rating = sum(r["rating"] for r in all_reviews) / len(all_reviews)
            
            reviews_text = f"⭐ **ביקורות המסעדה**\n\n"
            reviews_text += f"📊 דירוג ממוצע: {avg_rating:.1f}/5 ({len(all_reviews)} ביקורות)\n\n"
            
            # Show last 10 reviews
            for review in reversed(all_reviews[-10:]):
                date = datetime.fromisoformat(review["date"]).strftime("%d/%m/%Y")
                stars = "⭐" * review["rating"]
                reviews_text += f"{stars} ({review['rating']}/5)\n"
                reviews_text += f'"{review["content"]}"\n'
                reviews_text += f"📅 {date}\n\n"
            
            reviews_text += "לכתיבת ביקורת: /review <דירוג> <תוכן>"
            return reviews_text

        # Help command
        elif text == "/help":
            return """❓ **עזרה - כיצד להשתמש בבוט**

**תהליך הזמנה:**
1️⃣ /menu - צפה בתפריט
2️⃣ /add <מספר> - הוסף מנות לעגלה
3️⃣ /cart - בדוק את העגלה
4️⃣ /verify <שם> - אמת זהות (פעם אחת)
5️⃣ /checkout - בצע הזמנה ושלם

**ניהול עגלה:**
• /add <מספר> - הוסף מנה
• /remove <מספר> - הסר מנה
• /clear_cart - נקה עגלה

**ביקורות:**
• /review <1-5> <טקסט> - כתוב ביקורת
• /reviews - קרא ביקורות

**מידע:**
• /my_orders - ההזמנות שלי
• /status - סטטוס חשבון
• /start - תפריט ראשי

זקוק לעזרה נוספת? צור קשר עם התמיכה."""

        # Unknown command
        else:
            return """לא הבנתי את הבקשה 🤔

שלח /start כדי לראות את כל הפקודות הזמינות
או /help לקבלת עזרה מפורטת"""

    except Exception as e:
        return f"אירעה שגיאה: {str(e)}\n\nנסה שוב או שלח /start"