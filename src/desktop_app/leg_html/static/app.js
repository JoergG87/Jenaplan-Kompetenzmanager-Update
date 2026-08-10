"use strict";

(function () {
  const startedAt = performance.now();
  const app = document.getElementById("app");
  const loading = document.getElementById("loading");
  const liveStatus = document.getElementById("live-status");
  const navigationSamples = [];
  let bridge = null;
  let state = null;
  let activePhase = "goal";
  let evidenceBuilt = false;
  let evidenceState = null;
  let pendingCalls = 0;
  let savePending = false;
  let completionPending = false;
  window.__jkmLegDirty = false;
  window.__jkmLegPendingCalls = 0;

  window.__jkmLegMetrics = {
    firstUsableMs: null,
    navigationSamples: navigationSamples,
    evidenceBuildMs: null,
  };

  new QWebChannel(qt.webChannelTransport, function (channel) {
    bridge = channel.objects.legBridge;
    bridge.stateChanged.connect(function (payload) {
      state = parsePayload(payload);
      window.__jkmLegState = state;
      refreshChrome();
    });
    bridge.operationFinished.connect(function (payload) {
      const result = parsePayload(payload);
      if (!result.ok && result.phase_key) activatePhase(result.phase_key);
      announce(result.ok ? visibleResult(result.code) : visibleError(result), !result.ok);
      if (result.ok && result.code === "conference_completed") {
        rebuildPhase("agreements");
      }
    });
    bridge.initialState(function (payload) {
      state = parsePayload(payload);
      window.__jkmLegState = state;
      renderWorkspace();
      loading.hidden = true;
      app.hidden = false;
      window.__jkmLegMetrics.firstUsableMs = performance.now() - startedAt;
    });
  });

  const phases = [
    { key: "goal", label: "Gesprächsziel", render: goalPhase },
    { key: "strengths", label: "Was gelingt dem Kind?", render: strengthsPhase },
    { key: "development", label: "Welche Entwicklung sehen wir?", render: developmentPhase },
    { key: "goals", label: "Woran möchten wir gemeinsam arbeiten?", render: goalsPhase },
    { key: "evidence", label: "Welche Beispiele stützen unsere Einschätzung?", render: evidencePhase },
    { key: "agreements", label: "Welche Unterstützung und Vereinbarungen treffen wir?", render: agreementsPhase },
  ];

  function renderWorkspace() {
    app.replaceChildren();
    const workspace = node("div", { className: "workspace" });
    workspace.append(header());
    workspace.append(navigation());
    const stage = node("main", { className: "main-stage", id: "main-stage" });
    phases.forEach(function (phase, index) {
      const panel = node("section", {
        className: "phase",
        id: `phase-${phase.key}`,
        role: "region",
        "aria-labelledby": `nav-${phase.key}`,
      });
      panel.dataset.phase = phase.key;
      panel.hidden = index !== 0;
      if (phase.key === "evidence") {
        panel.append(empty("Kompetenzen und Belege werden beim ersten Öffnen aufgebaut."));
      } else {
        panel.append(phase.render());
      }
      stage.append(panel);
    });
    workspace.append(stage);
    workspace.append(actionBar());
    app.append(workspace);
  }

  function header() {
    const wrapper = node("header", { className: "context-header" });
    const copy = node("div");
    copy.append(node("p", { className: "eyebrow", textContent: "LERNENTWICKLUNGSGESPRÄCH" }));
    copy.append(node("h1", { textContent: "Gespräch in sechs Phasen" }));
    copy.append(node("p", {
      id: "student-context",
      textContent: studentContext(),
    }));
    wrapper.append(copy);
    const meta = node("div", { className: "header-meta" });
    meta.append(badge("Bearbeitbarer Entwurf", "info"));
    meta.append(badge(state.dirty ? "Ungespeicherte Änderungen" : "Entwurf gespeichert", state.dirty ? "warning" : "success", "dirty-badge"));
    wrapper.append(meta);
    return wrapper;
  }

  function navigation() {
    const nav = node("nav", { className: "side-nav", "aria-label": "LEG-Phasen" });
    nav.append(node("p", { className: "eyebrow", textContent: "GESPRÄCHSPHASEN" }));
    phases.forEach(function (phase, index) {
      const button = node("button", {
        className: "nav-button",
        id: `nav-${phase.key}`,
        type: "button",
        textContent: `${index + 1}. ${phase.label}`,
      });
      button.dataset.phaseTarget = phase.key;
      if (index === 0) button.setAttribute("aria-current", "page");
      button.addEventListener("click", function () { activatePhase(phase.key); });
      nav.append(button);
    });
    return nav;
  }

  function activatePhase(key) {
    const started = performance.now();
    const target = app.querySelector(`[data-phase="${cssSafe(key)}"]`);
    if (!target || key === activePhase) return;
    app.querySelectorAll("[data-phase]").forEach(function (phase) {
      phase.hidden = phase !== target;
    });
    app.querySelectorAll("[data-phase-target]").forEach(function (button) {
      if (button.dataset.phaseTarget === key) button.setAttribute("aria-current", "page");
      else button.removeAttribute("aria-current");
    });
    activePhase = key;
    if (key === "evidence" && !evidenceBuilt) {
      const buildStarted = performance.now();
      target.replaceChildren(empty("Kompetenzen und Belege werden vorbereitet …"));
      callBridge("loadEvidenceState", [], function (result) {
        if (!result || !Array.isArray(result.subjects)) return;
        evidenceState = result;
        target.replaceChildren(evidencePhase());
        evidenceBuilt = true;
        applyEvidenceFilters("");
        updateEvidenceWarning();
        window.__jkmLegMetrics.evidenceBuildMs = performance.now() - buildStarted;
      }, true);
    } else if (key === "agreements") {
      target.replaceChildren(agreementsPhase());
    }
    navigationSamples.push(performance.now() - started);
    const heading = target.querySelector("h2");
    if (heading) {
      heading.setAttribute("tabindex", "-1");
      heading.focus({ preventScroll: true });
    }
  }
  window.__jkmLegActivatePhase = activatePhase;

  function rebuildPhase(key) {
    const target = app.querySelector(`[data-phase="${cssSafe(key)}"]`);
    const phase = phases.find(function (item) { return item.key === key; });
    if (target && phase) target.replaceChildren(phase.render());
  }

  function goalPhase() {
    const root = phaseIntro("Gesprächsziel", "Rahmen und Schwerpunkte für das Lernentwicklungsgespräch.");
    const dates = node("div", { className: "field-grid" });
    dates.append(field("Zeitraum von", dateInput(state.draft.period_start, function (value) { updateDate("period_start", value); })));
    dates.append(field("Zeitraum bis", dateInput(state.draft.period_end, function (value) { updateDate("period_end", value); })));
    dates.append(field("Gesprächsdatum", dateInput(state.draft.conference_date, function (value) { updateDate("conference_date", value); })));
    dates.append(field("Verantwortliche Lehrkraft", textInput(state.draft.responsible_teacher, function (value) { updateText("responsible_teacher", value); })));
    root.append(card("Gesprächsrahmen", dates));
    const focus = node("div", { className: "selection-grid" });
    const selectedSubjects = new Set(state.draft.subject_ids);
    state.preparation.subjects.forEach(function (subject) {
      focus.append(checkRow(subject.subject_name, "Fachbereich", selectedSubjects.has(subject.subject_id), function (checked) {
        updateTuple("subject_ids", subject.subject_id, checked);
        callBridge("setSelection", ["subject", subject.subject_id, checked]);
        if (evidenceBuilt) applyEvidenceFilters(searchValue());
      }));
    });
    const selectedTopics = new Set(state.draft.cross_topic_keys);
    state.preparation.cross_topics.forEach(function (topic) {
      focus.append(checkRow(topic.label, "Übergreifendes Gesprächsthema", selectedTopics.has(topic.cross_topic_key), function (checked) {
        updateTuple("cross_topic_keys", topic.cross_topic_key, checked);
        callBridge("setSelection", ["cross_topic", topic.cross_topic_key, checked]);
      }));
    });
    root.append(card("Gesprächsschwerpunkte", focus));
    root.append(field("Gesprächseinstieg", textArea(state.draft.conversation_entry_text, function (value) { updateText("conversation_entry_text", value); })));
    return root;
  }

  function strengthsPhase() {
    const root = phaseIntro("Was gelingt dem Kind?", "Vorbereitung und Kinderperspektive bleiben getrennt sichtbar.");
    root.append(field("Stärken und Lehrkraftsicht", textArea(state.draft.strengths_text, function (value) { updateText("strengths_text", value); })));
    root.append(field("Rückblick des Kindes", textArea(state.draft.child_retrospective_text, function (value) { updateText("child_retrospective_text", value); })));
    root.append(evidenceSummary(false));
    return root;
  }

  function developmentPhase() {
    const root = phaseIntro("Welche Entwicklung sehen wir?", "Es findet keine automatische Interpretation oder Zielformulierung statt.");
    root.append(field("Sicht der Lehrkraft", textArea(state.draft.teacher_perspective_text, function (value) { updateText("teacher_perspective_text", value); })));
    root.append(field("Gemeinsam betrachtete Entwicklungsfelder", textArea(state.draft.development_fields_text, function (value) { updateText("development_fields_text", value); })));
    root.append(evidenceSummary(false));
    return root;
  }

  function goalsPhase() {
    const root = phaseIntro("Woran möchten wir gemeinsam arbeiten?", "Vorbereitete Inhalte werden nicht automatisch zu Vereinbarungen.");
    root.append(field("Vorbereitete Zielideen", textArea(state.draft.prepared_goals_text, function (value) { updateText("prepared_goals_text", value); })));
    root.append(field("Gemeinsam formulierte Ziele", textArea(state.draft.agreed_goals_text, function (value) { updateText("agreed_goals_text", value); })));
    root.append(evidenceSummary(false));
    return root;
  }

  function evidencePhase() {
    const root = phaseIntro("Welche Beispiele stützen unsere Einschätzung?", "Die kanonische Hierarchie wird beim ersten Öffnen aufgebaut und danach wiederverwendet.");
    if (!evidenceState) return root;
    const search = textInput("", function (value) { applyEvidenceFilters(value); });
    search.type = "search";
    search.id = "evidence-search";
    search.setAttribute("aria-label", "Kompetenzen und Belege durchsuchen");
    root.append(field("Kompetenzen und Belege durchsuchen", search));
    const competencyHost = node("div", { id: "competency-host" });
    const selectedCompetencies = new Set(state.draft.competency_ids);
    evidenceState.subjects.forEach(function (subject) {
      const subjectDetails = disclosure(subject.subject_name);
      subjectDetails.element.dataset.subjectId = subject.subject_id;
      const areas = grouped(subject.competencies, "learning_area");
      areas.forEach(function (area) {
        const areaDetails = disclosure(area.label || "Kompetenzbereich");
        grouped(area.items, "competency_group").forEach(function (topic) {
          const topicDetails = disclosure(topic.label || "Thema");
          topic.items.forEach(function (item) {
            const selected = selectedCompetencies.has(item.competency_id);
            const status = [item.documentation_state, item.observed_proposal, item.confirmed_rating].filter(Boolean).join(" · ");
            const row = checkRow(item.competency_text, status || "Noch kein dokumentierter Stand", selected, function (checked) {
              updateTuple("competency_ids", item.competency_id, checked);
              callBridge("setSelection", ["competency", item.competency_id, checked]);
              applyEvidenceFilters(search.value);
            }, !item.selectable && !selected);
            row.dataset.competencyId = item.competency_id;
            row.dataset.subjectId = subject.subject_id;
            row.dataset.searchText = [subject.subject_name, item.learning_area, item.competency_group, item.competency_text].join(" ").toLocaleLowerCase("de");
            row.dataset.observationDates = JSON.stringify(item.observation_dates || []);
            row.dataset.currentConfirmation = item.has_current_confirmation ? "true" : "false";
            if (item.historical || !item.selectable) row.append(node("small", { className: "historical-note", textContent: "Historischer Bezug – nicht neu auswählbar." }));
            topicDetails.body.append(row);
          });
          areaDetails.body.append(topicDetails.element);
        });
        subjectDetails.body.append(areaDetails.element);
      });
      competencyHost.append(subjectDetails.element);
    });
    root.append(competencyHost);
    const evidenceDetails = disclosure(`Beobachtungsbelege · ${evidenceState.evidence.length}`);
    evidenceDetails.element.id = "evidence-list";
    const selectedEvidence = new Set(state.draft.observation_ids);
    evidenceState.evidence.forEach(function (item) {
      const row = checkRow(item.note || "Beobachtung", [item.date_text, item.subject_name, item.context, item.is_quick_observation ? "Nur als Textbeleg" : ""].filter(Boolean).join(" · "), selectedEvidence.has(item.observation_id), function (checked) {
        updateTuple("observation_ids", item.observation_id, checked);
        callBridge("setSelection", ["observation", item.observation_id, checked]);
        updateEvidenceWarning();
      });
      row.dataset.observationId = item.observation_id;
      row.dataset.subjectName = item.subject_name;
      row.dataset.competencyIds = JSON.stringify(item.competency_ids || []);
      row.dataset.searchText = [item.date_text, item.subject_name, item.context, item.note].join(" ").toLocaleLowerCase("de");
      evidenceDetails.body.append(row);
    });
    (evidenceState.unavailable_observation_ids || []).forEach(function (observationId) {
      const row = checkRow("Beleg nicht mehr verfügbar", "Der gespeicherte Bezug bleibt erhalten, bis du ihn bewusst abwählst.", state.draft.observation_ids.includes(observationId), function (checked) {
        updateTuple("observation_ids", observationId, checked);
        callBridge("setSelection", ["observation", observationId, checked]);
        updateEvidenceWarning();
      });
      row.dataset.unavailable = "true";
      row.dataset.observationId = observationId;
      row.dataset.searchText = String(observationId).toLocaleLowerCase("de");
      evidenceDetails.body.append(row);
    });
    root.append(evidenceDetails.element);
    root.append(node("p", { id: "evidence-warning", className: "warning-text", textContent: "" }));
    const charts = disclosure("Optionale Gesprächsbilder");
    const selectedCharts = new Set(state.draft.chart_types);
    [
      ["documentation_coverage", "Dokumentationsabdeckung"],
      ["competency_timeline", "Kompetenzentwicklung"],
      ["observation_timeline", "Zeitachse ausgewählter Beobachtungsbelege"],
    ].forEach(function (option) {
      charts.body.append(checkRow(option[1], "Nur Dokumentations- und Evidenzzusammenhänge", selectedCharts.has(option[0]), function (checked) {
        updateTuple("chart_types", option[0], checked);
        callBridge("setSelection", ["chart", option[0], checked]);
      }));
    });
    root.append(charts.element);
    return root;
  }

  function agreementsPhase() {
    const root = phaseIntro("Welche Unterstützung und Vereinbarungen treffen wir?", "Gemeinsame Ergebnisse werden nur durch den bestehenden Python-Service abgeschlossen.");
    root.append(field("Vorbereitete Unterstützung", textArea(state.draft.prepared_support_text, function (value) { updateText("prepared_support_text", value); })));
    root.append(field("Vorbereitete Vereinbarungen", textArea(state.draft.prepared_agreements_text, function (value) { updateText("prepared_agreements_text", value); })));
    root.append(field("Gemeinsame Unterstützung", textArea(state.draft.agreed_support_text, function (value) { updateText("agreed_support_text", value); })));
    root.append(field("Vereinbarungen", textArea(state.draft.agreed_agreements_text, function (value) { updateText("agreed_agreements_text", value); })));
    root.append(field("Zuständigkeiten", textArea(state.draft.responsibilities_text, function (value) { updateText("responsibilities_text", value); })));
    root.append(field("Nächste Überprüfung", dateInput(state.draft.next_review_date, function (value) { updateDate("next_review_date", value); })));
    root.append(evidenceSummary(true));
    const confirmation = completionConfirmation();
    const complete = actionButton("Gespräch abschließen", "secondary", function () {
      confirmation.hidden = false;
      const target = confirmation.querySelector("button");
      if (target) target.focus();
    }, state.dirty || !state.draft.has_persistent_id || !state.capabilities.complete);
    complete.id = "complete-action";
    root.append(complete);
    root.append(confirmation);
    appendRevisions(root);
    return root;
  }

  function appendRevisions(root) {
    const status = state.revision_status;
    if (!status || !status.revisions || !status.revisions.length) return;
    root.append(node("h3", { textContent: "Abgeschlossene Revisionen" }));
    status.revisions.forEach(function (revision) {
      const box = node("article", { className: "card revision-readonly" });
      box.append(node("h3", { textContent: `Revision ${revision.revision_number} · ${revision.status_label}` }));
      box.append(node("p", { textContent: [revision.completed_at_text, revision.completed_by_display_name].filter(Boolean).join(" · ") }));
      box.append(actionButton("Abschluss anzeigen", "secondary", function () { callBridge("openRevision", [revision.revision_id]); }));
      if (revision.artifact) {
        box.append(actionButton("Finales PDF anzeigen", "secondary", function () { callBridge("showFinalPdf", [revision.artifact.artifact_id]); }));
      }
      root.append(box);
    });
  }

  function evidenceSummary(includeGoals) {
    const selectedNames = state.preparation.subjects
      .filter(function (subject) { return state.draft.subject_ids.includes(subject.subject_id); })
      .map(function (subject) { return subject.subject_name; });
    let text = `${selectedNames.join(", ") || "Keine Gesprächsbereiche ausgewählt"}\n${state.draft.competency_ids.length} Kompetenzen · ${state.draft.observation_ids.length} Beobachtungsbelege · ${state.draft.chart_types.length} Gesprächsbilder`;
    if (includeGoals && state.draft.agreed_goals_text) text += `\nVereinbarte Ziele: ${state.draft.agreed_goals_text}`;
    const content = node("div");
    const summary = node("p", { className: "summary-copy", textContent: text });
    summary.dataset.includeGoals = includeGoals ? "true" : "false";
    content.append(summary);
    content.append(actionButton("Belege ansehen", "secondary", function () { activatePhase("evidence"); }));
    return card(includeGoals ? "Ausgewählte Belege und Ziele" : "Ausgewählte Belege", content);
  }

  function applyEvidenceFilters(searchText) {
    if (!evidenceState) return;
    const search = String(searchText || "").trim().toLocaleLowerCase("de");
    const selectedSubjects = new Set(state.draft.subject_ids);
    const selectedCompetencies = new Set(state.draft.competency_ids);
    const hasCompletePeriod = Boolean(state.draft.period_start && state.draft.period_end);
    const periodStart = hasCompletePeriod ? state.draft.period_start : "";
    const periodEnd = hasCompletePeriod ? state.draft.period_end : "";
    document.querySelectorAll("[data-competency-id]").forEach(function (row) {
      const dates = parsePayload(row.dataset.observationDates || "[]");
      const documented = row.dataset.currentConfirmation === "true" || (Array.isArray(dates) && dates.some(function (value) {
        return (!periodStart || value >= periodStart) && (!periodEnd || value <= periodEnd);
      }));
      const selected = selectedCompetencies.has(row.dataset.competencyId);
      row.hidden = !selectedSubjects.has(row.dataset.subjectId) || (!(documented || selected)) || (search && !row.dataset.searchText.includes(search));
    });
    document.querySelectorAll("#competency-host details").forEach(function (details) {
      details.hidden = !details.querySelector("[data-competency-id]:not([hidden])");
    });
    const selectedNames = new Set(state.preparation.subjects.filter(function (subject) {
      return selectedSubjects.has(subject.subject_id);
    }).map(function (subject) { return subject.subject_name; }));
    document.querySelectorAll("[data-observation-id]").forEach(function (row) {
      if (row.dataset.unavailable === "true") {
        row.hidden = Boolean(search && !row.dataset.searchText.includes(search));
        return;
      }
      const competencyIds = parsePayload(row.dataset.competencyIds || "[]");
      const related = Array.isArray(competencyIds) && competencyIds.some(function (id) { return selectedCompetencies.has(id); });
      row.hidden = (!(selectedNames.has(row.dataset.subjectName) || related)) || (search && !row.dataset.searchText.includes(search));
    });
  }

  function updateEvidenceWarning() {
    const warning = document.getElementById("evidence-warning");
    if (!warning) return;
    const count = state.draft.observation_ids.length;
    warning.textContent = count > 5 ? `${count} Belege ausgewählt. Drei bis fünf Belege sind meist gut überschaubar. Die Auswahl bleibt unverändert.` : "";
  }

  function searchValue() {
    const search = document.getElementById("evidence-search");
    return search ? search.value : "";
  }

  function refreshEvidenceSummaries() {
    document.querySelectorAll(".summary-copy").forEach(function (summary) {
      const selectedNames = state.preparation.subjects
        .filter(function (subject) { return state.draft.subject_ids.includes(subject.subject_id); })
        .map(function (subject) { return subject.subject_name; });
      let text = `${selectedNames.join(", ") || "Keine Gesprächsbereiche ausgewählt"}\n${state.draft.competency_ids.length} Kompetenzen · ${state.draft.observation_ids.length} Beobachtungsbelege · ${state.draft.chart_types.length} Gesprächsbilder`;
      if (summary.dataset.includeGoals === "true" && state.draft.agreed_goals_text) text += `\nVereinbarte Ziele: ${state.draft.agreed_goals_text}`;
      summary.textContent = text;
    });
  }

  function actionBar() {
    const bar = node("footer", { className: "action-bar" });
    bar.append(node("span", { className: "status", id: "operation-status", textContent: state.dirty ? "Ungespeicherte Änderungen" : "Entwurf liegt in Python vor" }));
    const save = actionButton("Entwurf speichern", "primary", function () {
      if (savePending) return;
      savePending = true;
      refreshChrome();
      callBridge("saveConferenceDraft", [], function () {
        savePending = false;
        refreshChrome();
      });
    }, !state.capabilities.save);
    save.id = "save-action";
    bar.append(save);
    return bar;
  }

  function completionConfirmation() {
    const box = node("section", {
      className: "card completion-confirmation",
      id: "completion-confirmation",
      hidden: true,
      role: "alert",
    });
    box.append(node("h3", { textContent: "Gespräch wirklich abschließen?" }));
    box.append(node("p", { textContent: "Es wird ein unveränderlicher Abschlussstand erzeugt. Der Entwurf bleibt für spätere Korrekturen bearbeitbar." }));
    box.append(actionButton("Gespräch verbindlich abschließen", "primary", function () {
      if (completionPending) return;
      box.hidden = true;
      completionPending = true;
      refreshChrome();
      callBridge("completeConference", [], function () {
        completionPending = false;
        refreshChrome();
      });
    }));
    box.append(actionButton("Abbrechen", "secondary", function () {
      box.hidden = true;
      const complete = document.getElementById("complete-action");
      if (complete) complete.focus();
    }));
    return box;
  }

  function refreshChrome() {
    if (!state || !app.firstChild) return;
    const dirty = document.getElementById("dirty-badge");
    if (dirty) {
      dirty.textContent = state.dirty ? "Ungespeicherte Änderungen" : "Entwurf gespeichert";
      dirty.dataset.tone = state.dirty ? "warning" : "success";
    }
    const status = document.getElementById("operation-status");
    if (status && !status.classList.contains("error")) status.textContent = state.dirty ? "Ungespeicherte Änderungen" : "Entwurf liegt in Python vor";
    const complete = document.getElementById("complete-action");
    if (complete) complete.disabled = state.dirty || !state.draft.has_persistent_id || !state.capabilities.complete || completionPending;
    const save = document.getElementById("save-action");
    if (save) save.disabled = !state.capabilities.save || savePending;
    window.__jkmLegDirty = Boolean(state.dirty);
  }

  function updateText(fieldName, value) {
    state.draft[fieldName] = value;
    state.dirty = true;
    refreshChrome();
    refreshEvidenceSummaries();
    callBridge("updateText", [fieldName, value]);
  }

  function updateDate(fieldName, value) {
    state.draft[fieldName] = value || "";
    state.dirty = true;
    refreshChrome();
    callBridge("updateDate", [fieldName, value]);
    if (evidenceBuilt) applyEvidenceFilters(searchValue());
  }

  function updateTuple(fieldName, itemId, selected) {
    const values = state.draft[fieldName];
    const index = values.indexOf(itemId);
    if (selected && index < 0) values.push(itemId);
    else if (!selected && index >= 0) values.splice(index, 1);
    state.dirty = true;
    refreshChrome();
    refreshEvidenceSummaries();
  }

  function callBridge(methodName, args, onDone, rawResult) {
    const method = bridge && bridge[methodName];
    if (typeof method !== "function") {
      announce("Diese Aktion ist nicht verfügbar.", true);
      return;
    }
    pendingCalls += 1;
    window.__jkmLegPendingCalls = pendingCalls;
    method.apply(bridge, args.concat(function (payload) {
      const result = parsePayload(payload);
      pendingCalls = Math.max(0, pendingCalls - 1);
      window.__jkmLegPendingCalls = pendingCalls;
      if (!rawResult && !result.ok) announce(visibleError(result), true);
      if (onDone) onDone(result);
    }));
  }

  function grouped(items, key) {
    const result = [];
    items.forEach(function (item) {
      const label = item[key] || "";
      let group = result.find(function (candidate) { return candidate.label === label; });
      if (!group) {
        group = { label: label, items: [] };
        result.push(group);
      }
      group.items.push(item);
    });
    return result;
  }

  function disclosure(label) {
    const element = node("details");
    element.append(node("summary", { textContent: label }));
    const body = node("div", { className: "details-body" });
    element.append(body);
    return { element: element, body: body };
  }

  function phaseIntro(title, description) {
    const fragment = document.createDocumentFragment();
    fragment.append(node("h2", { textContent: title }));
    fragment.append(node("p", { className: "phase-intro", textContent: description }));
    return fragment;
  }

  function studentContext() {
    const source = state.preparation;
    return [source.student_name, source.group_name || source.membership_status_label, source.course_name].filter(Boolean).join(" · ");
  }

  function badge(text, tone, id) {
    return node("span", { className: "badge", textContent: text, "data-tone": tone || "info", id: id || "" });
  }

  function empty(text) { return node("div", { className: "empty", textContent: text }); }

  function card(title, content) {
    const box = node("article", { className: "card" });
    box.append(node("h3", { textContent: title }));
    box.append(content);
    return box;
  }

  function field(labelText, control) {
    const wrapper = node("label", { className: "field" });
    wrapper.append(node("span", { className: "field-label", textContent: labelText }));
    wrapper.append(control);
    return wrapper;
  }

  function textInput(value, onInput) {
    const input = node("input", { type: "text", value: value || "" });
    input.addEventListener("input", function () { onInput(input.value); });
    return input;
  }

  function dateInput(value, onChange) {
    const input = node("input", { type: "date", value: value || "" });
    input.addEventListener("change", function () { onChange(input.value); });
    return input;
  }

  function textArea(value, onInput) {
    const textarea = node("textarea", { value: value || "" });
    textarea.addEventListener("input", function () { onInput(textarea.value); });
    return textarea;
  }

  function checkRow(title, detail, checked, onChange, disabled) {
    const label = node("label", { className: "check-row" });
    const input = node("input", { type: "checkbox", checked: Boolean(checked), disabled: Boolean(disabled) });
    input.addEventListener("change", function () { onChange(input.checked); });
    const copy = node("span", { className: "check-copy" });
    copy.append(node("span", { textContent: title }));
    if (detail) copy.append(node("small", { textContent: detail }));
    label.append(input, copy);
    return label;
  }

  function actionButton(label, style, onClick, disabled) {
    const button = node("button", { type: "button", className: `button ${style}`, textContent: label, disabled: Boolean(disabled) });
    button.addEventListener("click", onClick);
    return button;
  }

  function node(tagName, attributes) {
    const element = document.createElement(tagName);
    Object.entries(attributes || {}).forEach(function (entry) {
      const key = entry[0];
      const value = entry[1];
      if (key === "className") element.className = value;
      else if (key === "textContent") element.textContent = value;
      else if (key === "checked" || key === "disabled" || key === "hidden") element[key] = Boolean(value);
      else if (key === "value") element.value = value;
      else if (value !== "") element.setAttribute(key, value);
    });
    return element;
  }

  function announce(message, isError) {
    liveStatus.textContent = message;
    const visible = document.getElementById("operation-status");
    if (visible) {
      visible.textContent = message;
      visible.classList.toggle("error", Boolean(isError));
    }
  }

  function parsePayload(payload) {
    try { return JSON.parse(payload); }
    catch (_error) { return { ok: false, code: "invalid_bridge_response" }; }
  }

  function visibleResult(code) {
    return {
      draft_saved: "LEG-Entwurf gespeichert.",
      conference_completed: "Das LEG wurde abgeschlossen.",
      revision_open_requested: "Der Abschluss wird in der Desktop-App geöffnet.",
      final_pdf_open_requested: "Das finale PDF wird sicher geöffnet.",
    }[code] || "Änderung liegt im Python-Entwurf vor.";
  }

  function visibleError(result) {
    if (result.message) return result.message;
    return {
      save_failed: "Der LEG-Entwurf konnte nicht gespeichert werden.",
      completion_not_ready: "Das LEG ist noch nicht bereit für den Abschluss.",
      completion_requires_saved_draft: "Bitte speichere den Entwurf vor dem Abschluss.",
      final_pdf_viewer_blocked: "Die sichere PDF-Anzeige ist technisch noch nicht freigegeben.",
      final_pdf_unavailable: "Das finale PDF ist nicht sicher verfügbar.",
      invalid_bridge_response: "Die lokale Oberfläche hat eine ungültige Antwort erhalten.",
    }[result.code] || "Die Aktion wurde durch den Bridge-Vertrag abgewiesen.";
  }

  function cssSafe(value) {
    return String(value).replace(/[^a-z0-9_-]/gi, "");
  }
}());
