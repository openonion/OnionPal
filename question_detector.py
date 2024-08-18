# path: question_detector.py
def is_question(text):
    # Convert to lowercase for easier matching
    text = text.lower()
    
    # Check for question marks
    if '?' in text:
        return True
    
    # Check for common question words at the start
    question_starters = ['what', 'when', 'where', 'who', 'whom', 'whose', 'which', 'why', 'how']
    if any(text.split()[0] == starter for starter in question_starters):
        return True
    
    # Check for common question patterns
    patterns = ['can you', 'could you', 'will you', 'do you', 'does anyone', 'is there', 'are there', 'am i']
    if any(pattern in text for pattern in patterns):
        return True
    
    return False