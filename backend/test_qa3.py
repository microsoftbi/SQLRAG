import requests

response = requests.post(
    "http://localhost:8798/graph/qa",
    json={"question": "哪些人物同时出现在多个案件中？"}
)

with open('qa_output2.txt', 'w', encoding='utf-8') as f:
    f.write(response.json()['answer'])
print("Done")
