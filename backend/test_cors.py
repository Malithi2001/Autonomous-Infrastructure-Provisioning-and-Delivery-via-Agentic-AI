import requests

# Test CORS by making a request to the login endpoint
# This simulates what the frontend would do
try:
    # Test OPTIONS preflight request (what browsers do for CORS)
    headers = {
        'Origin': 'http://localhost:5174',
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'content-type,authorization'
    }

    # First, test the preflight OPTIONS request
    response = requests.options('http://127.0.0.1:8000/api/v1/auth/login', headers=headers)
    print(f'OPTIONS Status: {response.status_code}')
    print(f'OPTIONS Headers: {dict(response.headers)}')

    # Check if CORS headers are present
    cors_headers = {k: v for k, v in response.headers.items() if k.lower().startswith('access-control')}
    print(f'CORS Headers: {cors_headers}')

    # Test actual POST request
    data = {'username': 'test', 'password': 'test'}
    headers = {'Origin': 'http://localhost:5174'}
    response = requests.post('http://127.0.0.1:8000/api/v1/auth/login',
                           json=data, headers=headers, allow_redirects=False)
    print(f'POST Status: {response.status_code}')
    print(f'POST Headers: {dict(response.headers)}')

except Exception as e:
    print(f'Error: {e}')