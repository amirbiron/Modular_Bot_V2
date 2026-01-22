def get_dashboard_widget():
    return {
        "title": "מונה מילים",
        "value": "0",
        "label": "מילים נספרו",
        "status": "info",
        "icon": "bi-chat-left-text"
    }

def handle_message(text):
    if not text.startswith('/word_counter'):
        return None
    
    message = text[len('/word_counter'):].strip()
    
    if not message:
        return "שלח לי טקסט אחרי הפקודה /word_counter ואספור כמה מילים יש בו!"
    
    words = message.split()
    word_count = len(words)
    
    if word_count == 1:
        return "שלחת הודעה עם מילה אחת"
    elif word_count == 2:
        return "שלחת הודעה עם 2 מילים"
    else:
        return f"שלחת הודעה עם {word_count} מילים"