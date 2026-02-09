import streamlit as st
import streamlit_authenticator as stauth
from openai import OpenAI
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json

# --- 1. UI & WATERMARK SETTINGS ---
st.set_page_config(page_title="Ibrahim's Roast Dungeon", page_icon="🔥", layout="wide")

# (CSS kept from previous version for watermarks and disclaimer)
st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #ff4b4b; }
    .watermark { position: fixed; opacity: 0.4; color: white; font-size: 14px; z-index: 99; }
    .top-r { top: 10px; right: 10px; }
    .bot-r { bottom: 10px; right: 10px; }
    .disclaimer-box { border: 1px dashed #ffffff; padding: 10px; background-color: #330000; color: white; text-align: center; }
    </style>
    <div class="watermark top-r">@ibrahimchoudhary__</div>
    <div class="watermark bot-r">@ibrahimchoudhary__</div>
    <div class="disclaimer-box">⚠️ ENTERTAINMENT ONLY: Nothing personal to victims from Ibrahim.</div>
    """, unsafe_allow_html=True)

# --- 2. AUTHENTICATION ---
# In a real app, you'd store these hashes in secrets
names = ["Ibrahim", "User1"]
usernames = ["ibrahim", "guest"]
passwords = ["admin123", "roastme"] # Use hashed passwords for real production!

authenticator = stauth.Authenticate(
    {"usernames": {un: {"name": n, "password": p} for un, n, p in zip(usernames, names, passwords)}},
    "roast_cookie", "signature_key", cookie_expiry_days=30
)

name, authentication_status, username = authenticator.login("Login", "main")

if authentication_status:
    authenticator.logout("Logout", "sidebar")
    st.write(f"Welcome back, **{name}**")

    # --- 3. GOOGLE SHEETS LOGGING FUNCTION ---
    def log_to_sheet(user, prompt, response):
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            # Get credentials from Streamlit secrets (paste JSON content there)
            creds_dict = json.loads(st.secrets["GCP_SERVICE_ACCOUNT"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client_gs = gspread.authorize(creds)
            sheet = client_gs.open("RoastBot_Logs").sheet1
            sheet.append_row([user, prompt, response])
        except Exception as e:
            st.error(f"Logging failed: {e}")

    # --- 4. CHAT BOT LOGIC ---
    SAFE_NAMES = ["ibrahim", "owner", "zainab"]
    
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
            # System Persona Logic
            is_safe = any(n in prompt.lower() for n in SAFE_NAMES)
            persona = "Loyal Butler" if is_safe else "Savage Roast Bot"
            
            try:
                client = OpenAI(base_url="https://router.huggingface.co/v1", api_key=st.secrets["HF_TOKEN"])
                response = client.chat.completions.create(
                    model="meta-llama/Llama-3.1-8B-Instruct",
                    messages=[{"role": "system", "content": f"Persona: {persona}"}, {"role": "user", "content": prompt}]
                )
                answer = response.choices[0].message.content
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
                
                # SAVE TO GOOGLE SHEETS
                log_to_sheet(username, prompt, answer)
                
            except Exception as e:
                st.error("Overload! Wait 5 mins.")

elif authentication_status is False:
    st.error("Username/password is incorrect")
elif authentication_status is None:
    st.warning("Please enter your username and password")