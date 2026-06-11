from fastapi import APIRouter, Depends
from typing import Dict, Any
import logging
from database import get_vector_db_connection, get_graph_db_connection

router = APIRouter(prefix="/debug", tags=["Debug"])


@router.post("/execute-sql")
async def debug_execute_sql(data: Dict[str, Any], conn=Depends(get_vector_db_connection)):
    """执行 SQL 并返回结果"""
    sql = data.get("sql", "").strip()
    if not sql:
        return {"success": False, "error": "SQL 不能为空"}

    try:
        cursor = conn.cursor()
        cursor.execute(sql)

        columns = [col[0] for col in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        results = [dict(zip(columns, row)) for row in rows]

        return {
            "success": True,
            "columns": columns,
            "rows": results,
            "row_count": len(results),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/call-llm")
async def debug_call_llm(data: Dict[str, Any]):
    """将自定义提示词发送给 LLM 并返回结果"""
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return {"success": False, "error": "提示词不能为空"}

    try:
        from langchain_deepseek import ChatDeepSeek
        from langchain_core.messages import HumanMessage
        from config import settings

        api_key = settings.llm_api_key
        if not api_key:
            raise Exception("LLM_API_KEY not set in .env file")

        llm = ChatDeepSeek(
            model=settings.llm_model,
            api_key=api_key,
            base_url=settings.llm_base_url,
            temperature=0,
            max_tokens=5000,
        )

        messages = [HumanMessage(content=prompt)]
        response = llm.invoke(messages)
        content = response.content

        return {
            "success": True,
            "response": content,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}