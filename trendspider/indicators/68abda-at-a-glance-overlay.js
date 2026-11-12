<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('At-A-Glance Overlay');

// Helper function to get the last non-null value from a series
const getLastValue = (series) => {
    for (let i = series.length - 1; i >= 0; i--) {
        if (series[i] !== null) return series[i];
    }
    return null;
};

// Helper function to format percentage
const formatPercentage = (value) => (value * 100).toFixed(2) + '%';

// Format the values for display
const myFormatValue = (value) => value.toFixed(2) + '%';



// Calculate price movements
const priceMovementShort = sub(close, shift(close, 5));
const priceMovementMed = sub(close, shift(close, 20));
const priceMovementLong = sub(close, shift(close, 60));

// Define colors based on price movements
const color5 = for_every(priceMovementShort, p => p > 0 ? 'green' : 'red');
const color20 = for_every(priceMovementMed, p => p > 0 ? 'green' : 'red');
const color60 = for_every(priceMovementLong, p => p > 0 ? 'green' : 'red');


// Input for customization
const volatilityShortPeriod = input.number('Volatility Short Period', 20, {
    min: 1
});
const volatilityLongPeriod = input.number('Volatility Long Period', 250, {
    min: 1
});

// Calculate range percentage for each bar
const myRangePercentage = for_every(high, low, close, (h, l, c) => ((h - l) / c) * 100);

// Calculate average range percentages
const myShortAvgRange = sma(myRangePercentage, volatilityShortPeriod);
const myLongAvgRange = sma(myRangePercentage, volatilityLongPeriod);

// Get the current values
const myCurrentRange = myRangePercentage[myRangePercentage.length - 1];
const myCurrentShortAvg = myShortAvgRange[myShortAvgRange.length - 1];
const myCurrentLongAvg = myLongAvgRange[myLongAvgRange.length - 1];

// Index data
const indexTicker = input.symbol('Index Ticker', 'SPY');
const indexData = await request.history(indexTicker, 'D');
assert(!indexData.error, `Error fetching data for ${indexTicker}: ${indexData.error}`);

const lastClose = indexData.close[indexData.close.length - 1];
const prevClose = indexData.close[indexData.close.length - 2];
const percentMove = ((lastClose - prevClose) / prevClose);

// Current Symbol
// Function to calculate daily move percentage
const calculateDailyMove = (open, close) => {
  return ((close - open) / open);
};

// Get the current day's open and close prices
const currentDayOpen = open[open.length - 1];
const currentDayClose = close[close.length - 1];

// Calculate the daily move percentage
const dailyMovePercentage = calculateDailyMove(currentDayOpen, currentDayClose);

// Paint the overlay
paint_overlay('Overlay', {
    position: 'top_right',
    offset_x: -60,
    offset_y: 20
}, {
    rows: [{
            cells: [{
                text: 'Price Movement',
                color: 'var(--text-color)'
            }]
        }, {
            cells: [{
                chart: {
                    width: '100px',
                    height: '30px',
                    type: 'bubble',
                    options: {
                        scales: {
                            x: {
                                display: false
                            },
                            y: {
                                display: false
                            }
                        },
                        plugins: {
                            legend: {
                                display: false
                            }
                        }
                    },
                    data: {
                        datasets: [{
                            data: [{
                                    x: 0,
                                    y: 0,
                                    r: 10
                                },
                                {
                                    x: 1,
                                    y: 0,
                                    r: 10
                                },
                                {
                                    x: 2,
                                    y: 0,
                                    r: 10
                                }
                            ],
                            backgroundColor: [
                                color5[color5.length - 1],
                                color20[color20.length - 1],
                                color60[color60.length - 1]
                            ]
                        }]
                    }
                }
            }]
        }, {
            cells: [{
                text: ' 5d    20d    60d',
                color: 'var(--text-color)'
            }]
        },
        {
            cells: [{
                text: ' ',
                color: 'var(--text-color)'
            }]
        },
        {
            cells: [{
                text: 'Period Volatility',
                color: 'var(--text-color)'
            }]
        },
        {
            cells: [{
                text: `Current:`,
                color: 'var(--text-color)'
            }, {
                text: `${myFormatValue(myCurrentRange)}`,
                color: myCurrentRange >= 0 ? 'green' : 'red'
            }]
        },
        {
            cells: [{
                text: `${volatilityShortPeriod}-bar Avg:`,
                color: 'var(--text-color)'
            }, {
                text: `${myFormatValue(myCurrentShortAvg)}`,
                color: myCurrentShortAvg >= 0 ? 'green' : 'red'
            }]
        },
        {
            cells: [{
                text: `${volatilityLongPeriod}-bar Avg:`,
                color: 'var(--text-color)'
            }, {
                text: `${myFormatValue(myCurrentLongAvg)}`,
                color: myCurrentLongAvg >= 0 ? 'green' : 'red'
            }]
        },
    	{
	        cells: [{
	            text: ' ',
                color: 'var(--text-color)'
	        }]
		},
    	{
	        cells: [{
	            text: 'Index Comparison',
                color: 'var(--text-color)'
	        }]
		},
    	{
	        cells: [{
	            text: `${current.ticker} Day Move:`,
	            color: 'var(--text-color)'
	        }, {
	            text: `${formatPercentage(dailyMovePercentage)}`,
	            color: percentMove >= 0 ? 'green' : 'red'
			}]
		},
    	{
	        cells: [{
	            text: `${indexTicker} Day Move:`,
	            color: 'var(--text-color)'
	        }, {
	            text: `${formatPercentage(percentMove)}`,
	            color: percentMove >= 0 ? 'green' : 'red'
			}]
		}
	]
});</code>