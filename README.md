# IECM Surrogate Modeling for CCUS

This repo holds Python tools that turn IECM (the carbon capture plant
simulator) output into machine learning ready datasets for training surrogate
models. `sensitivity_analysis_table_grab.py` pulls IECM sensitivity analysis
tables from the clipboard into a clean CSV, and `parse_uncertainty.py` reads a
full IECM uncertainty export, lets you pick the input and output variables you
want, and builds an aligned training set where every row is one consistent
simulation.

Datasets are built for all four IECM plant types, PC, NGCC, IGCC
and Low Carbon Hydrogen, each a 200 sample Latin Hypercube sweep covering
drivers like capture efficiency, fuel cost, plant size and cooling against
outputs like CO2 captured, net power and cost of CO2 captured. The aim is to
represent each plant as a fast surrogate that a cluster scale optimizer can
query thousands of times instead of rerunning the full simulator, so a multi
node regional cluster with shared transport and storage becomes tractable.

Note that the configurations, variable selections and value ranges here were
chosen for practice, to exercise the pipeline rather than model any specific
plant. In a real study they would be grounded in literature and process data
instead of picked by hand.
