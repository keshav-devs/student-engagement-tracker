import sys

print("=== Python Environment ===")
print(f"Executable: {sys.executable}")
print(f"Version: {sys.version.split()[0]}")
print("-" * 25)

print("=== Library Health Check ===")

# OpenCV Check
try:
    import cv2
    print(f"[SUCCESS] OpenCV (cv2) successfully imported. Version: {cv2.__version__}")
except ImportError as e:
    print(f"[FAIL] Failed to import OpenCV: {e}")

# Mediapipe Check
try:
    import mediapipe as mp
    print(f"[SUCCESS] Mediapipe successfully imported. Version: {mp.__version__}")
except ImportError as e:
    print(f"[FAIL] Failed to import Mediapipe: {e}")

# Streamlit Check
try:
    import streamlit as st
    print(f"[SUCCESS] Streamlit successfully imported. Version: {st.__version__}")
except ImportError as e:
    print(f"[FAIL] Failed to import Streamlit: {e}")

# Other Dependencies Check
try:
    import pandas as pd
    import numpy as np
    import matplotlib
    import seaborn as sns
    print("[SUCCESS] Data tools (pandas, numpy, matplotlib, seaborn) successfully imported.")
except ImportError as e:
    print(f"[FAIL] Failed to import data tools: {e}")

print("-" * 25)
print("If all checks have a [SUCCESS] next to them, your environment is ready to go!")
