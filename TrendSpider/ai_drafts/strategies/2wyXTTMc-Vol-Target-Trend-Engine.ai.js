// ─────────────────────────────────────────────────────────────────
// EXPERIMENTAL CONVERSION NOTICE:
// The original Pine script is a full STRATEGY: it tracks actual
// position size, equity, and executes scaled orders over time
// (strategy.equity, strategy.position_size, strategy.order, etc).
// TrendSpider Custom JS indicators have no concept of equity curves,
// live position size or order execution state - there is no
// "portfolio simulation" API available here. This indicator can only
// reproduce the SIGNAL / REGIME / TARGET-EXPOSURE math (which is
// deterministic and does not depend on broker state), not the actual
// held position size, which depended on path-dependent order fills.
// "Held exposure" below is therefore approximated as the computed
// TARGET exposure (frac), not a true simulated held position.
// ─────────────────────────────────────────────────────────────────
describe_indicator('Vol Target Trend Engine', 'price');

const myParamsTab = input.tab('Parameters');
// Input titles shortened below (platform limits input name length)
const myVolLen = myParamsTab.number('Vol Lookback Days', 20, { min: 5, max: 500 });
const myTargetVol = myParamsTab.number('Target Ann Vol Percent', 45, { min: 5, max: 300 });
const mySmaLen = myParamsTab.number('Regime SMA Length', 200, { min: 50, max: 500 });
const myBand = myParamsTab.number('Rebalance Band Percent', 10, { min: 1, max: 100 });
const myFastDrisk = myParamsTab.boolean('Fast Derisk At 1.5x', true);

// Daily return
const myRetD = div(sub(close, shift(close, 1)), shift(close, 1));

// Realized annualized vol (percent)
const mySqrt252x100 = Math.sqrt(252) * 100;
const myRealVol = mult(stdev(myRetD, myVolLen), mySqrt252x100);

// Regime SMA and gate
const mySmaReg = sma(close, mySmaLen);
const myRegime = for_every(close, mySmaReg, (_c, _s) => _c > _s);

// Target exposure fraction (vol targeting), capped at 100%
const myFrac = for_every(myRealVol, _r => Math.min(1, myTargetVol / Math.max(_r, 1)));
const myTargetExpPct = mult(myFrac, 100);

// Regime flip detection
const myRegimeShifted = shift(myRegime, 1);
const myRegimeFlip = for_every(myRegime, myRegimeShifted, (_cur, _prev, _p, _idx) => _idx > 0 && _cur !== _prev);
const myRiskOn = for_every(myRegime, myRegimeShifted, (_cur, _prev, _p, _idx) => _idx > 0 && _cur && !_prev);
const myRiskOff = for_every(myRegime, myRegimeShifted, (_cur, _prev, _p, _idx) => _idx > 0 && !_cur && _prev);

// Weekly turn detection (proxy for timeframe.change("1W"))
const myWeekOfYear = time.map(_t => time_of(_t).weekOfYear);
const myWeekOfYearShifted = shift(myWeekOfYear, 1);
const myWeekTurn = for_every(myWeekOfYear, myWeekOfYearShifted, (_cur, _prev, _p, _idx) => _idx > 0 && _cur !== _prev);

// Rebalance trigger proxy: approximates "weekTurn or regimeFlip or overExp"
// NOTE: true overExp requires live position size which is not available,
// so this trigger only reproduces the weekTurn/regimeFlip part exactly.
const myRebalanceTrigger = for_every(myWeekTurn, myRegimeFlip, (_w, _f) => _w || _f);

// Colors
const myColUp = '#26a69a';
const myColDn = '#ef5350';
const mySmaColor = for_every(myRegime, _r => _r ? myColUp : myColDn);
const mySmaLinePainted = paint(mySmaReg, { name: 'Regime SMA', color: mySmaColor, thickness: 2 });

// Risk on/off markers
const myRiskOnMarks = for_every(myRiskOn, _r => _r ? constants.icons.triangle_up : null);
const myRiskOffMarks = for_every(myRiskOff, _r => _r ? constants.icons.triangle_down : null);

paint(myRiskOnMarks, { style: 'labels_below', color: myColUp, name: 'Risk On' });
paint(myRiskOffMarks, { style: 'labels_above', color: myColDn, name: 'Risk Off' });

// Background tint approximation via candle coloring
const myCandleColors = for_every(myRegime, myTargetExpPct, (_r, _exp) => {
	const myAlpha = _r ? Math.min(0.35, Math.max(0.03, (_exp / 100) * 0.3)) : 0.12;
	const myBaseColor = _r ? '38,166,154' : '239,83,80';
	return `rgba(${myBaseColor}, ${myAlpha})`;
});
color_candles(myCandleColors);

// Table overlay with current stats
const myLastIndex = close.length - 1;
const myRegimeNow = myRegime[myLastIndex];
const myRealVolNow = myRealVol[myLastIndex];
const myTargetExpNow = myTargetExpPct[myLastIndex];

paint_overlay('VTTEStats', { position: 'top_right' }, {
	rows: [
		{ cells: [{ text: 'VTTE', color: '#d1d4dc' }, { text: myRegimeNow ? 'RISK ON' : 'RISK OFF', color: myRegimeNow ? myColUp : myColDn }] },
		{ cells: [{ text: 'Realized Vol', color: '#d1d4dc' }, { text: (myRealVolNow == null ? 'n/a' : myRealVolNow.toFixed(1) + '%'), color: '#d1d4dc' }] },
		{ cells: [{ text: 'Target Exposure', color: '#d1d4dc' }, { text: (myTargetExpNow == null ? 'n/a' : myTargetExpNow.toFixed(1) + '%'), color: '#d1d4dc' }] },
		{ cells: [{ text: 'Vol Target', color: '#d1d4dc' }, { text: myTargetVol + '%', color: '#d1d4dc' }] }
	]
});

// Signals for scanners, alerts and strategy tester
register_signal(myRegime, 'Regime Risk On');
register_signal(myRiskOn, 'Risk On Flip');
register_signal(myRiskOff, 'Risk Off Flip');
register_signal(myWeekTurn, 'Weekly Rebalance Window');
register_signal(myRebalanceTrigger, 'Rebalance Trigger Proxy');