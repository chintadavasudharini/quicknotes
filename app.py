from flask import Flask, request, redirect, render_template, url_for, flash, Response, send_file, session
from flask_session import Session
from otp import otp_gen
from flask import send_file
from cmail import send_mail
from secret_token import endata, dndata
from datetime import datetime
from io import BytesIO
import re
import bcrypt
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import generate_password_hash, check_password_hash
import flask_excel as excel
import mysql.connector
from mysql.connector import (connection)
import os

# Load environment variables from .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Database connection details loaded from environment variables
db_host = os.environ.get('DB_HOST', 'localhost')
db_user = os.environ.get('DB_USER', 'root')
db_password = os.environ.get('DB_PASSWORD', 'vasu')
db_name = os.environ.get('DB_NAME', 'quicknotes')

mydb = connection.MySQLConnection(
    host=db_host,
    user=db_user,
    password=db_password,
    database=db_name
)


app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
app.secret_key = os.environ.get('SECRET_KEY', 'quicknotes')
excel.init_excel(app)
Session(app)

# secret key for serializer
s = URLSafeTimedSerializer(app.secret_key)


# Auto-reconnect to database if connection was dropped
@app.before_request
def before_request():
    global mydb
    try:
        if getattr(mydb, '_socket', None) is None or not mydb.is_connected():
            mydb.reconnect(attempts=3, delay=2)
        else:
            mydb.ping(reconnect=True, attempts=3, delay=2)
    except Exception as e:
        try:
            mydb = connection.MySQLConnection(
                host=db_host,
                user=db_user,
                password=db_password,
                database=db_name
            )
        except Exception as reconnect_err:
            app.logger.error(f"Failed to rebuild database connection: {reconnect_err}")


# ------------------- HOME -------------------
@app.route('/')
def home():
    return render_template('index.html')

# ------------------- REGISTER -------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email'].strip()
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        try:
            cursor = mydb.cursor()
            cursor.execute('SELECT COUNT(user_email) FROM users WHERE user_email=%s', [email])
            email_count = cursor.fetchone()
        except Exception as e:
            print(e)
            flash('Could not load page...', 'warning')
            return redirect(url_for('home'))

        if email_count[0] == 0:
            gotp = otp_gen()
            userdata = {'username': username, 'password': password, 'email': email, 'gotp': gotp}
            
            # Store OTP token in session
            session['otp_data'] = endata(data=userdata)

            # Send OTP email
            subject = 'OTP for Quick Notes Registration'
            body = f'Your OTP for Quick Notes registration is {gotp} \n This OTP is valid for 1 minute.'
            send_mail(to=email, subject=subject, body=body)

            flash('OTP has been sent to your email... OTP is valid for 1 minute.', 'success')
            return redirect(url_for('send_otp'))  # No pendata in URL

        else:
            flash('Email is already registered. Please login.', 'warning')
            return redirect(url_for('login'))

    return render_template('register.html')


# ------------------- OTP -------------------
@app.route('/sendotp', methods=['GET', 'POST'])
def send_otp():
    if 'otp_data' not in session:
        flash('OTP session expired or missing. Please register again.', 'danger')
        return redirect(url_for('register'))

    try:
        ddata = dndata(session['otp_data'])
        if ddata is None:
            flash('OTP expired or invalid. Please register again.', 'danger')
            session.pop('otp_data', None)
            return redirect(url_for('register'))
        email = ddata.get('email')
    except Exception as e:
        print(f"Error reading OTP email: {e}")
        flash('OTP session invalid. Please register again.', 'danger')
        session.pop('otp_data', None)
        return redirect(url_for('register'))

    if request.method == 'POST':
        uotp = request.form['otp'].strip()
        try:
            ddata_post = dndata(session['otp_data'], max_age=60)  # OTP expires in 1 minute
            if ddata_post is None:
                flash('OTP expired. Please use "Resend OTP".', 'warning')
                return render_template('otp.html', email=email)   # Stay on OTP page
        except Exception as e:
            print(e)
            flash('Could not verify OTP. Please use "Resend OTP".', 'warning')
            return render_template('otp.html', email=email)       # Stay on OTP page

        if ddata_post['gotp'] == uotp:
            password_hash = generate_password_hash(ddata_post['password'])
            try:
                cursor = mydb.cursor()
                cursor.execute(
                    'INSERT INTO users (user_email, user_name, password) VALUES (%s, %s, %s)',
                    [ddata_post['email'], ddata_post['username'], password_hash]
                )
                mydb.commit()
            except Exception as e:
                print(e)
                flash('Registration failed. Try again.', 'danger')
                return redirect(url_for('register'))
            finally:
                session.pop('otp_data', None)

            flash('OTP verified and registered successfully!', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid OTP. Please enter the correct OTP or use "Resend OTP".', 'danger')
            return render_template('otp.html', email=email)       # Stay on OTP page

    return render_template('otp.html', email=email)



# ------------------- RESEND OTP -------------------
@app.route('/resend_otp')
def resend_otp():
    if 'otp_data' not in session:
        flash('OTP session expired or missing. Please register again.', 'danger')
        return redirect(url_for('register'))

    try:
        old_data = dndata(session['otp_data'])
        if old_data is None:
            flash('OTP expired. Please register again.', 'danger')
            session.pop('otp_data', None)
            return redirect(url_for('register'))
    except Exception as e:
        print(e)
        flash('Could not verify OTP. Please register again.', 'warning')
        session.pop('otp_data', None)
        return redirect(url_for('register'))

    # ✅ Generate brand new OTP
    new_otp = otp_gen()

    # ✅ Reset OTP session data (with fresh timestamp)
    new_data = {
        'email': old_data['email'],
        'username': old_data['username'],
        'password': old_data['password'],
        'gotp': new_otp
    }
    session['otp_data'] = endata(data=new_data)

    # ✅ Send new OTP
    subject = 'New OTP for Quick Notes Registration'
    body = f'Your new OTP for Quick Notes registration is {new_otp}\nThis OTP is valid for 1 minute.'
    send_mail(to=new_data['email'], subject=subject, body=body)

    flash('A new OTP has been sent to your email. Please check your inbox.', 'success')
    return render_template('otp.html', email=new_data['email'])


# ------------------- FORGOT PASSWORD -------------------
@app.route('/forgotpassword', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        user_email = request.form['email'].strip()
        try:
            cursor = mydb.cursor()
            cursor.execute('SELECT count(user_email) FROM users WHERE user_email=%s', [user_email])
            email_count = cursor.fetchone()
            if email_count[0] == 1:
                # generate a one-time token
                token = s.dumps(user_email, salt="reset-password")

                subject = 'Reset link for Quick Notes Password'
                body = f'''Click the link to reset your password:
{url_for("reset_password", token=token, _external=True)}

This link is valid for 1 minute and can be used only once.'''
                send_mail(to=user_email, subject=subject, body=body)

                flash('Password reset link sent to your registered email.', 'success')
                return redirect(url_for('forgot_password'))
            else:
                flash('Email not found.', 'danger')
                return redirect(url_for('login'))
        except Exception as e:
            print(f'Error in forgot password: {e}')
            flash('Could not process request. Please try again.', 'warning')
            return redirect(url_for('login'))
    return render_template('forgotpassword.html')


# ------------------- RESET PASSWORD -------------------
used_tokens = set()  # simple in-memory store (clears when app restarts)

@app.route('/resetpassword/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if request.method == 'POST':
        new_password = request.form['password'].strip()
        try:
            # check if already used
            if token in used_tokens:
                flash('This reset link has already been used.', 'warning')
                return redirect(url_for('forgot_password'))

            # validate and decode token
            user_email = s.loads(token, salt="reset-password", max_age=60)  # 1 min validity

            # 🔑 hash the new password
            new_hash = generate_password_hash(new_password)

            cursor = mydb.cursor()
            cursor.execute('UPDATE users SET password=%s WHERE user_email=%s',
                           [new_hash, user_email])
            mydb.commit()
            cursor.close()

            # mark token as used
            used_tokens.add(token)

            flash('Password reset successful! Please login.', 'success')
            return redirect(url_for('login'))

        except SignatureExpired:
            flash('Reset link expired. Please try again.', 'warning')
            return redirect(url_for('forgot_password'))
        except BadSignature:
            flash('Invalid reset link. Please try again.', 'danger')
            return redirect(url_for('forgot_password'))
        except Exception as e:
            print(f'Error in resetting password: {e}')
            flash('Could not reset password. Please try again.', 'danger')
            return redirect(url_for('forgot_password'))

    return render_template('resetpassword.html', token=token)


# ------------------- LOGIN -------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if not session.get('suemail'):
        if request.method == 'POST':
            uemail = request.form['email'].strip()
            upassword = request.form['password'].strip()
            try:
                cursor = mydb.cursor(buffered=True)
                cursor.execute('SELECT password FROM users WHERE user_email=%s', [uemail])
                result = cursor.fetchone()
            except Exception as e:
                print(f'Error in fetching user data: {e}')
                flash('Could not load page...', 'danger')
                return redirect(url_for('login'))

            if result:
                db_password = result[0]
                # Decode bytes to string because VARBINARY stores bytes
                if isinstance(db_password, bytes):
                    db_password = db_password.decode('utf-8')

                if check_password_hash(db_password, upassword):
                    session['suemail'] = uemail
                    try:
                        cursor.execute('UPDATE users SET last_login = NOW() WHERE user_email = %s', [uemail])
                        mydb.commit()
                    except Exception as e:
                        print("Failed to update last_login:", e)
                    flash('Login successful!', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    flash('Incorrect password. Please try again.', 'danger')
                    return redirect(url_for('login'))
            else:
                flash('Email not registered. Please register first.', 'danger')
                return redirect(url_for('register'))
        return render_template('login.html')
    else:
        return redirect(url_for('dashboard'))



# ------------------- DASHBOARD -------------------
@app.route('/dashboard')
def dashboard():

    if not session.get('suemail'):
        flash('Please login to access the dashboard.', 'warning')
        return redirect(url_for('login'))

    email = session['suemail']

    try:
        cursor = mydb.cursor()

        # Total Notes
        cursor.execute(
            "SELECT COUNT(*) FROM notes WHERE user_email=%s",
            (email,)
        )
        notes_count = cursor.fetchone()[0]

        # Total Files
        cursor.execute(
            "SELECT COUNT(*) FROM files WHERE user_email=%s",
            (email,)
        )
        files_count = cursor.fetchone()[0]

        cursor.close()

        print(email, "is logged in")

    except Exception as e:
        print("Dashboard Error:", e)
        notes_count = 0
        files_count = 0

    return render_template(
        'dashboard.html',
        notes_count=notes_count,
        files_count=files_count,
        notes_results=None,
        files_results=None,
        search_performed=False
    )


# ------------------- PROFILE -------------------
@app.route('/profile', methods=['GET'])
def profile():
    if 'suemail' not in session:  # Assuming 'suemail' stores the logged-in user's email
        flash('Please login first.', 'warning')
        return redirect(url_for('login'))

    email = session['suemail']
    try:
        cursor = mydb.cursor(dictionary=True)
        cursor.execute('SELECT user_email, user_name, created_at, updated_at, last_login FROM users WHERE user_email=%s', [email])
        user = cursor.fetchone()
        cursor.execute('select count(*) from notes where user_email=%s',[email])
        note_count = cursor.fetchone()
        print(note_count)
        cursor.execute('select count(*) from files where user_email=%s',[email])
        file_count = cursor.fetchone()
        cursor.close()
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('login'))
        else:
            return render_template('profile.html', user=user, note_count=note_count, file_count=file_count)
    except Exception as e:
        print("DB error:", e)
        flash('Something went wrong.', 'danger')
        return redirect(url_for('dashboard'))


# ------------------- CHANGE PASSWORD -------------------
@app.route('/change_password', methods=['POST'])
def change_password():
    if 'suemail' not in session:
        return redirect(url_for('login'))

    email = session['suemail']
    old_pass = request.form.get('old_password').strip()
    new_pass = request.form.get('new_password').strip()
    confirm_pass = request.form.get('confirm_password').strip()

    if not old_pass or not new_pass or not confirm_pass:
        flash('All fields are required.', 'danger')
        return redirect(url_for('profile'))

    if new_pass != confirm_pass:
        flash('New password and confirm password do not match.', 'danger')
        return redirect(url_for('profile'))

    try:
        cursor = mydb.cursor(dictionary=True)

        # Fetch current password hash from DB
        cursor.execute("SELECT password FROM users WHERE user_email=%s", (email,))
        user = cursor.fetchone()

        if not user:
            flash('User not found.', 'danger')
            cursor.close()
            return redirect(url_for('profile'))

        db_password = user['password']

        # Decode bytes to string if using VARBINARY
        if isinstance(db_password, bytes):
            db_password = db_password.decode('utf-8')

        # Check old password
        if not check_password_hash(db_password, old_pass):
            flash('Old password is incorrect.', 'danger')
            cursor.close()
            return redirect(url_for('profile'))

        # Prevent same password
        if check_password_hash(db_password, new_pass):
            flash('New password cannot be the same as the current password. Try a different one.', 'warning')
            cursor.close()
            return redirect(url_for('profile'))

        # Generate OTP and prepare password hash
        gotp = otp_gen()
        new_hash = generate_password_hash(new_pass)

        # Save to session (encrypted via endata)
        userdata = {
            'email': email,
            'new_password_hash': new_hash,
            'gotp': gotp
        }
        session['change_pass_otp_data'] = endata(data=userdata)

        # Send OTP email
        subject = 'OTP for Password Change'
        body = f'Your OTP to verify password change is {gotp} \n This OTP is valid for 1 minute.'
        send_mail(to=email, subject=subject, body=body)

        cursor.close()

        flash('An OTP has been sent to your email to verify password change... OTP is valid for 1 minute.', 'success')
        return redirect(url_for('verify_change_password_otp'))

    except Exception as e:
        print("DB error:", str(e))
        flash('Something went wrong. Please try again.', 'danger')
        return redirect(url_for('profile'))


# ------------------- VERIFY CHANGE PASSWORD OTP -------------------
@app.route('/verify_change_password_otp', methods=['GET', 'POST'])
def verify_change_password_otp():
    if 'suemail' not in session:
        return redirect(url_for('login'))

    if 'change_pass_otp_data' not in session:
        flash('Password change session expired or missing. Please try again.', 'danger')
        return redirect(url_for('profile'))

    try:
        ddata = dndata(session['change_pass_otp_data'])
        if ddata is None:
            flash('OTP expired or invalid. Please try again.', 'danger')
            session.pop('change_pass_otp_data', None)
            return redirect(url_for('profile'))
        email = ddata.get('email')
    except Exception as e:
        print(f"Error reading change pass OTP data: {e}")
        flash('Password change session invalid. Please try again.', 'danger')
        session.pop('change_pass_otp_data', None)
        return redirect(url_for('profile'))

    if request.method == 'POST':
        uotp = request.form['otp'].strip()
        try:
            ddata_post = dndata(session['change_pass_otp_data'], max_age=60)  # 1 min expiration
            if ddata_post is None:
                flash('OTP expired. Please use "Resend OTP".', 'warning')
                return render_template('change_password_otp.html', email=email)
        except Exception as e:
            print(e)
            flash('Could not verify OTP. Please use "Resend OTP".', 'warning')
            return render_template('change_password_otp.html', email=email)

        if ddata_post['gotp'] == uotp:
            try:
                cursor = mydb.cursor()
                # Update password in DB
                cursor.execute("UPDATE users SET password=%s WHERE user_email=%s",
                               [ddata_post['new_password_hash'], ddata_post['email']])
                # Update users.updated_at timestamp
                cursor.execute("UPDATE users SET updated_at = NOW() WHERE user_email = %s",
                               [ddata_post['email']])
                mydb.commit()
                cursor.close()
            except Exception as e:
                print(e)
                flash('Password update failed. Try again.', 'danger')
                return redirect(url_for('profile'))
            finally:
                session.pop('change_pass_otp_data', None)

            flash('Password changed successfully!', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Invalid OTP. Please enter the correct OTP or use "Resend OTP".', 'danger')
            return render_template('change_password_otp.html', email=email)

    return render_template('change_password_otp.html', email=email)


# ------------------- RESEND CHANGE PASSWORD OTP -------------------
@app.route('/resend_change_password_otp')
def resend_change_password_otp():
    if 'suemail' not in session:
        return redirect(url_for('login'))

    if 'change_pass_otp_data' not in session:
        flash('Password change session expired or missing. Please try again.', 'danger')
        return redirect(url_for('profile'))

    try:
        old_data = dndata(session['change_pass_otp_data'])
        if old_data is None:
            flash('OTP expired. Please try again.', 'danger')
            session.pop('change_pass_otp_data', None)
            return redirect(url_for('profile'))
    except Exception as e:
        print(e)
        flash('Could not verify OTP. Please try again.', 'warning')
        session.pop('change_pass_otp_data', None)
        return redirect(url_for('profile'))

    # Generate brand new OTP
    new_otp = otp_gen()

    # Reset session data with fresh timestamp
    new_data = {
        'email': old_data['email'],
        'new_password_hash': old_data['new_password_hash'],
        'gotp': new_otp
    }
    session['change_pass_otp_data'] = endata(data=new_data)

    # Send new OTP
    subject = 'New OTP for Password Change'
    body = f'Your new OTP to verify password change is {new_otp}\nThis OTP is valid for 1 minute.'
    send_mail(to=new_data['email'], subject=subject, body=body)

    flash('A new OTP has been sent to your email. Please check your inbox.', 'success')
    return render_template('change_password_otp.html', email=new_data['email'])


# ------------------- DELETE ALL NOTES -------------------
@app.route('/delete_all_notes')
def delete_all_notes():
    if 'suemail' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('login'))

    email = session['suemail']
    try:
        cursor = mydb.cursor()

        # Debug: check count before delete
        cursor.execute("SELECT COUNT(*) FROM notes WHERE user_email=%s", (email,))
        before_count = cursor.fetchone()[0]
        print(f"Before delete: {before_count} notes for {email}")

        # delete all notes
        cursor.execute("DELETE FROM notes WHERE user_email=%s", (email,))
        cursor.execute("UPDATE users SET updated_at = NOW() WHERE user_email = %s", (email,))
        mydb.commit()

        # Debug: check count after delete
        cursor.execute("SELECT COUNT(*) FROM notes WHERE user_email=%s", (email,))
        after_count = cursor.fetchone()[0]
        print(f"After delete: {after_count} notes for {email}")

        cursor.close()

        if before_count > 0 and after_count == 0:
            flash('All your notes have been deleted.', 'danger')
        elif before_count == 0:
            flash('No notes found to delete.', 'warning')
        elif after_count > 0:
            flash('Some notes could not be deleted. Please try again.', 'warning')
        elif after_count == 0:
            flash('All your notes have been deleted.', 'danger')
        else:
            flash('Some notes may not have been deleted.', 'warning')

        return redirect(url_for('viewallnotes'))

    except Exception as e:
        print("DB error in delete_all_notes:", e)
        flash('Could not delete notes. Try again.', 'warning')
        return redirect(url_for('viewallnotes'))


# ------------------- DELETE ALL FILES -------------------
@app.route('/delete_all_files')
def delete_all_files():
    if 'suemail' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('login'))

    email = session['suemail']
    try:
        cursor = mydb.cursor()

        # Count before delete
        cursor.execute("SELECT COUNT(*) FROM files WHERE user_email=%s", (email,))
        before_count = cursor.fetchone()[0]
        print(f"[DEBUG] Before delete: {before_count} files for {email}")

        # delete all files
        cursor.execute("DELETE FROM files WHERE user_email=%s", (email,))
        cursor.execute("UPDATE users SET updated_at = NOW() WHERE user_email = %s", (email,))
        mydb.commit()

        # Count after delete
        cursor.execute("SELECT COUNT(*) FROM files WHERE user_email=%s", (email,))
        after_count = cursor.fetchone()[0]
        print(f"[DEBUG] After delete: {after_count} files for {email}")

        cursor.close()
        

        if before_count > 0 and after_count == 0:
            flash('All your files have been deleted.', 'danger')
        elif before_count == 0:
            flash('No files found to delete.', 'warning')
        elif after_count > 0:
            flash('Some files could not be deleted. Please try again.', 'warning')
        elif after_count == 0:
            flash('All your files have been deleted.', 'danger')        
        else:
            flash('Some files may not have been deleted.', 'warning')

        return redirect(url_for('viewallfiles'))

    except Exception as e:
        print("DB error in delete_all_files:", e)
        flash('Could not delete files. Try again.', 'warning')
        return redirect(url_for('viewallfiles'))


# ------------------- DELETE ACCOUNT (with notes & files) -------------------
@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'suemail' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('login'))

    email = session['suemail']
    confirm_email = request.form.get('confirm_email', '').strip()

    if confirm_email != email:
        flash('Email does not match. Account not deleted.', 'warning')
        return redirect(url_for('profile'))

    try:
        cursor = mydb.cursor(dictionary=True)

        # Count notes & files
        cursor.execute("SELECT COUNT(*) AS cnt FROM notes WHERE user_email=%s", (email,))
        note_count = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) AS cnt FROM files WHERE user_email=%s", (email,))
        file_count = cursor.fetchone()['cnt']

        # Case checks
        if note_count > 0 and file_count > 0:
            flash('All your notes and files should be deleted before deleting your account.', 'warning')
            cursor.close()
            
            return redirect(url_for('profile'))

        elif note_count > 0 and file_count == 0:
            flash('Please delete all your notes. No files found. Account not deleted.', 'warning')
            cursor.close()
        
            return redirect(url_for('profile'))

        elif file_count > 0 and note_count == 0:
            flash('Please delete all your files. No notes found. Account not deleted.', 'warning')
            cursor.close()
            
            return redirect(url_for('profile'))

        # If no notes & no files → delete only account
        cursor.execute("DELETE FROM users WHERE user_email=%s", (email,))
        mydb.commit()

        cursor.close()
    

        session.clear()  # Logout
        flash('No notes or files found. Your account has been permanently deleted.', 'danger')
        return redirect(url_for('home'))

    except Exception as e:
        print("DB error in delete_account:", e)
        flash('Something went wrong. Could not delete account.', 'warning')
        return redirect(url_for('profile'))



# ------------------- SEARCH NOTES AND FILES -------------------
@app.route('/search', methods=['POST'])
def search():
    if not session.get('suemail'):
        flash('Please login to search.', 'warning')
        return redirect(url_for('login'))

    query = request.form.get('sdata', '').strip()

    if not query:
        flash('Please enter a search term.', 'warning')
        return redirect(url_for('dashboard'))

    # Allow letters, numbers, spaces
    pattern = re.compile(r'^[A-Za-z0-9 ]+$')
    if not pattern.match(query):
        flash('Invalid search term.', 'warning')
        return redirect(url_for('dashboard'))

    notes_results = []
    files_results = []
    notes_count = 0
    files_count = 0

    try:
        cursor = mydb.cursor(dictionary=True)

        # Fetch total counts for stats cards
        cursor.execute("SELECT COUNT(*) AS count FROM notes WHERE user_email=%s", (session.get('suemail'),))
        notes_count = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) AS count FROM files WHERE user_email=%s", (session.get('suemail'),))
        files_count = cursor.fetchone()['count']

        # --- SEARCH NOTES ---
        cursor.execute("""
            SELECT * FROM notes 
            WHERE user_email=%s AND (
                n_id LIKE %s OR
                n_title LIKE %s OR
                n_description LIKE %s OR
                created_at LIKE %s
            )
        """, [session.get('suemail'), f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%'])
        notes_results = cursor.fetchall()

        # --- SEARCH FILES ---
        cursor.execute("""
            SELECT * FROM files 
            WHERE user_email=%s AND (
                f_id LIKE %s OR
                f_title LIKE %s OR
                f_description LIKE %s OR
                file_name LIKE %s OR
                created_at LIKE %s
            )
        """, [session.get('suemail')] + [f'%{query}%']*5)
        files_results = cursor.fetchall()

    except Exception as e:
        print(f'Error searching notes/files: {e}')
        flash('Could not search notes/files. Please try again.', 'danger')
        return redirect(url_for('dashboard'))

    # Search has been performed
    return render_template('dashboard.html', 
                           notes_count=notes_count,
                           files_count=files_count,
                           notes_results=notes_results, 
                           files_results=files_results, 
                           search_performed=True)


# ------------------- ADD NOTE -------------------
@app.route('/addnotes', methods=['GET', 'POST'])
def add_notes():
    if not session.get('suemail'):
        flash('Please login to add notes.', 'warning')
        return redirect(url_for('login'))
    if request.method == 'POST':
        note_title = request.form['n_title'].strip()
        note_content = request.form['n_description'].strip()
        try:
            cursor = mydb.cursor(buffered=True)
            cursor.execute(
                'INSERT INTO notes (n_title, n_description, user_email) VALUES (%s, %s, %s)',
                [note_title, note_content, session['suemail']]
            )
            cursor.execute(
                'UPDATE users SET updated_at = NOW() WHERE user_email = %s',
                [session['suemail']]
            )
            mydb.commit()
            cursor.close()
        except Exception as e:
            print(f'Error adding note: {e}')
            flash('Could not add note. Please try again.', 'danger')
            return redirect(url_for('add_notes'))
        else:
            flash('Note added successfully!', 'success')
            return redirect(url_for('viewallnotes'))
    return render_template('addnote.html')


# ------------------- VIEW ALL NOTES -------------------
@app.route('/viewallnotes')
def viewallnotes():
    if session.get('suemail') is None:
        flash('Please login to view all notes.', 'warning')
        return redirect(url_for('login'))
    
    allnotesdata = []
    try:
        cursor = mydb.cursor(dictionary=True, buffered=True)
        cursor.execute(
            'SELECT n_id, n_title, created_at FROM notes WHERE user_email=%s',
            [session['suemail']]
        )
        allnotesdata = cursor.fetchall()
        cursor.close()
    except Exception as e:
        print(f'Error fetching notes: {e}')
        flash('Could not load notes. Showing empty notes list.', 'warning')

    if not allnotesdata:
        flash('No notes found. Please add some notes first.', 'info')

    return render_template('viewallnotes.html', notedata=allnotesdata)


# ------------------- GET NOTES DATA -------------------
@app.route('/getnotesdata')
def getnotesdata():
    if not session.get('suemail'):
        flash('Please login to download notes.', 'warning')
        return redirect(url_for('login'))

    try:
        cursor = mydb.cursor(dictionary=True)
        cursor.execute(
            'SELECT n_id, n_title, n_description, created_at FROM notes WHERE user_email=%s',
            [session['suemail']]
        )
        notesdata = cursor.fetchall()

        if not notesdata:   
            flash('No notes found to export.', 'info')
            return redirect(url_for('viewallnotes'))

        # Define headers
        columns = ['Notes_ID', 'Notes_Title', 'Notes_Content', 'Notes_Created_At']

        # Use list comprehension with correct order
        array_data = [list(note.values()) for note in notesdata]

        # Insert headers at top
        array_data.insert(0, columns)

        return excel.make_response_from_array(array_data, "xlsx", file_name="NotesData")

    except Exception as e:
        print(f'Error fetching notes for Excel: {e}')
        flash('Could not export notes. Please try again.', 'danger')
        return redirect(url_for('dashboard'))


# ------------------- VIEW NOTE -------------------
@app.route('/viewnote/<int:nid>', methods=['GET'])
def viewnote(nid):
    if not session.get('suemail'):
        flash('Please login to view note.', 'warning')
        return redirect(url_for('login'))
    try:
        cursor = mydb.cursor(dictionary=True, buffered=True)
        cursor.execute(
            'SELECT n_id, n_title, n_description, created_at FROM notes WHERE n_id=%s AND user_email=%s',
            [nid, session['suemail']]
        )
        note = cursor.fetchone()
        cursor.close()
    except Exception as e:
        print(f'Error fetching note: {e}')
        flash('Could not load note. Please try again.', 'danger')
        return redirect(url_for('dashboard'))
    if not note:
        flash('Note not found.', 'info')
        return redirect(url_for('viewallnotes'))
    return render_template('viewnote.html', note=note)


# ------------------- EDIT NOTE -------------------
@app.route('/editnote/<int:nid>', methods=['POST'])
def editnote(nid):
    if not session.get('suemail'):
        flash('Please login to edit note.', 'warning')
        return redirect(url_for('login'))
    new_title = request.form['n_title'].strip()
    new_content = request.form['n_description'].strip()
    try:
        cursor = mydb.cursor(buffered=True)
        cursor.execute(
            'UPDATE notes SET n_title=%s, n_description=%s WHERE n_id=%s AND user_email=%s',
            [new_title, new_content, nid, session['suemail']]
        )
        cursor.execute(
            'UPDATE users SET updated_at = NOW() WHERE user_email = %s',
            [session['suemail']]
        )
        mydb.commit()
        cursor.close()
    except Exception as e:
        print(f'Error updating note: {e}')
        flash('Could not update note. Please try again.', 'warning')
    else:
        flash('Note updated successfully!', 'info')
    return redirect(url_for('viewnote', nid=nid))


# ------------------- DOWNLOAD NOTE -------------------
@app.route('/download_note/<int:nid>')
def download_note(nid):
    if not session.get('suemail'):
        flash('Please login to download note.', 'warning')
        return redirect(url_for('login'))

    try:
        cursor = mydb.cursor(dictionary=True)
        cursor.execute('SELECT n_title, n_description, created_at FROM notes WHERE n_id=%s AND user_email=%s',
                       (nid, session['suemail']))
        note = cursor.fetchone()
        cursor.close()

        if not note:
            flash('Note not found.', 'danger')
            return redirect(url_for('viewallnotes'))

        # Create a downloadable text file
        content = f"\nTitle: {note['n_title']}\n\n\nContent:\n\n{note['n_description']}\n\n\nCreated At: {note['created_at'].strftime('%Y-%m-%d , %H:%M:%S')}"
        filename = f"{note['n_title'].replace(' ', '_')}.txt"
        return Response(
            content,
            mimetype='text/plain',
            headers={'Content-Disposition': f'attachment;filename={filename}'}
        )

    except Exception as e:
        print(f"Error downloading note: {e}")
        flash('Failed to download note.', 'warning')
        return redirect(url_for('viewallnotes'))


# ------------------- DELETE NOTE -------------------
@app.route('/deletenote/<int:nid>', methods=['POST'])
def deletenote(nid):
    if not session.get('suemail'):
        flash('Please login to delete note.', 'warning')
        return redirect(url_for('login'))
    try:
        cursor = mydb.cursor(buffered=True)
        cursor.execute(
            'DELETE FROM notes WHERE n_id=%s AND user_email=%s',
            [nid, session['suemail']]
        )
        cursor.execute(
            'UPDATE users SET updated_at = NOW() WHERE user_email = %s',
            [session['suemail']]
        )
        mydb.commit()
        cursor.close()
    except Exception as e:
        print(f'Error deleting note: {e}')
        flash('Could not delete note. Please try again.', 'warning')
        return redirect(url_for('viewnote', nid=nid))
    else:
        flash('Note deleted successfully!', 'danger')
        return redirect(url_for('viewallnotes'))



# ------------------- UPLOAD FILE -------------------
@app.route('/addfile', methods=['GET', 'POST'])
def fileupload():
    if not session.get('suemail'):
        flash('Please login to upload files.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part in the request.', 'warning')
            return redirect(url_for('dashboard'))

        file_toupload = request.files['file']
        if file_toupload.filename == '':
            flash('No selected file.', 'warning')
            return redirect(url_for('dashboard'))

        file_title = request.form.get('f_title').strip()
        file_content = request.form.get('f_description').strip()
        if not file_title:
            flash("File title is required!", "warning")
            return redirect(url_for('fileupload'))

        fname = file_toupload.filename
        print(f"Uploaded file name: {fname}")
        fdata = file_toupload.read()
        print(f"File size (bytes): {len(fdata)}")

        try:
            cursor = mydb.cursor(dictionary=True, buffered=True)

            # Check if file already exists
            cursor.execute("SELECT * FROM files WHERE file_name=%s AND user_email=%s", (fname, session['suemail']))
            existing_file = cursor.fetchone()
            if existing_file:
                flash('A file with this name already exists!', 'warning')
                cursor.close()
                return redirect(url_for('viewallfiles'))

            # Insert file if not exists
            cursor.execute(
                'INSERT INTO files(f_title, f_description, file_name, file_data, created_at, user_email) '
                'VALUES (%s, %s, %s, %s, %s, %s)',
                [file_title, file_content, fname, fdata, datetime.now(), session['suemail']]
            )
            cursor.execute(
                'UPDATE users SET updated_at = NOW() WHERE user_email = %s',
                [session['suemail']]
            )
            mydb.commit()
            cursor.close()

        except Exception as e:
            print(f'Error saving file: {e}')
            flash('Could not upload file. Please try again.', 'warning')
            return redirect(url_for('dashboard'))

        else:
            flash('File uploaded successfully!', 'success')
            return redirect(url_for('viewallfiles'))

    return render_template('addfile.html')


# ------------------- VIEW ALL FILES -------------------
@app.route('/viewallfiles')
def viewallfiles():
    if not session.get('suemail'):
        flash('Please login to view files.', 'warning')
        return redirect(url_for('login'))
    
    allfilesdata = []
    try:
        cursor = mydb.cursor(dictionary=True, buffered=True)
        cursor.execute(
            'SELECT f_id, f_title, file_name, created_at FROM files WHERE user_email=%s',
            [session['suemail']]
        )
        allfilesdata = cursor.fetchall()
        cursor.close()
    except Exception as e:
        print(f'Error fetching files: {e}')
        flash('Could not load files. Showing empty files list.', 'warning')
        
    if not allfilesdata:  
            flash('No files found. Please upload some files first.', 'info')
    
    return render_template('viewallfiles.html', filedata=allfilesdata)
    
    
# ------------------- GET FILES DATA -------------------
@app.route('/getfilesdata')
def getfilesdata():
    if not session.get('suemail'):
        flash('Please login to download files.', 'warning')
        return redirect(url_for('login'))

    try:
        cursor = mydb.cursor(dictionary=True)
        cursor.execute(
            'SELECT f_id, f_title, f_description, file_name, created_at FROM files WHERE user_email=%s',
            [session['suemail']]
        )
        filesdata = cursor.fetchall()

        if not filesdata:
            flash('No files found to export.', 'info')
            return redirect(url_for('viewallfiles'))

        # Reorder columns
        columns = ['FILE_ID', 'File_Title', 'File_Description', 'File_Name', 'File_Uploaded_At']
        array_data = [list(file.values()) for file in filesdata]
        array_data.insert(0, columns)

        return excel.make_response_from_array(array_data, "xlsx", file_name="FilesData")

    except Exception as e:
        print(f'Error fetching files for Excel: {e}')
        flash('Could not export files. Please try again.', 'warning')
        return redirect(url_for('dashboard'))
    

# ------------------- VIEW FILE -------------------
@app.route('/viewfile/<fid>')
def viewfile(fid):
    if not session.get('suemail'):
        flash('Please login to view files.', 'warning')
        return redirect(url_for('login'))
    try:
        cursor = mydb.cursor(dictionary=True, buffered=True)
        cursor.execute(
            'SELECT f_title, f_description, file_name, file_data, created_at FROM files WHERE f_id=%s AND user_email=%s',
            [fid, session['suemail']]
        )
        viewfile = cursor.fetchone()
        print(viewfile)
        cursor.close()
        if viewfile:
            return render_template('viewfile.html', file=viewfile,fid=fid)
        else:
            flash('File not found.', 'danger')
            return redirect(url_for('viewallfiles'))
    except Exception as e:
        print(f'Error fetching file: {e}')
        flash('Could not load file. Please try again.', 'warning')
        return redirect(url_for('dashboard'))
    
    
# ------------------- EDIT FILE -------------------
@app.route('/editfile/<fid>', methods=['POST'])
def edit_file(fid):
    if not session.get('suemail'):
        flash('Please login to edit files.', 'warning')
        return redirect(url_for('login'))
    try:
        file_title = request.form.get('f_title').strip()
        file_desc = request.form.get('f_description').strip()
        file_obj = request.files.get('f_file')  # <-- fixed here

        cursor = mydb.cursor()
        if file_obj and file_obj.filename != '':
            fdata = file_obj.read()
            cursor.execute(
                'UPDATE files SET f_title=%s, f_description=%s, file_name=%s, file_data=%s WHERE f_id=%s AND user_email=%s',
                [file_title, file_desc, file_obj.filename, fdata, fid, session['suemail']]
            )
        else:
            cursor.execute(
                'UPDATE files SET f_title=%s, f_description=%s WHERE f_id=%s AND user_email=%s',
                [file_title, file_desc, fid, session['suemail']]
            )
        cursor.execute(
            'UPDATE users SET updated_at = NOW() WHERE user_email = %s',
            [session['suemail']]
        )
        mydb.commit()
        cursor.close()
        flash('File updated successfully!', 'success')
    except Exception as e:
        print(f"Error updating file: {e}")
        flash('Could not update file. Please try again.', 'warning')
    return redirect(url_for('viewfile', fid=fid))


# ------------------- MIME TYPES -------------------
MIME_TYPES = {
    'pdf': 'application/pdf',
    'txt': 'text/plain',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'gif': 'image/gif',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
}

# ------------------- VIEW FILE ONLY -------------------
@app.route('/viewfileonly/<fid>')
def viewfileonly(fid):
    if 'suemail' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))

    cursor = mydb.cursor(dictionary=True)
    cursor.execute(
        'SELECT file_name FROM files WHERE f_id=%s AND user_email=%s',
        [fid, session['suemail']]
    )
    file = cursor.fetchone()
    cursor.close()

    if not file:
        flash('File not found.', 'danger')
        return redirect(url_for('viewallfiles'))

    filename = file['file_name']
    ext = filename.split('.')[-1].lower()

    # Inline supported (view in browser)
    if ext in ['pdf', 'txt', 'jpg', 'jpeg', 'png', 'gif']:
        return redirect(url_for('viewfileonly_direct', fid=fid))

    # Office files -> download locally
    elif ext in ['docx', 'pptx', 'xlsx']:
        flash("Preview for this file type is not supported locally. File will be downloaded.", "info")
        return redirect(url_for('download_file', fid=fid))

    # Other -> force download
    else:
        return redirect(url_for('download_file', fid=fid))


# ------------------- SERVE FILE FOR INLINE VIEW -------------------
@app.route('/viewfileonly_direct/<fid>')
def viewfileonly_direct(fid):
    if 'suemail' not in session:
        return "Unauthorized", 403

    cursor = mydb.cursor(dictionary=True)
    cursor.execute(
        'SELECT file_name, file_data FROM files WHERE f_id=%s AND user_email=%s',
        [fid, session['suemail']]
    )
    file = cursor.fetchone()
    cursor.close()

    if not file:
        return "File not found", 404

    ext = file['file_name'].split('.')[-1].lower()
    mimetype = MIME_TYPES.get(ext, 'application/octet-stream')

    return send_file(
        BytesIO(file['file_data']),
        download_name=file['file_name'],
        as_attachment=False,  # open in browser if possible
        mimetype=mimetype
    )

# ------------------- DOWNLOAD FILE ONLY -------------------
@app.route('/download_file/<fid>')
def download_file(fid):
    if not session.get('suemail'):
        flash('Please login to download files.', 'warning')
        return redirect(url_for('login'))
    try:
        cursor = mydb.cursor(dictionary=True)
        cursor.execute(
            'SELECT file_name, file_data FROM files WHERE f_id=%s AND user_email=%s',
            [fid, session['suemail']]
        )
        file = cursor.fetchone()
        cursor.close()
        if file:
            return send_file(
                BytesIO(file['file_data']),
                download_name=file['file_name'],
                as_attachment=True  # force download
            )
        else:
            flash('File not found.', 'danger')
            return redirect(url_for('viewallfiles'))
    except Exception as e:
        print(f"Error downloading file: {e}")
        flash('Could not download file. Please try again.', 'warning')
        return redirect(url_for('dashboard'))


# ------------------- DELETE FILE -------------------
@app.route('/delete_file/<fid>', methods=['POST'])
def delete_file(fid):
    if not session.get('suemail'):
        flash('Please login to delete files.', 'warning')
        return redirect(url_for('login'))
    try:
        cursor = mydb.cursor()
        cursor.execute(
            'DELETE FROM files WHERE f_id=%s AND user_email=%s',
            [fid, session['suemail']]
        )
        cursor.execute(
            'UPDATE users SET updated_at = NOW() WHERE user_email = %s',
            [session['suemail']]
        )
        mydb.commit()
        cursor.close()
        flash('File deleted successfully!', 'danger')
    except Exception as e:
        print(f"Error deleting file: {e}")
        flash('Could not delete file. Please try again.', 'warning')
    return redirect(url_for('viewallfiles'))


# ------------------- LOGOUT -------------------
@app.route('/logout')
def logout():
    if session.get('suemail'):
        session.clear()  # Clears the entire session
        print(session)
        print('User logged out successfully')
        flash('You have been logged out.', 'danger')
        return redirect(url_for('login'))
    else:
        flash('You are not logged in.', 'warning')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)