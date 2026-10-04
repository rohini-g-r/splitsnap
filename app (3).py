import smtplib
from email.mime.text import MIMEText

import streamlit as st
from google import genai
from google.genai import types

from prompts import SYSTEM_PROMPT, EMAIL_SUMMARY_PROMPT

# ---------- Config ----------
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
GMAIL_ADDRESS = st.secrets["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = st.secrets["GMAIL_APP_PASSWORD"]
MODEL = "gemini-2.5-flash"

st.set_page_config(page_title="SplitSnap", page_icon="🧾")


# ---------- Action tool (Gmail SMTP) ----------
def send_email(to_address, subject, body):
    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = GMAIL_ADDRESS
    message["To"] = to_address

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.send_message(message)


# ---------- Session state ----------
def init_state():
    st.session_state.setdefault("profile", None)
    st.session_state.setdefault("messages", [])  # what we show on screen
    st.session_state.setdefault("history", [])   # what we send to Gemini
    st.session_state.setdefault("last_image_id", None)


def ask(parts):
    """Send a message to Gemini with the full history; return the reply text.

    A fresh client is made for each call and kept alive until the call ends,
    which avoids the 'client has been closed' error on Streamlit reruns.
    """
    if isinstance(parts, str):
        parts = [parts]
    user_parts = [
        types.Part.from_text(text=p) if isinstance(p, str) else p for p in parts
    ]
    user_content = types.Content(role="user", parts=user_parts)

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=MODEL,
        contents=st.session_state.history + [user_content],
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
    )
    reply = response.text or "Sorry, I got an empty reply. Please try again."

    st.session_state.history.append(user_content)
    st.session_state.history.append(
        types.Content(role="model", parts=[types.Part.from_text(text=reply)])
    )
    return reply


init_state()

# ---------- Onboarding (once) ----------
if st.session_state.profile is None:
    st.title("🧾 SplitSnap")
    st.write("Snap a bill, split it in seconds, and get the breakdown by email.")
    with st.form("onboarding"):
        name = st.text_input("Your name")
        email = st.text_input("Email to receive the breakdown")
        people = st.number_input("How many people are splitting?", 1, 30, 2)
        submitted = st.form_submit_button("Start")
    if submitted:
        if not name.strip() or "@" not in email:
            st.error("Please enter your name and a valid email.")
        else:
            st.session_state.profile = {
                "name": name.strip(),
                "email": email.strip(),
                "people": int(people),
            }
            st.rerun()
    st.stop()

profile = st.session_state.profile

# ---------- Sidebar ----------
with st.sidebar:
    st.header(f"Hi, {profile['name']} 👋")
    st.caption(f"Splitting between **{profile['people']}** people")
    st.caption(f"Email: {profile['email']}")
    if st.button("Reset / new bill"):
        st.session_state.messages = []
        st.session_state.history = []
        st.session_state.last_image_id = None
        st.rerun()
    if st.button("Change details"):
        st.session_state.profile = None
        st.rerun()

st.title("🧾 SplitSnap")

# ---------- Photo input ----------
tab_upload, tab_camera = st.tabs(["Upload", "Camera"])
with tab_upload:
    upload = st.file_uploader("Upload a receipt", type=["jpg", "jpeg", "png", "webp"])
with tab_camera:
    camera = st.camera_input("Take a photo of the bill")

image_file = upload or camera
if image_file is not None:
    file_id = f"{image_file.name}-{image_file.size}"
    if file_id != st.session_state.last_image_id:
        st.session_state.last_image_id = file_id
        img_bytes = image_file.getvalue()
        mime = image_file.type or "image/jpeg"
        prompt = (
            f"Here is a bill. There are {profile['people']} people splitting it. "
            "Read it and give me the itemized breakdown and an even split."
        )
        with st.spinner("Reading the bill..."):
            try:
                reply = ask([types.Part.from_bytes(data=img_bytes, mime_type=mime), prompt])
            except Exception as e:
                reply = f"Sorry, I couldn't read that image ({e}). Try another photo."
        st.session_state.messages.append({"role": "user", "content": "📷 *(sent a bill photo)*"})
        st.session_state.messages.append({"role": "assistant", "content": reply})

# ---------- Chat history ----------
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if not st.session_state.messages:
    st.info("Upload or snap a receipt to begin, then chat to adjust the split.")

# ---------- Chat input ----------
if user_text := st.chat_input("e.g. Split by item, I didn't have the drinks"):
    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                reply = ask(user_text)
            except Exception as e:
                reply = f"Something went wrong: {e}"
        st.markdown(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})

# ---------- Send action ----------
if st.session_state.messages:
    st.divider()
    if st.button("📧 Send breakdown to my email", type="primary"):
        with st.spinner("Preparing and sending..."):
            try:
                summary = ask(EMAIL_SUMMARY_PROMPT.format(name=profile["name"]))
                send_email(profile["email"], "Your bill breakdown 🧾", summary)
                st.success(f"Sent to {profile['email']}!")
                with st.expander("What was sent"):
                    st.text(summary)
            except smtplib.SMTPAuthenticationError:
                st.error("Gmail login failed. Check your App Password in secrets.")
            except Exception as e:
                st.error(f"Could not send email: {e}")
