# E5 illustrative EC2/serverless cost model

Inputs are user-captured AWS Mumbai Linux t3.micro On-Demand price ($0.0112/hour), 730 hours/month, and E2 measured 256 MB Lambda durations. Price evidence was supplied 16 November 2026. No EC2 deployment or capacity benchmark was performed.

Both alternatives use one standard DynamoDB write per successful booking of at most 1 KB. Serverless uses Lambda + HTTP API + DynamoDB. The EC2 scenario assumes the application serves requests directly and writes to the same DynamoDB service. Additional public-serving, storage and availability costs are excluded.

EC2 subtotal = $8.176 + N × $0.00000071. Serverless subtotal = N × [(1-p) × $0.000002007666762 + p × $0.000004376115943333334], where p is an assumed cold fraction.

Crossover N = 8.176 / (serverless per-request cost - 0.00000071). Common DynamoDB writes cancel when solving for the crossover.

| Assumed cold fraction | Requests per 730-hour month at crossover | Average req/s | Both subtotals at crossover |
|---|---:|---:|---:|
| 0% | 6,300,539 | 2.397 | $12.6494 |
| 1% | 6,187,605 | 2.354 | $12.5692 |
| 10% | 5,328,079 | 2.027 | $11.9589 |
| 100% | 2,230,153 | 0.849 | $9.7594 |

The 0%, 1%, 10% and 100% cold fractions are sensitivity scenarios. Forced cold samples do not estimate the natural cold fraction. The all-cold case is an extreme bound.

| Requests per month | All-warm serverless | EC2 + DynamoDB |
|---|---:|---:|
| 100,000 | $0.2008 | $8.2470 |
| 1,000,000 | $2.0077 | $8.8860 |
| 5,000,000 | $10.0383 | $11.7260 |
| 10,000,000 | $20.0767 | $15.2760 |

## Limits and viva explanation

The curves compare selected service charges under fixed assumptions. One t3.micro must actually sustain the workload and latency target for its curve to apply. Average requests/second does not represent burst capacity. CPU credits, EBS, public IPv4, load balancing/TLS infrastructure, resilience, logs, data transfer, operations, taxes and free-tier credits are outside the calculation. Adding EC2 fixed costs moves its crossover to higher volume. Adding instances also changes the curve.

Viva wording: We used measured Lambda billed durations and verified regional prices to model a crossover. Under an all-warm scenario, the simplified subtotal crosses near 6.30 million requests in a 730-hour month. EC2 capacity was not measured, so we cannot conclude that one t3.micro meets the required performance at that volume.
