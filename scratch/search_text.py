import re

def print_context(path, query):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                if query.lower() in line.lower():
                    print(f"--- {path} line {i+1} ---")
                    start = max(0, i-5)
                    end = min(len(lines), i+15)
                    for j in range(start, end):
                        print(f"{j+1}: {lines[j].rstrip()}")
    except Exception as e:
        print(f"Error {e}")

print_context(r'c:\Users\User\Desktop\Multi-RAG\app.py', '@app.before_request')
