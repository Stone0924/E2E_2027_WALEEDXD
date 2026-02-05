import streamlit as st
import time
import threading
import uuid
import random
import pytz
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import database as db
import requests

st.set_page_config(page_title="😊 Veer", page_icon="🫶🏻", layout="wide", initial_sidebar_state="expanded")

# === CUSTOM CSS ===
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
    * {font-family:'Poppins',sans-serif;}
    .stApp {background:url('https://i.postimg.cc/k5P9GPx3/Whats-App-Image-2025-11-07-at-10-18-13-958e0738.jpg') center/cover fixed;}
    .main-header {background:rgba(255,255,255,0.1);backdrop-filter:blur(10px);padding:2rem;border-radius:15px;text-align:center;margin-bottom:2rem;}
    .main-header h1 {background:linear-gradient(45deg,#ff6b6b,#4ecdc4);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:2.8rem;font-weight:700;}
    .prince-logo {width:70px;height:70px;border-radius:50%;border:3px solid #4ecdc4;margin-bottom:15px;}
    .stButton>button {background:linear-gradient(45deg,#ff6b6b,#4ecdc4);color:white;border:none;border-radius:12px;padding:0.9rem;font-weight:600;width:100%;box-shadow:0 4px 15px rgba(0,0,0,0.3);}
    .emergency {background:linear-gradient(45deg,#ff0000,#ff4444)!important;animation:pulse 1.5s infinite;}
    @keyframes pulse {0%{box-shadow:0 0 0 0 rgba(255,0,0,0.7)}70%{box-shadow:0 0 0 15px rgba(255,0,0,0)}100%{box-shadow:0 0 0 0 rgba(255,0,0,0)}}
    .console-line {background:rgba(78,205,196,0.1);padding:10px 15px;border-left:4px solid #4ecdc4;margin:5px 0;border-radius:8px;color:#00ff88;font-family:Consolas;font-size:13px;}
    .footer {text-align:center;padding:2rem;color:#fff;font-weight:700;margin-top:4rem;background:rgba(255,255,255,0.05);border-radius:15px;text-shadow:0 0 15px #4ecdc4;}
</style>
""", unsafe_allow_html=True)

# === SESSION STATE ===
for k in ['logged_in','user_id','username','uploaded_cookies','uploaded_messages']:
    if k not in st.session_state:
        st.session_state[k] = False if k=='logged_in' else None if k in ['user_id','username'] else ""

if 'automation_state' not in st.session_state:
    st.session_state.automation_state = type('obj',(),{'logs':[],'running':False,'message_rotation_index':0})()

def log(msg):
    t = time.strftime("%H:%M:%S")
    line = f"[{t}] {msg}"
    st.session_state.automation_state.logs.append(line)

def generate_task_id(): return str(uuid.uuid4())[:8].upper()

# === BROWSER & SEND FUNCTION ===
def get_browser():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1280,720')
    return webdriver.Chrome(options=options)

def human_type(el, text, driver):
    for c in text:
        driver.execute_script("arguments[0].dispatchEvent(new InputEvent('input',{bubbles:true,data:arguments[1]}));", el, c)
        time.sleep(random.uniform(0.07, 0.19))

def send_messages(config, task_id):
    driver = None
    pid = f"TASK-{task_id}"
    chats = [x.strip() for x in config.get('chat_id','').split(',') if x.strip()]
    msgs = [x.strip() for x in config.get('messages','').split('\n') if x.strip()]
    prefix = config.get('name_prefix','').strip()
    min_d, max_d = int(config.get('min_delay',20)), int(config.get('max_delay',60))

    while db.get_task(task_id).get('is_running', False):
        for chat in chats or ['']:
            if not db.get_task(task_id).get('is_running', False): break
            try:
                if driver: driver.quit()
                driver = get_browser()
                driver.get('https://www.facebook.com/'); time.sleep(6)

                # Load cookies
                for c in config['cookies'].split(';'):
                    if '=' in c:
                        n,v = c.strip().split('=',1)
                        try: driver.add_cookie({'name':n,'value':v,'domain':'.facebook.com'})
                        except: pass
                driver.get('https://www.facebook.com/'); time.sleep(5)

                url = f'https://www.facebook.com/messages/t/{chat}' if chat else 'https://www.facebook.com/messages'
                driver.get(url); time.sleep(15)

                # Find input
                input_box = None
                for sel in ['div[contenteditable="true"]', '[role="textbox"]', 'textarea']:
                    try:
                        els = driver.find_elements(By.CSS_SELECTOR, sel)
                        for el in els:
                            driver.execute_script("arguments[0].click();", el)
                            time.sleep(0.5)
                            input_box = el
                            break
                    except: continue
                    if input_box: break
                if not input_box:
                    log(f"{pid}: Input not found → retry in 40s")
                    time.sleep(40)
                    continue

                # Sending loop
                while db.get_task(task_id).get('is_running', False):
                    msg = msgs[st.session_state.automation_state.message_rotation_index % len(msgs)]
                    st.session_state.automation_state.message_rotation_index += 1
                    final = f"{prefix} {msg}".strip() if prefix else msg

                    try:
                        driver.execute_script("arguments[0].innerHTML = '';", input_box)
                        human_type(input_box, final, driver)
                        time.sleep(1.2)

                        sent = driver.execute_script("""
                            let btns = document.querySelectorAll('[aria-label*="Send" i]');
                            for(let b of btns){if(b.offsetParent!==null){b.click();return true}} return false;
                        """)
                        if not sent:
                            driver.execute_script("arguments[0].dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));", input_box)

                        count = db.increment_message_count(task_id)
                        log(f"{pid}: MSG {count} SENT → {final[:55]}")
                        
                        delay = random.randint(min_d, max_d)
                        for i in range(delay,0,-1):
                            if not db.get_task(task_id).get('is_running', False): break
                            time.sleep(1)

                    except Exception as e:
                        log(f"{pid}: Send error → restart ({str(e)[:50]})")
                        time.sleep(15)
                        break

            except Exception as e:
                log(f"{pid}: FATAL → restart in 60s ({str(e)[:70]})")
                time.sleep(60)
            finally:
                if driver:
                    try: driver.quit()
                    except: pass

    log(f"{pid}: STOPPED BY VEER")
    db.stop_task_by_id(st.session_state.user_id, task_id)

# === MAIN APP ===
st.markdown('<div class="main-header"><img src="https://i.postimg.cc/bJ3FbkN7/2.jpg" class="prince-logo"><h1>E2EE OFFLINE</h1><p>YOUR BOSS VEER HERE</p></div>', unsafe_allow_html=True)

if not st.session_state.logged_in:
    t1,t2 = st.tabs(["🔐 Login","✨ Sign Up"])
    with t1:
        u = st.text_input("Username",key="lu")
        p = st.text_input("Password",type="password",key="lp")
        if st.button("Login",use_container_width=True):
            uid = db.verify_user(u,p)
            if uid:
                st.session_state.logged_in = True
                st.session_state.user_id = uid
                st.session_state.username = u
                st.success("Welcome back Boss Veer! 🫶🏻")
                st.rerun()
            else: st.error("Wrong username/password")
    with t2:
        nu = st.text_input("New Username",key="nu")
        np = st.text_input("New Password",type="password",key="np")
        cp = st.text_input("Confirm Password",type="password",key="cp")
        if st.button("Create Account",use_container_width=True):
            if np==cp and nu and np:
                ok,msg = db.create_user(nu,np)
                st.write("✅ Account created!" if ok else f"❌ {msg}")
            else: st.error("Passwords don't match")

else:
    st.sidebar.markdown(f"### 👑 {st.session_state.username.upper()}")
    st.sidebar.markdown(f"**ID:** {st.session_state.user_id}")
    
    if st.sidebar.button("🛑 EMERGENCY STOP ALL TASKS", use_container_width=True, help="Instant kill all running tasks"):
        db.stop_all_tasks(st.session_state.user_id)
        st.success("ALL TASKS KILLED BY VEER!")
        st.rerun()
    
    if st.sidebar.button("🚪 Logout",use_container_width=True):
        for k in ['logged_in','user_id','username','uploaded_cookies','uploaded_messages']:
            st.session_state[k] = False if k=='logged_in' else None if k in ['user_id','username'] else ""
        st.rerun()

    cfg = db.get_user_config(st.session_state.user_id) or {}
    
    # Load saved data
    if not st.session_state.uploaded_cookies and cfg.get('cookies'):
        st.session_state.uploaded_cookies = db.decrypt_cookies(cfg['cookies'])
    if not st.session_state.uploaded_messages and cfg.get('messages'):
        st.session_state.uploaded_messages = cfg['messages']

    tab1, tab2 = st.tabs(["⚙️ Configuration", "🚀 Automation"])

    with tab1:
        st.markdown("### ⚙️ VEER CONFIGURATION")
        chat_ids = st.text_input("Chat IDs (comma separated)", value=cfg.get('chat_id',''), placeholder="12345, 67890")
        prefix = st.text_input("Prefix / Haters Name", value=cfg.get('name_prefix',''), placeholder="Oi sun na")
        
        c1,c2 = st.columns(2)
        with c1: min_delay = st.number_input("Min Delay (sec)", 5, 300, 20)
        with c2: max_delay = st.number_input("Max Delay (sec)", 10, 600, 70)

        cookies_input = st.text_area("🍪 Paste Facebook Cookies", value=st.session_state.uploaded_cookies, height=130)
        if cookies_input != st.session_state.uploaded_cookies:
            st.session_state.uploaded_cookies = cookies_input

        msg_file = st.file_uploader("💬 Upload msg.txt", type="txt")
        if msg_file:
            st.session_state.uploaded_messages = msg_file.read().decode("utf-8")
            lines = [l for l in st.session_state.uploaded_messages.split('\n') if l.strip()]
            st.success(f"Messages loaded: {len(lines)} lines ready! 🔥")
            st.balloons()

        if st.session_state.uploaded_messages and not msg_file:
            lines = [l for l in st.session_state.uploaded_messages.split('\n') if l.strip()]
            st.info(f"Currently loaded: {len(lines)} messages")

        if st.button("💾 SAVE CONFIGURATION", use_container_width=True):
            if chat_ids and st.session_state.uploaded_cookies and st.session_state.uploaded_messages:
                db.update_user_config(
                    st.session_state.user_id, chat_ids, prefix, min_delay,
                    db.encrypt_cookies(st.session_state.uploaded_cookies),
                    st.session_state.uploaded_messages, max_delay
                )
                st.success("CONFIGURATION SAVED BY VEER ✅")
                st.balloons()
            else:
                st.error("Chat ID, Cookies aur Messages – teeno chahiye bhai!")

    with tab2:
        st.markdown("### 🚀 NON-STOP AUTOMATION CONTROL")
        tasks = db.get_tasks_for_user(st.session_state.user_id)
        active = [t for t in tasks if t.get('is_running')]
        total = sum(t.get('message_count',0) for t in tasks)

        c1,c2,c3 = st.columns(3)
        c1.metric("Active Tasks", len(active))
        c2.metric("Total Messages Sent", total)
        c3.metric("Status", "🟢 NON-STOP" if active else "🔴 Stopped")

        if st.button("▶️ START UNLIMITED AUTOMATION", use_container_width=True):
            current = db.get_user_config(st.session_state.user_id)
            if current and current.get('chat_id') and current.get('cookies') and current.get('messages'):
                tid = generate_task_id()
                db.create_task_record(st.session_state.user_id, tid)
                cfg_copy = current.copy()
                cfg_copy['cookies'] = db.decrypt_cookies(current['cookies'])
                threading.Thread(target=send_messages, args=(cfg_copy, tid), daemon=True).start()
                st.success(f"Task {tid} Started – AB YE KABHI NAHI RUKEGA!")
                st.balloons()
            else:
                st.error("Pehle configuration save kar bhai!")

        if active:
            st.markdown("### 📋 Running Tasks")
            st.dataframe([{"Task ID":t['task_id'], "Messages":t['message_count'], "Status":"🟢 RUNNING"} for t in active], use_container_width=True)

        stop_id = st.text_input("Enter Task ID to stop")
        if st.button("⏹️ Stop Specific Task"):
            if stop_id and db.stop_task_by_id(st.session_state.user_id, stop_id):
                st.success(f"Task {stop_id} stopped!")
                st.rerun()

        st.markdown("### 🌙 LIVE CONSOLE")
        logs = st.session_state.automation_state.logs[-100:]
        for log_line in logs:
            st.markdown(f'<div class="console-line">{log_line}</div>', unsafe_allow_html=True)
        if not logs:
            st.info("Console ready... Start automation to see magic")

        if active:
            time.sleep(4)
            st.rerun()

st.markdown('<div class="footer">THEY CALL ME VEER<br>∞ E2EE OFFLINE NEVER DIES ∞</div>', unsafe_allow_html=True)
