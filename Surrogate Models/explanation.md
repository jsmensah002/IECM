## Brief explanation

For each output (target), two surrogates are trained, a tree based model read with SHAP to explain what drives it
and a smooth linear or polynomial model to embed in the Pyomo optimizer,
so every plant becomes fast equations a cluster optimizer can query instead of rerunning IECM.
Water consumption is the exception to the clean fits above. On PC it is multiplicative and spans a wide range, so it is fitted in log space and the predictions are exponentiated back to tons/hr. On IGCC it is only weakly predictable, because its cooling load depends on process-area water demands that were not part of the sampled inputs.

Why Polynomial hits R2 = 1 on some targets:
If a target is built from its inputs using only +, −, *, and whole-number powers, a polynomial can match it exactly making R2 = 1.0. It fails only when the real relationship needs division, logs, roots, or exponents of those inputs.

## Insights from surrogate models:

**Capture is efficiency-driven (except PC).** In IGCC, NGCC and Hydrogen, CO2 captured is controlled almost entirely by absorber removal efficiency. PC is the exception because for PC, the gross electrical output is a sampled input whereas in the other plants gross electrical output is not a sampled input (IECM calculates it).

**Capture efficiency and output trade off.** Higher removal efficiency raises CO2 captured but lowers net power output in IGCC. The same effect appears in NGCC but is minor, since NGCC net output is driven mostly by ambient temperature. PC and Hydrogen are the exceptions: PC net output is set by its sampled gross electrical output, and Hydrogen's output is H2 production, driven by capacity factor rather than efficiency.

**Output reflects each technology.** NGCC net output is dominated by ambient temperature, IGCC spreads the load across ambient, efficiency and scrubber power, while Hydrogen production is driven almost entirely by capacity factor.

**Cost of CO2 captured differs by plant.** PC cost of CO2 captured is driven by gross electrical output, IGCC plant by capture efficiency, NGCC and Hydrogen plants by natural gas price.

**Water consumption.** In PC, NGCC and IGCC, water consumption is driven mainly by the cooling tower temperature change. Capture efficiency is only a minor driver on these plants. In IECM, hydrogen's cooling-tower ΔT is held fixed rather than sampled, so it carries no variance in the surrogate, leaving absorber efficiency as the dominant driver.
