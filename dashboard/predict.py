import time

import requests
from requests.exceptions import RequestException, Timeout
import streamlit as st

# --- Constant ---
API_URL = "https://bluerrose-attica-traffic-api.hf.space/predict"

def call_hf_api(road_name, target_date):

    payload = {
        "road_name": road_name,
        "target_date": target_date.strftime("%Y-%m-%d"),
        "target_hour": target_date.hour
    }

    with st.status("Connecting to API...", expanded=False) as status:
        
        max_retries = 5
        wait_seconds = 5
        multiplier = 2
        success = False
        
        for attempt in range(1, max_retries + 1):
            try:
                st.write(f"Attempt {attempt} of {max_retries}...")
                
                # Make the request
                response = requests.post(
                    API_URL, 
                    json=payload, 
                    timeout=5 
                )
                
                if response.status_code == 200:
                    st.write("✅ Connection successful!")
                    status.update(label="API Connection Established", state="complete")
                    success = True
                    return response.json()
                
                elif response.status_code == 503:
                    st.write("😴 Server is asleep...")
                    status.update(label="Server was asleep and is now waking up. This will take a minute...")
                    # We don't break here, we let the loop continue to retry
                    
            except Timeout:
                st.write("⏰ Server is walking up from sleep...")
                
            except RequestException as e:
                st.write(f"❌ Connection error: {e}")
            
            # If we are here, it failed. Wait before next attempt.
            if attempt < max_retries:
                st.write(f"Waiting {wait_seconds * attempt * multiplier} seconds...")
                time.sleep(wait_seconds * attempt * multiplier)

        # This runs after the loop finishes
        if not success:
            status.update(
                label="Connection failed after multiple attempts.", 
                state="error"
            )
            st.error("Could not connect to the API. Please try again later.")