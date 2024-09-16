# =================== IMPORTS AND SETUP ===================
from threading import Thread
from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime, timedelta
import hashlib
import sqlite3
import uuid
from flask_mail import Mail, Message
from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, FloatField
from wtforms.validators import DataRequired, Email
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import qrcode
from io import BytesIO
from email.mime.image import MIMEImage

app = Flask(__name__)
app.secret_key = '1234'  # Secret key for session management
mail = Mail(app)

import logging
app.logger.setLevel(logging.DEBUG)

# =================== DATABASE CONNECTION & CREATION ===================
import os

def get_db_connection():
    try:
        db_path = os.path.abspath('voucher.db')  # Get the absolute path of the database
        print(f"Connecting to database at: {db_path}")  # Debug: print the path

        conn = sqlite3.connect(db_path)  # Ensure correct database name
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to the database: {e}")
        return None


def create_tables():
    conn = get_db_connection()

    # Create events table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS events (
        event_id TEXT PRIMARY KEY,
        event_name TEXT NOT NULL,
        event_date TEXT NOT NULL
    )
    ''')

    # Create vendors table with the password column included
    conn.execute('''
    CREATE TABLE IF NOT EXISTS vendors (
        vendor_id TEXT PRIMARY KEY,
        vendor_name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT,
        password TEXT,  -- Use correct comment syntax for SQLite
        event_id TEXT NOT NULL,
        FOREIGN KEY (event_id) REFERENCES events(event_id)
    )
    ''')

    # Create vouchers table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS vouchers (
        voucher_id TEXT PRIMARY KEY,
        voucher_name TEXT NOT NULL,
        email TEXT NOT NULL,
        balance REAL NOT NULL,
        canceled INTEGER DEFAULT 0
    )
    ''')

    # Create sales table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS sales (
        sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
        voucher_id TEXT,
        booth_id TEXT,
        sale_amount REAL,
        sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (voucher_id) REFERENCES vouchers(voucher_id),
        FOREIGN KEY (booth_id) REFERENCES vendors(vendor_id)
    )
    ''')

    conn.commit()
    conn.close()

# Call the function to create tables if they don't exist
create_tables()

# =================== EMAIL CONFIGURATION ===================

@app.route('/sell_voucher', methods=['POST'])
def sell_voucher():
    # Retrieve form data
    voucher_name = request.form['voucher_name']
    voucher_email = request.form['voucher_email']
    voucher_amount = float(request.form['voucher_amount'])
    
    # Generate a unique voucher ID
    voucher_id = str(uuid.uuid4())
    
    # Generate QR code
    qr_code_img = generate_qr_code(voucher_id)
    
    # Save voucher to the database or perform necessary actions here
    conn = get_db_connection()
    conn.execute('INSERT INTO vouchers (voucher_id, voucher_name, email, balance) VALUES (?, ?, ?, ?)',
                 (voucher_id, voucher_name, voucher_email, voucher_amount))
    conn.commit()
    conn.close()

    # Send email with QR code
    subject = "Your Voucher Purchase Confirmation"
    body = f"Thank you for purchasing the {voucher_name} voucher! Use the QR code below to redeem your voucher."
    send_email(subject, body, voucher_email, voucher_id)
    
    flash(f'Voucher {voucher_name} sold successfully!')
    return redirect(url_for('admin_dash'))

def generate_qr_code(voucher_id):
    redemption_url = f"http://127.0.0.1:5000/redeem/{voucher_id}"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(redemption_url)
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')
    
    img_io = BytesIO()
    img.save(img_io, format='PNG')
    img_io.seek(0)
    
    return img_io

def send_email(subject, body, recipient, voucher_id):
    sender_email = 'sales@aurorainfinity.co.uk'
    email_password = 'Sales_Aurora_00'
    smtp_server = 'aurorainfinity.co.uk'
    smtp_port = 465

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    qr_code_img = generate_qr_code(voucher_id)
    qr_code_attachment = MIMEImage(qr_code_img.read(), name=f"{voucher_id}.png")
    qr_code_attachment.add_header('Content-Disposition', 'attachment', filename=f"{voucher_id}.png")
    msg.attach(qr_code_attachment)

    with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
        server.login(sender_email, email_password)
        server.send_message(msg)


def send_email(subject, body, recipient, voucher_id):
    email_sender = 'sales@aurorainfinity.co.uk'
    email_password = 'Sales_Aurora_00'
    smtp_server = 'aurorainfinity.co.uk'
    smtp_port = 465
    
    msg = MIMEMultipart()
    msg['From'] = email_sender
    msg['To'] = recipient
    msg['Subject'] = subject
    
    msg.attach(MIMEText(body, 'plain'))
    
    qr_code_img = generate_qr_code(voucher_id)
    qr_code_attachment = MIMEImage(qr_code_img.read(), name=f"{voucher_id}.png")
    qr_code_attachment.add_header('Content-Disposition', 'attachment', filename=f"{voucher_id}.png")
    msg.attach(qr_code_attachment)
    
    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(email_sender, email_password)
            server.send_message(msg)
        print(f"Email sent to {recipient} with QR code.")
    except Exception as e:
        print(f"Failed to send email: {e}")

def test_email_functionality():
    subject = "Your Voucher QR Code"
    body = "Please find your QR code attached."
    recipient = "dotunomoboye@gmail.com"
    voucher_id = "sample_voucher_id"
    send_email(subject, body, recipient, voucher_id)

# Call the test function
#test_email_functionality()      
        
def get_vendor_email(vendor_id):
    conn = get_db_connection()
    vendor = conn.execute('SELECT email FROM vendors WHERE vendor_id = ?', (vendor_id,)).fetchone()
    conn.close()
    return vendor['email'] if vendor else None

# =================== CUSTOM FILTER FOR DATE FORMATTING ===================
@app.template_filter('format_date')
def format_date(value, format='%Y-%m-%d'):
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d')
        except ValueError:
            return value  # If it's already formatted or can't be parsed
    return value.strftime(format)

# =================== ADMIN LOGIN ROUTE ===================
ADMIN_CREDENTIALS = {
    'username': 'admin',
    'password': 'adminpassword'  # Change this to a secure password
}

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == ADMIN_CREDENTIALS['username'] and password == ADMIN_CREDENTIALS['password']:
            session['admin_logged_in'] = True
            flash('You are now logged in as Admin.', 'success')
            return redirect(url_for('admin_dash'))
        else:
            flash('Invalid Credentials. Please try again.', 'error')
            return redirect(url_for('admin_login'))

    return render_template('admin_login.html')

# =================== ADMIN DASHBOARD ROUTE ===================
@app.route('/admin_dash')
def admin_dash():
    conn = get_db_connection()
    events = conn.execute('SELECT * FROM events').fetchall()

    event_vendors = {}
    for event in events:
        vendors = conn.execute('SELECT * FROM vendors WHERE event_id = ?', (event['event_id'],)).fetchall()
        event_vendors[event['event_id']] = vendors

    conn.close()

    return render_template('admin_dashboard.html', events=events, event_vendors=event_vendors)

@app.route('/admin_logout')
def admin_logout():
    session.pop('admin_logged_in', None)  # Remove the session
    flash('You have been logged out.')
    return redirect(url_for('admin_login'))

# =================== EVENT CREATION ROUTE ===================
from datetime import datetime

@app.route('/create_event', methods=['GET', 'POST'])
def create_event():
    if request.method == 'POST':
        event_name = request.form.get('event_name')
        event_date = request.form.get('event_date')
        
        if event_name and event_date:
            conn = get_db_connection()
            event_id = str(uuid.uuid4())
            conn.execute('INSERT INTO events (event_id, event_name, event_date) VALUES (?, ?, ?)',
                         (event_id, event_name, event_date))
            conn.commit()
            
            # Fetch the event back to verify what was inserted
            event = conn.execute('SELECT * FROM events WHERE event_id = ?', (event_id,)).fetchone()
            print(f"Inserted Event: {event}")
            
            conn.close()
            flash('Event Created Successfully', 'success')
            return redirect(url_for('admin_dash'))
        else:
            flash('Please provide all required fields', 'error')
    
    return render_template('event_creation.html')


@app.route('/remove_event/<event_id>', methods=['POST'])
def remove_event(event_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM events WHERE event_id = ?', (event_id,))
    conn.commit()
    conn.close()
    flash('Event removed successfully.', 'success')
    return redirect(url_for('admin_dash'))

@app.route('/delete_action', methods=['POST'])
def delete_action():
    action = request.form['action']
    event_or_vendor_id = request.form['event_or_vendor_id']
    admin_password = request.form['admin_password']

    if admin_password == 'adminpassword':  # Replace this with a more secure password check
        conn = get_db_connection()
        
        if action == 'delete_vendor':
            conn.execute('DELETE FROM vendors WHERE vendor_id = ?', (event_or_vendor_id,))
            flash('Vendor deleted successfully.', 'success')
        
        elif action == 'delete_event':
            conn.execute('DELETE FROM events WHERE event_id = ?', (event_or_vendor_id,))
            flash('Event deleted successfully.', 'success')
        
        conn.commit()
        conn.close()
    else:
        flash('Invalid admin password. Action not authorized.', 'error')
    
    return redirect(url_for('manage_vouchers'))

@app.route('/vendor_sales')
def vendor_sales():
    vendor_id = session.get('vendor_id')  # Ensure vendor is logged in

    if not vendor_id:
        flash('You must be logged in to view sales.', 'error')
        return redirect(url_for('vendor_login'))

    conn = get_db_connection()
    sales = conn.execute('SELECT * FROM sales WHERE booth_id = ?', (vendor_id,)).fetchall()

    # Calculate total sales and total amount
    total_sales = len(sales)  # Total number of sales
    total_amount = sum(sale['sale_amount'] for sale in sales)  # Total amount of all sales

    conn.close()

    return render_template('vendor_sales.html', sales=sales, total_sales=total_sales, total_amount=total_amount)


# =================== ADD VENDOR ROUTE ===================

@app.route('/add_vendor/<event_id>', methods=['GET', 'POST'])
def add_vendor(event_id):
    if request.method == 'POST':
        vendor_name = request.form['vendor_name']
        vendor_email = request.form['vendor_email']
        vendor_phone = request.form['vendor_phone']
        vendor_id = str(uuid.uuid4())

        try:
            conn = get_db_connection()
            conn.execute('INSERT INTO vendors (vendor_id, vendor_name, email, phone, event_id) VALUES (?, ?, ?, ?, ?)',
                         (vendor_id, vendor_name, vendor_email, vendor_phone, event_id))
            conn.commit()
            conn.close()

            # Send email to the vendor
            vendor_subject = "You've Been Added as a Vendor"
            vendor_body = f"Hello {vendor_name},\n\nYou have been added as a vendor. Please register using your email: {vendor_email}."
            send_email(vendor_email, vendor_subject, vendor_body)

            # Send notification email to the admin
            admin_subject = "New Vendor Added"
            admin_body = f"Vendor {vendor_name} ({vendor_email}) has been added to the event."
            send_email(EMAIL_SENDER, admin_subject, admin_body)

            flash('Vendor added successfully, and an email has been sent.', 'success')
        except Exception as e:
            print(f"Error adding vendor: {e}")
            flash('Error adding vendor. Please try again.', 'error')

        return redirect(url_for('admin_dash'))

    return render_template('add_vendor.html', event_id=event_id)

@app.route('/vendor_dash')
def vendor_dash():
    vendor_id = session.get('vendor_id')  # Ensure vendor is logged in

    if not vendor_id:
        flash('Please log in to access your dashboard.', 'error')
        return redirect(url_for('vendor_login'))

    conn = get_db_connection()
    vendor = conn.execute('SELECT * FROM vendors WHERE vendor_id = ?', (vendor_id,)).fetchone()

    # Fetch vendor's sales
    sales = conn.execute('SELECT * FROM sales WHERE booth_id = ?', (vendor_id,)).fetchall()

    # Calculate total sales and total sales amount
    total_sales = len(sales)
    total_sales_amount = sum(sale['sale_amount'] for sale in sales)

    conn.close()

    return render_template('vendor_dashboard.html', vendor=vendor, sales=sales, total_sales=total_sales, total_sales_amount=total_sales_amount)


@app.route('/vendor_login', methods=['GET', 'POST'])
def vendor_login():
    if request.method == 'POST':
        email = request.form['vendor_email']
        password = request.form['vendor_password']

        conn = get_db_connection()
        vendor = conn.execute('SELECT * FROM vendors WHERE email = ?', (email,)).fetchone()
        conn.close()

        if vendor and vendor['password'] == hashlib.sha256(password.encode()).hexdigest():
            session['vendor_logged_in'] = True
            session['vendor_id'] = vendor['vendor_id']  # Set vendor_id in session
            flash('Welcome to your dashboard!', 'success')
            return redirect(url_for('vendor_dash'))
        else:
            flash('Invalid credentials. Please try again.', 'error')

    return render_template('vendor_login.html')

@app.route('/vendor_logout', methods=['GET', 'POST'])
def vendor_logout():
    session.pop('vendor_logged_in', None)  # Remove vendor session
    flash('You have been logged out.', 'success')
    return redirect(url_for('vendor_login'))

    
def handle_voucher_redemption(voucher_id, booth_id, sale_amount):
    if redeem_voucher(voucher_id, booth_id, sale_amount):
        voucher = get_voucher_details(voucher_id)
        send_email(
            subject='Voucher Redeemed',
            body=f'Your voucher {voucher_id} has been redeemed. New balance: {voucher["balance"]}',
            to_email=voucher['email']
        )
    else:
        # Handle failure
        pass

# =================== REMOVE VENDOR ROUTE ===================
@app.route('/remove_vendor/<vendor_id>', methods=['POST'])
def remove_vendor(vendor_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM vendors WHERE vendor_id = ?', (vendor_id,))
    conn.commit()
    conn.close()
    flash('Vendor removed successfully.', 'success')
    return redirect(url_for('admin_dash'))

@app.route('/register', methods=['GET', 'POST'])
def register_vendor():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        conn = get_db_connection()

        # Check if the vendor exists and has not yet registered (i.e., no password set)
        vendor = conn.execute('SELECT * FROM vendors WHERE email = ?', (email,)).fetchone()

        if vendor:
            if vendor['password'] is None:  # Vendor is allowed to register
                conn.execute('UPDATE vendors SET password = ? WHERE email = ?', (hashed_password, email))
                conn.commit()
                flash('Vendor registered successfully!', 'success')
                return redirect(url_for('vendor_login'))
            else:
                flash('This email has already been registered.', 'error')
        else:
            flash('You are not authorized to register.', 'error')
        
        conn.close()

    return render_template('register_vendor.html')

    vendor = conn.execute('SELECT * FROM vendors WHERE email = ?', (email.strip().lower(),)).fetchone()

# =================== VIEW SALES FOR A VENDOR ===================
@app.route('/view_sales/<vendor_id>')
def view_sales(vendor_id):
    conn = get_db_connection()

    # Fetch all sales for the given vendor
    sales = conn.execute('SELECT * FROM sales WHERE booth_id = ?', (vendor_id,)).fetchall()

    # Calculate total sales and total amount
    total_sales = len(sales)
    total_sales_amount = sum(sale['sale_amount'] for sale in sales)

    # Fetch vendor details
    vendor = conn.execute('SELECT * FROM vendors WHERE vendor_id = ?', (vendor_id,)).fetchone()

    conn.close()

    return render_template('view_sales.html', sales=sales, vendor=vendor, total_sales=total_sales, total_sales_amount=total_sales_amount)

# =================== INDEX ROUTE ===================
@app.route('/')
def index():
    return render_template('index.html')
# =================== MANAGE VOUCHERS ROUTE ===================
@app.route('/manage_vouchers', methods=['GET', 'POST'])
def manage_vouchers():
    conn = get_db_connection()
    vouchers = conn.execute('SELECT * FROM vouchers').fetchall()  # Fetch all vouchers for dropdown
    conn.close()

    if request.method == 'POST':
        action = request.form['action']
        voucher_id = request.form['voucher_id']

        if action == 'top_up':
            top_up_amount = float(request.form['top_up_amount'])
            conn = get_db_connection()
            conn.execute('UPDATE vouchers SET balance = balance + ? WHERE voucher_id = ?', (top_up_amount, voucher_id))
            conn.commit()
            conn.close()
            flash(f'Voucher {voucher_id} topped up successfully by ${top_up_amount}', 'success')

        elif action == 'remove':
            conn = get_db_connection()
            conn.execute('DELETE FROM vouchers WHERE voucher_id = ?', (voucher_id,))
            conn.commit()
            conn.close()
            flash(f'Voucher {voucher_id} removed successfully', 'success')

        return redirect(url_for('manage_vouchers'))

    return render_template('manage_vouchers.html', vouchers=vouchers)

# =========================== PASSWORD ROUTE ============================

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        # Logic for handling the forgot password functionality goes here.
        flash('If this email is registered, a password reset link will be sent.', 'info')
        return redirect(url_for('vendor_login'))
    
    return render_template('forgot_password.html')

#def add_password_column_to_vendors():
#    conn = get_db_connection()
#    try:
#        conn.execute('ALTER TABLE vendors ADD COLUMN password TEXT')
#        conn.commit()
#    except sqlite3.OperationalError as e:
#       print(f"Error: {e}. This usually means the column already exists.")
#    finally:
#        conn.close()
#create_tables()
#add_password_column_to_vendors()
# =========================== VOUCHER ROUTE ============================
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

def send_voucher_email(subject, body, recipient, qr_code_img, voucher_id):
    sender_email = 'sales@aurorainfinity.co.uk'
    email_password = 'Sales_Aurora_00'
    smtp_server = 'aurorainfinity.co.uk'
    smtp_port = 465

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient
    msg['Subject'] = subject

    # Add the email body
    msg.attach(MIMEText(body, 'plain'))

    # Attach the QR code image
    qr_code_attachment = MIMEImage(qr_code_img.read(), name=f"{voucher_id}.png")
    qr_code_attachment.add_header('Content-Disposition', 'attachment', filename=f"{voucher_id}.png")
    msg.attach(qr_code_attachment)

    # Send the email
    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender_email, email_password)
            server.send_message(msg)
        print(f"Email sent to {recipient} with QR code.")
    except Exception as e:
        print(f"Failed to send email: {e}")
        
######
import qrcode
from io import BytesIO

def generate_qr_code(voucher_id):
    # Embed the unique voucher ID and domain in the QR code
    redemption_url = f"http://127.0.0.1:5000/redeem/{voucher_id}"  # Replace with your domain in production

    # Create the QR code object
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    # Add the URL data to the QR code
    qr.add_data(redemption_url)
    qr.make(fit=True)

    # Generate the image
    img = qr.make_image(fill='black', back_color='white')

    # Save the image in memory
    img_io = BytesIO()
    img.save(img_io, format='PNG')
    img_io.seek(0)

    return img_io

######
@app.route('/deduct_voucher', methods=['POST'])
def deduct_voucher():
    voucher_id = request.form['voucher_id']
    deduction_amount = float(request.form['deduction_amount'])
    
    conn = get_db_connection()
    voucher = conn.execute('SELECT * FROM vouchers WHERE voucher_id = ?', (voucher_id,)).fetchone()

    if voucher:
        current_balance = voucher['balance']

        if current_balance >= deduction_amount:
            new_balance = current_balance - deduction_amount
            conn.execute('UPDATE vouchers SET balance = ? WHERE voucher_id = ?', (new_balance, voucher_id))
            conn.commit()

            # Send email to buyer about balance update
            send_balance_update_email(voucher['voucher_name'], voucher['email'], deduction_amount, new_balance)

            flash('Deduction successful. Email sent to buyer.', 'success')
        else:
            flash('Insufficient balance on the voucher.', 'error')
    else:
        flash('Voucher not found.', 'error')

    conn.close()
    return redirect(url_for('admin_dash'))

def send_balance_update_email(voucher_name, voucher_email, deduction_amount, new_balance):
    try:
        print(f"Attempting to send balance update email to {voucher_email}")  # Debugging line
        msg = Message(
            'Voucher Balance Update',
            recipients=[voucher_email],
            body=f'A deduction of ${deduction_amount:.2f} was made on your voucher "{voucher_name}". Your remaining balance is ${new_balance:.2f}.'
        )
        mail.send(msg)
        print(f"Balance update email sent to {voucher_email}")  # Debugging line
    except Exception as e:
        print(f"Failed to send email: {e}")

def send_deduction_email(email, voucher_name, deduction_amount, remaining_balance):
    msg = Message('Voucher Deduction Notification', recipients=[email, 'sales@aurorainfinity.co.uk'])
    msg.body = f'''
    Hello,

    A deduction of ${deduction_amount:.2f} has been made from your voucher "{voucher_name}".

    Your remaining balance is now: ${remaining_balance:.2f}.

    Thank you,
    VoucherVault Team
    '''
    
    try:
        mail.send(msg)
        print(f"Deduction email sent to {email}")
    except Exception as e:
        print(f"Failed to send deduction email: {e}")
        
@app.route('/redeem/<voucher_id>', methods=['GET', 'POST'])
def redeem_voucher(voucher_id):
    vendor_id = session.get('vendor_id')  # Ensure vendor is logged in

    if not vendor_id:
        flash('You must be logged in to redeem vouchers.', 'error')
        return redirect(url_for('vendor_login'))

    conn = get_db_connection()
    voucher = conn.execute('SELECT * FROM vouchers WHERE voucher_id = ?', (voucher_id,)).fetchone()

    if request.method == 'POST':
        deduction_amount = float(request.form.get('deduction_amount'))

        # Debugging print statements
        print(f"Processing redemption for Voucher ID: {voucher_id}")
        print(f"Vendor ID: {vendor_id}")
        print(f"Deduction Amount: {deduction_amount}")

        # Check if the voucher has sufficient balance
        if voucher and voucher['balance'] >= deduction_amount:
            new_balance = voucher['balance'] - deduction_amount
            conn.execute('UPDATE vouchers SET balance = ? WHERE voucher_id = ?', (new_balance, voucher_id))

            # Insert the sale into the sales table
            conn.execute('INSERT INTO sales (voucher_id, booth_id, sale_amount) VALUES (?, ?, ?)',
                         (voucher_id, vendor_id, deduction_amount))
            
            conn.commit()  # Commit the transaction

            # Debugging print to confirm sale insertion
            print(f"Sale inserted for Voucher ID: {voucher_id}, Vendor ID: {vendor_id}, Amount: {deduction_amount}")

            flash(f'Deduction of £{deduction_amount} successful! New balance: £{new_balance}', 'success')
            return redirect(url_for('vendor_dash'))

        else:
            flash('Insufficient balance or voucher not found.', 'error')

    conn.close()
    return render_template('redeem_voucher.html', voucher_balance=voucher['balance'], voucher_id=voucher_id)


def send_balance_update_email(voucher_name, voucher_email, deduction_amount, new_balance):
    try:
        msg = Message(
            'Voucher Balance Update',
            recipients=[voucher_email],
            body=f'A deduction of ${deduction_amount:.2f} was made on your voucher "{voucher_name}". Your remaining balance is ${new_balance:.2f}.'
        )
        mail.send(msg)
        print(f"Balance update email sent to {voucher_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")
# =================== SEND EMAIL FUNCTION ===================
from threading import Thread


def send_voucher_purchase_email(voucher_name, voucher_email, voucher_amount):
    buyer_msg = Message(
        'Voucher Purchase Confirmation',
        recipients=[voucher_email],
        body=f'Thank you for purchasing {voucher_name} with a balance of ${voucher_amount}.'
    )
    
    admin_msg = Message(
        'Voucher Sold',
        recipients=['sales@aurorainfinity.co.uk'],  # Admin email
        body=f'Voucher {voucher_name} was purchased by {voucher_email} for ${voucher_amount}.'
    )
    
    # Send asynchronously
    Thread(target=send_async_email, args=(app, buyer_msg)).start()

# =================== SUPPORT HUB ROUTE (TO BE ADDED) ===================
@app.route('/support_hub')
def support_hub():
    return "Support hub coming soon."

# =================== SESSION MANAGEMENT ===================
@app.before_request
def ensure_admin_access():
    restricted_paths = ['admin_dash', 'create_event', 'manage_vouchers', 'register']
    if not session.get('admin_logged_in') and request.endpoint in restricted_paths:
        flash('You need to log in first!')
        return redirect(url_for('admin_login'))

@app.route('/create_voucher', methods=['GET', 'POST'])
def create_voucher():
    if request.method == 'POST':
        # Retrieve form data
        new_voucher_name = request.form['new_voucher_name']
        new_voucher_email = request.form['new_voucher_email']
        new_voucher_amount = float(request.form['new_voucher_amount'])

        # Generate a unique voucher ID
        new_voucher_id = str(uuid.uuid4())

        # Store the voucher in the database
        conn = get_db_connection()
        conn.execute('INSERT INTO vouchers (voucher_id, voucher_name, email, balance) VALUES (?, ?, ?, ?)',
                     (new_voucher_id, new_voucher_name, new_voucher_email, new_voucher_amount))
        conn.commit()
        conn.close()

        # Generate the QR code
        qr_code_img = generate_qr_code(new_voucher_id)

        # Send the voucher details via email
        subject = "Your Voucher Purchase Confirmation"
        body = f"Thank you for purchasing {new_voucher_name}! Use the attached QR code to redeem your voucher."
        send_voucher_email(subject, body, new_voucher_email, qr_code_img, new_voucher_id)

        flash(f'Voucher {new_voucher_name} sold successfully!', 'success')
        return redirect(url_for('admin_dash'))

    return render_template('create_voucher.html')

# =================== RUN THE APPLICATION ===================
if __name__ == '__main__':
    create_tables()
    app.run(debug=True)
    
print(request.form)

print(f"Inserting event: {event_name} on {event_date}")
