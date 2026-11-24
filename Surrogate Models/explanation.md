## Brief explanation

For each output (target), two surrogates are trained, a tree based model read with SHAP to explain what drives it
and a smooth linear or polynomial model to embed in the Pyomo optimizer,
so every plant becomes fast equations a cluster optimizer can query instead of rerunning IECM.

Why Polynomial hits R2 = 1 on some targets:
If a target is built from its inputs using only +, −, *, and whole-number powers, a polynomial can match it exactly and R2 = 1.0. It fails only when the real relationship needs division, logs, roots, or exponents of those inputs.

## Insights from surrogate models:

**Capture is efficiency-driven (except PC).** In IGCC, NGCC and Hydrogen, CO2 captured
is controlled almost entirely by absorber removal efficiency. PC is the
exception because for PC, the gross electrical output is  a sampled input whereas in the other plants gross electrical output is not a sampled input (IECM calculates it).

**The capture energy penalty shows up as a sign flip.** The same removal efficiency
that raises CO2 captured, lowers the net power output.

**Net power reflects each technology.** NGCC net output is dominated by ambient
temperature, while IGCC spreads the load across ambient, efficiency and scrubber power.

**Cost is economics, and differs by plant.** The cost driver changes with the
technology: PC cost is driven by gross electrical output, IGCC plant by
capture efficiency, NGCC and Hydrogen plants by natural gas price.
