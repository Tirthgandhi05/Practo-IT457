# E2 — Cost per 1,000 successful bookings

Completed calculation using matched measured billed durations and user-captured Mumbai pricing. This is a service-cost model, not an invoice.

| Scenario | Successful samples / matched logs | Mean billed duration (ms) | Lambda compute ($) | Lambda requests ($) | HTTP API ($) | DynamoDB ($) | Total per 1,000 ($) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Cold | 15 / 15 | 579.867 | 0.00241612 | 0.00020000 | 0.00105000 | 0.00071000 | 0.00437612 |
| Warm | 200 / 200 | 11.440 | 0.00004767 | 0.00020000 | 0.00105000 | 0.00071000 | 0.00200767 |

## Method

Lambda compute = 1,000 × 0.25 GB × mean billed duration in seconds × $0.0000166667/GB-second. Add $0.00020 Lambda requests + $0.00105 HTTP API + $0.00071 DynamoDB writes.

All 15 successful observed cold-candidate requests and all 200 successful observed warm-sequence requests matched CloudWatch by request ID. Burst, correctness and warmup rows are excluded. Initialization is already reflected in billed duration and is not added again.

CloudWatch exported memory as 256000000; the deployment is 256 MB, billed as 256/1024 = 0.25 GB. The raw field is not treated as megabytes.

## Interpretation and limitations

A hypothetical 1,000 all-cold successful bookings cost $0.004376; 1,000 all-warm successful bookings cost $0.002008 in these included services. These are two scenarios, not a claim that production traffic is entirely cold or warm.
Assumes one standard successful DynamoDB write per item <=1 KB, one HTTP API billing increment per call, and first-tier x86 on-demand rates. Excludes credits/free allowances, database storage, log ingestion/storage/querying, transfer, taxes, retries and failed/conflicting requests. It does not compute the full experiment invoice or production total cost.

## Sources

User screenshots of https://aws.amazon.com/lambda/pricing/, https://aws.amazon.com/api-gateway/pricing/, and https://aws.amazon.com/dynamodb/pricing/on-demand/ with Mumbai selected; request CSV and CloudWatch export supplied in this conversation.
