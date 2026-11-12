<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Chart Resolution and Candle Label');

const backgroundColor = input.color('Background Color', 'white');
const textColor = input.color('Text Color', 'black');
const resolutionColor = input.color('title', '#6300d3');
const fontSize = input.number('Font Size', 24, { min: 8, max: 24 });

// This indicator adds a label showing the current chart time interval and chart type in a table format
// It's a simple implementation and might need adjustments based on specific needs

const intervalMap = {
    '1': '1 min',
    '5': '5 min',
    '15': '15 min',
    '30': '30 min',
    '60': '1 hour',
    '240': '4 hour',
    'D': 'Daily',
    'W': 'Weekly',
    'M': 'Monthly',
    '1440': 'Session'
};

const chartTypeMap = {
    'line': 'Line',
    'bars': 'Bars',
    'candles': 'Candles',
    'hollowcandles': 'Hollow Candles',
    'rainfall': 'Rainfall',
    'heikinashi': 'Heikin Ashi'
};

const intervalLabel = intervalMap[current.resolution] || current.resolution;
const chartTypeLabel = chartTypeMap[current.chart_type] || current.chart_type;

paint_overlay('IntervalLabel', { position: 'top_right', offset_x: -200, offset_y: -5 }, {
    rows: [{
        cells: [{
            text: 'Resolution: ',
            color: resolutionColor,
            fontSize: `${fontSize}px`,
            font_weight: 'bold',
            background: backgroundColor,
            padding: '4px',
        }, {
            text: intervalLabel,
            color: textColor,
            fontSize: `${fontSize}px`,
            font_weight: 'bold',
            background: backgroundColor,
            padding: '2px',
        }, {
            text: ` | ${chartTypeLabel}`,
            color: textColor,
            fontSize: `${fontSize}px`,
            font_weight: 'bold',
            background: backgroundColor,
            padding: '2px',
        }]
    }]
});
</code>