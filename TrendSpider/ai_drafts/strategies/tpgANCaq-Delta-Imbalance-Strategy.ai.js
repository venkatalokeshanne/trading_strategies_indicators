describe_indicator('Delta Imbalance Strategy', 'lower');

// NOTE: TrendSpider Custom JS indicators cannot place real orders
// (strategy.entry / strategy.exit from Pine have no equivalent here).
// This script reproduces the Pine math exactly and exposes the
// resulting Long/Short resolve signals via register_signal(), so they
// can be used in Scanners, Alerts and the Strategy Tester visual
// script tooling. Actual stop/limit order management must be done
// in TrendSpider's Strategy Tester using these signals.

const myDecay = input.number('Imbalance Decay', 0.95, { min: 0, max: 1, step: 0.001 });
const myThreshold = input.number('Threshold Mult', 1.5, { min: 0, max: 10, step: 0.1 });
const myAtrLength = input.number('ATR Length', 14, { min: 1, max: 100 });

// delta = (close - open) * volume
const myDelta = mult(sub(close, open), volume);
const myAbsDelta = for_every(myDelta, _d => Math.abs(_d));
const myAvgDelta = sma(myAbsDelta, 50);

// Recursive bull imbalance ledger:
// accumulate on positive delta, resolve on negative delta,
// clamp to 0, then apply decay - exactly as in the Pine script.
const myBullImbalance = for_every(myDelta, (_d, _prev, _i) => {
	const myPrevValue = _i === 0 ? 0 : _prev;
	let myValue = _d > 0 ? myPrevValue + _d : myPrevValue - Math.abs(_d);
	myValue = Math.max(myValue, 0);
	myValue *= myDecay;
	return myValue;
});

// Recursive bear imbalance ledger (mirror logic).
const myBearImbalance = for_every(myDelta, (_d, _prev, _i) => {
	const myPrevValue = _i === 0 ? 0 : _prev;
	let myValue = _d < 0 ? myPrevValue + Math.abs(_d) : myPrevValue - Math.abs(_d);
	myValue = Math.max(myValue, 0);
	myValue *= myDecay;
	return myValue;
});

// Normalization
const myBullStrength = div(myBullImbalance, myAvgDelta);
const myBearStrength = div(myBearImbalance, myAvgDelta);

// Signal logic
const myBullPeak = for_every(myBullStrength, _s => _s > myThreshold);
const myBearPeak = for_every(myBearStrength, _s => _s > myThreshold);

const myResolveShort = for_every(myBullPeak, myDelta, (_peak, _d) => _peak && _d < 0);
const myResolveLong = for_every(myBearPeak, myDelta, (_peak, _d) => _peak && _d > 0);

// Risk management reference values (ATR based stop/limit), provided
// as context only; actual order placement is not available here.
const myAtr = atr(high, low, close, myAtrLength);
const myLongStop = sub(close, mult(myAtr, 2));
const myLongLimit = add(close, mult(myAtr, 3));
const myShortStop = add(close, mult(myAtr, 2));
const myShortLimit = sub(close, mult(myAtr, 3));

register_signal(myResolveLong, 'Resolve Long');
register_signal(myResolveShort, 'Resolve Short');

paint(myBullStrength, { name: 'Bull Imbalance', color: '#2ca599', thickness: 2 });
paint(myBearStrength, { name: 'Bear Imbalance', color: '#ee5451', thickness: 2 });
paint(horizontal_line(myThreshold), { name: 'Threshold', color: 'gray', style: 'dotted' });