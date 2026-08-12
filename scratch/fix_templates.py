with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Fix layout template
code = code.replace('{% block content %}{% endblock %}', '{content}')

# Replace SUPER_ADMIN_LEADS_HTML = SUPER_ADMIN_LAYOUT + '''\n{% block content %}
# with SUPER_ADMIN_LEADS_HTML = SUPER_ADMIN_LAYOUT.format(content='''

code = code.replace("SUPER_ADMIN_LEADS_HTML = SUPER_ADMIN_LAYOUT + '''\\n{% block content %}", "SUPER_ADMIN_LEADS_HTML = SUPER_ADMIN_LAYOUT.format(content='''")

# The block ends with {% endblock %}\n'''
code = code.replace("{% endblock %}\\n'''", "''')")

code = code.replace("SUPER_ADMIN_BRANDS_HTML = SUPER_ADMIN_LAYOUT + '''\\n{% block content %}", "SUPER_ADMIN_BRANDS_HTML = SUPER_ADMIN_LAYOUT.format(content='''")

# But wait, SUPER_ADMIN_LAYOUT contains many {} due to CSS.
# So using .format() will fail unless we escape them or use .replace().
# Let's switch back to .replace()!

# Reset code
with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

code = code.replace('{% block content %}{% endblock %}', '<!-- CONTENT -->')
code = code.replace("SUPER_ADMIN_LEADS_HTML = SUPER_ADMIN_LAYOUT + '''\\n{% block content %}", "SUPER_ADMIN_LEADS_HTML = SUPER_ADMIN_LAYOUT.replace('<!-- CONTENT -->', '''")
code = code.replace("{% endblock %}\\n'''", "''')")
code = code.replace("SUPER_ADMIN_BRANDS_HTML = SUPER_ADMIN_LAYOUT + '''\\n{% block content %}", "SUPER_ADMIN_BRANDS_HTML = SUPER_ADMIN_LAYOUT.replace('<!-- CONTENT -->', '''")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)
print('Fixed!')
