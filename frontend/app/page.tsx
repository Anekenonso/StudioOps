const examplePrompts = [
  'Nigerian crime thriller',
  'Afrobeats documentary',
  'Sci-fi series in Africa',
  'Coming-of-age drama',
];

const workflowSteps = [
  { title: 'Understand the brief', description: 'Gemini interprets your project idea, goals, audience, and research requirements.' },
  { title: 'Research the web', description: 'Parallel searches the live web for relevant entertainment intelligence.' },
  { title: 'Analyze & synthesize', description: 'StudioOps identifies signals, patterns, opportunities, and risks.' },
  { title: 'Generate studio brief', description: 'Receive a structured, actionable brief with supporting sources.' },
];

const progress = [
  { label: 'Understanding brief', active: true },
  { label: 'Searching the web', active: true },
  { label: 'Analyzing findings', active: false },
  { label: 'Building studio brief', active: false },
];

const briefSections = [
  {
    title: 'Executive Summary',
    body:
      'The project has strong opportunity in the premium African crime thriller space, particularly where grounded local environments, audience-specific tension, and globally legible storytelling converge. The strongest evidence points to rising appetite for culturally rooted genre work and a practical path for a focused release strategy.',
  },
  {
    title: 'Market Landscape',
    body:
      'Streaming demand remains strong for culturally anchored genre content, especially when paired with recognizable creative concepts and global distribution potential. Research suggests the strongest opportunities are in projects that balance local authenticity with clear international readability.',
  },
  {
    title: 'Comparable Projects',
    body:
      'Regional and global comparables suggest a market fit for premium crime narratives with strong urban identity, suspense, and audience specificity. The concept benefits from a clear differentiation strategy grounded in Lagos or broader Nigerian context.',
  },
  {
    title: 'Audience Intelligence',
    body:
      'Audience interest is strongest among viewers seeking grounded, high-tension stories with contemporary relevance, social drama, and cinematic production value. The strongest response is likely among young adults and crossover audiences who value authentic local stories with genre clarity.',
  },
  {
    title: 'Production Opportunities',
    body:
      'There is momentum around location-driven storytelling and high-value studio partnerships that can support premium visual execution without overextending budget. Focused production planning and local creative partnerships appear to be the most efficient route to execution.',
  },
  {
    title: 'Risks & Considerations',
    body:
      'The main risk is insufficient evidence in some market and production areas, especially around audience segmentation and specific partner viability. These should be validated before a full pre-production commitment is made.',
  },
  {
    title: 'Recommended Next Steps',
    body:
      'Validate audience demand, investigate distribution pathways, compare local production partners, and refine the positioning to emphasize authenticity plus commercial clarity.',
  },
];

const sources = [
  {
    title: 'Market report sample',
    publisher: 'Industry publication',
    date: '2026',
    url: 'https://example.com/market-report',
    why_it_matters: 'Supports the market demand signal for culturally rooted genre content.',
  },
  {
    title: 'Streaming audience trend summary',
    publisher: 'Research brief',
    date: '2026',
    url: 'https://example.com/audience-trend',
    why_it_matters: 'Highlights the audience conditions favoring premium local crime storytelling.',
  },
];

export default function Page() {
  return (
    <main className="page-shell">
      <header className="site-header">
        <div className="brand-block">
          <div className="brand-wordmark">StudioOps</div>
          <span className="brand-tag">PRODUCTION INTELLIGENCE</span>
        </div>

        <nav className="top-nav" aria-label="Main navigation">
          <a href="#">New Research</a>
          <a href="#">About</a>
        </nav>
      </header>

      <section className="hero hero-panel">
        <div className="hero-copy">
          <h1>Turn an idea into a production intelligence brief.</h1>
          <p>
            Research your film, series, or entertainment project against the live web and uncover the market,
            audience, competitive landscape, opportunities, and risks.
          </p>
        </div>
      </section>

      <section className="workspace-card panel">
        <div className="section-header">
          <div>
            <p className="eyebrow">What are you working on?</p>
            <p className="supporting-copy">Describe your project and what you want to understand.</p>
          </div>
          <span className="char-count">0 / 2000</span>
        </div>

        <textarea
          className="brief-input"
          defaultValue="We're developing a Nigerian crime thriller set in Lagos. Research the current market, comparable films, audience trends, potential locations, distribution opportunities, and relevant production companies."
          rows={7}
        />

        <div className="prompt-row">
          <button className="secondary-button" type="button">
            Try an example
          </button>
          <div className="chip-list" aria-label="Example prompts">
            {examplePrompts.map((prompt) => (
              <button key={prompt} className="chip" type="button">
                {prompt}
              </button>
            ))}
          </div>
        </div>

        <button className="primary-button" type="button">
          Start Research →
        </button>
      </section>

      <section className="how-it-works">
        <div className="section-title-row">
          <h2>How StudioOps works</h2>
        </div>

        <div className="workflow-grid">
          {workflowSteps.map((step, index) => (
            <article key={step.title} className="workflow-card">
              <span className="step-number">0{index + 1}</span>
              <h3>{step.title}</h3>
              <p>{step.description}</p>
            </article>
          ))}
        </div>
      </section>

      <div className="partner-line">
        <span>Powered by Gemini + Parallel</span>
      </div>

      <section className="processing-panel panel">
        <div className="processing-header">
          <div>
            <h2>Researching your project</h2>
            <p>StudioOps is gathering intelligence from the live web.</p>
          </div>
        </div>

        <div className="processing-steps" aria-label="Research progress">
          {progress.map((state, index) => (
            <div key={state.label} className={`progress-item ${state.active ? 'active' : ''}`}>
              <span className="progress-index">0{index + 1}</span>
              <span>{state.label}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="research-panel panel">
        <div className="research-panel-header">
          <div>
            <p className="eyebrow small">Live web research</p>
            <h2>Researching the live web</h2>
          </div>
        </div>

        <ul className="research-list">
          <li>Searching industry publications...</li>
          <li>Searching comparable films...</li>
          <li>Searching audience & market data...</li>
          <li>Searching distribution platforms...</li>
          <li>Searching production companies...</li>
        </ul>
      </section>

      <section className="brief-panel panel">
        <div className="brief-header-row">
          <div>
            <p className="eyebrow small">Studio Brief</p>
            <h2>Nigerian Crime Thriller</h2>
          </div>
          <div className="report-actions">
            <button type="button" className="ghost-button">Download</button>
            <button type="button" className="ghost-button">Share</button>
            <button type="button" className="ghost-button">New Research</button>
          </div>
        </div>

        <div className="brief-meta">
          <span>FEATURE FILM</span>
          <span>LAGOS</span>
          <span>RESEARCHED SEPTEMBER 2026</span>
        </div>

        {briefSections.map((section) => (
          <article key={section.title} className="brief-section">
            <h3>{section.title}</h3>
            <p>{section.body}</p>
          </article>
        ))}

        <article className="brief-section">
          <h3>Sources</h3>
          <div className="source-list">
            {sources.map((source) => (
              <div key={source.title} className="source-card">
                <div>
                  <strong>{source.title}</strong>
                  <p>{source.publisher}</p>
                </div>
                <div className="source-meta">
                  <span>{source.date}</span>
                  <a href={source.url}>Open link</a>
                </div>
                <p className="source-why">{source.why_it_matters}</p>
              </div>
            ))}
          </div>
        </article>
      </section>
    </main>
  );
}
