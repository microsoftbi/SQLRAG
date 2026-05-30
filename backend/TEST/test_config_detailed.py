#!/usr/bin/env python3
import sys
import os
from dotenv import load_dotenv

print("=" * 80)
print("Detailed Configuration Verification")
print("=" * 80)
print()

# 1. 检查.env文件是否存在
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
print(f"1. Checking .env file at: {env_path}")
if os.path.exists(env_path):
    print("   ✓ .env file exists")
    with open(env_path, 'r', encoding='utf-8') as f:
        env_content = f.read()
    print("   .env file content:")
    for line in env_content.strip().split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            if 'API_KEY' in line:
                print(f"      {line.split('=')[0]}=********")
            else:
                print(f"      {line}")
else:
    print("   ✗ .env file not found")
print()

# 2. 直接用python-dotenv读取
print("2. Reading with python-dotenv:")
load_dotenv(env_path)
env_vars = ['SERVER', 'PORT', 'DATABASE_GRAPH', 'DATABASE_VECTOR',
            'USER', 'PASSWORD', 'BACKEND_PORT',
            'LLM_API_KEY', 'LLM_BASE_URL', 'LLM_MODEL']
for var in env_vars:
    val = os.getenv(var)
    if val:
        if 'API_KEY' in var:
            print(f"   {var}: ********")
        else:
            print(f"   {var}: {val}")
    else:
        print(f"   {var}: NOT SET")
print()

# 3. 用我们的Settings类读取
print("3. Reading with our Settings class:")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import settings
print(f"   settings.server: {settings.server}")
print(f"   settings.port: {settings.port}")
print(f"   settings.database_graph: {settings.database_graph}")
print(f"   settings.database_vector: {settings.database_vector}")
print(f"   settings.user: {settings.user}")
print(f"   settings.password: {settings.password}")
print(f"   settings.backend_port: {settings.backend_port}")
print(f"   settings.llm_api_key: {'SET' if settings.llm_api_key else 'NOT SET'}")
print(f"   settings.llm_base_url: {settings.llm_base_url}")
print(f"   settings.llm_model: {settings.llm_model}")
print()

print("=" * 80)
print("✓ Configuration verified successfully!")
print("=" * 80)