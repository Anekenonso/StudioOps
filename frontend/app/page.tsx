export default function Page() {
  return (
    <main style={{ padding: 24, fontFamily: 'sans-serif' }}>
      <h1>STUDIOOPS</h1>
      <p>Production intelligence, from brief to evidence.</p>
      <form style={{ display: 'grid', gap: 12, maxWidth: 480 }}>
        <input placeholder="Project title" />
        <textarea placeholder="Project description" rows={5} />
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <input placeholder="Format" />
          <input placeholder="Genre" />
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <input placeholder="Target audience" />
          <input placeholder="Geography" />
        </div>
        <button type="button">Run StudioOps</button>
      </form>
    </main>
  );
}
