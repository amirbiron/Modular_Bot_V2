"""
Auto-generated plugin: crypto_tracker
Instruction: תציג את מחיר הביטקוין ותגיב לפקודה /btc
"""

def get_dashboard_widget():
    return {
        "title": "crypto_tracker",
        "value": "Ready",
        "label": "Auto-generated plugin",
        "status": "info",
        "icon": "bi-robot",
    }

def handle_message(text):
    if text.strip().startswith("/crypto_tracker"):
        return 'תציג את מחיר הביטקוין ותגיב לפקודה /btc'
    return None
