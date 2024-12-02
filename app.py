import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import time

# Page configuration
st.set_page_config(
    page_title="Keyword Search Volume Tool",
    page_icon="📊",
    layout="wide"
)

def get_keyword_data_batch(api_key, campaign_id, offset=0, start_date=None, end_date=None):
    """Get keyword data from SEOmonitor API"""
    base_url = "https://apigw.seomonitor.com/v3/rank-tracker/v3.0/keywords"
    
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

def process_keywords_in_batches(api_key, campaign_id, keywords, start_date=None, end_date=None, batch_size=100):
    """Process keywords in batches"""
    all_results = []
    keyword_set = {k.lower() for k in keywords}
    
    progress_text = st.empty()
    progress_bar = st.progress(0)
    
    # Initialize offset and total processed
    offset = 0
    total_processed = 0
    max_retries = 10  # Maximum number of empty results before stopping
    empty_results_count = 0
    
    while True:
        progress_text.text(f"Fetching keywords (offset: {offset})...")
        progress_bar.progress(min(total_processed / len(keywords), 1.0))
        
        # Get batch of keywords from the campaign
        batch_data = get_keyword_data_batch(api_key, campaign_id, offset, start_date, end_date)
        
        if not batch_data or not isinstance(batch_data, list) or len(batch_data) == 0:
            empty_results_count += 1
            if empty_results_count >= max_retries:
                break
            offset += batch_size
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
        if len(batch_data) < batch_size:
            break
            
        offset += batch_size
    
    progress_text.empty()
    progress_bar.empty()
    return all_results

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
    st.title("Keyword Search Volume Tool")
    st.markdown("Get search volumes for your keywords using SEOmonitor API")
    
    # Create columns for the form
    col1, col2 = st.columns(2)
    
    with col1:
        # API credentials input
        api_key = st.text_input("SEOmonitor API Key 🔑", type="password")
    
    with col2:
        campaign_id = st.text_input("Campaign ID 📋")
    
    uploaded_file = st.file_uploader("Choose a CSV file with keywords 📁", type="csv")
    
    if api_key and campaign_id and uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            keywords = df.iloc[:, 0].dropna().astype(str).tolist()
            keywords = [k.strip() for k in keywords if k.strip()]  # Clean the keywords
            
            st.info(f"📋 Found {len(keywords):,} keywords in the CSV file")
            
            # Date range selection
            date_col1, date_col2 = st.columns(2)
            with date_col1:
                default_start = datetime.now() - timedelta(days=30)
                start_date = st.date_input("Start Date 📅", default_start, max_value=datetime.now())
            with date_col2:
                end_date = st.date_input("End Date 📅", datetime.now(), min_value=start_date, max_value=datetime.now())
                
            if st.button("Get Search Volumes 🔍"):
                if start_date > end_date:
                    st.error("❌ Start date must be before end date")
                    return
                    
                with st.spinner('🔄 Fetching search volumes...'):
                    results_data = process_keywords_in_batches(
                        api_key=api_key,
                        campaign_id=campaign_id,
                        keywords=keywords,
                        start_date=start_date.strftime('%Y-%m-%d'),
                        end_date=end_date.strftime('%Y-%m-%d')
                    )
                    
                    if results_data is not None:
                        results = process_results(results_data, keywords)
                        results_df = pd.DataFrame(results)
                        
                        st.markdown("### 📊 Results")
                        if not results_df.empty:
                            # Filter out zero search volumes if requested
                            show_zeros = st.checkbox("Show keywords with zero search volume 👁️", value=True)
                            if not show_zeros:
                                results_df = results_df[results_df['search_volume'] > 0]
                            
                            results_df = results_df.sort_values('search_volume', ascending=False)
                            
                            # Show summary statistics
                            st.markdown("### 📈 Summary Statistics")
                            metric_col1, metric_col2, metric_col3 = st.columns(3)
                            with metric_col1:
                                st.metric("Total Keywords 📝", f"{len(results_df):,}")
                            with metric_col2:
                                st.metric("Avg Search Volume 🔍", f"{results_df['search_volume'].mean():,.0f}")
                            with metric_col3:
                                st.metric("Total Search Volume 📊", f"{results_df['search_volume'].sum():,.0f}")
                            
                            # Display dataframe
                            st.dataframe(
                                results_df.style.format({
                                    'search_volume': '{:,.0f}'
                                }),
                                height=400
                            )
                            
                            # Download button
                            csv = results_df.to_csv(index=False)
                            st.download_button(
                                "⬇️ Download Results",
                                csv,
                                "keyword_search_volumes.csv",
                                "text/csv",
                                help="Download the results as a CSV file"
                            )
                        else:
                            st.warning("⚠️ No results found for the specified parameters.")
        except Exception as e:
            st.error(f"❌ Error processing CSV file: {str(e)}")
    else:
        st.info("ℹ️ Please upload a CSV file and enter your SEOmonitor credentials to proceed.")

if __name__ == "__main__":
    main()
