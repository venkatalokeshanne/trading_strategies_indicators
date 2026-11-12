<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator("Correlation-Weighted RSI Predictor (Zeiierman)", "lower", {
  decimals: 0,
  mainColorInheritFrom: 'text',
  shortName: 'Correlation-Weighted RSI Predictor (Zeiierman)'
});

// Tooltips
const t1 = "RSI lookback length computed on the current timeframe.";
const t2 = "Moving Average lookback length computed on RSI.";
const t3 = "Rolling window for correlation learning and z-scoring.";

// Inputs
const rsiLen = input.number("RSI Length", 14, { min: 2, max: 300 });
const sigLen = input.number("Signal Length", 20, { min: 2, max: 300 });
const learnLen = input.number("Learning Window", 20, { min: 1, max: 300 });

// Per-bar features
const retLog = for_every(close, (_c, _prev, _idx) => {
    const prevClose = _idx > 0 ? close[_idx - 1] : _c;
    return Math.log(_c / prevClose);
});

const rsiVal = rsi(close, rsiLen);
const atrPct = div(atr(high, low, close, 200), close);

const volLogChg = for_every(volume, (_v, _prev, _idx) => {
    const prevVol = _idx > 0 ? volume[_idx - 1] : _v;
    return Math.log(_v / prevVol);
});

// Target (y): prior bar RSI
const y_rsi = shift(rsiVal, 1);

// Predictors (X): prior-bar values of each feature
const x_ret = shift(retLog, 1);
const x_rsi = shift(rsiVal, 1);
const x_atrp = shift(atrPct, 1);
const x_vchg = shift(volLogChg, 1);
const x_vol = shift(volume, 1);

// Z-score function
const f_z = (src, length) => {
    const myMean = sma(src, length);
    const myStdev = stdev(src, length);
    return div(sub(src, myMean), myStdev);
};

// Correlation absolute values
const corrs_abs_ret = correlation(y_rsi, x_ret, learnLen).map(v => Math.abs(v || 0));
const corrs_abs_rsi = correlation(y_rsi, x_rsi, learnLen).map(v => Math.abs(v || 0));
const corrs_abs_atrp = correlation(y_rsi, x_atrp, learnLen).map(v => Math.abs(v || 0));
const corrs_abs_vchg = correlation(y_rsi, x_vchg, learnLen).map(v => Math.abs(v || 0));
const corrs_abs_vol = correlation(y_rsi, x_vol, learnLen).map(v => Math.abs(v || 0));

// Z-scored predictors
const xz_ret = f_z(x_ret, learnLen);
const xz_rsi = f_z(x_rsi, learnLen);
const xz_atrp = f_z(x_atrp, learnLen);
const xz_vchg = f_z(x_vchg, learnLen);
const xz_vol = f_z(x_vol, learnLen);

// Signed coefficients
const coef_ret = correlation(y_rsi, x_ret, learnLen);
const coef_rsi = series_of(1.0);
const coef_atrp = correlation(y_rsi, x_atrp, learnLen);
const coef_vchg = correlation(y_rsi, x_vchg, learnLen);
const coef_vol = correlation(y_rsi, x_vol, learnLen);

// Prediction calculation
const pred_rsi_z = for_every(
    corrs_abs_ret, corrs_abs_rsi, corrs_abs_atrp, corrs_abs_vchg, corrs_abs_vol,
    xz_ret, xz_rsi, xz_atrp, xz_vchg, xz_vol,
    coef_ret, coef_rsi, coef_atrp, coef_vchg, coef_vol,
    (_cr, _ci, _ca, _cv, _co, _zr, _zi, _za, _zv, _zo, _cfr, _cfi, _cfa, _cfv, _cfo) => {
        const corrs = [_cr, _ci, _ca, _cv, _co];
        const zscores = [_zr, _zi, _za, _zv, _zo];
        const coefs = [_cfr, _cfi, _cfa, _cfv, _cfo];
        
        const indices = corrs.map((v, i) => ({ v: v || 0, i }))
            .sort((a, b) => b.v - a.v)
            .slice(0, 5)
            .map(x => x.i);
        
        let mySum = 0;
        for (const idx of indices) {
            mySum += (coefs[idx] || 0) * (zscores[idx] || 0);
        }
        return mySum;
    });

// Map z back to RSI level
const rsi_mean = sma(y_rsi, learnLen);
const rsi_std = stdev(y_rsi, learnLen);
const pred_rsi = add(rsi_mean, mult(rsi_std, pred_rsi_z));

// Map prediction to weight
const rsiWeight = for_every(pred_rsi, _p => {
    const weight = Math.max(-2, Math.min(2, (50 - (_p || 0)) / 50)) * -1;
    return weight;
});

const ma_rsi = sma(rsiWeight, sigLen);

// Overbought zone is above 0.5, oversold zone is below -0.5

// Create gradient fill series for overbought zone (above 0.5)
const overboughtTop = for_every(rsiWeight, _w => _w > 0.5 ? _w : null);
const overboughtBottom = for_every(rsiWeight, _w => _w > 0.5 ? 0.5 : null);

// Create gradient fill series for oversold zone (below -0.5)
const oversoldTop = for_every(rsiWeight, _w => _w < -0.5 ? -0.5 : null);
const oversoldBottom = for_every(rsiWeight, _w => _w < -0.4 ? _w : null);

// Main plots
const rsiPlot = paint(rsiWeight, { name: "Correlation-Weighted RSI Predictor", color: "#7E57C2" });
paint(ma_rsi, { name: "Correlation-Weighted RSI Predictor Signal Line", color: "orange" });

// Reference lines
const upperBand = paint(horizontal_line(0.5), { name: "Correlation-Weighted RSI Predictor Upper Band", color: "#787B86", style: "dotted" });
const midLine = paint(horizontal_line(0), { name: "Correlation-Weighted RSI Predictor Middle Band", color: "#787B86", style: "dotted" });
const lowerBand = paint(horizontal_line(-0.5), { name: "Correlation-Weighted RSI Predictor Lower Band", color: "#787B86", style: "dotted" });

// Background fill between upper and lower bands
fill(upperBand, lowerBand, "rgba(126, 87, 194, 0.1)", 0.1, "Correlation-Weighted RSI PredictorI Background Fill");

// Gradient fills for overbought zone (above 0.5)
color_cloud(overboughtTop, overboughtBottom, "rgba(0, 255, 0, 0)", "rgba(0, 255, 0, 1)", "Overbought Gradient Top", "Overbought Gradient Bottom", 0.5);

// Gradient fills for oversold zone (below -0.5)
color_cloud(oversoldTop, oversoldBottom, "rgba(255, 0, 0, 1)", "rgba(255, 0, 0, 0)", "Oversold Gradient Top", "Oversold Gradient Bottom", 0.5);
</code>