import urllib.request, json, os

# Test health check
r = urllib.request.urlopen('http://localhost:8798/', timeout=5)
print('GET /:', r.status, r.read().decode())

# Test upload using proper multipart
boundary = '----TestBoundary'
file_data = b'Hello SQLRAG test content.'

# Build multipart body carefully
body_parts = []
body_parts.append('--' + boundary)
body_parts.append('Content-Disposition: form-data; name="file"; filename="test.txt"')
body_parts.append('Content-Type: text/plain')
body_parts.append('')
body_parts.append(file_data.decode())
body_parts.append('--' + boundary + '--')
body_parts.append('')
body = '\r\n'.join(body_parts).encode('utf-8')

print(f'Sending {len(body)} bytes')
print(f'Body preview: {body[:100]}')

req = urllib.request.Request(
    'http://localhost:8798/vector/documents/upload',
    data=body,
    headers={'Content-Type': 'multipart/form-data; boundary=' + boundary}
)
r = urllib.request.urlopen(req, timeout=30)
print('POST /upload:', r.status, r.read().decode())

# Verify
r = urllib.request.urlopen('http://localhost:8798/vector/documents', timeout=10)
docs = json.loads(r.read())
print(f'Documents in DB: {len(docs.get("documents", []))}')
for d in docs.get('documents', []):
    print(f'  [{d["DocumentId"]}] {d["Title"]}')
