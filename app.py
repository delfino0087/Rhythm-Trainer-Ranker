from flask import Flask, render_template, Response, session, request, redirect, url_for
from flask_login import LoginManager, login_required, login_user, logout_user
import io
import csv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import imaplib
import email
import re
from functools import wraps

app = Flask(__name__)
app.secret_key = 'una_chiave_segreta_molto_lunga_e_complessa'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User:
    def __init__(self, username):
        self.username = username
    
    def is_authenticated(self):
        return True
    
    def is_active(self):
        return True
    
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return self.username

@login_manager.user_loader
def load_user(username):
    return User(username)
app.secret_key = 'una_chiave_segreta_molto_lunga_e_complessa'  # Cambia questa con una chiave sicura

def connect_to_email(username, password):
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(username, password)
    mail.select("inbox")
    return mail

def fetch_emails(mail):
    status, messages = mail.search(None, 'SUBJECT "Rhythm Trainer"')
    emails = messages[0].split()
    return emails

def parse_email(mail, email_id):
    status, msg_data = mail.fetch(email_id, "(RFC822)")
    raw_email = msg_data[0][1]
    msg = email.message_from_bytes(raw_email)  # Usa `message_from_bytes` per gestire byte direttamente

    for part in msg.walk():
        content_type = part.get_content_type()
        content_disposition = str(part.get("Content-Disposition"))

        if content_type == "text/plain" and "attachment" not in content_disposition:
            charset = part.get_content_charset() or 'utf-8'  # Imposta charset predefinito se None
            body = part.get_payload(decode=True).decode(charset, errors='replace')  # Gestione errori e charset
            return body

    # Se non trovata la parte in testo semplice, cerca in altre parti
    body = msg.get_payload(decode=True)
    charset = msg.get_content_charset() or 'utf-8'  # Imposta charset predefinito se None
    return body.decode(charset, errors='replace')

def extract_data(body):
    name = re.search(r"Submitted honestly by: (.+)", body).group(1)
    email_address = re.search(r"From Email: (.+)", body).group(1)
    score = re.search(r"Score: (\d+) correct out of (\d+) attempted", body)
    correct = int(score.group(1))
    attempted = int(score.group(2))
    percentage = int(re.search(r"Percentage: (\d+)%", body).group(1))
    date_time = re.search(r"Date and Time Submitted: (.+)", body).group(1)
    decimal_score = (percentage / 100) * 10
    return {
        "Name": name,
        "Email": email_address,
        "Correct": correct,
        "Attempted": attempted,
        "Percentage": percentage,
        "Date and Time": date_time,
        "Decimal Score": round(decimal_score, 2)
    }

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    try:
        username = session['username']
        password = session['password']

        mail = connect_to_email(username, password)
        emails = fetch_emails(mail)

        results = []

        for email_id in emails:
            try:
                body = parse_email(mail, email_id)
                data = extract_data(body)
                results.append(data)
            except Exception as e:
                app.logger.error(f"Errore nell'elaborazione dell'email {email_id}: {str(e)}")

        return render_template('index.html', results=results)
    except Exception as e:
        app.logger.error(f"Errore generale: {str(e)}")
        return render_template('error.html', error=str(e)), 500

@app.route('/download_csv')
def download_csv():
    username = "rhythmtrainerranker@gmail.com"  # Inserisci la tua email
    password = "rfmw jvkq ojuq oatp"  # Inserisci la password per l'app

    mail = connect_to_email(username, password)
    emails = fetch_emails(mail)

    results = []

    for email_id in emails:
        body = parse_email(mail, email_id)
        data = extract_data(body)
        results.append(data)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)
    output.seek(0)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=student_results.csv"}
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            connect_to_email(username, password)
            user = User(username)
            login_user(user)
            session['username'] = username
            session['password'] = password
            return redirect(url_for('index'))
        except:
            return render_template('login.html', error='Credenziali non valide')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('username', None)
    session.pop('password', None)
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, debug=True)