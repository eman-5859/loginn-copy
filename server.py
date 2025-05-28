from flask import Flask, request, jsonify, send_from_directory
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
import os
import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# MongoDB connection with error handling
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/') # Default to localhost if MONGO_URI not set
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    # The ping command is cheap and does not require auth.
    client.admin.command('ping')
    db = client['gamehub']
    users = db['users']
    print(f"✓ Successfully connected to MongoDB at {MONGO_URI}")
except ConnectionFailure as e:
    print(f"✗ Failed to connect to MongoDB at {MONGO_URI}: {e}")
    print("Please ensure MongoDB is running and accessible, or check your MONGO_URI environment variable.")
    exit(1)
except OperationFailure as e:
    print(f"✗ MongoDB authentication failed or invalid database/collection access: {e}")
    print("Please check your MONGO_URI credentials and permissions.")
    exit(1)
except Exception as e:
    print(f"✗ An unexpected error occurred during MongoDB connection: {e}")
    exit(1)

# Helper function to format API responses
def create_response(success, message, data=None, status_code=200):
    response = {
        'success': success,
        'message': message,
        'timestamp': datetime.datetime.utcnow().isoformat()
    }
    if data:
        response['data'] = data
    return jsonify(response), status_code

# Updated Game Achievements System
GAME_ACHIEVEMENTS = {
    'snake': [
        {
            'id': 'snake-1', 
            'title': 'First Slither', 
            'desc': 'Play your first Snake game', 
            'condition': lambda scores: scores.get('snake', 0) > 0
        },
        {
            'id': 'snake-2', 
            'title': 'Growing Appetite', 
            'desc': 'Reach a score of 50', 
            'condition': lambda scores: scores.get('snake', 0) >= 50
        },
        {
            'id': 'snake-3', 
            'title': 'Snake Master', 
            'desc': 'Reach a score of 100', 
            'condition': lambda scores: scores.get('snake', 0) >= 100
        },
        {
            'id': 'snake-4', 
            'title': 'Snake Legend', 
            'desc': 'Reach a score of 200', 
            'condition': lambda scores: scores.get('snake', 0) >= 200
        }
    ],
       'tictactoe': [
        {'id': 'ttt-1', 'title': 'First Blood', 'desc': 'Win your first Tic Tac Toe game', 
         'condition': lambda scores: scores.get('tictactoe_wins', 0) > 0},
        {'id': 'ttt-2', 'title': 'Three in a Row', 'desc': 'Win 3 games in a row', 
         'condition': lambda scores: scores.get('current_streaks', {}).get('tictactoe', 0) >= 3},
        {'id': 'ttt-3', 'title': 'Perfect Game', 'desc': 'Win without opponent scoring', 
         'condition': lambda scores: scores.get('perfect_wins', 0) > 0},
        {'id': 'ttt-4', 'title': 'Quick Win', 'desc': 'Win in just 3 moves', 
         'condition': lambda scores: scores.get('quick_wins', 0) > 0},
        {'id': 'ttt-5', 'title': 'Tic Tac Master', 'desc': 'Win 10 games', 
         'condition': lambda scores: scores.get('tictactoe_wins', 0) >= 10},
        {'id': 'ttt-6', 'title': 'Unstoppable', 'desc': 'Reach a 5-game win streak', 
         'condition': lambda scores: scores.get('max_streaks', {}).get('tictactoe', 0) >= 5},
        {'id': 'ttt-7', 'title': 'Comeback King', 'desc': 'Win after being one move from losing', 
         'condition': lambda scores: scores.get('comeback_wins', 0) > 0},
        {'id': 'ttt-8', 'title': 'Flawless Victory', 'desc': 'Win 5 games without losing', 
         'condition': lambda scores: scores.get('flawless_wins', 0) >= 5},
    ],
    'chess': [
        {
            'id': 'chess-1', 
            'title': 'First Victory', 
            'desc': 'Win your first Chess game', 
            'condition': lambda scores: scores.get('chess_wins', 0) > 0
        },
        {
            'id': 'chess-2', 
            'title': 'Chess Master', 
            'desc': 'Win 10 Chess games', 
            'condition': lambda scores: scores.get('chess_wins', 0) >= 10
        },
        {
            'id': 'chess-3', 
            'title': 'Chess Grandmaster', 
            'desc': 'Win 25 Chess games', 
            'condition': lambda scores: scores.get('chess_wins', 0) >= 25
        },
        {
            'id': 'chess-4', 
            'title': 'Chess Strategist', 
            'desc': 'Play 50 Chess games', 
            'condition': lambda scores: scores.get('chess_plays', 0) >= 50
        }
    ],
    'flappy': [
        {
            'id': 'flappy-1', 
            'title': 'First Flight', 
            'desc': 'Score your first point in Flappy Bird', 
            'condition': lambda scores: scores.get('flappy', 0) > 0
        },
        {
            'id': 'flappy-2', 
            'title': 'High Flyer', 
            'desc': 'Reach a score of 10 in Flappy Bird', 
            'condition': lambda scores: scores.get('flappy', 0) >= 10
        },
        {
            'id': 'flappy-3', 
            'title': 'Sky Master', 
            'desc': 'Reach a score of 25 in Flappy Bird', 
            'condition': lambda scores: scores.get('flappy', 0) >= 25
        },
        {
            'id': 'flappy-4', 
            'title': 'Flying Legend', 
            'desc': 'Reach a score of 50 in Flappy Bird', 
            'condition': lambda scores: scores.get('flappy', 0) >= 50
        }
    ]
}

# Helper function to safely initialize user achievements
def initialize_user_achievements(username):
    """Helper function to ensure user has proper achievements structure"""
    try:
        user = users.find_one({'username': username})
        if not user:
            return False
        
        update_needed = False
        if 'scores' not in user:
            user['scores'] = {}
            update_needed = True
            
        if 'achievements' not in user['scores']:
            user['scores']['achievements'] = {}
            update_needed = True
            
        # Initialize each game's achievements array
        for game in ['snake', 'tictactoe', 'chess', 'flappy']:
            if game not in user['scores']['achievements']:
                user['scores']['achievements'][game] = []
                update_needed = True
        
        if update_needed:
            users.update_one(
                {'username': username},
                {'$set': {'scores.achievements': user['scores']['achievements']}}
            )
        
        return True
    except Exception as e:
        print(f"Error initializing achievements for {username}: {e}")
        return False

# Routes for serving static files
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/dashboard.html')
def serve_dashboard():
    return send_from_directory('.', 'dashboard.html')

@app.route('/games/<path:filename>')
def serve_game_static(filename):
    return send_from_directory('games', filename)

@app.route('/profile(2).html')
def serve_profile():
    return send_from_directory('.', 'profile.html')

# Authentication Routes
@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.json
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        if not all([username, email, password]):
            return create_response(False, 'All fields (username, email, password) are required', status_code=400)

        if users.find_one({'username': username}):
            return create_response(False, f'Username "{username}" already exists', status_code=400)

        if users.find_one({'email': email}):
            return create_response(False, f'Email "{email}" already registered', status_code=400)

        hashed_password = generate_password_hash(password)
        
        # Initialize scores with zeros for all games
        initial_scores = {
            'snake': 0,
            'tictactoe': 0,
            'chess': 0,
            'flappy': 0,
            'tictactoe_plays': 0,
            'tictactoe_wins': 0,
            'chess_plays': 0,
            'chess_wins': 0,
            'chess_draws': 0,
            'chess_losses': 0,
            'achievements': {
                'snake': [],
                'tictactoe': [],
                'chess': [],
                'flappy': []
            }
        }
        
        user_data = {
            'username': username,
            'email': email,
            'password': hashed_password,
            'character': None,
            'high_score': 0,
            'scores': initial_scores,
            'created_at': datetime.datetime.utcnow(),
            'last_login': datetime.datetime.utcnow(),
            'last_played': None,
            'last_played_at': None
        }

        users.insert_one(user_data)
        return create_response(True, 'User created successfully', {
            'username': username,
            'email': email,
            'scores': initial_scores
        })

    except Exception as e:
        return create_response(False, f'Registration failed: {str(e)}', status_code=500)

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')

        if not all([username, password]):
            return create_response(False, 'Username and password required', status_code=400)

        user = users.find_one({'username': username})
        if not user or not check_password_hash(user['password'], password):
            return create_response(False, 'Invalid credentials', status_code=401)

        # Update last login time
        users.update_one(
            {'username': username},
            {'$set': {'last_login': datetime.datetime.utcnow()}}
        )
        
        # Ensure 'scores' sub-fields are present for existing users logging in
        if 'scores' not in user:
            user['scores'] = {}
        
        valid_games = ['snake', 'tictactoe', 'chess', 'flappy']
        for g_type in valid_games:
            if g_type not in user['scores']:
                user['scores'][g_type] = 0
        
        # Initialize tracking fields
        score_fields = ['tictactoe_plays', 'tictactoe_wins', 'chess_plays', 'chess_wins', 'chess_draws', 'chess_losses']
        for field in score_fields:
            if field not in user['scores']:
                user['scores'][field] = 0
        
        # Initialize achievements
        if 'achievements' not in user['scores']:
            user['scores']['achievements'] = {game: [] for game in valid_games}

        # Update the user document with any new fields
        users.update_one({'username': username}, {'$set': {'scores': user['scores']}})

        return create_response(True, 'Login successful', {
            'username': user['username'],
            'character': user.get('character'),
            'high_score': user.get('high_score', 0),
            'scores': user.get('scores', {}),
            'last_played': user.get('last_played'),
            'last_played_at': user.get('last_played_at'),
            'last_login': user.get('last_login')
        })

    except Exception as e:
        return create_response(False, f'Login failed: {str(e)}', status_code=500)

# Game Management Routes
@app.route('/api/start-game', methods=['POST'])
def start_game():
    try:
        data = request.json
        username = data.get('username')
        game_type = data.get('game')

        if not all([username, game_type]):
            return create_response(False, 'Missing required fields: username, game', status_code=400)

        valid_games = ['snake', 'tictactoe', 'chess', 'flappy']
        if game_type not in valid_games:
            return create_response(False, f'Invalid game type. Must be one of: {", ".join(valid_games)}', status_code=400)

        user = users.find_one({'username': username})
        if not user:
            return create_response(False, f'User "{username}" not found', status_code=404)

        users.update_one(
            {'username': username},
            {'$set': {
                'last_played': game_type,
                'last_played_at': datetime.datetime.utcnow()
            }}
        )
        return create_response(True, f'Last played game updated to: {game_type}')

    except Exception as e:
        return create_response(False, f'Error updating last played game: {str(e)}', status_code=500)

@app.route('/api/save-score', methods=['POST'])
def save_score():
    try:
        data = request.json
        username = data.get('username')
        game = data.get('game')
        score = data.get('score')
        result = data.get('result')

        # Define allowed game types for validation
        valid_games = ['snake', 'tictactoe', 'chess', 'flappy']

        # Validate essential fields based on game type
        missing_fields = []
        if username is None: missing_fields.append('username')
        if game is None: missing_fields.append('game')
        
        if game not in valid_games:
            return create_response(False, f'Invalid game type. Must be one of: {", ".join(valid_games)}', status_code=400)

        # Check for specific required fields based on game type
        if game in ['snake', 'flappy', 'tictactoe'] and (score is None or not isinstance(score, (int, float))):
            missing_fields.append('score (must be a number)')
        if game == 'chess' and result not in ['win', 'loss', 'draw']:
            missing_fields.append('result (must be "win", "loss", or "draw")')

        if missing_fields:
            error_message = f"Missing required fields: {', '.join(missing_fields[:-1])} and {missing_fields[-1]}" \
                            if len(missing_fields) > 1 else f"Missing required field: {missing_fields[0]}"
            return create_response(False, error_message, status_code=400)

        user = users.find_one({'username': username})
        if not user:
            return create_response(False, f'User "{username}" not found', status_code=404)

        # Initialize 'scores' and its sub-fields if they don't exist
        if 'scores' not in user:
            user['scores'] = {}
        for g_type in valid_games:
            if g_type not in user['scores']:
                user['scores'][g_type] = 0
        
        score_fields = ['tictactoe_plays', 'tictactoe_wins', 'chess_plays', 'chess_wins', 'chess_draws', 'chess_losses']
        for field in score_fields:
            if field not in user['scores']:
                user['scores'][field] = 0

  # Game-specific updates
        if game == 'tictactoe':
            user['scores']['tictactoe_plays'] = user['scores'].get('tictactoe_plays', 0) + 1
            
            if score == 1:  # Win
                user['scores']['tictactoe_wins'] = user['scores'].get('tictactoe_wins', 0) + 1
                
                # Update streaks
                current_streak = user['scores'].get('current_streaks', {}).get('tictactoe', 0) + 1
                user['scores'].setdefault('current_streaks', {})['tictactoe'] = current_streak
                
                # Update max streak if needed
                max_streak = user['scores'].get('max_streaks', {}).get('tictactoe', 0)
                if current_streak > max_streak:
                    user['scores'].setdefault('max_streaks', {})['tictactoe'] = current_streak
                
                # Check for perfect win (opponent didn't score)
                if additional_data.get('perfect_win'):
                    user['scores']['perfect_wins'] = user['scores'].get('perfect_wins', 0) + 1
                
                # Check for quick win (3 moves)
                if additional_data.get('quick_win'):
                    user['scores']['quick_wins'] = user['scores'].get('quick_wins', 0) + 1
                
                # Check for comeback win
                if additional_data.get('comeback_win'):
                    user['scores']['comeback_wins'] = user['scores'].get('comeback_wins', 0) + 1
                
                # Check for flawless victory (part of streak)
                if current_streak >= 5:
                    user['scores']['flawless_wins'] = user['scores'].get('flawless_wins', 0) + 1
            else:
                # Reset streak on loss
                user['scores'].setdefault('current_streaks', {})['tictactoe'] = 0


        # Initialize achievements if not exists
        initialize_user_achievements(username)

        update_data = {}
        current_high_score = user.get('high_score', 0)
        message = ''

        if game in ['snake', 'flappy']:
            try:
                score = int(score)
            except (ValueError, TypeError):
                return create_response(False, 'Score must be a number for this game type', status_code=400)

            current_game_score = user['scores'].get(game, 0)
            if score > current_game_score:
                update_data[f'scores.{game}'] = score
                message = f'New high score for {game} saved: {score}!'
            else:
                message = f'Score {score} not a new high for {game} (current high score is {current_game_score})'
            
            if score > current_high_score:
                 update_data['high_score'] = score
                 message += " New overall high score!"

        elif game == 'chess':
            new_chess_plays = user['scores']['chess_plays'] + 1
            update_data['scores.chess_plays'] = new_chess_plays
            message = f'Chess game recorded for {username} (Total plays: {new_chess_plays})!'

            if result == 'win':
                new_chess_wins = user['scores']['chess_wins'] + 1
                update_data['scores.chess_wins'] = new_chess_wins
                message += f' {username} won the chess game (Total wins: {new_chess_wins})!'
                if new_chess_wins > current_high_score:
                    update_data['high_score'] = new_chess_wins
                    message += " New overall high score (based on chess wins)!"
            elif result == 'draw':
                update_data['scores.chess_draws'] = user['scores']['chess_draws'] + 1
                message += f' Chess game was a draw for {username} (Total draws: {user["scores"]["chess_draws"] + 1})!'
            elif result == 'loss':
                update_data['scores.chess_losses'] = user['scores']['chess_losses'] + 1
                message += f' {username} lost the chess game (Total losses: {user["scores"]["chess_losses"] + 1})!'

        elif game == 'tictactoe':
            new_tictactoe_plays = user['scores']['tictactoe_plays'] + 1
            update_data['scores.tictactoe_plays'] = new_tictactoe_plays
            message = f'Tic-Tac-Toe game recorded for {username} (Total plays: {new_tictactoe_plays})!'

            try:
                score_value = int(score)
            except (ValueError, TypeError):
                score_value = 0

            if score_value == 1:
                new_tictactoe_wins = user['scores']['tictactoe_wins'] + 1
                update_data['scores.tictactoe_wins'] = new_tictactoe_wins
                message += f' {username} won Tic-Tac-Toe (Total wins: {new_tictactoe_wins})!'
                
                if new_tictactoe_wins > current_high_score:
                    update_data['high_score'] = new_tictactoe_wins
                    message += " New overall high score (based on Tic-Tac-Toe wins)!"
                
                update_data[f'scores.{game}'] = new_tictactoe_wins

        # Perform the update
        if update_data:
            users.update_one(
                {'username': username},
                {'$set': update_data}
            )

        updated_user = users.find_one({'username': username})
        
        return create_response(True, message, {
            'game': game,
            'score_sent': score,
            'result_sent': result,
            'updated_game_scores': updated_user['scores'],
            'high_score': updated_user.get('high_score', 0)
        })

    except Exception as e:
        print(f"Error in save_score: {e}")
        return create_response(False, f'Error saving score: {str(e)}', status_code=500)

@app.route('/api/get-scores', methods=['GET'])
def get_scores():
    try:
        username = request.args.get('username')
        if not username:
            return create_response(False, 'Username required', status_code=400)

        user = users.find_one({'username': username})
        if not user:
            return create_response(False, 'User not found', status_code=404)

        # Ensure scores exist and are initialized
        if 'scores' not in user:
            user['scores'] = {}
        
        valid_games = ['snake', 'tictactoe', 'chess', 'flappy']
        for g_type in valid_games:
            if g_type not in user['scores']:
                user['scores'][g_type] = 0
        
        score_fields = ['tictactoe_plays', 'tictactoe_wins', 'chess_plays', 'chess_wins', 'chess_draws', 'chess_losses']
        for field in score_fields:
            if field not in user['scores']:
                user['scores'][field] = 0

        # Initialize achievements
        initialize_user_achievements(username)

        # Update scores in DB if any new game types or sub-scores were initialized
        users.update_one(
            {'username': username},
            {'$set': {'scores': user['scores']}}
        )

        # Convert datetime objects to ISO format for JSON
        last_played_at_iso = user['last_played_at'].isoformat() if user.get('last_played_at') else None
        last_login_iso = user['last_login'].isoformat() if user.get('last_login') else None

        return create_response(True, 'Scores retrieved', {
            'username': user['username'],
            'scores': user['scores'],
            'high_score': user.get('high_score', 0),
            'last_played': user.get('last_played'),
            'last_played_at': last_played_at_iso,
            'last_login': last_login_iso,
            'character': user.get('character')
        })

    except Exception as e:
        return create_response(False, f'Error retrieving scores: {str(e)}', status_code=500)

# Achievement Routes
@app.route('/api/check-achievements', methods=['POST'])
def check_achievements():
    try:
        data = request.json
        username = data.get('username')
        game = data.get('game')

        if not username or not game:
            return create_response(False, 'Username and game are required', status_code=400)

        # Validate game type
        valid_games = ['snake', 'tictactoe', 'chess', 'flappy']
        if game not in valid_games:
            return create_response(False, f'Invalid game type. Must be one of: {", ".join(valid_games)}', status_code=400)

        user = users.find_one({'username': username})
        if not user:
            return create_response(False, 'User not found', status_code=404)

        # Ensure scores exist
        if 'scores' not in user:
            user['scores'] = {}

        # Initialize achievements structure
        initialize_user_achievements(username)
        
        # Get fresh user data after initialization
        user = users.find_one({'username': username})

        new_achievements = []
        achievements = GAME_ACHIEVEMENTS.get(game, [])
        
        for achievement in achievements:
            try:
                # Check if achievement is already earned
                if achievement['id'] in user['scores']['achievements'][game]:
                    continue
                
                # Safely check if condition is met
                if achievement['condition'](user['scores']):
                    new_achievements.append({
                        'id': achievement['id'],
                        'title': achievement['title'],
                        'desc': achievement['desc']
                    })
                    
                    # Add to user's achievements
                    users.update_one(
                        {'username': username},
                        {'$push': {f'scores.achievements.{game}': achievement['id']}}
                    )
            except Exception as condition_error:
                print(f"Error checking achievement {achievement['id']}: {condition_error}")
                continue

        # Get updated user data for response
        updated_user = users.find_one({'username': username})
        earned_count = len(updated_user['scores']['achievements'].get(game, []))

        return create_response(True, 'Achievements checked', {
            'game': game,
            'new_achievements': new_achievements,
            'total_achievements': len(achievements),
            'earned_achievements': earned_count,
            'all_earned_ids': updated_user['scores']['achievements'].get(game, [])
        })

    except Exception as e:
        print(f"Error in check_achievements: {e}")
        return create_response(False, f'Error checking achievements: {str(e)}', status_code=500)

@app.route('/api/get-achievements', methods=['GET'])
def get_achievements():
    try:
        username = request.args.get('username')
        if not username:
            return create_response(False, 'Username required', status_code=400)

        user = users.find_one({'username': username})
        if not user:
            return create_response(False, 'User not found', status_code=404)

        # Initialize achievements if not exists
        initialize_user_achievements(username)
        
        # Get fresh user data
        user = users.find_one({'username': username})

        # Build response with all games and their achievements
        all_achievements = {}
        total_earned = 0
        total_available = 0
        
        for game_name, game_achievements in GAME_ACHIEVEMENTS.items():
            earned_ids = user['scores']['achievements'].get(game_name, [])
            earned_count = len(earned_ids)
            total_count = len(game_achievements)
            
            total_earned += earned_count
            total_available += total_count
            
            all_achievements[game_name] = {
                'total': total_count,
                'earned': earned_count,
                'earned_ids': earned_ids,
                'achievements': []
            }
            
            for achievement in game_achievements:
                achievement_data = {
                    'id': achievement['id'],
                    'title': achievement['title'],
                    'desc': achievement['desc'],
                    'earned': achievement['id'] in earned_ids
                }
                all_achievements[game_name]['achievements'].append(achievement_data)

        return create_response(True, 'All achievements retrieved', {
            'username': username,
            'achievements': all_achievements,
            'summary': {
                'total_earned': total_earned,
                'total_available': total_available,
                'completion_percentage': round((total_earned / total_available) * 100, 1) if total_available > 0 else 0
            }
        })

    except Exception as e:
        print(f"Error in get_achievements: {e}")
        return create_response(False, f'Error retrieving achievements: {str(e)}', status_code=500)

# User Profile Routes
@app.route('/update-character', methods=['POST'])
def update_character():
    try:
        data = request.json
        username = data.get('username')
        character = data.get('character')

        if not all([username, character]):
            return create_response(False, 'Username and character required', status_code=400)

        result = users.update_one(
            {'username': username},
            {'$set': {'character': character}}
        )

        if result.modified_count > 0:
            return create_response(True, 'Character updated successfully')
        else:
            user_exists = users.find_one({'username': username})
            if user_exists:
                return create_response(False, 'No changes made (character might be the same)', status_code=200)
            else:
                return create_response(False, 'User not found', status_code=404)

    except Exception as e:
        return create_response(False, f'Error updating character: {str(e)}', status_code=500)

# Debug and utility routes
@app.route('/api/debug', methods=['GET'])
def debug():
    try:
        client.admin.command('ping')
        user_count = users.count_documents({})
        recent_users = list(users.find({}, {'username': 1, 'created_at': 1, '_id': 0}).sort('created_at', -1).limit(5))
        
        return create_response(True, 'Debug information', {
            'mongo_connected': True,
            'user_count': user_count,
            'collections': db.list_collection_names(),
            'recent_users': [u['username'] for u in recent_users],
            'total_achievements': sum(len(achievements) for achievements in GAME_ACHIEVEMENTS.values())
        })
    except Exception as e:
        return create_response(False, f'Debug failed: {str(e)}', {
            'mongo_connected': False,
            'error': str(e)
        }, 500)

# Static file serving
@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

# Cache control
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

if __name__ == '__main__':
    print("🎮 GameHub Server Starting...")
    print(f"📊 Total Achievements Available: {sum(len(achievements) for achievements in GAME_ACHIEVEMENTS.values())}")
    app.run(debug=True, port=5005, host='0.0.0.0')