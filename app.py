import streamlit as st
import cv2
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import time
import threading
from datetime import datetime, timedelta
from streamlit_webrtc import webrtc_streamer, RTCConfiguration, WebRtcMode

# Import the renamed module
try:
    from face_analysis import process_frame, release_resources
except ImportError:
    st.error("Missing face_analysis.py. Please ensure the file is in the root directory.")

from db_service import init_db, get_recent_data, get_all_data

# Initialize SQLite database
init_db()

st.set_page_config(page_title="Student Engagement Tracker", layout="wide", page_icon="📈")
st.title("👨‍🏫 Student Engagement Tracker")

# Expanded STUN Servers for better cloud connectivity
RTC_CONFIGURATION = RTCConfiguration(
    {
        "iceServers": [
            {"urls": ["stun:stun.l.google.com:19302"]},
            {"urls": ["stun:stun1.l.google.com:19302"]},
            {"urls": ["stun:stun2.l.google.com:19302"]},
            {"urls": ["stun:stun3.l.google.com:19302"]},
            {"urls": ["stun:stun4.l.google.com:19302"]},
        ]
    }
)

class AppState:
    def __init__(self):
        self.current_cei = 0.0
        self.peak_cei = 0.0
        self.show_landmarks = False
        self.lock = threading.Lock()

if "app_state" not in st.session_state:
    st.session_state.app_state = AppState()

app_state = st.session_state.app_state

def video_frame_callback(frame):
    img = frame.to_ndarray(format="bgr24")
    with app_state.lock:
        local_show_landmarks = app_state.show_landmarks
    
    # Process frame
    processed_frame, student_count, cei_raw = process_frame(img, show_landmarks=local_show_landmarks)
    
    with app_state.lock:
        app_state.current_cei = cei_raw
        if cei_raw > app_state.peak_cei:
            app_state.peak_cei = cei_raw
            
    import av
    return av.VideoFrame.from_ndarray(processed_frame, format="bgr24")

st.markdown("""
<style>
    canvas, video { border-radius: 15px !important; }
    .status-active { color: #00FF00 !important; font-size: 24px; font-weight: bold; text-shadow: 0 0 10px #00FF00; }
    .status-inactive { color: #888888 !important; font-size: 24px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("Control Panel")
    new_show_landmarks = st.checkbox("Show Landmarks", value=app_state.show_landmarks, key="landmarks_toggle")
    with app_state.lock:
        app_state.show_landmarks = new_show_landmarks
    
    st.markdown("---")
    st.markdown("### Session Statistics")
    metric_cei_placeholder = st.empty()
    metric_peak_placeholder = st.empty()
    metric_time_placeholder = st.empty()

    st.markdown("---")
    if st.button("Generate Report"):
        all_data = get_all_data()
        if not all_data.empty:
            csv = all_data.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download CSV", csv, "engagement_report.csv", "text/csv")

# Main Layout
col_main, col_status = st.columns([2.5, 1])

with col_main:
    st.subheader("Live Camera Feed")
    # Added defensive check to ensure ctx is created before use
    ctx = webrtc_streamer(
        key="engagement-tracker-v2", # Changed key to force re-initialization
        mode=WebRtcMode.SENDRECV,
        rtc_configuration=RTC_CONFIGURATION,
        video_frame_callback=video_frame_callback,
        media_stream_constraints={"video": True, "audio": False},
        async_processing=True,
    )

with col_status:
    st.subheader("Live Status")
    status_placeholder = st.empty()
    
    # Defensive check on ctx.state
    is_playing = False
    try:
        if ctx and ctx.state and ctx.state.playing:
            is_playing = True
    except Exception:
        pass

    if is_playing:
        if 'start_time' not in st.session_state:
            st.session_state.start_time = time.time()
        status_placeholder.markdown("<p class='status-active'>🟢 Active Tracking</p>", unsafe_allow_html=True)
    else:
        st.session_state.pop('start_time', None)
        status_placeholder.markdown("<p class='status-inactive'>⚫ Inactive</p>", unsafe_allow_html=True)
    
    st.markdown("### Engagement Trend")
    chart_placeholder = st.empty()

# UI Persistence
if 'chart_df' not in st.session_state:
    st.session_state.chart_df = pd.DataFrame(columns=['Time', 'CEI'])

if is_playing:
    try:
        with app_state.lock:
            current_cei = app_state.current_cei
            peak_cei = app_state.peak_cei
        
        elapsed = int(time.time() - st.session_state.start_time) if 'start_time' in st.session_state else 0
        metric_cei_placeholder.metric("Current Engagement (CEI)", f"{current_cei:.1f}%")
        metric_peak_placeholder.metric("Peak Engagement", f"{peak_cei:.1f}%")
        metric_time_placeholder.metric("Total Session Time", f"{elapsed // 60}m {elapsed % 60}s")
        
        now = datetime.now()
        new_row = pd.DataFrame([{'Time': now, 'CEI': current_cei}])
        st.session_state.chart_df = pd.concat([st.session_state.chart_df, new_row], ignore_index=True)
        cutoff = now - timedelta(seconds=30)
        st.session_state.chart_df = st.session_state.chart_df[st.session_state.chart_df['Time'] >= cutoff]
        
        if not st.session_state.chart_df.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=st.session_state.chart_df['Time'], y=st.session_state.chart_df['CEI'],
                mode='lines', line=dict(shape='spline', color='#6C63FF', width=3),
                fill='tozeroy', fillcolor='rgba(108, 99, 255, 0.2)'
            ))
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=10, b=0), height=250,
                yaxis=dict(range=[0, 100]), xaxis=dict(showgrid=False, tickformat='%M:%S')
            )
            chart_placeholder.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        time.sleep(1)
        st.rerun()
    except Exception:
        pass
else:
    with app_state.lock:
        peak_cei = app_state.peak_cei
    metric_cei_placeholder.metric("Current Engagement (CEI)", "0.0%")
    metric_peak_placeholder.metric("Peak Engagement", f"{peak_cei:.1f}%")
    metric_time_placeholder.metric("Total Session Time", "0m 0s")
    chart_placeholder.info("Start the stream to see the engagement trend.")
