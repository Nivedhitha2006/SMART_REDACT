🔒 Smart Redaction Tool (Flask-Based)

A powerful AI-powered redaction system that detects and hides sensitive information from text and documents automatically to ensure privacy and security.

🚀 Features

✅ Text Redaction

Detects sensitive data like:
Names
Phone numbers
Emails

✅ Document Redaction

Upload documents (TXT / PDF supported)
Automatically detects:
Name
Email
Phone number

✅ File Download

Download redacted files instantly after processing

✅ Logging System

Stores redaction history in SQLite database

🖼️ Screenshots

🏠 Homepage

📝 Text Redaction

📄 Document Redaction

⬇️ Download Redacted File

🏗️ Project Structure

REDACTION_TOOL/
│
├── static/
│   ├── app.js
│   └── style.css
│
├── templates/
│   └── index.html
│
├── app.py                # Main Flask App
├── database.py           # Database handling
├── file_parser.py        # File reading logic
├── redactor.py           # Core redaction logic
├── redaction_log.db      # SQLite database
├── requirements.txt
└── .gitignore

⚙️ Technologies Used
Frontend: HTML, CSS, JavaScript
Backend: Python (Flask)
Database: SQLite
Processing: Regex-based detection

🧠 How It Works
User enters text or uploads document
Flask backend receives data
redactor.py processes sensitive info
Data is masked securely
Output is displayed or downloadable
Activity logged in database

💻 Installation (Local Setup)
Step 1: Clone Repository
git clone https://github.com/your-username/redaction-tool.git
cd redaction-tool
Step 2: Create Virtual Environment
python -m venv venv
Step 3: Activate Environment
venv\Scripts\activate   # Windows
source venv/bin/activate  # Mac/Linux
Step 4: Install Requirements
pip install -r requirements.txt
Step 5: Run Application
python app.py
Step 6: Open in Browser
http://127.0.0.1:5000



📜 License

MIT License

👩‍💻 Author

Nivedhitha K






