#!/usr/bin/env python3
"""
iecm_surrogates.py — automated surrogate pipeline for IECM uncertainty datasets.

Run it from INSIDE the folder you want the outputs in, e.g.:
    cd ~/Desktop && mkdir IGCC_CO2_Removed && cd IGCC_CO2_Removed
    python3 ~/Desktop/iecm_surrogates.py

It asks for a CSV and the input/target columns (parse_iecm style), then for ONE
target: cleans the data, trains 6 models, writes a metrics .xlsx, auto-picks the
best tree (SHAP) and best smooth model (Pyomo) by overall metric rank (you can
override), saves SHAP PNGs, the smooth model (.pkl) + equation (.json), and a
full re-runnable notebook (.ipynb). All outputs go to the current folder.
"""

import os, re, sys, json, shutil
import numpy as np, pandas as pd, joblib
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.svm import SVR
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler, PolynomialFeatures
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, mean_squared_error
from xgboost import XGBRegressor

RANDOM_STATE = 42
TEST_SIZE = 0.20

# variable name each model gets in the generated notebook
VARNAME = {"Linear Regression": "best_reg", "SVR": "best_svr", "Random Forest": "best_rfr",
           "XGBoost": "best_xgb", "Gradient Boost": "best_gbr", "Polynomial": "best_poly"}


# ---------- input helpers ----------
def ask(prompt):
    raw = input(prompt).strip().strip('"').strip("'").replace("\\ ", " ")
    return raw.strip()

def parse_columns(spec, ncols):            # '1-5' or '1,2,3' -> 0-based indices
    spec = spec.replace(",", " ").strip(); idx = []
    for tok in spec.split():
        if "-" in tok:
            a, b = tok.split("-"); idx.extend(range(int(a), int(b) + 1))
        else:
            idx.append(int(tok))
    idx = [i - 1 for i in idx]
    for i in idx:
        if i < 0 or i >= ncols:
            raise ValueError(f"column {i+1} out of range (file has {ncols} columns)")
    return idx

def parse_targets(spec, ncols):
    # Each target column is wrapped in its own [ ] so you can list SEVERAL targets in
    # one run and the pipeline trains each separately, saving its own .ipynb + .xlsx.
    # e.g. [4][5][6] -> three separate targets (columns 4, 5, 6). A plain '6' still
    # works for a single target. The [ ] simply mark where one target ends and the
    # next begins, so multi-digit columns like [10][11] stay unambiguous.
    found = re.findall(r"\[\s*(\d+)\s*\]", spec)
    idx = [int(n) - 1 for n in found] if found else parse_columns(spec, ncols)
    for i in idx:
        if i < 0 or i >= ncols:
            raise ValueError(f"column {i+1} out of range (file has {ncols} columns)")
    if not idx:
        raise ValueError("no target columns given")
    return idx

def short_target_name(col):
    name = col.split(":")[-1]
    name = re.sub(r"\(.*?\)", "", name).replace("&", "and")
    return re.sub(r"[^0-9A-Za-z]+", "_", name).strip("_")

def plant_from_filename(path):
    base = os.path.basename(path)
    return base.split("_")[0] if "_" in base else os.path.splitext(base)[0]

def fmt(v): return f"{v:.4f}"


# ---------- models (exact grids) ----------
def build_models():
    return {
        "Linear Regression": (Pipeline([("scaler", StandardScaler()), ("reg", LinearRegression())]), {}),
        "SVR": (Pipeline([("scaler", StandardScaler()), ("svr", SVR())]),
                {"svr__kernel": ["linear", "rbf"], "svr__C": [0.01, 0.1, 1, 10, 100], "svr__gamma": ["scale"]}),
        "Random Forest": (RandomForestRegressor(random_state=RANDOM_STATE),
                {"n_estimators": [100, 300], "max_depth": [None, 5, 10, 20],
                 "min_samples_split": [2, 5, 10], "min_samples_leaf": [1, 2, 4],
                 "max_features": ["sqrt", 0.5, 0.7]}),
        "XGBoost": (XGBRegressor(random_state=RANDOM_STATE),
                {"n_estimators": [100, 300], "max_depth": [3, 6, 10],
                 "learning_rate": [0.01, 0.1, 0.3], "subsample": [0.8, 1.0], "colsample_bytree": [0.8, 1.0]}),
        "Gradient Boost": (GradientBoostingRegressor(random_state=RANDOM_STATE),
                {"n_estimators": [100, 300], "max_depth": [3, 6, 10],
                 "learning_rate": [0.01, 0.1, 0.3], "subsample": [0.8, 1.0], "max_features": [0.8, 1.0]}),
        "Polynomial": (Pipeline([("poly", PolynomialFeatures(include_bias=False)),
                 ("scaler", StandardScaler()), ("reg", LinearRegression())]), {"poly__degree": [2, 3]}),
    }

def fit_all(x_train, y_train):
    fitted = {}
    for name, (est, grid) in build_models().items():
        print(f"  training {name} ...", flush=True)
        s = GridSearchCV(est, grid, cv=5, scoring="r2", n_jobs=-1); s.fit(x_train, y_train)
        fitted[name] = s.best_estimator_
    return fitted

def metrics_row(name, model, experiment, xtr, ytr, xte, yte):
    yp = model.predict(xte)
    return {"Experiment": experiment, "Model": name,
            "Train R2": round(model.score(xtr, ytr), 4), "Test R2": round(model.score(xte, yte), 4),
            "MAE": round(mean_absolute_error(yte, yp), 4), "MSE": round(mean_squared_error(yte, yp), 4),
            "RMSE": round(np.sqrt(mean_squared_error(yte, yp)), 4),
            "MAPE (%)": round(np.mean(np.abs((yte - yp) / yte)) * 100, 4)}


# ---------- selection: whichever model wins across all metrics (rank aggregate) ----------
def _rank_pick(rows, group):
    cand = [r for r in rows if r["Model"] in group]
    gap = {r["Model"]: abs(r["Train R2"] - r["Test R2"]) for r in cand}
    crits = [(lambda r: r["Test R2"], True),          # higher better
             (lambda r: r["RMSE"], False),            # lower better
             (lambda r: r["MSE"], False),
             (lambda r: r["MAE"], False),
             (lambda r: r["MAPE (%)"], False),
             (lambda r: gap[r["Model"]], False)]      # smaller train-test gap better
    score = {r["Model"]: 0 for r in cand}
    for keyf, higher in crits:
        for rank, r in enumerate(sorted(cand, key=keyf, reverse=higher)):
            score[r["Model"]] += rank                 # 0 = best on that metric
    return min(cand, key=lambda r: (score[r["Model"]], -r["Test R2"]))["Model"]

def auto_pick_tree(rows):
    return _rank_pick(rows, {"Random Forest", "XGBoost", "Gradient Boost"})

def auto_pick_smooth(rows):
    return _rank_pick(rows, {"Linear Regression", "Polynomial"})

def confirm_pick(kind, auto_name, numbered):
    print(f"\nAuto-pick for {kind}: {auto_name}")
    c = input("  press Enter to accept, or type the model number to override: ").strip()
    if c == "": return auto_name
    if c not in numbered: print("  invalid number, keeping auto-pick."); return auto_name
    return numbered[c]


# ---------- saving: SHAP + equation ----------
def save_shap(tree_model, x_test, outdir, base):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt, shap
    explainer = shap.TreeExplainer(tree_model); sv = explainer.shap_values(x_test)
    shap.summary_plot(sv, x_test, plot_type="bar", show=False)
    plt.savefig(os.path.join(outdir, f"{base}_bar.png"), dpi=150, bbox_inches="tight"); plt.close()
    shap.summary_plot(sv, x_test, show=False)
    plt.savefig(os.path.join(outdir, f"{base}_beeswarm.png"), dpi=150, bbox_inches="tight"); plt.close()
    for i in np.argsort(np.abs(sv).mean(axis=0))[::-1][:2]:
        feat = x_test.columns[i]; shap.dependence_plot(feat, sv, x_test, show=False)
        slug = re.sub(r"[^0-9A-Za-z]+", "_", feat).strip("_")
        plt.savefig(os.path.join(outdir, f"{base}_dependence_{slug}.png"), dpi=150, bbox_inches="tight"); plt.close()

def save_equation(name, model, x, x_test, outdir, base):
    feat = list(x.columns)
    if name == "Polynomial":
        joblib.dump(model, os.path.join(outdir, f"{base}_poly.pkl"))
        poly, scaler, reg = model.named_steps["poly"], model.named_steps["scaler"], model.named_steps["reg"]
        coef = reg.coef_ / scaler.scale_
        intercept = reg.intercept_ - np.sum(reg.coef_ * scaler.mean_ / scaler.scale_)
        terms = [{"coef": float(c), "powers": {feat[j]: int(p[j]) for j in range(len(feat)) if p[j] > 0}}
                 for p, c in zip(poly.powers_, coef)]
        eq = {"intercept": float(intercept), "degree": int(poly.degree), "terms": terms}
        P = poly.transform(x_test.values)
        assert np.allclose(intercept + P @ coef, model.predict(x_test)), "poly equation mismatch!"
        path = os.path.join(outdir, f"{base}_poly_eq.json")
    else:
        joblib.dump(model, os.path.join(outdir, f"{base}_linear.pkl"))
        scaler, reg = model.named_steps["scaler"], model.named_steps["reg"]
        coef = reg.coef_ / scaler.scale_
        intercept = reg.intercept_ - np.sum(reg.coef_ * scaler.mean_ / scaler.scale_)
        eq = {"intercept": float(intercept), "coefficients": {feat[i]: float(coef[i]) for i in range(len(feat))}}
        assert np.allclose(intercept + x_test.values @ coef, model.predict(x_test)), "linear equation mismatch!"
        path = os.path.join(outdir, f"{base}_linear_eq.json")
    with open(path, "w") as f: json.dump(eq, f, indent=2)
    return os.path.basename(path)


# ---------- full re-runnable notebook ----------
MODEL_CELLS = {
 "Linear Regression":
"""# Linear Regression
reg_pipe = Pipeline([('scaler', StandardScaler()), ('reg', LinearRegression())])
reg_grid = GridSearchCV(reg_pipe, {}, cv=5, scoring='r2', n_jobs=-1)
reg_grid.fit(x_train, y_train)
best_reg = reg_grid.best_estimator_
print("Linear Regression best params:", reg_grid.best_params_)
print('Train R2:', best_reg.score(x_train, y_train))
print('Test R2:', best_reg.score(x_test, y_test))""",
 "SVR":
"""# SVR
svr_pipe = Pipeline([('scaler', StandardScaler()), ('svr', SVR())])
svr_grid = GridSearchCV(svr_pipe,
    {'svr__kernel': ['linear', 'rbf'], 'svr__C': [0.01, 0.1, 1, 10, 100], 'svr__gamma': ['scale']},
    cv=5, scoring='r2', n_jobs=-1)
svr_grid.fit(x_train, y_train)
best_svr = svr_grid.best_estimator_
print("SVR best params:", svr_grid.best_params_)
print('Train R2:', best_svr.score(x_train, y_train))
print('Test R2:', best_svr.score(x_test, y_test))""",
 "Random Forest":
"""# Random Forest Regressor
rfr_grid = GridSearchCV(RandomForestRegressor(random_state=42),
    {'n_estimators': [100, 300], 'max_depth': [None, 5, 10, 20],
     'min_samples_split': [2, 5, 10], 'min_samples_leaf': [1, 2, 4],
     'max_features': ['sqrt', 0.5, 0.7]},
    cv=5, scoring='r2', n_jobs=-1)
rfr_grid.fit(x_train, y_train)
best_rfr = rfr_grid.best_estimator_
print("RF best params:", rfr_grid.best_params_)
print('Train R2:', best_rfr.score(x_train, y_train))
print('Test R2:', best_rfr.score(x_test, y_test))""",
 "XGBoost":
"""# XGBoost Regressor
xgb_grid = GridSearchCV(XGBRegressor(random_state=42),
    {'n_estimators': [100, 300], 'max_depth': [3, 6, 10],
     'learning_rate': [0.01, 0.1, 0.3], 'subsample': [0.8, 1.0], 'colsample_bytree': [0.8, 1.0]},
    cv=5, scoring='r2', n_jobs=-1)
xgb_grid.fit(x_train, y_train)
best_xgb = xgb_grid.best_estimator_
print("XGBoost best params:", xgb_grid.best_params_)
print('Train R2:', best_xgb.score(x_train, y_train))
print('Test R2:', best_xgb.score(x_test, y_test))""",
 "Gradient Boost":
"""# Gradient Boosting Regressor
gbr_grid = GridSearchCV(GradientBoostingRegressor(random_state=42),
    {'n_estimators': [100, 300], 'max_depth': [3, 6, 10],
     'learning_rate': [0.01, 0.1, 0.3], 'subsample': [0.8, 1.0], 'max_features': [0.8, 1.0]},
    cv=5, scoring='r2', n_jobs=-1)
gbr_grid.fit(x_train, y_train)
best_gbr = gbr_grid.best_estimator_
print("Gradient Boosting best params:", gbr_grid.best_params_)
print('Train R2:', best_gbr.score(x_train, y_train))
print('Test R2:', best_gbr.score(x_test, y_test))""",
 "Polynomial":
"""# Polynomial
poly_pipe = Pipeline([('poly', PolynomialFeatures(include_bias=False)),
                      ('scaler', StandardScaler()), ('reg', LinearRegression())])
poly_grid = GridSearchCV(poly_pipe, {'poly__degree': [2, 3]}, cv=5, scoring='r2', n_jobs=-1)
poly_grid.fit(x_train, y_train)
best_poly = poly_grid.best_estimator_
print("Polynomial best params:", poly_grid.best_params_)
print('Train R2:', best_poly.score(x_train, y_train))
print('Test R2:', best_poly.score(x_test, y_test))""",
}

def _shap_cell(tree_name):
    v = VARNAME[tree_name]
    return (f"# SHAP on the chosen tree model: {tree_name}\n"
            "import shap, numpy as np\n"
            f"explainer   = shap.TreeExplainer({v})\n"
            f"shap_values = explainer.shap_values(x_test)\n"
            "shap.summary_plot(shap_values, x_test, plot_type='bar')\n"
            "shap.summary_plot(shap_values, x_test)\n"
            "mean_abs = np.abs(shap_values).mean(axis=0)\n"
            "order    = np.argsort(mean_abs)[::-1]\n"
            "for i in order[:2]:\n"
            "    print('Dependence plot for:', x_test.columns[i])\n"
            "    shap.dependence_plot(x_test.columns[i], shap_values, x_test)")

def _pyomo_cell(smooth_name, base):
    if smooth_name == "Polynomial":
        return (f"# Save the chosen smooth model ({smooth_name}) for Pyomo\n"
                "import numpy as np, json, joblib\n"
                f'joblib.dump(best_poly, "{base}_poly.pkl")\n'
                "poly, scaler, reg = best_poly.named_steps['poly'], best_poly.named_steps['scaler'], best_poly.named_steps['reg']\n"
                "coef_real = reg.coef_ / scaler.scale_\n"
                "intercept_real = reg.intercept_ - np.sum(reg.coef_ * scaler.mean_ / scaler.scale_)\n"
                "feature_names = list(x.columns)\n"
                "terms = [{'coef': float(c),\n"
                "          'powers': {feature_names[j]: int(p[j]) for j in range(len(feature_names)) if p[j] > 0}}\n"
                "         for p, c in zip(poly.powers_, coef_real)]\n"
                "equation = {'intercept': float(intercept_real), 'degree': int(poly.degree), 'terms': terms}\n"
                "P = poly.transform(x_test.values)\n"
                "assert np.allclose(intercept_real + P @ coef_real, best_poly.predict(x_test)), 'mismatch!'\n"
                f'json.dump(equation, open("{base}_poly_eq.json", "w"), indent=2)\n'
                "print('saved. degree', equation['degree'], 'terms', len(terms))")
    return (f"# Save the chosen smooth model ({smooth_name}) for Pyomo\n"
            "import numpy as np, json, joblib\n"
            f'joblib.dump(best_reg, "{base}_linear.pkl")\n'
            "scaler, reg = best_reg.named_steps['scaler'], best_reg.named_steps['reg']\n"
            "coef_real = reg.coef_ / scaler.scale_\n"
            "intercept_real = reg.intercept_ - np.sum(reg.coef_ * scaler.mean_ / scaler.scale_)\n"
            "feature_names = list(x.columns)\n"
            "equation = {'intercept': float(intercept_real),\n"
            "            'coefficients': {feature_names[i]: float(coef_real[i]) for i in range(len(feature_names))}}\n"
            "assert np.allclose(intercept_real + x_test.values @ coef_real, best_reg.predict(x_test)), 'mismatch!'\n"
            f'json.dump(equation, open("{base}_linear_eq.json", "w"), indent=2)\n'
            "print('saved. intercept', equation['intercept'])")

def save_notebook(outdir, base, csv_name, input_cols, target_col, tree_name, smooth_name):
    import nbformat as nbf
    inputs_repr = "[\n    " + ",\n    ".join(repr(c) for c in input_cols) + "\n]"
    cells = [
        f'import pandas as pd\ndf = pd.read_csv("{csv_name}")\ndf',
        'df.isna().sum()',
        'df.duplicated().sum()',
        f'x = df[{inputs_repr}]\ny = df[{target_col!r}]',
        ('from sklearn.model_selection import GridSearchCV, train_test_split\n'
         'from sklearn.linear_model import LinearRegression\nfrom sklearn.svm import SVR\n'
         'from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor\n'
         'from sklearn.preprocessing import StandardScaler, PolynomialFeatures\n'
         'from sklearn.pipeline import Pipeline\nfrom xgboost import XGBRegressor\n'
         'x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)'),
        MODEL_CELLS["Linear Regression"], MODEL_CELLS["SVR"], MODEL_CELLS["Random Forest"],
        MODEL_CELLS["XGBoost"], MODEL_CELLS["Gradient Boost"], MODEL_CELLS["Polynomial"],
        # metrics table
        ("import numpy as np\nfrom sklearn.metrics import mean_absolute_error, mean_squared_error\n"
         "models = {'Linear Regression': best_reg, 'SVR': best_svr, 'Random Forest': best_rfr,\n"
         "          'XGBoost': best_xgb, 'Gradient Boost': best_gbr, 'Polynomial': best_poly}\n"
         "rows = []\n"
         "for name, m in models.items():\n"
         "    yp = m.predict(x_test)\n"
         f"    rows.append({{'Experiment': '{base}', 'Model': name,\n"
         "        'Train R2': round(m.score(x_train, y_train), 4), 'Test R2': round(m.score(x_test, y_test), 4),\n"
         "        'MAE': round(mean_absolute_error(y_test, yp), 4), 'MSE': round(mean_squared_error(y_test, yp), 4),\n"
         "        'RMSE': round(np.sqrt(mean_squared_error(y_test, yp)), 4),\n"
         "        'MAPE (%)': round(np.mean(np.abs((y_test - yp) / y_test)) * 100, 4)})\n"
         "results_df = pd.DataFrame(rows)\n"
         f'results_df.to_excel("{base}.xlsx", index=False)\n'
         "results_df"),
        _shap_cell(tree_name),
        _pyomo_cell(smooth_name, base),
    ]
    nb = nbf.v4.new_notebook()
    nb.cells = [nbf.v4.new_code_cell(c) for c in cells]
    with open(os.path.join(outdir, f"{base}.ipynb"), "w") as f:
        nbf.write(nb, f)


# ---------- run ----------
def run(csv_path, input_cols, target_col):
    df = pd.read_csv(csv_path).dropna(how="all").reset_index(drop=True)
    nulls = int(df[input_cols + [target_col]].isna().sum().sum())
    if nulls > 0:
        print(f"\nERROR: {nulls} null value(s) in selected columns. Fix the dataset and re-run."); sys.exit(1)
    dups = int(df.duplicated().sum())
    if dups > 0:
        print(f"  note: dropping {dups} duplicate row(s)."); df = df.drop_duplicates().reset_index(drop=True)

    x, y = df[input_cols], df[target_col]
    base = f"{plant_from_filename(csv_path)}_{short_target_name(target_col)}"
    outdir = os.getcwd()                                   # save into the folder you ran from
    dest_csv = os.path.join(outdir, os.path.basename(csv_path))
    if os.path.abspath(csv_path) != os.path.abspath(dest_csv):
        shutil.copy(csv_path, dest_csv)

    print(f"\nRun: {base}   ({len(df)} rows, {len(input_cols)} inputs)  ->  {outdir}\n")
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=TEST_SIZE, random_state=RANDOM_STATE)
    fitted = fit_all(x_train, y_train)

    order = ["Linear Regression", "SVR", "Random Forest", "XGBoost", "Gradient Boost", "Polynomial"]
    rows = [metrics_row(n, fitted[n], base, x_train, y_train, x_test, y_test) for n in order]
    pd.DataFrame(rows).to_excel(os.path.join(outdir, f"{base}.xlsx"), index=False)

    print("\n" + "=" * 78)
    print(f"{'#':<3}{'Model':<20}{'Train R2':>9}{'Test R2':>9}{'RMSE':>10}{'MAE':>9}{'MAPE%':>8}")
    print("-" * 78)
    numbered = {}
    for k, r in enumerate(rows, 1):
        numbered[str(k)] = r["Model"]
        print(f"{k:<3}{r['Model']:<20}{fmt(r['Train R2']):>9}{fmt(r['Test R2']):>9}"
              f"{fmt(r['RMSE']):>10}{fmt(r['MAE']):>9}{fmt(r['MAPE (%)']):>8}")
    print("=" * 78)

    tree_name = confirm_pick("TREE model (SHAP)", auto_pick_tree(rows), numbered)
    smooth_name = confirm_pick("SMOOTH model (Pyomo)", auto_pick_smooth(rows), numbered)

    print(f"\nUsing {tree_name} for SHAP and {smooth_name} for Pyomo. Saving ...")
    save_shap(fitted[tree_name], x_test, outdir, base)
    eq_file = save_equation(smooth_name, fitted[smooth_name], x, x_test, outdir, base)
    save_notebook(outdir, base, os.path.basename(csv_path), input_cols, target_col, tree_name, smooth_name)
    print(f"\nDone. Folder: {outdir}\n  {base}.xlsx, {base}.ipynb, SHAP PNGs, {eq_file}")


def main():
    print("IECM surrogate pipeline\n")
    csv_path = ask("Drag the dataset CSV here (or paste its path): ")
    if not os.path.isfile(csv_path):
        print(f"ERROR: file not found: {csv_path}"); sys.exit(1)
    cols = list(pd.read_csv(csv_path, nrows=0).columns)
    print("\nColumns:")
    for i, c in enumerate(cols, 1): print(f"  {i}: {c}")
    input_idx = parse_columns(ask("\nInputs (e.g. 1,2,3,4,5): "), len(cols))
    # Outputs use [ ] so you can run MANY targets at once: [4][5][6] trains three
    # targets back-to-back, each saved to its own .ipynb + .xlsx. A single [6] or 6 is fine.
    target_idx = parse_targets(ask("Targets, each wrapped in [] (e.g. [6][7][8]): "), len(cols))
    input_cols = [cols[i] for i in input_idx]
    print(f"\n{len(target_idx)} target(s) to run: " + ", ".join(cols[t] for t in target_idx))
    for n, t in enumerate(target_idx, 1):
        print(f"\n########## target {n}/{len(target_idx)} ##########")
        run(csv_path, input_cols, cols[t])
    print("\nAll targets done.")


if __name__ == "__main__":
    main()
