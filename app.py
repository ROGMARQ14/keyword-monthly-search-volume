import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import time

st.set_page_config(
    page_title="SEO Keyword Analyzer",
    page_icon="📈",
    layout="wide"
)

def get_keyword_data(api_key, campaign_id, offset=0, start_date=None, end_date=None):
    """Get keyword data from SEOmonitor API"""
    base_url = "https://api.seomonitor.com/v3/rank-tracker/v3.0/keywords"
    
    headers = {
        'Accept': 'application/json',
        'Authorization': api_key
    }
    
    # Format dates as required by the API
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    params = {
        'campaign_id': campaign_id,
        'start_date': start_date,
        'end_date': end_date,
        'limit': '100',
        'offset': str(offset)
    }
    
    try:
        response = requests.get(base_url, headers=headers, params=params)
        if response.status_code == 401:
            st.error("Authentication failed. Please check your API key.")
            return None
        elif response.status_code == 404:
            st.error("Campaign not found. Please check your campaign ID.")
            return None
            
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching keyword data: {str(e)}")
        return None

def process_keywords(api_key, campaign_id, keywords):
    """Process keywords and get their search volumes"""
    keyword_set = {k.lower() for k in keywords}
    all_results = []
    
    # Initialize offset and total processed
    offset = 0
    total_processed = 0
    max_retries = 10  # Maximum number of empty results before stopping
    empty_results_count = 0
    
    progress_text = st.empty()
    progress_bar = st.progress(0)
    
    while True:
        progress_text.text(f"Processing keywords (offset: {offset})...")
        progress_bar.progress(min(total_processed / len(keywords), 1.0))
        
        # Get batch of keywords from the campaign
        batch_data = get_keyword_data(api_key, campaign_id, offset)
        
        if not batch_data or not isinstance(batch_data, list) or len(batch_data) == 0:
            empty_results_count += 1
            if empty_results_count >= max_retries:
                break
            offset += 100
            continue
        
        # Reset empty results counter if we got data
        empty_results_count = 0
        
        # Process the batch
        for item in batch_data:
            if isinstance(item, dict):
                keyword = item.get('keyword', '').lower()
                if keyword in keyword_set:
                    all_results.append(item)
                    total_processed += 1
        
        # If we got less than the batch size, we've reached the end
        if len(batch_data) < 100:
            break
            
        offset += 100
    
    progress_text.empty()
    progress_bar.empty()
    
    return process_results(all_results, keywords)

def process_results(data, original_keywords):
    """Process the API results into a DataFrame"""
    # Create a dictionary with all keywords initialized to 0 search volume
    results_dict = {keyword.lower(): {'keyword': keyword, 'search_volume': 0} for keyword in original_keywords}
    
    # Update search volumes for keywords found in the API response
    for item in data:
        try:
            keyword = item.get('keyword', '').lower()
            if keyword in results_dict:
                # Try to get search volume from different possible locations in the API response
                search_data = item.get('search_data', {})
                if isinstance(search_data, dict):
                    search_volume = search_data.get('search_volume')
                    if search_volume is not None:
                        results_dict[keyword]['search_volume'] = int(search_volume)
        except (TypeError, ValueError) as e:
            continue
    
    return list(results_dict.values())

def main():
    st.title("SEO Keyword Analyzer 📈")
    
    # Initialize session state
    if 'show_zero_volume' not in st.session_state:
        st.session_state.show_zero_volume = True
    
    # Create columns for the form
    col1, col2 = st.columns(2)
    
    with col1:
        api_key = st.text_input("API Key", type="password")
    
    with col2:
        campaign_id = st.text_input("Campaign ID")
    
    # File uploader
    uploaded_file = st.file_uploader("Upload Keywords CSV", type=['csv', 'txt'])
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            keywords = df.iloc[:, 0].tolist()  # Take the first column
            st.write(f"Found {len(keywords)} keywords in the file.")
            
            # Button to get search volumes
            if st.button("Get Search Volumes 🔍"):
                if not api_key or not campaign_id:
                    st.error("Please provide both API Key and Campaign ID.")
                else:
                    results = process_keywords(api_key, campaign_id, keywords)
                    
                    if results:
                        # Convert results to DataFrame
                        df_results = pd.DataFrame(results)
                        
                        # Results section
                        st.header("📊 Results")
                        
                        # Checkbox for showing zero volume keywords
                        st.session_state.show_zero_volume = st.checkbox(
                            "Show keywords with zero search volume",
                            value=st.session_state.show_zero_volume
                        )
                        
                        # Filter based on checkbox
                        if not st.session_state.show_zero_volume:
                            df_results = df_results[df_results['search_volume'] > 0]
                        
                        # Summary statistics
                        st.subheader("📈 Summary Statistics")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("Total Keywords 📝", len(df_results))
                        
                        with col2:
                            avg_volume = int(df_results['search_volume'].mean())
                            st.metric("Avg Search Volume 🔍", avg_volume)
                        
                        with col3:
                            total_volume = int(df_results['search_volume'].sum())
                            st.metric("Total Search Volume 📊", total_volume)
                        
                        # Display results table
                        st.dataframe(df_results)
                        
                        # Download button
                        csv = df_results.to_csv(index=False)
                        st.download_button(
                            label="Download Results CSV 📥",
                            data=csv,
                            file_name="keyword_volumes.csv",
                            mime="text/csv"
                        )
                    
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")

if __name__ == "__main__":
    main()
