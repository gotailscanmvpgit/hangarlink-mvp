import os
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader('templates'))

for root, _, files in os.walk('templates'):
    for file in files:
        if file.endswith('.html'):
            filepath = os.path.relpath(os.path.join(root, file), 'templates')
            try:
                env.get_template(filepath)
            except Exception as e:
                print(f"Error in {filepath}: {e}")
