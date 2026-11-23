import os
import sys
import django
import json

# Add both project root and backend dir so both backend.evaluation and api imports work.
sys.path.insert(0, r"C:\projects\NyaySaathi")
sys.path.insert(0, r"C:\projects\NyaySaathi\backend")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nyayasaathi.settings.development")
django.setup()

from backend.evaluation.runner import run_evaluation_suite

result = run_evaluation_suite()
print(json.dumps(result, indent=2))
