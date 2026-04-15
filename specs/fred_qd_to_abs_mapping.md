# FRED-QD → ABS Mapping
## Australian equivalents of the McCracken-Ng quarterly macro database

**FRED-QD** is the McCracken-Ng (2020) quarterly macroeconomic database for the US — 248 series across 14 thematic categories, all available via the FRED API. Source: https://research.stlouisfed.org/econ/mccracken/fred-databases/

This document maps every FRED-QD category to the equivalent Australian Bureau of Statistics (ABS) and Reserve Bank of Australia (RBA) series, with the dataflow ID or table reference needed to retrieve them.

**Status legend:**
- ✓ Direct equivalent (same concept, comparable measurement)
- ≈ Close proxy (same economic concept, different methodology or coverage)
- △ Partial — only sub-component or different frequency available
- ✗ No equivalent published

**Source legend:**
- `ABS,XXX` — ABS SDMX dataflow ID (use with `abs_ingest.fetch()`)
- `RBA-Fx` — RBA statistical table (use with `rba_ingest.fetch_series()`)
- `FRED:XXX` — series available on FRED but not ABS

---

## GROUP 1 — NIPA (National Income & Product Accounts)

FRED-QD: ~25 series. ABS counterpart: **Australian National Accounts (5206.0)**, dataflow `ABS,ANA_AGG`. Quarterly. Released ~9 weeks after quarter end.

| FRED-QD code | Description | AUS source | Match |
|---|---|---|---|
| GDPC1 | Real GDP, chained | ANA_AGG: GDP CVM | ✓ |
| GDP | Nominal GDP | ANA_AGG: GDP current prices | ✓ |
| GDPCTPI | GDP deflator | ANA_AGG: GDP IPD | ✓ |
| PCECC96 | Real personal consumption | ANA_AGG: HFCE CVM | ✓ |
| PCDGx | Durable goods consumption | ANA_AGG: HFCE durables | ✓ |
| PCNDx | Nondurable goods consumption | ANA_AGG: HFCE non-durables | ✓ |
| PCESVx | Services consumption | ANA_AGG: HFCE services | ✓ |
| GPDIC1 | Real gross private investment | ANA_AGG: GFCF private | ✓ |
| FPIx | Fixed private investment | ANA_AGG: Private GFCF | ✓ |
| Y033RC1Q027SBEA | Equipment investment | ANA_AGG: Machinery & equipment | ✓ |
| PNFIx | Non-residential fixed investment | ANA_AGG: Non-dwelling construction | ≈ |
| PRFIx | Residential investment | ANA_AGG: Dwellings | ✓ |
| GCEC1 | Real govt consumption + investment | ANA_AGG: GFCE + Public GFCF | ✓ |
| EXPGSC1 | Real exports | ANA_AGG: Exports CVM | ✓ |
| IMPGSC1 | Real imports | ANA_AGG: Imports CVM | ✓ |
| NETEXC | Net exports | ANA_AGG: Net exports | ✓ |
| GDPDEF | GDP deflator | ANA_AGG: GDP IPD | ✓ |
| DPIC96 | Real disposable income | ANA_AGG: Real net disposable income | ✓ |
| OUTNFB | Non-farm business output | ABS Industry Aggregates 5206.0 Tab 6 | ≈ |
| HOANBS | Hours worked, non-farm | ABS LF: Aggregate hours worked | ≈ |

**Coverage:** ~95% of NIPA group has direct AUS equivalents in ANA_AGG dataflow. The biggest gap is the consumption breakdown — ABS publishes durables/non-durables/services but with different SA conventions than BEA.

**ABS dataflow:** `ABS,ANA_AGG,1.1.0` (versioned). Key dimensions: MEASURE (CVM=chained volume, CP=current prices, IPD=implicit price deflator), TSEST (10=original, 20=SA, 30=trend), FREQUENCY=Q.

---

## GROUP 2 — INDUSTRIAL PRODUCTION

FRED-QD: ~20 series (INDPRO + sub-sectors + capacity utilization).

**AUSTRALIA HAS NO MONTHLY INDUSTRIAL PRODUCTION INDEX.** The ABS discontinued the Index of Industrial Production in 1979. The closest substitutes are:

| FRED-QD concept | AUS source | Match |
|---|---|---|
| INDPRO (Total IP) | RBA Chart Pack series; ANA_AGG GVA mining + manufacturing (quarterly) | △ |
| IPFINAL (Final products IP) | None | ✗ |
| IPCONGD (Consumer goods IP) | None | ✗ |
| IPMAT (Materials IP) | RBA Index of Commodity Prices (different concept) | ≈ |
| IPDMAT (Durable materials) | None | ✗ |
| IPNMAT (Nondurable materials) | None | ✗ |
| IPMANSICS (Manufacturing IP) | ABS Manufacturing GVA from ANA_AGG (quarterly) | △ |
| IPB51110SQ (Mining IP) | ABS Mining GVA from ANA_AGG (quarterly) | △ |
| CUMFNS (Capacity utilization) | NAB Business Survey: Capacity utilization (private) | ≈ |

**Bottom line:** Phase 2 should include the quarterly GVA-by-industry breakdown from ANA_AGG as the IP proxy. NAB capacity utilization is the only practitioner-available capacity measure but it's a survey diffusion index, not comparable to FRB CUMFNS.

**ABS dataflow:** `ABS,ANA_AGG,1.1.0` with INDUSTRY dimension filtered to mining (B) and manufacturing (C).

---

## GROUP 3 — EMPLOYMENT & UNEMPLOYMENT

FRED-QD: ~30 series. ABS counterpart: **Labour Force, Australia (6202.0)**, dataflow `ABS,LF`. Monthly.

| FRED-QD code | Description | ABS LF source | Match |
|---|---|---|---|
| UNRATE | Unemployment rate | LF: Unemployment rate, persons, SA | ✓ |
| UNRATESTx | Unemployment rate, short-term | LF: Median weeks unemployed | ≈ |
| UNRATELTx | Unemployment rate, long-term (>27wk) | LF: Long-term unemployed (52+ wk) | ≈ |
| UEMPMEAN | Mean duration of unemployment | LF: Mean duration | ✓ |
| UEMPLT5 | Unemployed <5 weeks | LF: Duration breakdown | ✓ |
| UEMP5TO14 | Unemployed 5-14 weeks | LF: Duration breakdown | ✓ |
| UEMP15OV | Unemployed 15+ weeks | LF: Duration breakdown | ✓ |
| UEMP15T26 | Unemployed 15-26 weeks | LF: Duration breakdown | ✓ |
| UEMP27OV | Unemployed 27+ weeks | LF: Duration breakdown | ✓ |
| LNS14000012 | Unemployment rate, 16-19 yrs | LF: Youth unemployment 15-24 | ≈ |
| LNS14000025 | Unemployment rate, 20+ male | LF: By sex/age | ✓ |
| LNS14000026 | Unemployment rate, 20+ female | LF: By sex/age | ✓ |
| PAYEMS | Total nonfarm payrolls | LF: Employed total OR Wage Price Index headcount | △ |
| USPRIV | Total private employment | LF: Employed by sector (private/public split via separate cube) | ≈ |
| MANEMP | Manufacturing employment | LF: Employed by industry (C) | ✓ |
| SRVPRD | Service-providing employment | LF: Employed by industry (services) | ✓ |
| USCONS | Construction employment | LF: Employed by industry (E) | ✓ |
| USEHS | Education + health employment | LF: Employed by industry (P+Q) | ✓ |
| USFIRE | Financial activities employment | LF: Employed by industry (K) | ✓ |
| USINFO | Information employment | LF: Employed by industry (J) | ✓ |
| USPBS | Professional & business services emp | LF: Employed by industry (M+N) | ✓ |
| USMINE | Mining + logging employment | LF: Employed by industry (B) | ✓ |
| USTRADE | Wholesale + retail trade employment | LF: Employed by industry (F+G) | ✓ |
| USWTRADE | Wholesale trade employment | LF: Employed by industry (F) | ✓ |
| USTPU | Transport + utilities employment | LF: Employed by industry (D+I) | ✓ |
| USGOVT | Government employment | LF: Employed by sector (public) | ✓ |
| CES0600000007 | Avg weekly hours, goods producers | LF: Aggregate hours by industry | ≈ |
| AWHMAN | Avg weekly hours manufacturing | LF: Hours by manufacturing | ≈ |
| AWOTMAN | Avg weekly overtime hours mfg | None directly | ✗ |
| HOABS | Hours worked, business sector | LF: Aggregate monthly hours worked | ✓ |
| CIVPART | Labour force participation rate | LF: Participation rate | ✓ |
| EMRATIO | Employment-population ratio | LF: Employment-to-population ratio | ✓ |
| CLAIMSx | Initial unemployment claims | None (no weekly admin claims series) | ✗ |
| ICSA | Initial claims SA | None | ✗ |

**Coverage:** ~85% of FRED-QD employment series have direct ABS LF equivalents. Two genuine gaps: (1) no weekly initial unemployment claims (Australia uses fortnightly Centrelink data which isn't published as a high-frequency series), and (2) overtime hours not broken out.

**ABS dataflow:** `ABS,LF` (also `ABS,LF_Q` for quarterly aggregates) and `ABS,LM1` (labour mobility). Key dimensions: MEASURE (employed/unemployed/participation), SEX_ABS (3=persons, 1=male, 2=female), AGE (multiple), STATUS, FREQ.

---

## GROUP 4 — HOUSING

FRED-QD: ~10 series. ABS counterparts split across **Building Approvals (8731.0)**, **Building Activity (8752.0)**, **Lending Indicators (5601.0)**.

| FRED-QD code | Description | AUS source | Match |
|---|---|---|---|
| HOUST | Housing starts, total | ABS Building Activity 8752.0: Dwellings commenced | ✓ |
| HOUST5F | Housing starts, 5+ unit | Building Activity: Other dwellings commenced | ✓ |
| HOUSTMW | Housing starts, midwest | Not regional (state-level only) | △ |
| HOUSTNE | Housing starts, northeast | Not regional | △ |
| HOUSTS | Housing starts, south | Not regional | △ |
| HOUSTW | Housing starts, west | State-level breakdown | ≈ |
| PERMIT | Building permits | ABS Building Approvals 8731.0: Dwelling units approved, total | ✓ |
| PERMITMW | Permits midwest | State-level only | △ |
| PERMITNE | Permits northeast | State-level only | △ |
| PERMITS | Permits south | State-level only | △ |
| PERMITW | Permits west | State-level only | △ |

**Coverage:** Excellent for national totals. Regional breakdown only by state, not by census region.

**ABS dataflows:**
- `ABS,BA` — Building Approvals (monthly, dwelling units approved)
- `ABS,BUILD_ACT` — Building Activity (quarterly, value of work done, commencements, completions)
- `ABS,LEND_FIN` — Lending Indicators (monthly, new housing loans by purpose)

**Bonus AUS series not in FRED-QD:**
- ABS Residential Property Price Indexes (6416.0) — quarterly capital city dwelling prices
- CoreLogic daily home value index (commercial, no API)
- ABS Total Value of Dwellings (6432.0)
- RBA Housing Credit growth (D2)

---

## GROUP 5 — INVENTORIES, ORDERS, SALES

FRED-QD: ~10 series.

| FRED-QD code | Description | AUS source | Match |
|---|---|---|---|
| AMDMNOx | New orders, durable goods | None (no monthly orders series) | ✗ |
| ANDENOx | New orders, capital goods | ABS 5625.0 Private New Capital Expenditure (quarterly) | ≈ |
| AMDMUOx | Unfilled orders, durable | None | ✗ |
| BUSINVx | Total business inventories | ABS 5676.0 Business Indicators: Inventories | ✓ |
| ISRATIOx | Inventory-to-sales ratio | ABS 5676.0: Inventories / Sales (computed) | ✓ |
| RSAFSx | Retail sales | ABS 8501.0 Retail Trade: Total turnover, SA | ✓ |
| RSXFSx | Retail sales ex food services | ABS 8501.0: ex Food retailing | ✓ |
| AMTMNOx | Total mfg new orders | ABS 5676.0: Sales of goods and services | ≈ |
| TOTBUSSMNSA | Mfg + trade sales | ABS 5676.0 Business Indicators | ≈ |
| MNFCTRSMSA | Mfg sales SA | ABS 5676.0: Mfg sales of goods | ✓ |

**Coverage:** Mid. The big gap is monthly new orders — Australia has no equivalent of the US Manufacturers' Shipments, Inventories, and Orders survey. The Private New Capital Expenditure survey is quarterly only.

**ABS dataflows:**
- `ABS,RT` — Retail Trade (monthly turnover by industry, by state)
- `ABS,RT_Q` — Retail Trade quarterly volume
- `ABS,BUS_IND` — Business Indicators (quarterly: sales, inventories, profits, wages)
- `ABS,CAPEX` — Private New Capital Expenditure (quarterly capex + 5-year expectations)

---

## GROUP 6 — PRICES

FRED-QD: ~20 series. ABS counterparts: **CPI (6401.0)**, **Monthly CPI Indicator (6484.0)**, **PPI (6427.0)**.

| FRED-QD code | Description | AUS source | Match |
|---|---|---|---|
| CPIAUCSL | CPI All Urban, all items | ABS,CPI: All groups, weighted average 8 capitals | ✓ |
| CPILFESL | Core CPI (ex food + energy) | ABS,CPI: Trimmed mean (RBA preferred core) | ≈ |
| CPIAPPSL | CPI apparel | ABS,CPI: Clothing & footwear | ✓ |
| CPITRNSL | CPI transportation | ABS,CPI: Transport | ✓ |
| CPIMEDSL | CPI medical care | ABS,CPI: Health | ✓ |
| CUSR0000SAC | CPI commodities | ABS,CPI: Goods | ✓ |
| CUSR0000SAS | CPI services | ABS,CPI: Services | ✓ |
| CPIULFSL | CPI ex food | ABS,CPI: All groups ex food and non-alcoholic bevs | ≈ |
| CUSR0000SA0L2 | CPI ex shelter | ABS,CPI: All groups ex housing | ≈ |
| CUSR0000SA0L5 | CPI ex medical | ABS,CPI: All groups ex health | ≈ |
| PCEPI | PCE price index | None (Australia uses CPI as headline) | ✗ |
| PCEPILFE | Core PCE | ABS,CPI: Trimmed mean is the analog | ≈ |
| GDPDEF | GDP deflator | ABS,ANA_AGG: GDP IPD | ✓ |
| WPSFD49207 | PPI final demand | ABS,PPI: Final demand stage | ✓ |
| WPSFD4111 | PPI final demand goods | ABS,PPI: Final demand goods | ✓ |
| WPSFD49502 | PPI final demand services | ABS,PPI: Final demand services | ✓ |
| WPSID61 | PPI intermediate demand | ABS,PPI: Intermediate stages | ✓ |
| WPSID62 | PPI raw materials | ABS,PPI: Preliminary stage | ≈ |
| OILPRICEx | Crude oil price (WTI) | RBA-I2: Crude oil USD or use FRED:DCOILWTICO | ✓ |
| PPICMM | Producer prices commodities | RBA-I2 Index of Commodity Prices | ✓ |

**Coverage:** Very high. Australia publishes both quarterly CPI (since 1948) and monthly CPI Indicator (since 2018). Trimmed mean CPI is the RBA's preferred core inflation measure and is a strong analog to US Core PCE.

**ABS dataflows:**
- `ABS,CPI` — Quarterly CPI (8 capital cities, 11 groups, sub-groups)
- `ABS,MONTHLY_CPI` — Monthly CPI Indicator (since 2018)
- `ABS,PPI` — Producer Price Indexes (Final, Intermediate, Preliminary stages)
- `ABS,IT_PRICE` — International Trade Price Indexes (export/import prices)

---

## GROUP 7 — EARNINGS & PRODUCTIVITY

FRED-QD: ~10 series. ABS counterparts: **Wage Price Index (6345.0)**, **Average Weekly Earnings (6302.0)**, **Estimates of Industry Multifactor Productivity (5260.0.55.002)**.

| FRED-QD code | Description | AUS source | Match |
|---|---|---|---|
| CES0600000008 | Avg hourly earnings, goods producers | ABS,AWE: Avg weekly ordinary time earnings | ≈ |
| CES2000000008 | Avg hourly earnings, construction | ABS,AWE by industry (E) | ≈ |
| CES3000000008 | Avg hourly earnings, mfg | ABS,AWE by industry (C) | ≈ |
| CES0500000003 | Avg hourly earnings, total private | ABS,AWE: All employees | ≈ |
| COMPRMS | Real compensation, mfg | ABS,WPI: Manufacturing | ≈ |
| RCPHBS | Real compensation per hour business | ABS Productivity series: Real labour costs | ≈ |
| OPHNFB | Output per hour, non-farm business | ABS Productivity: Multifactor productivity, market sector | ≈ |
| OPHMFG | Output per hour, mfg | ABS Productivity: Manufacturing | ≈ |
| ULCBS | Unit labour costs, business | ABS,ANA_AGG: Real unit labour costs | ✓ |
| ULCNFB | Unit labour costs, non-farm business | ABS,ANA_AGG: Non-farm ULC | ✓ |

**Coverage:** Conceptually equivalent but methodologically different. The US uses Average Hourly Earnings (BLS Establishment Survey); Australia uses the Wage Price Index (a Laspeyres index of fixed jobs, immune to compositional changes — actually superior). Productivity is published annually by ABS, not quarterly.

**ABS dataflows:**
- `ABS,WPI` — Wage Price Index (quarterly, by industry, by sector public/private)
- `ABS,AWE` — Average Weekly Earnings (semi-annual, by industry, by sex)
- `ABS,EARNINGS` — Employee earnings + hours
- ABS Multifactor Productivity is annual only — no SDMX dataflow as of 2024 last check

**RBA companion:** RBA tracks Wage Price Index quarterly in the Statement on Monetary Policy. RBA Discussion Papers regularly recompute productivity-adjusted unit labour costs.

---

## GROUP 8 — INTEREST RATES

FRED-QD: ~25 series. RBA counterparts: **F1, F1.1, F2, F2.1, F4, F5, F6** statistical tables. (Not ABS.)

| FRED-QD code | Description | RBA source | Match |
|---|---|---|---|
| FEDFUNDS | Effective federal funds rate | RBA-F1: Cash rate target | ✓ |
| TB3MS | 3-month Treasury bill | RBA-F1: Bank-accepted bills 90-day | ≈ |
| TB6MS | 6-month Treasury bill | RBA-F1: Bank-accepted bills 180-day | ≈ |
| GS1 | 1-year Treasury constant maturity | RBA-F2: 2-year Treasury bond yield is closest | ≈ |
| GS5 | 5-year Treasury | RBA-F2: 5-year Treasury bond yield | ✓ |
| GS10 | 10-year Treasury | RBA-F2: 10-year Treasury bond yield (FCMYGBAG10D) | ✓ |
| AAA | Moody's Aaa corporate yield | None (RBA publishes spread to bond, not absolute) | △ |
| BAA | Moody's Baa corporate yield | None | △ |
| AAAFFM | Aaa - Fed funds spread | None | △ |
| BAAFFM | Baa - Fed funds spread | RBA-F3: Corporate bond spreads (limited history) | ≈ |
| MORTGAGE30US | 30-yr fixed mortgage rate | RBA-F5: Standard variable rate (Australia is mostly variable rate) | ≈ |
| MORTG | Conventional mortgage rate | RBA-F6: New housing loans rate | ≈ |
| TB3SMFFM | 3M T-bill - Fed funds spread | Computed from F1 + F2 | ✓ |
| T1YFFM | 1Y - Fed funds spread | Computed | ✓ |
| T5YFFM | 5Y - Fed funds spread | Computed | ✓ |
| T10YFFM | 10Y - Fed funds spread | Computed | ✓ |
| GS10TB3Mx | 10Y - 3M term spread | Computed | ✓ |
| BAA10YM | Baa - 10Y spread | None | ✗ |

**Coverage:** Very high for sovereign yields and policy rates. Gap: **no Australian corporate bond yield index with long history**. RBA publishes corporate bond spreads in F3 but only since ~2005 and at limited maturities. KangaNews and Bloomberg AusBond Composite have proprietary data.

**RBA tables:**
- `f1` — Interest Rates and Yields: Money Market (cash rate, BBSW, etc.)
- `f1.1` — Money market rates, monthly history
- `f2` — Capital Market Yields — Government Bonds (2Y, 3Y, 5Y, 10Y CGB)
- `f2.1` — Capital market yields, monthly history
- `f3` — Capital market yields and spreads — corporate bonds
- `f4` — Lending rates by purpose (housing, personal, business)
- `f5` — Indicator lending rates
- `f6` — Housing lending rates

---

## GROUP 9 — MONEY & CREDIT

FRED-QD: ~15 series. RBA counterparts: **D1, D2, D3** statistical tables.

| FRED-QD code | Description | RBA source | Match |
|---|---|---|---|
| M1REAL | Real M1 | None directly (Australia stopped M1 publication in 2022) | △ |
| M2REAL | Real M2 | RBA-D3: M3 is the closest analog | ≈ |
| BUSLOANS | Commercial & industrial loans | RBA-D2: Business credit | ✓ |
| CONSUMER | Consumer loans | RBA-D2: Personal credit | ✓ |
| NONREVSL | Nonrevolving consumer credit | RBA-D2: Personal fixed loans | ≈ |
| REALLN | Real estate loans, all | RBA-D2: Housing credit total | ✓ |
| TOTALSL | Total consumer credit | RBA-D2: Personal + housing | ≈ |
| INVEST | Securities held by commercial banks | RBA-B2: Bank balance sheet items | ≈ |
| TOTRESNS | Total reserves (Fed) | RBA-A1: Liabilities & assets (ES balances) | ≈ |
| NONBORRES | Non-borrowed reserves | RBA-A1 | ≈ |
| DTCOLNVHFNM | Vehicle loans | None broken out | ✗ |
| DTCTHFNM | Total consumer loans | RBA-D2: Personal credit | ✓ |
| BOGMBASE | Monetary base | RBA-D3: Money base | ✓ |

**Coverage:** Mid. RBA publishes credit aggregates monthly in D2 (housing, personal, business, total) which are the workhorse Australian credit series. Money base / monetary aggregates are published in D3 but with less detail than US.

**RBA tables:**
- `d1` — Growth in selected financial aggregates
- `d2` — Lending and credit aggregates (housing, personal, business, total)
- `d3` — Monetary aggregates (M1, M3, broad money, money base)
- `b1` — Reserve Bank of Australia balance sheet
- `b2` — Banks balance sheet (assets, liabilities)

**ABS doesn't publish credit data — this is RBA territory.**

---

## GROUP 10 — HOUSEHOLD BALANCE SHEETS

FRED-QD: ~10 series. ABS counterpart: **Australian National Accounts Financial Accounts (5232.0)** + **Household Wealth and Wealth Distribution**.

| FRED-QD code | Description | AUS source | Match |
|---|---|---|---|
| TLBSHNOx | Household total liabilities | ABS,FA: Household sector liabilities | ✓ |
| TFAABSHNO | Household financial assets | ABS,FA: Household financial assets | ✓ |
| TNWBSHNO | Household net worth | ABS,FA: Household net worth | ✓ |
| TARESA | Household real estate assets | ABS,FA: Household land + dwellings | ✓ |
| HMLISHNO | Household home mortgage liabilities | ABS,FA: Household housing loans | ✓ |
| TDSP | Household debt service payments to DPI | RBA Chart Pack: Household debt servicing ratio | ≈ |
| HNOREMQ027S | Household real estate at market value | ABS,FA: Land and dwellings | ✓ |
| HHMSDODNS | Household + nonprofit total liabilities | ABS,FA: Household total | ≈ |

**Coverage:** Strong. ABS Financial Accounts (5232.0) publishes quarterly sectoral balance sheets matching the FRB Z.1 Flow of Funds structure.

**ABS dataflow:** `ABS,FA` (Financial Accounts). Key dimension: SECTOR (households vs non-financial corporations vs government), INSTRUMENT (loans, deposits, equity, etc.), STOCKS_FLOWS.

---

## GROUP 11 — EXCHANGE RATES

FRED-QD: ~5 series. RBA counterpart: **F11** (Exchange Rates).

| FRED-QD code | Description | RBA source | Match |
|---|---|---|---|
| EXCAUSx | Australia/US FX | RBA-F11: FXRUSD (AUD per USD) | ✓ inverted |
| EXJPUSx | Japan/US FX | RBA-F11: FXRJPY (cross via FXRUSD) | ≈ |
| EXSZUSx | Switzerland/US FX | RBA-F11: FXRCHF | ≈ |
| EXUSUKx | US/UK FX | RBA-F11: FXRGBP | ≈ |
| TWEXAFEGSMTHx | Trade-weighted USD | None for USD; for AUD: RBA-F11 FXRTWI | ≈ |

**Coverage:** RBA F11 publishes daily AUD bilateral rates against USD, EUR, GBP, JPY, NZD, CNY plus the trade-weighted index. The RBA TWI is the AUD analog of the Fed's broad dollar index.

**RBA tables:**
- `f11` — Exchange Rates (daily, post-1983 floating)
- `f11.1` — Exchange Rates monthly (longer history)

---

## GROUP 12 — OTHER (Sentiment & Surveys)

FRED-QD: ~5 series. AUS counterparts: **NAB Business Survey** (private, monthly) and **Westpac-Melbourne Institute Consumer Sentiment** (private, monthly).

| FRED-QD code | Description | AUS source | Match |
|---|---|---|---|
| UMCSENTx | U Mich consumer sentiment | Westpac-MI Consumer Sentiment Index | ≈ |
| BUSINVx | (covered in group 5) | — | — |
| ISMnoise | ISM manufacturing | NAB Business Conditions (services + non-mining) | ≈ |
| ISMNO | ISM new orders | NAB: Forward orders | ≈ |
| ISMSUP | ISM supplier deliveries | NAB: Stocks subindex | ≈ |

**Coverage:** Conceptually equivalent but **NAB and Westpac surveys do not publish via API** — they release PDF reports monthly. The data must be scraped or licensed. Trading Economics aggregates these.

**No ABS dataflow** for sentiment data.

---

## GROUP 13 — STOCK MARKETS

FRED-QD: ~5 series. AUS counterpart: ASX (via yfinance, not ABS).

| FRED-QD code | Description | AUS source | Match |
|---|---|---|---|
| S&P 500 | S&P 500 index level | ASX 200 (yfinance ^AXJO) | ≈ |
| S&P: indust | S&P industrial | ASX 200 sub-indices via yfinance | ≈ |
| S&P div yield | S&P dividend yield | ASX 200 div yield (S&P/ASX official) | ≈ |
| S&P PE | S&P P/E ratio | ASX 200 P/E (S&P/ASX official) | ≈ |
| VIXCLSx | CBOE VIX | ASX VIX (S&P/ASX 200 VIX, "A-VIX") | ✓ |

**Coverage:** All available via yfinance (already in your data-store) or Bloomberg. Not ABS territory.

---

## GROUP 14 — NON-HOUSEHOLD BALANCE SHEETS

FRED-QD: ~15 series. ABS counterpart: **ANA Financial Accounts (5232.0)** sectors other than household.

| FRED-QD code | Description | AUS source | Match |
|---|---|---|---|
| NWPIx | Net worth, non-financial corporate | ABS,FA: Non-financial corp net worth | ✓ |
| TABSHNNCB | Total assets, non-financial corp business | ABS,FA: Non-fin corp assets | ✓ |
| TLBSNNCB | Total liabilities non-fin corp | ABS,FA: Non-fin corp liabilities | ✓ |
| FBCELLQ027S | Bank loans non-financial business | ABS,FA: Loans by sector | ✓ |
| FOFCBLSAQ027S | Foreign-owned commercial banks loans | ABS,FA: Foreign sector | ✓ |
| FBSCNQ027S | Securities and credit market debt | ABS,FA: Debt securities | ✓ |

**Coverage:** Strong via ABS Financial Accounts dataflow.

---

## SUMMARY MATRIX

| Group | FRED-QD count | AUS coverage | Primary source |
|---|---|---|---|
| 1. NIPA | ~25 | 95% | `ABS,ANA_AGG` |
| 2. Industrial Production | ~20 | 30% (no monthly IP) | `ABS,ANA_AGG` (qtrly GVA only) |
| 3. Employment & Unemployment | ~30 | 85% (no weekly claims) | `ABS,LF` |
| 4. Housing | ~10 | 80% (national totals only) | `ABS,BA` + `ABS,BUILD_ACT` |
| 5. Inventories, Orders, Sales | ~10 | 60% (no monthly orders) | `ABS,RT` + `ABS,BUS_IND` |
| 6. Prices | ~20 | 95% | `ABS,CPI` + `ABS,PPI` |
| 7. Earnings & Productivity | ~10 | 70% (different methodology) | `ABS,WPI` + `ABS,AWE` |
| 8. Interest Rates | ~25 | 80% (no AUS corp yield) | RBA `f1` + `f2` + `f3` |
| 9. Money & Credit | ~15 | 75% | RBA `d1` + `d2` + `d3` |
| 10. Household Balance Sheets | ~10 | 85% | `ABS,FA` |
| 11. Exchange Rates | ~5 | 100% (different base currency) | RBA `f11` |
| 12. Sentiment Surveys | ~5 | 30% (no public APIs) | NAB + Westpac (manual) |
| 13. Stock Markets | ~5 | 100% (via yfinance) | yfinance `^AXJO` etc |
| 14. Non-Household Balance Sheets | ~15 | 90% | `ABS,FA` |

**Overall: ~75% of FRED-QD has a direct or close AUS equivalent.**

The biggest structural gaps are:
1. **No monthly Industrial Production** — FRED has 20 IP series, ABS has zero. Australia stopped publishing IIP in 1979. Quarterly GVA-by-industry from ANA is the only substitute.
2. **No weekly initial unemployment claims** — Centrelink data isn't released as a high-frequency time series.
3. **No monthly orders/shipments** — Capex is quarterly only.
4. **No public sentiment APIs** — NAB and Westpac surveys must be scraped.
5. **No long-history Australian corporate bond yield index**.

---

## RECOMMENDED PHASE 2A: AUS FRED-QD EQUIVALENT

Build a curated Australian quarterly database that mirrors FRED-QD as closely as possible. Target ~120 series (vs FRED-QD's 248 — half because of the structural gaps above).

### ABS dataflows to ingest

```python
# In data-store/pipeline/ingest/abs_ingest.py
ABS_FRED_QD_EQUIVALENTS = [
    # NIPA — quarterly national accounts
    ("ABS,ANA_AGG",      "AUS_GDP",        "GDP CVM, SA"),
    ("ABS,ANA_AGG",      "AUS_GDP_NOM",    "GDP current prices, SA"),
    ("ABS,ANA_AGG",      "AUS_GDP_DEFL",   "GDP implicit price deflator"),
    ("ABS,ANA_AGG",      "AUS_HFCE",       "Household consumption, real, SA"),
    ("ABS,ANA_AGG",      "AUS_GFCF",       "Gross fixed capital formation, real"),
    ("ABS,ANA_AGG",      "AUS_GFCE",       "Government consumption, real"),
    ("ABS,ANA_AGG",      "AUS_EXPORTS",    "Exports of goods and services, real"),
    ("ABS,ANA_AGG",      "AUS_IMPORTS",    "Imports of goods and services, real"),
    ("ABS,ANA_AGG",      "AUS_NETEXP",     "Net exports, real"),
    ("ABS,ANA_AGG",      "AUS_DPI",        "Real net disposable income per capita"),

    # Labour Force — monthly
    ("ABS,LF",           "AUS_UNEMP",      "Unemployment rate, persons, SA"),
    ("ABS,LF",           "AUS_EMP",        "Employed total, SA"),
    ("ABS,LF",           "AUS_PARTIC",     "Participation rate, persons, SA"),
    ("ABS,LF",           "AUS_HOURS",      "Aggregate monthly hours worked, SA"),
    ("ABS,LF",           "AUS_EMPPOP",     "Employment-to-population ratio, SA"),
    ("ABS,LF",           "AUS_UEMPLT5",    "Unemployed <5 weeks"),
    ("ABS,LF",           "AUS_UEMP15PLUS", "Unemployed 15+ weeks"),
    ("ABS,LF",           "AUS_UEMP_LT",    "Long-term unemployment 52+ weeks"),
    ("ABS,LF",           "AUS_YOUTH_UNEMP","Youth unemployment 15-24"),

    # CPI — quarterly + monthly indicator
    ("ABS,CPI",          "AUS_CPI",        "All groups CPI, weighted avg 8 capitals"),
    ("ABS,CPI",          "AUS_CPI_TRIM",   "Trimmed mean CPI (RBA core)"),
    ("ABS,CPI",          "AUS_CPI_GOODS",  "Goods CPI"),
    ("ABS,CPI",          "AUS_CPI_SERV",   "Services CPI"),
    ("ABS,CPI",          "AUS_CPI_HOUSING","Housing group CPI"),
    ("ABS,CPI",          "AUS_CPI_TRANS",  "Transport group CPI"),
    ("ABS,CPI",          "AUS_CPI_HEALTH", "Health group CPI"),
    ("ABS,MONTHLY_CPI",  "AUS_CPI_MONTHLY","Monthly CPI Indicator"),

    # PPI — quarterly
    ("ABS,PPI",          "AUS_PPI_FINAL",  "PPI Final demand, SA"),
    ("ABS,PPI",          "AUS_PPI_INTER",  "PPI Intermediate demand"),
    ("ABS,PPI",          "AUS_PPI_PRELIM", "PPI Preliminary stage"),

    # WPI — quarterly wages
    ("ABS,WPI",          "AUS_WPI",        "Wage Price Index, all sectors"),
    ("ABS,WPI",          "AUS_WPI_PRIVATE","WPI private sector"),
    ("ABS,WPI",          "AUS_WPI_PUBLIC", "WPI public sector"),

    # Retail trade — monthly
    ("ABS,RT",           "AUS_RETAIL",     "Retail turnover, SA, total"),
    ("ABS,RT",           "AUS_RETAIL_FOOD","Retail turnover, food retailing"),
    ("ABS,RT",           "AUS_RETAIL_HHGD","Retail turnover, household goods"),
    ("ABS,RT",           "AUS_RETAIL_DEPT","Retail turnover, dept stores"),

    # Building & housing
    ("ABS,BA",           "AUS_PERMITS",    "Dwelling units approved, total, SA"),
    ("ABS,BA",           "AUS_PERMITS_PRIV","Private sector dwellings approved"),
    ("ABS,BUILD_ACT",    "AUS_HOUSE_STARTS","Dwellings commenced, total"),
    ("ABS,BUILD_ACT",    "AUS_HOUSE_DONE", "Value of work done, residential"),
    ("ABS,RPPI",         "AUS_HOUSE_PRICE","Residential property price index, weighted avg"),

    # Lending — monthly
    ("ABS,LEND_FIN",     "AUS_LOANS_NEW",  "New housing loans, total, SA"),
    ("ABS,LEND_FIN",     "AUS_LOANS_FHB",  "First home buyer loans"),
    ("ABS,LEND_FIN",     "AUS_LOANS_INV",  "Investor housing loans"),

    # Business indicators — quarterly
    ("ABS,BUS_IND",      "AUS_BUS_SALES",  "Sales of goods and services, SA"),
    ("ABS,BUS_IND",      "AUS_BUS_INV",    "Inventories, SA"),
    ("ABS,BUS_IND",      "AUS_BUS_PROFIT", "Company gross operating profits, SA"),
    ("ABS,BUS_IND",      "AUS_BUS_WAGES",  "Wages and salaries, SA"),

    # Capital expenditure — quarterly
    ("ABS,CAPEX",        "AUS_CAPEX_TOT",  "Total private new capital expenditure, SA"),
    ("ABS,CAPEX",        "AUS_CAPEX_BLDG", "Buildings & structures capex"),
    ("ABS,CAPEX",        "AUS_CAPEX_EQUIP","Equipment, plant & machinery capex"),
    ("ABS,CAPEX",        "AUS_CAPEX_EXP",  "Expected capex, year ahead estimate"),

    # International trade — monthly
    ("ABS,MERCH_TRADE",  "AUS_EXPORTS_M",  "Goods exports, total, SA"),
    ("ABS,MERCH_TRADE",  "AUS_IMPORTS_M",  "Goods imports, total, SA"),
    ("ABS,MERCH_TRADE",  "AUS_TRADE_BAL",  "Goods trade balance, SA"),
    ("ABS,IT_PRICE",     "AUS_EXPORT_PX",  "Export price index"),
    ("ABS,IT_PRICE",     "AUS_IMPORT_PX",  "Import price index"),
    ("ABS,IT_PRICE",     "AUS_TOT",        "Terms of trade index"),

    # Balance of Payments — quarterly
    ("ABS,BOP",          "AUS_CAB",        "Current account balance, SA"),
    ("ABS,BOP",          "AUS_GDS_BAL",    "Goods balance"),
    ("ABS,BOP",          "AUS_SVCS_BAL",   "Services balance"),

    # Financial Accounts — quarterly balance sheets
    ("ABS,FA",           "AUS_HH_NW",      "Household net worth"),
    ("ABS,FA",           "AUS_HH_LIAB",    "Household liabilities"),
    ("ABS,FA",           "AUS_HH_LAND",    "Household land + dwellings"),
    ("ABS,FA",           "AUS_HH_FINASS",  "Household financial assets"),
    ("ABS,FA",           "AUS_NFC_NW",     "Non-financial corp net worth"),
    ("ABS,FA",           "AUS_NFC_LIAB",   "Non-financial corp liabilities"),
]
```

### RBA tables to ingest

```python
RBA_FRED_QD_EQUIVALENTS = [
    # Interest rates
    ("f1",  "FIRMMCRTD",   "AUS_CASHRATE",  "RBA cash rate target"),
    ("f1",  "FIRMMBAB30",  "AUS_BBSW30",    "30-day BBSW"),
    ("f1",  "FIRMMBAB90",  "AUS_BBSW90",    "90-day BBSW"),
    ("f1",  "FIRMMBAB180", "AUS_BBSW180",   "180-day BBSW"),
    ("f2",  "FCMYGBAG2D",  "AGB2Y",         "AUS 2yr Gov bond yield"),
    ("f2",  "FCMYGBAG3D",  "AGB3Y",         "AUS 3yr Gov bond yield"),
    ("f2",  "FCMYGBAG5D",  "AGB5Y",         "AUS 5yr Gov bond yield"),
    ("f2",  "FCMYGBAG10D", "AGB10Y",        "AUS 10yr Gov bond yield"),
    ("f3",  "FCMYBAGS3M",  "AUS_CORP_3M",   "Corporate bond yield 3-month"),
    ("f5",  "FILRHLBVS",   "AUS_MORTGAGE",  "Standard variable housing rate"),

    # Credit aggregates
    ("d2",  "DLFCAHFL",    "AUS_HOUSING_CR","Housing credit total"),
    ("d2",  "DLFCAPS",     "AUS_PERS_CR",   "Personal credit"),
    ("d2",  "DLFCABD",     "AUS_BUS_CR",    "Business credit"),
    ("d2",  "DLFCAT",      "AUS_TOTAL_CR",  "Total credit"),
    ("d3",  "DMABMM",      "AUS_M3",        "M3 money supply"),
    ("d3",  "DMABMM_BR",   "AUS_BROADMNY",  "Broad money"),

    # Exchange rates (daily)
    ("f11", "FXRUSD",      "AUDUSD",        "AUD/USD exchange rate"),
    ("f11", "FXRJPY",      "AUDJPY",        "AUD/JPY exchange rate"),
    ("f11", "FXREUR",      "AUDEUR",        "AUD/EUR exchange rate"),
    ("f11", "FXRGBP",      "AUDGBP",        "AUD/GBP exchange rate"),
    ("f11", "FXRCNY",      "AUDCNY",        "AUD/CNY exchange rate"),
    ("f11", "FXRNZD",      "AUDNZD",        "AUD/NZD exchange rate"),
    ("f11", "FXRTWI",      "AUD_TWI",       "AUD trade-weighted index"),

    # Commodities
    ("i2",  "GRCPBCSDR",   "AUS_COMM_SDR",  "Commodity price index, SDR"),
    ("i2",  "GRCPBCAUD",   "AUS_COMM_AUD",  "Commodity price index, AUD"),
    ("i2",  "GRCPBCNAUD",  "AUS_COMM_NRES", "Non-rural commodity price index"),
    ("i2",  "GRCPRCAUD",   "AUS_COMM_RUR",  "Rural commodity price index"),
    ("i2",  "GRCPBMAUD",   "AUS_COMM_BLK",  "Bulk commodity price index"),
]
```

That's ~80 ABS series + ~30 RBA series = **~110 Australian quarterly/monthly series** mapped to FRED-QD categories. Combined with the 27 FRED-M series already downloaded, the data-store would cover both economies side by side.

---

## NEXT STEPS

1. **Verify dataflow IDs** — the IDs above (`ABS,ANA_AGG`, `ABS,LF`, etc.) need to be verified against `https://data.api.abs.gov.au/rest/dataflow/ABS` once Phase 2 runs successfully and we can list the actual catalog.

2. **Map dimension keys** — each dataflow has a multi-dimensional structure. We need the SDMX dimension filters to pull a single time series rather than every cut. E.g. for CPI: `1.10001.10.50.Q` means (measure=index, region=8 capitals, group=all, weighting=normal, freq=quarterly). This requires running `read_api_datastructure()` per dataflow.

3. **Update update_aus.py** — replace the current 8-series shortlist with the full ~110-series catalog above, organised by FRED-QD group.

4. **Build aus_processed.parquet** — once raw data is in, build_processed.py needs new routing rules for monthly/quarterly Australian series.

5. **Cross-country regression-ready table** — final output: a wide DataFrame where columns are `{country}_{concept}` (e.g. `US_GDP`, `AUS_GDP`, `US_UNEMP`, `AUS_UNEMP`) so signal modules can directly compare or build cross-country signals.

---

**File location:** `data-store/specs/fred_qd_to_abs_mapping.md`
**Status:** Reference document — read by `update_aus.py` and `build_processed.py`
