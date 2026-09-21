# T4 Candidate Selection Rule

The candidate universe is the complete 165-variant T3 grid.

For each outer fold, score every candidate on the available pre-outer development sample.

Primary score:
minimum total net P&L across ₹10, ₹20 and ₹30 brokerage/order scenarios.

Secondary score:
median total net P&L across those scenarios.

Tertiary score:
maximum drawdown at ₹30/order, preferring the least negative drawdown.

Quaternary score:
lower exit-rule complexity.

This rule is frozen before the outer OOS result is read.
