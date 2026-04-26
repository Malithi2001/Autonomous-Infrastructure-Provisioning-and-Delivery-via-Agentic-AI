import requests

try:
    r = requests.get('http://127.0.0.1:8000/health')
    print('Status:', r.status_code)
    print('Response:', r.json())
except Exception as e:
    print('Error:', e)