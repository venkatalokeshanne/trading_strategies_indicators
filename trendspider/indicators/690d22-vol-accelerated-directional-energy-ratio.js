<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Vol. Accelerated Directional Energy Ratio', 'lower');

// ===========================================================================================================
//      Inputs
// ===========================================================================================================
const length = input.number('Length', 10, { min: 1 });
const DER_avg = input.number('DER Average', 5, { min: 1 });
const MA_Type = input.select('DER MA Type', 'wma', constants.ma_types);
const smooth = input.number('Smooth', 3, { min: 1 });
const show_senti = input.boolean('Show Sentiment', false);
const senti = input.number('Sentiment Length', 20, { min: 1 });
const v_calc = input.select('Volume Calculation', 'Relative', ['Relative', 'Full', 'None']);
const vlookbk = input.number('Volume Lookback', 20, { min: 1 });

// ===========================================================================================================
//          Calculations
// ===========================================================================================================

// Volume Calculation -- will revert to no volume acceleration for instruments with no volume data
const myVola = for_every(volume, (_v, _prevOut, _index) => {
    if (v_calc === 'None' || !current.volumeDataAvailable) {
        return 1;
    }
    if (v_calc === 'Relative') {
        const myVolWindow = volume.slice(Math.max(0, _index - vlookbk + 1), _index + 1);
        const myHighestVol = Math.max(...myVolWindow);
        const myLowestVol = Math.min(...myVolWindow);
        return myHighestVol === myLowestVol ? 0 : 100 * (_v - myLowestVol) / (myHighestVol - myLowestVol) / 100;
    }
    return _v;
});

// R is the 2-bar average bar range - accommodates bar gaps
const myR = for_every(high, low, (_h, _l, _prevOut, _index) => {
    if (_index < 1) return null;
    const myHigh2 = Math.max(high[_index], high[_index - 1]);
    const myLow2 = Math.min(low[_index], low[_index - 1]);
    return (myHigh2 - myLow2) / 2;
});

// Calculate ratio of change to R, restricted to +1/-1
const myC = for_every(close, myR, myVola, (_close, _r, _vola, _prevOut, _index) => {
    if (_index < 1 || _r === null || _r === 0) return 0;
    const myPriceChange = _close - close[_index - 1];
    const mySr = myPriceChange / _r;
    const myRsr = Math.max(Math.min(mySr, 1), -1);
    return myRsr * _vola;
});

// Calculate directional vol-accel energy
const myCPlus = myC.map(_c => Math.max(_c, 0));
const myCMinus = myC.map(_c => -Math.min(_c, 0));

// Calculate average volume acceleration
const myAvgVola = indicators[MA_Type](myVola, length);

// Calculate directional energy ratio (DER)
const myDem = div(indicators[MA_Type](myCPlus, length), myAvgVola);
const mySup = div(indicators[MA_Type](myCMinus, length), myAvgVola);

// Calculate average DER
const myAdp = mult(wma(myDem, DER_avg), 100);
const myAsp = mult(wma(mySup, DER_avg), 100);

// Calculate net DER
const myAnp = sub(myAdp, myAsp);
const myAnpS = wma(myAnp, smooth);

// Calculate Sentiment (longer period directional energy)
const mySAdp = mult(wma(myDem, senti), 100);
const mySAsp = mult(wma(mySup, senti), 100);
const myLongSenti = wma(sub(mySAdp, mySAsp), smooth);

// ===========================================================================================================
//      Colors & Plots
// ===========================================================================================================

// Sentiment histogram with 4 colors
const mySentimentColor = for_every(myLongSenti, (_senti, _prevOut, _index) => {
    if (_index < 1) return '#1b5e2080';
    const myIsUp = _senti >= 0;
    const myIsGrowing = Math.abs(_senti) >= Math.abs(myLongSenti[_index - 1]);
                
    if (myIsUp) {
        return myIsGrowing ? '#1b5e2080' : '#66bb6a80';
    } else {
        return myIsGrowing ? '#dc4c4a80' : '#ef8e9880';
    }
});

// Paint sentiment as columns if enabled, otherwise paint null series
paint(
    show_senti ? myLongSenti : series_of(null),
    { name: 'Sentiment', style: 'column', color: mySentimentColor });

// Paint Supply and Demand Energy
const mySupplyLine = paint(myAsp, { name: 'Supply Energy', color: '#ffa500', style: 'dotted' });
const myDemandLine = paint(myAdp, { name: 'Demand Energy', color: '#00ffff', style: 'dotted' });

// Fill between Supply and Demand - using a single static color
fill(myDemandLine, mySupplyLine, '#00ff00', 0.3);

// Color for the main signal line based on its value (positive or negative)
const mySignalColor = myAnpS.map(_v => _v >= 0 ? '#359bfc' : '#f57f17');

paint(myAnpS, { name: 'Net Energy Signal', color: mySignalColor, thickness: 2 });

// Paint zero line
paint(horizontal_line(0), { name: 'Zero Line', color: '#ffee00', style: 'dotted' });

// ===========================================================================================================
//      Signals for Visual Scripts
// ===========================================================================================================

const myAlertUp = for_every(myAnpS, (_anp, _prevOut, _index) => {
    if (_index < 1) return false;
    return myAnpS[_index - 1] < 0 && _anp >= 0;
});

const myAlertDown = for_every(myAnpS, (_anp, _prevOut, _index) => {
    if (_index < 1) return false;
    return myAnpS[_index - 1] > 0 && _anp <= 0;
});

const mySpeedUp = for_every(myAnpS, myLongSenti, (_anp, _senti, _prevOut, _index) => {
    if (_index < 1) return false;
    return myAnpS[_index - 1] <= myLongSenti[_index - 1] && _anp > _senti;
});

const mySlowDown = for_every(myAnpS, myLongSenti, (_anp, _senti, _prevOut, _index) => {
    if (_index < 1) return false;
    return myAnpS[_index - 1] >= myLongSenti[_index - 1] && _anp < _senti;
});

register_signal(myAlertUp, 'Energy Crossing Up');
register_signal(myAlertDown, 'Energy Crossing Down');
register_signal(mySpeedUp, 'Energy Speeding Up');
register_signal(mySlowDown, 'Energy Slowing Down');
</code>