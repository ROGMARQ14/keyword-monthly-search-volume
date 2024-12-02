# SEOmonitor Keyword Analysis Tool

This is a Streamlit-based web application that allows you to analyze keyword data using the SEOmonitor API. You can view search volumes, keyword difficulty, and ranking data for your campaign keywords.

## Features

- Input your SEOmonitor API key and campaign ID
- Optional CSV file upload for specific keywords
- Date range selection for data analysis
- Download results as CSV
- View key metrics including search volume, difficulty, and current rank

## Installation

1. Clone this repository
2. Install the required packages:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the Streamlit app:
```bash
streamlit run app.py
```

2. Enter your SEOmonitor API key and campaign ID
3. (Optional) Upload a CSV file containing keywords
4. Select your desired date range
5. Click "Get Keyword Data" to fetch and analyze the data
6. Download the results as a CSV file if needed

## Required Input Format

If uploading a CSV file, ensure it contains keywords in the first column. The column header name doesn't matter.

## Note

Make sure you have a valid SEOmonitor API key and campaign ID before using the application.
