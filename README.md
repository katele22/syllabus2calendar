# SyllabusToCalendar

A Flask web app that automates adding important academic deadlines from a `.docx` syllabus to your Google Calendar.

---

## Features

- Upload a `.docx` syllabus file.
- Extract assignments, quizzes, exams, and project deadlines using OpenAI GPT.
- Sync extracted events to Google Calendar with one click.
- Preview all extracted events before syncing.

---

## Technologies Used

- Python 3
- Flask
- Google Calendar API
- OpenAI API
- python-docx
- dotenv

---

## Installation

1. Clone the repository:

```bash
git clone https://github.com/katele22/syllabus2calendar.git
cd syllabus2calendar
```
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a .env file with your OpenAI API key:
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

4. Download your credentials.json from Google Cloud Console and place it in the project root.

## Usage

1. Run the Flask app:
```bash
python app.py
```

2. Open your browser at http://localhost:5000

3. Upload a syllabus .docx file.

4. Preview the extracted events.

5. Click Sync to Google Calendar to add events automatically.


## Notes

Make sure you authorize the app with your Google account.

Only .docx files are supported.

Events are added as all-day events in Google Calendar.
