import os
import sys
from jinja2 import Environment, FileSystemLoader, TemplateSyntaxError
from app import create_app

def validate_templates():
    """
    Finds all HTML templates in the templates directory and checks for syntax errors.
    """
    app = create_app()
    template_dir = os.path.join(os.getcwd(), 'templates')
    
    if not os.path.exists(template_dir):
        print(f"❌ Template directory not found at {template_dir}")
        sys.exit(1)

    env = Environment(loader=FileSystemLoader(template_dir))
    
    # Add common Flask/App globals to env if needed for complex parsing
    env.globals.update({
        'url_for': lambda x, **y: f"/{x}",
        'get_flashed_messages': lambda: [],
        'config': app.config,
    })

    success_count = 0
    error_count = 0
    
    print("\n🔍 Validating Jinja2 Template Syntax...")
    print("=" * 50)

    for root, dirs, files in os.walk(template_dir):
        for file in files:
            if file.endswith('.html'):
                relative_path = os.path.relpath(os.path.join(root, file), template_dir)
                try:
                    env.get_template(relative_path)
                    # print(f"✅ {relative_path}")
                    success_count += 1
                except TemplateSyntaxError as e:
                    print(f"❌ SYNTAX ERROR: {relative_path} (Line {e.lineno})")
                    print(f"   Message: {e.message}")
                    print(f"   Source: {e.source}")
                    error_count += 1
                except Exception as e:
                    # Some templates might depend on specific context for loading?
                    # Generally loading shouldn't fail if syntax is OK.
                    print(f"⚠️  WARNING: Could not load {relative_path}: {type(e).__name__}: {str(e)}")
                    # success_count += 1 # Not necessarily a syntax error

    print("=" * 50)
    print(f"📊 SUMMARY: {success_count} passed, {error_count} failed.")

    if error_count > 0:
        print("\n❌ Template validation FAILED!")
        sys.exit(1)
    else:
        print("\n✅ All templates passed syntax check.")

if __name__ == "__main__":
    validate_templates()
