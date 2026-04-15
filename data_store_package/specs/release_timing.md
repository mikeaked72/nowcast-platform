# Data Release Timing — Source Priority Guide
## Which source to use for each country × concept combination

**Principle:** Always prefer the source that releases earliest. For signal
research, stale data is worse than no data. The pipeline should pull from
the fastest source first, then backfill structural/annual data from slower
sources.

**Three-tier model:**
- **Tier 1 — Real-time layer** (NSO direct ingestors): national statistics
  offices publish first. Typical lag: CPI 2-4 weeks, GDP 4-8 weeks after
  quarter end, employment 2-4 weeks, rates same-day.
- **Tier 2 — Cyclical layer** (IMF IFS): IMF collects from NSOs and
  publishes with an additional 1-4 week lag. Monthly + quarterly frequency.
  Best for EM countries without a direct ingestor.
- **Tier 3 — Structural layer** (World Bank): Annual only, 6-12 month lag.
  Best for debt ratios, trade shares, population, GDP per capita, and
  historical backfill to 1960.

---

## Release timing by concept (typical lag after reference period ends)

| Concept | Tier 1 (NSO direct) | Tier 2 (IMF IFS) | Tier 3 (World Bank) |
|---|---|---|---|
| **CPI monthly** | 2-4 weeks | 4-8 weeks | Annual only, 6-12 months |
| **Industrial Production** | 4-6 weeks | 6-10 weeks | N/A |
| **Employment / Unemployment** | 2-4 weeks | 4-8 weeks | Annual only |
| **GDP quarterly** | 4-8 weeks (advance), 8-12 weeks (revised) | 8-16 weeks | Annual, 6-12 months |
| **Policy rate** | Same day | 1-2 weeks | N/A |
| **Government bond yields** | Same day | 1-2 weeks | N/A |
| **Exchange rates** | Same day | 1-2 weeks | Annual average, 6 months |
| **Retail sales** | 4-6 weeks | 6-10 weeks | N/A |
| **Money supply** | 4-6 weeks | 6-10 weeks | Annual, 6 months |
| **Current account** | 8-12 weeks (quarterly) | 12-16 weeks | Annual, 6-12 months |
| **Government debt** | Quarterly/annual | Varies | Annual, 6-12 months |
| **Population** | Annual | N/A | Annual, 6 months |
| **Trade (% of GDP)** | Quarterly | 8-12 weeks | Annual, 6-12 months |

---

## Source priority by country

### Countries with Tier 1 direct ingestors (use NSO first)

| Country | NSO source | Central bank | IMF IFS role | WB role |
|---|---|---|---|---|
| **US** | FRED (BEA/BLS/Census) | Fed H.15/H.6/H.8 | Backup only | Annual structural |
| **Australia** | ABS SDMX | RBA CSV tables | Backup only | Annual structural |
| **UK** | ONS time series | BoE IADB CSV | Backup only | Annual structural |
| **Euro Area** | Eurostat SDMX | ECB Data Portal | Backup only | Annual structural |
| **Germany** | DESTATIS Genesis + Bundesbank | (ECB covers) | Backup only | Annual structural |
| **France** | INSEE BDM + Banque de France | (ECB covers) | Backup only | Annual structural |
| **Canada** | StatCan WDS + Bank of Canada Valet | (covered) | Backup only | Annual structural |
| **Japan** | e-Stat + BoJ | (covered) | Backup only | Annual structural |
| **Switzerland** | FSO + SNB (pending) | (covered) | Backup for now | Annual structural |
| **New Zealand** | Stats NZ + RBNZ (pending) | (covered) | Backup for now | Annual structural |

### Countries covered by IMF IFS only (Tier 2 = primary)

| Country | ISO | IMF IFS coverage | WB role |
|---|---|---|---|
| **China** | CN | Monthly CPI, rates, FX, money. Quarterly GDP. | Annual structural |
| **India** | IN | Monthly CPI, rates, FX. Quarterly GDP (with lag). | Annual structural |
| **Brazil** | BR | Monthly CPI, rates, FX, money. Quarterly GDP. | Annual structural |
| **South Korea** | KR | Full coverage. Bank of Korea also has good API (ECOS). | Annual structural |
| **Mexico** | MX | Full coverage. Banxico also has API. | Annual structural |
| **Indonesia** | ID | Monthly CPI, rates, FX. GDP with lag. | Annual structural |
| **Turkey** | TR | Monthly CPI, rates, FX. GDP quarterly. | Annual structural |
| **South Africa** | ZA | Monthly CPI, rates, FX. SARB also publishes. | Annual structural |
| **Poland** | PL | Full. GUS also has API (BDL). | Annual structural |
| **Thailand** | TH | Monthly CPI, rates, FX. | Annual structural |
| **Malaysia** | MY | Monthly CPI, rates. Quarterly GDP. | Annual structural |
| **Philippines** | PH | Monthly CPI, rates. | Annual structural |
| **Chile** | CL | Full. BCCh also has API. | Annual structural |
| **Colombia** | CO | Monthly CPI, rates. | Annual structural |
| **Peru** | PE | Monthly CPI, rates. BCRP also publishes. | Annual structural |
| **Czech Republic** | CZ | Full. CZSO has Eurostat-compatible SDMX. | Annual structural |
| **Hungary** | HU | Full. KSH has Eurostat-compatible SDMX. | Annual structural |
| **Romania** | RO | Monthly CPI, rates. | Annual structural |
| **Israel** | IL | Monthly CPI, rates. CBS has good API. | Annual structural |
| **UAE** | AE | Limited (rates, FX). No CPI in IFS. | Annual structural |
| **Saudi Arabia** | SA | Limited (rates, FX, money). GASTAT for CPI. | Annual structural |

### Special cases — countries worth future individual ingestors

| Country | Why | API availability |
|---|---|---|
| **South Korea** | Deep, liquid market. Bank of Korea ECOS API is excellent. | Free API key |
| **Brazil** | BCB (Banco Central) has one of the best EM APIs in the world. | No auth |
| **India** | RBI DBIE database has comprehensive API. | No auth |
| **Israel** | CBS (Central Bureau of Statistics) publishes rich SDMX data. | No auth |

---

## Pipeline execution order (reflects timing priority)

When `update_international.py` runs, it should execute sources in this order:

1. **ECB** — same-day rates, daily FX, monthly monetary aggregates
2. **Eurostat** — monthly IP, retail, HICP (2-4 week lag)
3. **Bundesbank** — daily Bund yields
4. **Banque de France** — OAT yields, credit
5. **ONS + BoE** — monthly CPI, employment, GDP; daily Bank Rate, gilts
6. **Statistics Canada + BoC** — monthly macro + daily rates
7. **e-Stat + BoJ** — monthly/quarterly Japanese macro
8. **DESTATIS** — monthly German CPI, IP, retail (if API key available)
9. **INSEE** — monthly French CPI, IP, retail (if API key available)
10. **IMF IFS** — EM monthly/quarterly (runs last because it's the slowest Tier 2 source)
11. **World Bank** — annual structural (runs last, least time-sensitive)

This ordering is already reflected in `update_international.py`.

---

## Summary table

| Source | Countries | Frequency | Auth | Lag vs NSO | Use for |
|---|---|---|---|---|---|
| FRED | US | D/M/Q | API key | Baseline | All US macro |
| ABS | AU | M/Q | None | Baseline | All AUS macro |
| RBA | AU | D/M | None | Baseline | AUS rates, FX, credit, commodities |
| ONS | UK | M/Q | None | Baseline | UK CPI, employment, GDP, retail |
| BoE | UK | D/M | None | Baseline | UK rates, gilts, money, credit |
| Eurostat | EA + 27 EU | M/Q | None | Baseline | EA harmonised macro |
| ECB | EA | D/M/Q | None | Baseline | EA rates, FX, money, credit |
| Bundesbank | DE | D/M | None | Baseline | German Bund yields |
| DESTATIS | DE | M/Q | Free key | Baseline | German CPI, IP, retail, GDP |
| INSEE | FR | M/Q | Free OAuth2 | Baseline | French CPI, IP, GDP |
| Banque de France | FR | M | None | Baseline | French OAT, credit |
| StatCan + BoC | CA | M/Q/D | None | Baseline | Canadian macro |
| e-Stat | JP | M/Q | Free key | Baseline | Japanese CPI, IP, employment |
| BoJ | JP | D/M | None | Baseline | Japanese rates, money |
| **IMF IFS** | **~200** | **M/Q** | **None** | **+1-4 weeks** | **EM cyclical macro** |
| **World Bank** | **~260** | **Annual** | **None** | **+6-12 months** | **Structural / backfill** |

Last updated: 2026-04-12
