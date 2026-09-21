# T7 Protocol Freeze

The T7 candidate space and selection rule are frozen before reading joint WFO results.

## 448 configurations
- 14 entry variants: D0-D6 × two timing modes.
- 32 exit variants: expiry control + 7 fixed targets + 7 fixed stops + 12 trailing targets + 5 trailing stops.

## Minimum training sample
A joint configuration must contain at least 25 unique training decision dates.

## Selection
Primary: maximize worst-case mean net P&L per trade across brokerage stresses.
Secondary: maximize worst-case total net P&L.
Tertiary: least-negative worst-brokerage maximum drawdown.
Quaternary: lower complexity.

## Control
D3 + same-session 09:30 + expiry exit.

No configuration receives special treatment because it performed well in the earlier separate T2/T3 studies.
