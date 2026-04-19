from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import random
import string
import os

app = Flask(__name__)
app.secret_key = 'eco_remarket_super_secret_key' 

# --- DATABASE & UPLOAD SETUP ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ecoremarket.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static' 
db = SQLAlchemy(app)

# ==========================================
# DATABASE MODELS
# ==========================================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False) 

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    sub_category = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    photo = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    shop_name = db.Column(db.String(100), nullable=True)
    creator_id = db.Column(db.Integer, nullable=False)
    sold_count = db.Column(db.Integer, default=0)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(20), unique=True, nullable=False)
    buyer_email = db.Column(db.String(100), nullable=False)
    total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Unpaid')
    reseller_shop = db.Column(db.String(100), nullable=True)
    reseller_contact = db.Column(db.String(20), nullable=True)
    reseller_address = db.Column(db.Text, nullable=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(20), nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    photo = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    creator_id = db.Column(db.Integer, nullable=False)
    buyer_email = db.Column(db.String(100), nullable=False)

# Initialize Database
with app.app_context():
    db.create_all()
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

# ==========================================
# PUBLIC ROUTES (NO LOGIN REQUIRED)
# ==========================================

@app.route('/')
def index():
    return redirect(url_for('home'))

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/products')
def products():
    search_query = request.args.get('search', '')
    
    if search_query:
        all_products = Product.query.filter(
            (Product.category.ilike(f"%{search_query}%")) | 
            (Product.sub_category.ilike(f"%{search_query}%")) | 
            (Product.name.ilike(f"%{search_query}%")) |
            (Product.shop_name.ilike(f"%{search_query}%"))
        ).all()
    else:
        all_products = Product.query.all()

    auto_tab = 'electronics'
    if search_query:
        has_electronics = any(p.category == 'Electronics' for p in all_products)
        has_toys = any(p.category == 'Toys' for p in all_products)
        if has_toys and not has_electronics:
            auto_tab = 'toys'
            
    return render_template('products.html', products=all_products, auto_tab=auto_tab)

# ==========================================
# AUTHENTICATION
# ==========================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['fullName']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return render_template('register.html', error="Email already exists!")
        new_user = User(name=name, email=email, password=password, role=role)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        if role == 'admin' and email == 'admin@eco.com' and password == 'admin123':
            session['user'] = 'Admin'
            session['email'] = email
            session['role'] = 'admin'
            return redirect(url_for('admin_dashboard'))
        user = User.query.filter_by(email=email, password=password, role=role).first()
        if user:
            session['user'] = user.name
            session['email'] = user.email
            session['role'] = user.role
            session['user_id'] = user.id
            if 'cart' not in session:
                session['cart'] = []
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error="Invalid credentials or role mismatch.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ==========================================
# CREATOR & RESELLER SECURE ROUTES
# ==========================================
@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if 'user' not in session or session.get('role') != 'creator':
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')
        category = request.form.get('category')
        sub_category = request.form.get('sub_category')
        quantity = request.form.get('quantity')
        shop_name = request.form.get('shop_name') 
        description = request.form.get('description')

        photo_file = request.files.get('photo')
        photo_path = ""
        if photo_file and photo_file.filename != '':
            filename = secure_filename(photo_file.filename)
            photo_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            photo_path = f"/static/{filename}"

        new_product = Product(
            name=name,
            price=float(price) if price else 0.0,
            category=category,
            sub_category=sub_category,
            quantity=int(quantity) if quantity else 0,
            photo=photo_path,
            description=description,
            shop_name=shop_name,
            creator_id=session['user_id']
        )
        db.session.add(new_product)
        db.session.commit()
        return redirect(url_for('products'))
    return render_template('add_product.html')

@app.route('/delete_product/<int:product_id>')
def delete_product(product_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    product = Product.query.get(product_id)
    if product and (session.get('role') == 'admin' or product.creator_id == session.get('user_id')):
        db.session.delete(product)
        db.session.commit()
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('products'))

# --- CART & CHECKOUT ---
@app.route('/add_to_cart/<int:product_id>', methods=['POST', 'GET'])
def add_to_cart(product_id):
    if 'user' not in session or session.get('role') != 'reseller':
        return redirect(url_for('login'))
        
    product = Product.query.get(product_id)
    quantity = 1
    if request.method == 'POST':
        quantity = int(request.form.get('quantity', 1))
        
    if product and product.quantity >= quantity:
        cart = session.get('cart', [])
        cart.append({
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'photo': product.photo,
            'category': product.category,
            'creator_id': product.creator_id,
            'qty': quantity
        })
        session['cart'] = cart
        session.modified = True
    return redirect(url_for('cart'))

@app.route('/cart')
def cart():
    if 'user' not in session or session.get('role') != 'reseller':
        return redirect(url_for('login'))
    cart_items = session.get('cart', [])
    total = sum(item['price'] * item.get('qty', 1) for item in cart_items)
    return render_template('cart.html', items=cart_items, total=total)

@app.route('/remove_from_cart/<int:index>')
def remove_from_cart(index):
    cart = session.get('cart', [])
    if 0 <= index < len(cart):
        cart.pop(index)
        session['cart'] = cart
        session.modified = True
    return redirect(url_for('cart'))

@app.route('/clear_cart')
def clear_cart():
    session['cart'] = []
    session.modified = True
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user' not in session or not session.get('cart'):
        return redirect(url_for('cart'))
        
    if request.method == 'GET':
        return render_template('shipping_details.html')

    if request.method == 'POST':
        reseller_shop = request.form.get('reseller_shop')
        reseller_contact = request.form.get('reseller_contact')
        reseller_address = request.form.get('reseller_address')

        cart_items = session.get('cart', [])
        total = sum(item['price'] * item.get('qty', 1) for item in cart_items)
        order_id = 'ORD-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        
        new_order = Order(
            order_id=order_id, 
            buyer_email=session['email'], 
            total=total, 
            status='Unpaid',
            reseller_shop=reseller_shop,
            reseller_contact=reseller_contact,
            reseller_address=reseller_address
        )
        db.session.add(new_order)
        
        for item in cart_items:
            qty = item.get('qty', 1)
            for _ in range(qty):
                new_item = OrderItem(
                    order_id=order_id,
                    product_id=item['id'],
                    name=item['name'],
                    price=item['price'],
                    photo=item['photo'],
                    category=item['category'],
                    creator_id=item['creator_id'],
                    buyer_email=session['email']
                )
                db.session.add(new_item)
            
        db.session.commit()
        session['cart'] = []
        session.modified = True
        return redirect(url_for('payment', order_id=order_id))

@app.route('/payment/<order_id>')
def payment(order_id):
    order = Order.query.filter_by(order_id=order_id).first()
    if not order:
        return redirect(url_for('home'))
    order_dict = {'order_id': order.order_id, 'total': order.total}
    return render_template('payment.html', order=order_dict)

@app.route('/process_payment/<order_id>', methods=['POST'])
def process_payment(order_id):
    order = Order.query.filter_by(order_id=order_id).first()
    if order:
        order.status = 'Paid'
        items = OrderItem.query.filter_by(order_id=order_id).all()
        for item in items:
            product = Product.query.get(item.product_id)
            if product:
                product.quantity -= 1
                product.sold_count += 1
        db.session.commit()
    return redirect(url_for('my_orders'))

# --- DASHBOARDS ---
@app.route('/my_orders')
def my_orders():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    if session.get('role') == 'creator':
        sold_items = OrderItem.query.filter_by(creator_id=session['user_id']).all()
        
        sales_dict = {}
        total_earned = 0
        
        for item in sold_items:
            order = Order.query.filter_by(order_id=item.order_id).first()
            if order and order.status == 'Paid':
                key = f"{item.order_id}_{item.product_id}"
                
                if key not in sales_dict:
                    sales_dict[key] = {
                        'photo': item.photo,
                        'product_name': item.name,
                        'buyer': item.buyer_email,
                        'order_id': item.order_id,
                        'price': item.price,
                        'total_price': item.price,
                        'qty': 1, 
                        'reseller_shop': order.reseller_shop,
                        'reseller_contact': order.reseller_contact,
                        'reseller_address': order.reseller_address
                    }
                else:
                    sales_dict[key]['qty'] += 1
                    sales_dict[key]['total_price'] += item.price
                    
                total_earned += item.price
                
        sales_data = list(sales_dict.values())
        return render_template('my_orders.html', sales=sales_data, total_earned=total_earned)
        
    elif session.get('role') == 'reseller':
        user_orders = Order.query.filter_by(buyer_email=session['email']).order_by(Order.id.desc()).all()
        orders_data = []
        
        for order in user_orders:
            items = OrderItem.query.filter_by(order_id=order.order_id).all()
            
            grouped_items = {}
            for i in items:
                if i.product_id not in grouped_items:
                    grouped_items[i.product_id] = {
                        'photo': i.photo, 
                        'name': i.name, 
                        'category': i.category, 
                        'price': i.price,
                        'qty': 1 
                    }
                else:
                    grouped_items[i.product_id]['qty'] += 1
                    
            items_list = list(grouped_items.values())
            
            orders_data.append({
                'order_id': order.order_id,
                'status': order.status,
                'total': order.total,
                'items': items_list
            })
            
        return render_template('my_orders.html', orders=orders_data)

# --- ADMIN CONTROLS ---
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    users = User.query.all()
    products = Product.query.all()
    orders = Order.query.all()
    return render_template('admin_dashboard.html', users=users, all_products=products, all_orders=orders)

@app.route('/admin_delete_user/<int:user_id>')
def admin_delete_user(user_id):
    if 'user' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    user = User.query.get(user_id)
    if user and user.role != 'admin':
        Product.query.filter_by(creator_id=user.id).delete()
        db.session.delete(user)
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin_delete_product/<int:product_id>')
def admin_delete_product(product_id):
    if 'user' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    product = Product.query.get(product_id)
    if product:
        db.session.delete(product)
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)