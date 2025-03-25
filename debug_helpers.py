import os
import logging
from flask import request, jsonify

def setup_debug_routes(app, games, teams, users, messages):
    """
    Set up debug routes to help diagnose issues in the application.
    
    Args:
        app: The Flask application
        games, teams, users, messages: The in-memory data stores
    """
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('debug.log')
        ]
    )
    logger = logging.getLogger('wargame')
    
    # Add the logger to the app for use in other modules
    app.logger = logger
    
    @app.route('/debug/status')
    def debug_status():
        """Return the status of the application and its data stores."""
        return jsonify({
            'status': 'running',
            'games_count': len(games),
            'teams_count': len(teams),
            'users_count': len(users),
            'messages_count': len(messages),
            'static_folder_exists': os.path.exists(app.static_folder),
            'css_folder_exists': os.path.exists(os.path.join(app.static_folder, 'css')),
            'js_folder_exists': os.path.exists(os.path.join(app.static_folder, 'js')),
            'styles_css_exists': os.path.exists(os.path.join(app.static_folder, 'css', 'styles.css')),
            'main_js_exists': os.path.exists(os.path.join(app.static_folder, 'js', 'main.js')),
            'debug': app.debug,
            'request_endpoint': request.endpoint
        })
    
    @app.route('/debug/games')
    def debug_games():
        """Return the list of games."""
        return jsonify({
            'games': {game_id: {
                'scenario': game.get('scenario', '')[:100] + '...',  # Truncate for readability
                'teams_count': len(game.get('teams', [])),
                'created_at': game.get('created_at', ''),
                'scenario_history_count': len(game.get('scenario_history', []))
            } for game_id, game in games.items()}
        })
    
    @app.route('/debug/teams')
    def debug_teams():
        """Return the list of teams."""
        return jsonify({
            'teams': {team_id: {
                'name': team.get('name', ''),
                'game_id': team.get('game_id', ''),
                'members_count': len(team.get('members', [])),
                'created_at': team.get('created_at', '')
            } for team_id, team in teams.items()}
        })
    
    @app.route('/debug/clear_data')
    def debug_clear_data():
        """Clear all in-memory data (development only)."""
        if not app.debug:
            return jsonify({'error': 'This endpoint is only available in debug mode'}), 403
        
        games.clear()
        teams.clear()
        users.clear()
        messages.clear()
        return jsonify({'status': 'Data cleared'})
    
    # Add a request logger middleware
    @app.before_request
    def log_request_info():
        logger.debug(f'Request: {request.method} {request.path}')
        if request.json:
            logger.debug(f'Request JSON: {request.json}')
    
    # Add an after-request logger middleware
    @app.after_request
    def log_response_info(response):
        logger.debug(f'Response: {response.status}')
        return response
    
    # Add an error handler
    @app.errorhandler(Exception)
    def handle_exception(e):
        logger.error(f'Unhandled exception: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500

def log_socketio_events(socketio):
    """
    Set up logging for Socket.IO events.
    
    Args:
        socketio: The Socket.IO instance
    """
    logger = logging.getLogger('wargame_socketio')
    
    @socketio.on_error()
    def handle_error(e):
        logger.error(f'SocketIO error: {str(e)}', exc_info=True)
    
    @socketio.on('connect')
    def handle_connect():
        logger.info(f'Client connected: {request.sid}')
    
    @socketio.on('disconnect')
    def handle_disconnect():
        logger.info(f'Client disconnected: {request.sid}')