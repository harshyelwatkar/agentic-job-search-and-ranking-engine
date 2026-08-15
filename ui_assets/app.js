const form = document.querySelector("#search-form");
const queryInput = document.querySelector("#query");
const button = document.querySelector("#search-button");
const buttonLabel = document.querySelector("#button-label");

const summary = document.querySelector("#summary");
const rankingSummary = document.querySelector("#ranking-summary");
const statusPill = document.querySelector("#status-pill");

const results = document.querySelector("#results");
const pagination = document.querySelector("#pagination");
const chips = document.querySelectorAll(".chip");

const pageSize = 10;

let currentResults = [];
let currentTotal = 0;
let currentLatency = "";
let currentPage = 1;
let currentPlan = null;
let currentSummary = null;

const escapeHtml = (value) =>
  String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

const formatScore = (score) => {
  if (score === null || score === undefined || Number.isNaN(Number(score))) {
    return "Score unavailable";
  }

  return Number(score).toFixed(3);
};

const formatLatency = (milliseconds) => {
  if (milliseconds < 1000) {
    return `${Math.round(milliseconds)} ms`;
  }

  return `${(milliseconds / 1000).toFixed(2)} s`;
};

const qualityLabel = (quality) => {
  if (quality === "strong") {
    return "Strong match";
  }

  if (quality === "partial") {
    return "Partial match";
  }

  if (quality === "weak") {
    return "Weak match";
  }

  return "Unknown match";
};

const qualityClass = (quality) => {
  if (quality === "strong") {
    return "quality-strong";
  }

  if (quality === "partial") {
    return "quality-partial";
  }

  if (quality === "weak") {
    return "quality-weak";
  }

  return "quality-unknown";
};

const renderEmpty = (message) => {
  results.innerHTML = `
    <div class="empty">
      ${escapeHtml(message)}
    </div>
  `;

  pagination.innerHTML = "";
};

const renderPlan = (plan) => {
  if (!plan) {
    rankingSummary.textContent = "Agentic ranking";

    return;
  }

  const mode = plan.retrieval_mode
    ? plan.retrieval_mode.toUpperCase()
    : "HYBRID";

  const gate = plan.gate_mode ? plan.gate_mode : "normal";

  rankingSummary.textContent = `Agentic plan: ${mode} retrieval · ${gate} gate`;

  statusPill.textContent = `Vespa Cloud | ${mode} | ${gate} gate`;
};

const renderSummary = () => {
  if (!currentSummary) {
    return;
  }

  const total = currentTotal;

  summary.textContent =
    `${currentSummary.text} ` +
    `${total} eligible results · ` +
    `${currentSummary.strong_matches} strong · ` +
    `${currentSummary.partial_matches} partial · ` +
    `${currentSummary.weak_matches} weak · ` +
    `${currentLatency}`;
};

const renderSearchOverview = () => {
  const existing = document.querySelector("#search-overview");

  if (existing) {
    existing.remove();
  }

  if (!currentPlan || !currentSummary) {
    return;
  }

  const overview = document.createElement("section");

  overview.id = "search-overview";

  overview.className = "search-overview";

  const skills = currentPlan.skills || [];
  const locations = currentPlan.locations || [];
  const roleTerms = currentPlan.role_terms || [];

  const chips = [...roleTerms, ...skills, ...locations];

  overview.innerHTML = `
    <div class="overview-header">

      <div>
        <div class="eyebrow">
          SEARCH PLAN
        </div>

        <h2>
          Agentic interpretation
        </h2>
      </div>

      <span class="plan-badge">
        ${escapeHtml(currentPlan.retrieval_mode || "hybrid")}
      </span>

    </div>

    <div class="plan-grid">

      <div class="plan-item">
        <span>Role</span>

        <strong>
          ${escapeHtml(roleTerms.join(", ")) || "Any"}
        </strong>
      </div>

      <div class="plan-item">
        <span>Skills</span>

        <strong>
          ${escapeHtml(skills.join(", ")) || "Any"}
        </strong>
      </div>

      <div class="plan-item">
        <span>Location</span>

        <strong>
          ${escapeHtml(locations.join(", ")) || "Any"}
        </strong>
      </div>

      <div class="plan-item">
        <span>Gate</span>

        <strong>
          ${escapeHtml(currentPlan.gate_mode || "normal")}
        </strong>
      </div>

    </div>

    ${
      chips.length
        ? `
          <div class="plan-chips">
            ${chips
              .map(
                (chip) => `
                  <span class="plan-chip">
                    ${escapeHtml(chip)}
                  </span>
                `,
              )
              .join("")}
          </div>
        `
        : ""
    }
  `;

  results.parentNode.insertBefore(overview, results);
};

const renderPagination = () => {
  const pageCount = Math.ceil(currentResults.length / pageSize);

  if (pageCount <= 1) {
    pagination.innerHTML = "";
    return;
  }

  const pageButtons = Array.from(
    {
      length: pageCount,
    },
    (_, index) => {
      const page = index + 1;

      return `
        <button
          class="page-button"
          type="button"
          data-page="${page}"
          aria-current="${page === currentPage ? "page" : "false"}"
        >
          ${page}
        </button>
      `;
    },
  ).join("");

  pagination.innerHTML = `
    <button
      class="page-button"
      type="button"
      data-page="${currentPage - 1}"
      ${currentPage === 1 ? "disabled" : ""}
      aria-label="Previous page"
    >
      &lsaquo;
    </button>

    ${pageButtons}

    <button
      class="page-button"
      type="button"
      data-page="${currentPage + 1}"
      ${currentPage === pageCount ? "disabled" : ""}
      aria-label="Next page"
    >
      &rsaquo;
    </button>
  `;
};

const renderResults = () => {
  if (!currentResults.length) {
    renderEmpty(currentSummary?.text || "No matching jobs found.");

    renderSummary();

    return;
  }

  const start = (currentPage - 1) * pageSize;

  const pageItems = currentResults.slice(start, start + pageSize);

  results.innerHTML = pageItems
    .map((job, index) => {
      const quality = job.match_quality || "unknown";

      const matched = job.matched_skills || [];

      const missing = job.missing_skills || [];

      const title = job.title || "Untitled position";

      const company = job.company || "Company not provided";

      const location = job.location || "Location not provided";

      const experience = job.experience || "Experience not provided";

      const url = job.url || "";

      return `
        <article
          class="job-card"
          style="
            animation-delay:
            ${Math.min(index * 45, 300)}ms
          "
        >

          <div class="job-card-header">

            <div>

              <div class="job-rank">
                #${escapeHtml(job.rank)}
              </div>

              <h3 class="job-title">
                ${escapeHtml(title)}
              </h3>

              <div class="job-company">
                ${escapeHtml(company)}
              </div>

            </div>

            <span
              class="
                quality-badge
                ${qualityClass(quality)}
              "
            >
              ${escapeHtml(qualityLabel(quality))}
            </span>

          </div>

          <div class="job-meta">

            <span>
              ${escapeHtml(location)}
            </span>

            <span>
              ${escapeHtml(experience)}
            </span>

            ${
              job.employment_type
                ? `
                  <span>
                    ${escapeHtml(job.employment_type)}
                  </span>
                `
                : ""
            }

          </div>

          <div class="job-score-row">

            <div>
              <span class="score-label">
                Match score
              </span>

              <strong>
                ${escapeHtml(formatScore(job.job_match_score))}
              </strong>
            </div>

            <div>
              <span class="score-label">
                Vespa
              </span>

              <strong>
                ${escapeHtml(formatScore(job.relevance))}
              </strong>
            </div>

          </div>

          <div class="match-section">

            <div class="match-heading">
              <span>
                Matched skills
              </span>
            </div>

            <div class="skill-list">

              ${
                matched.length
                  ? matched
                      .map(
                        (skill) => `
                          <span
                            class="
                              skill-chip
                              skill-match
                            "
                          >
                            ✓ ${escapeHtml(skill)}
                          </span>
                        `,
                      )
                      .join("")
                  : `
                    <span
                      class="
                        skill-chip
                        skill-empty
                      "
                    >
                      None
                    </span>
                  `
              }

            </div>

          </div>

          <div class="match-section">

            <div class="match-heading">
              <span>
                Missing skills
              </span>
            </div>

            <div class="skill-list">

              ${
                missing.length
                  ? missing
                      .map(
                        (skill) => `
                          <span
                            class="
                              skill-chip
                              skill-missing
                            "
                          >
                            × ${escapeHtml(skill)}
                          </span>
                        `,
                      )
                      .join("")
                  : `
                    <span
                      class="
                        skill-chip
                        skill-empty
                      "
                    >
                      None
                    </span>
                  `
              }

            </div>

          </div>

          <details class="why-section">

            <summary>
              Why this job matched
            </summary>

            <div class="why-content">

              <div class="why-item">
                <span>
                  Role compatibility
                </span>

                <strong>
                  ${escapeHtml(formatScore(job.title_score))}
                </strong>
              </div>

              <div class="why-item">
                <span>
                  Skill coverage
                </span>

                <strong>
                  ${escapeHtml(formatScore(job.skill_score))}
                </strong>
              </div>

              <div class="why-item">
                <span>
                  Experience
                </span>

                <strong>
                  ${escapeHtml(formatScore(job.experience_score))}
                </strong>
              </div>

              <div class="why-item">
                <span>
                  Location
                </span>

                <strong>
                  ${escapeHtml(formatScore(job.location_score))}
                </strong>
              </div>

              ${
                job.plan_gate_reason
                  ? `
                    <p class="gate-reason">
                      ${escapeHtml(job.plan_gate_reason)}
                    </p>
                  `
                  : ""
              }

            </div>

          </details>

          <div class="job-card-footer">

            ${
              url
                ? `
                  <a
                    class="apply-link"
                    href="${escapeHtml(url)}"
                    target="_blank"
                    rel="noreferrer"
                  >
                    View job
                    <span aria-hidden="true">
                      ↗
                    </span>
                  </a>
                `
                : ""
            }

          </div>

        </article>
      `;
    })
    .join("");

  renderPagination();
  renderSummary();
};

const setLoading = (isLoading) => {
  button.disabled = isLoading;

  buttonLabel.innerHTML = isLoading
    ? '<span class="spinner" aria-hidden="true"></span>'
    : "Search";
};

const runSearch = async (query) => {
  const trimmed = query.trim();

  if (!trimmed) {
    queryInput.focus();

    results.innerHTML = "";
    pagination.innerHTML = "";

    currentResults = [];
    currentTotal = 0;
    currentPlan = null;
    currentSummary = null;

    summary.textContent = "Ready when you are.";

    rankingSummary.textContent = "Agentic ranking";

    return;
  }

  const startedAt = performance.now();

  setLoading(true);

  summary.textContent = `Planning and searching for "${trimmed}"...`;

  pagination.innerHTML = "";

  try {
    const response = await fetch("/api/search", {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        query: trimmed,
      }),
    });

    const data = await response.json();

    currentLatency = formatLatency(performance.now() - startedAt);

    if (!response.ok) {
      throw new Error(data.detail || "Search failed.");
    }

    currentResults = data.results || [];

    currentTotal = data.totalCount ?? currentResults.length;

    currentPlan = data.plan || null;

    currentSummary = data.summary || null;

    currentPage = 1;

    renderPlan(currentPlan);

    renderSearchOverview();

    renderResults();
  } catch (error) {
    currentLatency = formatLatency(performance.now() - startedAt);

    renderEmpty(error.message || "Something went wrong while searching.");

    summary.textContent = `Search failed · ${currentLatency}`;
  } finally {
    setLoading(false);
  }
};

form.addEventListener("submit", (event) => {
  event.preventDefault();

  runSearch(queryInput.value);
});

chips.forEach((chip) => {
  chip.addEventListener("click", () => {
    queryInput.value = chip.dataset.query;

    runSearch(queryInput.value);
  });
});

pagination.addEventListener("click", (event) => {
  const pageButton = event.target.closest("[data-page]");

  if (!pageButton || pageButton.disabled) {
    return;
  }

  const pageCount = Math.ceil(currentResults.length / pageSize);

  currentPage = Math.min(
    Math.max(Number(pageButton.dataset.page), 1),
    pageCount,
  );

  renderResults();

  results.scrollIntoView({
    behavior: "smooth",
    block: "start",
  });
});
