import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i in range(417, min(430, len(lines))):
    line = lines[i]
    # Only show printable ASCII and repr for rest
    print(f'{i+1}: {repr(line[:80])}...' if len(line) > 80 else f'{i+1}: {repr(line)}')
