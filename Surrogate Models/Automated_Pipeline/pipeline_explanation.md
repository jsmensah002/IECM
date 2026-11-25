# Automated Pipeline

Each surrogate target was first built manually (benchmark the models, read the best
tree with SHAP, save the smooth model's equation for Pyomo). This automated pipeline,
iecm_surrogate_pipeline.py, was then written to run the same steps end to end and check
it reproduces the manual results.

For every target the Linear, SVR, Random Forest, Gradient Boosting and
Polynomial results match the manual runs, and the models chosen for SHAP and for Pyomo
come out the same, so the saved equations and SHAP plots are identical.

The only difference is in XGBoost (and occasionally Random Forest), where the numbers
shift slightly. This is because the pipeline runs in a fresh environment with a newer
version of the tree libraries than the original notebooks used, and tree models change
a little between versions even with the same random seed. It does not affect the chosen
models or the saved outputs.

From here the pipeline is the standard: point it at a plant dataset, give it the input
and target columns, and it trains all targets and saves each one's notebook, metrics,
SHAP plots and equation automatically.

Each run also saves a full, re-runnable notebook with every model's code. So if any
part of a run needs to be changed, that notebook can be opened, edited and run again directly, 
without touching the pipeline script.
