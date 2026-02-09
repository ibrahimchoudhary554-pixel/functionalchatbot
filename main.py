import streamlit as st
import streamlit_authenticator as stauth
from openai import OpenAI
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json

# --- 1. UI & WATERMARK SETTINGS ---
st.set_page_config(page_title="Ibrahim's Roast Dungeon", page_icon="🔥", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #ff4b4b; }
    .watermark { position: fixed; opacity: 0.4; color: white; font-size: 14px; z-index: 99; }
    .top-r { top: 10px; right: 10px; }
    .bot-r { bottom: 10px; right: 10px; }
    .disclaimer-box { border: 1px dashed #ffffff; padding: 10px; background-color: #330000; color: white; text-align: center; margin-bottom: 20px;}
    </style>
    <div class="watermark top-r">@ibrahimchoudhary__</div>
    <div class="watermark bot-r">@ibrahimchoudhary__</div>
    <div class="disclaimer-box">⚠️ ENTERTAINMENT ONLY: Nothing personal to victims from Ibrahim.</div>
    """, unsafe_allow_html=True)

# --- 2. AUTHENTICATION CONFIG ---
# Add your users here. Password should ideally be hashed, but these are plain for your setup.
auth_config = {
    "credentials": {
        "usernames": {
            "ibrahim": {"name": "Ibrahim", "password": "yourpassword123"},
            "guest": {"name": "Guest Victim", "password": "roastme"}
        }
    },
    "cookie": {"expiry_days": 30, "key": "roast_signature", "name": "roast_cookie"}
}

authenticator = stauth.Authenticate(
    auth_config['credentials'],
    auth_config['cookie']['name'],
    auth_config['cookie']['key'],
    auth_config['cookie']['expiry_days']
)

# FIX: Using the correct 2026 login call to avoid the Location ValueError
authenticator.login()

if st.session_state["authentication_status"]:
    with st.sidebar:
        st.title(f"Welcome, {st.session_state['name']}")
        authenticator.logout("Logout")
        st.markdown("---")
        st.markdown("**Model Switcher (Anti-Crash)**")
        model_choice = st.selectbox("Select Model:", ["mistralai/Mistral-7B-Instruct-v0.3", "meta-llama/Llama-3.1-8B-Instruct"])

    # --- 3. GOOGLE SHEETS LOGGING FUNCTION ---
    def log_to_sheet(user, prompt, response):
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds_dict = json.loads(st.secrets["GCP_SERVICE_ACCOUNT"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            gc = gspread.authorize(creds)
            # Make sure your Google Sheet is named exactly "RoastBot_Logs"
            sheet = gc.open("RoastBot_Logs").sheet1
            sheet.append_row([user, prompt, response])
        except Exception as e:
            st.sidebar.error(f"Sheet Log Error: {e}")

    # --- 4. CHAT LOGIC ---
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    if prompt := st.chat_input("Enter a name to destroy..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            
            # Safe List Check
            is_safe = any(name in prompt.lower() for name in ["ibrahim", "zainab", "owner"])
            
            system_prompt = "You are a loyal assistant. Be nice." if is_safe else "You are a savage roast bot. Use adult humor and caps. Roast them hard."

            try:
                client = OpenAI(base_url="https://router.huggingface.co/v1", api_key=st.secrets["HF_TOKEN"])
                response = client.chat.completions.create(
                    model=model_choice,
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
                    max_tokens=400
                )
                answer = response.choices[0].message.content
                response_placeholder.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
                
                # Log to Google Sheets
                log_to_sheet(st.session_state["username"], prompt, answer)
                
            except Exception as e:
                st.error("Rate limit hit! Switch models or wait a bit.")

elif st.session_state["authentication_status"] is False:
    st.error("Username/password is incorrect")
elif st.session_state["authentication_status"] is None:
    st.warning("Please login to access the Dungeon.")
