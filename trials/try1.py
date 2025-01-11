import json

def load_intents(file_path):
    """
    Load the intents JSON file.
    """
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

def preprocess_patterns(intents):
    """
    Process intents JSON data to create a dictionary mapping tags to sets of unique pattern words.

    Args:
        intents (dict): A dictionary containing intents with tags and patterns.

    Returns:
        dict: A dictionary mapping tags to sets of unique words from their patterns.
    """
    tag_to_patterns = {}
    
    for intent in intents["intents"]:
        tag = intent["tag"]
        patterns = intent["patterns"]
        
        # Create a set of unique words from all patterns for the tag
        word_set = set()
        for pattern in patterns:
            word_set.update(pattern.lower().split())  # Split pattern into words and add to set
        
        tag_to_patterns[tag] = word_set

    return tag_to_patterns

def match_input(input_string, tag_to_patterns):
    """
    Match a user input string to a tag using the tokenized patterns.
    Find the tag whose patterns have the most overlap with the input words.
    
    Args:
        input_string (str): The input string provided by the user.
        tag_to_patterns (dict): A dictionary mapping tags to sets of pattern words.
        
    Returns:
        str: The tag with the highest match, or "No match found" if no match exists.
    """
    # Convert input_string to a set of words
    input_words = set(input_string.lower().split())
    
    best_match = None
    max_overlap = 0

    # Iterate through each tag and its patterns
    for tag, patterns in tag_to_patterns.items():
        # Calculate overlap (intersection) with each pattern
        overlap = len(input_words & patterns)
        if overlap > max_overlap:  # Update the best match if overlap is higher
            max_overlap = overlap
            best_match = tag

    return best_match if best_match else "No match found"

if __name__ == "__main__":
    # Path to your intents.json file
    file_path = "E:\\STDY\\GIT_PROJECTS\\Phoenix\\data\\intents.json"
    
    # Load and preprocess intents
    intents = load_intents(file_path)
    tag_to_patterns = preprocess_patterns(intents)#returns a dictionary of tags and their patterns
    # print(tag_to_patterns)
    # Example user input
    user_input = "play phoenix"
    
    # Match the input to a tag
    matched_tag = match_input(user_input, tag_to_patterns)
    
    print(f"Matched tag: {matched_tag}")
