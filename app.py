from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from chatbot import respond
import os
import json
import pickle
from datetime import datetime
import uuid
import random
from jose import jwt

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'quickbite_secret_key')

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please login to access this page'
login_manager.login_message_category = 'info'

# Database files
USERS_DB_FILE = 'users.pickle'
RECIPES_DB_FILE = 'recipes.pickle'
COLLECTIONS_DB_FILE = 'collections.pickle'
RATINGS_DB_FILE = 'ratings.pickle'
MEAL_PLANS_DB_FILE = 'meal_plans.pickle'

# Load or create databases
def load_or_create_db(filename, default={}):
    if os.path.exists(filename):
        try:
            with open(filename, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"Error loading {filename}: {str(e)}")
            return default
    else:
        try:
            with open(filename, 'wb') as f:
                pickle.dump(default, f)
            return default
        except Exception as e:
            print(f"Error creating {filename}: {str(e)}")
            return default

# Load all databases
users = load_or_create_db(USERS_DB_FILE)
recipes = load_or_create_db(RECIPES_DB_FILE)
collections = load_or_create_db(COLLECTIONS_DB_FILE)
ratings = load_or_create_db(RATINGS_DB_FILE)
meal_plans = load_or_create_db(MEAL_PLANS_DB_FILE)

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username, email):
        self.id = id
        self.username = username
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    if user_id in users:
        user_data = users[user_id]
        return User(user_id, user_data['username'], user_data['email'])
    return None

def save_db(data, filename):
    try:
        with open(filename, 'wb') as f:
            pickle.dump(data, f)
    except Exception as e:
        print(f"Error saving {filename}: {str(e)}")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Find user by email
        user_id = None
        for uid, user_data in users.items():
            if user_data['email'] == email:
                user_id = uid
                break
        
        if user_id and check_password_hash(users[user_id]['password'], password):
            # Log the user in directly
            user = User(user_id, users[user_id]['username'], users[user_id]['email'])
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('chat_page'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if email already exists
        for user_data in users.values():
            if user_data['email'] == email:
                flash('Email already registered', 'error')
                return render_template('signup.html')
        
        # Create user directly
        user_id = str(uuid.uuid4())
        users[user_id] = {
            'username': username,
            'email': email,
            'password': generate_password_hash(password)
        }
        save_db(users, USERS_DB_FILE)
        
        # Log the user in
        user = User(user_id, username, email)
        login_user(user)
        flash('Account created successfully!', 'success')
        return redirect(url_for('chat_page'))
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('home'))

@app.route('/chat')
@login_required
def chat_page():
    return render_template('chat.html', user=current_user)

@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        user_id = current_user.id
        
        # Get response from chatbot
        result = respond(user_id, user_message)
        
        # Format response properly for the frontend
        if isinstance(result, dict):
            # If the result is already a dict, use it directly
            response_data = result
        else:
            # Otherwise, wrap the string result
            response_data = {
                'response': result,
                'has_follow_up': False,
                'follow_up': None
            }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error in chat API: {str(e)}")
        return jsonify({
            'response': "Sorry, I encountered an error. Please try again.",
            'has_follow_up': False,
            'follow_up': None
        })

# New routes for recipe features
@app.route('/recipes')
@login_required
def recipe_list():
    return render_template('recipes.html', recipes=recipes)

@app.route('/recipe/<recipe_id>')
@login_required
def recipe_detail(recipe_id):
    recipe = recipes.get(recipe_id)
    if not recipe:
        flash('Recipe not found', 'error')
        return redirect(url_for('recipe_list'))
    
    # Get ratings for this recipe
    recipe_ratings = [r for r in ratings.values() if r['recipe_id'] == recipe_id]
    avg_rating = sum(r['rating'] for r in recipe_ratings) / len(recipe_ratings) if recipe_ratings else 0
    
    # Check if user has rated this recipe
    user_rating = next((r for r in recipe_ratings if r['user_id'] == current_user.id), None)
    
    return render_template('recipe_detail.html', 
                         recipe=recipe, 
                         avg_rating=avg_rating,
                         user_rating=user_rating)

@app.route('/rate-recipe', methods=['POST'])
@login_required
def rate_recipe():
    data = request.get_json()
    recipe_id = data.get('recipe_id')
    rating = data.get('rating')
    
    if not recipe_id or not rating:
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Save rating
    rating_id = str(uuid.uuid4())
    ratings[rating_id] = {
        'id': rating_id,
        'recipe_id': recipe_id,
        'user_id': current_user.id,
        'rating': rating,
        'timestamp': datetime.now().isoformat()
    }
    save_db(ratings, RATINGS_DB_FILE)
    
    return jsonify({'success': True})

@app.route('/collections')
@login_required
def user_collections():
    user_collections = [c for c in collections.values() if c['user_id'] == current_user.id]
    return render_template('collections.html', collections=user_collections)

@app.route('/create-collection', methods=['POST'])
@login_required
def create_collection():
    name = request.form.get('name')
    description = request.form.get('description')
    
    if not name:
        flash('Collection name is required', 'error')
        return redirect(url_for('user_collections'))
    
    collection_id = str(uuid.uuid4())
    collections[collection_id] = {
        'id': collection_id,
        'user_id': current_user.id,
        'name': name,
        'description': description,
        'recipes': [],
        'created_at': datetime.now().isoformat()
    }
    save_db(collections, COLLECTIONS_DB_FILE)
    
    flash('Collection created successfully', 'success')
    return redirect(url_for('user_collections'))

@app.route('/add-to-collection', methods=['POST'])
@login_required
def add_to_collection():
    collection_id = request.form.get('collection_id')
    recipe_id = request.form.get('recipe_id')
    
    if not collection_id or not recipe_id:
        flash('Missing required fields', 'error')
        return redirect(request.referrer)
    
    collection = collections.get(collection_id)
    if not collection or collection['user_id'] != current_user.id:
        flash('Invalid collection', 'error')
        return redirect(request.referrer)
    
    if recipe_id not in collection['recipes']:
        collection['recipes'].append(recipe_id)
        save_db(collections, COLLECTIONS_DB_FILE)
        flash('Recipe added to collection', 'success')
    
    return redirect(request.referrer)

@app.route('/meal-planner')
@login_required
def meal_planner():
    user_plans = [p for p in meal_plans.values() if p['user_id'] == current_user.id]
    return render_template('meal_planner.html', plans=user_plans)

@app.route('/create-meal-plan', methods=['POST'])
@login_required
def create_meal_plan():
    name = request.form.get('name')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    
    if not all([name, start_date, end_date]):
        flash('All fields are required', 'error')
        return redirect(url_for('meal_planner'))
    
    plan_id = str(uuid.uuid4())
    meal_plans[plan_id] = {
        'id': plan_id,
        'user_id': current_user.id,
        'name': name,
        'start_date': start_date,
        'end_date': end_date,
        'meals': {},
        'created_at': datetime.now().isoformat()
    }
    save_db(meal_plans, MEAL_PLANS_DB_FILE)
    
    flash('Meal plan created successfully', 'success')
    return redirect(url_for('meal_planner'))

@app.route('/share-recipe/<recipe_id>')
@login_required
def share_recipe(recipe_id):
    recipe = recipes.get(recipe_id)
    if not recipe:
        flash('Recipe not found', 'error')
        return redirect(url_for('recipe_list'))
    
    # Generate shareable URL
    share_url = url_for('view_shared_recipe', recipe_id=recipe_id, _external=True)
    return render_template('share_recipe.html', recipe=recipe, share_url=share_url)

@app.route('/shared/<recipe_id>')
def view_shared_recipe(recipe_id):
    recipe = recipes.get(recipe_id)
    if not recipe:
        flash('Recipe not found', 'error')
        return redirect(url_for('home'))
    
    return render_template('shared_recipe.html', recipe=recipe)

if __name__ == '__main__':
    # Determine if we're running on a local machine or a server
    host = '127.0.0.1'  # Default to localhost
    
    # Check if we should bind to all interfaces (for mobile access)
    if os.environ.get('BIND_ALL', '').lower() == 'true':
        host = '0.0.0.0'
        print(f"Starting QuickBite on http://{host}:8080")
        print("Access on your phone by using your computer's IP address")
    else:
        print(f"Starting QuickBite on http://{host}:8080")
    
    app.run(debug=True, host=host, port=8080)
