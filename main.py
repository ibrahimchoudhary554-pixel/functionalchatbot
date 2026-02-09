import streamlit as st
import streamlit_authenticator as stauth
from openai import OpenAI
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# --- 1. PAGE CONFIG & UI ---
st.set_page_config(page_title="Ibrahim's Roast Dungeon", page_icon="🔥", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #ff4b4b; }
    .disclaimer-box { border: 1px dashed #ffffff; padding: 10px; background-color: #330000; color: white; text-align: center; margin-bottom: 20px;}
    </style>
    <div class="disclaimer-box">⚠️ ENTERTAINMENT ONLY: No personal malice toward victims from Ibrahim.</div>
    """, unsafe_allow_html=True)

# --- 2. AUTHENTICATION LOGIC ---
# We initialize the credentials in session state so they persist during signup
if 'credentials' not in st.session_state:
    st.session_state['credentials'] = {
        "usernames": {
            "ibrahim": {"name": "Ibrahim", "password": "yourpassword123", "email": "ibrahim@example.com"}
        }
    }

authenticator = stauth.Authenticate(
    st.session_state['credentials'],
    "roast_cookie",
    "signature_key",
    cookie_expiry_days=30
)

# --- SIGNUP LOGIC ---
# We place this in a sidebar or an expander so it doesn't clutter the login
with st.sidebar:
    if not st.session_state.get("authentication_status"):
        try:
            if authenticator.register_user(location='main'):
                st.success('User registered successfully! You can now login.')
        except Exception as e:
            st.error(e)

# --- LOGIN LOGIC ---
authenticator.login()

if st.session_state["authentication_status"]:
    authenticator.logout("Logout", "sidebar")
    st.write(f"Welcome back, **{st.session_state['name']}**")

    # --- 3. GOOGLE SHEETS LOGGING ---
    def log_to_sheet(user, prompt, response):
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            # Loads from your Secret Box
            creds_dict = json.loads(st.secrets["GCP_SERVICE_ACCOUNT"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            gc = gspread.authorize(creds)
            # Ensure your sheet is shared with the client_email in your JSON
            sheet = gc.open("RoastBot_Logs").sheet1
            sheet.append_row([user, prompt, response])
        except Exception as e:
            st.error(f"GSheet Error: {e}. Did you share the sheet with the Service Account email?")

    # --- 4. THE ROAST ENGINE ---
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    if prompt := st.chat_input("Enter a name..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            # Check if user is being nice to Ibrahim
            is_safe = any(name in prompt.lower() for name in ["ibrahim", "owner", "zainab"])
            persona = "You are a loyal bodyguard. Be polite." if is_safe else "You are a savage roast bot. Use adult humor."

            try:
                client = OpenAI(base_url="https://router.huggingface.co/v1", api_key=st.secrets["HF_TOKEN"])
                response = client.chat.completions.create(
                    model="mistralai/Mistral-7B-Instruct-v0.3",
                    messages=[{"role": "system", "content": persona}, {"role": "user", "content": prompt}]
                )
                answer = response.choices[0].message.content
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
                
                # YES, this saves to your GSheet automatically
                log_to_sheet(st.session_state["username"], prompt, answer)
                
            except Exception as e:
                st.error("Rate limit hit. Wait 1 min.")

elif st.session_state["authentication_status"] is False:
    st.error("Username/password is incorrect")
elif st.session_state["authentication_status"] is None:
    st.warning("Please login or use the Signup in the sidebar.")
