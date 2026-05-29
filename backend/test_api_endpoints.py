import sys, os, json, http.client, traceback
sys.stdout.reconfigure(encoding='utf-8')

log_path = os.path.join(os.path.dirname(__file__), 'api_test_result.txt')
log = open(log_path, 'w', encoding='utf-8')

def log_print(msg):
    print(msg)
    log.write(msg + '\n')

try:
    # Test 1: Health check
    log_print('=== Test 1: GET / ===')
    conn = http.client.HTTPConnection('localhost', 8798, timeout=10)
    conn.request('GET', '/')
    resp = conn.getresponse()
    log_print(f'Status: {resp.status}')
    log_print(f'Body: {resp.read().decode()}')
    conn.close()

    # Test 2: Upload using multipart form data
    log_print('\n=== Test 2: POST /vector/documents/upload ===')
    boundary = '----FormBoundary7MA4YWxkTrZu0gW'

    file_content = b'Hello, this is a test document for SQLRAG upload.'

    # Build multipart body
    body = b''
    body += b'--' + boundary.encode('ascii') + b'\r\n'
    body += b'Content-Disposition: form-data; name="file"; filename="test_upload.txt"\r\n'
    body += b'Content-Type: text/plain\r\n'
    body += b'\r\n'
    body += file_content + b'\r\n'
    body += b'--' + boundary.encode('ascii') + b'--\r\n'

    headers = {
        'Content-Type': 'multipart/form-data; boundary=' + boundary,
        'Content-Length': str(len(body))
    }

    log_print(f'Sending {len(body)} bytes...')
    log_print(f'Content-Type: multipart/form-data; boundary={boundary}')

    conn = http.client.HTTPConnection('localhost', 8798, timeout=30)
    conn.request('POST', '/vector/documents/upload', body=body, headers=headers)
    resp = conn.getresponse()
    log_print(f'Status: {resp.status}')
    resp_body = resp.read().decode()
    log_print(f'Body: {resp_body}')
    conn.close()

    # Test 3: Verify document was inserted
    log_print('\n=== Test 3: GET /vector/documents ===')
    conn = http.client.HTTPConnection('localhost', 8798, timeout=10)
    conn.request('GET', '/vector/documents')
    resp = conn.getresponse()
    data = json.loads(resp.read().decode())
    log_print(f'Documents count: {len(data.get("documents", []))}')
    for doc in data.get('documents', []):
        log_print(f'  [{doc["DocumentId"]}] {doc["Title"]}')
    conn.close()

except Exception as e:
    log_print(f'ERROR: {e}')
    traceback.print_exc(file=log)

finally:
    log.close()
    log_print(f'\nDone - results in {log_path}')
