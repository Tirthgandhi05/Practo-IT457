# E3 memory comparison

| Memory | Scenario | Samples matched | Median client ms | Mean billed ms | USD / 1,000 successes |
|---|---|---:|---:|---:|---:|
| 256 MB | Cold | 15 / 15 | 771.407 | 579.867 | 0.00437612 |
| 256 MB | Warm | 200 / 200 | 40.773 | 11.440 | 0.00200767 |
| 512 MB | Cold | 10 / 10 | 693.780 | 497.100 | 0.00610251 |
| 512 MB | Warm | 100 / 100 | 69.722 | 6.910 | 0.00201758 |

At 512 MB, median cold client latency fell about 10.1%. Mean billed duration fell about 14.3% for cold requests and 39.6% for warm requests. Doubling memory raised modelled service cost per 1,000 successes by about 39.5% for cold requests and 0.5% for warm requests. Warm client median rose about 71.0%, despite shorter billed duration. Separate runs include network and service variability, so the client increase cannot be attributed to memory alone.

Keep 256 MB for this demonstration based on the lower measured cost. The sample sizes and sequential experimental design limit generalization. All successful observed cold candidates and warm-sequence samples matched CloudWatch by request ID. Correctness, warmup and burst calls are excluded.

Cost uses configured memory / 1024 GB, measured mean billed duration and screenshot rates captured 16 November 2026 in Mumbai. Lambda x86 duration $0.0000166667/GB-second, requests $0.20/million, HTTP API $1.05/million, DynamoDB standard writes $0.71/million. Assumes one successful <=1 KB write per booking. Adds $0.00196 per 1,000 for requests/API/writes. Excludes credits, storage, logs, transfer, taxes, retries and failed/conflicting calls. Initialization is already included in billed duration.

Inputs: requests.csv, cloudwatch-export.csv.csv, requests(1).csv, cloudwatch-512.csv.csv. Raw files remain authoritative.
