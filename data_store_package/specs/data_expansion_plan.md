# Data Expansion Plan: Global Macro Data Store
# Version: 1.0
# Created: 2026-04-09
# Status: PLAN — Not yet implemented

## Executive Summary

This plan expands the data-store from ~20 series (AU/US equities, rates, FX, commodities) to a comprehensive global macro database modelled on FRED-M (McCracken & Ng, 2016). The target is ~130 US series plus equivalent coverage for 7 additional countries, plus expanded commodities — roughly 400-500 total series.

The approach is phased: get FRED working first (the API key exists and the architecture is ready), then Australia (existing RBA/ABS stubs), then other developed markets, then commodities and derived signals.

---

## Phase 1: FRED (United States) — GET THIS WORKING FIRST

### Why First
- API key already available (9e824c10b39c317a034e84dc5ecd9e74)
- `fredapi` Python package is mature and well-documented
- FRED-M defines the template that other countries will map to
- 5 FRED series already defined in series_definitions.json (UST10Y, UST2Y, EURUSD, USDJPY, FED_FUNDS, US_CPI, JLN_UNCERTAINTY, IG_SPREAD)
- fred_ingest.py exists as a stub — just needs implementation

### API Details
- **Base URL**: https://api.stlouisfed.org
- **Auth**: API key as query parameter (`api_key=`)
- **Rate limit**: 120 requests/minute (conservative: 1 req/sec)
- **Python package**: `fredapi` — `pip install fredapi`
- **Response**: Returns pandas Series directly via `fred.get_series()`

### FRED-M Series to Implement (~80 core monthly series)

#### Output & Income (8 series)
| series_id | FRED ID | Label | Frequency | Start |
|-----------|---------|-------|-----------|-------|
| US_INDPRO | INDPRO | Industrial Production Index | monthly | 1919 |
| US_RPI | W875RX1 | Real Personal Income ex Transfers | monthly | 1959 |
| US_CUMFNS | CUMFNS | Capacity Utilization: Manufacturing | monthly | 1948 |
| US_IPMAN | IPMAN | IP: Manufacturing | monthly | 1972 |
| US_IPFPNSS | IPFPNSS | IP: Final Products & Nonindustrial Supplies | monthly | 1947 |
| US_IPDCONGD | IPDCONGD | IP: Durable Consumer Goods | monthly | 1947 |
| US_IPNCONGD | IPNCONGD | IP: Nondurable Consumer Goods | monthly | 1947 |
| US_IPBUSEQ | IPBUSEQ | IP: Business Equipment | monthly | 1947 |

#### Labor Market (12 series)
| series_id | FRED ID | Label | Frequency | Start |
|-----------|---------|-------|-----------|-------|
| US_PAYEMS | PAYEMS | Total Nonfarm Payrolls | monthly | 1939 |
| US_UNRATE | UNRATE | Civilian Unemployment Rate | monthly | 1948 |
| US_CIVPART | CIVPART | Labor Force Participation Rate | monthly | 1948 |
| US_EMRATIO | EMRATIO | Employment-Population Ratio | monthly | 1948 |
| US_AWHMAN | AWHMAN | Avg Weekly Hours: Manufacturing | monthly | 1939 |
| US_CES0600000008 | CES0600000008 | Avg Hourly Earnings: Goods-Producing | monthly | 1939 |
| US_ICSA | ICSA | Initial Jobless Claims (weekly→monthly) | weekly | 1967 |
| US_UEMPMEAN | UEMPMEAN | Avg Duration of Unemployment | monthly | 1948 |
| US_CE16OV | CE16OV | Civilian Employment | monthly | 1948 |
| US_CLF16OV | CLF16OV | Civilian Labor Force | monthly | 1948 |
| US_MANEMP | MANEMP | Manufacturing Employment | monthly | 1939 |
| US_SRVPRD | SRVPRD | Service-Providing Employment | monthly | 1939 |

#### Housing (5 series)
| series_id | FRED ID | Label | Frequency | Start |
|-----------|---------|-------|-----------|-------|
| US_HOUST | HOUST | Housing Starts: Total | monthly | 1959 |
| US_PERMIT | PERMIT | New Building Permits | monthly | 1960 |
| US_HSN1F | HSN1F | New One Family Houses Sold | monthly | 1963 |
| US_MORTGAGE30 | MORTGAGE30US | 30-Year Fixed Mortgage Rate | weekly | 1971 |
| US_USSTHPI | USSTHPI | All-Transactions House Price Index | quarterly | 1975 |

#### Consumption, Orders & Inventories (8 series)
| series_id | FRED ID | Label | Frequency | Start |
|-----------|---------|-------|-----------|-------|
| US_RRSFS | RSXFS | Real Retail & Food Services Sales | monthly | 1992 |
| US_UMCSENT | UMCSENT | U Michigan Consumer Sentiment | monthly | 1952 |
| US_DPCERA3M | DPCERA3M086SBEA | Real Personal Consumption Expenditures | monthly | 1959 |
| US_DGORDER | DGORDER | Durable Goods New Orders | monthly | 1992 |
| US_NEWORDER | NEWORDER | Manufacturers New Orders: Nondefense Capital Goods ex Aircraft | monthly | 1992 |
| US_ISRATIO | ISRATIO | Total Business: Inventories to Sales Ratio | monthly | 1992 |
| US_NAPM | NAPM | ISM Manufacturing PMI (if on FRED) | monthly | 1948 |
| US_NAPMNOI | NAPMNOI | ISM Manufacturing New Orders Index | monthly | 1948 |

#### Money & Credit (6 series)
| series_id | FRED ID | Label | Frequency | Start |
|-----------|---------|-------|-----------|-------|
| US_M1SL | M1SL | M1 Money Stock | monthly | 1959 |
| US_M2SL | M2SL | M2 Money Stock | monthly | 1959 |
| US_TOTRESNS | TOTRESNS | Total Reserves | monthly | 1959 |
| US_BUSLOANS | BUSLOANS | Commercial & Industrial Loans | monthly | 1947 |
| US_CONSUMER | CONSUMER | Consumer Loans at Commercial Banks | monthly | 1947 |
| US_TOTALSL | TOTALSL | Total Consumer Credit Outstanding | monthly | 1943 |

#### Interest Rates & Spreads (12 series — some already defined)
| series_id | FRED ID | Label | Frequency | Start |
|-----------|---------|-------|-----------|-------|
| FED_FUNDS | FEDFUNDS | Fed Funds Effective Rate | monthly | 1954 |
| US_DFF | DFF | Fed Funds Daily | daily | 1954 |
| US_TB3MS | TB3MS | 3-Month T-Bill | monthly | 1934 |
| US_GS1 | GS1 | 1-Year Treasury CMR | monthly | 1953 |
| US_GS5 | GS5 | 5-Year Treasury CMR | monthly | 1953 |
| UST10Y | DGS10 | 10-Year Treasury (already defined) | daily | 1962 |
| UST2Y | DGS2 | 2-Year Treasury (already defined) | daily | 1976 |
| US_AAA | AAA | Moody's Aaa Corporate Bond Yield | monthly | 1919 |
| US_BAA | BAA | Moody's Baa Corporate Bond Yield | monthly | 1919 |
| IG_SPREAD | BAMLC0A0CM | ICE BofA US Corporate OAS (already defined) | daily | 1996 |
| US_T5YIFR | T5YIFR | 5Y5Y Forward Inflation Expectation | daily | 2003 |
| US_TEDRATE | TEDRATE | TED Spread (3M LIBOR minus T-Bill) | daily | 1986 |

#### Prices & Inflation (8 series)
| series_id | FRED ID | Label | Frequency | Start |
|-----------|---------|-------|-----------|-------|
| US_CPI | CPIAUCSL | CPI All Urban SA (already defined) | monthly | 1947 |
| US_CPILFESL | CPILFESL | Core CPI (less food & energy) | monthly | 1957 |
| US_PPIACO | PPIACO | PPI All Commodities | monthly | 1913 |
| US_PCEPI | PCEPI | PCE Price Index | monthly | 1959 |
| US_PCEPILFE | PCEPILFE | Core PCE Price Index | monthly | 1959 |
| US_CPIENGSL | CPIENGSL | CPI Energy | monthly | 1957 |
| US_CPIFABSL | CPIFABSL | CPI Food & Beverages | monthly | 1967 |
| US_GDPDEF | GDPDEF | GDP Implicit Price Deflator | quarterly | 1947 |

#### Exchange Rates (4 series — some already defined)
| series_id | FRED ID | Label | Frequency | Start |
|-----------|---------|-------|-----------|-------|
| US_TWEXB | TWEXBMTH | Trade-Weighted Dollar Index: Broad | monthly | 1973 |
| EURUSD | DEXUSEU | EUR/USD (already defined) | daily | 1999 |
| USDJPY | DEXJPUS | USD/JPY (already defined) | daily | 1971 |
| US_EXUSUK | DEXUSUK | USD/GBP | daily | 1971 |

#### Uncertainty & Expectations (4 series)
| series_id | FRED ID | Label | Frequency | Start |
|-----------|---------|-------|-----------|-------|
| JLN_UNCERTAINTY | JLNUM12M | JLN Macro Uncertainty (already defined) | monthly | 1960 |
| US_VIXCLS | VIXCLS | VIX (FRED version) | daily | 1990 |
| US_EXPINF1YR | EXPINF1YR | Expected Inflation 1-Year | monthly | 1978 |
| US_UMCSENT | UMCSENT | Consumer Expectations (sub-index) | monthly | 1952 |

### Implementation Approach
```python
# fred_ingest.py approach
from fredapi import Fred
import pandas as pd

fred = Fred(api_key='9e824c10b39c317a034e84dc5ecd9e74')

def fetch(series_id: str, source_id: str, start: str) -> pd.DataFrame:
    """Download a single FRED series and return as DataFrame."""
    data = fred.get_series(source_id, observation_start=start)
    df = pd.DataFrame({'date': data.index, 'value': data.values})
    df['date'] = pd.to_datetime(df['date'])
    return df.set_index('date')
```

### Estimated Effort
- Implement fred_ingest.py: **2-3 hours**
- Add ~70 new series definitions to series_definitions.json: **1-2 hours**
- Test full FRED download pipeline: **1 hour**
- Total Phase 1: **~1 day**

---

## Phase 2: Australia (ABS + RBA) — SECOND PRIORITY

### Why Second
- Mike is Australia-based; AUS series already partially defined
- RBA data is simple CSV downloads (no API key needed)
- ABS has a free SDMX API (no API key needed since Nov 2024)
- Stubs already exist: rba_ingest.py, abs_ingest.py

### RBA Data Access
- **Method**: Direct CSV download from https://www.rba.gov.au/statistics/tables/csv/
- **Auth**: None required
- **Format**: CSV with date index
- **Rate limits**: None documented
- **URL pattern**: `https://www.rba.gov.au/statistics/tables/csv/{table}-data.csv`

#### RBA Series (~10 series)
| series_id | RBA Table | Column | Label | Freq |
|-----------|-----------|--------|-------|------|
| AGB10Y | F2 | FCMYGBAG10D | 10Y Govt Bond Yield | daily |
| AGB2Y | F2 | FCMYGBAG2D | 2Y Govt Bond Yield | daily |
| AUS_CASHRATE | F1 | FIRMMCRTD | Cash Rate Target | daily |
| AUDUSD | F11 | FXRUSD | AUD/USD | daily |
| AUS_TWI | F11 | FXRTWI | Trade-Weighted Index | daily |
| AUS_MORTGAGE | F5 | FILRHLBVS | Standard Variable Mortgage Rate | monthly |
| IRON_ORE | I2 | PCIRON | Iron Ore 62% Fe | monthly |
| AUS_COAL | I2 | PCCOAL | Thermal Coal | monthly |
| AUS_RURALCPI | G1 | — | CPI (RBA version) | quarterly |
| AUS_CORPSPREAD | F3 | — | Corporate Bond Spread | daily |

### ABS Data Access (SDMX API)
- **Base URL**: https://data.api.abs.gov.au/rest/data/
- **Auth**: None required (free since Nov 2024)
- **Format**: SDMX-JSON, SDMX-CSV
- **Python**: `pandasdmx` or direct HTTP requests
- **Rate limits**: Not documented

#### ABS Series (~12 series)
| series_id | ABS Cat | Label | Freq | Start |
|-----------|---------|-------|------|-------|
| AUS_CPI | 6401.0 | CPI All Groups | quarterly | 1948 |
| AUS_CPI_TRIMMED | 6401.0 | Trimmed Mean CPI | quarterly | 2002 |
| AUS_UNEMP | 6202.0 | Unemployment Rate SA | monthly | 1966 |
| AUS_EMPLOY | 6202.0 | Employment Level SA | monthly | 1966 |
| AUS_PARTRATE | 6202.0 | Participation Rate SA | monthly | 1966 |
| AUS_GDP | 5206.0 | GDP Chain Volume | quarterly | 1959 |
| AUS_RETAIL | 8501.0 | Retail Turnover SA | monthly | 1982 |
| AUS_BLDGAPPRV | 8731.0 | Building Approvals SA | monthly | 1983 |
| AUS_TRADEBAL | 5368.0 | Trade Balance | monthly | 1971 |
| AUS_HOUSINGFIN | 5609.0 | Housing Finance Commitments | monthly | 2002 |
| AUS_WAGEPRICE | 6345.0 | Wage Price Index | quarterly | 1997 |
| AUS_PPI | 6427.0 | Producer Price Index | quarterly | 1998 |

### Australia Gaps — NOT available via API
| Indicator | Source | Access Method | Notes |
|-----------|--------|---------------|-------|
| PMI (Manufacturing) | Judo Bank / S&P Global | Manual / Trading Economics | Subscription for full history |
| Consumer Confidence | Westpac-Melbourne Institute | Manual download | Published monthly, no API |
| Business Confidence | NAB Business Survey | Manual download | Published monthly, no API |
| Industrial Production | N/A — Australia has no IP index | Use retail + GDP as proxy | ABS stopped MBTI Oct 2025 |

### Implementation Approach
```python
# rba_ingest.py approach
import pandas as pd

RBA_CSV_BASE = "https://www.rba.gov.au/statistics/tables/csv"

def fetch(series_id: str, source_id: str, start: str, source_col: str = None) -> pd.DataFrame:
    url = f"{RBA_CSV_BASE}/{source_id}-data.csv"
    df = pd.read_csv(url)
    # RBA CSVs have metadata rows at top — need to find header row
    # Parse date column, select source_col, filter from start
    ...
```

### Estimated Effort
- Implement rba_ingest.py: **3-4 hours** (CSV parsing with RBA quirks)
- Implement abs_ingest.py: **4-5 hours** (SDMX API learning curve)
- Add ~22 new series definitions: **1 hour**
- Test pipeline: **2 hours**
- Total Phase 2: **~2 days**

---

## Phase 3: Other Developed Markets

### 3A. Canada

#### Statistics Canada (statcan.gc.ca)
- **API**: REST API (Web Data Service) + SDMX REST
- **Base URL**: https://www150.statcan.gc.ca/t1/wds/sdmx/statcan/rest/
- **Auth**: None required
- **Rate limits**: 50 req/sec server, 25 req/sec per IP
- **Format**: JSON, CSV, XML
- **Python**: `stats_can` package
- **API key needed**: No

#### Bank of Canada
- **API**: Valet API — https://www.bankofcanada.ca/valet/
- **Auth**: None required
- **Rate limits**: Not officially documented; start slow
- **Format**: JSON, CSV, XML
- **Python**: `pyvalet` package
- **API key needed**: No

#### Canadian Series (~18 series)
| series_id | Source | Source ID | Label | Freq |
|-----------|--------|-----------|-------|------|
| CA_CPI | StatCan | 18-10-0004-01 | CPI All Items | monthly |
| CA_COREINFL | StatCan | 18-10-0256-01 | CPI Common/Trim/Median | monthly |
| CA_UNEMP | StatCan | 14-10-0287-01 | Unemployment Rate SA | monthly |
| CA_EMPLOY | StatCan | 14-10-0287-01 | Employment Level SA | monthly |
| CA_GDP | StatCan | 36-10-0434-01 | GDP at Basic Prices Monthly | monthly |
| CA_GDP_Q | StatCan | 36-10-0104-01 | GDP Quarterly | quarterly |
| CA_INDPRO | StatCan | 16-10-0048-01 | Manufacturing Sales | monthly |
| CA_RETAIL | StatCan | 20-10-0008-01 | Retail Trade SA | monthly |
| CA_BLDGPERM | StatCan | 34-10-0066-01 | Building Permits | monthly |
| CA_TRADEBAL | StatCan | 12-10-0011-01 | Merchandise Trade | monthly |
| CA_POLRATE | BoC Valet | — | Overnight Rate | daily |
| CA_BOND2Y | BoC Valet | — | 2Y Govt Bond Yield | daily |
| CA_BOND10Y | BoC Valet | — | 10Y Govt Bond Yield | daily |
| CA_CADUSD | BoC Valet | FXCADUSD | CAD/USD | daily |
| CA_CEER | BoC Valet | CEER_MONTHLY | CAD Effective Exchange Rate | monthly |
| CA_M2 | BoC Valet | — | Monetary Aggregate M2+ | monthly |
| CA_HOUSEPRICE | StatCan/Teranet | — | House Price Index | monthly |
| CA_IVEY | External | — | Ivey PMI (manual) | monthly |

#### Gaps
- PMI: Ivey PMI not available via API (manual download from iveypmi.uwo.ca)
- Consumer Confidence: Conference Board of Canada (subscription required)
- Some leading indicators available via FRED's Canada category (~2,500 series)

#### API Key Required: **No** (neither StatCan nor BoC require keys)
#### Estimated Effort: **2-3 days** (two separate APIs to implement)

---

### 3B. United Kingdom

#### ONS (Office for National Statistics)
- **API**: REST API (Beta) — https://api.beta.ons.gov.uk/v1
- **Auth**: None required
- **Rate limits**: 120 req/10sec, 200 req/min
- **Format**: JSON, CSV
- **API key needed**: No

#### Bank of England
- **Method**: CSV download from IADB (Interactive Analytical Database)
- **URL**: https://www.bankofengland.co.uk/boeapps/database/
- **Auth**: None
- **Format**: CSV
- **Python**: Direct HTTP download; `boe` R package exists but no mature Python wrapper

#### UK Series (~18 series)
| series_id | Source | Label | Freq |
|-----------|--------|-------|------|
| UK_CPI | ONS | CPI All Items | monthly |
| UK_CPIH | ONS | CPIH (incl housing) | monthly |
| UK_COREINFL | ONS | Core CPI | monthly |
| UK_UNEMP | ONS | Unemployment Rate | monthly |
| UK_EMPLOY | ONS | Employment Level | monthly |
| UK_EARNINGS | ONS | Average Weekly Earnings | monthly |
| UK_GDP | ONS | GDP Monthly Estimate | monthly |
| UK_GDP_Q | ONS | GDP Quarterly | quarterly |
| UK_INDPRO | ONS | Index of Production | monthly |
| UK_RETAIL | ONS | Retail Sales Volume | monthly |
| UK_HPI | ONS | UK House Price Index | monthly |
| UK_TRADEBAL | ONS | Trade Balance | monthly |
| UK_BANKRATE | BoE | Bank Rate | daily |
| UK_GILT2Y | BoE | 2Y Gilt Yield | daily |
| UK_GILT10Y | BoE | 10Y Gilt Yield | daily |
| UK_GBPUSD | BoE | GBP/USD | daily |
| UK_M4 | BoE | Broad Money (M4) | monthly |
| UK_SONIA | BoE | Sterling Overnight Rate | daily |

#### Gaps
- PMI: S&P Global UK PMI (subscription required; headline available free)
- Consumer Confidence: GfK (subscription required)
- Housing: Halifax/Nationwide indices available as press releases only

#### API Key Required: **No**
#### Estimated Effort: **2-3 days** (ONS API is well-documented; BoE CSV needs custom parser)

---

### 3C. Euro Area / EMU

#### Eurostat
- **API**: SDMX 3.0 / 2.1 REST API
- **Base URL**: https://ec.europa.eu/eurostat/api/dissemination/
- **Auth**: None required
- **Rate limits**: Not documented
- **Format**: XML, JSON, CSV
- **Python**: `eurostat` package, `pandasdmx`
- **API key needed**: No

#### ECB Statistical Data Warehouse
- **API**: SDMX 2.1 REST API
- **Base URL**: https://data.ecb.europa.eu/ (new portal) / https://sdw-wsrest.ecb.europa.eu/ (legacy)
- **Auth**: None required
- **Format**: XML, JSON, CSV
- **Python**: `pandasdmx` (built-in ECB source)
- **API key needed**: No

#### Euro Area Series (~20 series)
| series_id | Source | Label | Freq | Start |
|-----------|--------|-------|------|-------|
| EA_HICP | Eurostat | HICP All Items | monthly | 1996 |
| EA_COREHICP | Eurostat | Core HICP (ex food/energy) | monthly | 1996 |
| EA_UNEMP | Eurostat | Unemployment Rate | monthly | 1998 |
| EA_EMPLOY | Eurostat | Employment Level | quarterly | 1995 |
| EA_GDP | Eurostat | GDP Volume | quarterly | 1995 |
| EA_INDPRO | Eurostat | Industrial Production Index | monthly | 1990 |
| EA_RETAIL | Eurostat | Retail Trade Volume | monthly | 1995 |
| EA_CONSTRPROD | Eurostat | Construction Production | monthly | 1995 |
| EA_TRADEBAL | Eurostat | Trade Balance | monthly | 1999 |
| EA_CONSCONF | Eurostat | Consumer Confidence Indicator | monthly | 1985 |
| EA_ECONSENTIMENT | Eurostat | Economic Sentiment Indicator | monthly | 1985 |
| EA_MRR | ECB | Main Refinancing Rate | daily | 1999 |
| EA_DEPORATE | ECB | Deposit Facility Rate | daily | 1999 |
| EA_DE10Y | ECB | German 10Y Bund Yield | daily | 1999 |
| EA_IT10Y | ECB | Italian 10Y BTP Yield | daily | 1999 |
| EA_FR10Y | ECB | French 10Y OAT Yield | daily | 1999 |
| EURUSD | FRED | EUR/USD (already defined) | daily | 1999 |
| EA_EURNEER | ECB | EUR Nominal Effective Exchange Rate | monthly | 1999 |
| EA_M3 | ECB | Monetary Aggregate M3 | monthly | 1980 |
| EA_CREDIT | ECB | Credit to Private Sector | monthly | 1999 |

#### Gaps
- PMI: S&P Global Euro PMI (subscription; headline free)
- Housing: Eurostat publishes House Price Index (sts_hpi) but quarterly only

#### API Key Required: **No** (neither Eurostat nor ECB require keys)
#### Estimated Effort: **2-3 days** (SDMX learning curve but pandasdmx handles both)

---

### 3D. Japan

#### e-Stat (Statistics Bureau)
- **API**: REST API at https://www.e-stat.go.jp/api/
- **Auth**: Free registration required — Application ID (up to 3 per account)
- **Format**: XML, JSON, CSV
- **Python**: Unofficial wrapper `estat-api` on GitHub
- **Language**: English documentation available
- **API key needed**: **Yes** (free registration at e-stat.go.jp)

#### Bank of Japan
- **API**: REST API at https://www.stat-search.boj.or.jp/
- **Auth**: None required (public)
- **Format**: JSON, CSV
- **Rate limits**: Max 60,000 observations per request
- **Python**: `bojpy` package on PyPI
- **Update frequency**: 3x daily (9:00, 12:00, 15:00 JST)
- **API key needed**: **No**

#### Japanese Series (~18 series)
| series_id | Source | Label | Freq | Start |
|-----------|--------|-------|------|-------|
| JP_CPI | e-Stat | CPI All Items | monthly | 1970 |
| JP_CORECPI | e-Stat | CPI ex Fresh Food | monthly | 1970 |
| JP_UNEMP | e-Stat | Unemployment Rate | monthly | 1953 |
| JP_EMPLOY | e-Stat | Employment Level | monthly | 1953 |
| JP_GDP | e-Stat/Cabinet Office | GDP Quarterly | quarterly | 1980 |
| JP_INDPRO | METI/e-Stat | Industrial Production Index | monthly | 1978 |
| JP_RETAIL | METI/e-Stat | Retail Sales | monthly | 1980 |
| JP_HOUSESTARTS | e-Stat | Housing Starts | monthly | 1965 |
| JP_TRADEBAL | e-Stat | Trade Balance | monthly | 1979 |
| JP_CONSCONF | Cabinet Office | Consumer Confidence | monthly | 1982 |
| JP_TANKAN_MFG | BOJ | Tankan Manufacturing DI | quarterly | 1974 |
| JP_TANKAN_NONMFG | BOJ | Tankan Non-Manufacturing DI | quarterly | 1974 |
| JP_CALLRATE | BOJ | Uncollateralized O/N Call Rate | daily | 1985 |
| JP_JGB2Y | BOJ/MOF | 2Y JGB Yield | daily | 1974 |
| JP_JGB10Y | BOJ/MOF | 10Y JGB Yield | daily | 1974 |
| USDJPY | FRED | USD/JPY (already defined) | daily | 1971 |
| JP_JPYNEER | BOJ | JPY Nominal Effective Exchange Rate | monthly | 1980 |
| JP_M2 | BOJ | Money Stock M2 | monthly | 1967 |

#### Gaps
- PMI: Jibun Bank/S&P Global (subscription; headline free)
- Economy Watchers Survey: Available via e-Stat API
- Some English documentation is limited; series codes may need mapping

#### API Key Required: **Yes — e-Stat requires free registration**
#### Estimated Effort: **3-4 days** (language/documentation challenges, two separate APIs)

---

### 3E. New Zealand

#### Stats NZ
- **API**: Aotearoa Data Explorer REST API
- **Base URL**: https://api.data.stats.govt.nz/
- **Auth**: **API key required** (free registration at portal.apis.stats.govt.nz)
- **Format**: JSON, XML, CSV (SDMX 2.1 compliant)
- **Alternative**: Infoshare (web tool, manual downloads)
- **API key needed**: **Yes** (free)

#### RBNZ
- **Method**: Excel spreadsheet downloads (no API)
- **URL**: https://www.rbnz.govt.nz/statistics/series/data-file-index-page
- **Auth**: None
- **Format**: Excel (.xlsx) only
- **Python**: Parse with openpyxl/pandas after download

#### NZ Series (~14 series)
| series_id | Source | Label | Freq |
|-----------|--------|-------|------|
| NZ_CPI | Stats NZ | CPI All Groups | quarterly |
| NZ_UNEMP | Stats NZ | Unemployment Rate | quarterly |
| NZ_EMPLOY | Stats NZ | Employment Level | quarterly |
| NZ_GDP | Stats NZ | GDP Production | quarterly |
| NZ_RETAIL | Stats NZ | Retail Trade | quarterly |
| NZ_BLDGCONSENT | Stats NZ | Building Consents | monthly |
| NZ_TRADEBAL | Stats NZ | Goods Trade Balance | monthly |
| NZ_OCR | RBNZ | Official Cash Rate | daily |
| NZ_BOND2Y | RBNZ | 2Y Govt Bond Yield | daily |
| NZ_BOND10Y | RBNZ | 10Y Govt Bond Yield | daily |
| NZ_NZDUSD | RBNZ | NZD/USD | daily |
| NZ_TWI | RBNZ | Trade-Weighted Index | daily |
| NZ_M2 | RBNZ | Broad Money | monthly |
| NZ_HOUSEPRICE | REINZ | REINZ House Price Index | monthly |

#### Key Limitation
NZ publishes most economic data **quarterly** (not monthly). CPI, labour force, and GDP are all quarterly. This limits usefulness for monthly factor models — NZ data is best used for quarterly models or as supplementary context.

#### Gaps
- PMI: BNZ-BusinessNZ PMI (published on website; no API)
- Consumer/Business Confidence: ANZ-Roy Morgan surveys (manual)
- Housing: REINZ data requires membership or fee

#### API Key Required: **Yes — Stats NZ requires free API key**
#### Estimated Effort: **2 days** (quarterly frequency simplifies things; RBNZ Excel parsing is fiddly)

---

### 3F. Switzerland

#### BFS (Federal Statistical Office)
- **API**: STAT-TAB PXWeb API (REST)
- **Auth**: None required
- **Format**: Various (via PXWeb)
- **Language**: German/French most complete; English limited
- **Python**: R package exists (`BFS`); Python via direct HTTP
- **API key needed**: No

#### SNB (Swiss National Bank)
- **API**: REST API with SDMX standard at https://data.snb.ch/
- **Auth**: None required
- **Format**: CSV, JSON
- **Python**: R package `SNBdata`; Python `kofdata_py` for KOF data
- **API key needed**: No

#### Swiss Series (~14 series)
| series_id | Source | Label | Freq |
|-----------|--------|-------|------|
| CH_CPI | BFS | CPI All Items | monthly |
| CH_CORECPI | BFS | Core CPI | monthly |
| CH_UNEMP | BFS/SECO | Unemployment Rate | monthly |
| CH_GDP | BFS | GDP Quarterly | quarterly |
| CH_INDPRO | BFS | Industrial Production | quarterly |
| CH_RETAIL | BFS | Retail Trade Turnover | monthly |
| CH_TRADEBAL | BFS | Trade Balance | monthly |
| CH_KOF | KOF | KOF Economic Barometer | monthly |
| CH_CONSCONF | SECO | Consumer Climate Index | quarterly |
| CH_POLICYRATE | SNB | SNB Policy Rate | daily |
| CH_CONFBOND10Y | SNB | 10Y Confederation Bond Yield | daily |
| CH_CHFUSD | SNB | CHF/USD | daily |
| CH_CHFEUR | SNB | CHF/EUR | daily |
| CH_M2 | SNB | Monetary Aggregate M2 | monthly |

#### Gaps
- PMI: procure.ch PMI (published on website; no API; headline via Trading Economics)
- Some BFS datasets have limited English metadata

#### API Key Required: **No**
#### KOF API: **Optional API key for full access** (public endpoint for headline indicators)
#### Estimated Effort: **2-3 days** (multiple sources to coordinate)

---

## Phase 4: Commodities & Derived Series

### 4A. Expanded Commodity Coverage

#### From FRED (most reliable)
| series_id | FRED ID | Label | Freq |
|-----------|---------|-------|------|
| COMM_WTI | DCOILWTICO | WTI Crude Oil | daily |
| COMM_BRENT_FRED | DCOILBRENTEU | Brent Crude (FRED version) | daily |
| COMM_GOLD_FRED | GOLDAMGBD228NLBM | Gold London AM Fix | daily |
| COMM_COPPER_M | PCOPPUSDM | Global Copper Price | monthly |
| COMM_ALLCOMM | PALLFNFINDEXM | All Commodities Price Index | monthly |
| COMM_NATGAS | MHHNGSP | Henry Hub Natural Gas Spot | monthly |
| COMM_ALUMINIUM | PALUMUSDM | Global Aluminum Price | monthly |
| COMM_NICKEL | PNICKUSDM | Global Nickel Price | monthly |

#### From yfinance (daily prices — use with retry logic)
| series_id | Ticker | Label | Freq |
|-----------|--------|-------|------|
| GOLD | GC=F | Gold Futures (already defined) | daily |
| BRENT | BZ=F | Brent Futures (already defined) | daily |
| COPPER | HG=F | Copper Futures (already defined) | daily |
| COMM_WTI_F | CL=F | WTI Futures | daily |
| COMM_NATGAS_F | NG=F | Natural Gas Futures | daily |
| COMM_SILVER | SI=F | Silver Futures | daily |
| COMM_CORN | ZC=F | Corn Futures | daily |
| COMM_WHEAT | ZW=F | Wheat Futures | daily |
| COMM_SOYBEANS | ZS=F | Soybean Futures | daily |

#### From RBA (already planned)
| series_id | Source | Label | Freq |
|-----------|--------|-------|------|
| IRON_ORE | RBA I2 | Iron Ore 62% Fe (already defined) | monthly |
| AUS_COAL | RBA I2 | Thermal Coal | monthly |

### 4B. Derived Series (computed from raw)

#### Cross-Country Spreads
| series_id | Formula | Label |
|-----------|---------|-------|
| US_TERM_SPREAD | UST10Y - UST2Y | US Term Spread (already defined) |
| AUS_TERM_SPREAD | AGB10Y - AUS_CASHRATE | AUS Term Spread (already defined) |
| UK_TERM_SPREAD | UK_GILT10Y - UK_BANKRATE | UK Term Spread |
| CA_TERM_SPREAD | CA_BOND10Y - CA_POLRATE | Canada Term Spread |
| EA_PERIPH_SPREAD | EA_IT10Y - EA_DE10Y | Italy-Germany 10Y Spread |
| JP_TERM_SPREAD | JP_JGB10Y - JP_CALLRATE | Japan Term Spread |

#### Inflation Differentials
| series_id | Formula | Label |
|-----------|---------|-------|
| US_REALRATE | UST10Y - US_T5YIFR | US Approx Real Rate |
| US_INFLATION_YOY | log_diff(US_CPI, 12) | US CPI YoY |
| AUS_INFLATION_YOY | log_diff(AUS_CPI, 4) | AUS CPI YoY (quarterly) |

#### Cross-Country Rate Differentials
| series_id | Formula | Label |
|-----------|---------|-------|
| AUUS_RATEDIFF | AUS_CASHRATE - FED_FUNDS | AU-US Rate Differential |
| USEA_RATEDIFF | FED_FUNDS - EA_DEPORATE | US-EA Rate Differential |
| USJP_RATEDIFF | FED_FUNDS - JP_CALLRATE | US-JP Rate Differential |

### Estimated Effort
- Expand yfinance_ingest.py with retry logic: **2-3 hours**
- Add FRED commodity series: **1 hour** (just new definitions; ingestor already built)
- Implement derived series computation: **3-4 hours**
- Total Phase 4: **~1 day**

---

## Phase 5: Supplementary & Cross-Country Sources

### OECD Data Explorer (fallback for gaps)
- **API**: SDMX REST via https://data-explorer.oecd.org/
- **Auth**: None required
- **Useful for**: Harmonized CPI, unemployment, GDP, CLI (Composite Leading Indicators) across all OECD countries
- **Advantage**: Single API for comparable cross-country series
- **Python**: `pandasdmx` (OECD is a built-in source)
- **Note**: Legacy OECD.Stat API shut down July 2024; use new Data Explorer API only

### IMF Data
- **API**: REST via https://data.imf.org/
- **Useful for**: IFS (International Financial Statistics), commodity prices
- **Python**: Direct HTTP requests

### World Bank
- **Method**: Bulk Excel download (Pink Sheet)
- **Useful for**: Long-history commodity prices back to 1960s
- **No REST API for commodity prices** — manual download

---

## API Key Registration Required

| Country | Agency | Key Required | Registration URL | Cost |
|---------|--------|-------------|-----------------|------|
| US | FRED | Already have | fredaccount.stlouisfed.org | Free |
| Australia | ABS | No (removed Nov 2024) | — | — |
| Australia | RBA | No | — | — |
| Japan | e-Stat | Yes | e-stat.go.jp | Free |
| New Zealand | Stats NZ | Yes | portal.apis.stats.govt.nz | Free |
| Canada | StatCan | No | — | — |
| Canada | Bank of Canada | No | — | — |
| UK | ONS | No | — | — |
| UK | Bank of England | No | — | — |
| EU | Eurostat | No | — | — |
| EU | ECB | No | — | — |
| Switzerland | BFS | No | — | — |
| Switzerland | SNB | No | — | — |
| Switzerland | KOF | Optional | datenservice.kof.ethz.ch | Free |

**Action items**: Register for free API keys at:
1. Japan e-Stat: https://www.e-stat.go.jp/api/en
2. NZ Stats: https://portal.apis.stats.govt.nz/

---

## Architecture Decisions

### New Ingest Scripts Required
```
pipeline/ingest/
  fred_ingest.py       ← Phase 1 (implement first)
  rba_ingest.py        ← Phase 2 (CSV downloads)
  abs_ingest.py        ← Phase 2 (SDMX API)
  yfinance_ingest.py   ← Phase 1 (already defined, add retry logic)
  statcan_ingest.py    ← Phase 3 (REST API)
  boc_ingest.py        ← Phase 3 (Valet API)
  ons_ingest.py        ← Phase 3 (REST API)
  boe_ingest.py        ← Phase 3 (CSV downloads)
  eurostat_ingest.py   ← Phase 3 (SDMX via pandasdmx)
  ecb_ingest.py        ← Phase 3 (SDMX via pandasdmx)
  estat_ingest.py      ← Phase 3 (Japan e-Stat API)
  boj_ingest.py        ← Phase 3 (BOJ API)
  statsnz_ingest.py    ← Phase 3 (SDMX API)
  rbnz_ingest.py       ← Phase 3 (Excel downloads)
  bfs_ingest.py        ← Phase 3 (PXWeb API)
  snb_ingest.py        ← Phase 3 (SDMX API)
  oecd_ingest.py       ← Phase 5 (SDMX via pandasdmx — fallback)
```

### Shared Infrastructure
Several APIs share SDMX protocol. A shared SDMX helper would reduce duplication:
```python
# pipeline/ingest/sdmx_helper.py
import pandasdmx as sdmx

PROVIDERS = {
    'abs': 'ABS',
    'ecb': 'ECB',
    'eurostat': 'ESTAT',
    'oecd': 'OECD',
}

def fetch_sdmx(provider: str, dataflow: str, key: str, start: str) -> pd.DataFrame:
    """Generic SDMX fetcher for ABS, ECB, Eurostat, OECD."""
    client = sdmx.Client(PROVIDERS[provider])
    data = client.data(dataflow, key=key, params={'startPeriod': start})
    df = sdmx.to_pandas(data)
    return df
```

### series_definitions.json Changes
- Add country prefix convention: `US_`, `AUS_`, `CA_`, `UK_`, `EA_`, `JP_`, `NZ_`, `CH_`
- Add new `source` values: `statcan`, `boc`, `ons`, `boe`, `eurostat`, `ecb`, `estat`, `boj`, `statsnz`, `rbnz`, `bfs`, `snb`
- Group by country within each asset class, or add a `country` field
- Estimated ~400 total series definitions when fully expanded

### Processed Parquet Structure
Current structure (daily/monthly/quarterly.parquet) scales fine to ~400 series. At 50 years monthly data across 400 series, that's still under 50MB compressed Parquet.

---

## Implementation Timeline (Estimated)

| Phase | Scope | Effort | Dependencies |
|-------|-------|--------|-------------|
| **1** | FRED (US) — ~80 series | 1 day | API key (have it) |
| **2** | Australia (ABS + RBA) — ~22 series | 2 days | Phase 1 complete |
| **3A** | Canada (StatCan + BoC) — ~18 series | 2-3 days | Phase 1 |
| **3B** | UK (ONS + BoE) — ~18 series | 2-3 days | Phase 1 |
| **3C** | Euro Area (Eurostat + ECB) — ~20 series | 2-3 days | Phase 1 |
| **3D** | Japan (e-Stat + BOJ) — ~18 series | 3-4 days | e-Stat API key |
| **3E** | New Zealand (Stats NZ + RBNZ) — ~14 series | 2 days | Stats NZ API key |
| **3F** | Switzerland (BFS + SNB + KOF) — ~14 series | 2-3 days | Phase 1 |
| **4** | Commodities + Derived — ~30 series | 1 day | Phases 1-3 |
| **5** | OECD fallback + gap filling | 1-2 days | As needed |
| | **Total** | **~18-24 working days** | |

### Recommended Execution Order
1. Phase 1 (FRED) — establishes the template and proves the pipeline
2. Phase 2 (Australia) — home market, existing stubs
3. Phase 3C (Euro Area) — Eurostat + ECB use SDMX, builds the shared helper
4. Phase 3B (UK) — well-documented APIs
5. Phase 3A (Canada) — good APIs, no keys needed
6. Phase 3F (Switzerland) — SNB uses SDMX too
7. Phase 3D (Japan) — needs separate API key, documentation challenges
8. Phase 3E (New Zealand) — lower priority (quarterly data limits usefulness)
9. Phase 4 (Commodities + Derived) — builds on everything above
10. Phase 5 (OECD fallback) — fill gaps as discovered

---

## FRED-M Factor Categories & Cross-Country Signal Mapping

The FRED-M factor decomposition (McCracken & Ng) organizes ~130 series into 8 groups that each load onto latent factors. Here's how each country maps:

| FRED-M Group | Factor Signal | US | AU | CA | UK | EU | JP | NZ | CH |
|---|---|---|---|---|---|---|---|---|---|
| Output & Income | Real activity | Full | Partial (no IP) | Full | Full | Full | Full | GDP only | Partial |
| Labor Market | Employment cycle | Full | Full | Full | Full | Full | Full | Quarterly | Full |
| Housing | Credit/housing cycle | Full | Partial | Partial | Full | Quarterly | Full | Limited | Limited |
| Consumption & Orders | Demand | Full | Retail only | Partial | Full | Full | Full | Quarterly | Partial |
| Money & Credit | Monetary conditions | Full | Limited | Full | Full | Full | Full | Limited | Full |
| Interest Rates | Term structure | Full | Full | Full | Full | Full | Full | Full | Full |
| Prices | Inflation | Full | Quarterly CPI | Full | Full | Full | Full | Quarterly | Full |
| Exchange Rates | External | Full | Full | Full | Full | Full | Full | Full | Full |

### Key Limitations by Country
- **Australia**: No industrial production index; CPI is quarterly only; consumer/business confidence surveys not API-accessible
- **New Zealand**: Most macro data quarterly; smallest economy in set; limited history
- **Japan**: Language barriers in documentation; e-Stat registration required; Tankan is quarterly
- **Switzerland**: Smaller economy; PMI from procure.ch has no API; some BFS data German-only
- **All countries**: PMI data (S&P Global) is subscription-only for full history; only headline available free

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| yfinance rate limiting/breakage | Loss of equity + daily commodity data | Diversify: use FRED for commodities, consider paid data sources for equities |
| API deprecation (OECD.Stat already happened) | Broken ingestors | Build with standard protocols (SDMX); monitor API health |
| SDMX complexity | Slower development for ABS/ECB/Eurostat | Build shared sdmx_helper.py; invest time upfront |
| Series ID changes | Silent data failures | Validate series exist on each run; alert on missing |
| Quarterly vs monthly mismatch | Can't use quarterly series in monthly models | Store at native frequency; align in processed/ step using forward-fill |
| PMI/confidence data not API-accessible | Missing key leading indicators | Accept gap for now; consider Trading Economics subscription later |
| RBA CSV format changes | rba_ingest.py breaks | Pin expected column names; validate on each download |

---

## Python Dependencies to Install

```
# Core
fredapi          # FRED API client
pandasdmx        # SDMX for ABS, ECB, Eurostat, OECD
yfinance         # Yahoo Finance (equities, FX, commodities)
openpyxl         # Excel parsing (RBNZ, RBA historical)
pyarrow          # Parquet read/write
pandas           # DataFrame operations

# Country-specific (optional)
stats_can        # Statistics Canada WDS wrapper
pyvalet          # Bank of Canada Valet API wrapper
bojpy            # Bank of Japan API wrapper

# Utilities
requests         # HTTP downloads (RBA CSVs, BoE CSVs)
```

---

## Next Steps (Immediate)

1. **Register for API keys**: Japan e-Stat, NZ Stats (both free, 5 min each)
2. **Implement fred_ingest.py**: Get the FRED pipeline working end-to-end
3. **Add the ~70 FRED-M series** to series_definitions.json
4. **Run first full FRED download** and validate output in store/raw/fred/
5. **Verify processed/monthly.parquet** generates correctly with all FRED series
6. Then proceed to Phase 2 (Australia)
