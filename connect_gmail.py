"""Run locally on the same computer as your browser. No mail sending scope."""
import os
from dotenv import load_dotenv
load_dotenv()
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from app.mail import SCOPES
from app.store import secret_set
flow=InstalledAppFlow.from_client_secrets_file(os.getenv('GOOGLE_CLIENT_FILE','credentials.json'),SCOPES)
creds=flow.run_local_server(port=0,access_type='offline',prompt='consent')
email=build('gmail','v1',credentials=creds).users().getProfile(userId='me').execute()['emailAddress'].lower()
secret_set('gmail:'+email,creds.to_json())
print('Connected read-only Gmail:',email)
