import subprocess, csv, re

rows, y_cols = {}, []

def nums(s):
    return re.findall(r"[-+]?\d*\.\d+|\d+", s)

xlabel = input("Independent variable (X-axis) column name: ").strip() or "x"

while True:
    name = input("Copy the IECM table, then type the dependent column name (or 'done'): ").strip()
    if name.lower() == "done":
        break
    y_cols.append(name)
    lines = subprocess.check_output("pbpaste").decode("utf-8", "ignore").splitlines()
    try:
        start = next(i for i, l in enumerate(lines) if l.strip().lower() == "values:")
    except StopIteration:
        print("  !! no 'Values:' found - did you click Copy Table to Clipboard?")
        y_cols.pop()
        continue
    n, x = 0, None
    for line in lines[start + 1:]:
        f = nums(line)
        if len(f) == 2:
            x = f[1]
        elif len(f) == 1 and x is not None:
            rows.setdefault(x, {})[name] = f[0]
            x, n = None, n + 1
    preview = ", ".join(f"{k}->{v[name]}" for k, v in list(rows.items())[:3])
    print(f"  captured {n} rows for '{name}': {preview} ...")

with open("iecm_surrogate_data.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow([xlabel] + y_cols)
    for x in sorted(rows, key=float):
        w.writerow([x] + [rows[x].get(c, "") for c in y_cols])
print(f"Done! Saved {len(rows)} rows, {len(y_cols)} dependent columns.")
