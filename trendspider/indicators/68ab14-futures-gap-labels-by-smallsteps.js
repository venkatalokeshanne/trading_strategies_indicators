<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Futures Gap Labels by SmallSteps');

// This indicator is designed for use with futures contracts such as MES1!, MNQ1!, and M2K1!. 
// This indicator colors the candles at two specific times each day (session start and session end), displays labels,
// and shows the previous day's session high and low using start/end time. 
// Note: This is based on the exchange time zone (mountain) of the current symbol, session end time are hardcoded.
// It uses the gap candle (first candle at session start) as ORB and signals Long or Short. Adjust gap threshold according to your future instrument. 
//I have been using this indicator for a while now, submitting with minor changes to #TSBuild25 and TrendSpider store.

// Create a variable to show the timeframe selection
const myTimeframe = current.resolution;

const myTime1 = input.number('Start Mountain Time', 830, { min: 0, max: 2359 });
const overrideEndTimeVal = input.number('End Mountain Time', 1455, { min: 0, max: 2359,  hide_in_legend: true });
const overrideEndTime = input.boolean('Use End Time', false, { hide_in_legend: true });

const myColorAtTime1 = input.color('Color 1st and Last Time', 'blue',  {hide_in_legend: true});
const myColorAtTime2 = myColorAtTime1;
const myGapThreshold = input.number('Gap Threshold', 5, { min: 0 });
const myColorCandle = input.boolean('Color Candle',false,  {hide_in_legend: true});

const myTrueGap = input.boolean('Use Prev H/L', false);
const debugDisplay = input.boolean('Debug Display', true, {hide_in_legend: true});
const myMaxSignals = input.number('Max Signals', 5, { min: 1, max: 50,  hide_in_legend: true });

// Check if the chart resolution is less than 30 minutes
assert(
    (Number(current.resolution) >= 5 && Number(current.resolution) <= 30),
    "This indicator only supports chart resolutions 5, 10 , 15 and 30 minutes."
);

const getHoursAndMinutes = (_time) => {
    const myHours = Math.floor(_time / 100);
    const myMinutes = _time % 100;
    return { hours: myHours, minutes: myMinutes };
};

let myTime2 ;
if(overrideEndTime) {
	myTime2 = overrideEndTimeVal;
} else {
	if(myTimeframe == '5') {
		myTime2 = 1455;
	} else if(myTimeframe == '10') {
		myTime2 = 1450;
	} else if(myTimeframe == '15') {
		myTime2 = 1445;
	} else if(myTimeframe == '30') {
		myTime2 = 1430;
	}	
}



const myTime1Values = getHoursAndMinutes(myTime1);
const myTime2Values = getHoursAndMinutes(myTime2);
const myCandleColors = series_of(null);
const myLabelPrices = series_of(null);
const gapCloseDisplay1 = series_of(null);
const gapCloseDisplay2 = series_of(null);
const myGapSignal = series_of(false);
const myGapShortSignal = series_of(false);
const myGapLongSignal = series_of(false);
let myPrevSessionTime2Price = null;
let myPrevSessionHigh = null;
let myPrevSessionLow = null;
let myCurrentSessionHigh = null;
let myCurrentSessionLow = null;
let myFirstCandleHigh = null;
let myFirstCandleLow = null;
let myFirstCandleOpen = null;
let myGapOccuredAbove = false;
let myGapOccuredBelow = false;
let myGapShortSignalOccurred = 0;
let myGapLongSignalOccurred = 0;
let myGapUpCloseVal = null;
let myGapDownCloseVal = null;
const myPrevDayHigh = series_of(null);
const myPrevDayLow = series_of(null);
const myGapCloseVal1Series = series_of(null);

for (let i = 0; i < time.length; i++) {
	if(i <= 10) {continue;}
    const myBarTime = time_of(time[i]);
    
    if (myBarTime.hours === myTime1Values.hours && myBarTime.minutes === myTime1Values.minutes) {
        // Set previous day's session high and low
        myPrevDayHigh[i] = myPrevSessionHigh;
        myPrevDayLow[i] = myPrevSessionLow;
		//For display purpose, for prior 5 candles. 
		myPrevDayHigh[i-1] = myPrevSessionHigh;
		myPrevDayHigh[i-2] = myPrevSessionHigh;
		myPrevDayHigh[i-3] = myPrevSessionHigh;
		myPrevDayHigh[i-4] = myPrevSessionHigh;
		myPrevDayHigh[i-5] = myPrevSessionHigh;
		myPrevDayLow[i-1] = myPrevSessionLow;
		myPrevDayLow[i-2] = myPrevSessionLow;
		myPrevDayLow[i-3] = myPrevSessionLow;
		myPrevDayLow[i-4] = myPrevSessionLow;
		myPrevDayLow[i-5] = myPrevSessionLow;
		
        // Reset current session high and low
        myCurrentSessionHigh = high[i];
        myCurrentSessionLow = low[i];
		
        //Reset gap status
		myGapOccuredAbove = false;
		myGapOccuredBelow = false;
		myFirstCandleOpen = null;
		myFirstCandleHigh = null;
		myFirstCandleLow = null;
		myGapShortSignalOccurred = 0;
		myGapLongSignalOccurred = 0;
		
        myCandleColors[i] = myColorAtTime1;
		myFirstCandleOpen = open[i];
        myFirstCandleHigh = high[i];
        myFirstCandleLow = low[i];
		if((myFirstCandleHigh - myFirstCandleLow) > 2 * myGapThreshold) {
			if(open[i] >= close[i]) {
				myFirstCandleHigh = open[i];
				myFirstCandleLow = close[i];
			} else {
				myFirstCandleHigh = close[i];
				myFirstCandleLow = open[i];
			}
		}
		
        if (myPrevSessionTime2Price !== null) {
            const myDifference = open[i] - myPrevSessionTime2Price;
			const myGapFound = Math.abs(myDifference) > myGapThreshold;
			
			if(myTrueGap) {
				if(open[i] > myPrevDayHigh[i] && myGapFound) {
					myLabelPrices[i] = myDifference.toFixed(2);
					myGapSignal[i] = true;
					myGapOccuredAbove = true;
					myGapUpCloseVal = low[i] - myPrevDayHigh[i];
				} else if(open[i] < myPrevDayLow[i] && myGapFound) {
					myLabelPrices[i] = myDifference.toFixed(2);
					
					myGapSignal[i] = true;
					myGapOccuredBelow = true;
					myGapDownCloseVal = high[i] - myPrevDayLow[i];
				}
			} else {
	            if (myGapFound) {
					myLabelPrices[i] = myDifference.toFixed(2);
	                myGapSignal[i] = true;
					if (myDifference > 0) {
						myGapOccuredAbove = true;
					} else {
						myGapOccuredBelow = true;
					}
	            }
			}
        }
        myPrevSessionTime2Price = null;
    } else if (myBarTime.hours === myTime2Values.hours && myBarTime.minutes === myTime2Values.minutes) {
        myCandleColors[i] = myColorAtTime2;
        myPrevSessionTime2Price = close[i];

        // Update current session high and low
        if (myCurrentSessionHigh !== null) {
            myCurrentSessionHigh = Math.max(myCurrentSessionHigh, high[i]);
            myCurrentSessionLow = Math.min(myCurrentSessionLow, low[i]);
        }
		
        // Update previous session high and low
        myPrevSessionHigh = myCurrentSessionHigh;
        myPrevSessionLow = myCurrentSessionLow;
		
        //Reset gap status 
		myGapOccuredAbove = false;
		myGapOccuredBelow = false;
		myFirstCandleOpen = null;
		myFirstCandleHigh = null;
		myFirstCandleLow = null;
		myGapShortSignalOccurred = 0;
		myGapLongSignalOccurred = 0;
		myGapUpCloseVal = null;
		myGapDownCloseVal = null;
    } else {
        
        // Update current session high and low
        if (myCurrentSessionHigh !== null) {
            myCurrentSessionHigh = Math.max(myCurrentSessionHigh, high[i]);
            myCurrentSessionLow = Math.min(myCurrentSessionLow, low[i]);
        }
        
        // Carry forward previous day's session high and low
        if (i > 0) {
            myPrevDayHigh[i] = myPrevDayHigh[i-1];
            myPrevDayLow[i] = myPrevDayLow[i-1];
        }
		if(myGapOccuredAbove) {
			if(myGapLongSignalOccurred < myMaxSignals && close[i] > myFirstCandleHigh && low[i] < myFirstCandleHigh) {
				myGapLongSignal[i] = true;
				myGapLongSignalOccurred++;
			} else if(myGapShortSignalOccurred < myMaxSignals && close[i] < myFirstCandleLow && high[i] > myFirstCandleLow) {
				myGapShortSignal[i] = true;
				myGapShortSignalOccurred++;
			}
			
			if(myTrueGap && myGapUpCloseVal != null) {
				myGapUpCloseVal = low[i] - myPrevDayHigh[i];
				myGapUpCloseVal < 0 ? myGapUpCloseVal = null : null;
				if(close[i] > myFirstCandleHigh) {
					myGapUpCloseVal = null;
				}
			}
		}
		if(myGapOccuredBelow) {
			if(myGapShortSignalOccurred < myMaxSignals && close[i] < myFirstCandleLow && high[i] > myFirstCandleLow) { //short - gap on downside
				myGapShortSignal[i] = true;
				myGapShortSignalOccurred++;
			} else if(myGapLongSignalOccurred < myMaxSignals && close[i] > myFirstCandleHigh && low[i] < myFirstCandleHigh) {//long - gap on upside
				myGapLongSignal[i] = true;
				myGapLongSignalOccurred++;
			}
			
			if(myTrueGap && myGapDownCloseVal != null) {
				myGapDownCloseVal = high[i] - myPrevDayLow[i];
				myGapDownCloseVal > 0 ? myGapDownCloseVal = null : null;
				if(close[i] < myFirstCandleLow) {
					myGapDownCloseVal = null;
				}
			}
		}
    }
    
    // Update gapCloseVal1Series for each candle between myTime1Values and myTime2Values
    const isWithinTimeRange = (myBarTime.hours > myTime1Values.hours || 
                               (myBarTime.hours === myTime1Values.hours && myBarTime.minutes >= myTime1Values.minutes)) &&
                              (myBarTime.hours < myTime2Values.hours || 
                               (myBarTime.hours === myTime2Values.hours && myBarTime.minutes <= myTime2Values.minutes));
    
    if (isWithinTimeRange) {
        if (myGapUpCloseVal !== null) {
            myGapCloseVal1Series[i] = myGapUpCloseVal.toFixed(2);
        } else if (myGapDownCloseVal !== null) {
            myGapCloseVal1Series[i] = myGapDownCloseVal.toFixed(2);
        }
    }
}

if(myColorCandle) { 
    color_candles(myCandleColors); 
}

// Paint previous day's session high and low
const prevDayHighPaint = paint(myPrevDayHigh, { color: 'white', name: 'Prev Day High', style: 'ladder' });
paint_label_at_line(prevDayHighPaint, close.length - 5, 'Y-High', { color: 'gray' });
const prevDayLowPaint = paint(myPrevDayLow, { color: 'white', name: 'Prev Day Low', style: 'ladder' });
paint_label_at_line(prevDayLowPaint, close.length - 5, 'Y-Low', { color: 'gray' });

register_signal(myGapSignal, 'Gap Signal');
register_signal(myGapShortSignal, 'Gap Short Signal');
register_signal(myGapLongSignal, 'Gap Long Signal');

// Create label series for each signal type
const myGapLabels = for_every(myLabelPrices, _price => _price !== null ? _price : null);
const myGapShortLabels = for_every(myGapShortSignal, _signal => _signal ? 'S' : null);
const myGapLongLabels = for_every(myGapLongSignal, _signal => _signal ? 'L' : null);

// Paint labels using the paint() function
paint(myGapLabels, { 
    color: 'white',
    backgroundColor: 'blue',
    name: 'Gap Labels',
    style: 'labels_above' 
});

// Paint gapCloseVal1 labels based on debugDisplay input
if (debugDisplay) {
	paint(myGapShortLabels, { 
	    color: 'white',
	    backgroundColor: 'rgba(255, 0, 0, 0.5)',
	    name: 'Gap Short Labels',
	    style: 'labels_above' 
	});
	
	paint(myGapLongLabels, { 
	    color: 'white',
	    backgroundColor: 'rgba(255, 0, 0, 0.5)',
	    name: 'GapGo Long Labels',
	    style: 'labels_below' 
	});
}


</code>