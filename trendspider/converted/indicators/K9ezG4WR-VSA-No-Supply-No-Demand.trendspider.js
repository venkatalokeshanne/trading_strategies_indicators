/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : VSA No Supply No Demand
 * Author       : chartnow606
 * Source URL   : https://www.tradingview.com/script/K9ezG4WR-VSA-No-Supply-No-Demand
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : VSA No Supply No Demand_TV
 *
 * Deviations from the original: Reviewed AI draft; syminfo.mintick replaced by a Min Tick input (default 0.01);
 *   ND/NS text as icons.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('VSA No Supply No Demand_TV', 'price');
const myCount = input.number('NSND Count', 10, { min: 1, max: 100 });
const myPip = input.number('Min Tick', 0.01, { min: 0.00000001, step: 0.01 });
const myDir = close.map((_c, _i) => open[_i] > _c ? 'Bear' : (_c > open[_i] ? 'Bull' : ''));
const myNoDemand = close.map(() => false);
const myNoSupply = close.map(() => false);
for (let myI = 0; myI < close.length; myI += 1) {
	const myD = myDir[myI];
	const myLowVol = myI >= 2 ? (volume[myI] < volume[myI - 1] && volume[myI] < volume[myI - 2]) : false;
	let myPins = false;
	if (myD === 'Bear') myPins = high[myI] > open[myI] + myPip && low[myI] < close[myI] - myPip;
	if (myD === 'Bull') myPins = high[myI] > close[myI] + myPip && low[myI] < open[myI] - myPip;
	let myBearBelow = false, myBearAbove = false, myBullAbove = false, myBullBelow = false;
	if (myI >= myCount) {
		for (let myK = 0; myK < myCount; myK += 1) {
			const myC = close[myI - myK];
			if (myD === 'Bear') { if (myC < low[myI]) myBearBelow = true; if (myC > high[myI]) myBearAbove = true; }
			if (myD === 'Bull') { if (myC > high[myI]) myBullAbove = true; if (myC < low[myI]) myBullBelow = true; }
		}
	}
	myNoDemand[myI] = myD === 'Bull' && myLowVol && myPins && !myBullAbove && myBullBelow;
	myNoSupply[myI] = myD === 'Bear' && myLowVol && myPins && !myBearBelow && myBearAbove;
}
paint(myNoDemand.map(_f => _f ? constants.icons.triangle_down : null), { name: 'No Demand Mark', style: 'labels_above', color: 'red' });
paint(myNoSupply.map(_f => _f ? constants.icons.triangle_up : null), { name: 'No Supply Mark', style: 'labels_below', color: 'lime' });
register_signal(myNoDemand, 'No Demand');
register_signal(myNoSupply, 'No Supply');
