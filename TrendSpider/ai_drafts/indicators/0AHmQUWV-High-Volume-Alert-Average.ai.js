describe_indicator('High Volume Alert (Above Average)', 'lower');

const myLookback = input.number('Lookback Period (candles)', 20, { min: 1, max: 500 });

// Average volume of the last `myLookback` candles, excluding the
// current (still-forming) candle. Shifting volume by 1 before
// computing the SMA reproduces Pine's `ta.sma(volume[1], lookback)`.
const myAvgVol = sma(shift(volume, 1), myLookback);

// Condition: current volume greater than the average of the
// previous `myLookback` candles.
const myVolumeSpike = for_every(volume, myAvgVol, (_v, _a) => _v > _a);

const myVolColor = for_every(myVolumeSpike, _s => _s ? 'red' : 'gray');

paint(volume, { name: 'Volume', style: 'column', color: myVolColor });
paint(myAvgVol, { name: 'Average Volume', color: 'orange', thickness: 1 });

// Marker shown above the volume column when a spike occurs
const myMarker = for_every(myVolumeSpike, _s => _s ? constants.icons.triangle_up : null);
paint(myMarker, { name: 'Volume Spike Marker', style: 'labels_above', color: 'red' });

// Signal usable in scanners, alerts and the strategy tester
register_signal(myVolumeSpike, 'Volume Above Average');