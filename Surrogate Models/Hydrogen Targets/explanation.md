# Derived columns — Hydrogen dataset

Two columns are computed from IECM outputs rather than pulled directly, because the hydrogen (14.0 beta) module does not report them in a form consistent with the power plants.

## CO2 Captured (tons/hr)

IECM reports hydrogen CO2 annually, and its direct "CO2 Captured (tons/hr)" output covers only the flue-gas (MEA) stream — not the whole plant. To get the whole-plant hourly rate (both the syngas MDEA capture and the flue-gas MEA capture), annual capture is divided by annual operating hours:

    CO2 Captured (tons/hr) = Annual CO2 Captured × 1,000,000 ÷ Annual Operating Hours

Both figures cover the same year, so the year cancels and the result is a rate in tonnes per hour.

## Cost of CO2 Captured ($/ton)

The hydrogen module provides no cost of CO2 captured; its only CO2-cost metric is "cost of CO2 avoided," which returns unusable negative values for this always-on-CCS plant. The power-plant "Cost of CO2 Captured" was found to equal the full levelized cost of electricity divided by the CO2 captured — not an incremental with/without-capture figure. The same basis is applied here: the full levelized cost of hydrogen divided by the CO2 captured per unit of hydrogen:

    Cost of CO2 Captured ($/ton) = Levelized Cost ($/lb H2) × (Annual H2 ÷ Annual CO2) × 2204.62

The 2204.62 converts hydrogen from tonnes to pounds so the hydrogen units cancel against the per-pound cost, leaving $/tonne CO2. This keeps hydrogen on the same cost basis as the PC, IGCC and NGCC plants (result: ~$135–341/ton, within the power-plant range).
