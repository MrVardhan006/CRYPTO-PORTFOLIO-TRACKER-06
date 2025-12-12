from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, current_user
from models import db, User

bp = Blueprint('auth', __name__)

@bp.route('/', methods=['GET'])
@bp.route('/index.html', methods=['GET'])
def home():
    return render_template('index.html')

@bp.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    username = data.get('username', '').strip().lower()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    if not username or len(password) < 6:
        return jsonify({'message': 'Username & password (min 6 chars) required'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'Username already exists'}), 400
    user = User(name=name, username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'Account created! Please login.'}), 200

@bp.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    username = data.get('username', '').strip().lower()
    password = data.get('password', '')
    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({'message': 'Invalid username or password'}), 401
    login_user(user)
    return jsonify({'message': 'Login successful!', 'name': user.name}), 200

@bp.route('/login', methods=['POST'])
def login():
    username = request.form.get('username', '').strip().lower()
    password = request.form.get('password', '')
    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return render_template('index.html', login_msg='Invalid username or password', reg_msg=None)
    login_user(user)
    return redirect(url_for('dashboard.dashboard'))

@bp.route('/register', methods=['POST'])
def register():
    name = request.form.get('name', '').strip()
    username = request.form.get('username', '').strip().lower()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    if not username or len(password) < 6:
        return render_template('index.html', reg_msg='Username & password (min 6 chars) required', login_msg=None)
    if User.query.filter_by(username=username).first():
        return render_template('index.html', reg_msg='Username already exists', login_msg=None)
    user = User(name=name, username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return render_template('index.html', reg_msg='Account created! Please login.', login_msg=None)

@bp.route('/logout', methods=['GET'])
def logout():
    logout_user()
    return redirect(url_for('auth.home'))
