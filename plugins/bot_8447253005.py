import random
import json

WORDS = [
    "תפוח", "בננה", "אבטיח", "תפוז", "ענבים",
    "מחשב", "טלפון", "מקלדת", "עכבר", "מסך",
    "שולחן", "כיסא", "מיטה", "ספה", "ארון",
    "ספר", "עט", "מחברת", "תיק", "מחק",
    "כלב", "חתול", "ציפור", "דג", "סוס"
]

HANGMAN_STAGES = [
    """
     ------
     |    |
     |
     |
     |
     |
    ---
    """,
    """
     ------
     |    |
     |    O
     |
     |
     |
    ---
    """,
    """
     ------
     |    |
     |    O
     |    |
     |
     |
    ---
    """,
    """
     ------
     |    |
     |    O
     |   /|
     |
     |
    ---
    """,
    """
     ------
     |    |
     |    O
     |   /|\\
     |
     |
    ---
    """,
    """
     ------
     |    |
     |    O
     |   /|\\
     |   /
     |
    ---
    """,
    """
     ------
     |    |
     |    O
     |   /|\\
     |   / \\
     |
    ---
    """
]

game_state = {
    "active": False,
    "word": "",
    "guessed": set(),
    "mistakes": 0,
    "score": 0,
    "games_played": 0,
    "games_won": 0
}

def get_dashboard_widget():
    if game_state["games_played"] > 0:
        win_rate = int((game_state["games_won"] / game_state["games_played"]) * 100)
        status = "success" if win_rate >= 60 else "warning" if win_rate >= 40 else "danger"
    else:
        win_rate = 0
        status = "info"
    
    return {
        "title": "איש תלוי 🎮",
        "value": f"{game_state['score']} נקודות",
        "label": f"אחוז ניצחונות: {win_rate}% ({game_state['games_won']}/{game_state['games_played']})",
        "status": status,
        "icon": "bi-controller"
    }

def get_display_word():
    return " ".join([letter if letter in game_state["guessed"] else "_" for letter in game_state["word"]])

def start_new_game():
    game_state["active"] = True
    game_state["word"] = random.choice(WORDS)
    game_state["guessed"] = set()
    game_state["mistakes"] = 0
    game_state["games_played"] += 1
    
    return f"""🎮 משחק חדש התחיל!

{HANGMAN_STAGES[0]}

המילה: {get_display_word()}

אורך המילה: {len(game_state['word'])} אותיות
שלח אות בעברית לניחוש!

💡 טיפ: נסה אותיות נפוצות כמו א, ו, ה, ת"""

def handle_message(text):
    text = text.strip()
    
    if text == "/bot_8447253005" or text.lower() == "משחק חדש" or text.lower() == "התחל":
        return start_new_game()
    
    if not game_state["active"]:
        return f"""👋 ברוכים הבאים למשחק איש תלוי!

📊 הסטטיסטיקה שלך:
🏆 ניקוד: {game_state['score']}
🎯 משחקים: {game_state['games_played']}
✅ ניצחונות: {game_state['games_won']}

כדי להתחיל משחק חדש, שלח:
/bot_8447253005"""
    
    if len(text) != 1:
        return "❌ שלח אות אחת בלבד בעברית!"
    
    letter = text
    
    if not ('א' <= letter <= 'ת'):
        return "❌ שלח אות בעברית בלבד!"
    
    if letter in game_state["guessed"]:
        return f"⚠️ כבר ניחשת את האות '{letter}'!\n\nהמילה: {get_display_word()}\nאותיות שניחשת: {', '.join(sorted(game_state['guessed']))}"
    
    game_state["guessed"].add(letter)
    
    if letter in game_state["word"]:
        display = get_display_word()
        
        if "_" not in display:
            game_state["score"] += 10 + (6 - game_state["mistakes"]) * 2
            game_state["games_won"] += 1
            game_state["active"] = False
            
            return f"""🎉 כל הכבוד! ניצחת!

המילה הייתה: {game_state['word']}

📊 תוצאות:
✅ טעויות: {game_state['mistakes']}/6
🏆 נקודות שהרווחת: {10 + (6 - game_state['mistakes']) * 2}
💰 ניקוד כולל: {game_state['score']}

רוצה לשחק שוב? שלח: /bot_8447253005"""
        
        return f"""✅ נכון! האות '{letter}' נמצאת במילה!

{HANGMAN_STAGES[game_state['mistakes']]}

המילה: {display}
אותיות שניחשת: {', '.join(sorted(game_state['guessed']))}
טעויות: {game_state['mistakes']}/6"""
    else:
        game_state["mistakes"] += 1
        
        if game_state["mistakes"] >= 6:
            game_state["active"] = False
            
            return f"""💀 אוי לא! הפסדת!

{HANGMAN_STAGES[6]}

המילה הייתה: {game_state['word']}

📊 תוצאות:
❌ טעויות: 6/6
💰 ניקוד כולל: {game_state['score']}

רוצה לשחק שוב? שלח: /bot_8447253005"""
        
        return f"""❌ טעות! האות '{letter}' לא נמצאת במילה.

{HANGMAN_STAGES[game_state['mistakes']]}

המילה: {get_display_word()}
אותיות שניחשת: {', '.join(sorted(game_state['guessed']))}
טעויות: {game_state['mistakes']}/6"""