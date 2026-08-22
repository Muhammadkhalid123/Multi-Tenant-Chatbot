def find_routes():
    with open(r'c:\Users\User\Desktop\Multi-RAG\app.py', 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if '@app.route' in line:
                print(f"Line {i+1}: {line.strip()}")
            if 'def ' in line and 'chat' in line:
                print(f"Line {i+1}: {line.strip()}")
find_routes()
