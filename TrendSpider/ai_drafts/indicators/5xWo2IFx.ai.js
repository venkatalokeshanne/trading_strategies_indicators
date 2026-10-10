describe_indicator('144000 EMA Deviation Channel', 'price');

// EMA(1440) basis and standard deviation channel, replicating
// the Pine Script "144000人" indicator. 12 bands + mid EMA line.
const myLength = input.number('EMA / StDev Length', 1440, { min: 1, max: 5000 });

const myMean = ema(close, myLength);
const myStdev = stdev(close, myLength);

const myP30 = add(myMean, mult(myStdev, 3.0));
const myP25 = add(myMean, mult(myStdev, 2.5));
const myP20 = add(myMean, mult(myStdev, 2.0));
const myP15 = add(myMean, mult(myStdev, 1.5));
const myP10 = add(myMean, mult(myStdev, 1.0));
const myP05 = add(myMean, mult(myStdev, 0.5));

const myM05 = sub(myMean, mult(myStdev, 0.5));
const myM10 = sub(myMean, mult(myStdev, 1.0));
const myM15 = sub(myMean, mult(myStdev, 1.5));
const myM20 = sub(myMean, mult(myStdev, 2.0));
const myM25 = sub(myMean, mult(myStdev, 2.5));
const myM30 = sub(myMean, mult(myStdev, 3.0));

const myLastIndex = close.length - 1;

const myLineP30 = paint(myP30, { name: 'Plus3SD', color: '#FF1744', thickness: 1 });
const myLineP25 = paint(myP25, { name: 'Plus25SD', color: '#FF5252', thickness: 1 });
const myLineP20 = paint(myP20, { name: 'Plus2SD', color: '#FF9100', thickness: 1 });
const myLineP15 = paint(myP15, { name: 'Plus15SD', color: '#FFEA00', thickness: 1 });
const myLineP10 = paint(myP10, { name: 'Plus1SD', color: '#76FF03', thickness: 1 });
const myLineP05 = paint(myP05, { name: 'Plus05SD', color: '#00E676', thickness: 1 });

const myLineMid = paint(myMean, { name: 'EMA1440Mid', color: 'white', thickness: 2 });

const myLineM05 = paint(myM05, { name: 'Minus05SD', color: '#1DE9B6', thickness: 1 });
const myLineM10 = paint(myM10, { name: 'Minus1SD', color: '#00E5FF', thickness: 1 });
const myLineM15 = paint(myM15, { name: 'Minus15SD', color: '#2979FF', thickness: 1 });
const myLineM20 = paint(myM20, { name: 'Minus2SD', color: '#651FFF', thickness: 1 });
const myLineM25 = paint(myM25, { name: 'Minus25SD', color: '#D500F9', thickness: 1 });
const myLineM30 = paint(myM30, { name: 'Minus3SD', color: '#F50057', thickness: 1 });

// Labels on last bar, equivalent to barstate.islast label.new() calls
paint_label_at_line(myLineP30, myLastIndex, 'Plus 3.0 SD', { background_color: '#FF1744', color: 'white' });
paint_label_at_line(myLineP25, myLastIndex, 'Plus 2.5 SD', { background_color: '#FF5252', color: 'white' });
paint_label_at_line(myLineP20, myLastIndex, 'Plus 2.0 SD', { background_color: '#FF9100', color: 'black' });
paint_label_at_line(myLineP15, myLastIndex, 'Plus 1.5 SD', { background_color: '#FFEA00', color: 'black' });
paint_label_at_line(myLineP10, myLastIndex, 'Plus 1.0 SD', { background_color: '#76FF03', color: 'black' });
paint_label_at_line(myLineP05, myLastIndex, 'Plus 0.5 SD', { background_color: '#00E676', color: 'black' });

paint_label_at_line(myLineMid, myLastIndex, 'EMA 1440', { background_color: 'white', color: 'black' });

paint_label_at_line(myLineM05, myLastIndex, 'Minus 0.5 SD', { background_color: '#1DE9B6', color: 'black' });
paint_label_at_line(myLineM10, myLastIndex, 'Minus 1.0 SD', { background_color: '#00E5FF', color: 'black' });
paint_label_at_line(myLineM15, myLastIndex, 'Minus 1.5 SD', { background_color: '#2979FF', color: 'white' });
paint_label_at_line(myLineM20, myLastIndex, 'Minus 2.0 SD', { background_color: '#651FFF', color: 'white' });
paint_label_at_line(myLineM25, myLastIndex, 'Minus 2.5 SD', { background_color: '#D500F9', color: 'white' });
paint_label_at_line(myLineM30, myLastIndex, 'Minus 3.0 SD', { background_color: '#F50057', color: 'white' });

// Signals for scanners/alerts/strategies: price crossing each band
// and the mid EMA line, both upward and downward crossings.
const myPrevClose = shift(close, 1);

const myCrossUpMid = for_every(close, myPrevClose, myMean, shift(myMean, 1), (_c, _pc, _m, _pm) => _pc <= _pm && _c > _m);
const myCrossDownMid = for_every(close, myPrevClose, myMean, shift(myMean, 1), (_c, _pc, _m, _pm) => _pc >= _pm && _c < _m);

const myCrossUpP10 = for_every(close, myPrevClose, myP10, shift(myP10, 1), (_c, _pc, _b, _pb) => _pc <= _pb && _c > _b);
const myCrossDownP10 = for_every(close, myPrevClose, myP10, shift(myP10, 1), (_c, _pc, _b, _pb) => _pc >= _pb && _c < _b);

const myCrossUpP20 = for_every(close, myPrevClose, myP20, shift(myP20, 1), (_c, _pc, _b, _pb) => _pc <= _pb && _c > _b);
const myCrossDownP20 = for_every(close, myPrevClose, myP20, shift(myP20, 1), (_c, _pc, _b, _pb) => _pc >= _pb && _c < _b);

const myCrossUpM10 = for_every(close, myPrevClose, myM10, shift(myM10, 1), (_c, _pc, _b, _pb) => _pc <= _pb && _c > _b);
const myCrossDownM10 = for_every(close, myPrevClose, myM10, shift(myM10, 1), (_c, _pc, _b, _pb) => _pc >= _pb && _c < _b);

const myCrossUpM20 = for_every(close, myPrevClose, myM20, shift(myM20, 1), (_c, _pc, _b, _pb) => _pc <= _pb && _c > _b);
const myCrossDownM20 = for_every(close, myPrevClose, myM20, shift(myM20, 1), (_c, _pc, _b, _pb) => _pc >= _pb && _c < _b);

register_signal(myCrossUpMid, 'Cross Up Mid EMA');
register_signal(myCrossDownMid, 'Cross Down Mid EMA');
register_signal(myCrossUpP10, 'Cross Up Plus1SD');
register_signal(myCrossDownP10, 'Cross Down Plus1SD');
register_signal(myCrossUpP20, 'Cross Up Plus2SD');
register_signal(myCrossDownP20, 'Cross Down Plus2SD');
register_signal(myCrossUpM10, 'Cross Up Minus1SD');
register_signal(myCrossDownM10, 'Cross Down Minus1SD');
register_signal(myCrossUpM20, 'Cross Up Minus2SD');
register_signal(myCrossDownM20, 'Cross Down Minus2SD');