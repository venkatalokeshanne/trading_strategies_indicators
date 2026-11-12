<code x-ref="code" class="hljs" data-clipboard-text>const countries = {
  "Australia": "AUS",
  "Canada": "CAN",
  "China": "CHN",
  "European Union": "EUU",
  "Japan": "JPN",
  "Mexico": "MEX",
  "United Kingdom": "GBR",
  "United States": "USA",
  "World": "WLD"
};
const validIndicatorIds = ["BM.KLT.DINV.CD.WD","BX.TRF.PWKR.CD.DT","BX.TRF.PWKR.DT.GD.ZS","BM.KLT.DINV.WD.GD.ZS","BN.KLT.DINV.CD","BX.KLT.DINV.WD.GD.ZS","BX.KLT.DINV.CD.WD","BM.TRF.PWKR.CD.DT","BX.PEF.TOTL.CD.WD","CM.MKT.INDX.ZG","BN.KLT.PTXL.CD","CM.MKT.LDOM.NO","CM.MKT.LCAP.CD","CM.MKT.LCAP.GD.ZS","CM.MKT.TRAD.CD","CM.MKT.TRNR","FB.ATM.TOTL.P5","CM.MKT.TRAD.GD.ZS","FB.BNK.CAPA.ZS","FB.CBK.BRCH.P5","FD.AST.PRVT.GD.ZS","FM.AST.CGOV.ZG.M3","FB.AST.NPER.ZS","FD.RES.LIQU.AS.ZS","FI.RES.XGLD.CD","FI.RES.TOTL.MO","FM.AST.DOMO.ZG.M3","FI.RES.TOTL.CD","FM.AST.DOMS.CN","FM.AST.PRVT.GD.ZS","FM.LBL.BMNY.CN","FM.LBL.BMNY.GD.ZS","FM.LBL.BMNY.ZG","FM.AST.PRVT.ZG.M3","FP.CPI.TOTL","FM.LBL.BMNY.IR.ZS","FP.CPI.TOTL.ZG","FM.AST.NFRG.CN","FR.INR.LEND","FR.INR.RINR","FS.AST.DOMO.GD.ZS","FS.AST.CGOV.GD.ZS","FR.INR.RISK","FS.AST.PRVT.GD.ZS","FX.OWN.TOTL.40.ZS","FX.OWN.TOTL.FE.ZS","FX.OWN.TOTL.60.ZS","FX.OWN.TOTL.OL.ZS","FX.OWN.TOTL.MA.ZS","FX.OWN.TOTL.SO.ZS","FX.OWN.TOTL.YG.ZS","FX.OWN.TOTL.ZS","GFDD.AI.02","FX.OWN.TOTL.PL.ZS","FS.AST.DOMS.GD.ZS","GFDD.AI.06","GFDD.AI.05","GFDD.AI.07","GFDD.AI.10","GFDD.AI.08","GFDD.AI.11","GFDD.AI.12","GFDD.AI.15","GFDD.AI.13","GFDD.AI.16","GFDD.AI.20","GFDD.AI.14","GFDD.AI.21","GFDD.AI.19","GFDD.AI.18","GFDD.AI.23","GFDD.AI.17","GFDD.AI.22","GFDD.AI.09","GFDD.AI.25","GFDD.AI.26","GFDD.AM.02","GFDD.AM.01","GFDD.DI.01","GFDD.DI.02","GFDD.DI.06","GFDD.DI.03","GFDD.DI.05","GFDD.DI.07","GFDD.DI.04","GFDD.DI.08","GFDD.DI.11","GFDD.DI.12","GFDD.DI.10","GFDD.DI.13","GFDD.DM.01","GFDD.DM.02","GFDD.DI.14","GFDD.DI.09","GFDD.DM.08","GFDD.DM.09","GFDD.DM.10","GFDD.DM.07","GFDD.DM.06","GFDD.DM.05","GFDD.EI.01","GFDD.EI.03","GFDD.EI.05","GFDD.EI.06","GFDD.EI.07","GFDD.EI.09","GFDD.EI.08","GFDD.EI.04","GFDD.OI.01","GFDD.OI.02","GFDD.EM.01","GFDD.EI.10","GFDD.OI.06","GFDD.OI.07","GFDD.OI.08","GFDD.OI.09","GFDD.OI.12","GFDD.OI.10","GFDD.OI.13","GFDD.OI.11","GFDD.OI.16","GFDD.OI.14","GFDD.OI.15","GFDD.OI.18","GFDD.OI.17","GFDD.OI.19","GFDD.SI.01","GFDD.OM.02","GFDD.SI.03","GFDD.SI.02","GFDD.SI.05","GFDD.SI.06","GFDD.SI.04","GFDD.OM.01","GFDD.SM.01","GFDD.SI.07","NY.GDP.DEFL.KD.ZG.AD","NY.GDP.DEFL.ZS.AD","PA.NUS.FCRF","PX.REX.REER","PA.NUS.ATLS","SI.RMT.COST.OB.ZS","SM.POP.TOTL","SM.POP.TOTL.ZS","SM.POP.NETM"];
const data = await request.http(`https://api.worldbank.org/v2/topic/7/indicator?per_page=1000&format=json`);
const currentTopicIndicators = data[1].filter(indicator => validIndicatorIds.includes(indicator.id));
const indicatorTitles = currentTopicIndicators.map(indicator => indicator.name);
const currentIndicatorTitle = input.select('Indicator', indicatorTitles[0], indicatorTitles);
const currentIndicator = currentTopicIndicators.find(indicator => indicator.name == currentIndicatorTitle);
const indicatorId = currentIndicator.id;
const indicatorNote = (str => str.length > 80 ? str.slice(0, 80 - 3) + '...' : str)(currentIndicator.sourceNote);
describe_indicator(`World Bank Indicators - Financial Sector`, 'lower', { citation: indicatorNote, shortName: `WBI Finance` });
const country = input.select('Country', 'United States', Object.keys(countries));
const indicatorData = await request.http(`https://api.worldbank.org/v2/country/${countries[country]}/indicator/${indicatorId}?format=json&per_page=20000`);
assert(indicatorData[1] && indicatorData[1].some(d => d.value !== null && d.value !== ''), `The selected indicator doesn't return any data for "${country}".`);
const indicatorTimestamps = indicatorData[1].map(record => {
  const year = parseInt(record.date);
  const milliseconds = Date.UTC(year, 0, 1);
  return milliseconds / 1000;
}).reverse();
const indicatorValues = indicatorData[1].map(record => +record.value || null).reverse();
const lastIndexWithValue = indicatorValues.reduce((a, v, i) => a = v !== null ? i : a, 0);
const isLastValueOlderThanCandles = indicatorTimestamps[lastIndexWithValue] < time[0];
if (isLastValueOlderThanCandles) {
  indicatorTimestamps.push(time[0]);
  indicatorValues.push(indicatorValues[lastIndexWithValue]);
}
const indicatorLine = interpolate_sparse_series(land_points_onto_series(indicatorTimestamps, interpolate_sparse_series(indicatorValues), time, 'ge'), 'constant');
paint(indicatorLine, 'Line', '#469e48');</code>