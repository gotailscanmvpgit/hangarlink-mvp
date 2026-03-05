import traceback
import jinja2
try:
    jinja2.Environment(loader=jinja2.FileSystemLoader('templates')).get_template('listing_detail.html')
except Exception:
    traceback.print_exc()
