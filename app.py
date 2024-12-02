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

def get_keyword_ids(api_key, campaign_id, keywords):
    """Get keyword IDs from SEOmonitor API"""
    base_url = "https://api.seomonitor.com/v3/rank-tracker/v3.0/keywords"
    
    headers = {
        'Accept': 'application/json',
        'Authorization': api_key
    }
    
    params = {
        'campaign_id': campaign_id
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
        data = response.json()
        
        # Create a mapping of keyword text to keyword ID
        keyword_map = {}
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    keyword = item.get('keyword', '').lower()
                    keyword_id = item.get('id')
                    if keyword and keyword_id:
                        keyword_map[keyword] = keyword_id
        
        # Get IDs for our target keywords
        keyword_ids = []
        for keyword in keywords:
            keyword_id = keyword_map.get(keyword.lower())
            if keyword_id:
                keyword_ids.append(keyword_id)
                
        return keyword_ids
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching keyword IDs: {str(e)}")
        return None

def get_keyword_data_batch(api_key, campaign_id, keywords, start_date=None, end_date=None):
    """Get keyword data from SEOmonitor API"""
    base_url = "https://api.seomonitor.com/v3/rank-tracker/bulk-traffic-keywords"
    
    headers = {
        'Accept': 'application/json',
        'Authorization': api_key,
        'Content-Type': 'application/json'
    }
    
    # Prepare the request data
    data = {
        'campaign_id': int(campaign_id),
        'keywords': [{'keyword': k} for k in keywords]
    }
    
    try:
        response = requests.post(base_url, headers=headers, json=data)
        
        # Debug the raw response
        st.write(f"Debug - Status Code: {response.status_code}")
        st.write("Debug - Response Headers:", dict(response.headers))
        
        if response.status_code == 401:
            st.error("Authentication failed. Please check your API key.")
            return None
        elif response.status_code == 404:
            st.error("Campaign not found. Please check your campaign ID.")
            return None
            
        response.raise_for_status()
        data = response.json()
        
        # Debug the parsed response
        st.write("Debug - API Response:", data)
        
        # Extract keyword data from response
        if isinstance(data, dict):
            keywords_data = data.get('keywords', [])
            if keywords_data:
                return keywords_data
        return None
        
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching keyword data: {str(e)}")
        if hasattr(e.response, 'text'):
            st.error(f"Response content: {e.response.text}")
        return None

def process_keywords_in_batches(api_key, campaign_id, keywords, start_date=None, end_date=None, batch_size=10):
    """Process keywords in batches"""
    all_results = []
    total_batches = (len(keywords) + batch_size - 1) // batch_size
    
    progress_text = st.empty()
    progress_bar = st.progress(0)
    
    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min((batch_num + 1) * batch_size, len(keywords))
        current_batch = keywords[start_idx:end_idx]
        
        # Update progress
        progress = (batch_num + 1) / total_batches
        progress_text.text(f"Processing batch {batch_num + 1} of {total_batches}...")
        progress_bar.progress(progress)
        
        # Get data for current batch
        batch_data = get_keyword_data_batch(api_key, campaign_id, current_batch, start_date, end_date)
        if batch_data:
            all_results.extend(batch_data)
        
        # Small delay to prevent rate limiting
        time.sleep(0.5)  # Increased delay to be more conservative
    
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
                # Try to get search volume from different possible locations
                search_volume = None
                traffic_data = item.get('traffic_data', {})
                if isinstance(traffic_data, dict):
                    search_volume = traffic_data.get('monthly_searches')
                
                if search_volume is None:
                    search_volume = item.get('monthly_searches')
                
                if search_volume is not None:
                    try:
                        search_volume = int(search_volume)
                        results_dict[keyword]['search_volume'] = search_volume
                    except (TypeError, ValueError):
                        st.write(f"Error converting search volume for keyword '{keyword}': {search_volume}")
                        continue
                
                # Debug: Print items with zero search volume
                if results_dict[keyword]['search_volume'] == 0:
                    st.write(f"Debug - Zero search volume for keyword '{keyword}'. API response item:", item)
        except (TypeError, ValueError) as e:
            st.write(f"Error processing keyword data: {str(e)}")
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
