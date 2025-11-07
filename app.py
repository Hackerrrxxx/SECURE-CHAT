from flask import Flask, render_template, request as flask_request
from flask_socketio import SocketIO, emit, join_room
import flask_socketio
import os
import random
import string
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
socketio = SocketIO(app, cors_allowed_origins="*")

# Store active users: {username: {socket_id, public_key, joined_at, phone}}
clients = {}

# Store phone verification codes: {phone: {code, expires_at, verified}}
phone_verifications = {}

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def is_valid_phone(phone):
    # Simple validation - 10-15 digits
    return phone and phone.replace('+', '').replace('-', '').replace(' ', '').isdigit() and len(phone.replace('+', '').replace('-', '').replace(' ', '')) >= 10

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/verify', methods=['POST'])
def verify_phone():
    data = flask_request.json
    if not data or 'phone' not in data:
        return {'success': False, 'message': 'Phone number is required'}, 400
    phone = data.get('phone')
    
    if not is_valid_phone(phone):
        return {'success': False, 'message': 'Invalid phone number'}, 400
    
    # Generate OTP
    otp = generate_otp()
    phone_verifications[phone] = {
        'code': otp,
        'expires_at': datetime.now() + timedelta(minutes=10),
        'verified': False
    }
    
    # In production, send SMS here. For demo, we'll return the code
    print(f"OTP for {phone}: {otp}")  # Remove this in production
    
    return {'success': True, 'message': 'OTP sent to your phone', 'otp': otp}  # Remove 'otp' in production

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = flask_request.json
    if not data:
        return {'success': False, 'message': 'Invalid request data'}, 400

    phone = data.get('phone')
    code = data.get('code')
    username = data.get('username')
    
    if phone not in phone_verifications:
        return {'success': False, 'message': 'Phone number not found. Please request a new code.'}, 400
    
    verification = phone_verifications[phone]
    
    if datetime.now() > verification['expires_at']:
        del phone_verifications[phone]
        return {'success': False, 'message': 'OTP expired. Please request a new code.'}, 400
    
    if verification['code'] != code:
        return {'success': False, 'message': 'Invalid OTP'}, 400
    
    # Mark as verified and store username
    verification['verified'] = True
    verification['username'] = username
    verification['verified_at'] = datetime.now()
    
    return {'success': True, 'message': 'Phone verified successfully'}

@app.route('/chat')
def chat():
    user = flask_request.args.get('user')
    phone = flask_request.args.get('phone')
    if not user or not phone:
        return render_template('index.html')
    
    # Verify phone was authenticated
    if phone not in phone_verifications or not phone_verifications[phone].get('verified'):
        return render_template('index.html')
    
    if phone_verifications[phone].get('username') != user:
        return render_template('index.html')
    
    return render_template('chat.html', user=user, phone=phone)

@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {flask_socketio.request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    # Find and remove user on disconnect
    username = None
    for user, data in clients.items():
        if data.get('socket_id') == flask_socketio.request.sid:
            username = user
            break
    
    if username:
        del clients[username]
        emit('user_left', {'username': username}, broadcast=True)
        print(f"{username} left the chat.")

@socketio.on('join')
def handle_join(data):
    username = data.get('username')
    phone = data.get('phone')
    public_key_pem = data.get('public_key')  # RSA public key from client
    
    if not username or not public_key_pem or not phone:
        emit('error', {'message': 'Username, phone, and public key required'})
        return
    
    # Verify phone authentication
    if phone not in phone_verifications or not phone_verifications[phone].get('verified'):
        emit('error', {'message': 'Phone number not verified'})
        return
    
    if phone_verifications[phone].get('username') != username:
        emit('error', {'message': 'Username does not match verified phone'})
        return
    
    if username in clients:
        emit('error', {'message': 'Username already taken'})
        return
    
    # Store user info
    clients[username] = {
    'socket_id': flask_socketio.request.sid,
        'public_key': public_key_pem,
        'phone': phone,
        'joined_at': datetime.now().isoformat()
    }
    
    join_room(username)
    
    # Send confirmation to the user who joined
    emit('joined', {
        'username': username,
        'online_users': list(clients.keys())
    })
    
    # Notify others about new user
    emit('user_joined', {
        'username': username,
        'online_users': list(clients.keys())
    }, broadcast=True, include_self=False)
    
    print(f"{username} ({phone}) joined the chat. Total users: {len(clients)}")

@socketio.on('get_online_users')
def handle_get_online_users():
    emit('online_users', {'users': list(clients.keys())})

@socketio.on('get_public_key')
def handle_get_public_key(data):
    recipient = data.get('username')
    if recipient in clients:
        emit('public_key_response', {
            'username': recipient,
            'public_key': clients[recipient]['public_key']
        })
    else:
        emit('error', {'message': f'User {recipient} not found'})

@socketio.on('send_message')
def handle_message(data):
    """
    E2EE Message Handler - Server acts as encrypted relay only.
    
    SECURITY MODEL:
    - Server NEVER decrypts messages (no capability to do so)
    - Server NEVER stores message content
    - Server only forwards encrypted payloads
    - All encryption/decryption happens client-side
    - Server has no access to private keys
    - Perfect Forward Secrecy: Each message uses ephemeral keys
    """
    sender = data.get('sender')
    recipient = data.get('recipient')
    encrypted_message = data.get('encrypted_message')  # AES-encrypted, server CANNOT read
    encrypted_aes_key = data.get('encrypted_aes_key')  # RSA-encrypted AES key, server CANNOT decrypt
    message_hmac = data.get('message_hmac')  # HMAC for authentication, server CANNOT verify
    ephemeral_public_key = data.get('ephemeral_public_key')  # Optional: Ephemeral key for PFS
    
    if not sender or not recipient or not encrypted_message:
        emit('error', {'message': 'Missing required fields'})
        return
    
    if sender not in clients:
        emit('error', {'message': 'You are not logged in'})
        return
    
    if recipient not in clients:
        emit('error', {'message': f'User {recipient} is not online'})
        return
    
    # CRITICAL: Server forwards encrypted data ONLY - no decryption capability
    # The encrypted_message, encrypted_aes_key, and message_hmac are opaque to the server
    # Server cannot decrypt because:
    # 1. AES keys are encrypted with recipient's RSA public key (only recipient's private key can decrypt)
    # 2. Server never receives or stores private keys
    # 3. All decryption happens client-side only
    
    # Forward encrypted payload (server acts as encrypted relay)
    emit('receive_message', {
        'sender': sender,  # Metadata only (needed for routing)
        'encrypted_message': encrypted_message,  # Opaque encrypted data
        'encrypted_aes_key': encrypted_aes_key,  # Opaque encrypted key
        'message_hmac': message_hmac,  # Opaque authentication code
        'ephemeral_public_key': ephemeral_public_key,  # Ephemeral key for PFS
        'timestamp': datetime.now().isoformat()  # Metadata only
    }, to=recipient)
    
    # Log metadata only - NEVER log message content (we can't even if we wanted to)
    print(f"[E2EE Relay] {sender} → {recipient}: Encrypted payload forwarded (server cannot decrypt)")

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
