<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('SMA MAD SuperTrend | Alpha Scope');

// Inputs
const src = input.select('Source', 'close', constants.price_source_options);
const price = market[src];
const smaLen = input.number('SMA Length', 25, { min: 1, max: 500 });
const factorValue = input.number('Factor', 2.3, { min: 0.05, max: 10 });
const madLen = input.number('MAD Length', 25, { min: 1, max: 500 });

// Compute SMA
const mySma = sma(price, smaLen);

// Compute Mean Absolute Deviation (MAD)
const myMad = absdev(price, madLen);

// SMA MAD SuperTrend calculation
const smaMadSupertrend = for_every(price, mySma, myMad, (_price, _sma, _mad, prevValue, index) => {
    if (index === 0) {
        return { st: null, dir: 1 };
    }
    
    const myUpperband = _sma + factorValue * _mad;
    const myLowerband = _sma - factorValue * _mad;
    
    const prevUpperband = prevValue?.upperband ?? myUpperband;
    const prevLowerband = prevValue?.lowerband ?? myLowerband;
    const prevClose = price[index - 1];
    
    const upperband = myUpperband < prevUpperband || prevClose > prevUpperband ? myUpperband : prevUpperband;
    const lowerband = myLowerband > prevLowerband || prevClose < prevLowerband ? myLowerband : prevLowerband;
    
    let myDir;
    const prevSt = prevValue?.st ?? null;
    const prevDir = prevValue?.dir ?? 1;
    
    if (prevValue?.mad === null) {
        myDir = 1;
    } else if (prevSt === prevUpperband) {
        myDir = _price > upperband ? -1 : 1;
    } else {
        myDir = _price < lowerband ? 1 : -1;
    }
    
    const mySt = myDir === -1 ? lowerband : upperband;
    
    return { st: mySt, dir: myDir, upperband, lowerband, mad: _mad };
});

const stValues = smaMadSupertrend.map(v => v?.st ?? null);
const dirValues = smaMadSupertrend.map(v => v?.dir ?? 1);
const upperbandValues = smaMadSupertrend.map(v => v?.upperband ?? null);
const lowerbandValues = smaMadSupertrend.map(v => v?.lowerband ?? null);
const stLong = dirValues.map(d => d < 0);
const stShort = dirValues.map(d => d > 0);

// Compute AS for entire series
const as = [];
for (let i = 0; i < close.length; i++) {
    const currentLong = stLong[i];
    const currentShort = stShort[i];
    const prevAs = i > 0 ? as[i - 1] : 0;
    
    if (currentLong && !currentShort) {
        as.push(1);
    } else if (currentShort) {
        as.push(-1);
    } else {
        as.push(prevAs);
    }
}

// Colors
const asGreen = '#1fd325';
const asPurple = '#bc08db';
const colors = for_every(close, (_, index) => {
    return as[index] === 1 ? asGreen : as[index] === -1 ? asPurple : null;
});

// Plotting
const stUp = for_every(dirValues, stValues, (_dir, _st) => _dir < 0 ? _st : null);
const stDown = for_every(dirValues, stValues, (_dir, _st) => _dir > 0 ? _st : null);
const stUpPainted = paint(stUp, { name: 'ST UP', color: asGreen, style: 'line' });
const stDownPainted = paint(stDown, { name: 'ST Down', color: asPurple, style: 'line' });

const myOc2 = div(add(open, close), 2);
const oc2Painted = paint(myOc2, { name: 'Plot oc2', color: colors });

// Fill between bands and oc2
fill(stUpPainted, oc2Painted, asGreen, 0.15);
fill(stDownPainted, oc2Painted, asPurple, 0.15);

// Color candles
color_candles(colors);

// Register signals for alerts
const asLongSignal = for_every(close, (_, index) => {
    if (index === 0) return false;
    const prevAs = as[index - 1];
    const currentAs = as[index];
    return prevAs <= 0 && currentAs > 0;
});

const asShortSignal = for_every(close, (_, index) => {
    if (index === 0) return false;
    const prevAs = as[index - 1];
    const currentAs = as[index];
    return prevAs >= 0 && currentAs < 0;
});

register_signal(asLongSignal, 'SMA MAD SuperTrend Long');
register_signal(asShortSignal, 'SMA MAD SuperTrend Short');
</code>