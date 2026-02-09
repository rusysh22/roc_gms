import os

file_path = r'd:\dani_coding\django_gms\templates\gms\homepage.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Define the target split string
target_split = '{% if forloop.counter0\n                    !=current_month_index %}'
# Also try other variations of whitespace
target_split_2 = '{% if forloop.counter0\n                    != current_month_index %}'

replacement = '{% if forloop.counter0 != current_month_index %}'

if target_split in content:
    print("Found split target 1")
    content = content.replace(target_split, replacement)
elif target_split_2 in content:
    print("Found split target 2")
    content = content.replace(target_split_2, replacement)
else:
    # Try regex if exact match fails
    import re
    pattern = r'{% if forloop\.counter0\s+!=\s*current_month_index %}'
    if re.search(pattern, content):
        print("Found matching pattern via regex")
        content = re.sub(pattern, replacement, content)
    else:
        print("Target not found!")
        # Print a snippet to see what's there
        start_idx = content.find('data-month-index')
        if start_idx != -1:
            print("Snippet around data-month-index:")
            print(content[start_idx:start_idx+200])

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("File updated.")
