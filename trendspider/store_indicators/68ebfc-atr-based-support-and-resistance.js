<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('ATR Based Support and Resistance');

// ATR Calculations group
const atrPeriod = input.number('ATR Length', 21, { min: 1, max: 100 });
const atrMultiplier = input.number('ATR Multiplier', 1.718, { min: 0.1, max: 10 });
const lineLength = input.number('Horizontal Line Length', 50, { min: 1, max: 500 });
const wickPercent = input.number('Wick %', 70, { min: 0, max: 100 });

// Supply & Demand Zones styling - Down
const downLineStyle = input.select('Down Zone Line Style', 'line', ['line', 'dotted']);
const downBorderColor = input.color('Down Zone Border Color', 'rgba(255, 0, 0, 0.2)');
const downBgColor = input.color('Down Zone Background Color', 'rgba(255, 0, 0, 0.7)');

// Supply & Demand Zones styling - Up
const upLineStyle = input.select('Up Zone Line Style', 'line', ['line', 'dotted']);
const upBorderColor = input.color('Up Zone Border Color', 'rgba(0, 255, 0, 0.2)');
const upBgColor = input.color('Up Zone Background Color', 'rgba(0, 255, 0, 0.7)');

// Calculate ATR and True Range
const myAtr = atr(high, low, close, atrPeriod);
const myAtrMultiplied = mult(myAtr, atrMultiplier);

// Calculate True Range for each candle
const myTrueRange = for_every(high, low, close, (_h, _l, _c, _prev, _i) => {
    if (_i === 0) return _h - _l;
    const prevClose = close[_i - 1];
    return Math.max(_h - _l, Math.abs(_h - prevClose), Math.abs(_l - prevClose));
});

// Identify impulse candles
const myImpulseUp = for_every(myTrueRange, close, open, myAtrMultiplied, (_tr, _c, _o, _atrMult, _prev, _i) => {
    if (_i === 0) return false;
    const prevTr = myTrueRange[_i - 1];
    const prevAtr = myAtr[_i - 1];
    return _tr >= _atrMult && _c > _o && prevTr <= prevAtr;
});

const myImpulseDown = for_every(myTrueRange, close, open, myAtrMultiplied, (_tr, _c, _o, _atrMult, _prev, _i) => {
    if (_i === 0) return false;
    const prevTr = myTrueRange[_i - 1];
    const prevAtr = myAtr[_i - 1];
    return _tr >= _atrMult && _c < _o && prevTr <= prevAtr;
});

// Color candles based on impulse
const myCandleColors = for_every(myImpulseUp, myImpulseDown, (_up, _down) => {
    if (_up) return 'green';
    if (_down) return 'red';
    return null;
});
color_candles(myCandleColors);

// Paint impulse markers - using smaller dot icon
const myImpulseUpMarkers = for_every(myImpulseUp, _up => _up ? '·' : null);
const myImpulseDownMarkers = for_every(myImpulseDown, _down => _down ? '·' : null);

paint(myImpulseUpMarkers, { style: 'labels_below', color: 'green', name: 'Impulse Up' });
paint(myImpulseDownMarkers, { style: 'labels_above', color: 'red', name: 'Impulse Down' });

// Calculate wick percentages and zones
const totalPercentCalc = wickPercent * 0.01;

// Calculate zones for impulse down candles
const myDownZoneTop = series_of(null);
const myDownZoneBottom = series_of(null);

for (let i = 0; i < close.length; i++) {
    if (myImpulseDown[i]) {
        const impulseDownWick = high[i] - open[i];
        const wickPercentValue = impulseDownWick / myTrueRange[i];
        
        if (wickPercentValue <= totalPercentCalc) {
            myDownZoneTop[i] = high[i];
            myDownZoneBottom[i] = open[i];
            
            // Extend zone forward
            for (let j = 1; j <= lineLength && (i + j) < close.length; j++) {
                myDownZoneTop[i + j] = high[i];
                myDownZoneBottom[i + j] = open[i];
            }
        }
    }
}

// Calculate zones for impulse up candles
const myUpZoneTop = series_of(null);
const myUpZoneBottom = series_of(null);

for (let i = 0; i < close.length; i++) {
    if (myImpulseUp[i]) {
        const impulseUpWick = open[i] - low[i];
        const wickPercentValue = impulseUpWick / myTrueRange[i];
        
        if (wickPercentValue <= totalPercentCalc) {
            myUpZoneTop[i] = open[i];
            myUpZoneBottom[i] = low[i];
            
            // Extend zone forward
            for (let j = 1; j <= lineLength && (i + j) < close.length; j++) {
                myUpZoneTop[i + j] = open[i];
                myUpZoneBottom[i + j] = low[i];
            }
        }
    }
}

// Paint the zones
const downTopLine = paint(myDownZoneTop, { 
    style: downLineStyle, 
    color: downBorderColor, 
    name: 'Down Zone Top',
    hidden: true 
});

const downBottomLine = paint(myDownZoneBottom, { 
    style: downLineStyle, 
    color: downBorderColor, 
    name: 'Down Zone Bottom',
    hidden: true 
});

fill(downTopLine, downBottomLine, downBgColor, 0.7, 'Down Supply Zone');

const upTopLine = paint(myUpZoneTop, { 
    style: upLineStyle, 
    color: upBorderColor, 
    name: 'Up Zone Top',
    hidden: true 
});

const upBottomLine = paint(myUpZoneBottom, { 
    style: upLineStyle, 
    color: upBorderColor, 
    name: 'Up Zone Bottom',
    hidden: true 
});

fill(upTopLine, upBottomLine, upBgColor, 0.7, 'Up Demand Zone');
</code>