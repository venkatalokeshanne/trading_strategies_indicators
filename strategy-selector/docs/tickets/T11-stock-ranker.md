# T11 Stock ranker ("in play")
- From ~69 symbols pick top K (default 3) at a checkpoint: soft score from gap, relative volume, ATR expansion, events, early range + the symbol's historical tradeability on similar days; walk-forward fit
- Baseline: rank by gap × relative volume
Accept: out-of-sample, top-ranked stocks have higher best-variant PnL than random/baseline.
