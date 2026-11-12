<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('ATR Table');

const atrLength = input.number('ATR Length', 14, { min: 1 });
const tablePosition = input.select('Table Position', 'Bottom Left', ['Top Left', 'Top Right', 'Bottom Left', 'Bottom Right']);

const myAtr = atr(high, low, close, atrLength);
const myAtrAverage = sma(myAtr, 5);

const positionMap = {
    'Top Left': 'top_left',
    'Top Right': 'top_right',
    'Bottom Left': 'bottom_left',
    'Bottom Right': 'bottom_right'
};

const formatNumber = (num) => num.toFixed(2);
const formatPercent = (num) => num.toFixed(2) + '%';

// Import the tinycolor library
const tinycolor = library('tinycolor2');

const getColor = (color, alpha) => tinycolor(color).setAlpha(alpha).toRgbString();

paint_overlay('ATR Table', { position: positionMap[tablePosition] }, {
    rows: [
        {
            cells: [
                { text: 'ATR Period', color: 'white', background: getColor('blue', 0.1) },
                { text: atrLength.toString(), color: 'white', background: getColor('blue', 0.1) }
            ]
        },
        {
            cells: [
                { text: 'Current ATR (Points)', color: 'white', background: getColor('green', 0.1) },
                { text: formatNumber(myAtr[myAtr.length - 1]), color: 'white', background: getColor('green', 0.1) }
            ]
        },
        {
            cells: [
                { text: 'Current ATR (%)', color: 'white', background: getColor('green', 0.1) },
                { text: formatPercent((myAtr[myAtr.length - 1] / close[close.length - 1]) * 100), color: 'white', background: getColor('green', 0.1) }
            ]
        },
        {
            cells: [
                { text: 'ATR 1 Bar Ago (Points)', color: 'white', background: getColor('orange', 0.1) },
                { text: formatNumber(myAtr[myAtr.length - 2]), color: 'white', background: getColor('orange', 0.1) }
            ]
        },
        {
            cells: [
                { text: 'ATR 1 Bar Ago (%)', color: 'white', background: getColor('orange', 0.1) },
                { text: formatPercent((myAtr[myAtr.length - 2] / close[close.length - 2]) * 100), color: 'white', background: getColor('orange', 0.1) }
            ]
        },
        {
            cells: [
                { text: 'ATR Avg (5 Bars) (Points)', color: 'white', background: getColor('purple', 0.1) },
                { text: formatNumber(myAtrAverage[myAtrAverage.length - 1]), color: 'white', background: getColor('purple', 0.1) }
            ]
        },
        {
            cells: [
                { text: 'ATR Avg (5 Bars) (%)', color: 'white', background: getColor('purple', 0.1) },
                { text: formatPercent((myAtrAverage[myAtrAverage.length - 1] / close[close.length - 1]) * 100), color: 'white', background: getColor('purple', 0.1) }
            ]
        }
    ]
});
</code>