import streamlit as st
import streamlit_authenticator as stauth
from openai import OpenAI
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import time

# --- 1. UI & STYLING ---
st.set_page_config(page_title="Ibrahim's Roast Dungeon", page_icon="🔥", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #ff4b4b; }
    .disclaimer-box { border: 2px dashed #ffffff; padding: 15px; background-color: #330000; color: white; text-align: center; margin-bottom: 20px;}
    </style>
    <div class="disclaimer-box">⚠️ ENTERTAINMENT ONLY: No personal malice toward victims. It's just AI humor.</div>
    """, unsafe_allow_html=True)

# --- 2. AUTHENTICATION (Signup & Login) ---
if 'credentials' not in st.session_state:
    st.session_state['credentials'] = {"usernames": {}}

authenticator = stauth.Authenticate(
    st.session_state['credentials'],
    "roast_session",
    "signature_key",
    cookie_expiry_days=30
)

# Show Signup if not logged in
if not st.session_state.get("authentication_status"):
    tab1, tab2 = st.tabs(["Login", "Sign Up (New Victims)"])
    with tab2:
        try:
            if authenticator.register_user(location='main'):
                st.success('Registration successful! Switch to Login tab.')
        except Exception as e:
            st.error(f"Signup error: {e}")
    with tab1:
        authenticator.login()
else:
    # --- 3. THE MAIN APP (LOGGED IN) ---
    authenticator.logout("Logout", "sidebar")
    st.title(f"🔥 Welcome to the Dungeon, {st.session_state['name']}")

    # --- GOOGLE SHEETS LOGGING ---
    def log_to_sheet(user, prompt, response):
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds_info = json.loads(st.secrets["GCP_SERVICE_ACCOUNT"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
            gc = gspread.authorize(creds)
            
            # Use the EXACT name of your Google Sheet
            sheet = gc.open("RoastBot_Logs").sheet1
            sheet.append_row([time.ctime(), user, prompt, response])
            st.toast("✅ Roasted data saved to Google Sheets!")
        except Exception as e:
            st.sidebar.error(f"GSheet Error: {e}")

    # --- CHAT INTERFACE ---
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    if prompt := st.chat_input("Name a victim..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            # SAFE LIST PROTECTION
            is_safe = any(n in prompt.lower() for n in ["ibrahim", "owner", "zainab"])
            system_msg = "You are a loyal slave. Be nice." if is_safe else "You are a brutal roast bot. Be savage."

            try:
                # CHANGED MODEL TO BYPASS RATE LIMITS
                client = OpenAI(base_url="https://router.huggingface.co/v1", api_key=st.secrets["HF_TOKEN"])
                response = client.chat.completions.create(
                    model="Qwen/Qwen2.5-72B-Instruct", 
                    messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": prompt}],
                    max_tokens=300
                )
                answer = response.choices[0].message.content
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
                
                # EXECUTE LOGGING
                log_to_sheet(st.session_state["username"], prompt, answer)

            except Exception as e:
                st.error(f"Rate Limit or API Error. Try again in 60s. Details: {e}")

# --- FALLBACKS ---
elif st.session_state["authentication_status"] is False:
    st.error("Username/password is incorrect")
