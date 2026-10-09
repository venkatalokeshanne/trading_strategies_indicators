describe_indicator('Volume Plus 20 SMA Plus Pocket Pivot', 'lower');

// ---------- Inputs ----------
const myMaLen = input.number('Volume SMA length', 20, { min: 1, max: 500 });
const myPpLookback = input.number('Pocket pivot lookback bars', 10, { min: 1, max: 200 });
const myCompareAll = input.boolean('Compare vs ALL days volume', false);
const myUsePriceMA = input.boolean('Stricter: require close above 10 day price SMA', false);
const myShowOnPrice = input.boolean('Show pocket pivot marker on price chart', true);

// ---------- Volume + moving average ----------
const myVolSma = sma(volume, myMaLen);
const myPrevClose = shift(close, 1);
const myUpDay = for_every(close, myPrevClose, (_c, _pc) => _c > _pc);

// ---------- Pocket pivot logic ----------
// Volume counted only on down days (0 on up days)
const myDownDayVol = for_every(close, myPrevClose, volume, (_c, _pc, _v) => _c < _pc ? _v : 0);

// Highest down-day volume over the PRIOR lookback bars (today excluded)
const myMaxDownVol = highest(shift(myDownDayVol, 1), myPpLookback);

// Highest volume of ALL prior lookback bars (up + down days)
const myMaxAllVol = highest(shift(volume, 1), myPpLookback);

// Threshold: classic PP compares vs down days only; toggle to compare vs every day
const myVolThresh = myCompareAll ? myMaxAllVol : myMaxDownVol;

// Optional trend filter (part of the classic Morales/Kacher definition)
const mySma10 = sma(close, 10);
const myPriceOk = for_every(close, mySma10, (_c, _s) => !myUsePriceMA || _c > _s);

const myPocketPivot = for_every(myUpDay, volume, myVolThresh, myPriceOk, (_up, _v, _thresh, _ok) => _up && _v > _thresh && _ok);

// ---------- Plots ----------
const myVolumeColor = for_every(myUpDay, _up => _up ? 'teal' : 'red');
paint(volume, { name: 'Volume', style: 'column', color: myVolumeColor });
paint(myVolSma, { name: 'Volume SMA', color: 'orange', thickness: 2 });

// Marker just above the volume bar on pocket pivot days
const myPpVolumeMarker = for_every(myPocketPivot, volume, (_pp, _v) => _pp ? _v * 1.05 : null);
paint(myPpVolumeMarker, { name: 'Pocket Pivot Marker', style: 'labels_above', color: 'yellow' });

// Optional marker on the main price chart (triangle under the PP day's candle)
const myPpPriceMarker = for_every(myPocketPivot, low, (_pp, _l) => (myShowOnPrice && _pp) ? _l : null);
paint(myPpPriceMarker, { name: 'Pocket Pivot Price', style: 'labels_below', color: 'yellow', forceUsePriceAxis: true });

// ---------- Signal for scanners, alerts, strategies ----------
register_signal(myPocketPivot, 'Pocket Pivot');