from flask import Flask, render_template, request, redirect, session, jsonify, flash
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask_sqlalchemy import SQLAlchemy

# Initialize the Flask application
app = Flask(__name__)

# Secret key for session management (should be kept secret in production)
app.secret_key = 'your_secret_key'

# Configuration for file uploads
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)  # Ensure the directory exists
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Configure SQLite database connection
db_path = os.path.join(os.getcwd(), "product_management.db")
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the SQLAlchemy database instance
db = SQLAlchemy(app)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')

# Product Model
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_path = db.Column(db.String(255), nullable=True)

# Create database tables if they don't exist
with app.app_context():
    db.create_all()

# Utility Function

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Authentication Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash("You need to log in first!", "warning")
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

# Admin Decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or session.get('role') != 'admin':
            flash("Admin access required!", "danger")
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists!", "danger")
            return redirect('/register')
        new_user = User(username=username, password=generate_password_hash(password), role='user')
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! Please log in.", "success")
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['logged_in'] = True
            session['role'] = user.role
            flash("Login successful!", "success")
            return redirect('/admin' if user.role == 'admin' else '/')
        flash("Invalid username or password!", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect('/login')

@app.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        description = request.form['description']
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            new_product = Product(name=name, price=price, description=description, image_path=filepath)
            db.session.add(new_product)
            db.session.commit()
            flash("Product added successfully!", "success")
            return redirect('/admin')
    return render_template('add_product.html')

@app.route('/')
def public_page():
    products = Product.query.all()
    return render_template('index.html', products=products)

@app.route('/admin')
@admin_required
def admin():
    products = Product.query.all()
    return render_template('admin.html', products=products)

@app.route('/delete_product/<int:product_id>', methods=['POST'])
@admin_required
def delete_product(product_id):
    product = Product.query.get(product_id)
    if product:
        try:
            if product.image_path and os.path.exists(product.image_path):
                os.remove(product.image_path)
        except Exception as e:
            flash(f"Error deleting file: {e}", "danger")
        db.session.delete(product)
        db.session.commit()
        flash("Product deleted successfully!", "success")
    return redirect('/admin')

@app.route('/cart')
@login_required
def cart():
    return render_template('cart.html', cart=session.get('cart', {}))

@app.route('/clear_cart', methods=['POST'])
@login_required
def clear_cart():
    session.pop('cart', None)
    flash("Cart cleared successfully!", "success")
    return redirect('/cart')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
