describe_indicator('SMA10 Cross Up Plus15', 'price');

// Minimum points above SMA10 required to trigger a BUY once price
// crosses above it, and minimum points below SMA10 to trigger a SELL.
const myMinPktOpen = input.number('Min pts above SMA10', 15.0, { min: 0.1, max: 1000, step: 0.5 });
const myMinPktClose = input.number('Min pts below SMA10', 12.0, { min: 0.1, max: 1000, step: 0.5 });

const mySma10 = sma(close, 10);
const myBuySignal = series_of(null);
const mySellSignal = series_of(null);

// Stateful simulation replicating Pine Script's `var` state and
// strategy.position_size behavior (0 = flat, >0 = long).
let myWatchingBuy = false;
let myPositionSize = 0;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myClose = close[myIndex];
	const mySma = mySma10[myIndex];
	const myPrevClose = myIndex > 0 ? close[myIndex - 1] : null;
	const myPrevSma = myIndex > 0 ? mySma10[myIndex - 1] : null;

	let myBuy = false;
	let mySell = false;

	if (mySma != null && myPrevSma != null && myPrevClose != null) {
		const myCrossover = myPrevClose <= myPrevSma && myClose > mySma;
		const myCrossunder = myPrevClose >= myPrevSma && myClose < mySma;

		if (myCrossover) {
			myWatchingBuy = true;
		}
		if (myCrossunder) {
			myWatchingBuy = false;
		}

		myBuy = myWatchingBuy && (myClose - mySma) >= myMinPktOpen && myPositionSize === 0;
		mySell = (mySma - myClose) >= myMinPktClose && myPositionSize > 0;

		if (myBuy) {
			myWatchingBuy = false;
		}
	}

	myBuySignal[myIndex] = myBuy ? true : null;
	mySellSignal[myIndex] = mySell ? true : null;

	// Simulate position state transitions (single long position, no sizing)
	if (myBuy) {
		myPositionSize = 1;
	}
	if (mySell) {
		myPositionSize = 0;
	}
}

paint(sma(close, 10), { name: 'SMA10', color: '#4DA3FF', thickness: 1 });

const myBuyShape = for_every(close, low, myBuySignal, (_c, _l, _b) => _b ? _l : null);
const mySellShape = for_every(close, high, mySellSignal, (_c, _h, _s) => _s ? _h : null);

paint(myBuyShape, { name: 'Buy', style: 'labels_below', color: '#00e676' });
paint(mySellShape, { name: 'Sell', style: 'labels_above', color: '#ff1744' });

register_signal(for_every(myBuySignal, _b => !!_b), 'Buy Signal');
register_signal(for_every(mySellSignal, _s => !!_s), 'Sell Signal');