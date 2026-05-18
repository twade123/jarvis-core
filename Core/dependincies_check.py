#!/usr/bin/env python3

import whisper
import pyaudio
import ctypes
import subprocess

try:
	# Attempt to load FFmpeg libraries
	ffmpeg_path = "/path/to/ffmpeg/lib"
	ctypes.CDLL(f"{ffmpeg_path}/libavutil.so")  # Example call, customize as needed
	print("FFmpeg libraries loaded successfully.")
except Exception as e:
	print(f"Error loading FFmpeg libraries: {e}")
	
# Check Whisper and PyAudio
try:
	whisper_model = whisper.load_model("base")
	print("Whisper model loaded successfully.")
except Exception as e:
	print(f"Error loading Whisper model: {e}")
	
try:
	audio = pyaudio.PyAudio()
	print("PyAudio initialized successfully.")
	audio.terminate()
except Exception as e:
	print(f"Error initializing PyAudio: {e}")