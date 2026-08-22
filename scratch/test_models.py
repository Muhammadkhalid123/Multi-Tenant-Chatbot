import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

candidates = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.6-27b"]

for model_name in candidates:
    try:
        llm = ChatOpenAI(
            openai_api_base="https://api.groq.com/openai/v1",
            openai_api_key=os.getenv("GROQ_API_KEY"),
            model_name=model_name,
            temperature=0.7,
            model_kwargs={"response_format": {"type": "json_object"}}
        )
        res = llm.invoke('{"question": "Say hello in JSON with key reply"}')
        print(f"[SUCCESS] Model '{model_name}' works! Response: {res.content}")
        break
    except Exception as e:
        print(f"[FAIL] Model '{model_name}': {e}")
