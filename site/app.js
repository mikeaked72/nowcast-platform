(async function () {
  const state = {
    schemaVersion: 1,
    countries: [],
    manifest: null,
    country: null,
    indicator: null,
    period: null,
    payload: null,
    overview: [],
    sourceCoverage: null,
  };

  const elements = {
    status: document.getElementById("status"),
    pageTitle: document.getElementById("page-title"),
    countrySelect: document.getElementById("country-select"),
    indicatorSelect: document.getElementById("indicator-select"),
    periodSelect: document.getElementById("period-select"),
    panels: {
      headline: document.getElementById("headline"),
      history: document.getElementById("history"),
      comparison: document.getElementById("comparison"),
      contributions: document.getElementById("contributions"),
      "release-impacts": document.getElementById("release-impacts"),
      "release-dates": document.getElementById("release-dates"),
      methodology: document.getElementById("methodology"),
      faq: document.getElementById("faq"),
      downloads: document.getElementById("downloads"),
    },
  };

  try {
    const [countries, manifest, sourceCoverage] = await Promise.all([
      fetchJson("data/countries.json"),
      fetchOptionalJson("data/manifest.json"),
      fetchOptionalJson("data/source_coverage.json"),
    ]);
    state.countries = countries.filter((country) => country.enabled);
    state.manifest = manifest;
    state.sourceCoverage = sourceCoverage;
    if (!state.countries.length) {
      throw new Error("No enabled countries");
    }
    wireTabs();
    wireControls();
    populateCountries();
    const initial = readUrlState();
    await selectCountry(initial.country || state.countries[0].code, initial.indicator, initial.run);
  } catch (error) {
    elements.status.textContent = `Could not render published nowcast data: ${error.message}`;
  }

  function wireTabs() {
    for (const button of document.querySelectorAll(".tab")) {
      button.addEventListener("click", () => {
        for (const item of document.querySelectorAll(".tab")) {
          item.classList.toggle("active", item === button);
        }
        for (const [name, panel] of Object.entries(elements.panels)) {
          panel.classList.toggle("active", name === button.dataset.tab);
        }
      });
    }
  }

  function wireControls() {
    elements.countrySelect.addEventListener("change", () => selectCountry(elements.countrySelect.value));
    elements.indicatorSelect.addEventListener("change", () => selectIndicator(elements.indicatorSelect.value));
    elements.periodSelect.addEventListener("change", () => {
      state.period = elements.periodSelect.value;
      writeUrlState();
      render();
    });
  }

  function populateCountries() {
    elements.countrySelect.replaceChildren(
      ...state.countries.map((country) => option(country.code, country.name)),
    );
  }

  async function selectCountry(countryCode, indicatorCode, runDate) {
    state.country = state.countries.find((country) => country.code === countryCode) || state.countries[0];
    elements.countrySelect.value = countryCode;
    elements.indicatorSelect.replaceChildren(
      ...state.country.indicators.map((indicator) => option(indicator.code, indicator.display_name)),
    );
    state.overview = await loadCountryOverview(state.country);
    const nextIndicator = state.country.indicators.some((indicator) => indicator.code === indicatorCode)
      ? indicatorCode
      : state.country.indicators[0].code;
    await selectIndicator(nextIndicator, runDate);
  }

  async function selectIndicator(indicatorCode, runDate) {
    state.indicator = state.country.indicators.find((indicator) => indicator.code === indicatorCode);
    elements.indicatorSelect.value = indicatorCode;
    state.payload = await loadIndicatorPayload(state.country.code, indicatorCode);
    const dates = unique(state.payload.history.map((row) => row.as_of_date));
    elements.periodSelect.replaceChildren(...dates.map((date) => option(date, dateLabel(date))));
    state.period = dates.includes(runDate) ? runDate : state.payload.latest.as_of_date;
    elements.periodSelect.value = state.period;
    writeUrlState();
    render();
  }

  async function loadIndicatorPayload(countryCode, indicatorCode) {
    const base = `data/${countryCode}/${indicatorCode}`;
    const [latest, metadata, historyCsv, contributionsCsv, releaseImpactsCsv] = await Promise.all([
      fetchJson(`${base}/latest.json`),
      fetchJson(`${base}/metadata.json`),
      fetchText(`${base}/history.csv`),
      fetchText(`${base}/contributions.csv`),
      fetchText(`${base}/release_impacts.csv`),
    ]);
    const extras = await loadOptionalArtifacts(base, metadata.downloads || []);
    const payload = {
      latest,
      metadata,
      history: parseCsv(historyCsv),
      contributions: parseCsv(contributionsCsv),
      releaseImpacts: parseCsv(releaseImpactsCsv),
      extras,
      base,
    };
    validatePayload(payload, countryCode, indicatorCode);
    return payload;
  }

  async function loadCountryOverview(country) {
    return Promise.all(country.indicators.map(async (indicator) => {
      try {
        const [latest, metadata] = await Promise.all([
          fetchJson(`data/${country.code}/${indicator.code}/latest.json`),
          fetchJson(`data/${country.code}/${indicator.code}/metadata.json`),
        ]);
        return { indicator, latest, metadata };
      } catch (error) {
        return { indicator, error: error.message };
      }
    }));
  }

  function render() {
    const { latest } = state.payload;
    const snapshot = selectedSnapshot();
    elements.pageTitle.textContent = `${latest.country_name} ${latest.indicator_name}`;
    elements.status.textContent = statusText(snapshot, latest);
    renderHeadline();
    renderHistory();
    renderComparison();
    renderContributions();
    renderReleaseImpacts();
    renderReleaseDates();
    renderMethodology();
    renderFaq();
    renderDownloads();
  }

  function renderHeadline() {
    const { latest, metadata } = state.payload;
    const snapshot = selectedSnapshot();
    const releaseRows = state.payload.releaseImpacts
      .filter((row) => row.as_of_date === state.period)
      .sort((left, right) => statusRank(left.notes) - statusRank(right.notes) || Math.abs(Number(right.impact)) - Math.abs(Number(left.impact)));
    const topRows = releaseRows.filter((row) => row.notes === "new_release").slice(0, 3);
    elements.panels.headline.replaceChildren(
      card("Headline estimate", formatValue(snapshot.estimate_value, metadata), snapshot.reference_period),
      card("Change", formatSigned(snapshot.delta_vs_prior, metadata), "vs prior estimate"),
      card("Prior estimate", formatValue(snapshot.prior_estimate_value, metadata), snapshot.as_of_date),
      statusCard(latest),
      card("Schema", `v${latest.schema_version}`, latest.model_version),
      card("Cadence", metadata.update_cadence_label, latest.next_update_date),
      modelNotice(),
      divWithChildren("overview-wide", [
        sectionIntro("Latest news", "Newly incorporated releases for the selected run date."),
        topRows.length
          ? table(["Release", "Impact", "Direction"], topRows.map((row) => [
              row.release_name,
              formatSigned(row.impact, metadata),
              row.direction,
            ]))
          : emptyState("No new releases for this run date."),
      ]),
      divWithChildren("overview-wide", [
        sectionIntro(`${latest.country_name} indicators`, "Latest published values across enabled indicators."),
        table(["Indicator", "Latest", "Reference", "Updated", "Status"], state.overview.map((item) => [
          item.error ? item.indicator.display_name : item.latest.indicator_name,
          item.error ? "unavailable" : formatValue(item.latest.estimate_value, item.metadata),
          item.error ? "n/a" : item.latest.reference_period,
          item.error ? "n/a" : item.latest.as_of_date,
          item.error ? statusBadge("error") : statusBadge(item.latest.model_status),
        ])),
      ]),
    );
  }

  function renderHistory() {
    const selected = selectedSnapshot();
    const rows = state.payload.history.filter((row) => row.reference_period === selected.reference_period);
    elements.panels.history.replaceChildren(
      sectionIntro("Estimate Evolution", state.payload.metadata.explanatory_text),
      renderEstimateChart(rows),
      table(["Run date", "Reference period", "Estimate", "Change"], rows.map((row) => [
        row.as_of_date,
        row.reference_period,
        formatValue(row.estimate_value, state.payload.metadata),
        formatSigned(row.delta_vs_prior, state.payload.metadata),
      ])),
    );
  }

  function renderComparison() {
    const snapshot = selectedSnapshot();
    const prior = priorSnapshot(snapshot);
    if (!prior) {
      elements.panels.comparison.replaceChildren(
        sectionIntro("Run Comparison", "No prior run is available for this reference period."),
        emptyState("Choose a later run date to compare against a prior estimate."),
      );
      return;
    }
    const changedReleases = state.payload.releaseImpacts
      .filter((row) => row.as_of_date === snapshot.as_of_date && row.notes === "new_release")
      .sort((left, right) => Math.abs(Number(right.impact)) - Math.abs(Number(left.impact)));
    const contributionRows = contributionDeltas(snapshot.as_of_date, prior.as_of_date);
    elements.panels.comparison.replaceChildren(
      sectionIntro("Run Comparison", `${snapshot.as_of_date} compared with ${prior.as_of_date}.`),
      divWithChildren("impact-summary", [
        card("Estimate change", formatSigned(Number(snapshot.estimate_value) - Number(prior.estimate_value), state.payload.metadata), "current minus prior"),
        card("Changed releases", String(changedReleases.length), "new rows"),
        card("Contribution movers", String(contributionRows.filter((row) => row.delta !== 0).length), "component deltas"),
      ]),
      table(["Release", "Source", "Impact", "Category"], changedReleases.map((row) => [
        row.release_name,
        sourceCell(row),
        formatSigned(row.impact, state.payload.metadata),
        row.category,
      ])),
      table(["Component", "Prior", "Current", "Delta"], contributionRows.map((row) => [
        row.name,
        formatSigned(row.prior, state.payload.metadata),
        formatSigned(row.current, state.payload.metadata),
        formatSigned(row.delta, state.payload.metadata),
      ])),
    );
  }

  function renderContributions() {
    const rows = state.payload.contributions.filter((row) => row.as_of_date === state.period);
    const allRows = state.payload.contributions.filter((row) => row.reference_period === selectedSnapshot().reference_period);
    elements.panels.contributions.replaceChildren(
      sectionIntro("Drivers", "Component contributions to the selected estimate."),
      renderStackedContributionChart(allRows, state.payload.history),
      renderContributionChangeChart(allRows),
      table(["Component", "Category", "Contribution", "Direction"], rows.map((row) => [
        row.component_name,
        row.category,
        formatSigned(row.contribution, state.payload.metadata),
        row.direction,
      ])),
    );
  }

  function renderEstimateChart(rows) {
    const points = rows.map((row) => ({
      label: row.as_of_date,
      value: Number(row.estimate_value),
    }));
    const chart = createSvgChart("Estimate path", 760, 320);
    const scale = chartScale(points.map((point) => point.value), 0.5);
    drawYAxis(chart, scale);
    const line = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
    line.setAttribute("fill", "none");
    line.setAttribute("stroke", "#2f7d32");
    line.setAttribute("stroke-width", "3");
    line.setAttribute("points", points.map((point, index) => `${xAt(chart, index, points.length)},${yAt(chart, point.value, scale)}`).join(" "));
    chart.plot.append(line);
    for (const [index, point] of points.entries()) {
      drawPoint(chart, xAt(chart, index, points.length), yAt(chart, point.value, scale), "#2f7d32");
      drawXAxisLabel(chart, xAt(chart, index, points.length), point.label);
    }
    return chart.wrapper;
  }

  function renderStackedContributionChart(rows, historyRows) {
    const dates = unique(rows.map((row) => row.as_of_date));
    const components = unique(rows.map((row) => row.component_code));
    const values = rows.map((row) => Number(row.contribution));
    const estimates = historyRows.map((row) => Number(row.estimate_value));
    const scale = chartScale([...values, ...estimates, 0], 0.75);
    const chart = createSvgChart("Subcomponent contribution levels", 900, 360);
    drawYAxis(chart, scale);
    for (const [dateIndex, date] of dates.entries()) {
      const dateRows = rows.filter((row) => row.as_of_date === date);
      let positiveBase = 0;
      let negativeBase = 0;
      for (const component of components) {
        const row = dateRows.find((item) => item.component_code === component);
        if (!row) continue;
        const value = Number(row.contribution);
        const from = value >= 0 ? positiveBase : negativeBase;
        const to = from + value;
        drawStackSegment(chart, dateIndex, dates.length, from, to, scale, colorFor(component));
        if (value >= 0) positiveBase = to;
        else negativeBase = to;
      }
      const estimate = historyRows.find((row) => row.as_of_date === date);
      if (estimate) {
        drawForecastTick(chart, dateIndex, dates.length, Number(estimate.estimate_value), scale);
      }
      drawXAxisLabel(chart, xAt(chart, dateIndex, dates.length), date);
    }
    chart.wrapper.append(legend(components));
    return chart.wrapper;
  }

  function renderContributionChangeChart(rows) {
    const dates = unique(rows.map((row) => row.as_of_date));
    const components = unique(rows.map((row) => row.component_code));
    const changes = [];
    for (let index = 1; index < dates.length; index += 1) {
      for (const component of components) {
        const current = contributionValue(rows, dates[index], component);
        const prior = contributionValue(rows, dates[index - 1], component);
        changes.push({ date: dates[index], component, value: current - prior });
      }
    }
    const scale = chartScale([...changes.map((row) => row.value), 0], 0.4);
    const chart = createSvgChart("Changes in subcomponent contributions", 900, 320);
    drawYAxis(chart, scale);
    const datesWithChanges = dates.slice(1);
    for (const [dateIndex, date] of datesWithChanges.entries()) {
      let positiveBase = 0;
      let negativeBase = 0;
      for (const component of components) {
        const value = changes.find((row) => row.date === date && row.component === component)?.value || 0;
        const from = value >= 0 ? positiveBase : negativeBase;
        const to = from + value;
        drawStackSegment(chart, dateIndex, datesWithChanges.length, from, to, scale, colorFor(component));
        if (value >= 0) positiveBase = to;
        else negativeBase = to;
      }
      drawXAxisLabel(chart, xAt(chart, dateIndex, datesWithChanges.length), date);
    }
    chart.wrapper.append(legend(components));
    return chart.wrapper;
  }

  function renderReleaseImpacts() {
    const rows = state.payload.releaseImpacts
      .filter((row) => row.as_of_date === state.period)
      .sort((left, right) => statusRank(left.notes) - statusRank(right.notes) || Math.abs(Number(right.impact)) - Math.abs(Number(left.impact)));
    const newRows = rows.filter((row) => row.notes === "new_release");
    const newImpact = newRows.reduce((total, row) => total + Number(row.impact), 0);
    const sourceCount = unique(rows.map((row) => row.source).filter(Boolean)).length;
    elements.panels["release-impacts"].replaceChildren(
      sectionIntro("Release Impacts", "Latest source surprises and their estimated effect."),
      renderNewsFlowChart(state.payload.releaseImpacts, state.payload.history),
      divWithChildren("impact-summary", [
        card("New releases", String(newRows.length), state.period),
        card("New-release impact", formatSigned(newImpact, state.payload.metadata), "sum of new rows"),
        card("Sources", String(sourceCount), "selected run"),
        card("Carried forward", String(rows.filter((row) => row.notes === "carried_forward").length), "previous releases"),
        card("Pending", String(rows.filter((row) => row.notes === "pending").length), "not yet released"),
      ]),
      runDownloadLink(rows),
      table(["Date", "Release", "Source", "Actual", "Expected", "Impact", "Status"], rows.map((row) => [
        row.release_date,
        row.release_name,
        sourceCell(row),
        number(row.actual_value, state.payload.metadata.decimals),
        number(row.expected_value, state.payload.metadata.decimals),
        formatSigned(row.impact, state.payload.metadata),
        row.notes,
      ])),
    );
  }

  function runDownloadLink(rows) {
    const wrapper = div("download-inline");
    const link = document.createElement("a");
    const csv = toCsv(rows);
    const blob = new Blob([csv], { type: "text/csv" });
    link.href = URL.createObjectURL(blob);
    link.download = `${state.country.code}_${state.indicator.code}_${state.period}_release_impacts.csv`;
    link.textContent = "Download selected run release impacts";
    wrapper.append(link);
    return wrapper;
  }

  function renderNewsFlowChart(releaseRows, historyRows) {
    const dates = unique(historyRows.map((row) => row.as_of_date));
    const points = dates.map((date) => ({
      label: date,
      value: releaseRows
        .filter((row) => row.as_of_date === date && row.notes === "new_release")
        .reduce((total, row) => total + Number(row.impact), 0),
    }));
    const scale = chartScale([...points.map((point) => point.value), 0], 0.5);
    const chart = createSvgChart("Net new-release impact by run date", 900, 300);
    drawYAxis(chart, scale);
    for (const [index, point] of points.entries()) {
      drawStackSegment(chart, index, points.length, 0, point.value, scale, point.value >= 0 ? "#3b8c7c" : "#b85532");
      drawXAxisLabel(chart, xAt(chart, index, points.length), point.label);
      if (point.label === state.period) {
        drawSelectedRunMarker(chart, index, points.length);
      }
    }
    return chart.wrapper;
  }

  function renderReleaseDates() {
    const rows = state.payload.releaseImpacts
      .filter((row) => row.reference_period === selectedSnapshot().reference_period)
      .sort((left, right) => left.release_date.localeCompare(right.release_date) || statusRank(left.notes) - statusRank(right.notes));
    const grouped = groupBy(rows, "release_date");
    const timeline = div("timeline");
    timeline.replaceChildren(
      ...Object.entries(grouped).map(([releaseDate, items]) => {
        const block = div("timeline-item");
        const title = document.createElement("h3");
        const summary = document.createElement("p");
        title.textContent = releaseDate;
        summary.textContent = items.map((item) => `${item.release_name} (${item.notes})`).join("; ");
        block.append(title, summary);
        return block;
      }),
    );
    elements.panels["release-dates"].replaceChildren(
      sectionIntro("Release Dates", "Source releases used across the selected reference period."),
      timeline,
      table(["Release date", "Release", "Run date", "Status", "Impact"], rows.map((row) => [
        row.release_date,
        row.release_name,
        row.as_of_date,
        row.notes,
        formatSigned(row.impact, state.payload.metadata),
      ])),
    );
  }

  function renderMethodology() {
    elements.panels.methodology.replaceChildren(
      sectionIntro("Methodology", state.payload.metadata.methodology || state.payload.metadata.explanatory_text),
    );
  }

  function renderFaq() {
    const list = document.createElement("dl");
    for (const item of state.payload.metadata.faq || []) {
      const dt = document.createElement("dt");
      const dd = document.createElement("dd");
      dt.textContent = item.question;
      dd.textContent = item.answer;
      list.append(dt, dd);
    }
    elements.panels.faq.replaceChildren(sectionIntro("FAQ", "Common interpretation notes."), list);
  }

  function renderDownloads() {
    const list = document.createElement("ul");
    const files = state.payload.metadata.downloads || [];
    const artifacts = downloadArtifacts(files);
    for (const file of files) {
      const item = document.createElement("li");
      const link = document.createElement("a");
      link.href = `${state.payload.base}/${file}`;
      link.download = file;
      link.textContent = `${state.country.code}/${state.indicator.code}/${file}`;
      item.append(link);
      list.append(item);
    }
    const countryIndex = document.createElement("a");
    countryIndex.href = "data/countries.json";
    countryIndex.download = "countries.json";
    countryIndex.textContent = "countries.json";
    const indexItem = document.createElement("li");
    indexItem.append(countryIndex);
    list.prepend(indexItem);
    elements.panels.downloads.replaceChildren(
      sectionIntro("Downloads", "Static artifacts for this selection and the country index."),
      divWithChildren("download-grid", [
        card("Artifact count", String(files.length + 1), "including country index"),
        card("Rows", String(totalRows()), "CSV records"),
        card("Sources", String(totalSourceCount()), "release-impact source ids"),
        card("Country", state.country.name, state.country.code),
        card("Indicator", state.payload.latest.indicator_name, state.indicator.code),
        card("Schema", `v${state.payload.latest.schema_version}`, state.payload.latest.model_version),
      ]),
      table(["Artifact", "Format", "Rows", "Purpose"], artifacts.map((artifact) => [
        artifactLink(artifact),
        artifact.format,
        artifact.rows,
        artifact.purpose,
      ])),
      diagnosticsPanel(),
      sourceCoveragePanel(),
      provenancePanel(),
      list,
    );
  }

  function downloadArtifacts(files) {
    const rowsByFile = {
      "history.csv": state.payload.history.length,
      "contributions.csv": state.payload.contributions.length,
      "release_impacts.csv": state.payload.releaseImpacts.length,
      "latest.json": 1,
      "metadata.json": 1,
      "model_summary.json": state.payload.extras?.modelSummary ? 1 : "",
      "component_diagnostics.csv": state.payload.extras?.componentDiagnostics?.length ?? "",
      "data_inventory.csv": state.payload.extras?.dataInventory?.length ?? "",
    };
    const purposeByFile = {
      "latest.json": "current snapshot",
      "history.csv": "estimate path",
      "contributions.csv": "driver chart",
      "release_impacts.csv": "news table",
      "metadata.json": "labels and methodology",
      "model_summary.json": "model diagnostics",
      "component_diagnostics.csv": "component fit diagnostics",
      "data_inventory.csv": "source freshness inventory",
    };
    const rootArtifacts = [
      { file: "countries.json", path: "data/countries.json", format: "json", rows: state.countries.length, purpose: "country index" },
    ];
    if (state.sourceCoverage) {
      rootArtifacts.push({ file: "source_coverage.json", path: "data/source_coverage.json", format: "json", rows: sourceCoverageRows(), purpose: "data-store coverage" });
    }
    return [
      ...rootArtifacts,
      ...files.map((file) => ({
        file,
        path: `${state.payload.base}/${file}`,
        format: file.split(".").at(-1),
        rows: rowsByFile[file] ?? "",
        purpose: purposeByFile[file] ?? "published artifact",
      })),
    ];
  }

  function artifactLink(artifact) {
    const link = document.createElement("a");
    link.href = artifact.path;
    link.download = artifact.file;
    link.textContent = artifact.file;
    return link;
  }

  function diagnosticsPanel() {
    const diagnostics = state.payload.extras || {};
    if (!diagnostics.modelSummary && !diagnostics.componentDiagnostics?.length && !diagnostics.dataInventory?.length) {
      return emptyState("Model diagnostics are not published for this selection.");
    }
    const summary = diagnostics.modelSummary || {};
    const components = diagnostics.componentDiagnostics || [];
    const inventory = diagnostics.dataInventory || [];
    const pending = inventory.filter((row) => row.target_quarter_status === "pending");
    const released = inventory.filter((row) => row.target_quarter_status === "released");
    const worstFit = [...components].sort((left, right) => Number(right.training_rmse || 0) - Number(left.training_rmse || 0)).slice(0, 5);
    const staleInputs = [...inventory].sort((left, right) => left.latest_observation_date.localeCompare(right.latest_observation_date)).slice(0, 8);
    return divWithChildren("diagnostics-panel", [
      sectionIntro("Model Diagnostics", "Published run diagnostics for this model-backed output."),
      divWithChildren("download-grid", [
        card("Model run", summary.model || state.payload.latest.model_version, summary.latest_as_of_date || state.payload.latest.as_of_date),
        card("Training window", `${summary.training_start || "n/a"} to ${summary.training_end || "n/a"}`, `${summary.training_rows || "n/a"} rows`),
        card("Components", String(components.length), "component bridges"),
        card("Inventory", String(inventory.length), `${released.length} released, ${pending.length} pending`),
      ]),
      components.length
        ? table(["Component", "RMSE", "MAE", "Latest contribution", "Status"], worstFit.map((row) => [
            row.component_name,
            number(row.training_rmse, 2),
            number(row.training_mae, 2),
            formatSigned(row.latest_contribution, state.payload.metadata),
            row.latest_release_status,
          ]))
        : emptyState("Component diagnostics are unavailable."),
      inventory.length
        ? table(["Series", "Role", "Frequency", "Latest observation", "Target-quarter status"], staleInputs.map((row) => [
            row.series_id,
            row.role,
            row.frequency,
            row.latest_observation_date,
            row.target_quarter_status,
          ]))
        : emptyState("Data inventory is unavailable."),
    ]);
  }

  function provenancePanel() {
    const latest = state.payload.latest;
    const section = div("provenance-panel");
    section.replaceChildren(
      card("Last updated", latest.last_updated_utc, latest.as_of_date),
      card("Site build", siteBuildTime(), "manifest"),
      card("Reference period", latest.reference_period, latest.unit),
      card("Model", latest.model_version, latest.model_status),
      card("Top source", topSourceLabel(), "largest absolute impact"),
    );
    return section;
  }

  function sourceCoveragePanel() {
    if (!state.sourceCoverage) {
      return emptyState("Source coverage is unavailable for this build.");
    }
    const selected = state.sourceCoverage.countries?.find((country) => country.code === state.country.code);
    const processed = state.sourceCoverage.processed || [];
    const statusCounts = state.sourceCoverage.status_counts || {};
    return divWithChildren("source-coverage-panel", [
      sectionIntro("Data Store Coverage", "Upstream macro series available to the model pipeline."),
      divWithChildren("download-grid", [
        card("Store refresh", state.sourceCoverage.store_last_full_update || "unavailable", "data manifest"),
        card("Manifest series", String(state.sourceCoverage.series_count || 0), `${statusCounts.OK || 0} OK`),
        card("Selected country", selected ? `${selected.ok_count}/${selected.series_count}` : "n/a", "OK series"),
        card("Processed columns", String(processed.reduce((total, row) => total + Number(row.columns || 0), 0)), "all frequencies"),
      ]),
      table(["Frequency", "Rows", "Columns", "Range"], processed.map((row) => [
        row.frequency,
        String(row.rows),
        String(row.columns),
        `${row.start || "n/a"} to ${row.end || "n/a"}`,
      ])),
      selected
        ? table(["Series", "Rows", "Status", "Source"], selected.top_series.map((row) => [
            row.local_id,
            String(row.rows),
            statusBadge(row.status.toLowerCase()),
            row.source,
          ]))
        : emptyState("No country-level source coverage matched this selection."),
    ]);
  }

  function statusText(snapshot, latest) {
    const build = siteBuildTime();
    const extra = build === "unavailable" ? "" : ` Site build ${build}.`;
    const model = modelNoticeText();
    const modelText = model ? ` ${model}` : "";
    return `Selected run ${snapshot.as_of_date}. Latest update ${latest.as_of_date}. Next update ${latest.next_update_date}.${extra}${modelText}`;
  }

  function siteBuildTime() {
    return state.manifest?.generated_at_utc || "unavailable";
  }

  function totalRows() {
    return state.payload.history.length + state.payload.contributions.length + state.payload.releaseImpacts.length;
  }

  function totalSourceCount() {
    return unique(state.payload.releaseImpacts.map((row) => row.source).filter(Boolean)).length;
  }

  function sourceCoverageRows() {
    if (!state.sourceCoverage) return "";
    return state.sourceCoverage.series_count || "";
  }

  function topSourceLabel() {
    const rows = [...state.payload.releaseImpacts].sort((left, right) => Math.abs(Number(right.impact)) - Math.abs(Number(left.impact)));
    if (!rows.length) return "n/a";
    return rows[0].source || rows[0].release_name;
  }

  function validatePayload(payload, countryCode, indicatorCode) {
    const errors = [];
    requireFields(errors, "latest.json", payload.latest, [
      "schema_version",
      "country_code",
      "indicator_code",
      "as_of_date",
      "next_update_date",
      "estimate_value",
      "unit",
      "model_status",
      "model_version",
      "last_updated_utc",
    ]);
    requireFields(errors, "metadata.json", payload.metadata, [
      "country_code",
      "indicator_code",
      "display_name",
      "unit",
      "decimals",
      "update_cadence_label",
    ]);
    requireColumns(errors, "history.csv", payload.history, [
      "as_of_date",
      "reference_period",
      "estimate_value",
      "model_status",
      "model_version",
    ]);
    requireColumns(errors, "contributions.csv", payload.contributions, [
      "as_of_date",
      "component_code",
      "component_name",
      "contribution",
      "direction",
      "unit",
    ]);
    requireColumns(errors, "release_impacts.csv", payload.releaseImpacts, [
      "latest_as_of_date",
      "prior_as_of_date",
      "as_of_date",
      "release_date",
      "release_name",
      "impact",
      "notes",
      "source",
      "source_url",
    ]);
    if (payload.latest.schema_version !== state.schemaVersion) {
      errors.push(`latest.json schema_version must be ${state.schemaVersion}`);
    }
    if (payload.latest.country_code !== countryCode || payload.metadata.country_code !== countryCode) {
      errors.push(`payload country_code must match ${countryCode}`);
    }
    if (payload.latest.indicator_code !== indicatorCode || payload.metadata.indicator_code !== indicatorCode) {
      errors.push(`payload indicator_code must match ${indicatorCode}`);
    }
    if (!isIsoDate(payload.latest.as_of_date) || !isIsoDate(payload.latest.next_update_date)) {
      errors.push("latest.json dates must use YYYY-MM-DD");
    }
    if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(payload.latest.last_updated_utc || "")) {
      errors.push("last_updated_utc must use YYYY-MM-DDTHH:MM:SSZ");
    }
    if (errors.length) {
      throw new Error(errors.join("; "));
    }
  }

  function requireFields(errors, label, payload, fields) {
    for (const field of fields) {
      if (!Object.hasOwn(payload, field)) {
        errors.push(`${label} missing ${field}`);
      }
    }
  }

  function requireColumns(errors, label, rows, columns) {
    if (!rows.length) {
      errors.push(`${label} must contain at least one row`);
      return;
    }
    for (const column of columns) {
      if (!Object.hasOwn(rows[0], column)) {
        errors.push(`${label} missing ${column}`);
      }
    }
  }

  function selectedSnapshot() {
    return state.payload.history.find((row) => row.as_of_date === state.period) || state.payload.history.at(-1);
  }

  function priorSnapshot(snapshot) {
    const rows = state.payload.history.filter((row) => row.reference_period === snapshot.reference_period);
    const index = rows.findIndex((row) => row.as_of_date === snapshot.as_of_date);
    return index > 0 ? rows[index - 1] : null;
  }

  function contributionDeltas(currentDate, priorDate) {
    const currentRows = state.payload.contributions.filter((row) => row.as_of_date === currentDate);
    const priorRows = state.payload.contributions.filter((row) => row.as_of_date === priorDate);
    const components = unique([...currentRows, ...priorRows].map((row) => row.component_code));
    return components.map((component) => {
      const current = contributionValue(state.payload.contributions, currentDate, component);
      const prior = contributionValue(state.payload.contributions, priorDate, component);
      return {
        component,
        name: labelForComponent(component),
        current,
        prior,
        delta: current - prior,
      };
    }).sort((left, right) => Math.abs(right.delta) - Math.abs(left.delta));
  }

  function createSvgChart(title, width, height) {
    const wrapper = div("chart-card");
    const heading = document.createElement("h3");
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    const plot = document.createElementNS("http://www.w3.org/2000/svg", "g");
    heading.textContent = title;
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", title);
    plot.setAttribute("transform", "translate(64 24)");
    svg.append(plot);
    wrapper.append(heading, svg);
    return {
      wrapper,
      svg,
      plot,
      width,
      height,
      innerWidth: width - 96,
      innerHeight: height - 82,
      top: 24,
      left: 64,
    };
  }

  function chartScale(values, pad) {
    const min = Math.min(...values);
    const max = Math.max(...values);
    const padding = Math.max(max - min, 1) * pad;
    return {
      min: Math.min(0, min - padding),
      max: Math.max(0, max + padding),
    };
  }

  function xAt(chart, index, count) {
    if (count <= 1) return chart.left + chart.innerWidth / 2;
    return chart.left + (index / (count - 1)) * chart.innerWidth;
  }

  function yAt(chart, value, scale) {
    return chart.top + ((scale.max - value) / (scale.max - scale.min)) * chart.innerHeight;
  }

  function drawYAxis(chart, scale) {
    const axis = document.createElementNS("http://www.w3.org/2000/svg", "line");
    axis.setAttribute("x1", "64");
    axis.setAttribute("x2", chart.left + chart.innerWidth);
    axis.setAttribute("y1", yAt(chart, 0, scale));
    axis.setAttribute("y2", yAt(chart, 0, scale));
    axis.setAttribute("class", "zero-axis");
    chart.svg.append(axis);
    for (const value of [scale.min, 0, scale.max]) {
      const y = yAt(chart, value, scale);
      const grid = document.createElementNS("http://www.w3.org/2000/svg", "line");
      const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
      grid.setAttribute("x1", chart.left);
      grid.setAttribute("x2", chart.left + chart.innerWidth);
      grid.setAttribute("y1", y);
      grid.setAttribute("y2", y);
      grid.setAttribute("class", "grid-line");
      label.setAttribute("x", chart.left - 12);
      label.setAttribute("y", y + 4);
      label.setAttribute("text-anchor", "end");
      label.setAttribute("class", "axis-label");
      label.textContent = Number(value).toFixed(1);
      chart.svg.append(grid, label);
    }
  }

  function drawStackSegment(chart, index, count, from, to, scale, color) {
    const center = xAt(chart, index, count);
    const width = Math.min(42, Math.max(20, 520 / Math.max(count, 1)));
    const y1 = yAt(chart, from, scale);
    const y2 = yAt(chart, to, scale);
    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("x", center - width / 2);
    rect.setAttribute("y", Math.min(y1, y2));
    rect.setAttribute("width", width);
    rect.setAttribute("height", Math.max(Math.abs(y2 - y1), 1));
    rect.setAttribute("fill", color);
    chart.svg.append(rect);
  }

  function drawForecastTick(chart, index, count, value, scale) {
    const center = xAt(chart, index, count);
    const y = yAt(chart, value, scale);
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", center - 26);
    line.setAttribute("x2", center + 26);
    line.setAttribute("y1", y);
    line.setAttribute("y2", y);
    line.setAttribute("class", "forecast-line");
    chart.svg.append(line);
  }

  function drawSelectedRunMarker(chart, index, count) {
    const x = xAt(chart, index, count);
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", x);
    line.setAttribute("x2", x);
    line.setAttribute("y1", "22");
    line.setAttribute("y2", chart.height - 54);
    line.setAttribute("class", "selected-run-line");
    chart.svg.append(line);
  }

  function drawPoint(chart, x, y, color) {
    const point = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    point.setAttribute("cx", x);
    point.setAttribute("cy", y);
    point.setAttribute("r", "4");
    point.setAttribute("fill", color);
    chart.svg.append(point);
  }

  function drawXAxisLabel(chart, x, text) {
    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", x);
    label.setAttribute("y", chart.height - 24);
    label.setAttribute("text-anchor", "end");
    label.setAttribute("transform", `rotate(-38 ${x} ${chart.height - 24})`);
    label.setAttribute("class", "axis-label");
    label.textContent = text;
    chart.svg.append(label);
  }

  function contributionValue(rows, date, component) {
    const row = rows.find((item) => item.as_of_date === date && item.component_code === component);
    return row ? Number(row.contribution) : 0;
  }

  function legend(components) {
    const wrapper = div("legend");
    wrapper.replaceChildren(
      ...components.map((component) => {
        const item = div("legend-item");
        const swatch = div("legend-swatch");
        swatch.style.backgroundColor = colorFor(component);
        item.append(swatch, spanText(labelForComponent(component)));
        return item;
      }),
    );
    return wrapper;
  }

  function colorFor(component) {
    const colors = {
      dspic96: "#4c9ac3",
      houst: "#6aa84f",
      indpro: "#d6a700",
      payems: "#c75a23",
      rsafs: "#5bb8c7",
      consumption: "#4c9ac3",
      investment: "#6aa84f",
      trade: "#d6a700",
      goods: "#4c9ac3",
      services: "#6aa84f",
      energy: "#c75a23",
      goods_trade: "#4c9ac3",
      services_trade: "#6aa84f",
      prices: "#d6a700",
    };
    return colors[component] || "#8a6bb8";
  }

  function labelForComponent(component) {
    const row = state.payload.contributions.find((item) => item.component_code === component);
    return row ? row.component_name : component;
  }

  function card(label, value, detail) {
    const article = document.createElement("article");
    const h2 = document.createElement("h2");
    const strong = document.createElement("strong");
    const p = document.createElement("p");
    h2.textContent = label;
    strong.textContent = value;
    p.textContent = detail;
    article.append(h2, strong, p);
    return article;
  }

  function statusCard(latest) {
    const article = card("Status", latest.model_status, statusDetail(latest));
    article.classList.add(`model-status-${latest.model_status}`);
    return article;
  }

  function statusDetail(latest) {
    if (isExperimentalTracker()) {
      return "Data-backed experimental tracker";
    }
    if (latest.model_status === "sample") {
      return "Sample scaffold output";
    }
    if (latest.model_status === "stale") {
      return `Stale output, updated ${latest.last_updated_utc}`;
    }
    if (latest.model_status === "error") {
      return `Error output, updated ${latest.last_updated_utc}`;
    }
    return `Updated ${latest.last_updated_utc}`;
  }

  function modelNotice() {
    const text = modelNoticeText();
    if (!text) {
      return document.createDocumentFragment();
    }
    const notice = div("model-notice overview-wide");
    const title = document.createElement("strong");
    const detail = document.createElement("p");
    title.textContent = "Data-backed experimental tracker";
    detail.textContent = text;
    notice.append(title, detail);
    return notice;
  }

  function modelNoticeText() {
    if (isExperimentalTracker()) {
      return "This page uses real source data with transparent fixed weights. Treat the estimate as an experimental tracking proxy until a full indicator model is added.";
    }
    if (state.payload.latest.model_status === "sample") {
      return "This page is sample scaffold output and is not yet connected to a data-backed indicator model.";
    }
    return "";
  }

  function isExperimentalTracker() {
    return state.payload.latest.model_status === "warning" && state.payload.latest.model_version.startsWith("tracking-");
  }

  function statusBadge(status) {
    const badge = document.createElement("span");
    badge.className = `model-status-badge model-status-badge-${status}`;
    badge.textContent = status;
    return badge;
  }

  function sectionIntro(title, text) {
    const wrapper = div("section-heading");
    const h2 = document.createElement("h2");
    const p = document.createElement("p");
    h2.textContent = title;
    p.textContent = text;
    wrapper.append(h2, p);
    return wrapper;
  }

  function table(headers, rows) {
    const wrap = div("table-wrap");
    const output = document.createElement("table");
    const thead = document.createElement("thead");
    const tbody = document.createElement("tbody");
    const headRow = document.createElement("tr");
    headRow.replaceChildren(...headers.map((header) => headerCell(header)));
    thead.append(headRow);
    if (!rows.length) {
      wrap.append(emptyState("No records available for this selection."));
      return wrap;
    }
    tbody.replaceChildren(...rows.map((row) => {
      const tr = document.createElement("tr");
      tr.replaceChildren(...row.map((value) => cell(value)));
      return tr;
    }));
    output.append(thead, tbody);
    wrap.append(output);
    return wrap;
  }

  function emptyState(message) {
    const item = div("empty-state");
    item.textContent = message;
    return item;
  }

  async function fetchJson(path) {
    const response = await fetch(path, { cache: "no-store" });
    if (!response.ok) throw new Error(`Could not load ${path}`);
    return response.json();
  }

  async function fetchOptionalJson(path) {
    const response = await fetch(path, { cache: "no-store" });
    if (!response.ok) return null;
    return response.json();
  }

  async function fetchText(path) {
    const response = await fetch(path, { cache: "no-store" });
    if (!response.ok) throw new Error(`Could not load ${path}`);
    return response.text();
  }

  async function loadOptionalArtifacts(base, downloads) {
    const extras = {};
    if (downloads.includes("model_summary.json")) {
      extras.modelSummary = await fetchOptionalJson(`${base}/model_summary.json`);
    }
    if (downloads.includes("component_diagnostics.csv")) {
      const text = await fetchOptionalText(`${base}/component_diagnostics.csv`);
      extras.componentDiagnostics = text ? parseCsv(text) : [];
    }
    if (downloads.includes("data_inventory.csv")) {
      const text = await fetchOptionalText(`${base}/data_inventory.csv`);
      extras.dataInventory = text ? parseCsv(text) : [];
    }
    return extras;
  }

  async function fetchOptionalText(path) {
    const response = await fetch(path, { cache: "no-store" });
    if (!response.ok) return "";
    return response.text();
  }

  function parseCsv(text) {
    const lines = text.trim().split(/\r?\n/);
    const headers = splitCsvLine(lines.shift());
    return lines.map((line) => Object.fromEntries(headers.map((header, index) => [header, splitCsvLine(line)[index] ?? ""])));
  }

  function splitCsvLine(line) {
    const values = [];
    let current = "";
    let quoted = false;
    for (let index = 0; index < line.length; index += 1) {
      const char = line[index];
      if (char === '"' && line[index + 1] === '"') {
        current += '"';
        index += 1;
      } else if (char === '"') {
        quoted = !quoted;
      } else if (char === "," && !quoted) {
        values.push(current);
        current = "";
      } else {
        current += char;
      }
    }
    values.push(current);
    return values;
  }

  function toCsv(rows) {
    if (!rows.length) return "";
    const headers = Object.keys(rows[0]);
    const body = rows.map((row) => headers.map((header) => csvCell(row[header])).join(","));
    return [headers.join(","), ...body].join("\n") + "\n";
  }

  function csvCell(value) {
    const text = String(value ?? "");
    if (/[",\n]/.test(text)) return `"${text.replaceAll('"', '""')}"`;
    return text;
  }

  function option(value, label) {
    const item = document.createElement("option");
    item.value = value;
    item.textContent = label;
    return item;
  }

  function dateLabel(date) {
    const snapshot = state.payload?.history.find((row) => row.as_of_date === date);
    if (!snapshot) return date;
    return `${date} (${number(snapshot.estimate_value, state.payload.metadata.decimals)})`;
  }

  function div(className) {
    const item = document.createElement("div");
    item.className = className;
    return item;
  }

  function divWithChildren(className, children) {
    const item = div(className);
    item.replaceChildren(...children);
    return item;
  }

  function spanText(text) {
    const item = document.createElement("span");
    item.textContent = text;
    return item;
  }

  function headerCell(value) {
    const th = document.createElement("th");
    th.textContent = value;
    return th;
  }

  function cell(value) {
    const td = document.createElement("td");
    if (value instanceof Node) {
      td.append(value);
    } else if (["ok", "sample", "warning", "error", "stale"].includes(value)) {
      td.append(statusBadge(value));
    } else if (["new_release", "carried_forward", "pending"].includes(value)) {
      const badge = document.createElement("span");
      badge.className = `status-badge ${value}`;
      badge.textContent = value.replace("_", " ");
      td.append(badge);
    } else {
      td.textContent = value;
    }
    return td;
  }

  function sourceCell(row) {
    const text = row.source || "n/a";
    if (!row.source_url) {
      return spanText(text);
    }
    const link = document.createElement("a");
    link.href = row.source_url;
    link.textContent = text;
    link.rel = "noreferrer";
    return link;
  }

  function unique(values) {
    return [...new Set(values)];
  }

  function groupBy(rows, field) {
    return rows.reduce((groups, row) => {
      groups[row[field]] = groups[row[field]] || [];
      groups[row[field]].push(row);
      return groups;
    }, {});
  }

  function formatValue(value, metadata) {
    if (value === null || value === "") return "n/a";
    return `${number(value, metadata.decimals)} ${metadata.unit}`;
  }

  function formatSigned(value, metadata) {
    if (value === null || value === "") return "n/a";
    const amount = Number(value);
    return `${amount >= 0 ? "+" : ""}${number(amount, metadata.decimals)}`;
  }

  function number(value, decimals) {
    return Number(value).toFixed(Number(decimals));
  }

  function isIsoDate(value) {
    return /^\d{4}-\d{2}-\d{2}$/.test(value || "");
  }

  function statusRank(status) {
    return { new_release: 0, carried_forward: 1, pending: 2 }[status] ?? 3;
  }

  function readUrlState() {
    const params = new URLSearchParams(window.location.search);
    return {
      country: params.get("country"),
      indicator: params.get("indicator"),
      run: params.get("run"),
    };
  }

  function writeUrlState() {
    const params = new URLSearchParams();
    params.set("country", state.country.code);
    params.set("indicator", state.indicator.code);
    params.set("run", state.period);
    window.history.replaceState(null, "", `${window.location.pathname}?${params.toString()}`);
  }
})();
