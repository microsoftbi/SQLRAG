#!/usr/bin/env python3
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings

print("=" * 80)
print("配置文件读取测试")
print("=" * 80)
print()

print("数据库配置：")
print(f"  SERVER: {settings.server}")
print(f"  PORT: {settings.port}")
print(f"  DATABASE_GRAPH: {settings.database_graph}")
print(f"  DATABASE_VECTOR: {settings.database_vector}")
print(f"  USER: {settings.user}")
print(f"  PASSWORD: {settings.password}")
print()

print("后端配置：")
print(f"  BACKEND_PORT: {settings.backend_port}")
print()

print("LLM配置：")
print(f"  LLM_API_KEY: {settings.llm_api_key[:20] if settings.llm_api_key else 'NOT SET'}...")
print(f"  LLM_BASE_URL: {settings.llm_base_url}")
print(f"  LLM_MODEL: {settings.llm_model}")
print()

print("=" * 80)

# 检查LLM配置是否完整
if not settings.llm_api_key:
    print("⚠️  警告：LLM_API_KEY 未设置，请配置 .env 文件")
else:
    print("✅ LLM_API_KEY 已设置")

if settings.llm_base_url == "https://api.deepseek.com/v1":
    print("✅ 使用默认的DeepSeek API端点")

if settings.llm_model == "deepseek-chat":
    print("✅ 使用默认的deepseek-chat模型")

print("=" * 80)