<code x-ref="code" class="hljs" data-clipboard-text>// ═══════════════════════════════════════════════════════════════════════════════
//    THOMPSON-ENHANCED DERIVATIVE PATTERN ENGINE — TrendSpider
//    Recursive Derivative Cascade • Bayesian Thompson-Sampling Bandit •
//    Weighted-Euclidean Analog Search • EV-Gated Signals • Adaptive TP/SL
//    Created by Dskyz (DAFE) Trading Systems
//    © DAFE — Dskyz Advanced Financial Engineering
// ═══════════════════════════════════════════════════════════════════════════════
//  THEORETICAL FOUNDATION
//  Full derivation: "Non-Parametric Phase-Space Reconstruction and Bayesian
//  Bandit Optimization in Higher-Order Financial Derivatives: The TED-PE
//  Framework" — Shaun Lear (DskyzInvestments), July 2026. Section references
//  below point back to that paper; this file is the executable form of it.
//
//  • Kinematic cascade (Sec. 2) — a price oscillator is treated as the
//    displacement term of a physical system. Four successive finite
//    differences (d1 Velocity, d2 Acceleration, d3 Jerk, d4 Snap) expose the
//    structural fingerprint of a reversal — Snap and Jerk decay well before
//    price itself rolls over, which is the whole premise for reacting off
//    d1-d4 rather than the base oscillator's own overbought/oversold levels.
//  • Tompson causal Gaussian filter (Sec. 3.1) — repeated differentiation
//    amplifies high-frequency noise exponentially (Sec. 3, the Δⁿf(t)
//    binomial-difference identity), so the base indicator is smoothed with a
//    Gaussian-weighted kernel before differentiation. Per the paper's own
//    correction: this is causal, not zero-lag — expect ~(L−1)/2 bars of group
//    delay at the chosen Filter Period. That delay is inherent to the
//    method, not a porting artifact (see the real-time/confirmed note below
//    for the one piece of *additional*, avoidable lag this file controls).
//  • Rolling Z-score normalization (Sec. 3.2) — nD1-nD4 rescale each
//    derivative to standard deviations from its own rolling mean, which is
//    what makes d1-d4 comparable to each other and to the same indicator on
//    a different asset/timeframe.
//  • Weighted Euclidean analog search (Sec. 4) — the current 4D state vector
//    [nD1,nD2,nD3,nD4] is compared against up to `Search History Depth` bars
//    of prior states; matches are converted to a similarity score
//    1/(1+distance) and aggregated as a similarity-weighted ensemble, not a
//    plain top-C average or raw win rate.
//  • Expected Value gating (Sec. 4-5) — signals fire on probability-weighted
//    (avg win) − (probability-weighted avg loss), so payoff magnitude gates
//    the signal, not direction frequency alone.
//  • Bayesian bandit dimension weighting (Sec. 5) — normW1-normW4 come from a
//    Beta(α,β) posterior per derivative, decayed each bar by the forgetting
//    factor before the new observation is folded in. Stochastic mode draws a
//    Normal-moment-matched approximation of the Beta posterior (Box-Muller
//    via Math.random(), redrawn every bar) rather than an exact Beta
//    variate, per the paper's own correction that TrendSpider/Pine have no
//    native Beta-variate sampler; Deterministic mode uses the posterior mean
//    directly and is recommended for reproducible, repaint-free live use.
//  • Known, explicitly-flagged limitations carried over unchanged (Sec. 4-5,
//    7.5) — d1-d4 are treated as orthogonal axes and independent bandit arms
//    even though they're mechanically correlated successive differences of
//    one series (a Mahalanobis distance / correlated-arm bandit would
//    correct this — not implemented, flagged as future work in the paper
//    itself). Analog sample sizes are typically single digits, so win-rate
//    and EV readouts are high-variance and descriptive, not statistically
//    conclusive (Sec. 6). No out-of-sample or walk-forward validation has
//    been performed (Sec. 7, 7.5). Transaction costs, slippage, and spread
//    are not modeled anywhere in the EV or TP/SL math (Sec. 7.5, item 6).
// ══════════════════════════════════════════════════════════════════════════════
describe_indicator('Thompson-Enhanced Derivative Pattern Engine', 'price', { shortName: '⟡ TED-PE', mainColorInheritFrom: 'legend_anchor' });
// ╔════════════════════════════════════════════════════════════════════════════╗
// ║  INPUTS & CONFIGURATION                                                    ║
// ╚════════════════════════════════════════════════════════════════════════════╝
var i_baseType    = input.select('Base Indicator', 'CCI', ['RSI', 'MFI', 'CCI', 'OBV', 'CMF', 'ROC']);
var i_baseLen     = input.number('Indicator Length', 14, { min: 2 });
var i_banditMode  = input.select('Bandit Mode', 'Stochastic', ['Stochastic', 'Deterministic']);
var i_filterPer   = input.number('Filter Period', 9, { min: 3, max: 30 });
var i_normLen     = input.number('Normalization Lookback', 50, { min: 5 });
var i_decay       = input.number('Bandit Decay Factor', 0.999, { min: 0.90, max: 1.0, step: 0.001 });
var i_useFilter   = input.boolean('Apply Low-Pass Filter', true);
var i_useBandit   = input.boolean('Dynamic Bayesian Weighting', true);
var i_searchWin   = input.number('Search History Depth (Bars)', 500, { min: 100, max: 1000 });
var i_matchCount  = input.number('Analog Matches to Find', 5, { min: 2, max: 10 });
var i_matchThr    = input.number('Similarity Threshold', 0.75, { min: 0.1, max: 1.0, step: 0.05 });
var i_projFwd     = input.number('Projection Horizon (Bars)', 10, { min: 3, max: 50 });
var i_evThresh    = input.number('Minimum EV Threshold %', 0.10, { min: 0.0, max: 5.0, step: 0.05 });
var i_minMatches  = input.number('Minimum Analog Count', 2, { min: 1, max: 10 });
var i_signalMode  = input.select('Signal Timing', 'Real-Time', ['Real-Time', 'Confirmed (Bar Close)']);
var i_atrLen      = input.number('ATR Length', 14, { min: 1 });
var i_atrMult     = input.number('ATR Stop Multiplier', 2.0, { min: 0.1, step: 0.1 });
var i_showSignals = input.boolean('Show Signal Markers', true);
var i_showBars    = input.boolean('Color Candles by EV', true);
var i_showZones   = input.boolean('Show TP/SL Zone', true);
var i_glow        = input.boolean('Glow-Halo Signal Markers', true);
var i_theme       = input.select('Dashboard', 'Full', ['Full', 'Compact', 'Off']);
// ╔════════════════════════════════════════════════════════════════════════════╗
// ║  CORE HELPERS                                                              ║
// ╚════════════════════════════════════════════════════════════════════════════╝
var n = close.length;
function fillNull(len) {
    var arr = [];
    for (var i = 0; i < len; i++) arr.push(null);
    return arr;
}
function nz(v, fallback) {
    var fb = fallback === undefined ? 0 : fallback;
    if (v === null || v === undefined) return fb;
    if (typeof v === 'number' && isNaN(v)) return fb;
    return v;
}
function fmtNum(v, dec) {
    if (v === null || v === undefined || isNaN(v)) return '---';
    return v.toFixed(dec);
}
function smaArr(arr, len) {
    var m = arr.length;
    var out = fillNull(m);
    var runSum = 0, cnt = 0;
    for (var i = 0; i < m; i++) {
        var v = arr[i];
        if (v !== null && v !== undefined) { runSum += v; cnt++; }
        if (i >= len) {
            var old = arr[i - len];
            if (old !== null && old !== undefined) { runSum -= old; cnt--; }
        }
        if (i >= len - 1 && cnt > 0) out[i] = runSum / len;
    }
    return out;
}
function rmaArr(arr, len) {
    var m = arr.length;
    var out = fillNull(m);
    var smoothK = 1.0 / len;
    var prev = null;
    for (var i = 0; i < m; i++) {
        if (arr[i] === null || arr[i] === undefined) continue;
        prev = (prev === null) ? arr[i] : (smoothK * arr[i] + (1 - smoothK) * prev);
        out[i] = prev;
    }
    return out;
}
function diffArr(src) {
    var m = src.length;
    var out = fillNull(m);
    for (var i = 1; i < m; i++) {
        if (src[i] === null || src[i - 1] === null) continue;
        out[i] = src[i] - src[i - 1];
    }
    return out;
}
function zScoreArr(src, len) {
    var m = src.length;
    var out = fillNull(m);
    var meanArr = smaArr(src, len);
    for (var i = len - 1; i < m; i++) {
        if (src[i] === null || meanArr[i] === null) continue;
        var sumSq = 0, cnt = 0;
        for (var k = 0; k < len; k++) {
            var v = src[i - k];
            if (v === null || v === undefined) continue;
            sumSq += Math.pow(v - meanArr[i], 2);
            cnt++;
        }
        var sd = cnt > 0 ? Math.sqrt(sumSq / cnt) : 0;
        out[i] = sd === 0 ? 0 : (src[i] - meanArr[i]) / sd;
    }
    return out;
}
function barString(val, slots) {
    var s = slots || 10;
    var filled = Math.max(0, Math.min(s, Math.round(val)));
    var str = '';
    for (var i = 1; i <= s; i++) str += (i <= filled ? '█' : '░');
    return str;
}
// ╔════════════════════════════════════════════════════════════════════════════╗
// ║  BASE INDICATOR ENGINE                                                     ║
// ╚════════════════════════════════════════════════════════════════════════════╝
function rsiCalc(src, len) {
    var m = src.length;
    var gains = fillNull(m), losses = fillNull(m);
    gains[0] = 0; losses[0] = 0;
    for (var i = 1; i < m; i++) {
        var chg = src[i] - src[i - 1];
        gains[i] = chg > 0 ? chg : 0;
        losses[i] = chg < 0 ? -chg : 0;
    }
    var avgG = rmaArr(gains, len);
    var avgL = rmaArr(losses, len);
    var out = fillNull(m);
    for (var i = 0; i < m; i++) {
        if (avgG[i] === null || avgL[i] === null) continue;
        out[i] = avgL[i] === 0 ? 100 : (100 - (100 / (1 + avgG[i] / avgL[i])));
    }
    return out;
}
function trCalc() {
    var out = fillNull(n);
    for (var i = 0; i < n; i++) {
        if (i === 0) { out[i] = high[i] - low[i]; continue; }
        var a = high[i] - low[i];
        var b = Math.abs(high[i] - close[i - 1]);
        var c = Math.abs(low[i] - close[i - 1]);
        out[i] = Math.max(a, Math.max(b, c));
    }
    return out;
}
function atrCalc(len) {
    return rmaArr(trCalc(), len);
}
function mfiCalc(len) {
    var tp = fillNull(n), mf = fillNull(n), posMF = fillNull(n), negMF = fillNull(n);
    for (var i = 0; i < n; i++) {
        tp[i] = (high[i] + low[i] + close[i]) / 3.0;
        mf[i] = tp[i] * volume[i];
        if (i === 0) { posMF[i] = 0; negMF[i] = 0; continue; }
        if (tp[i] > tp[i - 1]) { posMF[i] = mf[i]; negMF[i] = 0; }
        else if (tp[i] < tp[i - 1]) { posMF[i] = 0; negMF[i] = mf[i]; }
        else { posMF[i] = 0; negMF[i] = 0; }
    }
    var posSum = smaArr(posMF, len);
    var negSum = smaArr(negMF, len);
    var out = fillNull(n);
    for (var i = 0; i < n; i++) {
        if (posSum[i] === null || negSum[i] === null) continue;
        var pS = posSum[i] * len, nS = negSum[i] * len;
        out[i] = nS === 0 ? 100 : (100 - (100 / (1 + pS / nS)));
    }
    return out;
}
function cciCalc(len) {
    var tp = fillNull(n);
    for (var i = 0; i < n; i++) tp[i] = (high[i] + low[i] + close[i]) / 3.0;
    var tpSma = smaArr(tp, len);
    var out = fillNull(n);
    for (var i = len - 1; i < n; i++) {
        if (tpSma[i] === null) continue;
        var devSum = 0;
        for (var k = 0; k < len; k++) devSum += Math.abs(tp[i - k] - tpSma[i]);
        var devMean = devSum / len;
        out[i] = devMean === 0 ? 0 : (tp[i] - tpSma[i]) / (0.015 * devMean);
    }
    return out;
}
function obvCalc() {
    var out = fillNull(n);
    var run = 0;
    for (var i = 0; i < n; i++) {
        if (i === 0) { run = volume[i]; }
        else if (close[i] > close[i - 1]) run += volume[i];
        else if (close[i] < close[i - 1]) run -= volume[i];
        out[i] = run;
    }
    return out;
}
function cmfCalc(len) {
    var mfv = fillNull(n);
    for (var i = 0; i < n; i++) {
        var hl = high[i] - low[i];
        mfv[i] = hl === 0 ? 0 : (((close[i] - low[i]) - (high[i] - close[i])) / hl) * volume[i];
    }
    var mfvSma = smaArr(mfv, len);
    var volSma = smaArr(volume, len);
    var out = fillNull(n);
    for (var i = 0; i < n; i++) {
        if (mfvSma[i] === null || volSma[i] === null || volSma[i] === 0) continue;
        out[i] = mfvSma[i] / volSma[i];
    }
    return out;
}
function rocCalc(len) {
    var out = fillNull(n);
    for (var i = len; i < n; i++) {
        out[i] = close[i - len] === 0 ? 0 : ((close[i] - close[i - len]) / close[i - len]) * 100.0;
    }
    return out;
}
var rawBase = fillNull(n);
if (i_baseType === 'RSI') rawBase = rsiCalc(close, i_baseLen);
else if (i_baseType === 'MFI') rawBase = mfiCalc(i_baseLen);
else if (i_baseType === 'CCI') rawBase = cciCalc(i_baseLen);
else if (i_baseType === 'OBV') rawBase = obvCalc();
else if (i_baseType === 'CMF') rawBase = cmfCalc(i_baseLen);
else rawBase = rocCalc(i_baseLen);
function lowPassFilter(src, length) {
    var clampLen = Math.max(length, 3);
    var weights = [];
    for (var k = 0; k < clampLen; k++) {
        weights.push(Math.exp(-Math.pow(k - (clampLen - 1) / 2.0, 2) / (2.0 * Math.pow(clampLen / 4.0, 2))));
    }
    var out = fillNull(n);
    for (var i = 0; i < n; i++) {
        if (src[i] === null) continue;
        var valSum = 0, wUsed = 0;
        for (var k = 0; k < clampLen; k++) {
            var idx = i - k;
            if (idx < 0 || src[idx] === null || src[idx] === undefined) continue;
            valSum += src[idx] * weights[k];
            wUsed += weights[k];
        }
        out[i] = wUsed === 0 ? src[i] : valSum / wUsed;
    }
    return out;
}
var baseInd = i_useFilter ? lowPassFilter(rawBase, i_filterPer) : rawBase;
// ╔════════════════════════════════════════════════════════════════════════════╗
// ║  DERIVATIVE ENGINE & STANDARD NORMALIZATION                                ║
// ╚════════════════════════════════════════════════════════════════════════════╝
var d1 = diffArr(baseInd);
var d2 = diffArr(d1);
var d3 = diffArr(d2);
var d4 = diffArr(d3);
var nD1 = zScoreArr(d1, i_normLen);
var nD2 = zScoreArr(d2, i_normLen);
var nD3 = zScoreArr(d3, i_normLen);
var nD4 = zScoreArr(d4, i_normLen);
// ╔════════════════════════════════════════════════════════════════════════════╗
// ║  BAYESIAN BANDIT (THOMPSON SAMPLING DYNAMIC WEIGHTING)                     ║                               
// ╚════════════════════════════════════════════════════════════════════════════╝
function mulberry32(seed) {
    var s = seed >>> 0;
    return function () {
        s = (s + 0x6D2B79F5) | 0;
        var t = s;
        t = Math.imul(t ^ (t >>> 15), t | 1);
        t = (t + Math.imul(t ^ (t >>> 7), t | 61)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
}
function betaNormalSample(a, b, rngNext) {
    var mu = a / (a + b);
    var sig2 = (a * b) / (Math.pow(a + b, 2) * (a + b + 1.0));
    var sig = Math.sqrt(Math.max(sig2, 0.0));
    var u1 = Math.max(Math.min(rngNext(), 0.999999), 0.000001);
    var u2 = Math.max(Math.min(rngNext(), 0.999999), 0.000001);
    var zz = Math.sqrt(-2.0 * Math.log(u1)) * Math.cos(2.0 * Math.PI * u2);
    return Math.max(Math.min(mu + zz * sig, 1.0), 0.0);
}
var normW1 = fillNull(n), normW2 = fillNull(n), normW3 = fillNull(n), normW4 = fillNull(n);
var bd1A = 1.0, bd1B = 1.0, bd2A = 1.0, bd2B = 1.0, bd3A = 1.0, bd3B = 1.0, bd4A = 1.0, bd4B = 1.0;
var bw1 = 1.0, bw2 = 1.0, bw3 = 1.0, bw4 = 1.0;
for (var i = 0; i < n; i++) {
    if (i_useBandit) {
        if (i > i_projFwd) {
            var lb = i - i_projFwd;
            if (close[lb] !== null && close[lb] !== 0) {
                var priceChange = close[i] - close[lb];
                var priceDir = priceChange > 0 ? 1 : (priceChange < 0 ? -1 : 0);
                if (priceDir !== 0 && nD1[lb] !== null && nD2[lb] !== null && nD3[lb] !== null && nD4[lb] !== null) {
                    bd1A *= i_decay; bd1B *= i_decay;
                    bd2A *= i_decay; bd2B *= i_decay;
                    bd3A *= i_decay; bd3B *= i_decay;
                    bd4A *= i_decay; bd4B *= i_decay;
                    if ((nD1[lb] > 0 && priceDir === 1) || (nD1[lb] < 0 && priceDir === -1)) bd1A += 1;
                    if ((nD1[lb] > 0 && priceDir === -1) || (nD1[lb] < 0 && priceDir === 1)) bd1B += 1;
                    if ((nD2[lb] > 0 && priceDir === 1) || (nD2[lb] < 0 && priceDir === -1)) bd2A += 1;
                    if ((nD2[lb] > 0 && priceDir === -1) || (nD2[lb] < 0 && priceDir === 1)) bd2B += 1;
                    if ((nD3[lb] > 0 && priceDir === 1) || (nD3[lb] < 0 && priceDir === -1)) bd3A += 1;
                    if ((nD3[lb] > 0 && priceDir === -1) || (nD3[lb] < 0 && priceDir === 1)) bd3B += 1;
                    if ((nD4[lb] > 0 && priceDir === 1) || (nD4[lb] < 0 && priceDir === -1)) bd4A += 1;
                    if ((nD4[lb] > 0 && priceDir === -1) || (nD4[lb] < 0 && priceDir === 1)) bd4B += 1;
                }
            }
        }
        if (i_banditMode === 'Stochastic') {
            var rngNext = mulberry32(i + 1);
            bw1 = betaNormalSample(bd1A, bd1B, rngNext);
            bw2 = betaNormalSample(bd2A, bd2B, rngNext);
            bw3 = betaNormalSample(bd3A, bd3B, rngNext);
            bw4 = betaNormalSample(bd4A, bd4B, rngNext);
        } else {
            bw1 = bd1A / (bd1A + bd1B);
            bw2 = bd2A / (bd2A + bd2B);
            bw3 = bd3A / (bd3A + bd3B);
            bw4 = bd4A / (bd4A + bd4B);
        }
    } else {
        bw1 = 1.0; bw2 = 1.0; bw3 = 1.0; bw4 = 1.0;
    }
    var totalW = bw1 + bw2 + bw3 + bw4;
    normW1[i] = (bw1 / totalW) * 4.0;
    normW2[i] = (bw2 / totalW) * 4.0;
    normW3[i] = (bw3 / totalW) * 4.0;
    normW4[i] = (bw4 / totalW) * 4.0;
}
// ╔════════════════════════════════════════════════════════════════════════════╗
// ║  6. PATTERN RECOGNITION — WEIGHTED EUCLIDEAN ANALOG SEARCH                 ║            
// ╚════════════════════════════════════════════════════════════════════════════╝
var atrVals = atrCalc(i_atrLen);
var actualMatchesArr    = fillNull(n);
var weightedWinProbArr  = fillNull(n);
var avgWinArr           = fillNull(n);
var avgLossArr          = fillNull(n);
var expectedValueArr    = fillNull(n);
var consensusArr        = fillNull(n);
var winRateArr          = fillNull(n);
var avgWinAtrArr        = fillNull(n);
var avgLossAtrArr       = fillNull(n);
var searchStart = i_searchWin + i_projFwd + i_normLen + 5;
for (var i = searchStart; i < n; i++) {
    if (nD1[i] === null || nD2[i] === null || nD3[i] === null || nD4[i] === null) continue;
    var simArr = [];
    var retArr = [];
    var retArrAtr = [];
    var lowBound = Math.max(0, i - i_searchWin);
    var highBound = i - i_projFwd;
    for (var j = lowBound; j <= highBound; j++) {
        if (nD1[j] === null || nD2[j] === null || nD3[j] === null || nD4[j] === null) continue;
        var sq = 0;
        sq += normW1[i] * Math.pow(nD1[i] - nD1[j], 2);
        sq += normW2[i] * Math.pow(nD2[i] - nD2[j], 2);
        sq += normW3[i] * Math.pow(nD3[i] - nD3[j], 2);
        sq += normW4[i] * Math.pow(nD4[i] - nD4[j], 2);
        var dist = Math.sqrt(sq);
        var sim = 1.0 / (1.0 + dist);
        if (sim >= i_matchThr) {
            var fwdIdx = j + i_projFwd;
            var atrAtJ = nz(atrVals[j], 0);
            if (fwdIdx < n && close[j] !== 0 && atrAtJ > 0) {
                simArr.push(sim);
                retArr.push((close[fwdIdx] - close[j]) / close[j]);
                retArrAtr.push((close[fwdIdx] - close[j]) / atrAtJ);
            }
        }
    }
    var mLen = simArr.length;
    for (var a1 = 0; a1 < mLen - 1; a1++) {
        var bestIdx = a1;
        for (var a2 = a1 + 1; a2 < mLen; a2++) {
            if (simArr[a2] > simArr[bestIdx]) bestIdx = a2;
        }
        if (bestIdx !== a1) {
            var ts = simArr[a1]; simArr[a1] = simArr[bestIdx]; simArr[bestIdx] = ts;
            var tr = retArr[a1]; retArr[a1] = retArr[bestIdx]; retArr[bestIdx] = tr;
            var tra = retArrAtr[a1]; retArrAtr[a1] = retArrAtr[bestIdx]; retArrAtr[bestIdx] = tra;
        }
    }
    var actualMatches = Math.min(mLen, i_matchCount);
    actualMatchesArr[i] = actualMatches;
    if (actualMatches > 0) {
        var sumW = 0, sumWRet = 0, sumWWin = 0, sumWUpRet = 0, sumWUpW = 0, sumWDownRet = 0, sumWDownW = 0, winCnt = 0;
        var sumWUpRetAtr = 0, sumWDownRetAtr = 0;
        for (var kk = 0; kk < actualMatches; kk++) {
            var sim2 = simArr[kk], ret2 = retArr[kk], ret2Atr = retArrAtr[kk];
            sumW += sim2;
            sumWRet += sim2 * ret2;
            if (ret2 > 0) { winCnt += 1; sumWWin += sim2; sumWUpRet += sim2 * ret2; sumWUpW += sim2; sumWUpRetAtr += sim2 * ret2Atr; }
            else { sumWDownRet += sim2 * Math.abs(ret2); sumWDownW += sim2; sumWDownRetAtr += sim2 * Math.abs(ret2Atr); }
        }
        var wWinProb = sumW > 0 ? (sumWWin / sumW) : 0;
        var aWin = sumWUpW > 0 ? (sumWUpRet / sumWUpW) * 100.0 : 0;
        var aLoss = sumWDownW > 0 ? (sumWDownRet / sumWDownW) * 100.0 : 0;
        var ev = (wWinProb * aWin) - ((1.0 - wWinProb) * aLoss);
        weightedWinProbArr[i] = wWinProb;
        avgWinArr[i] = aWin;
        avgLossArr[i] = aLoss;
        expectedValueArr[i] = ev;
        consensusArr[i] = Math.max(Math.min(ev * 20.0, 100.0), -100.0);
        winRateArr[i] = (winCnt / actualMatches) * 100.0;
        avgWinAtrArr[i] = sumWUpW > 0 ? (sumWUpRetAtr / sumWUpW) : 0;
        avgLossAtrArr[i] = sumWDownW > 0 ? (sumWDownRetAtr / sumWDownW) : 0;
    } else {
        weightedWinProbArr[i] = 0; avgWinArr[i] = 0; avgLossArr[i] = 0;
        expectedValueArr[i] = 0; consensusArr[i] = 0; winRateArr[i] = 0;
        avgWinAtrArr[i] = 0; avgLossAtrArr[i] = 0;
    }
}
// ╔════════════════════════════════════════════════════════════════════════════╗
// ║  SIGNAL GENERATION — EXPECTED VALUE GATED                                  ║
// ╚════════════════════════════════════════════════════════════════════════════╝
var buyStateArr = fillNull(n), sellStateArr = fillNull(n);
for (var i = 0; i < n; i++) {
    var am = nz(actualMatchesArr[i], 0);
    var ev = nz(expectedValueArr[i], 0);
    var wp = nz(weightedWinProbArr[i], 0);
    buyStateArr[i] = (am >= i_minMatches && ev >= i_evThresh && wp > 0.5) ? 1 : 0;
    sellStateArr[i] = (am >= i_minMatches && ev <= -i_evThresh && wp < 0.5) ? 1 : 0;
}
var finalBuyArr = fillNull(n), finalSellArr = fillNull(n);
for (var i = 1; i < n; i++) {
    finalBuyArr[i] = (i_showSignals && buyStateArr[i] === 1 && buyStateArr[i - 1] === 0);
    finalSellArr[i] = (i_showSignals && sellStateArr[i] === 1 && sellStateArr[i - 1] === 0);
}
if (i_signalMode === 'Confirmed (Bar Close)' && n > 0) {
    finalBuyArr[n - 1] = false;
    finalSellArr[n - 1] = false;
}
// ╔════════════════════════════════════════════════════════════════════════════╗
// ║  DYNAMIC TP / SL ENGINE                                                    ║
// ╚════════════════════════════════════════════════════════════════════════════╝
var tpLineArr = fillNull(n), slLineArr = fillNull(n);
var tradeDir = 0, activeTp = null, activeSl = null, barsInTrade = 0;
var tradeStatus = 'Flat';
for (var i = 0; i < n; i++) {
    if (tradeDir !== 0) {
        barsInTrade += 1;
        if (tradeDir === 1 && high[i] >= activeTp) { tradeStatus = 'TP Hit (Long)'; tradeDir = 0; }
        else if (tradeDir === 1 && low[i] <= activeSl) { tradeStatus = 'SL Hit (Long)'; tradeDir = 0; }
        else if (tradeDir === -1 && low[i] <= activeTp) { tradeStatus = 'TP Hit (Short)'; tradeDir = 0; }
        else if (tradeDir === -1 && high[i] >= activeSl) { tradeStatus = 'SL Hit (Short)'; tradeDir = 0; }
        else if (barsInTrade >= i_projFwd) { tradeStatus = 'Time Exit'; tradeDir = 0; }
    }
    if (tradeDir === 0) { activeTp = null; activeSl = null; }
    if (finalBuyArr[i]) {
        activeTp = close[i] + (nz(avgWinAtrArr[i], 0) * nz(atrVals[i], 0));
        activeSl = close[i] - (nz(atrVals[i], 0) * i_atrMult);
        tradeDir = 1; barsInTrade = 0; tradeStatus = 'Long Active';
    } else if (finalSellArr[i]) {
        activeTp = close[i] - (nz(avgLossAtrArr[i], 0) * nz(atrVals[i], 0));
        activeSl = close[i] + (nz(atrVals[i], 0) * i_atrMult);
        tradeDir = -1; barsInTrade = 0; tradeStatus = 'Short Active';
    }
    tpLineArr[i] = i_showZones ? activeTp : null;
    slLineArr[i] = i_showZones ? activeSl : null;
}
// ╔════════════════════════════════════════════════════════════════════════════╗
// ║  9. VISUAL LAYER                                                           ║
// ╚════════════════════════════════════════════════════════════════════════════╝
var TH = {
    bull:    '#00FF88',
    bear:    '#FF3C00',
    bullDim: 'rgba(0,255,136,0.35)',
    bearDim: 'rgba(255,60,0,0.35)',
    glowBull:'rgba(0,255,136,0.16)',
    glowBear:'rgba(255,60,0,0.16)',
    zoneBull:'rgba(0,255,136,0.08)',
    zoneBear:'rgba(255,60,0,0.08)',
    gold:    '#FFD700',
    cyan:    '#00F5E9',
    d1:      '#00FF88',
    d2:      '#00D9FF',
    d3:      '#FFA500',
    d4:      '#FF3C60',
    panel:   '#0A0A14',
    border:  '#333344',
    a1:      '#00F5E9',
    a2:      '#9D4EDD',
    txt:     '#E2F1FF',
    dim:     '#8888AA'
};
var tiny = library('tinycolor2');
function rgba(h, a) { return tiny(h).setAlpha(a).toRgbString(); }
var glowBuyOuter = fillNull(n), glowBuyInner = fillNull(n), markerBuy = fillNull(n);
var glowSellOuter = fillNull(n), glowSellInner = fillNull(n), markerSell = fillNull(n);
for (var i = 0; i < n; i++) {
    if (finalBuyArr[i]) {
        if (i_glow) { glowBuyOuter[i] = '●'; glowBuyInner[i] = '●'; }
        markerBuy[i] = '▲';
    }
    if (finalSellArr[i]) {
        if (i_glow) { glowSellOuter[i] = '●'; glowSellInner[i] = '●'; }
        markerSell[i] = '▼';
    }
}
paint(glowBuyOuter,  { name: 'Buy Glow Outer',  style: 'labels_below', color: TH.glowBull, size: 'large' });
paint(glowBuyInner,  { name: 'Buy Glow Inner',  style: 'labels_below', color: TH.bullDim,  size: 'normal' });
paint(markerBuy,     { name: 'Buy Signal',      style: 'labels_below', color: TH.bull,     size: 'normal' });
paint(glowSellOuter, { name: 'Sell Glow Outer', style: 'labels_above', color: TH.glowBear, size: 'large' });
paint(glowSellInner, { name: 'Sell Glow Inner', style: 'labels_above', color: TH.bearDim,  size: 'normal' });
paint(markerSell,    { name: 'Sell Signal',     style: 'labels_above', color: TH.bear,     size: 'normal' });
var barColArr = fillNull(n);
for (var i = 0; i < n; i++) {
    if (!i_showBars) continue;
    var ev = expectedValueArr[i];
    if (ev === null) continue;
    if (ev >= i_evThresh) barColArr[i] = TH.bull;
    else if (ev <= -i_evThresh) barColArr[i] = TH.bear;
}
color_candles(barColArr, { name: 'EV Candle Color' });
paint(tpLineArr, { name: 'Take Profit', color: TH.bull, style: 'dotted', thickness: 2 });
paint(slLineArr, { name: 'Stop Loss',   color: TH.bear, style: 'dotted', thickness: 2 });
var bullZoneTop = fillNull(n), bullZoneBot = fillNull(n);
var bearZoneTop = fillNull(n), bearZoneBot = fillNull(n);
for (var i = 0; i < n; i++) {
    if (tpLineArr[i] === null || slLineArr[i] === null) continue;
    if (tpLineArr[i] > slLineArr[i]) { bullZoneTop[i] = tpLineArr[i]; bullZoneBot[i] = slLineArr[i]; }
    else { bearZoneTop[i] = slLineArr[i]; bearZoneBot[i] = tpLineArr[i]; }
}
color_cloud(bullZoneTop, bullZoneBot, TH.zoneBull, TH.zoneBull, 'Bull Zone Top', 'Bull Zone Bottom');
color_cloud(bearZoneTop, bearZoneBot, TH.zoneBear, TH.zoneBear, 'Bear Zone Top', 'Bear Zone Bottom');
var lastIdx = Math.max(n - 1, 0);
var tpLabelY = (n > 0 && tpLineArr[n - 1] !== null) ? tpLineArr[n - 1] : nz(close[lastIdx], 0);
var slLabelY = (n > 0 && slLineArr[n - 1] !== null) ? slLineArr[n - 1] : nz(close[lastIdx], 0);
var tpLabelText = (n > 0 && tpLineArr[n - 1] !== null) ? ('TP ' + fmtNum(tpLineArr[n - 1], 5)) : 'TP —';
var slLabelText = (n > 0 && slLineArr[n - 1] !== null) ? ('SL ' + fmtNum(slLineArr[n - 1], 5)) : 'SL —';
var tpLabelPts = fillNull(n); tpLabelPts[lastIdx] = tpLabelY;
var slLabelPts = fillNull(n); slLabelPts[lastIdx] = slLabelY;
var rTpLabel = paint(tpLabelPts, { name: 'TP Label Anchor', color: 'transparent', affects_scale: false, show_in_legend: false });
var rSlLabel = paint(slLabelPts, { name: 'SL Label Anchor', color: 'transparent', affects_scale: false, show_in_legend: false });
paint_label_at_line(rTpLabel, lastIdx, tpLabelText, { color: TH.bull, background_color: 'transparent', border_width: 0, vertical_align: 'middle' });
paint_label_at_line(rSlLabel, lastIdx, slLabelText, { color: TH.bear, background_color: 'transparent', border_width: 0, vertical_align: 'middle' });
register_signal(finalBuyArr, 'TED-PE Buy');
register_signal(finalSellArr, 'TED-PE Sell');
// ╔════════════════════════════════════════════════════════════════════════════╗
// ║  DASHBOARDS                                                                ║
// ╚════════════════════════════════════════════════════════════════════════════╝
var last = n - 1;
var l_nD1 = last >= 0 ? nD1[last] : null;
var l_nD2 = last >= 0 ? nD2[last] : null;
var l_nD3 = last >= 0 ? nD3[last] : null;
var l_nD4 = last >= 0 ? nD4[last] : null;
var l_w1 = last >= 0 ? normW1[last] : null;
var l_w2 = last >= 0 ? normW2[last] : null;
var l_w3 = last >= 0 ? normW3[last] : null;
var l_w4 = last >= 0 ? normW4[last] : null;
var l_matches = last >= 0 ? nz(actualMatchesArr[last], 0) : 0;
var l_winRate = last >= 0 ? nz(winRateArr[last], 0) : 0;
var l_wp = last >= 0 ? nz(weightedWinProbArr[last], 0) : 0;
var l_avgWin = last >= 0 ? nz(avgWinArr[last], 0) : 0;
var l_avgLoss = last >= 0 ? nz(avgLossArr[last], 0) : 0;
var l_ev = last >= 0 ? nz(expectedValueArr[last], 0) : 0;
var l_rr = l_avgLoss > 0 ? (l_avgWin / l_avgLoss) : null;
var e_d1 = Math.min(Math.abs(nz(l_nD1, 0)) * 2.5, 10.0);
var e_d2 = Math.min(Math.abs(nz(l_nD2, 0)) * 2.5, 10.0);
var e_d3 = Math.min(Math.abs(nz(l_nD3, 0)) * 2.5, 10.0);
var e_d4 = Math.min(Math.abs(nz(l_nD4, 0)) * 2.5, 10.0);
var totalEnergy = Math.abs(nz(l_nD1, 0)) + Math.abs(nz(l_nD2, 0)) + Math.abs(nz(l_nD3, 0)) + Math.abs(nz(l_nD4, 0));
var pctEnergy = Math.min((totalEnergy / 16.0) * 100.0, 100.0);
var energyColor = totalEnergy > 6.0 ? '#FF3C00' : totalEnergy > 4.0 ? '#FFA500' : totalEnergy > 2.0 ? '#9D4EDD' : '#666677';
function dirArrow(v) { return nz(v, 0) > 0 ? '▲ UP' : '▼ DN'; }
function dirColor(v) { return nz(v, 0) > 0 ? TH.bull : TH.bear; }
function mkCell(t, c, a, b, cs, bg) { return { text: String(t), color: c || TH.txt, textAlign: a || 'left', fontSize: 10, fontWeight: b ? 'bold' : 'normal', colspan: cs || 1, background: bg || TH.panel }; }
function mkSub(t, c, bg) { return { text: String(t), color: c || TH.a1, background: bg || rgba(TH.a1, 0.08), textAlign: 'center', fontSize: 9, fontWeight: 'bold', colspan: 2 }; }
var statsRows = [];
if (i_theme !== 'Off') {
    var statusColor = tradeDir === 1 ? TH.bull : (tradeDir === -1 ? TH.bear : TH.dim);
    statsRows.push({ cells: [ mkCell('⟡ TED-PE STATS', TH.a1, 'center', true, 2, TH.panel) ] });
    var barsNeeded = i_searchWin + i_projFwd + i_normLen + 5;
    var barsOk = n >= barsNeeded;
    statsRows.push({ cells: [ mkCell('Bars Loaded / Needed', TH.dim, 'left', false, 1), mkCell(n + ' / ' + barsNeeded, barsOk ? TH.bull : TH.bear, 'right', true, 1) ] });
    if (!barsOk) {
        statsRows.push({ cells: [ { text: '⚠ Not enough history — lower Search Depth', color: '#ffffff', background: rgba(TH.bear, 0.35), colspan: 2, textAlign: 'center', fontSize: 8.5, fontWeight: 'bold' } ] });
    }
    statsRows.push({ cells: [ mkCell('d1 Velocity', TH.dim, 'left', false, 1), mkCell(fmtNum(l_w1, 2) + 'x', TH.d1, 'right', true, 1) ] });
    statsRows.push({ cells: [ mkCell('d2 Accel', TH.dim, 'left', false, 1), mkCell(fmtNum(l_w2, 2) + 'x', TH.d2, 'right', true, 1) ] });
    if (i_theme === 'Full') {
        statsRows.push({ cells: [ mkCell('d3 Jerk', TH.dim, 'left', false, 1), mkCell(fmtNum(l_w3, 2) + 'x', TH.d3, 'right', true, 1) ] });
        statsRows.push({ cells: [ mkCell('d4 Snap', TH.dim, 'left', false, 1), mkCell(fmtNum(l_w4, 2) + 'x', TH.d4, 'right', true, 1) ] });
    }
    statsRows.push({ cells: [ mkSub('» ANALOG SEARCH') ] });
    statsRows.push({ cells: [ mkCell('Analogs / Win%', TH.dim, 'left', false, 1), mkCell(l_matches + ' / ' + fmtNum(l_winRate, 1) + '%', TH.txt, 'right', true, 1) ] });
    statsRows.push({ cells: [ mkCell('Weighted WinProb', TH.dim, 'left', false, 1), mkCell(fmtNum(l_wp * 100.0, 1) + '%', l_wp > 0.5 ? TH.bull : TH.bear, 'right', true, 1) ] });
    if (i_theme === 'Full') {
        statsRows.push({ cells: [ mkCell('Avg Win / Loss', TH.dim, 'left', false, 1), mkCell(fmtNum(l_avgWin, 2) + '% / ' + fmtNum(l_avgLoss, 2) + '%', TH.txt, 'right', true, 1) ] });
        statsRows.push({ cells: [ mkCell('Reward:Risk', TH.dim, 'left', false, 1), mkCell(l_rr === null ? 'n/a' : fmtNum(l_rr, 2), TH.txt, 'right', true, 1) ] });
    }
    statsRows.push({ cells: [ mkCell('Expected Value', TH.dim, 'left', false, 1), mkCell(fmtNum(l_ev, 3) + '%', l_ev >= 0 ? TH.bull : TH.bear, 'right', true, 1) ] });
    statsRows.push({ cells: [ { text: tradeStatus, color: '#ffffff', background: statusColor, colspan: 2, textAlign: 'center', fontSize: 9, fontWeight: 'bold' } ] });
}
paint_overlay('TED-PE Stats Dashboard', { position: 'top_right', order: 'above_all' }, { background: rgba(TH.panel, 0.95), border: '1px solid ' + TH.border, borderRadius: 4, width: 200, rows: statsRows });
var energyRows = [];
if (i_theme === 'Full') {
    energyRows.push({ cells: [ mkCell('⚡ DERIVATIVE ENERGY', TH.a2, 'center', true, 2, TH.panel) ] });
    energyRows.push({ cells: [ mkCell('d1 ' + dirArrow(l_nD1), dirColor(l_nD1), 'left', false, 1), mkCell(barString(e_d1), dirColor(l_nD1), 'right', false, 1) ] });
    energyRows.push({ cells: [ mkCell('d2 ' + dirArrow(l_nD2), dirColor(l_nD2), 'left', false, 1), mkCell(barString(e_d2), dirColor(l_nD2), 'right', false, 1) ] });
    energyRows.push({ cells: [ mkCell('d3 ' + dirArrow(l_nD3), dirColor(l_nD3), 'left', false, 1), mkCell(barString(e_d3), dirColor(l_nD3), 'right', false, 1) ] });
    energyRows.push({ cells: [ mkCell('d4 ' + dirArrow(l_nD4), dirColor(l_nD4), 'left', false, 1), mkCell(barString(e_d4), dirColor(l_nD4), 'right', false, 1) ] });
    energyRows.push({ cells: [
        { text: 'Total Energy', color: '#ffffff', background: energyColor, textAlign: 'left', fontSize: 9, fontWeight: 'bold' },
        { text: fmtNum(totalEnergy, 2) + ' (' + fmtNum(pctEnergy, 1) + '%)', color: '#ffffff', background: energyColor, textAlign: 'right', fontSize: 9, fontWeight: 'bold' }
    ] });
}
paint_overlay('TED-PE Energy Dashboard', { position: 'bottom_right', order: 'above_all' }, { background: rgba(TH.panel, 0.95), border: '1px solid ' + TH.border, borderRadius: 4, width: 220, rows: energyRows });</code>