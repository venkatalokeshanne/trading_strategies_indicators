<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Neal or No Deal ');

const dashPosition = input.select(
    'Dash Position',
    'top_right',
    [
        'top_left',
        'top_right',
        'center_left',
        'center_right',
        'bottom_left',
        'bottom_right'
    ]
);

const showGammaLines = input.boolean('Show Gamma Lines', true);
const callLineColor = input.color('Call Line', '#00E676');
const putLineColor = input.color('Put Line', '#FF1744');

const FAST_LENGTH = 9;
const MID_LENGTH = 21;
const SLOW_LENGTH = 50;
const RSI_LENGTH = 14;
const ATR_LENGTH = 14;
const VOLUME_LENGTH = 20;
const STRUCTURE_LENGTH = 10;

const EXECUTION_THRESHOLD = 55;
const MINIMUM_TECHNICAL = 55;
const MINIMUM_OPTIONS = 15;
const MINIMUM_RR = 1.00;
const MINIMUM_PREMIUM = 25000;
const MAXIMUM_DTE = 90;
const GAMMA_MINIMUM_OI = 100;
const PROJECTION_BARS = 40;

const RISK_FREE_RATE = 0.045;
const DIVIDEND_YIELD = 0.012;

function compactMoney(value) {
    const absoluteValue = Math.abs(value);

    if (absoluteValue >= 1000000000) {
        return `$${(value / 1000000000).toFixed(2)}B`;
    }

    if (absoluteValue >= 1000000) {
        return `$${(value / 1000000).toFixed(2)}M`;
    }

    if (absoluteValue >= 1000) {
        return `$${(value / 1000).toFixed(1)}K`;
    }

    return `$${Math.round(value)}`;
}

function priceText(value) {
    if (
        value === null ||
        value === undefined ||
        !Number.isFinite(value)
    ) {
        return 'N/A';
    }

    return `$${Number(value).toFixed(2)}`;
}

function signedNumber(value) {
    const roundedValue = Math.round(value);

    return roundedValue > 0
        ? `+${roundedValue}`
        : `${roundedValue}`;
}

function biasName(value) {
    if (value >= 60) return 'STRONG BULL';
    if (value >= 20) return 'BULLISH';
    if (value <= -60) return 'STRONG BEAR';
    if (value <= -20) return 'BEARISH';

    return 'NEUTRAL';
}

function biasColor(value) {
    if (value >= 60) return '#00E676';
    if (value >= 20) return '#69F0AE';
    if (value <= -60) return '#FF1744';
    if (value <= -20) return '#FF5252';

    return '#CFD8DC';
}

function labelCell(text) {
    return {
        text,
        color: '#90A4AE',
        background: '#0D171E',
        border: 'solid #263C47 1px',
        padding: '5px 8px',
        fontSize: '10px',
        fontWeight: 'bold',
        textAlign: 'left',
        whiteSpace: 'nowrap'
    };
}

function valueCell(text, color) {
    return {
        text,
        color: color || '#FFFFFF',
        background: '#16242D',
        border: 'solid #263C47 1px',
        padding: '5px 8px',
        fontSize: '10px',
        fontWeight: 'bold',
        textAlign: 'right',
        whiteSpace: 'nowrap'
    };
}

function normalPdf(value) {
    return (
        Math.exp(-0.5 * value * value) /
        Math.sqrt(2 * Math.PI)
    );
}

function gammaValue(
    spotPrice,
    strikePrice,
    yearsToExpiration,
    volatility
) {
    const safeTime = Math.max(
        yearsToExpiration,
        0.0005
    );

    const safeVolatility = Math.max(
        volatility,
        0.01
    );

    const squareRootTime = Math.sqrt(safeTime);

    const distributionValue =
        (
            Math.log(spotPrice / strikePrice) +
            (
                RISK_FREE_RATE -
                DIVIDEND_YIELD +
                safeVolatility *
                safeVolatility /
                2
            ) *
            safeTime
        ) /
        (
            safeVolatility *
            squareRootTime
        );

    return (
        Math.exp(
            -DIVIDEND_YIELD *
            safeTime
        ) *
        normalPdf(distributionValue)
    ) /
    (
        spotPrice *
        safeVolatility *
        squareRootTime
    );
}

function chainOpenInterest(chain) {
    let totalOpenInterest = 0;

    if (
        !chain ||
        !chain.resultByStrike
    ) {
        return 0;
    }

    Object.keys(
        chain.resultByStrike
    ).forEach(strikeKey => {
        const strikeRow =
            chain.resultByStrike[strikeKey];

        totalOpenInterest += Number(
            strikeRow.C &&
            strikeRow.C.oi
        ) || 0;

        totalOpenInterest += Number(
            strikeRow.P &&
            strikeRow.P.oi
        ) || 0;
    });

    return totalOpenInterest;
}

function projectedLevel(value) {
    const projection = [];

    for (
        let projectionIndex = 0;
        projectionIndex < PROJECTION_BARS;
        projectionIndex++
    ) {
        projection.push(value);
    }

    return projection;
}

const fastEMA = ema(close, FAST_LENGTH);
const midEMA = ema(close, MID_LENGTH);
const slowEMA = ema(close, SLOW_LENGTH);

const previousFastEMA = shift(fastEMA, 1);
const previousMidEMA = shift(midEMA, 1);

const rsiValue = rsi(close, RSI_LENGTH);
const atrValue = atr(ATR_LENGTH);
const averageVolume = sma(volume, VOLUME_LENGTH);

const structureHigh = shift(
    highest(high, STRUCTURE_LENGTH),
    1
);

const structureLow = shift(
    lowest(low, STRUCTURE_LENGTH),
    1
);

const relativeVolume = for_every(
    volume,
    averageVolume,
    (currentVolume, averageValue) => {
        if (
            averageValue === null ||
            averageValue <= 0
        ) {
            return 0;
        }

        return currentVolume / averageValue;
    }
);

const bullishTechnicalScore = [];
const bearishTechnicalScore = [];

for (
    let candleIndex = 0;
    candleIndex < close.length;
    candleIndex++
) {
    let bullishPoints = 0;
    let bearishPoints = 0;

    if (
        fastEMA[candleIndex] >
        midEMA[candleIndex]
    ) {
        bullishPoints += 20;
    } else if (
        fastEMA[candleIndex] <
        midEMA[candleIndex]
    ) {
        bearishPoints += 20;
    }

    if (
        close[candleIndex] >
        midEMA[candleIndex]
    ) {
        bullishPoints += 15;
    } else if (
        close[candleIndex] <
        midEMA[candleIndex]
    ) {
        bearishPoints += 15;
    }

    if (
        close[candleIndex] >
        slowEMA[candleIndex]
    ) {
        bullishPoints += 15;
    } else if (
        close[candleIndex] <
        slowEMA[candleIndex]
    ) {
        bearishPoints += 15;
    }

    if (
        fastEMA[candleIndex] >
            previousFastEMA[candleIndex] &&
        midEMA[candleIndex] >
            previousMidEMA[candleIndex]
    ) {
        bullishPoints += 15;
    }

    if (
        fastEMA[candleIndex] <
            previousFastEMA[candleIndex] &&
        midEMA[candleIndex] <
            previousMidEMA[candleIndex]
    ) {
        bearishPoints += 15;
    }

    if (
        rsiValue[candleIndex] >= 52 &&
        rsiValue[candleIndex] <= 78
    ) {
        bullishPoints += 15;
    }

    if (
        rsiValue[candleIndex] <= 48 &&
        rsiValue[candleIndex] >= 22
    ) {
        bearishPoints += 15;
    }

    if (
        relativeVolume[candleIndex] >= 0.80
    ) {
        if (
            close[candleIndex] >=
            open[candleIndex]
        ) {
            bullishPoints += 10;
        } else {
            bearishPoints += 10;
        }
    }

    if (
        structureHigh[candleIndex] !== null &&
        close[candleIndex] >
            structureHigh[candleIndex]
    ) {
        bullishPoints += 10;
    }

    if (
        structureLow[candleIndex] !== null &&
        close[candleIndex] <
            structureLow[candleIndex]
    ) {
        bearishPoints += 10;
    }

    bullishTechnicalScore.push(
        Math.min(100, bullishPoints)
    );

    bearishTechnicalScore.push(
        Math.min(100, bearishPoints)
    );
}

const technicalDirectionalScore = [];

for (
    let candleIndex = 0;
    candleIndex < close.length;
    candleIndex++
) {
    technicalDirectionalScore.push(
        bullishTechnicalScore[candleIndex] -
        bearishTechnicalScore[candleIndex]
    );
}

const lastIndex = close.length - 1;
const currentPrice = close[lastIndex];

const currentATR =
    Number.isFinite(atrValue[lastIndex]) &&
    atrValue[lastIndex] > 0
        ? atrValue[lastIndex]
        : currentPrice * 0.01;

/*
 * CURRENT UNUSUAL OPTIONS FLOW
 */

const unusualOptionsData =
    await request.unusual_options(
        constants.ticker
    );

let callPressure = 0;
let putPressure = 0;
let callPremium = 0;
let putPremium = 0;
let acceptedTrades = 0;
let sweepCount = 0;

const optionsByStrike = {};

if (
    unusualOptionsData &&
    unusualOptionsData.length > 0
) {
    unusualOptionsData.forEach(trade => {
        const premium = Math.abs(
            Number(trade.costBasis) || 0
        );

        const contractSize = Math.abs(
            Number(trade.size) || 0
        );

        const openInterest = Math.abs(
            Number(trade.oi) || 0
        );

        const oiPercentage = Math.abs(
            Number(trade.oiPercent) || 0
        );

        const daysToExpiration = Number(
            trade.daysToExp
        );

        const strikePrice = Number(
            trade.strike
        );

        const optionType = String(
            trade.type || ''
        ).toUpperCase();

        const dealType = String(
            trade.dealType || ''
        ).toUpperCase();

        const moneyStatus = String(
            trade.moneyStatus || ''
        ).toUpperCase();

        if (premium < MINIMUM_PREMIUM) {
            return;
        }

        if (
            !Number.isFinite(daysToExpiration) ||
            daysToExpiration < 0 ||
            daysToExpiration > MAXIMUM_DTE
        ) {
            return;
        }

        if (
            optionType !== 'CALL' &&
            optionType !== 'PUT'
        ) {
            return;
        }

        if (!Number.isFinite(strikePrice)) {
            return;
        }

        acceptedTrades += 1;

        let dealMultiplier = 1;

        if (dealType === 'SWEEP') {
            dealMultiplier = 1.25;
            sweepCount += 1;
        } else if (dealType === 'BLOCK') {
            dealMultiplier = 1.15;
        }

        let expirationMultiplier = 1;

        if (daysToExpiration === 0) {
            expirationMultiplier = 1.20;
        } else if (daysToExpiration <= 7) {
            expirationMultiplier = 1.15;
        } else if (daysToExpiration <= 45) {
            expirationMultiplier = 1.05;
        } else {
            expirationMultiplier = 0.90;
        }

        let moneyMultiplier = 1;

        if (moneyStatus === 'ATM') {
            moneyMultiplier = 1.15;
        } else if (moneyStatus === 'ITM') {
            moneyMultiplier = 1.05;
        } else if (moneyStatus === 'OTM') {
            moneyMultiplier = 0.95;
        }

        let participationMultiplier =
            1 +
            Math.min(oiPercentage, 25) /
            100;

        if (
            openInterest > 0 &&
            contractSize > openInterest
        ) {
            participationMultiplier += 0.20;
        }

        const weightedPressure =
            premium *
            dealMultiplier *
            expirationMultiplier *
            moneyMultiplier *
            participationMultiplier;

        if (!optionsByStrike[strikePrice]) {
            optionsByStrike[strikePrice] = {
                callPressure: 0,
                putPressure: 0,
                totalPressure: 0
            };
        }

        if (optionType === 'CALL') {
            callPressure += weightedPressure;
            callPremium += premium;

            optionsByStrike[
                strikePrice
            ].callPressure += weightedPressure;
        } else {
            putPressure += weightedPressure;
            putPremium += premium;

            optionsByStrike[
                strikePrice
            ].putPressure += weightedPressure;
        }

        optionsByStrike[
            strikePrice
        ].totalPressure += weightedPressure;
    });
}

const totalOptionsPressure =
    callPressure + putPressure;

let optionsScore = 0;

if (totalOptionsPressure > 0) {
    optionsScore =
        (
            callPressure -
            putPressure
        ) /
        totalOptionsPressure *
        100;
}

optionsScore = Math.max(
    -100,
    Math.min(100, optionsScore)
);

let premiumRatioText = 'NO FLOW';

if (
    callPremium > 0 ||
    putPremium > 0
) {
    if (callPremium >= putPremium) {
        const callRatio =
            putPremium > 0
                ? callPremium / putPremium
                : 99;

        premiumRatioText =
            `${callRatio.toFixed(2)}x CALL`;
    } else {
        const putRatio =
            callPremium > 0
                ? putPremium / callPremium
                : 99;

        premiumRatioText =
            `${putRatio.toFixed(2)}x PUT`;
    }
}

let dominantStrike = null;
let dominantStrikePressure = 0;
let dominantStrikeType = 'NONE';

Object.keys(optionsByStrike).forEach(
    strikeKey => {
        const strikePrice = Number(strikeKey);
        const strikeData =
            optionsByStrike[strikeKey];

        const closeEnough =
            Math.abs(
                strikePrice - currentPrice
            ) /
            currentPrice <= 0.08;

        if (
            closeEnough &&
            strikeData.totalPressure >
                dominantStrikePressure
        ) {
            dominantStrikePressure =
                strikeData.totalPressure;

            dominantStrike = strikePrice;

            dominantStrikeType =
                strikeData.callPressure >=
                strikeData.putPressure
                    ? 'CALL'
                    : 'PUT';
        }
    }
);

const dominantStrikeText =
    dominantStrike !== null
        ? `${dominantStrikeType} $${dominantStrike}`
        : 'NONE NEARBY';

/*
 * CURRENT OPTIONS CHAIN AND ESTIMATED GAMMA
 */

let gammaDataAvailable = false;
let gammaExpirationDTE = null;
let gammaAtmIV = null;

let estimatedNetGEX = 0;
let gammaCallWall = null;
let gammaPutWall = null;
let gammaMagnet = null;
let gammaFlip = null;

let expectedMove = null;
let expectedMoveUpper = null;
let expectedMoveLower = null;

const gammaByStrike = {};

try {
    const optionsSchedule =
        await request.options_schedule(
            constants.ticker
        );

    if (
        optionsSchedule &&
        optionsSchedule.length > 0
    ) {
        const sortedSchedule =
            optionsSchedule
                .slice()
                .sort(
                    (
                        firstExpiration,
                        secondExpiration
                    ) =>
                        firstExpiration
                            .expiration
                            .dte -
                        secondExpiration
                            .expiration
                            .dte
                );

        let selectedExpiration =
            sortedSchedule[0];

        let selectedChain =
            await request
                .options_data_for_expiration(
                    constants.ticker,
                    selectedExpiration
                        .expiration
                        .code,
                    ['oi', 'iv']
                );

        if (
            chainOpenInterest(selectedChain) <
            GAMMA_MINIMUM_OI
        ) {
            for (
                let scheduleIndex = 1;
                scheduleIndex <
                    sortedSchedule.length;
                scheduleIndex++
            ) {
                const candidateExpiration =
                    sortedSchedule[scheduleIndex];

                const candidateChain =
                    await request
                        .options_data_for_expiration(
                            constants.ticker,
                            candidateExpiration
                                .expiration
                                .code,
                            ['oi', 'iv']
                        );

                if (
                    chainOpenInterest(
                        candidateChain
                    ) >= GAMMA_MINIMUM_OI
                ) {
                    selectedExpiration =
                        candidateExpiration;

                    selectedChain =
                        candidateChain;

                    break;
                }
            }
        }

        const resultByStrike =
            selectedChain &&
            selectedChain.resultByStrike;

        if (
            resultByStrike &&
            chainOpenInterest(selectedChain) >=
                GAMMA_MINIMUM_OI
        ) {
            gammaExpirationDTE =
                selectedExpiration
                    .expiration
                    .dte;

            const timeToExpiration =
                Math.max(
                    gammaExpirationDTE,
                    0.25
                ) /
                365;

            let nearestIVDistance = Infinity;

            Object.keys(
                resultByStrike
            ).forEach(strikeKey => {
                const strikePrice =
                    Number(strikeKey);

                const strikeRow =
                    resultByStrike[strikeKey];

                if (
                    !Number.isFinite(
                        strikePrice
                    )
                ) {
                    return;
                }

                let strikeGEX = 0;
                let strikeOI = 0;

                ['C', 'P'].forEach(side => {
                    const contract =
                        strikeRow[side];

                    if (!contract) {
                        return;
                    }

                    const openInterest =
                        Math.max(
                            0,
                            Number(
                                contract.oi
                            ) || 0
                        );

                    let normalizedIV =
                        Number(contract.iv);

                    if (
                        !Number.isFinite(
                            normalizedIV
                        )
                    ) {
                        normalizedIV = 0.50;
                    }

                    if (normalizedIV > 3) {
                        normalizedIV /= 100;
                    }

                    normalizedIV = Math.max(
                        0.005,
                        Math.min(
                            3,
                            normalizedIV
                        )
                    );

                    const contractGamma =
                        gammaValue(
                            currentPrice,
                            strikePrice,
                            timeToExpiration,
                            normalizedIV
                        );

                    const direction =
                        side === 'C'
                            ? 1
                            : -1;

                    const contractGEX =
                        contractGamma *
                        openInterest *
                        100 *
                        currentPrice *
                        currentPrice *
                        0.01 *
                        direction;

                    strikeGEX += contractGEX;
                    strikeOI += openInterest;

                    const distanceFromPrice =
                        Math.abs(
                            strikePrice -
                            currentPrice
                        );

                    if (
                        distanceFromPrice <
                        nearestIVDistance
                    ) {
                        nearestIVDistance =
                            distanceFromPrice;

                        gammaAtmIV =
                            normalizedIV;
                    }
                });

                gammaByStrike[strikePrice] = {
                    gex: strikeGEX,
                    oi: strikeOI
                };
            });

            const allGammaStrikes =
                Object.keys(gammaByStrike)
                    .map(Number)
                    .sort(
                        (
                            firstStrike,
                            secondStrike
                        ) =>
                            firstStrike -
                            secondStrike
                    );

            let nearbyGammaStrikes =
                allGammaStrikes.filter(
                    strikePrice =>
                        Math.abs(
                            strikePrice -
                            currentPrice
                        ) /
                        currentPrice <= 0.15
                );

            if (
                nearbyGammaStrikes.length === 0
            ) {
                nearbyGammaStrikes =
                    allGammaStrikes;
            }

            let maximumPositiveGEX =
                -Infinity;

            let minimumNegativeGEX =
                Infinity;

            let magnetNumerator = 0;
            let magnetDenominator = 0;

            nearbyGammaStrikes.forEach(
                strikePrice => {
                    const strikeGEX =
                        gammaByStrike[
                            strikePrice
                        ].gex;

                    estimatedNetGEX += strikeGEX;

                    magnetNumerator +=
                        strikePrice *
                        Math.abs(strikeGEX);

                    magnetDenominator +=
                        Math.abs(strikeGEX);

                    if (
                        strikeGEX >
                        maximumPositiveGEX
                    ) {
                        maximumPositiveGEX =
                            strikeGEX;

                        gammaCallWall =
                            strikePrice;
                    }

                    if (
                        strikeGEX <
                        minimumNegativeGEX
                    ) {
                        minimumNegativeGEX =
                            strikeGEX;

                        gammaPutWall =
                            strikePrice;
                    }
                }
            );

            gammaMagnet =
                magnetDenominator > 0
                    ? magnetNumerator /
                        magnetDenominator
                    : currentPrice;

            let cumulativeGEX = 0;

            nearbyGammaStrikes.forEach(
                strikePrice => {
                    const previousCumulative =
                        cumulativeGEX;

                    cumulativeGEX +=
                        gammaByStrike[
                            strikePrice
                        ].gex;

                    const crossedZero =
                        (
                            previousCumulative < 0 &&
                            cumulativeGEX >= 0
                        ) ||
                        (
                            previousCumulative > 0 &&
                            cumulativeGEX <= 0
                        );

                    if (
                        crossedZero &&
                        (
                            gammaFlip === null ||
                            Math.abs(
                                strikePrice -
                                currentPrice
                            ) <
                            Math.abs(
                                gammaFlip -
                                currentPrice
                            )
                        )
                    ) {
                        gammaFlip = strikePrice;
                    }
                }
            );

            if (
                gammaAtmIV !== null &&
                gammaAtmIV < 2
            ) {
                expectedMove =
                    currentPrice *
                    gammaAtmIV *
                    Math.sqrt(
                        timeToExpiration
                    );

                expectedMoveUpper =
                    currentPrice +
                    expectedMove;

                expectedMoveLower =
                    currentPrice -
                    expectedMove;
            }

            gammaDataAvailable =
                nearbyGammaStrikes.length > 0 &&
                magnetDenominator > 0;
        }
    }
} catch (gammaRequestError) {
    gammaDataAvailable = false;
}

let gammaRegime = 'UNAVAILABLE';
let gammaRegimeColor = '#90A4AE';

if (gammaDataAvailable) {
    if (
        estimatedNetGEX < 0 &&
        gammaFlip !== null &&
        currentPrice < gammaFlip
    ) {
        gammaRegime = 'AMPLIFICATION';
        gammaRegimeColor = '#FF1744';
    } else if (estimatedNetGEX < 0) {
        gammaRegime = 'NEGATIVE GAMMA';
        gammaRegimeColor = '#FF5252';
    } else if (
        gammaMagnet !== null &&
        Math.abs(
            currentPrice -
            gammaMagnet
        ) /
        currentPrice < 0.003
    ) {
        gammaRegime = 'PIN RISK';
        gammaRegimeColor = '#FFD600';
    } else {
        gammaRegime = 'POSITIVE GAMMA';
        gammaRegimeColor = '#69F0AE';
    }
}

let gammaDirectionalScore = 0;

if (gammaDataAvailable) {
    if (gammaMagnet !== null) {
        gammaDirectionalScore +=
            currentPrice >= gammaMagnet
                ? 35
                : -35;
    }

    if (gammaFlip !== null) {
        gammaDirectionalScore +=
            currentPrice >= gammaFlip
                ? 35
                : -35;
    }

    if (
        gammaCallWall !== null &&
        currentPrice > gammaCallWall
    ) {
        gammaDirectionalScore += 30;
    }

    if (
        gammaPutWall !== null &&
        currentPrice < gammaPutWall
    ) {
        gammaDirectionalScore -= 30;
    }
}

gammaDirectionalScore = Math.max(
    -100,
    Math.min(
        100,
        gammaDirectionalScore
    )
);

/*
 * COMBINED BEAST DECISION
 */

const currentTechnicalScore =
    technicalDirectionalScore[lastIndex];

const combinedScore =
    currentTechnicalScore * 0.55 +
    optionsScore * 0.25 +
    gammaDirectionalScore * 0.20;

const signalStrength = Math.min(
    100,
    Math.round(
        Math.abs(combinedScore)
    )
);

const technicalLongConfirmed =
    bullishTechnicalScore[lastIndex] >=
        MINIMUM_TECHNICAL &&
    fastEMA[lastIndex] >
        midEMA[lastIndex] &&
    close[lastIndex] >
        midEMA[lastIndex];

const technicalShortConfirmed =
    bearishTechnicalScore[lastIndex] >=
        MINIMUM_TECHNICAL &&
    fastEMA[lastIndex] <
        midEMA[lastIndex] &&
    close[lastIndex] <
        midEMA[lastIndex];

const optionsLongConfirmed =
    optionsScore >= MINIMUM_OPTIONS;

const optionsShortConfirmed =
    optionsScore <= -MINIMUM_OPTIONS;

const gammaLongAllowed =
    !gammaDataAvailable ||
    gammaDirectionalScore > -35;

const gammaShortAllowed =
    !gammaDataAvailable ||
    gammaDirectionalScore < 35;

const baseBuyCondition =
    combinedScore >=
        EXECUTION_THRESHOLD &&
    technicalLongConfirmed &&
    optionsLongConfirmed &&
    gammaLongAllowed;

const baseSellCondition =
    combinedScore <=
        -EXECUTION_THRESHOLD &&
    technicalShortConfirmed &&
    optionsShortConfirmed &&
    gammaShortAllowed;

/*
 * GAMMA TRADE MAP
 */

const gammaLevelCandidates = [
    {
        value: gammaMagnet,
        name: 'MAGNET'
    },
    {
        value: gammaFlip,
        name: 'GAMMA FLIP'
    },
    {
        value: gammaCallWall,
        name: 'CALL WALL'
    },
    {
        value: gammaPutWall,
        name: 'PUT WALL'
    },
    {
        value: expectedMoveUpper,
        name: 'EM HIGH'
    },
    {
        value: expectedMoveLower,
        name: 'EM LOW'
    }
];

function uniqueSortedLevels(
    levels,
    ascending
) {
    const seenLevels = {};

    return levels
        .filter(level => {
            if (
                level.value === null ||
                level.value === undefined ||
                !Number.isFinite(level.value)
            ) {
                return false;
            }

            const levelKey =
                Number(
                    level.value
                ).toFixed(4);

            if (seenLevels[levelKey]) {
                return false;
            }

            seenLevels[levelKey] = true;

            return true;
        })
        .sort(
            (
                firstLevel,
                secondLevel
            ) =>
                ascending
                    ? firstLevel.value -
                        secondLevel.value
                    : secondLevel.value -
                        firstLevel.value
        );
}

const tradeEntry = currentPrice;

let tradeDirection = 'NONE';
let tradeStop = null;
let tradeTargetOne = null;
let tradeTargetTwo = null;
let tradeTargetOneName = '';
let tradeTargetTwoName = '';
let tradeTargetOneRR = null;

if (baseBuyCondition) {
    tradeDirection = 'LONG';

    const longTargets =
        uniqueSortedLevels(
            gammaLevelCandidates.filter(
                level =>
                    Number.isFinite(
                        level.value
                    ) &&
                    level.value >=
                        tradeEntry +
                        currentATR * 0.25
            ),
            true
        );

    const longStops =
        uniqueSortedLevels(
            gammaLevelCandidates.filter(
                level =>
                    Number.isFinite(
                        level.value
                    ) &&
                    level.value <=
                        tradeEntry -
                        currentATR * 0.80
            ),
            false
        );

    tradeStop =
        longStops.length > 0
            ? longStops[0].value
            : tradeEntry -
                currentATR * 1.25;

    if (longTargets.length > 0) {
        tradeTargetOne =
            longTargets[0].value;

        tradeTargetOneName =
            longTargets[0].name;
    }

    if (longTargets.length > 1) {
        tradeTargetTwo =
            longTargets[1].value;

        tradeTargetTwoName =
            longTargets[1].name;
    }
}

if (baseSellCondition) {
    tradeDirection = 'SHORT';

    const shortTargets =
        uniqueSortedLevels(
            gammaLevelCandidates.filter(
                level =>
                    Number.isFinite(
                        level.value
                    ) &&
                    level.value <=
                        tradeEntry -
                        currentATR * 0.25
            ),
            false
        );

    const shortStops =
        uniqueSortedLevels(
            gammaLevelCandidates.filter(
                level =>
                    Number.isFinite(
                        level.value
                    ) &&
                    level.value >=
                        tradeEntry +
                        currentATR * 0.80
            ),
            true
        );

    tradeStop =
        shortStops.length > 0
            ? shortStops[0].value
            : tradeEntry +
                currentATR * 1.25;

    if (shortTargets.length > 0) {
        tradeTargetOne =
            shortTargets[0].value;

        tradeTargetOneName =
            shortTargets[0].name;
    }

    if (shortTargets.length > 1) {
        tradeTargetTwo =
            shortTargets[1].value;

        tradeTargetTwoName =
            shortTargets[1].name;
    }
}

if (
    tradeStop !== null &&
    tradeTargetOne !== null
) {
    const tradeRisk =
        Math.abs(
            tradeEntry -
            tradeStop
        );

    if (tradeRisk > 0) {
        tradeTargetOneRR =
            Math.abs(
                tradeTargetOne -
                tradeEntry
            ) /
            tradeRisk;
    }
}

const forceDebitSpread =
    tradeTargetOneRR !== null &&
    tradeTargetOneRR >= 1.00 &&
    tradeTargetOneRR < 1.50;

const validTradeMap =
    tradeTargetOneRR !== null &&
    tradeTargetOneRR >= MINIMUM_RR;

const executeBuy =
    baseBuyCondition &&
    validTradeMap;

const executeSell =
    baseSellCondition &&
    validTradeMap;

let recommendation = 'NO TRADE';
let action = 'WAIT';
let status = 'MIXED CONDITIONS';
let decisionColor = '#455A64';
let decisionIcon = '●';

const dataConflict =
    (
        currentTechnicalScore >= 20 &&
        optionsScore <= -20
    ) ||
    (
        currentTechnicalScore <= -20 &&
        optionsScore >= 20
    );

const gammaConflict =
    gammaDataAvailable &&
    (
        (
            currentTechnicalScore >= 20 &&
            gammaDirectionalScore <= -35
        ) ||
        (
            currentTechnicalScore <= -20 &&
            gammaDirectionalScore >= 35
        )
    );

if (executeBuy) {
    recommendation = 'BUY';
    action = 'LONG CONFIRMED';
    status = 'TECH + FLOW + GAMMA AGREE';
    decisionColor = '#008F5A';
    decisionIcon = '🐂';
} else if (executeSell) {
    recommendation = 'SELL';
    action = 'SHORT CONFIRMED';
    status = 'TECH + FLOW + GAMMA AGREE';
    decisionColor = '#C40000';
    decisionIcon = '🐻';
} else if (combinedScore >= 25) {
    recommendation = 'BULLISH WATCH';
    action = 'WAIT FOR BUY';
    status = 'BELOW EXECUTION';
    decisionColor = '#2E7D32';
    decisionIcon = '👀';
} else if (combinedScore <= -25) {
    recommendation = 'BEARISH WATCH';
    action = 'WAIT FOR SELL';
    status = 'BELOW EXECUTION';
    decisionColor = '#B71C1C';
    decisionIcon = '👀';
}

if (acceptedTrades === 0) {
    status = 'OPTIONS DATA UNAVAILABLE';
} else if (dataConflict) {
    status = 'TECH + OPTIONS CONFLICT';
} else if (gammaConflict) {
    status = 'GAMMA POSITIONING CONFLICT';
} else if (
    (
        baseBuyCondition ||
        baseSellCondition
    ) &&
    !validTradeMap
) {
    status = 'TARGET TOO CLOSE - POOR R:R';
} else if (
    Math.abs(currentTechnicalScore) >= 20 &&
    Math.abs(optionsScore) <
        MINIMUM_OPTIONS
) {
    status =
        'WAITING FOR OPTIONS CONFIRMATION';
} else if (
    Math.abs(optionsScore) >=
        MINIMUM_OPTIONS &&
    Math.abs(currentTechnicalScore) < 20
) {
    status =
        'WAITING FOR TECHNICAL CONFIRMATION';
}

/*
 * OPTIONS PLAY RECOMMENDER
 */

const availableOptionStrikes =
    Object.keys(gammaByStrike)
        .map(Number)
        .filter(
            strikeValue =>
                Number.isFinite(
                    strikeValue
                )
        )
        .sort(
            (
                firstStrike,
                secondStrike
            ) =>
                firstStrike -
                secondStrike
        );

function nearestOptionStrike(
    targetValue
) {
    if (
        availableOptionStrikes.length === 0 ||
        !Number.isFinite(targetValue)
    ) {
        return null;
    }

    return availableOptionStrikes.reduce(
        (
            nearestStrike,
            candidateStrike
        ) =>
            Math.abs(
                candidateStrike -
                targetValue
            ) <
            Math.abs(
                nearestStrike -
                targetValue
            )
                ? candidateStrike
                : nearestStrike,
        availableOptionStrikes[0]
    );
}

const recommendedBuyStrike =
    nearestOptionStrike(
        currentPrice
    );

const recommendedTargetStrike =
    nearestOptionStrike(
        tradeTargetOne !== null
            ? tradeTargetOne
            : currentPrice
    );

const emaCompression =
    Math.abs(
        fastEMA[lastIndex] -
        slowEMA[lastIndex]
    ) /
    currentATR;

const elevatedIV =
    gammaAtmIV !== null &&
    gammaAtmIV >= 0.55;

const positiveGammaEnvironment =
    gammaRegime ===
        'POSITIVE GAMMA' ||
    gammaRegime ===
        'PIN RISK';

const moderateConviction =
    signalStrength < 70;

const compressedTrend =
    emaCompression < 0.75;

const nearbyDirectionalWall =
    executeBuy &&
    gammaCallWall !== null
        ? Math.abs(
            gammaCallWall -
            currentPrice
        ) <=
            currentATR * 1.50
        : executeSell &&
            gammaPutWall !== null
            ? Math.abs(
                currentPrice -
                gammaPutWall
            ) <=
                currentATR * 1.50
            : false;

const preferDebitSpread =
    forceDebitSpread ||
    positiveGammaEnvironment ||
    elevatedIV ||
    moderateConviction ||
    compressedTrend ||
    nearbyDirectionalWall;
    
let optionPlay = '🛑 NO OPTION PLAY';
let optionContract = 'WAIT FOR SIGNAL';
let optionExpiration = 'N/A';
let optionTrigger = 'WAIT';
let optionTargetText = 'N/A';
let optionStopText = 'N/A';
let optionEnvironment = 'MIXED / NO EDGE';
let optionReason = status;
let optionStatus = '⏳ WAIT';
let optionColor = '#90A4AE';

if (executeBuy || executeSell) {
    const bullishOptionPlay =
        executeBuy;

    const optionSide =
        bullishOptionPlay
            ? 'CALL'
            : 'PUT';

    optionExpiration =
        gammaExpirationDTE !== null &&
        gammaExpirationDTE >= 14
            ? `${gammaExpirationDTE} DTE`
            : '21-45 DTE';

    optionTrigger =
        `${bullishOptionPlay
            ? 'ABOVE'
            : 'BELOW'} ` +
        `${priceText(tradeEntry)}`;

    optionTargetText =
        `${priceText(
            tradeTargetOne
        )} ${tradeTargetOneName}`;

    optionStopText =
        `${bullishOptionPlay
            ? 'BELOW'
            : 'ABOVE'} ` +
        `${priceText(tradeStop)}`;

    optionColor =
        bullishOptionPlay
            ? '#00E676'
            : '#FF5252';

    if (preferDebitSpread) {
        optionPlay =
            bullishOptionPlay
                ? '🛡️ CALL DEBIT SPREAD'
                : '🛡️ PUT DEBIT SPREAD';

        optionContract =
            recommendedBuyStrike !== null &&
            recommendedTargetStrike !== null
                ? `BUY $${recommendedBuyStrike}${optionSide} / ` +
                    `SELL $${recommendedTargetStrike}${optionSide}`
                : `${optionSide} DEBIT SPREAD`;

        if (positiveGammaEnvironment) {
            optionEnvironment =
                '🧲 CHOP / SUPPRESSION';

            optionReason =
                'POSITIVE GAMMA FAVORS SPREAD';
        } else if (elevatedIV) {
            optionEnvironment =
                '🛡️ ELEVATED IV';

            optionReason =
                'SPREAD REDUCES IV COST';
        } else if (
            nearbyDirectionalWall
        ) {
            optionEnvironment =
                '🧱 WALL CAPS MOVE';

            optionReason =
                'SELL LEG NEAR GAMMA TARGET';
        } else {
            optionEnvironment =
                '〰️ MODERATE MOMENTUM';

            optionReason =
                'CHOP FILTER PREFERS SPREAD';
        }

        optionStatus =
            bullishOptionPlay
                ? '✅ BULLISH SPREAD CONFIRMED'
                : '✅ BEARISH SPREAD CONFIRMED';
    } else {
        optionPlay =
            bullishOptionPlay
                ? '⚡ LONG CALL'
                : '⚡ LONG PUT';

        optionContract =
            recommendedBuyStrike !== null
                ? `$${recommendedBuyStrike} ${optionSide}`
                : `ATM ${optionSide}`;

        optionEnvironment =
            '⚡ NEGATIVE GAMMA EXPANSION';

        optionReason =
            'STRONG TREND + FLOW + GAMMA';

        optionStatus =
            bullishOptionPlay
                ? '🐂 LONG CALL CONFIRMED'
                : '🐻 LONG PUT CONFIRMED';
    }
}

/*
 * GAMMA CHART LEVELS
 */

function paintGammaLevel(
    value,
    enabled,
    lineName,
    projectionName,
    labelText,
    lineColor,
    labelOffset,
    lineThickness
) {
    const validLevel =
        enabled &&
        value !== null &&
        value !== undefined &&
        Number.isFinite(value);

    const levelSeries = series_of(null);

    if (validLevel) {
        for (
            let candleIndex = 0;
            candleIndex < close.length;
            candleIndex++
        ) {
            levelSeries[candleIndex] = value;
        }
    }

    const gammaLine = paint(
        levelSeries,
        {
            name: lineName,
            color: lineColor,
            style: 'line',
            thickness: lineThickness,
            ignoreWhenScaling: true,
            hideInLegend: true
        }
    );

    paint_projection(
        projectedLevel(
            validLevel
                ? value
                : null
        ),
        {
            name: projectionName,
            color: lineColor,
            style: 'line',
            thickness: lineThickness,
            ignoreWhenScaling: true,
            hideInLegend: true
        }
    );

    paint_label_at_line(
        gammaLine,
        Math.max(
            0,
            lastIndex -
            labelOffset
        ),
        validLevel
            ? labelText
            : ' ',
        {
            color: '#FFFFFF',
            background_color: '#101820',
            border_color: lineColor,
            border_width: 1,
            border_radius: 3
        }
    );
}

const gammaLinesEnabled =
    showGammaLines &&
    gammaDataAvailable;

paintGammaLevel(gammaCallWall, gammaLinesEnabled, 'BEAST Call Wall', 'BEAST Call Wall Extension', `CALL WALL ${priceText(gammaCallWall)}`, callLineColor, 0, 2);
paintGammaLevel(gammaPutWall, gammaLinesEnabled, 'BEAST Put Wall', 'BEAST Put Wall Extension', `PUT WALL ${priceText(gammaPutWall)}`, putLineColor, 2, 2);
paintGammaLevel(gammaMagnet, gammaLinesEnabled, 'BEAST Magnet', 'BEAST Magnet Extension', `🧲 MAGNET ${priceText(gammaMagnet)}`, '#AA00FF', 4, 2);
paintGammaLevel(gammaFlip, gammaLinesEnabled, 'BEAST Gamma Flip', 'BEAST Gamma Flip Extension', `GAMMA FLIP ${priceText(gammaFlip)}`, '#FF9100', 6, 2);
paintGammaLevel(expectedMoveUpper, gammaLinesEnabled, 'BEAST EM High', 'BEAST EM High Extension', `EM HIGH ${priceText(expectedMoveUpper)}`, '#00B8D4', 8, 1);
paintGammaLevel(expectedMoveLower, gammaLinesEnabled, 'BEAST EM Low', 'BEAST EM Low Extension', `EM LOW ${priceText(expectedMoveLower)}`, '#00B8D4', 10, 1);

/*
 * ACTIVE TRADE LEVELS
 */

const activeTrade =
    executeBuy ||
    executeSell;

paintGammaLevel(tradeEntry, activeTrade, 'BEAST Trade Entry', 'BEAST Trade Entry Extension', `${executeBuy ? '🐂 BUY' : '🐻 SELL'} ENTRY ${priceText(tradeEntry)}`, '#FFFFFF', 0, 2);
paintGammaLevel(tradeStop, activeTrade, 'BEAST Trade Stop', 'BEAST Trade Stop Extension', `STOP ${priceText(tradeStop)}`, '#FF1744', 2, 2);
paintGammaLevel(tradeTargetOne, activeTrade, 'BEAST Target One', 'BEAST Target One Extension', `T1 ${priceText(tradeTargetOne)} ${tradeTargetOneName}`, '#FFD600', 4, 2);
paintGammaLevel(tradeTargetTwo, activeTrade && tradeTargetTwo !== null, 'BEAST Target Two', 'BEAST Target Two Extension', `T2 ${priceText(tradeTargetTwo)} ${tradeTargetTwoName}`, '#CE93D8', 6, 2);

/*
 * BEAUTIFUL TWO-SECTION DASHBOARD
 */

const dashboardRows = [
    {
        cells: [
            {
                text:'🔥 Neal or No Deal 🐂🐻',
                colspan: 2,
                color: '#FFFFFF',
                background:
                    'linear-gradient(90deg,#00796B,#4527A0)',
                padding: '7px',
                fontSize: '11px',
                fontWeight: 'bold',
                textAlign: 'center'
            }
        ]
    },
    {
        cells: [
            {
                text:
                    `${decisionIcon} ${recommendation}`,
                colspan: 2,
                color: '#FFFFFF',
                background: decisionColor,
                padding: '9px',
                fontSize: '15px',
                fontWeight: 'bold',
                textAlign: 'center'
            }
        ]
    },
    {
        cells: [
            labelCell('ACTION'),
            valueCell(
                action,
                decisionColor
            )
        ]
    },
    {
        cells: [
            labelCell('SIGNAL STRENGTH'),
            valueCell(
                `${signalStrength}/100`,
                signalStrength >=
                    EXECUTION_THRESHOLD
                    ? '#FFD600'
                    : '#CFD8DC'
            )
        ]
    },
    {
        cells: [
            labelCell('TECHNICAL'),
            valueCell(
                `${biasName(
                    currentTechnicalScore
                )} ${signedNumber(
                    currentTechnicalScore
                )}`,
                biasColor(
                    currentTechnicalScore
                )
            )
        ]
    },
    {
        cells: [
            labelCell('OPTIONS FLOW'),
            valueCell(
                `${biasName(
                    optionsScore
                )} ${signedNumber(
                    optionsScore
                )}`,
                biasColor(optionsScore)
            )
        ]
    },
    {
        cells: [
            labelCell('EST. GAMMA'),
            valueCell(
                gammaDataAvailable
                    ? `${biasName(
                        gammaDirectionalScore
                    )} ${signedNumber(
                        gammaDirectionalScore
                    )}`
                    : 'UNAVAILABLE',
                gammaDataAvailable
                    ? biasColor(
                        gammaDirectionalScore
                    )
                    : '#90A4AE'
            )
        ]
    },
    {
        cells: [
            labelCell('GAMMA REGIME'),
            valueCell(
                gammaRegime,
                gammaRegimeColor
            )
        ]
    },
    {
        cells: [
            labelCell('PREMIUM BIAS'),
            valueCell(
                premiumRatioText,
                callPremium >= putPremium
                    ? '#69F0AE'
                    : '#FF5252'
            )
        ]
    },
    {
        cells: [
            labelCell('CALL / PUT'),
            valueCell(
                `${compactMoney(
                    callPremium
                )} / ${compactMoney(
                    putPremium
                )}`
            )
        ]
    },
    {
        cells: [
            labelCell('MAIN FLOW'),
            valueCell(
                dominantStrikeText,
                dominantStrikeType ===
                    'CALL'
                    ? '#69F0AE'
                    : dominantStrikeType ===
                        'PUT'
                        ? '#FF5252'
                        : '#CFD8DC'
            )
        ]
    },
    {
        cells: [
            labelCell('CALL / PUT WALL'),
            valueCell(
                gammaDataAvailable
                    ? `${priceText(
                        gammaCallWall
                    )} / ${priceText(
                        gammaPutWall
                    )}`
                    : 'N/A'
            )
        ]
    },
    {
        cells: [
            labelCell('🧲 MAGNET / FLIP'),
            valueCell(
                gammaDataAvailable
                    ? `${priceText(
                        gammaMagnet
                    )} / ${priceText(
                        gammaFlip
                    )}`
                    : 'N/A',
                '#CE93D8'
            )
        ]
    },
    {
        cells: [
            labelCell('EXPECTED MOVE'),
            valueCell(
                expectedMove !== null
                    ? `±${priceText(
                        expectedMove
                    )} | ` +
                        `${gammaExpirationDTE}d`
                    : 'N/A',
                '#80DEEA'
            )
        ]
    },
    {
        cells: [
            labelCell('FLOW ACTIVITY'),
            valueCell(
                `${acceptedTrades} trades | ` +
                `${sweepCount} sweeps`
            )
        ]
    },
    {
        cells: [
            {
                text: status,
                colspan: 2,
                color:
                    dataConflict ||
                    gammaConflict
                        ? '#FFD600'
                        : '#FFFFFF',
                background: '#0A1116',
                border:
                    'solid #37474F 1px',
                padding: '5px 8px',
                fontSize: '10px',
                fontWeight: 'bold',
                textAlign: 'center',
                whiteSpace: 'nowrap'
            }
        ]
    },
    {
        cells: [
            {
                text:
                    '🎯 BEAST OPTIONS PLAN',
                colspan: 2,
                color: '#FFFFFF',
                background:
                    'linear-gradient(90deg,#6A1B9A,#1565C0)',
                border:
                    'solid #5C6BC0 1px',
                padding: '7px 8px',
                fontSize: '12px',
                fontWeight: 'bold',
                textAlign: 'center'
            }
        ]
    },
    {
        cells: [
            {
                text: optionPlay,
                colspan: 2,
                color: '#FFFFFF',
                background:
                    executeBuy ||
                    executeSell
                        ? optionColor
                        : '#263238',
                border:
                    'solid #455A64 1px',
                padding: '8px',
                fontSize: '14px',
                fontWeight: 'bold',
                textAlign: 'center'
            }
        ]
    },
    {
        cells: [
            labelCell('CONTRACT'),
            valueCell(
                optionContract,
                optionColor
            )
        ]
    },
    {
        cells: [
            labelCell('EXPIRATION'),
            valueCell(
                optionExpiration,
                '#80DEEA'
            )
        ]
    },
    {
        cells: [
            labelCell('TRIGGER'),
            valueCell(
                optionTrigger,
                '#FFFFFF'
            )
        ]
    },
    {
        cells: [
            labelCell('🎯 TARGET'),
            valueCell(
                optionTargetText,
                '#FFD600'
            )
        ]
    },
    {
        cells: [
            labelCell('🛑 INVALIDATION'),
            valueCell(
                optionStopText,
                '#FF8A80'
            )
        ]
    },
    {
        cells: [
            labelCell('R:R TO TARGET'),
            valueCell(
                tradeTargetOneRR !== null
                    ? `${tradeTargetOneRR
                        .toFixed(2)}R`
                    : 'N/A',
                tradeTargetOneRR !== null &&
                tradeTargetOneRR >= 2
                    ? '#69F0AE'
                    : '#FFD600'
            )
        ]
    },
    {
        cells: [
            labelCell('ENVIRONMENT'),
            valueCell(
                optionEnvironment,
                '#CE93D8'
            )
        ]
    },
    {
        cells: [
            labelCell('WHY THIS PLAY'),
            valueCell(
                optionReason,
                '#CFD8DC'
            )
        ]
    },
    {
        cells: [
            {
                text: optionStatus,
                colspan: 2,
                color:
                    executeBuy ||
                    executeSell
                        ? '#FFFFFF'
                        : '#FFD600',
                background: '#0A1116',
                border:
                    'solid #455A64 1px',
                padding: '6px 8px',
                fontSize: '10px',
                fontWeight: 'bold',
                textAlign: 'center',
                whiteSpace: 'nowrap'
            }
        ]
    }
];

const dashboardDefinition = {
    width: '340px',
    borderCollapse: 'collapse',
    background: '#101820',
    border: 'solid #455A64 1px',
    borderRadius: '10px',
    boxShadow:
        '0 5px 18px rgba(0,0,0,0.65)',
    overflow: 'hidden',
    rows: dashboardRows
};

let dashboardPosition = dashPosition;
let dashboardOffsetX = 15;
let dashboardOffsetY = 15;

if (
    dashPosition === 'top_right' ||
    dashPosition === 'center_right' ||
    dashPosition === 'bottom_right'
) {
    dashboardOffsetX = -155;
}

if (
    dashPosition === 'center_left' ||
    dashPosition === 'center_right'
) {
    dashboardOffsetY = 0;
}

if (
    dashPosition === 'bottom_left' ||
    dashPosition === 'bottom_right'
) {
    dashboardOffsetY = -15;
}

paint_overlay(
    'NEAL BEAST V3 DASHBOARD',
    {
        position: dashboardPosition,
        parent: 'chart',
        order: 'above_all',
        offset_x: dashboardOffsetX,
        offset_y: dashboardOffsetY
    },
    dashboardDefinition
);

/*
 * LIVE BUY/SELL TAGS AND ALERT SIGNALS
 */

const buySignal = series_of(false);
const sellSignal = series_of(false);

buySignal[lastIndex] = executeBuy;
sellSignal[lastIndex] = executeSell;

paint(
    buySignal.map(
        signal =>
            signal
                ? '🐂 BEAST BUY'
                : null
    ),
    {
        name: 'BEAST V3 LIVE BUY TAG',
        style: 'labels_below',
        color: '#00E676'
    }
);

paint(
    sellSignal.map(
        signal =>
            signal
                ? '🐻 BEAST SELL'
                : null
    ),
    {
        name: 'BEAST V3 LIVE SELL TAG',
        style: 'labels_above',
        color: '#FF1744'
    }
);

register_signal(
    buySignal,
    'BEAST V3 LIVE BUY'
);

register_signal(
    sellSignal,
    'BEAST V3 LIVE SELL'
);
</code>