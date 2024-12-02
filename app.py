import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import math

def get_keyword_data_batch(api_key, campaign_id, offset=0, limit=1000, start_date=None, end_date=None):
    """Get a batch of keyword data from SEOmonitor API"""
    base_url = "https://apigw.seomonitor.com/v3/rank-tracker/v3.0/keywords"
    
    headers = {
        'Accept': 'application/json',
        'Authorization': api_key
    }
    
    params = {
        'campaign_id': campaign_id,
        'start_date': start_date or (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
        'end_date': end_date or datetime.now().strftime('%Y-%m-%d'),
        'limit': limit,
        'offset': offset
    }
    
    try:
        response = requests.get(base_url, headers=headers, params=params)
        if response.status_code == 401:
            st.error("Authentication failed. Please check your API key.")
            return None
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching keyword data: {str(e)}")
        return None

def get_all_keyword_data(api_key, campaign_id, total_keywords=None, start_date=None, end_date=None):
    """Get all keyword data with pagination"""
    all_results = []
    offset = 0
    limit = 1000  # Increased batch size
    
    with st.progress(0) as progress_bar:
        while True:
            batch = get_keyword_data_batch(api_key, campaign_id, offset, limit, start_date, end_date)
            if not batch:
                break
                
            if isinstance(batch, list):
                all_results.extend(batch)
                
                # Update progress
                if total_keywords:
                    progress = min(1.0, len(all_results) / total_keywords)
                    progress_bar.progress(progress)
                    
                if len(batch) < limit:  # Last batch
                    break
                    
                offset += limit
            else:
                break
                
    return all_results

def process_results(data):
    """Process the API results into a DataFrame"""
    results = []
    for item in data:
        keyword_data = {
            'keyword': item.get('keyword', ''),
            'search_volume': int(item.get('search_data', {}).get('search_volume', 0) or 0),  # Handle None values
            'difficulty': float(item.get('difficulty', 0) or 0),  # Handle None values
            'current_rank': int(item.get('rank_data', {}).get('current_rank', 0) or 0),  # Handle None values
            'trend': item.get('search_data', {}).get('trend', '')
        }
        results.append(keyword_data)
    return results

def main():
    st.title("Keyword Analysis Tool (SEOmonitor)")
    st.write("Enter your SEOmonitor API key and campaign ID to analyze keyword data.")
    
    # API credentials input
    api_key = st.text_input("SEOmonitor API Key", type="password")
    campaign_id = st.text_input("Campaign ID")
    
    if api_key and campaign_id:
        uploaded_file = st.file_uploader("Choose a CSV file with keywords (optional)", type="csv")
        
        # Date range selection
        col1, col2 = st.columns(2)
        with col1:
            default_start = datetime.now() - timedelta(days=30)
            start_date = st.date_input("Start Date", default_start, max_value=datetime.now())
        with col2:
            end_date = st.date_input("End Date", datetime.now(), min_value=start_date, max_value=datetime.now())
            
        if st.button("Get Keyword Data"):
            if start_date > end_date:
                st.error("Start date must be before end date")
                return
                
            with st.spinner('Fetching keyword data...'):
                total_keywords = None
                if uploaded_file:
                    try:
                        df = pd.read_csv(uploaded_file)
                        total_keywords = len(df.iloc[:, 0].tolist())
                    except Exception as e:
                        st.error(f"Error reading CSV file: {str(e)}")
                        return
                
                results_data = get_all_keyword_data(
                    api_key=api_key,
                    campaign_id=campaign_id,
                    total_keywords=total_keywords,
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d')
                )
                
                if results_data:
                    results = process_results(results_data)
                    results_df = pd.DataFrame(results)
                    
                    st.write("### Results")
                    # Format the dataframe
                    if not results_df.empty:
                        results_df = results_df.sort_values('search_volume', ascending=False)
                        st.dataframe(results_df.style.format({
                            'search_volume': '{:,.0f}',
                            'difficulty': '{:.1f}',
                            'current_rank': '{:.0f}'
                        }))
                        
                        # Show summary statistics
                        st.write("### Summary Statistics")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Keywords", len(results_df))
                        with col2:
                            st.metric("Avg Search Volume", f"{results_df['search_volume'].mean():,.0f}")
                        with col3:
                            st.metric("Avg Difficulty", f"{results_df['difficulty'].mean():.1f}")
                    
                        csv = results_df.to_csv(index=False)
                        st.download_button(
                            "Download Results",
                            csv,
                            "keyword_analysis_results.csv",
                            "text/csv",
                            key='download-csv'
                        )
                    else:
                        st.warning("No results found for the specified parameters.")
    else:
        st.info("Please enter your SEOmonitor API key and campaign ID to proceed.")

if __name__ == "__main__":
    main()
