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
    print(f" Successfully connected to MongoDB at {MONGO_URI}")
except ConnectionFailure as e:
    print(f" Failed to connect to MongoDB at {MONGO_URI}: {e}")
    print("Please ensure MongoDB is running and accessible, or check your MONGO_URI environment variable.")
    exit(1)
except OperationFailure as e:
    print(f" MongoDB authentication failed or invalid database/collection access: {e}")
    print("Please check your MONGO_URI credentials and permissions.")
    exit(1)
except Exception as e:
    print(f" An unexpected error occurred during MongoDB connection: {e}")
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

# Routes
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/dashboard.html')
def serve_dashboard():
    return send_from_directory('.', 'dashboard.html')

# Route to serve files from the 'games' folder
@app.route('/games/<path:filename>')
def serve_game_static(filename):
    return send_from_directory('games', filename)
@app.route('/profile(2).html')
def serve_profile():
    return send_from_directory('.', 'profile.html') #

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
            'chess_losses': 0
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
            'last_played': None, # Default to None
            'last_played_at': None # Default to None
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
        
        if 'tictactoe_plays' not in user['scores']: user['scores']['tictactoe_plays'] = 0
        if 'tictactoe_wins' not in user['scores']: user['scores']['tictactoe_wins'] = 0
        if 'chess_plays' not in user['scores']: user['scores']['chess_plays'] = 0
        if 'chess_wins' not in user['scores']: user['scores']['chess_wins'] = 0
        if 'chess_draws' not in user['scores']: user['scores']['chess_draws'] = 0
        if 'chess_losses' not in user['scores']: user['scores']['chess_losses'] = 0

        # It's good practice to update the user document if new fields were added
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

# NEW ENDPOINT: Update last_played when a user *starts* a game
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
        
        if game not in valid_games: # First check for invalid game type
            return create_response(False, f'Invalid game type. Must be one of: {", ".join(valid_games)}', status_code=400)

        # Now check for specific required fields based on a valid game type
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
        
        if 'tictactoe_plays' not in user['scores']: user['scores']['tictactoe_plays'] = 0
        if 'tictactoe_wins' not in user['scores']: user['scores']['tictactoe_wins'] = 0
        if 'chess_plays' not in user['scores']: user['scores']['chess_plays'] = 0
        if 'chess_wins' not in user['scores']: user['scores']['chess_wins'] = 0
        if 'chess_draws' not in user['scores']: user['scores']['chess_draws'] = 0
        if 'chess_losses' not in user['scores']: user['scores']['chess_losses'] = 0


        update_data = {} # Initialize empty, only add score-related updates here
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
            else:
                 message += f' Chess game ended without a specific win/loss/draw for {username}.'
            
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
                
                update_data[f'scores.{game}'] = new_tictactoe_wins # Set main game score to wins
            elif score_value == 0:
                message += f' Tic-Tac-Toe game finished without a win for {username}.'
            
        # Perform the update
        if update_data: # Only update if there's actual score data to modify
            result_update = users.update_one(
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
        
        if 'tictactoe_plays' not in user['scores']: user['scores']['tictactoe_plays'] = 0
        if 'tictactoe_wins' not in user['scores']: user['scores']['tictactoe_wins'] = 0
        if 'chess_plays' not in user['scores']: user['scores']['chess_plays'] = 0
        if 'chess_wins' not in user['scores']: user['scores']['chess_wins'] = 0
        if 'chess_draws' not in user['scores']: user['scores']['chess_draws'] = 0
        if 'chess_losses' not in user['scores']: user['scores']['chess_losses'] = 0

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
            'recent_users': [u['username'] for u in recent_users]
        })
    except Exception as e:
        return create_response(False, f'Debug failed: {str(e)}', {
            'mongo_connected': False,
            'error': str(e)
        }, 500)

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
    app.run(debug=True, port=5005, host='0.0.0.0')