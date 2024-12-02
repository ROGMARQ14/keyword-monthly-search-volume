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

def verify_campaign(api_key, campaign_id):
    """Verify if the campaign ID exists"""
    base_url = "https://api.seomonitor.com/v3/campaigns"
    
    headers = {
        'Accept': 'application/json',
        'Authorization': api_key
    }
    
    try:
        response = requests.get(base_url, headers=headers)
        if response.status_code == 401:
            st.error("Authentication failed. Please check your API key.")
            return False
        response.raise_for_status()
        campaigns = response.json()
        st.write("Available campaigns:", campaigns)  # Debug print
        return any(str(campaign.get('campaign_id')) == str(campaign_id) for campaign in campaigns)
    except requests.exceptions.RequestException as e:
        st.error(f"Error verifying campaign: {str(e)}")
        return False

def get_keyword_data_batch(api_key, campaign_id, keywords, start_date=None, end_date=None):
    """Get keyword data from SEOmonitor API"""
    base_url = f"https://api.seomonitor.com/v3/campaigns/{campaign_id}/keywords/search-data"
    
    headers = {
        'Accept': 'application/json',
        'Authorization': api_key
    }
    
    try:
        response = requests.get(base_url, headers=headers)
        if response.status_code == 401:
            st.error("Authentication failed. Please check your API key.")
            return None
        response.raise_for_status()
        data = response.json()
        st.write("API Response:", data)  # Debug print
        return data
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching keyword data: {str(e)}")
        return None

def process_keywords_in_batches(api_key, campaign_id, keywords, start_date=None, end_date=None, batch_size=100):
    """Process keywords in batches"""
    if not verify_campaign(api_key, campaign_id):
        st.error("Invalid campaign ID. Please check your campaign ID and try again.")
        return None
        
    all_results = []
    total_batches = (len(keywords) + batch_size - 1) // batch_size
    
    progress_text = st.empty()
    
    batch_data = get_keyword_data_batch(api_key, campaign_id, keywords, start_date, end_date)
    if batch_data:
        all_results.extend(batch_data.get('keywords', []))
    
    progress_text.empty()
    return all_results

def process_results(data, original_keywords):
    """Process the API results into a DataFrame"""
    # Create a dictionary with all keywords initialized to 0 search volume
    results_dict = {keyword: {'keyword': keyword, 'search_volume': 0} for keyword in original_keywords}
    
    if isinstance(data, dict):
        keyword_data = data.get('keywords', [])
    else:
        keyword_data = data or []
        
    # Update search volumes for keywords found in the API response
    for item in keyword_data:
        try:
            keyword = item.get('keyword', '')
            if keyword in results_dict:
                search_volume = item.get('search_data', {}).get('search_volume', 0)
                if search_volume is not None:
                    results_dict[keyword]['search_volume'] = int(search_volume)
        except (TypeError, ValueError) as e:
            st.warning(f"Error processing keyword {keyword}: {str(e)}")
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
                        all_results = results_data
                        
                        results_df = pd.DataFrame(process_results(all_results, keywords))
                        
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
