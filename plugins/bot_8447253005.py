import random
import json
import os

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(PLUGIN_DIR, 'hangman_data.json')

WORDS = [
    'מחשב', 'תכנות', 'פייתון', 'בינה', 'מלאכותית', 'אינטרנט', 'מקלדת',
    'עכבר', 'מסך', 'תוכנה', 'חומרה', 'רשת', 'שרת', 'לקוח', 'נתונים',
    'אלגוריתם', 'פונקציה', 'משתנה', 'מערך', 'מחרוזת', 'מספר', 'בוליאני',
    'תנאי', 'לולאה', 'מחלקה', 'אובייקט', 'ירושה', 'פולימורפיזם', 'אנקפסולציה',
    'ממשק', 'חריג', 'קובץ', 'תיקייה', 'נתיב', 'פרוטוקול', 'דפדפן',
    'אתר', 'דף', 'קישור', 'טופס', 'כפתור', 'תמונה', 'וידאו', 'שמע'
]

HANGMAN_PICS = [
    '''
   +---+
   |   |
       |
       |
       |
       |
=========''',
    '''
   +---+
   |   |
   O   |
       |
       |
       |
=========''',
    '''
   +---+
   |   |
   O   |
   |   |
       |
       |
=========''',
    '''
   +---+
   |   |
   O   |
  /|   |
       |
       |
=========''',
    '''
   +---+
   |   |
   O   |
  /|\\  |
       |
       |
=========''',
    '''
   +---+
   |   |
   O   |
  /|\\  |
  /    |
       |
=========''',
    '''
   +---+
   |   |
   O   |
  /|\\  |
  / \\  |
       |
========='''
]

def load_game_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_game_data(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

def get_dashboard_widget():
    data = load_game_data()
    total_games = sum(d.get('games_won', 0) + d.get('games_lost', 0) for d in data.values())
    total_wins = sum(d.get('games_won', 0) for d in data.values())
    
    if total_games > 0:
        win_rate = int((total_wins / total_games) * 100)
        status = 'success' if win_rate >= 60 else 'warning' if win_rate >= 40 else 'info'
    else:
        win_rate = 0
        status = 'info'
    
    return {
        'title': 'איש תלוי',
        'value': f'{total_games}',
        'label': f'משחקים | {win_rate}% ניצחונות',
        'status': status,
        'icon': 'bi-person-x'
    }

def handle_message(text):
    user_id = 'default_user'
    
    parts = text.strip().split(maxsplit=1)
    command = parts[0].lower()
    
    if command != '/bot_8447253005':
        return None
    
    data = load_game_data()
    
    if user_id not in data:
        data[user_id] = {
            'games_won': 0,
            'games_lost': 0,
            'current_game': None
        }
    
    user_data = data[user_id]
    
    if len(parts) == 1:
        word = random.choice(WORDS)
        user_data['current_game'] = {
            'word': word,
            'guessed': [],
            'wrong': 0,
            'max_wrong': 6
        }
        save_game_data(data)
        
        display = ' '.join('_' for _ in word)
        return f"🎮 משחק חדש התחיל!\n\n{display}\n\n{HANGMAN_PICS[0]}\n\nנחשו אות! (לדוגמה: א)"
    
    if user_data['current_game'] is None:
        return "❌ אין משחק פעיל. התחל משחק חדש עם /bot_8447253005"
    
    game = user_data['current_game']
    guess = parts[1].strip()
    
    if len(guess) != 1 or not guess.isalpha():
        return "❌ נא לנחש אות אחת בלבד"
    
    if guess in game['guessed']:
        return f"⚠️ כבר ניחשת את האות '{guess}'. נסה אות אחרת"
    
    game['guessed'].append(guess)
    
    word = game['word']
    if guess not in word:
        game['wrong'] += 1
    
    display = ' '.join(c if c in game['guessed'] else '_' for c in word)
    
    response = f"{display}\n\n{HANGMAN_PICS[game['wrong']]}\n\n"
    response += f"אותיות שנוחשו: {', '.join(sorted(game['guessed']))}\n"
    response += f"טעויות: {game['wrong']}/{game['max_wrong']}\n\n"
    
    if '_' not in display:
        user_data['games_won'] += 1
        user_data['current_game'] = None
        save_game_data(data)
        return f"🎉 ניצחת!\n\n{response}המילה הייתה: {word}\n\nניצחונות: {user_data['games_won']} | הפסדים: {user_data['games_lost']}\n\nמשחק חדש: /bot_8447253005"
    
    if game['wrong'] >= game['max_wrong']:
        user_data['games_lost'] += 1
        user_data['current_game'] = None
        save_game_data(data)
        return f"💀 הפסדת!\n\n{response}המילה הייתה: {word}\n\nניצחונות: {user_data['games_won']} | הפסדים: {user_data['games_lost']}\n\nמשחק חדש: /bot_8447253005"
    
    save_game_data(data)
    
    if guess in word:
        return f"✅ נכון!\n\n{response}המשך לנחש..."
    else:
        return f"❌ טעות!\n\n{response}נסה שוב..."