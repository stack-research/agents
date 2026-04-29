1. Validate stage, failure signal, and attempt counts.
2. Classify failure signal into retryable vs non-retryable.
3. If attempts are exhausted, escalate or stop.
4. If retryable, choose retry/backoff and bounded delay.
5. Emit decision with reason code and next-step guidance.
