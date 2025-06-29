import nltk
import re
import pandas as pd
import random
import os
import csv
import traceback
from nltk.tokenize import word_tokenize
import numpy as np
# Import Word2Vec with try/except to handle potential import errors
try:
    from gensim.models import Word2Vec
    from sklearn.metrics.pairwise import cosine_similarity
    WORD2VEC_AVAILABLE = True
except ImportError as e:
    WORD2VEC_AVAILABLE = False
# Download necessary NLTK data quietly
try:
    nltk.download('punkt', quiet=True)
except Exception:
    pass  # Silently continue if download fails
# Load the dataset with error handling
csv_path = "Dataset.csv"
try:
    with open(csv_path, 'r', encoding='ISO-8859-1') as f:
        reader = csv.reader(f)
        header = next(reader)
    recipes_data = []
    with open(csv_path, 'r', encoding='ISO-8859-1') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        for row in reader:
            if len(row) >= 3:
                recipe = {
                    'TranslatedRecipeName': row[0],
                    'TranslatedIngredients': row[1] if len(row) > 1 else '',
                    'TranslatedInstructions': row[2] if len(row) > 2 else '',
                    'Cleaned-Ingredients': row[-1] if len(row) > 3 else ''
                }
                recipes_data.append(recipe)
    df = pd.DataFrame(recipes_data)
except Exception as e:
    # Create a minimal DataFrame if loading fails
    df = pd.DataFrame({
        'TranslatedRecipeName': ['Example Recipe'],
        'TranslatedIngredients': ['ingredient1, ingredient2, ingredient3'],
        'TranslatedInstructions': ['Step 1. Mix ingredients. Step 2. Cook.'],
        'Cleaned-Ingredients': ['ingredient1, ingredient2, ingredient3']
    })
# Manual implementation of cosine similarity to avoid scipy dependency issues
def manual_cosine_similarity(vec_a, vec_b):
    """Calculate cosine similarity between two vectors without using scipy"""
    dot_product = np.dot(vec_a, vec_b)
    magnitude_a = np.sqrt(np.sum(np.square(vec_a)))
    magnitude_b = np.sqrt(np.sum(np.square(vec_b)))
    # Avoid division by zero
    if magnitude_a == 0 or magnitude_b == 0:
        return 0
    # Cosine similarity
    return dot_product / (magnitude_a * magnitude_b)
# Try to build the Word2Vec model if libraries are available
w2v_model = None
if WORD2VEC_AVAILABLE and not df.empty:
    try:
        # Process ingredients into tokens
        ingredient_sentences = []
        for ing_list in df['Cleaned-Ingredients']:
            if not isinstance(ing_list, str):
                continue
            # Split by comma and tokenize each ingredient
            ingredients = ing_list.lower().split(',')
            for ing in ingredients:
                tokens = word_tokenize(ing.strip())
                if tokens:  # Only add if there are tokens
                    ingredient_sentences.append(tokens)
        # Only build the model if we have enough data
        if len(ingredient_sentences) > 10:
            w2v_model = Word2Vec(sentences=ingredient_sentences, vector_size=100, window=5, min_count=1, workers=4)
    except Exception:
        w2v_model = None
def get_ingredient_vector(ingredient_words):
    """Get the vector representation of ingredients using Word2Vec if available"""
    if not w2v_model:
        return None
    vectors = []
    for word in ingredient_words:
        if word in w2v_model.wv:
            vectors.append(w2v_model.wv[word])
    if vectors:
        return np.mean(vectors, axis=0)
    return None
def get_recipes_by_ingredients(ingredients):
    """Find recipes that match the given ingredients using Word2Vec or scoring-based approach"""
    if not ingredients or not isinstance(ingredients, str):
        # Return random recipes if no ingredients provided or input is invalid
        selected_indices = random.sample(range(len(df)), min(2, len(df)))
        return df.iloc[selected_indices]
    
    # Clean and validate ingredients
    ingredient_list = [ing.strip().lower() for ing in ingredients.split(',') if ing.strip()]
    valid_ingredients = [ing for ing in ingredient_list if len(ing) >= 3]
    
    # If no valid ingredients after cleaning and validation, return empty DataFrame
    if not valid_ingredients:
        return pd.DataFrame()
    
    # Key ingredients to prioritize exact matches
    key_ingredients = ['chicken', 'paneer', 'mutton', 'lamb', 'fish', 'prawn', 'shrimp', 'potato', 'aloo', 'gobi', 'cauliflower', 'palak', 'spinach', 'chana', 'chickpea', 'rajma', 'bean', 'mushroom', 'rice', 'dal', 'lentil', 'tomato', 'onion', 'garlic', 'ginger', 'curry', 'masala', 'spice']
    
    # Check if any of the ingredients are valid food items
    has_valid_food = any(any(key in ing for key in key_ingredients) for ing in valid_ingredients)
    if not has_valid_food:
        return pd.DataFrame()
    
    # Check for presence of key ingredients in user input
    primary_ingredients = [ing for ing in valid_ingredients if any(key in ing for key in key_ingredients)]
    
    # Try using Word2Vec approach if available
    if WORD2VEC_AVAILABLE and w2v_model:
        try:
            # Tokenize and get vector representation
            ingredient_words = []
            for ing in ingredient_list:
                ingredient_words.extend(word_tokenize(ing))
            user_vector = get_ingredient_vector(ingredient_words)
            
            # Fall back to scoring approach if vector creation fails
            if user_vector is None:
                return get_recipes_by_scoring(ingredient_list, primary_ingredients)
            
            # Calculate similarity for each recipe
            recipe_scores = []
            for idx, row in df.iterrows():
                try:
                    cleaned_ing = str(row.get('Cleaned-Ingredients', ''))
                    if not cleaned_ing:
                        continue
                    # Get recipe vector and calculate similarity
                    recipe_ing_words = word_tokenize(cleaned_ing.lower())
                    recipe_vector = get_ingredient_vector(recipe_ing_words)
                    if recipe_vector is None:
                        continue
                    similarity = manual_cosine_similarity(user_vector, recipe_vector)
                    # Boost score for primary ingredients
                    for p_ing in primary_ingredients:
                        if p_ing in cleaned_ing.lower():
                            similarity += 0.3
                    recipe_scores.append((idx, similarity))
                except Exception:
                    continue
            
            # Sort and get top recipes
            recipe_scores.sort(key=lambda x: x[1], reverse=True)
            top_indices = [idx for idx, score in recipe_scores[:2]]
            if top_indices:
                return df.iloc[top_indices]
        except Exception:
            pass
    
    # Fall back to scoring approach
    return get_recipes_by_scoring(ingredient_list, primary_ingredients)
def get_recipes_by_scoring(ingredient_list, primary_ingredients):
    """Fallback method for ingredient matching using a scoring system"""
    recipe_scores = []
    # Score each recipe based on ingredient matches
    for idx, row in df.iterrows():
        try:
            cleaned_ing = str(row.get('Cleaned-Ingredients', ''))
            translated_ing = str(row.get('TranslatedIngredients', ''))
            recipe_ingredients = cleaned_ing.lower() if cleaned_ing else translated_ing.lower()
            score = 0
            # Higher score for primary ingredient matches
            for p_ing in primary_ingredients:
                if p_ing in recipe_ingredients:
                    score += 10
            # Score regular ingredient matches
            for ing in ingredient_list:
                if ing in recipe_ingredients:
                    score += 5
                # Partial matches for word parts
                elif any(part in recipe_ingredients for part in ing.split() if len(part) > 2):
                    score += 2
            recipe_scores.append((idx, score))
        except Exception:
            continue
    # Sort and return top 2 recipes
    recipe_scores.sort(key=lambda x: x[1], reverse=True)
    top_indices = [idx for idx, score in recipe_scores if score > 0][:2]
    # Return empty DataFrame if no matches found
    if not top_indices:
        return pd.DataFrame()
    return df.iloc[top_indices]
def format_translated_recipe(recipes):
    """Format recipe output with translated recipe name and ingredients"""
    if recipes.empty:
        return "No recipe found for the given ingredients. Please try with different ingredients."
    response = "Here are the recipes you can prepare with your ingredients:\n\n"
    try:
        for i, (_, recipe) in enumerate(recipes.iterrows(), 1):
            try:
                # Recipe name and ingredients formatting
                recipe_name = recipe.get('TranslatedRecipeName', 'Untitled Recipe')
                response += f"🍴 Recipe: {recipe_name}\n\n"
                response += "📋 Ingredients:\n"
                ingredients_raw = str(recipe.get('TranslatedIngredients', ''))
                # Format ingredients as bullet points
                if ',' in ingredients_raw:
                    ingredients_list = ingredients_raw.split(',')
                    for ingredient in ingredients_list:
                        clean_ingredient = ingredient.strip()
                        if clean_ingredient:
                            response += f"• {clean_ingredient}\n"
                else:
                    response += f"• {ingredients_raw.strip()}\n"
                # Add separator between recipes
                response += "\n"
                if i < len(recipes):
                    response += "\n"
            except Exception:
                continue
    except Exception:
        return "No recipe found. Please try with different ingredients."
    # Truncate long responses
    if len(response) > 4000:
        response = response[:4000] + "...\n(Response truncated due to length)"
    return response
# Track user sessions
user_sessions = {}
def respond(user_id, user_message):
    """Main function to respond to user queries"""
    try:
        # Initialize user session if not exists
        if user_id not in user_sessions:
            user_sessions[user_id] = {
                "stage": "greeting",
                "ingredients": None,
                "last_message": None,
                "active": True
            }
        session = user_sessions[user_id]
        user_message_clean = user_message.lower().strip() if user_message else ""
        
        # Handle greetings and reset commands
        if any(user_message_clean.startswith(greeting) or user_message_clean == greeting 
               for greeting in ["hi", "hello", "hey", "start over", "reset"]):
            session["stage"] = "ask_ingredients"
            return {"response": "Hello! I'm your Indian recipe assistant. What ingredients do you have available? Please list them separated by commas.", "has_follow_up": False}
        
        # If still in greeting stage, require a greeting first
        if session["stage"] == "greeting":
            return {"response": "Please say 'hi' or 'hello' to start our conversation.", "has_follow_up": False}
        
        # Validate ingredient input in ask_ingredients stage
        if session["stage"] == "ask_ingredients":
            if len(user_message_clean) < 3 or all(len(ing.strip()) < 3 for ing in user_message_clean.split(',')):
                return {"response": "I need valid ingredients to suggest recipes. Please provide ingredients that are at least 3 letters long, separated by commas (like 'rice, tomato, onion').", "has_follow_up": False}
            
            # Check if the ingredients contain any valid food items
            key_ingredients = ['chicken', 'paneer', 'mutton', 'lamb', 'fish', 'prawn', 'shrimp', 'potato', 'aloo', 'gobi', 'cauliflower', 'palak', 'spinach', 'chana', 'chickpea', 'rajma', 'bean', 'mushroom', 'rice', 'dal', 'lentil', 'tomato', 'onion', 'garlic', 'ginger', 'curry', 'masala', 'spice']
            has_valid_food = any(any(key in ing for key in key_ingredients) for ing in user_message_clean.split(','))
            if not has_valid_food:
                return {"response": "I couldn't find any valid food ingredients in your input. Please provide actual food ingredients like 'rice', 'chicken', 'tomato', etc.", "has_follow_up": False}
        
        # Handle yes/no responses in ask_try_different stage
        if session["stage"] == "ask_try_different":
            # Handle positive response
            if any(pos in user_message_clean for pos in ["yes", "yeah", "yep", "sure", "ok", "okay", "y"]):
                session["stage"] = "ask_ingredients"
                return {"response": "Great! What ingredients would you like to use now? Please list them separated by commas.", "has_follow_up": False}
            # Handle negative response
            elif any(neg in user_message_clean for neg in ["no", "nope", "nah", "n", "not"]):
                session["stage"] = "greeting"
                return {"response": "Feel free to come back anytime you want recipe suggestions! Say 'hi' or 'hello' to start a new conversation.", "has_follow_up": False}
            # Treat other responses as ingredients
            else:
                if len(user_message_clean) < 3 or all(len(ing.strip()) < 3 for ing in user_message_clean.split(',')):
                    return {"response": "I need valid ingredients to suggest recipes. Please provide ingredients that are at least 3 letters long, separated by commas (like 'rice, tomato, onion').", "has_follow_up": False}
                recipes = get_recipes_by_ingredients(user_message_clean)
                response = format_translated_recipe(recipes)
                if not recipes.empty:
                    session["stage"] = "ask_try_different"
                    return {"response": response, "has_follow_up": True, "follow_up": "Would you like to try different ingredients? (Yes/No)"}
                else:
                    session["stage"] = "ask_try_different"
                    return {"response": "I couldn't find any specific recipes with those ingredients. Would you like to try different ingredients? (Yes/No)", "has_follow_up": False}
        # Handle direct ingredient/recipe queries
        if "recipe" in user_message_clean or "cook" in user_message_clean or "make" in user_message_clean or "," in user_message or "with" in user_message_clean:
            potential_ingredients = user_message_clean
            if "with" in potential_ingredients:
                potential_ingredients = potential_ingredients.split("with")[1].strip()
            # Validate ingredient input
            if len(potential_ingredients) < 3 or all(len(ing.strip()) < 3 for ing in potential_ingredients.split(',')):
                return {"response": "I need valid ingredients to suggest recipes. Please provide ingredients that are at least 3 letters long, separated by commas (like 'rice, tomato, onion').", "has_follow_up": False}
            recipes = get_recipes_by_ingredients(potential_ingredients)
            response = format_translated_recipe(recipes)
            if not recipes.empty:
                session["stage"] = "ask_try_different"
                return {"response": response, "has_follow_up": True, "follow_up": "Would you like to try different ingredients? (Yes/No)"}
            else:
                session["stage"] = "ask_try_different"
                return {"response": "I couldn't find any specific recipes with those ingredients. Would you like to try different ingredients? (Yes/No)", "has_follow_up": False}
        # Handle general food queries
        if any(food_keyword in user_message_clean for food_keyword in ["food", "cuisine", "dish", "spice", "indian"]):
            return {
                "response": "Indian cuisine is diverse and flavorful, known for its use of spices like turmeric, cumin, and garam masala. Common dishes include curry, biryani, and various vegetarian options.",
                "has_follow_up": True,
                "follow_up": "Would you like to find recipes based on specific ingredients? Just list what you have available."
            }
        # Default: treat as ingredient list
        if len(user_message_clean) < 3 or all(len(ing.strip()) < 3 for ing in user_message_clean.split(',')):
            return {"response": "I need valid ingredients to suggest recipes. Please provide ingredients that are at least 3 letters long, separated by commas (like 'rice, tomato, onion').", "has_follow_up": False}
        recipes = get_recipes_by_ingredients(user_message_clean)
        response = format_translated_recipe(recipes)
        if not recipes.empty:
            session["stage"] = "ask_try_different"
            return {"response": response, "has_follow_up": True, "follow_up": "Would you like to try different ingredients? (Yes/No)"}
        else:
            session["stage"] = "ask_try_different"
            return {"response": "I couldn't find any specific recipes with those ingredients. Would you like to try different ingredients? (Yes/No)", "has_follow_up": False}
    except Exception as e:
        return {"response": "I encountered an error. Please try again with a simpler query about Indian recipes.", "has_follow_up": False}
# Command-line testing code
if __name__ == "__main__":
    print("QuickBite")
    print("Say 'hi' or 'hello' to start!")
    try:
        # Test basic functionality
        test_response = respond("test_user", "hi")
        print("Test greeting response:", test_response['response'][:50] + "...")
        test_ingredients = "chicken, onion"
        test_response = respond("test_user", test_ingredients)
        print(f"\nTest ingredient search for '{test_ingredients}':")
        print(test_response['response'][:200] + "...\n")
        print("Interactive mode starting now:")
    except Exception as e:
        print(f"Error during startup tests: {str(e)}")  
    # Interactive conversation loop
    while True:
        try:
            user_input = input("You: ").strip()
            response = respond("test_user", user_input)
            print("Assistant:", response['response'])
            if response.get('has_follow_up') and response.get('follow_up'):
                print("Assistant:", response['follow_up'])
        except Exception as e:
            print(f"Error: {str(e)}")
            print("Assistant: Sorry, something went wrong. Please try again.")
