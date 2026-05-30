import requests
import json

response = requests.post(
    "http://localhost:8798/graph/qa",
    json={"question": "谁认识方超，同时又和周荣有关系？"}
)

with open('qa_output.txt', 'w', encoding='utf-8') as f:
    f.write(response.json()['answer'])
print("Done")
