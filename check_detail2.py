import traceback
import jinja2

env = jinja2.Environment(loader=jinja2.FileSystemLoader('templates'))

for filename in ['listing_detail.html', 'insights/optimizer.html']:
    try:
        env.get_template(filename)
    except Exception:
        print(f"--- Error in {filename} ---")
        traceback.print_exc()
