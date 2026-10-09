describe_indicator('Gann HiLo Activator', 'price');

// Length for the SMA used in the HiLo calculation
const myLength = input.number('Length', 3, { min: 1 });

// Mode: "End of Day" shifts the plotted line forward by 1 bar
// (as Pine's plot offset=1 does), "Real Time" keeps offset=0
const myMode = input.select('Mode', 'End of Day', ['End of Day', 'Real Time']);
const myPlotOffset = myMode === 'End of Day' ? 1 : 0;

const myHi = sma(high, myLength);
const myLo = sma(low, myLength);

// Recursive state: hl stays at previous value unless close breaks
// above hi (switch to uptrend) or below lo (switch to downtrend)
const myHl = for_every(close, myHi, myLo, (_close, _hi, _lo, _prev) => {
	if (_close > _hi) return 1;
	if (_close < _lo) return -1;
	return _prev === undefined ? null : _prev;
});

// ghla = hi when in downtrend (hl == -1), lo when in uptrend
const myGhla = for_every(myHl, myHi, myLo, (_hl, _hi, _lo) => _hl === -1 ? _hi : _lo);

const myUpRaw = for_every(myHl, myGhla, (_hl, _g) => _hl > 0 ? _g : null);
const myDownRaw = for_every(myHl, myGhla, (_hl, _g) => _hl < 0 ? _g : null);

// Apply the Pine "plot offset" by shifting the plotted series forward
const myUpLine = shift(myUpRaw, myPlotOffset);
const myDownLine = shift(myDownRaw, myPlotOffset);

paint(myUpLine, { name: 'HiLoUp', color: 'green', style: 'line', thickness: 2 });
paint(myDownLine, { name: 'HiLoDown', color: 'red', style: 'line', thickness: 2 });

// Signals for scanner/alerts/strategy use (based on unshifted, non-repainting state)
const myIsUptrend = for_every(myHl, _hl => _hl > 0);
const myIsDowntrend = for_every(myHl, _hl => _hl < 0);
const myFlipToUp = for_every(myHl, (_hl, _prev, _idx) => _idx > 0 && _hl > 0 && myHl[_idx - 1] <= 0);
const myFlipToDown = for_every(myHl, (_hl, _prev, _idx) => _idx > 0 && _hl < 0 && myHl[_idx - 1] >= 0);

register_signal(myIsUptrend, 'HiLo Uptrend');
register_signal(myIsDowntrend, 'HiLo Downtrend');
register_signal(myFlipToUp, 'HiLo Flip To Up');
register_signal(myFlipToDown, 'HiLo Flip To Down');