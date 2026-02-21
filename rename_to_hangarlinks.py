import os
import re

def replace_in_file(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        updated = re.sub(r'HangarLink(?!s)', 'HangarLinks', content)
        if updated != content:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(updated)
            print(f'Updated: {os.path.basename(path)}')
        else:
            print(f'No change: {os.path.basename(path)}')
    except Exception as e:
        print(f'Error {path}: {e}')

# Key Python/config files
for fpath in [
    r'd:\HangarLink-MVP-2025\app.py',
    r'd:\HangarLink-MVP-2025\config.py',
    r'd:\HangarLink-MVP-2025\routes.py',
    r'd:\HangarLink-MVP-2025\force_reset_db.py',
    r'd:\HangarLink-MVP-2025\README.md',
    r'd:\HangarLink-MVP-2025\static\manifest.json',
]:
    replace_in_file(fpath)

# All templates
templates_dir = r'd:\HangarLink-MVP-2025\templates'
for fname in os.listdir(templates_dir):
    if fname.endswith('.html'):
        replace_in_file(os.path.join(templates_dir, fname))

print('\nAll done!')
