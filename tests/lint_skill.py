import sys, re, yaml
path = sys.argv[1]
with open(path, encoding="utf-8") as source:
    text = source.read()
checks = dict.fromkeys((
    "frontmatter_parses", "has_name", "name_kebab_case", "has_description",
    "desc_under_1024_chars", "desc_has_trigger_phrases", "desc_has_negative_trigger",
), False)
fm = re.match(r'^---\n(.*?)\n---', text, re.S)
if fm:
    try:
        meta = yaml.safe_load(fm.group(1))
        if isinstance(meta, dict):
            checks["frontmatter_parses"] = True
            name = meta.get("name")
            if isinstance(name, str):
                checks["has_name"] = bool(name)
                checks["name_kebab_case"] = bool(re.fullmatch(r'[a-z0-9]+(-[a-z0-9]+)*', name))
            desc = meta.get("description")
            if isinstance(desc, str):
                checks["has_description"] = bool(desc)
                checks["desc_under_1024_chars"] = len(desc) <= 1024
                checks["desc_has_trigger_phrases"] = "Use this skill when" in desc or "Use when" in desc
                checks["desc_has_negative_trigger"] = "Do NOT" in desc or "Do not" in desc
    except Exception:
        pass
checks["body_under_500_lines"] = len(text.splitlines()) <= 500
checks["has_limitations_section"] = "Limitations" in text
for k, v in checks.items():
    print(f"{'PASS' if v else 'FAIL'}  {k}")
sys.exit(0 if all(checks.values()) else 1)
