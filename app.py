from flask import Flask, redirect, url_for, session, render_template, request, flash
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from datetime import datetime
import os
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # only for development
app = Flask(__name__)
app.secret_key = "dev-secret"  # replace with a secure secret in production

GOOGLE_CLIENT_SECRETS_FILE = "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

def credentials_from_session():
    if "credentials" not in session:
        return None
    return Credentials.from_authorized_user_info(session["credentials"], SCOPES)

@app.route("/")
def index():
    creds = credentials_from_session()
    if not creds:
        return redirect(url_for("authorize"))

    service = build("calendar", "v3", credentials=creds)
    # list next 5 upcoming events
    events_result = service.events().list(
        calendarId="primary",
        maxResults=5,
        singleEvents=True,
        orderBy="startTime",
        timeMin=datetime.utcnow().isoformat() + 'Z'  # only events after now
    ).execute()
    events = events_result.get("items", [])

    return render_template("index.html", events=events)

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
    # store credentials in session
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
