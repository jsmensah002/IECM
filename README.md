# IECM Surrogate Modeling for CCUS

This repo holds Python tools that turn IECM (the carbon capture plant
simulator) output into machine learning ready datasets for training
surrogate models. `sensitivity_analysis_table_grab.py` pulls IECM sensitivity analysis tables from the
clipboard into a clean CSV, and `parse_uncertainty.py` reads a full IECM uncertainty
export, lets you pick the input and output variables you want, and builds an
aligned training set where every row is one consistent simulation. The example
here is a pulverized coal retrofit with a 200 sample Latin Hypercube sweep covering drivers like absorber CO2
removal efficiency, plant size, fuel cost and cooling against outputs like
CO2 removed, net power, cost of CO2 captured and water use. The aim is to
represent each plant as a fast surrogate that a cluster scale optimizer can
query thousands of times instead of rerunning the full simulator, and to
extend the same workflow to NGCC, IGCC and low carbon hydrogen plants.

Note that the plant configurations, variable selections and value ranges in
this example were chosen for practice, to build and exercise the pipeline
rather than to model any specific plant. In a real study each of these, the
uncertain inputs, their distributions and the configurations, would be
grounded in literature and process data instead of picked by hand.
