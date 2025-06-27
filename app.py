from flask import Flask, render_template, request, redirect, url_for, session, flash
import json
import os
import hashlib
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'supersecretkeychangeinproduction'

DATA_DIR = 'data'
USERS_FILE = os.path.join(DATA_DIR, 'users.json')

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def get_user(email):
    users = load_users()
    email = email.lower()
    for user in users:
        if user['email'] == email:
            return user
    return None

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'email' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def load_user_data(email):
    data_file = os.path.join(DATA_DIR, f'{email}_data.json')
    if not os.path.exists(data_file):
        return {'transactions': [], 'budgets': []}
    with open(data_file, 'r') as f:
        return json.load(f)

def save_user_data(email, data):
    data_file = os.path.join(DATA_DIR, f'{email}_data.json')
    with open(data_file, 'w') as f:
        json.dump(data, f, indent=2)

def format_inr(amount):
    return "₹{:,.2f}".format(amount)

@app.context_processor
def utility_processor():
    return dict(format_inr=format_inr, datetime=datetime)

@app.route('/')
def index():
    if 'email' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'email' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        if not (name and email and password and confirm):
            flash('Please fill all fields.', 'error')
            return render_template('register.html')
        if password != confirm:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')
        if get_user(email):
            flash('User with this email already exists.', 'error')
            return render_template('register.html')
        users = load_users()
        users.append({
            'name': name,
            'email': email,
            'password': hash_password(password)
        })
        save_users(users)
        save_user_data(email, {'transactions': [], 'budgets': []})
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'email' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = get_user(email)
        if not user:
            flash('User not found.', 'error')
            return render_template('login.html')
        if hash_password(password) != user['password']:
            flash('Incorrect password.', 'error')
            return render_template('login.html')
        session['email'] = user['email']
        session['name'] = user['name']
        flash('Login successful!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    email = session['email']
    data = load_user_data(email)

    if request.method == 'POST':
        if 'add_transaction' in request.form:
            try:
                amount = float(request.form.get('amount', 0))
                category = request.form.get('category', '')
                date_str = request.form.get('date', '')
                description = request.form.get('description', '').strip()
                split_with = request.form.get('split_with', '').strip()

                if amount <= 0:
                    flash('Amount must be a positive number.', 'error')
                    return redirect(url_for('dashboard'))
                if not category:
                    flash('Please choose a category.', 'error')
                    return redirect(url_for('dashboard'))
                if not date_str:
                    flash('Please provide a valid date.', 'error')
                    return redirect(url_for('dashboard'))

                datetime.strptime(date_str, '%Y-%m-%d')

                transaction = {
                    'amount': amount,
                    'category': category,
                    'date': date_str,
                    'description': description if description else None,
                    'split_with': split_with if split_with else None,
                }
                data['transactions'].insert(0, transaction)
                save_user_data(email, data)
                flash('Transaction added!', 'success')
                return redirect(url_for('dashboard'))
            except Exception as e:
                flash('Error adding transaction: ' + str(e), 'error')
                return redirect(url_for('dashboard'))

        elif 'add_budget' in request.form:
            try:
                category = request.form.get('budget_category', '')
                limit_amount = float(request.form.get('limit_amount', 0))
                if not category:
                    flash('Please choose a category.', 'error')
                    return redirect(url_for('dashboard'))
                if limit_amount <= 0:
                    flash('Limit amount must be a positive number.', 'error')
                    return redirect(url_for('dashboard'))
                index = next((i for i,b in enumerate(data['budgets']) if b['category'] == category), -1)
                if index >= 0:
                    data['budgets'][index]['limit_amount'] = limit_amount
                else:
                    data['budgets'].append({'category': category, 'limit_amount': limit_amount})
                save_user_data(email, data)
                flash('Budget set/updated!', 'success')
                return redirect(url_for('dashboard'))
            except Exception as e:
                flash('Error setting budget: ' + str(e), 'error')
                return redirect(url_for('dashboard'))

    expenses_by_category = {}
    for t in data['transactions']:
        expenses_by_category[t['category']] = expenses_by_category.get(t['category'], 0) + t['amount']

    return render_template('dashboard.html', name=session['name'], transactions=data['transactions'], budgets=data['budgets'], expenses_by_category=expenses_by_category)

@app.route('/delete_transaction/<int:index>', methods=['POST'])
@login_required
def delete_transaction(index):
    email = session['email']
    data = load_user_data(email)
    if 0 <= index < len(data['transactions']):
        data['transactions'].pop(index)
        save_user_data(email, data)
        flash('Transaction deleted.', 'success')
    else:
        flash('Invalid transaction index.', 'error')
    return redirect(url_for('dashboard'))

@app.route('/delete_budget/<category>', methods=['POST'])
@login_required
def delete_budget(category):
    email = session['email']
    data = load_user_data(email)
    initial_len = len(data['budgets'])
    data['budgets'] = [b for b in data['budgets'] if b['category'] != category]
    if len(data['budgets']) < initial_len:
        save_user_data(email, data)
        flash('Budget deleted.', 'success')
    else:
        flash('Budget category not found.', 'error')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
