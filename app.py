from flask import Flask, redirect, url_for, session, render_template, request, flash
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from datetime import datetime
import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from docx import Document
import re

# Load environment variables
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # only for development
app = Flask(__name__)
app.secret_key = "dev-secret"

GOOGLE_CLIENT_SECRETS_FILE = "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Initialize OpenAI client
openai_client = OpenAI(api_key=openai_api_key)


def credentials_from_session():
    if "credentials" not in session:
        return None
    return Credentials.from_authorized_user_info(session["credentials"], SCOPES)


@app.route("/")
def index():
    return render_template("upload.html")


@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("file")
    if not file or not file.filename.endswith(".docx"):
        flash("Please upload a Word (.docx) syllabus")
        return redirect(url_for("index"))

    # 1️⃣ Extract text from Word file
    doc = Document(file)
    text = "\n".join([p.text for p in doc.paragraphs if p.text.strip() != ""])
    
    print("DEBUG: Word text extracted:")
    print(text[:500])  # first 500 characters

    # 2️⃣ Prepare prompt for OpenAI
    prompt = f"""
Extract all important academic deadlines (assignments, midterms, exams, projects, quizzes) 
from the syllabus below. Assume the year to be 2025. Return them as a JSON array of objects with fields:
- title
- date (YYYY-MM-DD)
- description

Syllabus:
{text}
"""

    # 3️⃣ Call OpenAI GPT API
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an assistant that extracts academic deadlines."},
            {"role": "user", "content": prompt}
        ]
    )

    events_text = response.choices[0].message.content
    print("DEBUG: OpenAI raw output:")
    print(events_text)

    # 4️⃣ Extract JSON from OpenAI output
    try:
        json_match = re.search(r"\[.*\]", events_text, re.DOTALL)
        if json_match:
            events_text = json_match.group()
            events = json.loads(events_text)
        else:
            print("DEBUG: No JSON array found in OpenAI output")
            events = []
    except Exception as e:
        flash("Failed to parse AI response. Check syllabus format.")
        print("Exception while parsing JSON:", e)
        events = []

    # 5️⃣ Store in session and show preview
    session["parsed_events"] = events
    return render_template("preview.html", events=events)


@app.route("/sync", methods=["POST"])
def sync():
    creds = credentials_from_session()
    if not creds:
        return redirect(url_for("authorize"))

    service = build("calendar", "v3", credentials=creds)
    events = session.get("parsed_events", [])

    if not events:
        flash("No events to sync!")
        return redirect(url_for("index"))

    # List all calendars for debug
    calendar_list = service.calendarList().list().execute()
    print("Available calendars for this account:")
    for cal in calendar_list['items']:
        print(f"- {cal['summary']} (ID: {cal['id']})")

    success_count = 0
    failed_events = []

    for e in events:
        # Make sure date is valid
        event_date = e.get("date", "").strip()
        if not event_date:
            print(f"Skipping event with missing date: {e}")
            failed_events.append(e)
            continue

        event_body = {
            "summary": e.get("title", "No Title"),
            "description": e.get("description", ""),
            "start": {"date": event_date},  # all-day event
            "end": {"date": event_date}     # all-day event
        }

        print("Inserting event:")
        print(event_body)

        try:
            service.events().insert(calendarId="primary", body=event_body).execute()
            success_count += 1
        except Exception as err:
            print(f"Error inserting event {e}: {err}")
            failed_events.append(e)

    flash(f"Successfully synced {success_count} events to Google Calendar!")
    if failed_events:
        flash(f"{len(failed_events)} events failed to sync. Check console for details.")

    return redirect(url_for("index"))



@app.route("/authorize")
def authorize():
    flow = Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=url_for("oauth2callback", _external=True)
    )
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    session["state"] = state
    return redirect(authorization_url)


@app.route("/oauth2callback")
def oauth2callback():
    state = session.get("state")
    flow = Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=url_for("oauth2callback", _external=True)
    )
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    session["credentials"] = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes
    }
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)

