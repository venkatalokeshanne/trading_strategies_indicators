<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Goldbach Shelves', 'price');

// Inputs
const expOptions = [3, 9, 27, 81, 243, 729, 2187, 6561, 19683, 59049, 177147];
const multiOptions = [0.01, 0.1, 1, 10, 100, 1000, 10000, 100000, 1000000];
const exp = input.select('PO3 Exponent', 243, expOptions);
const multi = input.select('Decimal Multiplier', 1, multiOptions);

// Store previous r_l and r_h values for referencing prior bars
let myPrevRl = null;
let myPrevRh = null;

const calculatePO3Levels = (_openPrice) => {
  const myIp = _openPrice * multi;
  const myPo3 = exp;
  let myPo3R = Math.floor(myIp / myPo3) * myPo3;
  let myRl = myPo3R / multi;
  let myRh = (myPo3R + myPo3) / multi;
  
  if (myPrevRl !== null && myPrevRh !== null) {
    const myMaxRef = Math.max(
      myPrevRh + (myPrevRl - myPrevRh) * -0.111,
      myPrevRh + (myPrevRl - myPrevRh) * 1.111
    );
    const myMinRef = Math.min(
      myPrevRh + (myPrevRl - myPrevRh) * -0.111,
      myPrevRh + (myPrevRl - myPrevRh) * 1.111
    );
    if (_openPrice > myMaxRef || _openPrice < myMinRef) {
      myRl = myPo3R / multi;
      myRh = (myPo3R + myPo3) / multi;
    } else {
      myRl = myPrevRl;
      myRh = myPrevRh;
    }
  }
  
  myPrevRl = myRl;
  myPrevRh = myRh;
  return { myRl, myRh };
};

// Color helpers (using rgb colors for dark shades)
const myColorGray = 'gray';
const myColorDarkGreen = 'darkgreen';
const myColorDarkRed = 'darkred';
const myColorCrimson = 'crimson';

// Levels and their relative positions
const myLevels = [1.111, 1.0, 0.95, 0.71, 0.66, 0.61, 0.38, 0.33, 0.28, 0.05, 0.0, -0.111];

// Calculate the current range
const myCurrentOpen = open[open.length - 1];
const { myRl: myCurrentRl, myRh: myCurrentRh } = calculatePO3Levels(myCurrentOpen);

// Function to calculate price for a given level
const calculatePrice = (myRel) => {
  return myCurrentRh + (myCurrentRl - myCurrentRh) * (1 - myRel);
};

// Function to determine the current shelf
const getCurrentShelf = (myCurrentPrice) => {
  const myTopShelfLow = calculatePrice(0.66);
  const myMidShelfLow = calculatePrice(0.33);
  const myBottomShelfLow = calculatePrice(-0.111);

  if (myCurrentPrice >= myTopShelfLow) {
    return "Top Shelf";
  } else if (myCurrentPrice >= myMidShelfLow) {
    return "Mid Shelf";
  } else if (myCurrentPrice >= myBottomShelfLow) {
    return "Bottom Shelf";
  } else {
    return "Below Range";
  }
};

// Paint the level lines for the current range only
for (let i = 0; i < myLevels.length; i++) {
  const myRel = myLevels[i];
  const myPrice = calculatePrice(myRel);
  
  // Determine the line thickness
  const myLineThickness = (myRel === 0.0 || myRel === 0.35 || myRel === 0.65 || myRel === 1.0) ? 4 : 1;
  
  // Determine the line color
  let myLineColor;
  if (myRel === 1.111 || myRel === -0.111) {
    myLineColor = myColorCrimson;
  } else if (myRel === 0.95 || myRel === 0.61 || myRel === 0.28) {
    myLineColor = myColorDarkRed;
  } else if (myRel === 0.71 || myRel === 0.38 || myRel === 0.05) {
    myLineColor = myColorDarkGreen;
  } else {
    myLineColor = myColorGray;
  }
  
  const myPaintedLine = paint(series_of(myPrice), {
    color: myLineColor,
    linewidth: myLineThickness,
    style: 'ladder',
    title: `Level ${myRel}`
  });

  // Add labels to show the level values
  let myLabelText;
  if (myRel === 0.95) {
    myLabelText = "top shelf 0.95";
  } else if (myRel === 0.71) {
    myLabelText = "top shelf 0.71";
  } else if (myRel === 0.61) {
    myLabelText = "mid shelf 0.61";
  } else if (myRel === 0.38) {
    myLabelText = "mid shelf 0.38";
  } else if (myRel === 0.28) {
    myLabelText = "bottom shelf 0.28";
  } else if (myRel === 0.05) {
    myLabelText = "bottom shelf 0.05";
  } else if (myRel === -0.111) {
    myLabelText = "-0.111";
  } else if (myRel === 1.111) {
    myLabelText = "1.111";
  } else {
    myLabelText = myRel.toFixed(2);
  }

  paint_label_at_line(
    myPaintedLine,
    close.length - 1,
    myLabelText,
    {
      color: myLineColor,
      vertical_align: 'middle'
    }
  );
}

// Add the current PO3 setting as a label at the bottom of the range
const myBottomPrice = calculatePrice(-0.111);
const myPo3Label = paint(series_of(myBottomPrice), {
  color: myColorGray,
  linewidth: 1,
  style: 'ladder',
  title: 'PO3 Label'
});

paint_label_at_line(
  myPo3Label,
  close.length - 1,
  `PO3: ${exp}`,
  {
    color: myColorGray,
    vertical_align: 'bottom'
  }
);

// Add a label at the top of the range showing the current shelf
const myTopPrice = calculatePrice(1.111);
const myCurrentPrice = close[close.length - 1];
const myCurrentShelf = getCurrentShelf(myCurrentPrice);

const myShelfLabel = paint(series_of(myTopPrice), {
  color: myColorGray,
  linewidth: 1,
  style: 'ladder',
  title: 'Current Shelf Label'
});

paint_label_at_line(
  myShelfLabel,
  close.length - 1,
  `Current: ${myCurrentShelf}`,
  {
    color: myColorGray,
    vertical_align: 'top'
  }
);
</code>