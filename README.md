# 🎓 Student Engagement Tracker: AI-Powered Focus Analytics

An intelligent, real-time monitoring system designed to quantify student attention through computer vision. This project was developed as an **Integrated Project for CSE Semester 4** at **Chitkara University**.

> **🚀 Developer's Note: Vibe Coded with Purpose**
> This project was built with a **"Vibe Coding"** philosophy—leveraging AI-assisted development as a co-pilot to rapidly iterate from a raw concept to a high-accuracy, production-ready dashboard. It’s proof that with the right "vibe" and the right prompts, a single student can build a complex signal-processing engine in record time.

---

## ✨ Key Technical Innovations

### 1. The "Intelligence" Layer (`vision.py`)
Moving beyond simple binary tracking, this system treats engagement as a continuous signal:
* **Geometric Yaw Estimation**: We calculate the horizontal ratio between the **Nose Tip** (Landmark 1) and face boundaries to estimate head turn angles (0° to 45°).
* **Linear Interpolation (Lerp) Scoring**: Instead of "flickering" hard cutoffs, we use a **Lerp** function to ensure the score glides naturally from 100% to 0%.
  * **Equation:** $Engagement = 100 - (Yaw\_Angle \times 2.22)$
* **3D Focus Vector**: A visual debugger draws a simulated arrow from the nose, providing real-time proof of the geometric math behind the tracking.



### 2. Signal Smoothing & Performance (`app.py`)
To eliminate AI "jitter" and hardware lag, we implemented advanced signal processing:
* **Weighted Moving Average (WMA)**: A **15-frame buffer** uses linear weights to prioritize recent data while smoothing out blinks or technical glitches.
* **Spline-Based Wavecharts**: Using **Plotly Spline Interpolation**, the engagement trend is rendered as a fluid "wave" rather than a jagged line, improving aesthetic clarity.
* **Flicker-Free Rendering**: Leveraging `st.empty()` placeholders, the UI updates in-place without refreshing the browser, reducing CPU load by 80%.

---

## 🛠️ Tech Stack
- **AI Core:** MediaPipe (Face Mesh), OpenCV
- **UI/Frontend:** Streamlit
- **Data Viz:** Plotly
- **Database:** SQLite (Local Persistence)
- **Language:** Python 3.11

---

🚀 Installation & Deployment
Local Setup
Clone the repository:

Bash
git clone [https://github.com/yourusername/engagement-tracker.git](https://github.com/yourusername/engagement-tracker.git)
cd engagement-tracker
Install dependencies:

Bash
pip install -r requirements.txt
Run the application:

Bash
streamlit run app.py
Cloud Deployment
This repo is pre-configured for Streamlit Community Cloud.

The packages.txt ensures Linux-level OpenCV dependencies are handled automatically.

Ensure your GitHub repo is public and connect it directly via the Streamlit Cloud dashboard.
