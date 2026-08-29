from pathlib import Path
import re
from collections import Counter

text = Path('results/full_report.txt').read_text(encoding='utf-8')
ids = re.findall(r'"case_id": "(case_\d+)"', text)
print(Counter(ids))
print('total_file_size_chars:', len(text))
