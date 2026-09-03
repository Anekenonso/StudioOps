const progress = [
  { label: 'Brief analyzed', active: true },
  { label: 'Research plan created', active: true },
  { label: 'Parallel search completed', active: true },
  { label: 'Synthesizing evidence', active: true },
  { label: 'Report generation', active: false },
];

const report = {
  executive_summary:
    'The brief suggests a strong opportunity for a young adult African crime thriller with a clear genre hook and broad streaming appeal. Evidence quality is moderate, with the strongest signals around audience receptivity, market trends, and comparable titles.',
  key_opportunities: [
    'Distinctive Nigerian crime-thriller positioning',
    'Young African streaming audience potential',
    'Cross-market appeal via genre familiarity',
  ],
  comparable_titles: [
    { title: 'Blood & Water', why_it_matters: 'Regional success with a strong streaming identity', evidence_url: 'https://example.com' },
    { title: 'The Last of Us', why_it_matters: 'Genre credibility and audience retention pattern', evidence_url: 'https://example.com' },
  ],
  market_signals: [
    { signal: 'Streaming growth', detail: 'Demand for regionally grounded genre storytelling continues to rise across African and global audiences.', evidence_url: 'https://example.com' },
  ],
  production_intelligence: [
    { topic: 'Budget planning', detail: 'The concept is viable in a focused mid-budget framework with strong location strategy and talent curation.', evidence_url: 'https://example.com' },
  ],
  risks: [
    {
      title: 'Evidence gaps',
      severity: 'medium',
      explanation: 'Some assumptions still require more validation around specific audience segmentation and local production constraints.',
      evidence_urls: ['https://example.com'],
      recommended_action: 'Complete a targeted validation pass before green-lighting a full production plan.',
    },
  ],
  next_steps: [
    'Validate comparable title performance in the target market.',
    'Review local production and talent constraints.',
    'Refine audience positioning before launch.',
  ],
  sources: [
    { title: 'Sample Evidence', url: 'https://example.com', snippet: 'Example source snippet for demo purposes.', source_type: 'web', relevance: 0.92 },
  ],
};

export default function Page() {
  return (
    <main className="page-shell">
      <div className="topbar">
        <div>
          <span className="eyebrow">STUDIOOPS</span>
          <h1>Production intelligence, from brief to evidence.</h1>
        </div>
      </div>

      <section className="grid layout">
        <div className="panel form-panel">
          <h2>Project brief</h2>
          <div className="field-grid">
            <label>
              <span>Project title</span>
              <input defaultValue="Untitled Nigerian Crime Thriller" />
            </label>
            <label>
              <span>Project description</span>
              <textarea rows={5} defaultValue="A crime thriller series for a young African streaming audience." />
            </label>
            <div className="row two-up">
              <label>
                <span>Format</span>
                <input defaultValue="Series" />
              </label>
              <label>
                <span>Genre</span>
                <input defaultValue="Crime Thriller" />
              </label>
            </div>
            <div className="row two-up">
              <label>
                <span>Target audience</span>
                <input defaultValue="Young Adults" />
              </label>
              <label>
                <span>Geography</span>
                <input defaultValue="Nigeria / Africa" />
              </label>
            </div>
            <button type="button">Run StudioOps</button>
          </div>
        </div>

        <div className="panel">
          <h2>Agent activity</h2>
          <ul className="status-list">
            {progress.map((step) => (
              <li key={step.label} className={step.active ? 'active' : ''}>
                <span className="dot" />
                {step.label}
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="panel report-panel">
        <div className="section-heading">
          <h2>Production intelligence brief</h2>
          <span className="tag">Evidence-based</span>
        </div>

        <article className="report-section">
          <h3>Executive summary</h3>
          <p>{report.executive_summary}</p>
        </article>

        <article className="report-section">
          <h3>Key opportunities</h3>
          <ul>
            {report.key_opportunities.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>

        <article className="report-section">
          <h3>Comparable titles</h3>
          <div className="card-grid">
            {report.comparable_titles.map((title) => (
              <div key={title.title} className="card">
                <strong>{title.title}</strong>
                <p>{title.why_it_matters}</p>
                <a href={title.evidence_url}>Source</a>
              </div>
            ))}
          </div>
        </article>

        <article className="report-section">
          <h3>Market signals</h3>
          <div className="card-grid">
            {report.market_signals.map((signal) => (
              <div key={signal.signal} className="card">
                <strong>{signal.signal}</strong>
                <p>{signal.detail}</p>
                <a href={signal.evidence_url}>Evidence</a>
              </div>
            ))}
          </div>
        </article>

        <article className="report-section">
          <h3>Production intelligence</h3>
          <div className="card-grid">
            {report.production_intelligence.map((item) => (
              <div key={item.topic} className="card">
                <strong>{item.topic}</strong>
                <p>{item.detail}</p>
                <a href={item.evidence_url}>Evidence</a>
              </div>
            ))}
          </div>
        </article>

        <article className="report-section">
          <h3>Risks</h3>
          <div className="card-grid">
            {report.risks.map((risk) => (
              <div key={risk.title} className="card risk-card">
                <strong>{risk.title}</strong>
                <span className="severity">{risk.severity}</span>
                <p>{risk.explanation}</p>
                <p><strong>Action:</strong> {risk.recommended_action}</p>
              </div>
            ))}
          </div>
        </article>

        <article className="report-section">
          <h3>Next steps</h3>
          <ol>
            {report.next_steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </article>

        <article className="report-section">
          <h3>Sources</h3>
          <ul className="source-list">
            {report.sources.map((source) => (
              <li key={source.url}>
                <a href={source.url}>{source.title}</a>
                <p>{source.snippet}</p>
              </li>
            ))}
          </ul>
        </article>
      </section>
    </main>
  );
}
