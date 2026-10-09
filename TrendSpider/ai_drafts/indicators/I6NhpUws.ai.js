describe_indicator('Volume with Alert', 'lower');

// ── INPUTS ──────────────────────────────────────────────────────────
const myThreshold = input.number('Alert Volume Threshold', 1000, { min: 0 });
const myMaLength = input.number('Volume MA Length', 20, { min: 1 });

// ── CALCULATIONS ────────────────────────────────────────────────────
const myVol = volume;
const myMaVol = sma(myVol, myMaLength);
const myIsBullish = for_every(close, open, (_c, _o) => _c >= _o);
const myTriggered = for_every(myVol, _v => _v >= myThreshold);

// Column color: yellow if triggered, else teal/red based on candle direction
const myFinalColor = for_every(myIsBullish, myTriggered, (_bull, _trig) => {
	if (_trig) return '#FFEB3B';
	return _bull ? '#009688' : '#F44336';
});

// ── PLOTS ───────────────────────────────────────────────────────────
paint(myVol, { name: 'Volume', style: 'column', color: myFinalColor });
paint(myMaVol, { name: 'VolumeMovingAverage', color: '#2962FF', thickness: 1 });
paint(horizontal_line(myThreshold), { name: 'ThresholdLine', color: '#FF9800', style: 'dotted' });

// ── SIGNAL (for scanners/alerts/strategies) ───────────────────────────
register_signal(myTriggered, 'Volume exceeds threshold');