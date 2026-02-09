import os

file_path = r'd:\dani_coding\django_gms\templates\gms\homepage.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# The specific split tag causing the error
split_tag = """                <div class="month-calendar" data-month-index="{{ forloop.counter0 }}" {% if forloop.counter0
                    !=current_month_index %}style="display:none;" {% endif %}>"""

# The corrected single-line tag
corrected_tag = """                <div class="month-calendar" data-month-index="{{ forloop.counter0 }}" {% if forloop.counter0 != current_month_index %}style="display:none;"{% endif %}>"""

# Use a more lenient normalization approach
normalized_content = ' '.join(content.split())
normalized_split = ' '.join(split_tag.split())

if split_tag in content:
    print("Found split tag using exact string match!")
    new_content = content.replace(split_tag, corrected_tag)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Fixed homepage.html")
else:
    print("Exact match failed. Trying finding by unique start...")
    start_marker = '<div class="month-calendar" data-month-index="{{ forloop.counter0 }}"'
    start_idx = content.find(start_marker)
    
    if start_idx != -1:
        # Find the closing > of this tag
        # Since it's a div tag opening, we search for >
        end_idx = content.find('>', start_idx)
        
        if end_idx != -1:
            bad_segment = content[start_idx:end_idx+1]
            print(f"Found segment: {bad_segment}")
            
            # Replace with correct one
            new_content = content[:start_idx] + corrected_tag + content[end_idx+1:]
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print("Fixed homepage.html using segment replacement")
        else:
            print("Could not find closing >")
    else:
        print("Could not find start marker")
