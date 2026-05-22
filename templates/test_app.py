import pytest
from app import app, db, User, UserData, Income, Expense, Repay, Payment
from datetime import date

# Configure the app for testing
@pytest.fixture(scope='module')
def test_client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing forms
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()

# Helper function to register a user
def register_user(client, name, mobile, password, job="Tester", daily_earning=100.0):
    return client.post('/signup', data={
        'name': name,
        'mobile': mobile,
        'password': password,
        'job': job,
        'daily_earning': daily_earning
    }, follow_redirects=True)

# Helper function to log in a user
def login_user(client, mobile, password):
    return client.post('/login', data={
        'mobile': mobile,
        'password': password
    }, follow_redirects=True)

# Test for the home route redirect
def test_home_redirect(test_client):
    response = test_client.get('/')
    assert response.status_code == 200
    assert b"Login" in response.data # Redirects to login page

# Test signup page (GET)
def test_signup_page(test_client):
    response = test_client.get('/signup')
    assert response.status_code == 200
    assert b"Signup" in response.data

# Test successful signup (POST)
def test_signup_success(test_client):
    response = register_user(test_client, 'Test User', '1234567890', 'password123')
    assert response.status_code == 200
    assert b"Account created successfully! Please login." in response.data
    
    with app.app_context():
        user = User.query.filter_by(mobile='1234567890').first()
        assert user is not None
        assert user.name == 'Test User'

# Test signup with existing mobile number (POST)
def test_signup_existing_mobile(test_client):
    # Register first user
    register_user(test_client, 'Existing User', '9876543210', 'pass1')
    
    # Try to register with the same mobile
    response = register_user(test_client, 'Another User', '9876543210', 'pass2')
    assert response.status_code == 200
    assert b"Mobile number already registered. Please login or use a different number." in response.data
    
    with app.app_context():
        users = User.query.filter_by(mobile='9876543210').all()
        assert len(users) == 1 # Only one user should exist with this mobile

# Test login page (GET)
def test_login_page(test_client):
    response = test_client.get('/login')
    assert response.status_code == 200
    assert b"Login" in response.data

# Test successful login (POST)
def test_login_success(test_client):
    # Register a user first
    register_user(test_client, 'Login User', '1112223333', 'loginpass')
    
    # Then try to log in
    response = login_user(test_client, '1112223333', 'loginpass')
    assert response.status_code == 200
    assert b"Welcome back, Login User!" in response.data # Assuming dashboard shows welcome message
    assert 'user_id' in test_client.session

# Test login with invalid password (POST)
def test_login_invalid_password(test_client):
    # Register a user
    register_user(test_client, 'Bad Pass User', '4445556666', 'correctpass')
    
    # Try to log in with wrong password
    response = login_user(test_client, '4445556666', 'wrongpass')
    assert response.status_code == 200
    assert b"Invalid mobile or password" in response.data
    assert 'user_id' not in test_client.session

# Test login with non-existent mobile (POST)
def test_login_non_existent_mobile(test_client):
    response = login_user(test_client, '0000000000', 'anypass')
    assert response.status_code == 200
    assert b"Invalid mobile or password" in response.data
    assert 'user_id' not in test_client.session

# Test logout functionality
def test_logout(test_client):
    # Register and login a user
    register_user(test_client, 'Logout User', '7778889999', 'logoutpass')
    login_user(test_client, '7778889999', 'logoutpass')
    
    # Check if logged in
    with test_client.session_transaction() as sess:
        assert 'user_id' in sess
    
    # Perform logout
    response = test_client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b"Login" in response.data # Redirects to login page after logout
    
    # Check if user_id is cleared from session
    with test_client.session_transaction() as sess:
        assert 'user_id' not in sess

# Test dashboard access without login
def test_dashboard_access_without_login(test_client):
    response = test_client.get('/dashboard', follow_redirects=True)
    assert response.status_code == 200
    assert b"Login" in response.data # Should redirect to login page
    assert '/login' in response.request.path

# Test dashboard access with login
def test_dashboard_access_with_login(test_client):
    register_user(test_client, 'Dashboard User', '5555555555', 'dashpass')
    login_user(test_client, '5555555555', 'dashpass')
    
    response = test_client.get('/dashboard')
    assert response.status_code == 200
    assert b"Welcome back, Dashboard User!" in response.data