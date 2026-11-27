# Derived columns: Hydrogen dataset

Two columns are computed from IECM outputs rather than pulled directly, because the hydrogen (14.0 beta) module does not report them in a form consistent with the power plants.

## CO2 Captured (tons/hr)

IECM reports hydrogen CO2 annually, and its direct "CO2 Captured (tons/hr)" output does not match the plant's total annual capture. This is because from the hydrogen uncertainty export file (Hyrogen_uncertainty_export.txt), the direct "CO2 Captured (tons/hr)" output equals "CO2 Captured from MEA" (confirmed identical across all rows), i.e. only the flue-gas stream, not the whole plant.
To get a whole-plant hourly rate, Annual CO2 Captured is divided by Annual Operating Hours, then converted from metric tonnes to short tons:

    CO2 Captured (tons/hr) =
        Annual CO2 Captured (million tonne/yr) × 1,000,000 (tonne/million tonne)
        ÷ Annual Operating Hours (hours/year)
        × 1.10231 (short ton/tonne)

Both figures cover the same year, so the year cancels and dividing gives a rate in metric tonnes per hour. The 1.10231 then converts metric tonnes to short tons, because the power plants report CO2 Removed in short tons.

## Cost of CO2 Captured ($/ton)

The hydrogen module provides no cost of CO2 captured. The power-plant "Cost of CO2 Captured" was found to equal the cost of electricity multiplied by the electricity produced per unit of CO2 captured. The same basis is applied here: the full Levelized Cost of hydrogen multiplied by the hydrogen produced per unit of CO2 captured:

    Cost of CO2 Captured ($/ton) =
        Levelized Cost ($/lb H2)
        × Annual H2 Production (million tonne/yr) ÷ Annual CO2 Captured (million tonne/yr)
        × 2204.62 (lb/tonne)
        ÷ 1.10231 (short ton/tonne)

The 2204.62 converts hydrogen from tonnes to pounds so the hydrogen units cancel against the per-pound cost, leaving a cost in dollars per metric tonne of CO2. The 1.10231 then converts it to dollars per short ton, matching the power plants. This keeps hydrogen on the same cost basis as the PC, IGCC and NGCC plants.
