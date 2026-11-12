<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Full Time Frame Continuity', { shortName: 'FTFC' });
/*
This indicator colors candles depending on whether there is a Full Timeframe Continuity 
situation currently in force. Candles are green if all 4 time frames go up. Candles are 
red if all 4 time frames go down, and candles are gray otherwise.
This script uses 4 time frames: 3 of customizable intraday tiem frames (30, 60 and 240 by default)
and Daily time frame.
Please note that various time frames candles are being "reconstructed" to match how they looked like back
then. I.e., when computing FTFC status for a 5min candle at 10:15, current Daily candle is being reconstructed
as "open = open of the day" and "close = close at 10:15".
*/
const COLOR_UNCERTAIN = 'silver';
const COLOR_FTFC_UP = 'rgb(44, 165, 153)';
const COLOR_FTFC_DOWN = 'rgb(238, 84, 81)';
const resolution1 = input("TF1", 30, { min: 5, max: 240 });
const resolution2 = input("TF2", 60, { min: 5, max: 240 });
const resolution3 = input("TF3", 240, { min: 5, max: 240 });
const minTimeFrame = Math.min(resolution1, resolution2, resolution3);
if (isNaN(constants.resolution) || constants.resolution > minTimeFrame) {
    throw Error(`This indicator only works for time frames <= ${minTimeFrame} minutes`);
}
const moment = library('moment-timezone');
const FTFCColors = series_of(null);
const candleIndexAtResolution = (timestamp, resolution) => {
    const sessionStart = moment(timestamp).hours(constants.session.start.hours).minutes(constants.session.start.minutes).seconds(0).milliseconds(0);
    if (constants.session.overnight) {
        sessionStart.subtract(1, 'day');
    }
    return Math.floor((timestamp - sessionStart) / (resolution * 60 * 1e3));
};
const intradayResolutions = [resolution1, resolution2, resolution3];
//  +1 is for "Daily"
const RANK_MAX = intradayResolutions.length + 1;
const candleStartByResolution = {};
for (let candleIndex = 1; candleIndex < time.length; candleIndex += 1) {
    
    let FTFCRank = 0;
    for (const resolution of intradayResolutions) {
        if (candleIndexAtResolution(time[candleIndex] * 1e3, resolution) != candleIndexAtResolution(time[candleIndex - 1] * 1e3, resolution)) {
            candleStartByResolution[resolution] = candleIndex;
        }
        if (candleStartByResolution[resolution]) {
            if (close[candleIndex] > open[candleStartByResolution[resolution]]) {
                FTFCRank += 1;
            }
            else {
                FTFCRank -= 1;
            }
        }
    }
    if (time_of(time[candleIndex]).dayOfYear != time_of(time[candleIndex - 1]).dayOfYear) {
        candleStartByResolution.D = candleIndex;
    }
    if (candleStartByResolution.D) {    
        const currentDailyCandleOpen = open[candleStartByResolution.D];
        const currentDailyCandleClose = close[candleIndex];
        if (currentDailyCandleClose > currentDailyCandleOpen) {
            FTFCRank += 1;
        }
        else {
            FTFCRank -= 1;
        }
    }
    FTFCColors[candleIndex] = (() => {
        if (FTFCRank == -RANK_MAX) {
            return COLOR_FTFC_DOWN;
        }
        if (FTFCRank == RANK_MAX) {
            return COLOR_FTFC_UP;
        }
        return COLOR_UNCERTAIN;
    })();
}
color_candles(FTFCColors);</code>