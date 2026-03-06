# 👨‍🏫 Student Engagement Tracker: Presentation Guide

This guide provides a deep technical walkthrough of the **Student Engagement Tracker**. Use these points to explain the project's functioning and support during your presentation.

---

## 1. High-Level Architecture
The project is built on a "Real-time Signal Processing" pipeline with three core layers:
- **Frontend (Streamlit)**: Handles the UI layout, Plotly data visualization, and the 10fps rendering loop.
- **AI Core (MediaPipe + OpenCV)**: Performs sub-millisecond face landmark detection and geometric calculations.
- **Persistence (SQLite)**: Logs engagement data every 30 seconds for long-term historical reporting.

---

## 2. The "Intelligence" Layer (`vision.py`)
Instead of simple binary "yes/no" tracking, we use **Geometric Yaw Estimation**:

### A. Nose-to-Edge Ratio (Head Yaw)
- We calculate the distance from the **Nose Tip** (Landmark 1) to the **Left** and **Right** edges of the face.
- **Mathematical Logic**: As the head turns, the nose moves closer to one edge of the face's bounding box.
- **Yaw Angle Estimation**: We convert this horizontal ratio into an approximate degree of turn (0° to 45°).

### B. Linear Interpolation (Lerp) Scoring
- **Old Way (Binary)**: Hard cutoffs (if angle > 20, Distracted) cause "flickering" scores.
- **Our Way (Continuous)**: We use a **Lerp** function: `Engagement = 100 - (Yaw_Angle * 2.22)`.
  - **Centered (0°)**: 100% Engagement score.
  - **Half-Turn (22.5°)**: 50% Engagement score.
  - **Full Turn (45°)**: 0% Engagement score.
- This results in a smooth, professional feel where the score glides naturally.

### C. Visual Debugger: The "Focus Vector"
- We draw a 3D-simulated arrow coming out of the nose.
- The arrow's angle is calculated directly from the Yaw ratio.
- **Presentation Tip**: Show how the arrow points straight at the camera when you are focused, and "breaks" away when you turn. This is the visual proof of the math.

---

## 3. The "Signal Smoothing" Layer (`app.py`)
Raw AI data is often "noisy" (jittery). We solve this with **Advanced Signal Processing**:

### Weighted Moving Average (WMA)
- We maintain a **15-frame buffer** of raw scores.
- Unlike a standard average, we apply **Linear Weights** `[1, 2, ..., 15]`.
- **Why?**: This gives more importance to the most recent frame while still "remembering" the previous second of data.
- **Effect**: If you blink or the AI glitches for a single frame, the score remains stable. It requires a sustained head turn to drop the score, mimicking human attention.

---

## 4. UI Performance & Aesthetics
Real-time video in a web browser is computationally expensive. We optimized it using:

- **`st.empty()` In-place Updates**: Instead of rebuilding the whole page (which causes white flashes), we use "slots" to swap only the video frame and the graph.
- **Plotly Spline Interpolation**: We use a `spline` shape for the area chart. This mathematically rounds the corners of the data points to create a "wave-like" aesthetic rather than jagged sticks.
- **Frame-Skipped Rendering**: The AI detects data at full speed (~30fps), but we only update the Plotly graph every **5 frames**. 
  - **Benefit**: This reduces browser CPU load by 80%, keeping the UI responsive even on lower-end laptops.

---

## 5. Summary of Key Innovations
1. **No Hard Cutoffs**: 0-100% continuous range for nuanced tracking.
2. **Double-Smoothing**: Geometric Lerp (Vision) + Weighted Average (App).
3. **Transparent Persistence**: Background SQLite logging without slowing down the live feed.
4. **Adaptive Baseline**: Min-Max scaling that maps raw sensor data into human-readable percentages.

---

### Presentation Quote
> *"Our project moves beyond binary distraction detection by treating student attention as a continuous signal. By leveraging 3D geometric yaw estimation and weighted signal smoothing, we've created a dashboard that is both scientifically accurate and visually fluid."*
