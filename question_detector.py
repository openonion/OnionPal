# path: question_detector.py
def is_question(text):
    # Handle empty or whitespace-only messages
    if not text or not text.strip():
        return False

    # Split the text into words and ensure there's at least one word
    words = text.strip().split()
    if not words:
        return False

    question_starters = ["what", "when", "where", "which", "who", "whom", "whose", "why", "how"]
    
    # Check if the first word is a question starter
    if any(words[0].lower() == starter for starter in question_starters):
        return True
    
    # Check if the text ends with a question mark
    return text.strip().endswith("?")