<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Consecutive Candles', 'lower');

// Input parameter to toggle between close momentum and candle color modes
const myMode = input.select('Mode', 'vs. Last close', ['vs. Last close', 'Candle Color']);

// This indicator counts consecutive closes above or below the previous close
// Green bars grow when price closes higher than the previous close
// Red bars grow when price closes lower than the previous close
// The count resets when the trend reverses
const consecutiveBars = for_every(close, open, (currentClose, currentOpen, prevValue, index) => {
  if (index === 0) {
    return 0;
  }
  
  let isHigherClose;
  let isLowerClose;
  
  if (myMode === 'vs. Last close') {
    // Compare current close to previous close
    const prevClose = close[index - 1];
    isHigherClose = currentClose > prevClose;
    isLowerClose = currentClose < prevClose;
  } else {
    // Compare current close to current open (candle color)
    isHigherClose = currentClose > currentOpen;
    isLowerClose = currentClose < currentOpen;
  }
  
  if (isHigherClose) {
    // If previous value was positive, add 1. If negative, reset to 1
    return (prevValue > 0) ? prevValue + 1 : 1;
  }
  else if (isLowerClose) {
    // If previous value was negative, subtract 1. If positive, reset to -1
    return (prevValue < 0) ? prevValue - 1 : -1;
  }
  else {
    // Close equals previous close (or open in color mode), maintain current streak
    return prevValue;
  }
});

// Create colors: green for positive values, red for negative
const barColors = for_every(consecutiveBars, value => value >= 0 ? '#469e48' : '#f34539');

paint(consecutiveBars, { 
  style: 'column', 
  color: barColors, 
  name: 'Consecutive Closes' 
});

// Paint a zero line for reference
paint(horizontal_line(0), { 
  style: 'dotted', 
  color: 'gray', 
  thickness: 1, 
  name: 'Zero Line' 
});
</code>