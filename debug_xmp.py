#!/usr/bin/env python3
"""Debug XMP parsing."""

import xml.etree.ElementTree as ET

xmp_path = 'testxmp.NEF.xmp'

tree = ET.parse(xmp_path)
root = tree.getroot()

print("All elements in XMP:")
print("=" * 70)

for elem in root.iter():
    tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
    if elem.text and elem.text.strip():
        print(f"{tag}: {elem.text}")

print("\n" + "=" * 70)
print("Looking for GPS tags:")
print("=" * 70)

for elem in root.iter():
    tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
    if 'GPS' in tag or 'GPS' in str(elem.attrib):
        print(f"Tag: {tag}")
        print(f"  Text: {elem.text}")
        print(f"  Attrib: {elem.attrib}")
