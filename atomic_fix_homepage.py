import os

file_path = r'd:\dani_coding\django_gms\templates\gms\homepage.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix Split Tag at line 1002-1003
old_split_tag = """                <div class="month-calendar" data-month-index="{{ forloop.counter0 }}" {% if forloop.counter0
                    !=current_month_index %}style="display:none;" {% endif %}>"""
                    
new_split_tag = """                <div class="month-calendar" data-month-index="{{ forloop.counter0 }}" {% if forloop.counter0 != current_month_index %}style="display:none;"{% endif %}>"""

if old_split_tag in content:
    content = content.replace(old_split_tag, new_split_tag)
    print("Fixed split tag at lines 1002-1003")
else:
    print("WARNING: Could not find exact match for split tag at 1002-1003. Trying loose match...")
    # Robust fallback: find the surrounding context
    start_marker = 'data-month-index="{{ forloop.counter0 }}"'
    end_marker = 'style="display:none;"'
    
    start_idx = content.find(start_marker)
    if start_idx != -1:
        # Find the closing > near this
        tag_end = content.find('>', start_idx)
        if tag_end != -1:
            segment = content[start_idx:tag_end+1]
            if '{% if' in segment and 'endif' in segment: # Confirm it's the right place
                print(f"Found segment to replace: {segment}")
                # Construct clean segment
                clean_segment = 'data-month-index="{{ forloop.counter0 }}" {% if forloop.counter0 != current_month_index %}style="display:none;"{% endif %}>'
                
                # Replace just this part in the whole file
                # We need to be careful to replace the *whole* div open tag line
                div_start = content.rfind('<div', 0, start_idx)
                if div_start != -1:
                    full_bad_tag = content[div_start:tag_end+1]
                    clean_tag = '<div class="month-calendar" ' + clean_segment
                    content = content.replace(full_bad_tag, clean_tag)
                    print("Fixed split tag via segment replacement")


# 2. Fix Visual Bug at line 1032 (missing <span and split tag)
# The bad content looks like:
#                                 class="text-sm font-medium {% if day_info.is_today %}text-blue-600 dark:text-blue-400{%
#                                 else %}text-gray-900 dark:text-gray-300{% endif %}">{{ day_info.day }}</span>

# We search for the distinctive end part "</span>" and the start "class="text-sm..."
bad_visual_part_start = 'class="text-sm font-medium {% if day_info.is_today %}text-blue-600 dark:text-blue-400{%'
bad_visual_part_end = '{{ day_info.day }}</span>'

if bad_visual_part_start in content:
    print("Found bad visual bug part (exact match start)")
    
    # Check if it spans two lines as expected
    split_index = content.find(bad_visual_part_start)
    end_index = content.find(bad_visual_part_end, split_index)
    
    if end_index != -1:
        full_bad_visual = content[split_index:end_index + len(bad_visual_part_end)]
        print(f"Replacing visual bug block:\n{full_bad_visual}")
        
        fixed_visual = '<span class="text-sm font-medium {% if day_info.is_today %}text-blue-600 dark:text-blue-400{% else %}text-gray-900 dark:text-gray-300{% endif %}">{{ day_info.day }}</span>'
        
        content = content.replace(full_bad_visual, fixed_visual)
        print("Fixed visual bug at line 1032")
else:
    print("Could not find exact match for visual bug. Trying loose match...")
    # Loose match strategy
    loose_marker = 'class="text-sm font-medium {% if day_info.is_today %}'
    idx = content.find(loose_marker)
    if idx != -1:
        # Check if preceding char is NOT <span
        # Actually in the bad case, it's inside a div, so preceding might be whitespace
        preceding = content[idx-10:idx]
        if '<span' not in preceding:
            print("Found malformed class definition without span tag.")
            # Find the end of this span
            end_span = content.find('</span>', idx)
            if end_span != -1:
                bad_segment = content[idx:end_span+7] # +7 for </span>
                print(f"Bad segment: {bad_segment}")
                
                # Normalize spaces to construct replacement
                clean_segment = '<span ' + ' '.join(bad_segment.split())
                content = content.replace(bad_segment, clean_segment)
                print("Fixed visual bug via loose match")

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Saved homepage.html with all fixes.")
