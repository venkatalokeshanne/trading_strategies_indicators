# T12 Strategy selector
- For each chosen stock pick variant or abstain. Score from similar past days with hierarchical shrinkage; similarity = regime and/or nearest neighbour on features; min-sample rule; abstain if score ≤ threshold; log candidates considered
- Only days strictly before the target day (assert)
Accept: picks for 20 consecutive days with sample sizes.
