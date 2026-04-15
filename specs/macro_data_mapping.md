# Cross-Country Macro Data Mapping
## Master file — FRED-MD/QD equivalents by country

**Purpose.** A single living document that maps every concept in the McCracken–Ng FRED-MD (134 monthly series) and FRED-QD (248 quarterly series) databases to its equivalent series in each country we cover. The goal is a fully harmonised cross-country macro panel for signal research.

**Scope.** US (benchmark) → Australia → Euro Area (Eurostat + ECB) → Germany → France → Italy → Spain → Netherlands → UK → Canada → Japan → Switzerland → New Zealand. Add countries as we expand.

**File location.** `data-store/specs/macro_data_mapping.md` — read by all `update_*.py` runners. Edit this file to extend coverage; the runners pick up changes on the next pass.

**Status legend.**
- ✓ Direct equivalent (same concept, comparable measurement)
- ≈ Close proxy (same concept, different methodology, coverage, or frequency)
- △ Partial — only sub-component or different aggregation available
- ✗ No equivalent published

**FRED-MD groups (8):**
1. Output and income
2. Labor market
3. Housing
4. Consumption, orders and inventories
5. Money and credit
6. Interest and exchange rates
7. Prices
8. Stock market

**FRED-QD adds 6 more (14 total):** earnings & productivity, household balance sheets, non-household balance sheets, sentiment surveys, NIPA breakdowns, and additional financial indicators. The QD-only categories are noted in the **Quarterly add-ons** sections below.

---

# 0. UNITED STATES (BENCHMARK)

This section is the reference. Every other country chapter maps back to these FRED codes.

## 0.1 FRED-MD groups (134 monthly series)

| Group | Series count | Representative FRED codes | Source |
|-------|-------------|---------------------------|--------|
| 1. Output & income | 17 | RPI, INDPRO, IPFINAL, IPCONGD, IPMAT, IPMANSICS, IPB51110SQ, CUMFNS, CMRMTSPLx | BEA, FRB |
| 2. Labor market | 32 | UNRATE, UEMPMEAN, PAYEMS, MANEMP, USCONS, USTRADE, USGOVT, CES0600000007, AWHMAN, AWOTMAN, CIVPART, EMRATIO, ICSA, CES3000000008 | BLS |
| 3. Housing | 10 | HOUST, HOUST5F, HOUSTMW, HOUSTNE, HOUSTS, HOUSTW, PERMIT (and four regional permit series) | Census |
| 4. Consumption, orders, inventories | 10 | RETAILx, AMDMNOx, ANDENOx, AMDMUOx, BUSINVx, ISRATIOx, AMTMNOx, NAPMxxx (PMIs) | Census, ISM |
| 5. Money & credit | 14 | M1SL, M2SL, BOGMBASE, TOTRESNS, NONBORRES, BUSLOANS, CONSUMER, NONREVSL, REALLN, CONSPI, MZMSL | FRB H.6 / H.8 |
| 6. Interest & exchange rates | 22 | FEDFUNDS, TB3MS, TB6MS, GS1, GS5, GS10, AAA, BAA, MORTG, T10YFFM, AAAFFM, BAAFFM, EXSZUSx, EXJPUSx, EXUSUKx, EXCAUSx, TWEXAFEGSMTHx | FRB H.15 / G.5 |
| 7. Prices | 21 | CPIAUCSL, CPILFESL, CPIAPPSL, CPITRNSL, CPIMEDSL, PCEPI, PCEPILFE, GDPDEF, WPSFD49207, WPSFD4111, WPSID61, WPSID62, OILPRICEx, PPICMM | BLS, BEA |
| 8. Stock market | 5 | S&P 500, S&P industrial, S&P div yield, S&P P/E, VIXCLSx | S&P, CBOE |

## 0.2 FRED-QD additional groups (114 more quarterly series)

| Group | Series count | Representative FRED codes |
|-------|-------------|---------------------------|
| 9. NIPA detail | ~25 | GDPC1, GDP, PCECC96, PCDGx, PCNDx, PCESVx, GPDIC1, FPIx, GCEC1, EXPGSC1, IMPGSC1, NETEXC, GDPDEF, DPIC96 |
| 10. Earnings & productivity | ~10 | COMPRMS, RCPHBS, OPHNFB, OPHMFG, ULCBS, ULCNFB, CES0500000003 |
| 11. Household balance sheets | ~10 | TLBSHNOx, TFAABSHNO, TNWBSHNO, TARESA, HMLISHNO, TDSP, HNOREMQ027S |
| 12. Non-household balance sheets | ~15 | NWPIx, TABSHNNCB, TLBSNNCB, FBCELLQ027S, FOFCBLSAQ027S, FBSCNQ027S |
| 13. Sentiment surveys | ~5 | UMCSENTx, ISMxx, NAPMxxx |
| 14. Additional financial | ~5 | BAA10YM, AAA10YM (corporate-Treasury spreads) |

**Total:** 134 monthly + ~114 quarterly = ~248 unique series.

---

# 1. AUSTRALIA

**National statistical agency.** Australian Bureau of Statistics (ABS) — `https://data.api.abs.gov.au/rest/data/{flow_ref}/{key}` (SDMX, no auth since Nov 2024).
**Central bank.** Reserve Bank of Australia (RBA) — `https://www.rba.gov.au/statistics/tables/csv/{table}-data.csv` (CSV, no auth).
**Status.** Phase 2 ingestor written, awaiting host run.

## 1.1 FRED-MD by group

### Group 1 — Output & Income

**Major gap.** Australia has no monthly Industrial Production index (the IIP was discontinued in 1979). The closest substitute is quarterly Gross Value Added by industry from ANA_AGG.

| FRED-MD | Concept | AUS source | Match |
|---|---|---|---|
| RPI | Real personal income | `ABS,ANA_AGG`: Real net disposable income (Q only) | △ |
| INDPRO | Industrial production total | `ABS,ANA_AGG`: GVA mining + mfg + utilities + construction (Q) | △ |
| IPFINAL | IP final products | None | ✗ |
| IPMANSICS | IP manufacturing | `ABS,ANA_AGG`: Manufacturing GVA (Q) | △ |
| IPB51110SQ | IP mining | `ABS,ANA_AGG`: Mining GVA (Q) | △ |
| CUMFNS | Capacity utilisation, mfg | NAB Business Survey: Capacity utilisation (no API) | ≈ |
| CMRMTSPLx | Mfg & trade real sales | `ABS,BUS_IND`: Sales of goods & services (Q) | ≈ |

### Group 2 — Labor Market

| FRED-MD | Concept | ABS source | Match |
|---|---|---|---|
| UNRATE | Unemployment rate | `ABS,LF`: Unemployment rate persons SA | ✓ |
| UEMPMEAN | Mean weeks unemployed | `ABS,LF`: Average duration of unemployment | ✓ |
| UEMPLT5 | Unemployed <5 weeks | `ABS,LF`: Duration breakdown | ✓ |
| UEMP5TO14 | Unemployed 5-14 weeks | `ABS,LF`: Duration breakdown | ✓ |
| UEMP15OV | Unemployed 15+ weeks | `ABS,LF`: Duration breakdown | ✓ |
| UEMP15T26 | Unemployed 15-26 weeks | `ABS,LF`: Duration breakdown | ✓ |
| UEMP27OV | Unemployed 27+ weeks | `ABS,LF`: Duration breakdown | ✓ |
| CLAIMSx | Initial claims | None — Centrelink data not published as time series | ✗ |
| PAYEMS | Total nonfarm payrolls | `ABS,LF`: Employed total (different methodology) | ≈ |
| USPRIV | Private employment | `ABS,LF`: by sector (private/public split) | ≈ |
| MANEMP | Manufacturing employment | `ABS,LF`: by industry C | ✓ |
| USCONS | Construction employment | `ABS,LF`: by industry E | ✓ |
| USTRADE | Wholesale + retail employment | `ABS,LF`: by industry F+G | ✓ |
| USGOVT | Government employment | `ABS,LF`: by sector (public) | ✓ |
| CES0600000007 | Avg weekly hours, goods producers | `ABS,LF`: Aggregate monthly hours by industry | ≈ |
| AWHMAN | Avg weekly hours mfg | `ABS,LF`: Hours by mfg industry | ≈ |
| AWOTMAN | Avg weekly overtime hours mfg | None | ✗ |
| CIVPART | Labour force participation | `ABS,LF`: Participation rate | ✓ |
| EMRATIO | Employment-population ratio | `ABS,LF`: Employment to population ratio | ✓ |

**Coverage: 80% — gaps are weekly claims and overtime hours.**

### Group 3 — Housing

| FRED-MD | Concept | AUS source | Match |
|---|---|---|---|
| HOUST | Housing starts total | `ABS,BUILD_ACT`: Dwellings commenced (Q) | ✓ |
| HOUST5F | Housing starts 5+ unit | `ABS,BUILD_ACT`: Other residential dwellings | ✓ |
| HOUSTMW/NE/S/W | Regional housing starts | `ABS,BUILD_ACT`: by state/territory | ≈ |
| PERMIT | Building permits | `ABS,BA`: Dwelling units approved total SA | ✓ |
| PERMITMW/NE/S/W | Regional permits | `ABS,BA`: by state/territory | ≈ |

### Group 4 — Consumption, Orders, Inventories

| FRED-MD | Concept | AUS source | Match |
|---|---|---|---|
| RETAILx | Retail sales | `ABS,RT`: Retail turnover total SA (monthly) | ✓ |
| AMDMNOx | New orders durable goods | None | ✗ |
| ANDENOx | New orders capital goods | `ABS,CAPEX`: Private new capex (Q) | ≈ |
| AMDMUOx | Unfilled orders durable | None | ✗ |
| BUSINVx | Business inventories total | `ABS,BUS_IND`: Inventories (Q) | ✓ |
| ISRATIOx | Inventory-to-sales | `ABS,BUS_IND`: derived | ✓ |
| AMTMNOx | Total mfg new orders | `ABS,BUS_IND`: Sales of goods & services | ≈ |
| NAPMSXx | ISM new orders | None public; Ai Group / NAB (no API) | ✗ |
| NAPMPRI | ISM prices | NAB business survey: Selling prices (no API) | ✗ |

### Group 5 — Money & Credit

| FRED-MD | Concept | RBA source | Match |
|---|---|---|---|
| M1SL | M1 money stock | RBA D3: M1 (discontinued 2022) | △ |
| M2SL | M2 money stock | RBA D3: M3 (closest analog) | ≈ |
| BOGMBASE | Monetary base | RBA D3: Money base | ✓ |
| TOTRESNS | Total reserves | RBA A1: Liabilities & assets | ≈ |
| NONBORRES | Non-borrowed reserves | RBA A1 | ≈ |
| BUSLOANS | Commercial & industrial loans | RBA D2: Business credit | ✓ |
| CONSUMER | Consumer loans | RBA D2: Personal credit | ✓ |
| NONREVSL | Nonrevolving consumer credit | RBA D2: Personal fixed loans | ≈ |
| REALLN | Real estate loans | RBA D2: Housing credit total | ✓ |
| TOTALSL | Total consumer credit | RBA D2: Personal + housing | ≈ |
| INVEST | Bank securities holdings | RBA B2: Bank balance sheet items | ≈ |

### Group 6 — Interest & Exchange Rates

| FRED-MD | Concept | RBA source | Match |
|---|---|---|---|
| FEDFUNDS | Effective fed funds | RBA F1: Cash rate target | ✓ |
| TB3MS | 3M T-bill | RBA F1: Bank-accepted bills 90-day | ≈ |
| TB6MS | 6M T-bill | RBA F1: Bank-accepted bills 180-day | ≈ |
| GS1 | 1Y Treasury | RBA F2: 2Y CGB (closest) | ≈ |
| GS5 | 5Y Treasury | RBA F2: 5Y CGB | ✓ |
| GS10 | 10Y Treasury | RBA F2: 10Y CGB | ✓ |
| AAA / BAA | Corporate yields | None — RBA F3 has spreads only, post-2005 | ✗ |
| MORTGAGE30US | 30Y fixed mortgage | RBA F5: Standard variable rate (mostly variable in AUS) | ≈ |
| EXCAUSx | AUD per USD | RBA F11: FXRUSD (inverted) | ✓ |
| EXJPUSx | JPY per USD | Cross from RBA F11 | ≈ |
| EXSZUSx | CHF per USD | Cross from RBA F11 | ≈ |
| EXUSUKx | USD per GBP | Cross from RBA F11 | ≈ |
| TWEXAFEGSMTHx | Trade-weighted USD | RBA F11: AUD TWI (analogous AUD-side index) | ≈ |

### Group 7 — Prices

| FRED-MD | Concept | ABS source | Match |
|---|---|---|---|
| CPIAUCSL | CPI all urban | `ABS,CPI`: All groups, weighted avg 8 capitals | ✓ |
| CPILFESL | Core CPI ex food & energy | `ABS,CPI`: Trimmed mean (RBA preferred core) | ≈ |
| CPIAPPSL | CPI apparel | `ABS,CPI`: Clothing & footwear | ✓ |
| CPITRNSL | CPI transportation | `ABS,CPI`: Transport | ✓ |
| CPIMEDSL | CPI medical care | `ABS,CPI`: Health | ✓ |
| CUSR0000SAC | CPI commodities | `ABS,CPI`: Goods | ✓ |
| CUSR0000SAS | CPI services | `ABS,CPI`: Services | ✓ |
| CPIULFSL | CPI ex food | `ABS,CPI`: ex food & non-alcoholic bev | ≈ |
| PCEPI / PCEPILFE | PCE / Core PCE | None — AUS uses CPI as headline | ✗ |
| GDPDEF | GDP deflator | `ABS,ANA_AGG`: GDP IPD (Q) | ✓ |
| WPSFD49207 | PPI final demand | `ABS,PPI`: Final demand (Q) | ✓ |
| WPSFD4111 | PPI final demand goods | `ABS,PPI`: Final demand goods | ✓ |
| WPSFD49502 | PPI final demand services | `ABS,PPI`: Final demand services | ✓ |
| WPSID61 | PPI intermediate | `ABS,PPI`: Intermediate stages | ✓ |
| WPSID62 | PPI raw materials | `ABS,PPI`: Preliminary stage | ≈ |
| OILPRICEx | WTI crude | RBA I2: Bulk commodity AUD/USD | ≈ |
| PPICMM | Commodity prices | RBA I2: Index of commodity prices | ✓ |

### Group 8 — Stock Market

| FRED-MD | Concept | AUS source | Match |
|---|---|---|---|
| S&P 500 level | Equity index level | yfinance `^AXJO` ASX 200 | ≈ |
| S&P industrial | Sector index | yfinance ASX sub-indices | ≈ |
| S&P div yield | Dividend yield | S&P/ASX official (paid) | ≈ |
| S&P P/E | Price-earnings | S&P/ASX official (paid) | ≈ |
| VIXCLSx | VIX | yfinance `^AXVI` (S&P/ASX 200 VIX, "A-VIX") | ✓ |

## 1.2 FRED-QD additional groups (Quarterly add-ons for AUS)

### Group 9 — NIPA detail

`ABS,ANA_AGG` (5206.0). Quarterly. ~95% match to BEA NIPA.

| FRED-QD | AUS equivalent |
|---|---|
| GDPC1, GDP, GDPDEF | GDP CVM, GDP CP, GDP IPD |
| PCECC96, PCDGx, PCNDx, PCESVx | HFCE CVM total + durables/nondurables/services breakdown |
| GPDIC1, FPIx, PNFIx, PRFIx | Private GFCF; non-dwelling vs dwellings |
| GCEC1 | Public GFCE + Public GFCF |
| EXPGSC1, IMPGSC1, NETEXC | Exports / imports / net exports CVM |
| DPIC96 | Real net disposable income |

### Group 10 — Earnings & productivity

| FRED-QD | AUS equivalent |
|---|---|
| CES0600000008 (avg hourly earnings goods) | `ABS,AWE`: Avg weekly ordinary time earnings |
| ULCBS, ULCNFB | `ABS,ANA_AGG`: Real unit labour costs |
| OPHNFB, OPHMFG | ABS Multifactor Productivity (annual only) |

**Note.** Australia uses the Wage Price Index (`ABS,WPI`) — a Laspeyres index of fixed jobs that strips out compositional effects. Conceptually superior to BLS Average Hourly Earnings but not directly comparable.

### Group 11 — Household balance sheets

`ABS,FA` Financial Accounts (5232.0). Quarterly. Mirrors FRB Z.1 sectoral structure.

| FRED-QD | AUS equivalent |
|---|---|
| TLBSHNOx | Household total liabilities |
| TFAABSHNO | Household financial assets |
| TNWBSHNO | Household net worth |
| TARESA | Household land + dwellings |
| HMLISHNO | Household housing loans |
| TDSP | Household debt service ratio (RBA Chart Pack) |

### Group 12 — Non-household balance sheets

Also `ABS,FA`, by sector dimension.

### Group 13 — Sentiment surveys

| Source | Notes |
|---|---|
| Westpac-Melbourne Institute Consumer Sentiment | Monthly, no API, PDF only |
| NAB Business Survey (conditions, confidence, orders) | Monthly, no API, PDF only |
| Roy Morgan Consumer Confidence | Weekly, no API |

**Action.** Either license commercial data (Bloomberg, Refinitiv, Trading Economics) or build a PDF scraper with named-entity extraction. Trading Economics has APIs covering all three.

### Group 14 — Additional financial

RBA F3 corporate spreads (post-2005 only); KangaNews / Bloomberg AusBond Composite for credit indices.

## 1.3 ABS dataflows to ingest (Phase 2A target)

| Dataflow | Description | Frequency | Series count |
|---|---|---|---|
| `ABS,ANA_AGG` | National Accounts aggregates | Q | ~30 |
| `ABS,LF` | Labour Force monthly | M | ~25 |
| `ABS,LF_Q` | Labour Force quarterly | Q | ~10 |
| `ABS,CPI` | Consumer Price Index quarterly | Q | ~15 |
| `ABS,MONTHLY_CPI` | Monthly CPI Indicator | M | ~10 |
| `ABS,PPI` | Producer Price Indexes | Q | ~6 |
| `ABS,WPI` | Wage Price Index | Q | ~6 |
| `ABS,AWE` | Average Weekly Earnings | semi-annual | ~5 |
| `ABS,RT` | Retail Trade monthly | M | ~10 |
| `ABS,RT_Q` | Retail Trade quarterly volume | Q | ~5 |
| `ABS,BUS_IND` | Business Indicators | Q | ~8 |
| `ABS,CAPEX` | Private New Capital Expenditure | Q | ~6 |
| `ABS,BA` | Building Approvals | M | ~6 |
| `ABS,BUILD_ACT` | Building Activity | Q | ~6 |
| `ABS,LEND_FIN` | Lending Indicators | M | ~6 |
| `ABS,RPPI` | Residential Property Price Indexes | Q | ~10 |
| `ABS,FA` | Financial Accounts (household + corp + govt) | Q | ~20 |
| `ABS,BOP` | Balance of Payments | Q | ~10 |
| `ABS,MERCH_TRADE` | International Merchandise Trade | M | ~8 |
| `ABS,IT_PRICE` | International Trade Price Indexes | Q | ~6 |
| **Total ABS** | | | **~210** |

## 1.4 RBA tables to ingest

| Table | Description | Frequency | Series count |
|---|---|---|---|
| f1 / f1.1 | Money market interest rates | D / M | ~5 |
| f2 / f2.1 | Government bond yields (2/3/5/10Y) | D / M | ~5 |
| f3 | Corporate bond yields & spreads | D | ~6 |
| f4 | Lending rates by purpose | M | ~8 |
| f5 | Indicator lending rates | M | ~5 |
| f6 | Housing lending rates | M | ~5 |
| f11 / f11.1 | Exchange rates (AUD bilateral + TWI) | D / M | ~10 |
| d1 / d2 / d3 | Credit aggregates, monetary aggregates | M | ~15 |
| b1 / b2 | RBA + bank balance sheets | M | ~10 |
| i1 / i2 | Commodity prices | M | ~10 |
| **Total RBA** | | | **~80** |

**AUS grand total: ~290 series mapped, ~75% of FRED-QD covered.**

---

# 2. EURO AREA (Eurostat + ECB)

**Statistical authority.** Eurostat — `https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/{flow}/{key}` (SDMX 2.1, no auth).
**Central bank.** ECB Data Portal — `https://data-api.ecb.europa.eu/service/data/{flow}/{key}` (SDMX, no auth).
**Status.** Phase 3 ECB ingestor written. Eurostat ingestor pending.

The Euro Area is unique because we have both a harmonised area-level layer (Eurostat / ECB) AND member-state national statistics offices. This section covers the area-level layer; subsequent sections cover individual member states.

## 2.1 FRED-MD by group

### Group 1 — Output & Income

| FRED-MD | Concept | Eurostat / ECB source | Match |
|---|---|---|---|
| RPI | Real personal income | `nama_10_gdp` / `namq_10_gdp`: Real disposable income | ✓ |
| INDPRO | Industrial production | `sts_inpr_m`: Industrial production index, monthly, EA19 | ✓ |
| IPFINAL | IP final products | `sts_inpr_m`: by MIG (Main Industrial Groupings) — consumer durables, capital goods, intermediate goods, energy | ✓ |
| IPCONGD | IP consumer goods | `sts_inpr_m` MIG: durable + non-durable consumer goods | ✓ |
| IPMAT | IP materials | `sts_inpr_m` MIG: intermediate goods | ✓ |
| IPMANSICS | IP manufacturing | `sts_inpr_m` NACE C: Manufacturing | ✓ |
| IPB51110SQ | IP mining | `sts_inpr_m` NACE B: Mining and quarrying | ✓ |
| CUMFNS | Capacity utilisation mfg | `ei_bsin_q_r2`: Industry capacity utilisation, quarterly | ✓ |
| CMRMTSPLx | Manufacturing & trade real sales | `sts_trtu_m`: Retail trade volume | ≈ |

**Coverage: ~95% — Eurostat publishes industrial production at multiple aggregation levels and frequencies.**

### Group 2 — Labor Market

| FRED-MD | Concept | Eurostat source | Match |
|---|---|---|---|
| UNRATE | Unemployment rate | `une_rt_m`: Unemployment rate, monthly, SA, EA19 | ✓ |
| UEMPMEAN | Mean weeks unemployed | `une_ltu_a`: Long-term unemployment (>12 months) | ≈ |
| UEMPLT5 / 5to14 / 15ov / 15to26 / 27ov | Duration breakdown | `lfsq_ugad`: Unemployment by duration, quarterly | ≈ |
| CLAIMSx | Initial unemployment claims | None — EU member states have administrative claims data published nationally, no harmonised series | ✗ |
| PAYEMS | Total nonfarm payrolls | `lfsi_emp_m`: Employment monthly | ✓ |
| USPRIV | Private employment | `nama_10_a64_e`: Employment by NACE sector (annual) | ≈ |
| MANEMP | Manufacturing employment | `lfsq_egan2`: Employment by NACE C, quarterly | ✓ |
| USCONS | Construction employment | `lfsq_egan2`: NACE F | ✓ |
| USTRADE | Wholesale + retail employment | `lfsq_egan2`: NACE G | ✓ |
| USGOVT | Government employment | `lfsq_egan2`: NACE O | ✓ |
| CES0600000007 | Avg weekly hours goods | `lfsa_ewhuna`: Avg hours worked by NACE | ≈ |
| CIVPART | Labour force participation | `une_rt_m`: Activity rate, EA | ✓ |
| EMRATIO | Employment-population ratio | `une_rt_m`: Employment rate, EA | ✓ |

**Coverage: ~85% — gap is weekly initial claims (no EA equivalent).**

### Group 3 — Housing

| FRED-MD | Concept | Eurostat source | Match |
|---|---|---|---|
| HOUST | Housing starts | `sts_cobp_m`: Building permits index | ≈ |
| PERMIT | Building permits | `sts_cobp_m`: Building permits — number of dwellings | ✓ |
| Regional housing/permit series | EU member-state level | `sts_cobp_q` by country | ≈ |

### Group 4 — Consumption, Orders, Inventories

| FRED-MD | Concept | Eurostat source | Match |
|---|---|---|---|
| RETAILx | Retail sales volume | `sts_trtu_m`: Retail trade turnover/volume | ✓ |
| AMDMNOx | New orders durable goods | `sts_inno_m`: New orders in industry | ✓ |
| ANDENOx | New orders capital goods | `sts_inno_m` MIG: capital goods | ✓ |
| BUSINVx | Business inventories | None monthly; quarterly via national accounts | △ |
| ISRATIOx | Inventory-to-sales | None | ✗ |
| AMTMNOx | Total mfg new orders | `sts_inno_m` | ✓ |
| NAPMxxx | ISM PMIs | S&P Global PMI (commercial); Eurostat `ei_bsin_q_r2` business confidence (Q) | ≈ |

### Group 5 — Money & Credit (ECB)

| FRED-MD | Concept | ECB source | Match |
|---|---|---|---|
| M1SL | M1 money stock | `BSI/M.U2.Y.V.M10.X.1.U2.2300.Z01.E` | ✓ |
| M2SL | M2 money stock | `BSI/M.U2.Y.V.M20.X.1.U2.2300.Z01.E` | ✓ |
| M3SL | M3 money stock | `BSI/M.U2.Y.V.M30.X.1.U2.2300.Z01.E` | ✓ |
| BOGMBASE | Monetary base | ECB Balance Sheet of the Eurosystem | ≈ |
| BUSLOANS | Commercial & industrial loans | `BSI` MFI loans to non-financial corporations | ✓ |
| CONSUMER | Consumer loans | `BSI` MFI loans to households for consumption | ✓ |
| REALLN | Real estate loans | `BSI` MFI loans to households for house purchase | ✓ |
| TOTALSL | Total consumer credit | `BSI` total household loans | ≈ |
| INVEST | Bank securities holdings | `BSI` MFI holdings of securities | ✓ |

**Coverage: ~95% — ECB Balance Sheet Items (BSI) statistics are extremely rich.**

### Group 6 — Interest & Exchange Rates (ECB)

| FRED-MD | Concept | ECB source | Match |
|---|---|---|---|
| FEDFUNDS | Policy rate | `FM/D.U2.EUR.4F.KR.DFR.LEV` Deposit facility rate | ✓ |
| TB3MS | 3M T-bill | `FM` 3-month Euribor | ≈ |
| GS1 / GS5 / GS10 | Sovereign yields | `FM/D.DE.EUR.4F.BB.U_A2Y.YLD` etc — German Bunds (proxy for area) | ✓ |
| AAA / BAA | Corporate yields | iBoxx Euro Corporate (commercial); ECB yield curve dataset | ≈ |
| MORTGAGE30US | Mortgage rate | `MIR/M.U2.B.A2C.A.R.A.2240.EUR.N` MFI lending rates housing | ≈ |
| EXJPUSx / EXSZUSx etc | Bilateral FX | `EXR/D.JPY.EUR.SP00.A` etc | ✓ |
| TWEXAFEGSMTHx | Trade-weighted USD | Euro effective exchange rate (EER-19, EER-42) | ≈ (Euro side) |

### Group 7 — Prices

| FRED-MD | Concept | Eurostat source | Match |
|---|---|---|---|
| CPIAUCSL | CPI all items | `prc_hicp_midx`: HICP all items, EA19 | ✓ |
| CPILFESL | Core CPI | `prc_hicp_midx`: HICP ex energy, food, alcohol, tobacco | ✓ |
| CPIAPPSL | CPI apparel | `prc_hicp_midx`: COICOP CP03 Clothing & footwear | ✓ |
| CPITRNSL | CPI transportation | `prc_hicp_midx`: COICOP CP07 Transport | ✓ |
| CPIMEDSL | CPI medical | `prc_hicp_midx`: COICOP CP06 Health | ✓ |
| CUSR0000SAC | CPI commodities | `prc_hicp_midx`: Goods | ✓ |
| CUSR0000SAS | CPI services | `prc_hicp_midx`: Services | ✓ |
| GDPDEF | GDP deflator | `namq_10_gdp`: GDP price deflator | ✓ |
| WPSFD4111 | PPI goods | `sts_inpp_m`: Industrial producer prices | ✓ |
| WPSID61 | PPI intermediate | `sts_inpp_m` MIG: intermediate goods | ✓ |
| OILPRICEx | Oil price | Brent via Eurostat energy or use FRED:DCOILBRENTEU | ✓ |
| PPICMM | Commodity prices | HWWI Commodity Price Index (Hamburg) | ≈ |

**Coverage: ~95% — HICP is methodologically the closest international comparator for US CPI.**

### Group 8 — Stock Market

| FRED-MD | Concept | Source | Match |
|---|---|---|---|
| S&P 500 level | Equity index | yfinance `^STOXX50E` (Euro Stoxx 50) or `^STOXX` (Stoxx 600) | ≈ |
| S&P industrial | Sector index | Stoxx sectoral indices via yfinance | ≈ |
| S&P div yield | Dividend yield | Stoxx official (paid) | ≈ |
| VIXCLSx | VIX | yfinance `^V2TX` (VSTOXX) | ✓ |

## 2.2 FRED-QD additional groups for Euro Area

### Group 9 — NIPA detail

`namq_10_gdp` (Eurostat Quarterly National Accounts). ESA 2010 framework. Coverage matches BEA NIPA almost line-for-line.

### Group 10 — Earnings & productivity

| FRED-QD | EU equivalent |
|---|---|
| CES0600000008 | `ei_lmlc_q`: Labour cost index quarterly |
| ULCBS, ULCNFB | `nama_10_lp_ulc`: Unit labour costs annual; `namq_10_lp_ulc` quarterly |
| OPHNFB | `nama_10_lp_ulc`: Labour productivity per hour |

### Group 11 — Household balance sheets

`nasq_10_f_bs`: Quarterly financial balance sheets by sector. Matches FRB Z.1 sectoral structure (households, non-financial corp, financial corp, government, ROW).

### Group 12 — Non-household balance sheets

Same dataflow as above, by sector dimension.

### Group 13 — Sentiment surveys

`ei_bsco_m` Consumer Confidence Indicator, `ei_bsin_q_r2` Industry Confidence Indicator, `ei_bssi_m_r2` Economic Sentiment Indicator (ESI). All harmonised across EU countries by DG ECFIN.

## 2.3 Eurostat dataflows to ingest

| Dataflow | Description | Freq | Series target |
|---|---|---|---|
| `namq_10_gdp` | Quarterly GDP and main components | Q | ~25 |
| `namq_10_a10` | GVA and income by NACE A10 industries | Q | ~10 |
| `nasq_10_f_bs` | Financial balance sheets by sector | Q | ~20 |
| `sts_inpr_m` | Industrial production index monthly | M | ~15 |
| `sts_inno_m` | New orders in industry | M | ~5 |
| `sts_trtu_m` | Retail trade turnover | M | ~5 |
| `sts_cobp_m` | Construction permits | M | ~5 |
| `sts_inpp_m` | Industrial producer prices | M | ~10 |
| `prc_hicp_midx` | HICP monthly index | M | ~15 |
| `prc_hicp_manr` | HICP annual rate of change | M | ~5 |
| `une_rt_m` | Monthly unemployment rate | M | ~6 |
| `lfsi_emp_m` | Monthly employment | M | ~5 |
| `lfsq_egan2` | Employment by NACE quarterly | Q | ~10 |
| `ei_bsco_m` | Consumer confidence | M | ~3 |
| `ei_bsin_q_r2` | Business confidence | M/Q | ~5 |
| `ei_bssi_m_r2` | Economic Sentiment Indicator | M | ~3 |
| `ei_lmlc_q` | Labour cost index | Q | ~5 |
| `bop_eu6_q` | Balance of payments quarterly | Q | ~10 |
| `ext_lt_intertrd` | International trade data | M | ~10 |
| **Total Eurostat** | | | **~170** |

## 2.4 ECB dataflows to ingest

| Dataflow | Description | Freq | Series target |
|---|---|---|---|
| `FM` | Financial markets — policy rates, sovereign yields, money markets | D | ~25 |
| `BSI` | Balance sheet items — money supply, MFI loans | M | ~30 |
| `MIR` | MFI interest rates on loans and deposits | M | ~10 |
| `EXR` | Exchange rates | D | ~15 |
| `ICP` | Harmonised consumer prices (alternate to Eurostat HICP) | M | ~10 |
| `MNA` | National accounts | Q | ~20 |
| `LFSI` | Labour force survey indicators | M/Q | ~5 |
| `STS` | Short-term statistics (IP, retail) | M | ~10 |
| **Total ECB** | | | **~125** |

**Euro Area grand total: ~295 series, ~95% of FRED-QD covered.**

---

# 3. GERMANY (DESTATIS + Bundesbank)

**Statistical office.** Statistisches Bundesamt (DESTATIS) — `https://www-genesis.destatis.de/genesisWS/rest/2020/data/tablefile` (Genesis-Online API, free key required).
**Central bank.** Deutsche Bundesbank — `https://api.statistiken.bundesbank.de/rest/data/{flow}/{key}` (no auth).
**Status.** Not yet ingested.

## 3.1 FRED-MD highlights

| FRED-MD | DE source | Match |
|---|---|---|
| INDPRO | DESTATIS GENESIS table 42153-0001: Index der industriellen Nettoproduktion | ✓ |
| UNRATE | Bundesagentur für Arbeit / Eurostat HICP-aligned rate | ✓ |
| HOUST | DESTATIS table 31231-0002: Baugenehmigungen | ✓ |
| RETAILx | DESTATIS table 45211-0001: Einzelhandelsumsatz | ✓ |
| M1/M2/M3 | Bundesbank `BBK01.WT5613` etc — German contribution to EA monetary aggregates | △ (now reported only at EA level by ECB) |
| FEDFUNDS | ECB Deposit Facility Rate (no national policy rate post-1999) | ✓ |
| GS10 | Bundesbank `BBK01.WT3110`: Umlaufrendite öffentlicher Anleihen 10Y | ✓ |
| CPIAUCSL | DESTATIS table 61111-0001: Verbraucherpreisindex Deutschland (national CPI) | ✓ |
| HICPDE | Eurostat `prc_hicp_midx` filtered to GEO=DE | ✓ |
| Stock market | DAX via yfinance `^GDAXI` | ✓ |

## 3.2 Country-specific series of interest

| Series | Description | Source |
|---|---|---|
| Ifo Geschäftsklima | Business climate index (most-watched DE survey) | ifo Institute (paid API) |
| ZEW Indikator | Investor confidence index | ZEW (paid) |
| GfK Konsumklima | Consumer confidence | GfK (paid) |
| Bundesbank balance sheet | Monthly | Bundesbank `BBK01` series |
| German Bund yields | 1Y, 2Y, 5Y, 10Y, 30Y | Bundesbank `BBK01.WT*` or ECB `FM/D.DE.EUR.4F.BB.*` |

## 3.3 Data sources

| Source | Endpoint | Auth | Series target |
|---|---|---|---|
| DESTATIS Genesis-Online | `https://www-genesis.destatis.de/genesisWS/rest/2020/` | Free API key | ~40 |
| Bundesbank Statistical API | `https://api.statistiken.bundesbank.de/rest/data/` | None | ~60 |

**Phase 3B target: ~100 German series, ~85% FRED-MD coverage.**

---

# 4. FRANCE (INSEE + Banque de France)

**Statistical office.** INSEE — `https://api.insee.fr/series/BDM/V1/data/{seriesIds}` (BDM API, free key required).
**Central bank.** Banque de France — `https://webstat.banque-france.fr/ws_wsen/rest/data/{flow}/{key}` (SDMX, no auth).
**Status.** Not yet ingested.

## 4.1 FRED-MD highlights

| FRED-MD | FR source | Match |
|---|---|---|
| INDPRO | INSEE BDM `010767687`: Indice de production industrielle | ✓ |
| UNRATE | INSEE BDM unemployment rate (ILO definition, harmonised) | ✓ |
| HOUST | INSEE: Mises en chantier de logements | ✓ |
| RETAILx | INSEE: Indice du commerce de détail | ✓ |
| GS10 | Banque de France OAT 10Y yield | ✓ |
| CPIAUCSL | INSEE: Indice des prix à la consommation (national CPI) | ✓ |
| Stock market | CAC 40 via yfinance `^FCHI` | ✓ |

## 4.2 Country-specific series

| Series | Description | Source |
|---|---|---|
| Climat des affaires | INSEE business climate index | INSEE BDM |
| Confiance des ménages | INSEE consumer confidence | INSEE BDM |
| Banque de France investment survey | Quarterly investment intentions | Banque de France |

## 4.3 Data sources

| Source | Endpoint | Auth | Series target |
|---|---|---|---|
| INSEE BDM | `https://api.insee.fr/series/BDM/V1/` | OAuth2 free key | ~50 |
| Banque de France WebStat | `https://webstat.banque-france.fr/ws_wsen/rest/data/` | None | ~30 |

**Phase 3C target: ~80 French series.**

---

# 5. ITALY (ISTAT + Banca d'Italia)

**Statistical office.** ISTAT — SDMX REST `https://sdmx.istat.it/SDMXWS/rest/data/{flow}/{key}` (no auth).
**Central bank.** Banca d'Italia — `https://infostat.bancaditalia.it/inquiry/api/data/{flow}/{key}` (no auth).
**Status.** Not yet ingested.

## 5.1 Coverage

ISTAT publishes harmonised SDMX-formatted data through their REST API. The dataflows mirror the Eurostat structure (national accounts, prices, labour, IP) but with Italian-specific series codes. ISTAT also publishes a unique set of regional and sectoral cuts.

**Phase 3D target: ~60 Italian series.**

---

# 6. SPAIN (INE + Banco de España)

**Statistical office.** INE — `https://servicios.ine.es/wstempus/jsCache/ES/DATOS_TABLA/{table}` (JSON, no auth).
**Central bank.** Banco de España — `https://www.bde.es/webbe/en/estadisticas/recursos/descargas-completas.html` (CSV downloads + REST endpoint).
**Status.** Not yet ingested.

**Phase 3E target: ~50 Spanish series.**

---

# 7. NETHERLANDS (CBS + DNB)

**Statistical office.** Centraal Bureau voor de Statistiek (CBS) — `https://opendata.cbs.nl/ODataApi/odata/{table}` (OData, no auth).
**Central bank.** De Nederlandsche Bank (DNB) — public CSV downloads.
**Status.** Not yet ingested.

**Phase 3F target: ~40 Dutch series.**

---

# 8. UNITED KINGDOM (ONS + BoE)

**Statistical office.** Office for National Statistics — `https://www.ons.gov.uk/{topic}/timeseries/{series}/{dataset}/data` (JSON, no auth).
**Central bank.** Bank of England — Statistical Interactive Database (CSV downloads, no auth).
**Status.** Phase 3 ingestor written.

## 8.1 FRED-MD highlights

| FRED-MD | UK source | Match |
|---|---|---|
| INDPRO | ONS K222/DIOP: Index of Production | ✓ |
| UNRATE | ONS MGSX/LMS: ILO unemployment rate | ✓ |
| PAYEMS | ONS BCAJ/EMP: PAYE employees | ✓ |
| HOUST | ONS housing starts (DCLG) | ≈ |
| RETAILx | ONS K54L/RSI: Retail Sales Index | ✓ |
| FEDFUNDS | BoE Bank Rate (`IUMABEDR`) | ✓ |
| GS10 | BoE 10Y nominal yield (`IUDMNZC`) | ✓ |
| CPIAUCSL | ONS L55O/MM23: CPI all items (CPIH if including owner housing) | ✓ |
| Stock market | FTSE 100 via yfinance `^FTSE` | ✓ |

## 8.2 Data sources

| Source | Endpoint | Auth | Series target |
|---|---|---|---|
| ONS time series API | `https://www.ons.gov.uk/{topic}/timeseries/{id}/{ds}/data` | None | ~50 |
| BoE Statistical Interactive | CSV downloads via `/boeapps/database/` | None | ~40 |

**Phase 3 (UK partial) target: ~90 series, ~80% FRED-MD coverage.**

---

# 9. CANADA (StatCan + BoC)

**Statistical office.** Statistics Canada — `https://www150.statcan.gc.ca/t1/wds/rest/` (Web Data Service, no auth).
**Central bank.** Bank of Canada — `https://www.bankofcanada.ca/valet/observations/{series}/csv` (Valet API, no auth).
**Status.** Phase 3 ingestor written.

**Phase 3 (Canada) target: ~70 series.**

---

# 10. JAPAN (e-Stat + BoJ)

**Statistical office.** e-Stat (Statistics Bureau of Japan) — `https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData` (free API key required).
**Central bank.** Bank of Japan — `https://www.stat-search.boj.or.jp/ssi/cgi-bin/famecgi2` (CSV via web form; SDMX limited).
**Status.** Pending API key registration.

**Phase 3 (Japan) target: ~80 series, ~80% FRED-MD coverage.**

---

# 11. SWITZERLAND (FSO + SNB)

**Statistical office.** Bundesamt für Statistik (BFS/FSO) — SDMX endpoints via `https://www.pxweb.bfs.admin.ch/api/v1/en/`.
**Central bank.** Swiss National Bank — `https://data.snb.ch/api/cube/{cube}/data/csv` (no auth).
**Status.** Not yet ingested.

**Phase 3 (CH) target: ~50 series.**

---

# 12. NEW ZEALAND (Stats NZ + RBNZ)

**Statistical office.** Stats NZ — `https://api.stats.govt.nz/wds/rest/` (free API key required).
**Central bank.** Reserve Bank of New Zealand — `https://www.rbnz.govt.nz/-/media/RelatedDocuments/Statistics/{file}.csv` (CSV, no auth).
**Status.** Pending API key registration.

**Phase 3 (NZ) target: ~50 series.**

---

# CROSS-COUNTRY SUMMARY

| Country | Statistical office | Central bank | API auth | Status | Series target | FRED-MD coverage |
|---|---|---|---|---|---|---|
| US | BEA / BLS / Census | Fed / FRB | None (FRED key) | **DONE** Phase 1 | 27 done; 134 target | 100% |
| AUS | ABS | RBA | None | Phase 2 (queued) | 290 | 75% |
| EA | Eurostat | ECB | None | Phase 3A (ECB written) | 295 | 95% |
| DE | DESTATIS | Bundesbank | Free key | Phase 3B | 100 | 85% |
| FR | INSEE | Banque de France | OAuth2 free key | Phase 3C | 80 | 80% |
| IT | ISTAT | Banca d'Italia | None | Phase 3D | 60 | 75% |
| ES | INE | Banco de España | None | Phase 3E | 50 | 70% |
| NL | CBS | DNB | None | Phase 3F | 40 | 70% |
| UK | ONS | BoE | None | Phase 3 (written) | 90 | 80% |
| CA | StatCan | BoC | None | Phase 3 (written) | 70 | 80% |
| JP | e-Stat | BoJ | Free key | Phase 3 (pending) | 80 | 80% |
| CH | FSO | SNB | None | Phase 3 (pending) | 50 | 75% |
| NZ | Stats NZ | RBNZ | Free key | Phase 3 (pending) | 50 | 70% |

**Total target: ~1,280 series across 13 jurisdictions.** Of these, ~75–95% will map directly to FRED-MD/QD concepts depending on country, giving us a true cross-country macro panel for signal research.

---

# OPEN QUESTIONS / DECISIONS

1. **Sentiment surveys.** Most countries' best business and consumer surveys are commercial. Either license one provider (Trading Economics is the most comprehensive aggregator) or accept the gap and build only on official statistics.

2. **PMI data.** S&P Global PMI is the global standard but is subscription-only. The Eurostat / national equivalents (ESI, business confidence) are free but less frequently used by practitioners.

3. **Corporate bond yields.** Long-history corporate bond yield indices are uniformly proprietary (ICE BofA, iBoxx, Bloomberg AusBond). Consider using sovereign yields + a constant spread proxy until a budget exists.

4. **High-frequency unemployment.** Only the US publishes weekly initial claims. Every other country has fortnightly or monthly admin data not published as a time series. Accept the gap.

5. **Credit aggregates.** US (FRB H.8), AUS (RBA D2), Euro Area (ECB BSI) all publish monthly credit by sector. UK (BoE), Canada (BoC), Japan (BoJ) publish similar. Mapping is direct.

---

# MAINTENANCE PROTOCOL

When a new dataflow is added or an old one breaks:

1. Update this file (`macro_data_mapping.md`) — add the row to the relevant country section.
2. Update the corresponding ingest module (`{source}_ingest.py`) with the new flow_ref or table ID.
3. Update the runner (`update_{country}.py`) to fetch the new series.
4. Re-run `build_processed.py` to refresh the parquet files.
5. Commit with message `data: add {country} {concept}`.

Last updated: 2026-04-11
