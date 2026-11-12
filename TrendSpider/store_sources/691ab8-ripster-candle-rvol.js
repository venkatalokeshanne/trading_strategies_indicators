<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Ripster Candle Rvol');
const myAverageCandles = input.number('Average of Candles', 50, { min: 1 });
const myLocation = 'top_right';

// === Volume & RVOL Calculation ===
const myCurrentCandleVolume = volume[volume.length - 1];
const myAverageVolume = sma(volume, myAverageCandles)[volume.length - 1];
const myRelativeVolume = (myCurrentCandleVolume / myAverageVolume) * 100;

// === Previous Candle RVOL ===
const myRelativeVolumeSeries = div(volume, sma(volume, myAverageCandles));
const myRelativeVolumePercent = mult(myRelativeVolumeSeries, 100);
const previousRvol = shift(myRelativeVolumePercent, 1);

// === Volume Formatter ===
const formatVolume = vol => vol >= 1000000 ? (vol / 1000000).toFixed(2) + 'M' : vol.toString();

// === Custom Colors ===
const myLightGray = '#D3D3D3';
const myOrange = 'orange';
const myRed = 'red';
const myGreen = 'green';
const myYellow = 'yellow';
const myDarkBorder = '#333333';

// === Draw Table ===
const myRvolColor = myRelativeVolume > 200 ? myRed : myRelativeVolume > 100 ? myOrange : myYellow;
const myLastRvolColor = previousRvol[previousRvol.length - 1] > 200 ? myRed : previousRvol[previousRvol.length - 1] > 100 ? myOrange : myYellow;

paint_overlay('Volume Table', { position: myLocation, offset_x: -100 }, {
    rows: [
        {
            cells: [
                { text: 'Candle Vol', color: 'white', background: myGreen, fontSize: 12, fontWeight: 'bold', border: `solid ${myDarkBorder} 1px`, padding: 8 },
                { text: formatVolume(myCurrentCandleVolume), color: 'black', background: myYellow, fontSize: 12, fontWeight: 'bold', border: `solid ${myDarkBorder} 1px`, padding: 8 },
                { text: 'Prev. Candle Rvol', color: 'white', background: myGreen, fontSize: 12, fontWeight: 'bold', border: `solid ${myDarkBorder} 1px`, padding: 8 }
            ]
        },
        {
            cells: [
                { text: 'Candle Rvol', color: 'white', background: myGreen, fontSize: 12, fontWeight: 'bold', border: `solid ${myDarkBorder} 1px`, padding: 8 },
                { text: myRelativeVolume.toFixed(2) + '%', color: 'black', background: myRvolColor, fontSize: 12, fontWeight: 'bold', border: `solid ${myDarkBorder} 1px`, padding: 8 },
                { text: previousRvol[previousRvol.length - 1] ? previousRvol[previousRvol.length - 1].toFixed(2) + '%' : 'N/A', color: 'black', background: myLastRvolColor, fontSize: 12, fontWeight: 'bold', border: `solid ${myDarkBorder} 1px`, padding: 8 }
            ]
        }
    ],
    cellPadding: 0,
    rowGap: 1,
    border: `solid ${myDarkBorder} 6px`,
    borderRadius: 4
});</code>