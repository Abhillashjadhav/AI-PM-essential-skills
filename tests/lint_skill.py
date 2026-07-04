import sys, re, yaml
path = sys.argv[1]
text = open(path).read()
checks = {}
fm = re.match(r'^---\n(.*?)\n---', text, re.S)
checks["frontmatter_parses"] = False
if fm:
    try:
        meta = yaml.safe_load(fm.group(1))
        checks["frontmatter_parses"] = True
        checks["has_name"] = bool(meta.get("name"))
        checks["name_kebab_case"] = bool(re.fullmatch(r'[a-z0-9]+(-[a-z0-9]+)*', meta.get("name","")))
        desc = meta.get("description","")
        checks["has_description"] = bool(desc)
        checks["desc_under_1024_chars"] = len(desc) <= 1024
        checks["desc_has_trigger_phrases"] = "Use this skill when" in desc or "Use when" in desc
        checks["desc_has_negative_trigger"] = "Do NOT" in desc or "Do not" in desc
    except Exception as e:
        pass
checks["body_under_500_lines"] = len(text.splitlines()) <= 500
checks["has_limitations_section"] = "Limitations" in text
for k, v in checks.items():
    print(f"{'PASS' if v else 'FAIL'}  {k}")
sys.exit(0 if all(checks.values()) else 1)
