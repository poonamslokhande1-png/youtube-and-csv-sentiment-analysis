import re
import os
import uuid
import pandas as pd

from flask import Flask, render_template, request, send_file
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from langdetect import detect
from googletrans import Translator
from googleapiclient.discovery import build

# ---------------- APP CONFIG ----------------
app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- TOOLS ----------------
analyzer = SentimentIntensityAnalyzer()
translator = Translator()

# ---------------- YOUTUBE API KEY ----------------
YOUTUBE_API_KEY = "AIzaSyBMlxfWR4gb7FQGdmKLhy6FxCxYMItDwQI"


# ---------------- HELPERS ----------------
def extract_video_id(url):
    pattern = r"(?:v=|youtu\.be/|shorts/|embed/)([0-9A-Za-z_-]{11})"
    m = re.search(pattern, url)
    return m.group(1) if m else None


def translate_to_english(text):
    try:
        if detect(text) != "en":
            return translator.translate(text, dest="en").text
        return text
    except:
        return text


def get_sentiment(text):
    text = translate_to_english(str(text))
    score = analyzer.polarity_scores(text)["compound"]
    if score >= 0.05:
        return "Positive"
    elif score <= -0.05:
        return "Negative"
    else:
        return "Neutral"

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return render_template("index.html")


# ---------------- CSV SENTIMENT ----------------
@app.route("/predict", methods=["POST"])
def predict_csv():
    file = request.files.get("csvfile")
    if not file:
        return "Invalid CSV"

    df = pd.read_csv(file)
    text_col = df.columns[0]

    df["sentiment"] = df[text_col].astype(str).apply(get_sentiment)

    pos = int((df["sentiment"] == "Positive").sum())
    neg = int((df["sentiment"] == "Negative").sum())
    neu = int((df["sentiment"] == "Neutral").sum())

    key = str(uuid.uuid4())
    df.to_csv(f"{UPLOAD_FOLDER}/{key}.csv", index=False)

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
    video_url = request.form.get("youtube_url")
    video_id = extract_video_id(video_url)
    if not video_id:
        return "Invalid YouTube URL"

    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    response = youtube.commentThreads().list(
        part="snippet",
        videoId=video_id,
        maxResults=100,
        textFormat="plainText"
    ).execute()

    rows = []
    pos = neg = neu = 0

    for item in response.get("items", []):
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

    pos, neg, neu = int(pos), int(neg), int(neu)

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
@app.route("/download/<key>")
def download(key):
    return send_file(f"{UPLOAD_FOLDER}/{key}.csv", as_attachment=True)


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
