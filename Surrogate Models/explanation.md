For each output (target), two surrogates are trained, a tree based model read with SHAP to explain what drives it
and a smooth linear or polynomial model to embed in the Pyomo optimizer,
so every plant becomes fast equations a cluster optimizer can query instead of rerunning IECM.

Why Polynomial hits R2 = 1 on some targets:
If a target is built from its inputs using only +, −, *, and whole-number powers, a polynomial can match it exactly and R2 = 1.0. It fails only when the real relationship needs division, logs, roots, or exponents of those inputs.
