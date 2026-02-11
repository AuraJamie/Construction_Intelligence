import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

# URL from York Open Data for Planning Applications (GeoJSON)
# Dataset ID: 7044d1920639460da3fc4a3fa9273107_5
URL = "https://data-cyc.opendata.arcgis.com/datasets/7044d1920639460da3fc4a3fa9273107_5.geojson"

def inspect_api_structure():
    print("Fetching GeoJSON sample (streaming)...")
    
    # Do a range request or just stream specific bytes to avoid 20MB download if possible?
    # No, let's just fetch, it's open data. But requests doesn't support partial geojson parsing easily.
    # We will fetch queries against the FeatureServer REST API which is vastly more efficient.
    # We need to find the FeatureServer URL.
    # Usually: https://services.arcgis.com/.../FeatureServer/0
    
    # Try to find the FeatureServer url from the 'datasets' page metadata
    # Or just use the query endpoint for the known dataset.
    
    # Let's try querying the specific Feature Service directly if we can guess the ID.
    # A common pattern for York Open Data.
    
    # Backup: Fetch the first few lines of the CSV to get headers? No, we have the CSV.
    # We want the API.
    
    # Let's try fetching the GeoJSON with a limit parameter? GeoJSON endpoint often ignores params.
    # Let's try to query the ArcGIS REST API directly.
    # Search found: "live API link to the City of York Council's (CYC) GIS server"
    
    # Let's try to fetch the query endpoint.
    query_url = "https://services1.arcgis.com/ESVITQSjLdI1tN6U/arcgis/rest/services/Planning_Applications_V2/FeatureServer/0/query"
    params = {
        'where': '1=1',
        'outFields': '*',
        'resultRecordCount': 1,
        'f': 'json'
    }
    
    print(f"Testing Query URL: {query_url}")
    try:
        r = requests.get(query_url, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if 'features' in data and len(data['features']) > 0:
                print("\nSUCCESS! Found REST API.")
                feat = data['features'][0]
                print(json.dumps(feat, indent=2))
                return
            else:
                 print("Response valid but no features/error?", data.keys())
    except Exception as e:
        print(f"Query 1 failed: {e}")

    # Fallback: Try identifying the service URL from the page via scraping? No too complex.
    # Let's just fetch the 1-record element from the GeoJSON if possible?
    # No, let's look at the CSV headers we ALREADY have and map them.
    # CSV headers: DATEAPRECV, DCSTAT, KEYVAL, OBJ, PROPOSAL, LATITUDE, LONGITUDE
    
    print("\n--- Map from CSV Headers ---")
    print("Assuming we can use the CSV download as the 'Sync' source if API fails.")
    print("But let's try one more common URL pattern.")
    
inspect_api_structure()
