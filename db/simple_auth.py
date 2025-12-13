import json
import os
import bcrypt
from typing import Optional, Dict

AUTH_FILE = "users.json"


def load_users() -> Dict:
    if not os.path.exists(AUTH_FILE):
        return {}
    try:
        with open(AUTH_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}


def save_users(users: Dict):
    with open(AUTH_FILE, 'w') as f:
        json.dump(users, f, indent=2)


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def register_user(username: str, email: str, password: str) -> tuple[bool, str]:
    if not username or len(username) < 3:
        return False, "Username must be at least 3 characters"
    
    if not email or '@' not in email:
        return False, "Invalid email format"
    
    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters"
    
    users = load_users()
    
    if username in users:
        return False, "Username already exists"
    
    for user_data in users.values():
        if user_data.get('email') == email:
            return False, "Email already registered"
    
    users[username] = {
        'email': email,
        'password': hash_password(password)
    }
    
    save_users(users)
    return True, "Registration successful!"


def login_user(username: str, password: str) -> tuple[bool, str]:
    if not username or not password:
        return False, "Username and password required"
    
    users = load_users()
    
    if username not in users:
        return False, "Invalid username or password"
    
    user_data = users[username]
    
    if not verify_password(password, user_data['password']):
        return False, "Invalid username or password"
    
    return True, "Login successful!"
