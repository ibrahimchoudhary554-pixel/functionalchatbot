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
    .stChatFloatingInputContainer { background-color: #1a0000; }
    </style>
    <div class="disclaimer-box">⚠️ ENTERTAINMENT ONLY: No personal malice toward victims from Ibrahim. Just AI jokes.</div>
    """, unsafe_allow_html=True)

# --- 2. GOOGLE SHEETS FUNCTION (Defined Early) ---
def log_to_sheet(user, prompt, response="[AI RATE LIMITED/PENDING]"):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        # Ensure 'GCP_SERVICE_ACCOUNT' is formatted correctly in your Streamlit Secrets
        creds_info = json.loads(st.secrets["GCP_SERVICE_ACCOUNT"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        gc = gspread.authorize(creds)
        
        # Opens the sheet named exactly: RoastBot_Logs
        sheet = gc.open("RoastBot_Logs").sheet1
        sheet.append_row([time.ctime(), user, prompt, response])
        return True
    except Exception as e:
        # This will show in the sidebar if the connection fails
        st.sidebar.error(f"GSheet Connection Error: {e}")
        return False

# --- 3. AUTHENTICATION ---
if 'credentials' not in st.session_state:
    st.session_state['credentials'] = {"usernames": {}}

authenticator = stauth.Authenticate(
    st.session_state['credentials'],
    "roast_cookie_session",
    "signature_key_123",
    cookie_expiry_days=30
)

# Login/Signup Tabs
if not st.session_state.get("authentication_status"):
    tab1, tab2 = st.tabs(["🔒 Log In", "📝 Sign Up"])
    with tab2:
        try:
            if authenticator.register_user(location='main'):
                st.success('Victim registered! You can now Log In.')
        except Exception as e:
            st.error(f"Signup error: {e}")
    with tab1:
        authenticator.login()

# --- 4. MAIN CHAT INTERFACE ---
if st.session_state.get("authentication_status"):
    st.sidebar.title(f"Welcome, {st.session_state['name']}")
    authenticator.logout("Logout", "sidebar")
    
    st.title("🤖 Ibrahim's Savage Bot")
    st.info("If it says 'Rate Limit', wait 60 seconds. Every attempt is logged to the Google Sheet!")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    if prompt := st.chat_input("Enter a name to destroy..."):
        # 1. DISPLAY USER MESSAGE
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 2. IMMEDIATE LOGGING (Records the attempt before AI potentially crashes)
        log_to_sheet(st.session_state["username"], prompt)

        # 3. GENERATE AI ROAST
        with st.chat_message("assistant"):
            # Check for Ibrahim or the Safe List
            is_safe = any(n in prompt.lower() for n in ["ibrahim", "owner", "zainab"])
            system_msg = "You are a polite, professional assistant." if is_safe else "You are a savage, brutal roast bot. Use hilarious adult humor. Roast the person the user mentioned."

            try:
                # Using Qwen2.5 for better stability on free tier
                client = OpenAI(base_url="https://router.huggingface.co/v1", api_key=st.secrets["HF_TOKEN"])
                response = client.chat.completions.create(
                    model="Qwen/Qwen2.5-72B-Instruct",
                    messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": prompt}],
                    max_tokens=350
                )
                answer = response.choices[0].message.content
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
                
                # 4. UPDATE LOG WITH ACTUAL ROAST
                log_to_sheet(st.session_state["username"], prompt, answer)
                
            except Exception as e:
                st.error("⚠️ Hugging Face Rate Limit. Your prompt was saved to the sheet, but the AI is tired. Try again in 1 minute.")

# --- 5. AUTH ERROR HANDLING ---
elif st.session_state.get("authentication_status") is False:
    st.error("Username or password incorrect.")
elif st.session_state.get("authentication_status") is None:
    st.warning("Please Login or Sign Up to access the bot.")
