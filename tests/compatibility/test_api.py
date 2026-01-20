import requests
import sys

def test_api():
    try:
        response = requests.get("http://localhost:5000/api/filings/deadline-alerts?days_ahead=30&limit=5")
        print(f"Deadline Alerts Code: {response.status_code}")
        print(f"Deadline Alerts Response: {response.text}")
        
        response = requests.get("http://localhost:5000/api/filings/compliance-report?days_ahead=30&limit=5")
        print(f"Compliance Report Code: {response.status_code}")
        print(f"Compliance Report Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api()
