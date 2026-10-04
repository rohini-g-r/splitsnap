# SplitSnap – Receipt & Bill Splitter Chatbot

Gemini vision + chat, with Gmail SMTP as the action tool.

## Run
1. `pip install -r requirements.txt`
2. Get a Gemini key at https://aistudio.google.com/apikey
3. On the sending Gmail: enable 2-Step Verification, then create an App Password at myaccount.google.com/apppasswords
4. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill it in
5. `streamlit run app.py`

## Flow
Onboard (name, email, # people) -> upload/snap bill -> chat to adjust split -> "Send breakdown" emails it.

## Deploy
Push to GitHub, deploy on Streamlit Community Cloud, paste the three secrets in the app's Secrets settings.
