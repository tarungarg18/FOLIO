# Financial Methodology

## Portfolio value

Current equity market value = quantity × latest valid unadjusted closing price. Mutual fund value = units × latest valid NAV. Display each valuation date. Historical returns instead use a consistently adjusted historical price or reconstructed total-return series with splits and dividends applied exactly once.

## Look-through exposure

For each fund and mapped security, indirect value = fund market value × disclosed constituent weight. Combined company value = direct value + indirect value from all held funds. Combined percentage = combined company value / total portfolio value. Constituents decompose fund assets and are not added to portfolio total.

Coverage = verified mapped eligible exposure / total eligible exposure × 100. Eligible exposure comprises direct equities plus equity exposure within funds included in look-through. Report debt, cash, other ineligible assets, and unmapped eligible exposure separately. Missing coverage is a confidence limitation, not low risk.

## Historical series and risk

With current positions and average costs only, a historical series is a hypothetical buy-and-hold reconstruction of today's quantities, not the investor's actual past performance. Volatility is sample standard deviation of aligned daily returns × √252. Drawdown is the minimum value/running peak − 1. Beta is covariance of aligned portfolio and benchmark returns divided by benchmark variance. Correlation uses common dates only. Require adequate observations or show unavailable.

Benchmark series use TRI, are rebased to the same first common date, and end on the same date. HHI is sum of squared normalized company weights; effective holdings is 1/HHI when mapping coverage supports it. Sharpe is omitted without a dated risk-free series. XIRR is omitted without complete dated cash flows.

## Health score

Version 1 component weights: diversification 30%, concentration 25%, volatility 20%, drawdown 15%, mapping coverage/freshness 10%. Thresholds, normalization/clamping, sample minimums and incomplete-data behavior must be versioned with the implementation. Missing components produce an incomplete score; never award a better score because data is absent.
