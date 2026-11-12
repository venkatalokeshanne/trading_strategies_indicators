"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : GLD linear threshold strategy
Author       : hiron2
Source URL   : https://www.tradingview.com/script/7yIh8gog-GLD-Machine-Learning-Strategy-Lasso-Feature-Selection
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation of the exported linear model: five standardised features (volume SMA, candle
body, wick product, body x volume, low-close x volume) with fixed coefficients; hold a long while the
score is at or above the threshold, otherwise close. The coefficients were fitted on GLD daily data.

Deviations from the original: none.
Not carried over: the hline and the position-flag plot (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class GldLinearThreshold(Script):
    TITLE = "GLD linear threshold strategy"
    PINE_VERSION = 5
    OVERLAY = False
    STRATEGY = dict(pyramiding=0, commission_type="percent", commission_value=0.05)
    SOURCE = {"id": "7yIh8gog", "author": "hiron2", "licence": "not stated",
              "url": "https://www.tradingview.com/script/7yIh8gog-GLD-Machine-Learning-Strategy-Lasso-Feature-Selection"}

    def init(self):
        self.threshold = self.input.float(0.379073202241, "Threshold", step=0.000001)

    def on_bar(self):
        f0 = ta.sma(self.volume, 2)
        f1 = ta.sma((self.open - self.close), 1)
        f2 = ta.sma((self.high - self.close) * (self.low - self.close), 1)
        f3 = (ta.sma((self.open - self.close), 2)) * (ta.sma(self.volume, 2))
        f4 = (ta.sma((self.low - self.close), 1)) * (ta.sma(self.volume, 2))
        score_lin = 0.5223463687150838
        score_lin += (0.0012444888950145) * ((f0 - (6735594.9841713225468993)) / (3241843.4822131437249482))
        score_lin += (0.0029769186339496) * ((f1 - (-0.0910537243947856)) / (1.4953030683416331))
        score_lin += (0.0061458206471210) * ((f2 - (-0.9481280302141537)) / (1.4894312820065110))
        score_lin += (0.0113005100794886) * ((f3 - (-603183.3954082156997174)) / (9833879.5778208561241627))
        score_lin += (0.0065075254154198) * ((f4 - (-8826653.8223241623491049)) / (11670853.5754192266613245))
        score = score_lin
        long_cond = score >= self.threshold
        st = self.strategy
        if long_cond:
            st.entry("L", st.long)
        else:
            st.close("L")
        self.plot(score, "score", color=color.new(color.aqua, 0))
        self.plot(1 if long_cond else 0, "position_flag", color=color.new(color.green, 0))
