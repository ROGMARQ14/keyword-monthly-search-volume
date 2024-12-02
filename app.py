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

def get_keyword_data(api_key, campaign_id, keywords):
    """Fetch keyword data from SEOmonitor API"""
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    # Process keywords in batches
    batch_size = 100
    all_results = []
    
    for i in range(0, len(keywords), batch_size):
        batch = keywords[i:i + batch_size]
        
        # Construct the URL with query parameters
        base_url = f'https://api.seomonitor.com/v3/rank-tracker/v3.0/keywords'
        params = {
            'campaign_id': campaign_id,
            'keyword': ','.join(batch)
        }
        
        try:
            response = requests.get(base_url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and 'data' in data:
                    all_results.extend(data['data'])
                elif isinstance(data, list):
                    all_results.extend(data)
            elif response.status_code == 401:
                raise ValueError("Authentication failed. Please check your API key.")
            elif response.status_code == 404:
                raise ValueError(f"Campaign ID {campaign_id} not found.")
            else:
                raise ValueError(f"Error fetching keyword data: {response.status_code} {response.reason}")
                
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Network error: {str(e)}")
        except ValueError as e:
            raise e
        except Exception as e:
            raise ValueError(f"Unexpected error: {str(e)}")
            
    return all_results

def process_keywords(api_key, campaign_id, keywords):
    """Process keywords and get their search volumes"""
    try:
        results = get_keyword_data(api_key, campaign_id, keywords)
        return process_results(results, keywords)
    except ValueError as e:
        st.error(str(e))
        return None

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
                    # Try to get from search_data
                    if 'volume' in search_data:
                        results_dict[keyword]['search_volume'] = int(search_data['volume'])
                    elif 'search_volume' in search_data:
                        results_dict[keyword]['search_volume'] = int(search_data['search_volume'])
                    elif 'monthly_searches' in search_data:
                        results_dict[keyword]['search_volume'] = int(search_data['monthly_searches'])
                # If not found in search_data, try root level
                elif 'volume' in item:
                    results_dict[keyword]['search_volume'] = int(item['volume'])
                elif 'search_volume' in item:
                    results_dict[keyword]['search_volume'] = int(item['search_volume'])
                elif 'monthly_searches' in item:
                    results_dict[keyword]['search_volume'] = int(item['monthly_searches'])
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
