#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings

print("=" * 80)
print("Configuration Test")
print("=" * 80)
print()

print("Database Configuration:")
print(f"  SERVER: {settings.server}")
print(f"  PORT: {settings.port}")
print(f"  DATABASE_GRAPH: {settings.database_graph}")
print(f"  DATABASE_VECTOR: {settings.database_vector}")
print(f"  USER: {settings.user}")
print(f"  PASSWORD: {settings.password}")
print()

print("Backend Configuration:")
print(f"  BACKEND_PORT: {settings.backend_port}")
print()

print("LLM Configuration:")
print(f"  LLM_API_KEY: {'SET' if settings.llm_api_key else 'NOT SET'}")
print(f"  LLM_BASE_URL: {settings.llm_base_url}")
print(f"  LLM_MODEL: {settings.llm_model}")
print()

print("=" * 80)