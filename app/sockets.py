"""
Initializes the SocketIO instance for the application.
"""
from flask_socketio import SocketIO

# Create the instance with async_mode='eventlet' (which we installed)
# and configure it to handle CORS from any origin.
# WARNING: cors_allowed_origins="*" allows connections from any domain.
# In production, consider restricting this to specific trusted domains
# for better security (e.g., cors_allowed_origins=["https://yourdomain.com"]).
socketio = SocketIO(async_mode='eventlet', cors_allowed_origins="*")
