"""
Initializes the SocketIO instance for the application.
"""
from flask_socketio import SocketIO

# Create the instance with async_mode='eventlet' (which we installed)
# and configure it to handle CORS from any origin.
socketio = SocketIO(cors_allowed_origins="*")
