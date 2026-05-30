import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')

# Write output to a log file for debugging
log_path = os.path.join(os.path.dirname(__file__), 'upload_test_result.txt')
log = open(log_path, 'w', encoding='utf-8')

try:
    # Test upload
    import urllib.request

    boundary = '----TestBoundary'
    file_content = 'Hello, this is a test document for SQLRAG upload.'.encode('utf-8')

    data_parts = [
        f'--{boundary}'.encode(),
        b'Content-Disposition: form-data; name="file"; filename="test.txt"',
        b'Content-Type: text/plain',
        b'',
        file_content,
        f'--{boundary}--'.encode(),
        b''
    ]
    body = b'\r\n'.join(data_parts)

    req = urllib.request.Request(
        'http://localhost:8798/vector/documents/upload',
        data=body,
        headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
    )

    log.write('Sending upload request...\n')
    resp = urllib.request.urlopen(req, timeout=30)
    log.write(f'Status: {resp.status}\n')
    result = json.loads(resp.read().decode())
    log.write(f'Result: {json.dumps(result, indent=2, ensure_ascii=False)}\n')

    # Now list documents
    req2 = urllib.request.Request('http://localhost:8798/vector/documents')
    resp2 = urllib.request.urlopen(req2, timeout=10)
    docs = json.loads(resp2.read().decode())
    log.write(f'\nDocuments in DB: {len(docs.get("documents", []))}\n')
    for doc in docs.get('documents', []):
        log.write(f'  - [{doc.get("DocumentId")}] {doc.get("Title")}\n')

except Exception as e:
    log.write(f'ERROR: {str(e)}\n')
    import traceback
    traceback.print_exc(file=log)

finally:
    log.close()

print(f'Test complete. Check {log_path} for results')
