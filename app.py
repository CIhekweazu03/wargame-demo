from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit, join_room, leave_room
import uuid
import json
from datetime import datetime
import boto3
import time
import random
import threading

app = Flask(__name__, static_folder='static')
app.secret_key = 'your_secret_key'  # Replace with a real secret key
socketio = SocketIO(app, cors_allowed_origins="*")

# In-memory storage for our proof of concept
games = {}
teams = {}
users = {}
messages = []

# Initialize AWS Bedrock client
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
model_id = 'us.anthropic.claude-3-7-sonnet-20250219-v1:0'

# Add this function to app.py
def generate_scenario_update(current_scenario, team_messages, decision):
    """
    Use AWS Bedrock to generate a scenario update based on the team's decision.
    
    Args:
        current_scenario (str): The current scenario description
        team_messages (list): Recent team chat messages for context
        decision (str): The team leader's decision
        
    Returns:
        str: The updated scenario
    """
    try:
        # Format recent team messages for context
        formatted_messages = "\n".join([
            f"{users.get(msg['user_id'], {}).get('role', 'Unknown')} {users.get(msg['user_id'], {}).get('name', 'User')}: {msg['content']}"
            for msg in team_messages[-10:]  # Include last 10 messages
        ])
        
        # Create prompt for Claude
        prompt = f"""
        You are the narrator of an interactive wargame. Your role is to update the scenario based on the team's decision.

        CURRENT SCENARIO:
        {current_scenario}

        TEAM DISCUSSION (MOST RECENT):
        {formatted_messages}

        TEAM DECISION:
        {decision}

        Please provide an updated scenario based on this decision. Your response should:
        1. Acknowledge the team's decision. This could be in the form of "As a result of the team's decision to [decision], [describe the immediate outcome]."
        2. Describe realistic consequences (both intended and unintended)
        3. Introduce new challenges or developments
        4. End with the current state of affairs and implicit options for future decisions
        5. Be approximately 250 words in length
        6. Never make it clear that they are directly interacting with a LLM. Instead, write as if you are a narrator describing what happened as a result of their actions.
        6a. So, if they say something inappropriate or out of line, rather than saying "that is not allowed" or "you can't do that", you would say something like "the team leader's suggestion was met with skepticism" or we cannot proceed with those actions due to X, Y, Z.
        6b. We effectively never should break character and should always write as if it is a script for a narrator. Don't add any ahems or clears throat or anything like that.

        The tone should be objective and realistic, reflecting a serious geopolitical/military simulation.
        """
        
        # Prepare request for Bedrock
        request_body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "temperature": 0.7,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        })
        
        # Call Bedrock
        response = bedrock.invoke_model(
            modelId=model_id,
            contentType='application/json',
            accept='application/json',
            body=request_body
        )
        
        # Parse the response
        response_body = json.loads(response['body'].read())
        content = response_body.get('content', [])
        
        if content and isinstance(content, list) and 'text' in content[0]:
            return content[0]['text'].strip()
        else:
            print("Unexpected response format from Bedrock")
            return f"{current_scenario}\n\nAfter the team's decision to {decision}, the situation continues to develop..."
    
    except Exception as e:
        print(f"Error calling Bedrock: {str(e)}")
        # Fallback response if the API call fails
        return f"{current_scenario}\n\nAfter the team's decision to {decision}, the situation continues to develop. [AI generation failed, please try again]"

def generate_ai_response(user_id, team_id, scenario, recent_messages, role):
    """
    Generate an AI teammate response based on the current scenario and chat history.
    
    Args:
        user_id (str): The ID of the AI user
        team_id (str): The team ID
        scenario (str): The current scenario text
        recent_messages (list): Recent chat messages for context
        role (str): The AI teammate's role (e.g., "Military Advisor")
        
    Returns:
        str: The AI teammate's response
    """
    try:
        # Format recent team messages for context
        formatted_messages = "\n".join([
            f"{users.get(msg['user_id'], {}).get('role', 'Unknown')} {users.get(msg['user_id'], {}).get('name', 'User')}: {msg['content']}"
            for msg in recent_messages[-10:]  # Include last 10 messages
        ])
        
        # Create prompt for Claude
        prompt = f"""
        You are a {role} on a crisis management team. Your goal is to provide advice based on your expertise.
        
        CURRENT SCENARIO:
        {scenario}
        
        RECENT TEAM DISCUSSION:
        {formatted_messages}
        
        Based on the current scenario and team discussion, provide a response as the {role}.
        Your response should:
        1. Be concise (at most 75-100 words)
        2. Focus on your specific area of expertise based on your role
        3. Provide actionable advice or insights
        4. Consider both short-term and long-term implications
        5. Respond directly to any questions or points raised in the recent discussion that are relevant to your role
        
        IMPORTANT FORMATTING INSTRUCTIONS:
        - Do NOT use markdown formatting (no asterisks for bold/italic, no hashtags for headers)
        - Use plain text formatting only
        - Avoid gendered language and pronouns (don't use he/she/him/her).
        - For emphasis, use ALL CAPS sparingly instead of bold/italic
        - For lists, use simple dashes or plain text numbering (1., 2., etc.)
        - Separate sections with line breaks, not markdown headers
        
        Your tone should be professional but conversational, as if you're speaking in a team meeting.
        """
        
        # Prepare request for Bedrock
        request_body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 500,
            "temperature": 0.7,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        })
        
        # Call Bedrock
        response = bedrock.invoke_model(
            modelId=model_id,
            contentType='application/json',
            accept='application/json',
            body=request_body
        )
        
        # Parse the response
        response_body = json.loads(response['body'].read())
        content = response_body.get('content', [])
        
        if content and isinstance(content, list) and 'text' in content[0]:
            return content[0]['text'].strip()
        else:
            print("Unexpected response format from Bedrock")
            return "I'm analyzing the situation and will provide insights shortly."
    
    except Exception as e:
        print(f"Error calling Bedrock for AI teammate: {str(e)}")
        return "I'm having trouble connecting right now. I'll try to respond again shortly."

# Add this function to app.py to handle AI teammate creation
def create_ai_teammate(team_id, role):
    """
    Create an AI teammate with a specific role for a team.
    
    Args:
        team_id (str): The team ID
        role (str): The role of the AI teammate
        
    Returns:
        str: The user ID of the AI teammate
    """
    user_id = str(uuid.uuid4())
    
    # Name the AI based on role
    role_names = {
        "Military Advisor": "Gen. Anderson",
        "Economic Advisor": "Dr. Matthews",
        "Intelligence Officer": "Agent Chen",
        "Diplomatic Advisor": "Ambassador Rivera",
        "Science Advisor": "Dr. Patel"
    }
    
    name = role_names.get(role, f"AI {role}")
    
    # Create the user
    users[user_id] = {
        'name': name,
        'role': role,
        'team_id': team_id,
        'is_ai': True,  # Flag to identify AI teammates
        'joined_at': datetime.now().isoformat()
    }
    
    # Add to team
    teams[team_id]['members'].append(user_id)
    
    # Also add AI user to the AI teammates list for this team
    if 'ai_teammates' not in teams[team_id]:
        teams[team_id]['ai_teammates'] = []
    
    teams[team_id]['ai_teammates'].append(user_id)
    
    return user_id

# Updated function to trigger AI responses only when requested
def trigger_ai_responses(team_id, human_message=None):
    """
    Trigger responses from all AI teammates in a team when explicitly requested.
    
    Args:
        team_id (str): The team ID
        human_message (dict, optional): The message that triggered the AI responses
    """
    if team_id not in teams or 'ai_teammates' not in teams[team_id]:
        print(f"No AI teammates found for team {team_id}")
        return
        
    # Check if the human message contains a trigger word
    # Make this very generous to catch various forms
    trigger_words = ["thought", "thoughts", "advice", "input", "feedback", "comment", "opinion", "?"]
    should_respond = False
    
    if human_message and 'content' in human_message:
        message_lower = human_message['content'].lower()
        print(f"Checking message for triggers: '{message_lower}'")
        
        # More liberal matching logic
        should_respond = any(trigger in message_lower for trigger in trigger_words)
        print(f"Should AI respond: {should_respond}")
    
    if not should_respond:
        print("No trigger words found, AI will not respond")
        return
    
    print(f"AI response triggered for team {team_id}")
    
    # Get the current game
    game_id = teams[team_id]['game_id']
    current_scenario = games[game_id]['scenario']
    
    # Get recent team messages for context
    team_messages = [msg for msg in messages if msg['team_id'] == team_id][-15:]
    
    # First, emit "typing" indicators for all AI teammates
    for ai_user_id in teams[team_id]['ai_teammates']:
        print(f"Sending typing indicator for AI {users[ai_user_id]['name']}")
        socketio.emit('typing_indicator', {
            'user_id': ai_user_id,
            'user_name': users[ai_user_id]['name'],
            'role': users[ai_user_id]['role'],
            'is_typing': True
        }, room=team_id)
    
    # Have each AI teammate respond with a slight delay between them
    for i, ai_user_id in enumerate(teams[team_id]['ai_teammates']):
        # Get AI role
        role = users[ai_user_id]['role']
        
        # Add a delay based on position in the list to make responses feel natural
        # First advisor responds quicker, later ones take longer
        delay_time = random.uniform(2.0 + i*1.5, 4.0 + i*2.0)
        print(f"AI {users[ai_user_id]['name']} will respond in {delay_time} seconds")
        time.sleep(delay_time)
        
        # Generate a response
        print(f"Generating response for AI {users[ai_user_id]['name']}")
        ai_response = generate_ai_response(
            ai_user_id,
            team_id,
            current_scenario,
            team_messages,
            role
        )
        
        # Turn off typing indicator
        socketio.emit('typing_indicator', {
            'user_id': ai_user_id,
            'is_typing': False
        }, room=team_id)
        
        # Send the message
        new_message = {
            'user_id': ai_user_id,
            'team_id': team_id,
            'content': ai_response,
            'timestamp': datetime.now().isoformat()
        }
        
        messages.append(new_message)
        
        # Broadcast to team
        print(f"Sending AI response from {users[ai_user_id]['name']}")
        socketio.emit('team_message', {
            'type': 'chat',
            'user_id': ai_user_id,
            'user_name': users[ai_user_id]['name'],
            'role': role,
            'content': ai_response,
            'timestamp': datetime.now().isoformat()
        }, room=team_id)

@app.route('/')
def index():
    return render_template('index.html')

# API routes for game management
@app.route('/api/games', methods=['POST'])
def create_game():
    data = request.json
    game_id = str(uuid.uuid4())
    
    initial_scenario = data.get('scenario', 'Default scenario')
    
    games[game_id] = {
        'scenario': initial_scenario,
        'state': 'active',
        'teams': [],
        'created_at': datetime.now().isoformat(),
        'scenario_history': [{
            'scenario': initial_scenario,
            'timestamp': datetime.now().isoformat()
        }]
    }
    
    return jsonify({'game_id': game_id})

# API route for user management
@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.json
    team_id = data.get('team_id')
    
    if team_id not in teams:
        return jsonify({'error': 'Team not found'}), 404
    
    user_id = str(uuid.uuid4())
    users[user_id] = {
        'name': data.get('name', 'Anonymous'),
        'role': data.get('role', 'Member'),
        'team_id': team_id
    }
    
    teams[team_id]['members'].append(user_id)
    
    return jsonify({'user_id': user_id})

@app.route('/api/teams', methods=['GET', 'POST'])
def teams_endpoint():
    if request.method == 'POST':
        # Create a new team
        data = request.json
        game_id = data.get('game_id')
        
        if game_id not in games:
            return jsonify({'error': 'Game not found'}), 404
        
        team_id = str(uuid.uuid4())
        teams[team_id] = {
            'name': data.get('name', f'Team {len(games[game_id]["teams"]) + 1}'),
            'game_id': game_id,
            'members': [],
            'ai_teammates': [],  # New field for AI teammates
            'created_at': datetime.now().isoformat()
        }
        
        games[game_id]['teams'].append(team_id)
        
        # Create AI teammates if requested
        ai_roles = data.get('ai_roles', [])
        for role in ai_roles:
            create_ai_teammate(team_id, role)
        
        return jsonify({
            'team_id': team_id,
            'ai_teammates': len(ai_roles)
        })
    else:
        # GET method - List all teams
        teams_list = []
        
        for team_id, team in teams.items():
            game_id = team.get('game_id')
            # Only include teams from active games
            if game_id in games and games[game_id].get('state') == 'active':
                teams_list.append({
                    'id': team_id,
                    'name': team.get('name', 'Unnamed Team'),
                    'member_count': len(team.get('members', [])),
                    'ai_count': len(team.get('ai_teammates', [])),
                    'created_at': team.get('created_at', '')
                })
        
        return jsonify({'teams': teams_list})

# Replace the existing handle_team_chat function in app.py with this improved version

@socketio.on('team_chat')
def handle_team_chat(data):
    """
    Handle incoming team chat messages and trigger AI responses when appropriate.
    """
    user_id = data.get('user_id')
    team_id = data.get('team_id')
    message = data.get('message')
    
    print(f"Received chat message: '{message}' from user {user_id} in team {team_id}")
    
    if not user_id or not team_id or not message:
        print("Missing data in team_chat event")
        return {'status': 'error', 'message': 'Missing required data'}
    
    if user_id not in users:
        print(f"User {user_id} not found")
        return {'status': 'error', 'message': 'User not found'}
        
    if team_id not in teams:
        print(f"Team {team_id} not found")
        return {'status': 'error', 'message': 'Team not found'}
    
    try:
        # Store the message
        new_message = {
            'user_id': user_id,
            'team_id': team_id,
            'content': message,
            'timestamp': datetime.now().isoformat()
        }
        messages.append(new_message)
        
        # Broadcast to team
        emit('team_message', {
            'type': 'chat',
            'user_id': user_id,
            'user_name': users[user_id]['name'],
            'role': users[user_id]['role'],
            'content': message,
            'timestamp': datetime.now().isoformat()
        }, room=team_id)
        
        # Check for AI teammates and trigger words
        if 'ai_teammates' in teams[team_id] and teams[team_id]['ai_teammates']:
            # Check if message contains trigger words
            trigger_words = ["thought", "thoughts", "advice", "input", "feedback", "?"]
            message_lower = message.lower()
            should_respond = any(trigger in message_lower for trigger in trigger_words)
            
            if should_respond:
                print(f"Trigger word detected in message '{message}'")
                # Trigger AI responses in a separate thread to avoid blocking
                threading.Thread(
                    target=trigger_ai_responses,
                    args=(team_id, new_message)
                ).start()
            else:
                print(f"No trigger word found in message '{message}'")
        
        return {'status': 'success'}
        
    except Exception as e:
        print(f"Error processing team chat: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'status': 'error', 'message': str(e)}
    

# Update the join_team socket handler to announce AI teammates
@socketio.on('join_team')
def handle_join_team(data):
    user_id = data.get('user_id')
    team_id = data.get('team_id')
    get_history = data.get('get_history', False)
    
    if user_id in users and team_id in teams:
        join_room(team_id)
        user_name = users[user_id]['name']
        user_role = users[user_id]['role']
        
        # Add a joined_at timestamp to the user in the team
        if 'joined_at' not in users[user_id]:
            users[user_id]['joined_at'] = datetime.now().isoformat()
        
        # Notify team members
        emit('team_message', {
            'type': 'system',
            'content': f"{user_name} ({user_role}) has joined the team."
        }, room=team_id)
        
        # Get the game
        game_id = teams[team_id]['game_id']
        
        # Send current scenario
        emit('scenario_update', {
            'scenario': games[game_id]['scenario']
        }, room=request.sid)
        
        # Send scenario history if requested
        if get_history:
            emit('scenario_history', {
                'history': games[game_id].get('scenario_history', [])
            }, room=request.sid)
            
            # Also send previous messages
            team_chat_history = [
                {
                    'type': 'chat',
                    'user_id': msg['user_id'],
                    'user_name': users.get(msg['user_id'], {}).get('name', 'Unknown'),
                    'role': users.get(msg['user_id'], {}).get('role', 'Unknown'),
                    'content': msg['content'],
                    'timestamp': msg['timestamp']
                }
                for msg in messages 
                if msg['team_id'] == team_id
            ]
            
            for msg in team_chat_history:
                emit('team_message', msg, room=request.sid)
        
        # Show list of AI teammates if any exist
        if 'ai_teammates' in teams[team_id] and teams[team_id]['ai_teammates']:
            ai_team_members = []
            for ai_id in teams[team_id]['ai_teammates']:
                if ai_id in users:
                    ai_team_members.append(f"{users[ai_id]['name']} ({users[ai_id]['role']})")
            
            if ai_team_members:
                emit('team_message', {
                    'type': 'system',
                    'content': f"AI team members: {', '.join(ai_team_members)}. Ask for their 'thoughts?' to get their input."
                }, room=request.sid)

# Add a socket event for typing indicators
@socketio.on('typing_indicator')
def handle_typing_indicator(data):
    """
    Handle typing indicator events, broadcasting them to the team.
    """
    user_id = data.get('user_id')
    team_id = data.get('team_id')
    is_typing = data.get('is_typing', False)
    
    if user_id in users and team_id in teams:
        emit('typing_indicator', {
            'user_id': user_id,
            'user_name': users[user_id]['name'],
            'role': users[user_id]['role'],
            'is_typing': is_typing
        }, room=team_id, include_self=False)  # Don't send back to sender


# Socket.IO event handlers
@socketio.on('connect')
def handle_connect():
    print('Client connected:', request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected:', request.sid)

@socketio.on('join_team')
def handle_join_team(data):
    user_id = data.get('user_id')
    team_id = data.get('team_id')
    get_history = data.get('get_history', False)
    
    if user_id in users and team_id in teams:
        join_room(team_id)
        user_name = users[user_id]['name']
        user_role = users[user_id]['role']
        
        # Add a joined_at timestamp to the user in the team
        if 'joined_at' not in users[user_id]:
            users[user_id]['joined_at'] = datetime.now().isoformat()
        
        # Notify team members
        emit('team_message', {
            'type': 'system',
            'content': f"{user_name} ({user_role}) has joined the team."
        }, room=team_id)
        
        # Get the game
        game_id = teams[team_id]['game_id']
        
        # Send current scenario
        emit('scenario_update', {
            'scenario': games[game_id]['scenario']
        }, room=request.sid)
        
        # Send scenario history if requested
        if get_history:
            emit('scenario_history', {
                'history': games[game_id].get('scenario_history', [])
            }, room=request.sid)
            
            # Also send previous messages
            team_chat_history = [
                {
                    'type': 'chat',
                    'user_id': msg['user_id'],
                    'user_name': users.get(msg['user_id'], {}).get('name', 'Unknown'),
                    'role': users.get(msg['user_id'], {}).get('role', 'Unknown'),
                    'content': msg['content'],
                    'timestamp': msg['timestamp']
                }
                for msg in messages 
                if msg['team_id'] == team_id
            ]
            
            for msg in team_chat_history:
                emit('team_message', msg, room=request.sid)


@socketio.on('submit_decision')
def handle_decision(data):
    user_id = data.get('user_id')
    team_id = data.get('team_id')
    decision = data.get('decision')
    
    if user_id not in users or users[user_id]['role'] != 'Team Leader':
        emit('error', {'message': 'Only team leaders can submit decisions'}, room=request.sid)
        return
    
    if team_id not in teams:
        emit('error', {'message': 'Team not found'}, room=request.sid)
        return
    
    # Get the game
    game_id = teams[team_id]['game_id']
    current_scenario = games[game_id]['scenario']
    
    # Get recent team messages for context
    team_messages = [msg for msg in messages if msg['team_id'] == team_id][-20:]
    
    # Immediately notify that the submission was received
    emit('submission_received', {}, room=team_id)
    
    # Generate new scenario using AWS Bedrock
    new_scenario = generate_scenario_update(current_scenario, team_messages, decision)
    
    # Update the game state
    games[game_id]['scenario'] = new_scenario
    
    # Store in scenario history
    if 'scenario_history' not in games[game_id]:
        games[game_id]['scenario_history'] = []
    
    games[game_id]['scenario_history'].append({
        'scenario': new_scenario,
        'timestamp': datetime.now().isoformat()
    })
    
    # Store the decision in the game history
    if 'decisions' not in games[game_id]:
        games[game_id]['decisions'] = []
    
    games[game_id]['decisions'].append({
        'user_id': user_id,
        'team_id': team_id,
        'decision': decision,
        'timestamp': datetime.now().isoformat()
    })
    
    # Notify the team
    emit('scenario_update', {
        'scenario': new_scenario
    }, room=team_id)
    
    emit('team_message', {
        'type': 'system',
        'content': f"Team Leader has submitted a decision. The scenario has been updated."
    }, room=team_id)

# For debugging - display application status
@app.route('/debug/status')
def debug_status():
    return jsonify({
        'games_count': len(games),
        'teams_count': len(teams),
        'users_count': len(users),
        'messages_count': len(messages),
    })

if __name__ == '__main__':
    socketio.run(app, debug=True)