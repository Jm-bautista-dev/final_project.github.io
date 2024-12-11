from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename
from flask import flash


app = Flask(__name__)

app.secret_key = 'your_generated_secret_key'

# MySQL configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'  
app.config['MYSQL_PASSWORD'] = ''  
app.config['MYSQL_DB'] = 'accounts'

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def is_admin():
    return session.get('email') == 'jmbautistaa0428@gmail.com'


mysql = MySQL(app)

@app.route('/', methods=['GET', 'POST'])
def index():
    msg = ''
    if request.method == 'POST':
        if 'login' in request.form:
            # Login form
            email = request.form['email']
            password = request.form['password']
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM accounts WHERE email = %s', (email,))
            account = cursor.fetchone()
            if account and check_password_hash(account['password'], password):
                session['loggedin'] = True
                session['id'] = account['id']
                session['email'] = account['email']
                session['name'] = account['name']
                msg = 'Logged in successfully!'
                return redirect(url_for('home'))
            else:
                msg = 'Incorrect email/password!'
        elif 'register' in request.form:
            # Register form
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM accounts WHERE email = %s', (email,))
            account = cursor.fetchone()
            if account:
                msg = 'Account already exists!'
            elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
                msg = 'Invalid email address!'
            elif not re.match(r'[A-Za-z0-9]+', name):
                msg = 'Name must contain only characters and numbers!'
            elif not name or not password or not email:
                msg = 'Please fill out the form!'
            else:
                hashed_password = generate_password_hash(password)
                cursor.execute('INSERT INTO accounts (name, email, password) VALUES (%s, %s, %s)', (name, email, hashed_password,))
                mysql.connection.commit()
                msg = 'You have successfully registered!'
                print(msg)
    return render_template('index.html', msg=msg)

@app.route('/admin', methods=['GET'])
def admin():
    if 'loggedin' in session and is_admin():
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts')
        accounts = cursor.fetchall()
        return render_template('admin.html', accounts=accounts)
    return redirect(url_for('index'))


@app.route('/home')
def home():
    if 'loggedin' in session:
        return render_template('home.html', name=session['name'])
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('email', None)
    session.pop('name', None)
    response = redirect(url_for('index'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.before_request
def before_request():
    if 'loggedin' not in session and request.endpoint not in ('index', 'login', 'static'):
        return redirect(url_for('index'))



@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'loggedin' in session:
        msg = ''
        if request.method == 'POST':
            if 'update' in request.form:
                name = request.form['name']
                email = request.form['email']
                cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                cursor.execute('UPDATE accounts SET name = %s, email = %s WHERE id = %s', (name, email, session['id'],))
                mysql.connection.commit()
                session['name'] = name
                session['email'] = email
                msg = 'Profile updated successfully!'
            elif 'delete' in request.form:
                cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                cursor.execute('DELETE FROM accounts WHERE id = %s', (session['id'],))
                mysql.connection.commit()
                session.pop('loggedin', None)
                session.pop('id', None)
                session.pop('email', None)
                session.pop('name', None)
                return redirect(url_for('index'))
        if is_admin():
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM accounts')
            accounts = cursor.fetchall()
            return render_template('settings.html', name=session['name'], email=session['email'], profile_pic=session.get('profile_pic', 'default.png'), msg=msg, accounts=accounts)
        return render_template('settings.html', name=session['name'], email=session['email'], profile_pic=session.get('profile_pic', 'default.png'), msg=msg)
    return redirect(url_for('index'))


@app.route('/delete_account/<int:id>', methods=['POST'])
def delete_account(id):
    if 'loggedin' in session and is_admin():
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('DELETE FROM accounts WHERE id = %s', (id,))
        mysql.connection.commit()
        return redirect(url_for('settings'))
    return redirect(url_for('index'))

@app.route('/update_account_name/<int:id>', methods=['POST'])
def update_account_name(id):
    if 'loggedin' in session and is_admin():
        name = request.form['name']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('UPDATE accounts SET name = %s WHERE id = %s', (name, id,))
        mysql.connection.commit()
        flash('Account name updated successfully!')
        return redirect(url_for('settings'))
    return redirect(url_for('index'))

@app.route('/update_account_email/<int:id>', methods=['POST'])
def update_account_email(id):
    if 'loggedin' in session and is_admin():
        email = request.form['email']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('UPDATE accounts SET email = %s WHERE id = %s', (email, id,))
        mysql.connection.commit()
        flash('Account email updated successfully!')
        return redirect(url_for('settings'))
    return redirect(url_for('index'))



@app.route('/upload_profile_pic', methods=['POST'])
def upload_profile_pic():
    if 'loggedin' in session:
        if 'profile_pic' not in request.files:
            flash('No file part')
            return redirect(url_for('settings'))
        file = request.files['profile_pic']
        if file.filename == '':
            flash('No selected file')
            return redirect(url_for('settings'))
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('UPDATE accounts SET profile_pic = %s WHERE id = %s', (filename, session['id'],))
            mysql.connection.commit()
            session['profile_pic'] = filename
            flash('Profile picture updated successfully!')
            return redirect(url_for('settings'))
    return redirect(url_for('index'))




if __name__ == '__main__':
    app.run(debug=True)
