#!/usr/bin/env python3
"""
WALEED AUTO-RESTART SCRIPT
This script monitors and automatically restarts the Streamlit app if it crashes
"""

import subprocess
import time
import sys
import os
from datetime import datetime

def log_message(msg):
    """Print timestamped log message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")

def run_streamlit():
    """Run the Streamlit application"""
    log_message("Starting Waleed Streamlit App...")
    
    # Command to run streamlit
    cmd = [sys.executable, "-m", "streamlit", "run", "app.py", 
           "--server.port=8501", 
           "--server.address=0.0.0.0",
           "--server.headless=true"]
    
    try:
        # Start the streamlit process
        process = subprocess.Popen(cmd)
        log_message(f"Streamlit started with PID: {process.pid}")
        
        # Wait for the process to complete
        process.wait()
        
        # If we get here, the process has ended
        log_message(f"Streamlit process ended with code: {process.returncode}")
        return process.returncode
        
    except KeyboardInterrupt:
        log_message("Received keyboard interrupt, stopping...")
        process.terminate()
        return -1
    except Exception as e:
        log_message(f"Error running Streamlit: {e}")
        return 1

def main():
    """Main loop to keep restarting Streamlit"""
    log_message("=== WALEED AUTO-RESTART MANAGER STARTED ===")
    
    restart_count = 0
    max_restart_delay = 60  # Maximum delay between restarts
    
    while True:
        restart_count += 1
        log_message(f"Restart attempt #{restart_count}")
        
        # Run streamlit
        exit_code = run_streamlit()
        
        # Check if user wants to stop
        if exit_code == -1:
            log_message("User requested stop. Exiting...")
            break
        
        # Calculate restart delay (increases with failures, max 60 seconds)
        restart_delay = min(restart_count * 5, max_restart_delay)
        
        log_message(f"Streamlit crashed! Restarting in {restart_delay} seconds...")
        
        # Wait before restarting
        try:
            time.sleep(restart_delay)
        except KeyboardInterrupt:
            log_message("Received interrupt during wait. Exiting...")
            break
        
        # Reset counter after successful runs
        if restart_delay >= max_restart_delay:
            restart_count = 0

if __name__ == "__main__":
    main()
