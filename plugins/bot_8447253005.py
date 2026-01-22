import random
import json
import os

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(PLUGIN_DIR, 'hangman_data.json')

WORDS = [
    'מחשב', 'תכנות', 'פייתון', 'משחק', 'אינטרנט', 'מקלדת', 'עכבר', 'מסך',
    'תוכנה', 'חומרה', 'רשת', 'שרת', 'לקוח', 'דפדפן', 'אתר', 'קובץ',
    'תיקייה', 'מערכת', 'הפעלה', 'זיכרון', 'מעבד', 'דיסק', 'נתונים', 'מידע',
    'אבטחה', 'סיסמה', 'משתמש', 'כניסה', 'יציאה', 'שמירה', 'טעינה', 'הורדה'
]

HANGMAN_STAGES = [
    '''
   ------
   |    |
   |
   |
   |
   |
---------
''',
    '''
   ------
   |    |
   |    O
   |
   |
   |
---------
''',
    '''
   ------
   |    |
   |    O
   |    |
   |
   |
---------
''',
    '''
   ------
   |    |
   |    O
   |   /|
   |
   |
---------
''',
    '''
   ------
   |    |
   |    O
   |   /|\\
   |
   |
---------
''',
    '''
   ------
   |    |
   |    O
   |   /|\\
   |   /
   |
---------
''',
    '''
   ------
   |    |
   |    O
   |   /|\\
   |   / \\
   |
---------
'''
]

def load_game_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_game_data(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

def get_dashboard_widget():
    data = load_game_data()
    total_games = data.get('total_games', 0)
    wins = data.get('wins', 0)
    
    win_rate = (wins / total_games * 100) if total_games > 0 else 0
    
    return {
        "title": "🎮 איש תלוי",
        "value": f"{total_games} משחקים",
        "label": f"ניצחונות: {wins} ({win_rate:.1f}%)",
        "status": "success" if win_rate > 50 else "info",
        "icon": "bi-controller"
    }

def handle_message(text):
    text = text.strip()
    
    data = load_game_data()
    
    if 'current_word' not in data or text.lower() == '/bot_8447253005' or text.lower() == 'משחק חדש':
        word = random.choice(WORDS)
        data['current_word'] = word
        data['guessed_letters'] = []
        data['wrong_guesses'] = 0
        data['game_active'] = True
        save_game_data(data)
        
        display = ' '.join(['_' for _ in word])
        return f"🎮 משחק חדש התחיל!\n\n{HANGMAN_STAGES[0]}\n\nהמילה: {display}\n\nנחשו אות (בעברית) או שלחו 'משחק חדש' להתחלה מחדש"
    
    if not data.get('game_active'):
        return "המשחק הסתיים. שלחו 'משחק חדש' או /bot_8447253005 כדי להתחיל משחק חדש"
    
    if len(text) != 1:
        return "אנא שלחו אות בודדת בעברית"
    
    letter = text
    word = data['current_word']
    guessed = data['guessed_letters']
    wrong = data['wrong_guesses']
    
    if letter in guessed:
        display = ' '.join([l if l in guessed else '_' for l in word])
        return f"כבר ניסיתם את האות '{letter}'!\n\n{HANGMAN_STAGES[wrong]}\n\nהמילה: {display}\n\nאותיות שנוחשו: {', '.join(guessed)}"
    
    guessed.append(letter)
    
    if letter not in word:
        wrong += 1
        data['wrong_guesses'] = wrong
    
    data['guessed_letters'] = guessed
    save_game_data(data)
    
    display = ' '.join([l if l in guessed else '_' for l in word])
    
    if wrong >= len(HANGMAN_STAGES) - 1:
        data['game_active'] = False
        data['total_games'] = data.get('total_games', 0) + 1
        save_game_data(data)
        return f"💀 הפסדתם!\n\n{HANGMAN_STAGES[wrong]}\n\nהמילה הייתה: {word}\n\nשלחו 'משחק חדש' או /bot_8447253005 להתחלה מחדש"
    
    if all(l in guessed for l in word):
        data['game_active'] = False
        data['total_games'] = data.get('total_games', 0) + 1
        data['wins'] = data.get('wins', 0) + 1
        save_game_data(data)
        return f"🎉 ניצחתם!\n\n{HANGMAN_STAGES[wrong]}\n\nהמילה: {word}\n\nניחושים שגויים: {wrong}\n\nשלחו 'משחק חדש' או /bot_8447253005 להתחלה מחדש"
    
    status = "✓" if letter in word else "✗"
    return f"{status} האות '{letter}' {'נמצאת' if letter in word else 'לא נמצאת'} במילה\n\n{HANGMAN_STAGES[wrong]}\n\nהמילה: {display}\n\nאותיות שנוחשו: {', '.join(guessed)}\nניחושים שגויים: {wrong}/{len(HANGMAN_STAGES)-1}"