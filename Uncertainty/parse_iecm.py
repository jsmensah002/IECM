import re, html, csv, os

def clean_path(p):
    p = p.strip().strip("'\"")
    p = p.replace("\\ ", " ").replace("\\'", "'")
    return os.path.expanduser(p)

while True:
    path = clean_path(input("Drag the IECM export into the terminal (or type its path): "))
    if os.path.isfile(path):
        break
    print(f"  Not found: {path}\n  Tip: in Finder, drag the file into this window to paste its full path.\n")

text = html.unescape(open(path, encoding="utf-8", errors="ignore").read())
text = re.sub(r"<[^>]+>", "", text)

section = "Input"
params = []
for block in re.split(r"\n(?=[A-Z0-9].*:)", text):
    if "Output Screens:" in text[:text.find(block)]:
        section = "Output"
    m = re.search(r"^([^\n:]+(?:\([^)]+\))?):\s*\n(?:[^\n]+\n)*?\s*Values:\s*\n((?:\s*[-+\d.eE]+\s*\n)+)", block)
    if m:
        name = f"[{section}] {m.group(1).strip()}"
        vals = [float(x) for x in m.group(2).split()]
        if not any(p[0] == name for p in params):
            params.append((name, vals))

print(f"\nFound {len(params)} parameters in {os.path.basename(path)}:\n")
for idx, (name, _) in enumerate(params, 1):
    print(f"  {idx:3d}. {name}")

def pick(label, s):
    m = re.search(label + r"\s*:?\s*([\d,\s]*)", s, re.I)
    nums = [int(n) for n in re.findall(r"\d+", m.group(1))] if m else []
    return [n for n in nums if 1 <= n <= len(params)]

while True:
    sel = input("\nSelect (e.g. Inputs: 1,2,3; Outputs: 36,40): ")
    in_idx, out_idx = pick("inputs", sel), pick("outputs", sel)
    if in_idx or out_idx:
        break
    print("  Use the format  Inputs: 1,2,3; Outputs: 36,40")

def clean(i):
    return re.sub(r"^\[(Input|Output)\]\s*", "", params[i - 1][0])

in_cols, out_cols = [clean(i) for i in in_idx], [clean(i) for i in out_idx]
cols = in_cols + out_cols
data = [params[i - 1][1] for i in in_idx] + [params[i - 1][1] for i in out_idx]

out_csv = input("Output CSV filename (.csv added if you omit it; default iecm_dataset.csv): ").strip() or "iecm_dataset.csv"
if not out_csv.lower().endswith(".csv"):
    out_csv += ".csv"

with open(out_csv, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(cols)
    for row in zip(*data):
        w.writerow(row)

print(f"\nSaved {len(data[0])} rows x {len(cols)} columns to {out_csv}")
print("\nPaste into your ML script:")
print("input_cols  = " + repr(in_cols))
print("output_cols = " + repr(out_cols))
