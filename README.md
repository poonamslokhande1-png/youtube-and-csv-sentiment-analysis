# YouTube & CSV Sentiment Analysis (Flask App)

This is a Flask-based web application that performs sentiment analysis on
YouTube comments or any text data provided via a CSV file.

The application classifies comments into:
- Positive
- Negative
- Neutral

and shows a summary along with downloadable CSV files for each sentiment.

---

## 🚀 Features

- Upload CSV file containing comments
- Sentiment analysis using TextBlob
- Displays total, positive, negative, and neutral 
- Download filtered CSV files 
- Simple and user-friendly web interface

---

## 🛠️ Technologies Used

- Python
- Flask
- TextBlob
- HTML, CSS, Bootstrap
- Pandas

---
## 📂 Project Structure

youtube-and-csv-sentiment-analysis/
│
├── app.py
├── templates/
│ ├── index.html
│ └── result.html
├── static/
│ └── css/
├── uploads/
├── requirements.txt
└── README.md


---

## ⚙️ Installation & Setup

### 1️⃣ Clone the repository
```bash
git clone https://github.com/poonamslokhande1-png/youtube-and-csv-sentiment-analysis.git
cd youtube-and-csv-sentiment-analysis
###create virtual envirment
python -m venv SAU
.\SAU\Scripts\activate

pip install -r requirements.txt
python app.py
http://127.0.0.1:5000


## 📂 Project Structure

