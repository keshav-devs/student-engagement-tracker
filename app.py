import streamlit as st
import cv2
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import time
from vision import process_frame, release_resources
from db_service import init_db, get_recent_data, get_all_data

# 1. Silence Warnings (layout='wide' at very top)
st.set_page_config(page_title="Student Engagement Tracker", layout="wide", page_icon="📈")

# Initialize SQLite database
init_db()

st.title("👨‍🏫 Student Engagement Tracker")

# Apply Custom Styled CSS
st.markdown("""
<style>
    /* Rounded corners for camera feed */
    img {
        border-radius: 15px;
    }
    
    /* Live Status Light */
    .status-active {
        color: #00FF00 !important;
        font-size: 24px;
        font-weight: bold;
        text-shadow: 0 0 10px #00FF00;
    }
    
    .status-inactive {
        color: #888888 !important;
        font-size: 24px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

from collections import deque
from datetime import datetime, timedelta

# Session tracking variables
if 'start_time' not in st.session_state:
    st.session_state.start_time = None
if 'peak_cei' not in st.session_state:
    st.session_state.peak_cei = 0
if 'current_cei' not in st.session_state:
    st.session_state.current_cei = 0
if 'wma_buffer' not in st.session_state:
    st.session_state.wma_buffer = deque(maxlen=15)  # 15-frame Weighted Moving Average
if 'chart_buffer' not in st.session_state:
    st.session_state.chart_buffer = deque(maxlen=900)  # ~30s at 30fps

# Sidebar Migration
with st.sidebar:
    st.header("Control Panel")
    run_camera = st.checkbox("Start Camera", value=False)
    
    st.markdown("---")
    st.markdown("### Session Statistics")
    
    # Native Streamlit Native Containers for border + light/dark adaptivity
    with st.container(border=True):
        metric_cei = st.empty()
    with st.container(border=True):
        metric_peak = st.empty()
    with st.container(border=True):
        metric_time = st.empty()
    
    # Fill with placeholder/initial values immediately
    metric_cei.metric(label="Current Engagement (CEI)", value=f"{st.session_state.current_cei:.1f}%")
    metric_peak.metric(label="Peak Engagement", value=f"{st.session_state.peak_cei:.1f}%")
    
    elapsed_seconds = int(time.time() - st.session_state.start_time) if st.session_state.start_time else 0
    session_time = f"{elapsed_seconds // 60}m {elapsed_seconds % 60}s"
    metric_time.metric(label="Total Session Time", value=session_time)

    st.markdown("---")
    
    st.markdown("### Export Logs")
    all_data = get_all_data()
    if not all_data.empty:
        # Report Fix: HH:MM:SS format
        if pd.api.types.is_datetime64_any_dtype(all_data['timestamp']):
            all_data['timestamp'] = all_data['timestamp'].dt.strftime('%H:%M:%S')
        else:
            # If it's stored as a string, parse and re-format
            try:
                all_data['timestamp'] = pd.to_datetime(all_data['timestamp']).dt.strftime('%H:%M:%S')
            except Exception:
                pass
        csv = all_data.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Report (CSV)",
            data=csv,
            file_name="engagement_report.csv",
            mime="text/csv",
        )

    st.markdown("---")
    st.markdown("**Powered by:** OpenCV, Mediapipe, SQLite")
    
    st.markdown("---")
    st.markdown("### Debug")
    show_landmarks = st.checkbox("Show Landmarks", value=False)

# Aesthetic Layout: Two columns (Video | Status & Chart)
col_main, col_status = st.columns([2.5, 1])

with col_main:
    st.subheader("Live Camera Feed")
    frame_placeholder = st.empty()

with col_status:
    st.subheader("Live Status")
    status_placeholder = st.empty()
    status_placeholder.markdown("<p class='status-inactive'>⚫ Inactive</p>", unsafe_allow_html=True)
    
    st.markdown("### Engagement Trend")
    chart_placeholder = st.empty()

if run_camera:
    if st.session_state.start_time is None:
        st.session_state.start_time = time.time()
        
    status_placeholder.markdown("<p class='status-active'>🟢 Active Tracking</p>", unsafe_allow_html=True)
    
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) # Eliminate Lag
    
    try:
        frame_count = 0
    
        while run_camera:
            ret, frame = cap.read()
            if not ret:
                st.error("Could not read frame from webcam.")
                break
            
            frame_count += 1
            
            processed_frame, student_count, cei_raw = process_frame(frame, show_landmarks=show_landmarks)
            
            # 15-Frame Weighted Moving Average (WMA)
            # Recent frames weighted more heavily: weights [1, 2, 3, ..., 15]
            st.session_state.wma_buffer.append(cei_raw)
            buf = list(st.session_state.wma_buffer)
            weights = list(range(1, len(buf) + 1))  # [1, 2, ..., n]
            wma_value = sum(w * v for w, v in zip(weights, buf)) / sum(weights)
            
            st.session_state.current_cei = wma_value
        
            # Correctly update Peak CEI logic
            if wma_value > st.session_state.peak_cei:
                st.session_state.peak_cei = wma_value
            
            elapsed_seconds = int(time.time() - st.session_state.start_time)
            session_time = f"{elapsed_seconds // 60}m {elapsed_seconds % 60}s"
        
            # Update sidebar metrics dynamically
            metric_cei.metric(label="Current Engagement (CEI)", value=f"{wma_value:.1f}%")
            metric_peak.metric(label="Peak Engagement", value=f"{st.session_state.peak_cei:.1f}%")
            metric_time.metric(label="Total Session Time", value=session_time)
        
            # Update Streamlit image
            processed_frame_rgb = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
            frame_placeholder.image(processed_frame_rgb, channels="RGB", use_container_width=True)
        
            # Always collect data into buffer
            now = datetime.now()
            st.session_state.chart_buffer.append({'Time': now, 'CEI': wma_value})
            
            # Only render the chart every 5 frames to prevent blinking
            if frame_count % 5 == 0:
                df_chart = pd.DataFrame(list(st.session_state.chart_buffer))
                cutoff = now - timedelta(seconds=30)
                df_chart = df_chart[df_chart['Time'] >= cutoff]
                
                if not df_chart.empty:
                    df_chart['CEI'] = df_chart['CEI'].clip(0, 100)
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=df_chart['Time'],
                        y=df_chart['CEI'],
                        mode='lines',
                        line=dict(shape='spline', smoothing=1.3, color='#6C63FF', width=3),
                        fill='tozeroy',
                        fillcolor='rgba(108, 99, 255, 0.2)',
                        hovertemplate='%{y:.1f}%<extra></extra>'
                    ))
                    
                    fig.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        margin=dict(l=0, r=0, t=10, b=0),
                        yaxis=dict(range=[0, 100], title='CEI %', showgrid=False),
                        xaxis=dict(
                            range=[cutoff, now],
                            showticklabels=True,
                            tickformat='%M:%S',
                            title='Time',
                            showgrid=False
                        ),
                        showlegend=False,
                        height=280
                    )
                    
                    chart_placeholder.plotly_chart(
                        fig, use_container_width=True,
                        config={'displayModeBar': False}
                    )
            
    finally:
        cap.release()
        release_resources()
else:
    # Release camera explicitly when unchecked to prevent hangups
    try:
        cap.release()
        release_resources()
    except Exception:
        pass
        
    st.session_state.start_time = None
    frame_placeholder.info("Camera is currently stopped. Check the box in the sidebar to start.")
