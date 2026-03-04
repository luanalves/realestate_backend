#!/usr/bin/env python3
"""Fix CPF generation bugs in integration test scripts.
Bug: 8-digit base instead of 9, plus wrong format string."""

import os

fixes = {
    'test_us2_s3_manager_assigns_properties.sh': [
        ('base = "66677788"', 'base = "666777888"'),
        ('base = "77788899"', 'base = "777888990"'),
        ('base = "88899900"', 'base = "888999001"'),
    ],
    'test_us3_s1_agent_assigned_properties.sh': [
        ('base = "33344455"', 'base = "333444557"'),
        ('base = "44455566"', 'base = "444555669"'),
    ],
    'test_us3_s2_agent_auto_assignment.sh': [
        ('base = "55566677"', 'base = "555666778"'),
    ],
    'test_us3_s3_agent_own_leads.sh': [
        ('base = "66677788"', 'base = "666777888"'),
        ('base = "77788899"', 'base = "777888990"'),
    ],
    'test_us3_s4_agent_cannot_modify_others.sh': [
        ('base = "12312312"', 'base = "123123128"'),
        ('base = "98798798"', 'base = "987987989"'),
    ],
    'test_us5_s1_prospector_creates_property.sh': [
        ('base = "11122233"', 'base = "111222337"'),
    ],
}

old_fmt = '{base[6:8]}{d1}-{d2}'
new_fmt = '{base[6:9]}-{d1}{d2}'

total = 0
for filename, replacements in fixes.items():
    filepath = os.path.join(os.path.dirname(__file__), filename)
    with open(filepath, 'r') as f:
        content = f.read()
    
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            total += 1
            print(f"  {filename}: {old} -> {new}")
    
    count = content.count(old_fmt)
    if count > 0:
        content = content.replace(old_fmt, new_fmt)
        total += count
        print(f"  {filename}: fixed {count} format strings")
    
    with open(filepath, 'w') as f:
        f.write(content)

print(f"\nTotal: {total} fixes across {len(fixes)} files")
