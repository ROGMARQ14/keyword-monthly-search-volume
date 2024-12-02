import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import time
import base64

# Page configuration
st.set_page_config(
    page_title="Keyword Search Volume Tool",
    page_icon="",
    layout="wide"
)

def get_keyword_data_batch(api_key, campaign_id, keywords, start_date=None, end_date=None):
    """Get keyword data from SEOmonitor API"""
    base_url = "https://apigw.seomonitor.com/v3/rank-tracker/v3.0/keywords"
    
    headers = {
        'Accept': 'application/json',
        'Authorization': api_key
    }
    
    params = {
        'campaign_id': campaign_id,
        'start_date': start_date or (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
        'end_date': end_date or datetime.now().strftime('%Y-%m-%d'),
        'keywords': ','.join(keywords)  # Send keywords as comma-separated list
    }
    
    try:
        response = requests.get(base_url, headers=headers, params=params)
        if response.status_code == 401:
            st.error("Authentication failed. Please check your API key.")
            return None
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching keyword data: {str(e)}")
        return None

def process_keywords_in_batches(api_key, campaign_id, keywords, start_date=None, end_date=None, batch_size=100):
    """Process keywords in batches"""
    all_results = []
    total_batches = (len(keywords) + batch_size - 1) // batch_size
    
    progress_text = st.empty()
    
    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min((batch_num + 1) * batch_size, len(keywords))
        current_batch = keywords[start_idx:end_idx]
        
        progress_text.text(f"Processing batch {batch_num + 1}/{total_batches} (keywords {start_idx + 1}-{end_idx})...")
        
        batch_data = get_keyword_data_batch(api_key, campaign_id, current_batch, start_date, end_date)
        if batch_data and isinstance(batch_data, list):
            all_results.extend(batch_data)
        
        time.sleep(0.1)  # Small delay to prevent rate limiting
    
    progress_text.empty()
    return all_results

def process_results(data, original_keywords):
    """Process the API results into a DataFrame"""
    # Create a dictionary with all keywords initialized to 0 search volume
    results_dict = {keyword: {'keyword': keyword, 'search_volume': 0} for keyword in original_keywords}
    
    # Update search volumes for keywords found in the API response
    for item in data:
        try:
            keyword = item.get('keyword', '')
            if keyword in results_dict:
                search_data = item.get('search_data', {}) or {}
                results_dict[keyword]['search_volume'] = int(search_data.get('search_volume', 0) or 0)
        except (TypeError, ValueError) as e:
            st.warning(f"Error processing keyword {item.get('keyword', 'unknown')}: {str(e)}")
            continue
    
    return list(results_dict.values())

def main():
    st.title("Keyword Search Volume Tool")
    st.markdown("Get search volumes for your keywords using SEOmonitor API")
    
    # Create columns for the form
    col1, col2 = st.columns(2)
    
    with col1:
        # API credentials input
        api_key = st.text_input("SEOmonitor API Key ", type="password")
    
    with col2:
        campaign_id = st.text_input("Campaign ID ")
    
    uploaded_file = st.file_uploader("Choose a CSV file with keywords ", type="csv")
    
    if api_key and campaign_id and uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            keywords = df.iloc[:, 0].dropna().astype(str).tolist()
            keywords = [k.strip() for k in keywords if k.strip()]  # Clean the keywords
            
            st.info(f" Found {len(keywords):,} keywords in the CSV file")
            
            # Date range selection
            date_col1, date_col2 = st.columns(2)
            with date_col1:
                default_start = datetime.now() - timedelta(days=30)
                start_date = st.date_input("Start Date ", default_start, max_value=datetime.now())
            with date_col2:
                end_date = st.date_input("End Date ", datetime.now(), min_value=start_date, max_value=datetime.now())
                
            if st.button("Get Search Volumes "):
                if start_date > end_date:
                    st.error(" Start date must be before end date")
                    return
                    
                with st.spinner(' Fetching search volumes...'):
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
                        
                        st.markdown("###  Results")
                        if not results_df.empty:
                            # Filter out zero search volumes if requested
                            show_zeros = st.checkbox("Show keywords with zero search volume ", value=True)
                            if not show_zeros:
                                results_df = results_df[results_df['search_volume'] > 0]
                            
                            results_df = results_df.sort_values('search_volume', ascending=False)
                            
                            # Show summary statistics
                            st.markdown("###  Summary Statistics")
                            metric_col1, metric_col2, metric_col3 = st.columns(3)
                            with metric_col1:
                                st.metric("Total Keywords ", f"{len(results_df):,}")
                            with metric_col2:
                                st.metric("Avg Search Volume ", f"{results_df['search_volume'].mean():,.0f}")
                            with metric_col3:
                                st.metric("Total Search Volume ", f"{results_df['search_volume'].sum():,.0f}")
                            
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
                                " Download Results",
                                csv,
                                "keyword_search_volumes.csv",
                                "text/csv",
                                key='download-csv',
                                help="Download the results as a CSV file"
                            )
                        else:
                            st.warning(" No results found for the specified parameters.")
        except Exception as e:
            st.error(f" Error processing CSV file: {str(e)}")
    else:
        st.info(" Please upload a CSV file and enter your SEOmonitor credentials to proceed.")

if __name__ == "__main__":
    main()
