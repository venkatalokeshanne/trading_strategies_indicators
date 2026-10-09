describe_indicator('VASA Position Size and ATR Stop', 'price');

// ---------- Inputs ----------
const groupAccount = input.group('Account and Risk');
const myAccountSize = groupAccount.number('Account size', 10000, { min: 0, step: 100 });
const myRiskPercent = groupAccount.number('Risk percent', 1.0, { min: 0.01, max: 100, step: 0.1 });
// shortened title (platform rejects overly long input titles)
const myDirectionLong = groupAccount.boolean('Direction Long', true);

const groupEntryStop = input.group('Entry and Stop');
// shortened title (platform rejects overly long input titles)
const myUseClose = groupEntryStop.boolean('Entry equals Close', true);
const myManualEntry = groupEntryStop.number('Manual entry price', 0.0, { min: 0 });
const myAtrLength = groupEntryStop.number('ATR length', 14, { min: 1 });
const myAtrMultiplier = groupEntryStop.number('ATR multiplier', 1.5, { min: 0.1, step: 0.1 });

const groupStyle = input.group('Style');
const myTablePosition = groupStyle.select('Table position', 'bottom_right', ['top_right', 'top_left', 'bottom_right', 'bottom_left']);
const myShowLines = groupStyle.boolean('Draw lines', true);

// ---------- Calculation ----------
// Non-repainting: uses current (settled) bar's ATR
const myAtrValue = atr(high, low, close, myAtrLength);
const myEntry = myUseClose ? close : series_of(myManualEntry);
const myStopDistance = mult(myAtrValue, myAtrMultiplier);
const myStop = myDirectionLong
	? sub(myEntry, myStopDistance)
	: add(myEntry, myStopDistance);

const myRiskCash = myAccountSize * myRiskPercent / 100.0;
const myRiskPerUnit = for_every(myEntry, myStop, (_e, _s) => Math.abs(_e - _s));
// qty is null (na) whenever riskPerUnit is 0 or negative
const myQty = for_every(myRiskPerUnit, _r => _r > 0 ? myRiskCash / _r : null);

// ---------- Lines ----------
const myEntryLinePainted = paint(myShowLines ? myEntry : constants.empty_series, {
	name: 'Entry',
	color: '#2563eb',
	thickness: 1,
	style: 'line'
});

const myStopLinePainted = paint(myShowLines ? myStop : constants.empty_series, {
	name: 'ATRStop',
	color: '#b91c1c',
	thickness: 1,
	style: 'line'
});

// ---------- Table (last bar only) ----------
const myLastIndex = close.length - 1;
const myDirectionText = myDirectionLong ? 'LONG' : 'SHORT';
const myDirectionColor = myDirectionLong ? '#15803d' : '#b91c1c';
const myEntryText = myEntry[myLastIndex] != null ? myEntry[myLastIndex].toFixed(current.decimals) : 'n/a';
const myStopText = myStop[myLastIndex] != null ? myStop[myLastIndex].toFixed(current.decimals) : 'n/a';
const myStopDistanceText = myStopDistance[myLastIndex] != null ? myStopDistance[myLastIndex].toFixed(current.decimals) : 'n/a';
const myRiskCashText = myRiskCash.toFixed(2);
const myQtyValue = myQty[myLastIndex];
const myQtyText = myQtyValue == null ? 'n/a' : `${myQtyValue.toFixed(4)} units`;

paint_overlay('VASARiskTable', { position: myTablePosition }, {
	rows: [
		{ cells: [{ text: 'Direction', background_color: '#16233b', color: 'white' }, { text: myDirectionText, color: myDirectionColor }] },
		{ cells: [{ text: 'Entry', background_color: '#16233b', color: 'white' }, { text: myEntryText, color: 'white' }] },
		{ cells: [{ text: 'ATR stop', background_color: '#16233b', color: 'white' }, { text: myStopText, color: '#b91c1c' }] },
		{ cells: [{ text: 'Stop distance', background_color: '#16233b', color: 'white' }, { text: myStopDistanceText, color: 'white' }] },
		{ cells: [{ text: 'Risk dollars', background_color: '#16233b', color: 'white' }, { text: myRiskCashText, color: 'white' }] },
		{ cells: [{ text: 'Position size', background_color: '#16233b', color: 'white' }, { text: myQtyText, color: '#2563eb' }] }
	]
});

// ---------- Signals for Scanners, Alerts and Strategy Tester ----------
const mySignalLong = series_of(myDirectionLong);
const mySignalShort = series_of(!myDirectionLong);
const mySignalQtyValid = for_every(myQty, _q => _q != null && _q > 0);

register_signal(mySignalLong, 'Direction Long');
register_signal(mySignalShort, 'Direction Short');
register_signal(mySignalQtyValid, 'Valid Position Size');