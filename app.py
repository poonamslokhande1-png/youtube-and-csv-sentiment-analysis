import os#create folders, manage file paths.
import re#helps to search patterns inside text (to extract YouTube video ID).
import uuid#give unique download csv file names.
import pandas as pd
import emoji
from emot.emo_unicode import EMOTICONS_EMO
#Flask → creates the application

#render_template → shows HTML pages

#request → receives form input

#redirect + url_for → navigation between routes

#session → stores logged-in user

#send_file → download CSV

#flash → display messagess
from flask import (
    Flask, render_template, request,
    redirect, url_for, session,
    send_file, flash
)
#Connects Flask with SQLite database using ORM model.

from flask_sqlalchemy import SQLAlchemy
#Never store plain password — convert to HASH and verify during login.
from werkzeug.security import generate_password_hash, check_password_hash
#Sentiment engine that returns polarity scores.
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
#Detects language of input text.
from langdetect import detect
#Translates non-English text to English.
from googletrans import Translator
#Builds YouTube service object to extract comments
from googleapiclient.discovery import build

# ---------------- APP CONFIG ----------------
#Creates Flask application instance
app = Flask(__name__)
#Required for session management.
app.secret_key = "sentiment_secret_key"
#Defines SQLite database file → users.db.
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
#disables unnecessary tracking.
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
#Create folder “uploads” if not exists.
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- NLP TOOLS ----------------
#Vader sentiment object
analyzer = SentimentIntensityAnalyzer()
translator = Translator(service_urls=["translate.googleapis.com"])

#YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
# ---------------- YOUTUBE API KEY ----------------
YOUTUBE_API_KEY = "AIzaSyBMlxfWR4gb7FQGdmKLhy6FxCxYMItDwQI"


# ---------------- DATABASE MODEL ----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# ---------------- HELPERS ----------------
def extract_video_id(url):
    pattern = r"(?:v=|youtu\.be/|shorts/|embed/)([0-9A-Za-z_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None
def emoji_to_text(text):
    """
    Converts emojis and emoticons to meaningful words
    😊 -> happy
    😡 -> angry
    🔥 -> fire
    """
#Convert Unicode emoji to words.
    text = emoji.demojize(text, delimiters=(" ", " "))

    # Replace text emoticons.
    for emot, meaning in EMOTICONS_EMO.items():
        text = text.replace(emot, " " + meaning + " ")

    return text

TEXT_EXPANSION = {
    "u": "you",
    "ur": "your",
    "r": "are",
    "gr8": "great",
    "gud": "good",
    "nyc": "nice",
    "lol": "laughing",
    "omg": "oh my god",
    "wtf": "what the hell",
    "idk": "i do not know",
    "imo": "in my opinion",

    # Hinglish / Marathi slang
    "mast": "very good",
    "kadak": "excellent",
    "bakwas": "very bad",
    "faltu": "useless",
    "bekar": "bad",
    "jhakkas": "excellent",
    "kharab": "bad"
}
def expand_text(text):
    words = text.split()
    expanded_words = []

    for word in words:
        key = word.lower()
        if key in TEXT_EXPANSION:
            expanded_words.append(TEXT_EXPANSION[key])
        else:
            expanded_words.append(word)

    return " ".join(expanded_words)#rebuild sentences

def translate_to_english(text):
    try:
        if detect(text) != "en":#If not English.
            return translator.translate(text, dest="en").text
        return text
    except:
        return text


def get_sentiment(text):
    text = str(text)

    # 1️⃣ Emoji mapping
    text = emoji_to_text(text)

    # 2️⃣ Text expansion
    text = expand_text(text)

    # 3️⃣ Translate to English
    text = translate_to_english(text)

    # 4️⃣ Sentiment
    score = analyzer.polarity_scores(text)["compound"]#Vader compound score.
#Classification.
    if score >= 0.05:
        return "Positive"
    elif score <= -0.05:
        return "Negative"
    else:
        return "Neutral"

# ---------------- BASIC PAGES ----------------
@app.route("/")
def home():
    return render_template("home.html")


@app.route("/about")
def about():
    return render_template("about.html")

# ---------------- REGISTER ----------------
from werkzeug.security import generate_password_hash
from flask import flash, redirect, url_for

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        #  form validation
        if not username or not email or not password:
            flash("All fields are required")
            return redirect(url_for("register"))

        #  email already exists check
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered. Please login.")
            return redirect(url_for("login"))

        #  new user create
        hashed_password = generate_password_hash(password)
        new_user = User(
            username=username,
            email=email,
            password=hashed_password
        )
#Save user
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful. Please login.")
        return redirect(url_for("login"))

    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session["user"] = user.username
            return redirect(url_for("index"))

        flash("Invalid email or password")

    return render_template("login.html")

# ---------------- LOGOUT ----------------
#Remove session.
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully")
    return redirect(url_for("home"))


# ---------------- DASHBOARD ----------------
@app.route("/index")
def index():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("index.html")

# ---------------- CSV SENTIMENT ----------------
@app.route("/predict", methods=["POST"])
def predict_csv():
    file = request.files.get("csvfile")

    if not file or not file.filename.endswith(".csv"):
        flash("Only CSV files allowed")
        return redirect(url_for("index"))

    df = pd.read_csv(file)
    #Find text column.
    text_col = df.select_dtypes(include=["object"]).columns[0]
#Apply function.
    df["sentiment"] = df[text_col].astype(str).apply(get_sentiment)
#Count.
    pos = int((df["sentiment"] == "Positive").sum())
    neg = int((df["sentiment"] == "Negative").sum())
    neu = int((df["sentiment"] == "Neutral").sum())

    key = str(uuid.uuid4())#Save result.
    df.to_csv(
        f"{UPLOAD_FOLDER}/{key}.csv",
        index=False,
        encoding="utf-8-sig"
    )

    return render_template(
        "result.html",
        mode="csv",
        total=len(df),
        pos=pos,
        neg=neg,
        neu=neu,
        download_key=key
    )

# ---------------- YOUTUBE SENTIMENT ----------------
@app.route("/youtube", methods=["POST"])
def youtube_comments():
    video_url = request.form["youtube_url"]
    video_id = extract_video_id(video_url)

    if not video_id:
        flash("Invalid YouTube URL")
        return redirect(url_for("index"))

    youtube = build(
        "youtube", "v3",
        developerKey=YOUTUBE_API_KEY
    )

    rows = []
    pos = neg = neu = 0
    next_page = None

    while True:
        response = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=100,
            pageToken=next_page,
            textFormat="plainText"
        ).execute()

        for item in response["items"]:
            comment = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
            sentiment = get_sentiment(comment)

            if sentiment == "Positive":
                pos += 1
            elif sentiment == "Negative":
                neg += 1
            else:
                neu += 1

            rows.append({
                "comment": comment,
                "sentiment": sentiment
            })

        next_page = response.get("nextPageToken")
        if not next_page:
            break

    df = pd.DataFrame(rows)
    key = str(uuid.uuid4())
    df.to_csv(
        f"{UPLOAD_FOLDER}/{key}.csv",
        index=False,
        encoding="utf-8-sig"
    )

    return render_template(
        "result.html",
        mode="youtube",
        total=len(rows),
        pos=pos,
        neg=neg,
        neu=neu,
        download_key=key
    )

# ---------------- DOWNLOAD ----------------


@app.route("/download/all/<key>")
def download_all(key):
    return send_file(f"uploads/{key}.csv", as_attachment=True)


@app.route("/download/positive/<key>")
def download_positive(key):
    df = pd.read_csv(f"uploads/{key}.csv")
    df[df["sentiment"] == "Positive"].to_csv(
        f"uploads/{key}_positive.csv", index=False
    )
    return send_file(f"uploads/{key}_positive.csv", as_attachment=True)


@app.route("/download/negative/<key>")
def download_negative(key):
    df = pd.read_csv(f"uploads/{key}.csv")
    df[df["sentiment"] == "Negative"].to_csv(
        f"uploads/{key}_negative.csv", index=False
    )
    return send_file(f"uploads/{key}_negative.csv", as_attachment=True)


@app.route("/download/neutral/<key>")
def download_neutral(key):
    df = pd.read_csv(f"uploads/{key}.csv")
    df[df["sentiment"] == "Neutral"].to_csv(
        f"uploads/{key}_neutral.csv", index=False
    )
    return send_file(f"uploads/{key}_neutral.csv", as_attachment=True)


# ---------------- RUN APP ----------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
