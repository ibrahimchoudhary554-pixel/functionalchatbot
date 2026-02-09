import streamlit as st
import streamlit_authenticator as stauth
from openai import OpenAI
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import time

# --- 1. PAGE CONFIG & STYLING ---
st.set_page_config(page_title="Ibrahim's Roast Dungeon", page_icon="🔥", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #ff4b4b; }
    .disclaimer-box { border: 2px dashed #ffffff; padding: 15px; background-color: #330000; color: white; text-align: center; margin-bottom: 20px;}
    </style>
    <div class="disclaimer-box">⚠️ IBRAHIM'S ROAST DUNGEON: Just jokes, don't cry about it.</div>
    """, unsafe_allow_html=True)

# --- 2. AUTHENTICATION (Initialization) ---
# We use session state so users added via Signup are remembered during the session
if 'credentials' not in st.session_state:
    st.session_state['credentials'] = {"usernames": {}}

authenticator = stauth.Authenticate(
    st.session_state['credentials'],
    "roast_cookie",
    "signature_key",
    cookie_expiry_days=30
)

# --- 3. LOGIN & SIGNUP UI ---
if not st.session_state.get("authentication_status"):
    tab1, tab2 = st.tabs(["Log In", "Sign Up"])
    with tab2:
        try:
            # register_user handles the signup form automatically
            if authenticator.register_user(location='main'):
                st.success('Victim registered! Now go to the Log In tab.')
        except Exception as e:
            st.error(f"Signup error: {e}")
    with tab1:
        authenticator.login()

# --- 4. MAIN APP LOGIC (Only runs if logged in) ---
if st.session_state.get("authentication_status"):
    authenticator.logout("Logout", "sidebar")
    st.sidebar.title(f"Welcome, {st.session_state['name']}")
    
    # Model Selection to help with Rate Limits
    model_choice = st.sidebar.selectbox("Choose AI Model:", ["Qwen/Qwen2.5-72B-Instruct", "mistralai/Mistral-7B-Instruct-v0.3"])

    # Google Sheets Logging Function
    def log_to_sheet(user, prompt, response):
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds_info = json.loads(st.secrets["GCP_SERVICE_ACCOUNT"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
            gc = gspread.authorize(creds)
            # Make sure your GSheet is named "RoastBot_Logs"
            sheet = gc.open("RoastBot_Logs").sheet1
            sheet.append_row([time.ctime(), user, prompt, response])
        except Exception as e:
            st.sidebar.warning(f"GSheet Log Failed: {e}")

    # Chat Interface
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    if prompt := st.chat_input("Enter a name to roast..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            # Safe list check for the boss
            is_safe = any(n in prompt.lower() for n in ["ibrahim", "owner", "zainab"])
            system_msg = "You are a humble servant. Be very polite." if is_safe else "You are a brutal roast bot. Use adult humor and roast them into the ground."

            try:
                client = OpenAI(base_url="https://router.huggingface.co/v1", api_key=st.secrets["HF_TOKEN"])
                response = client.chat.completions.create(
                    model=model_choice,
                    messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": prompt}]
                )
                answer = response.choices[0].message.content
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
                
                # SAVE TO SHEET
                log_to_sheet(st.session_state["username"], prompt, answer)
                
            except Exception as e:
                st.error("Rate limit! Switch models in the sidebar or wait a minute.")

# --- 5. ERROR HANDLING (Must be at the same level as the 'if' above) ---
elif st.session_state.get("authentication_status") is False:
    st.error("Username/password is incorrect")
elif st.session_state.get("authentication_status") is None:
    st.warning("Please Login or Sign Up to enter the Dungeon.")
