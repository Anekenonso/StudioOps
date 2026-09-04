"use client"
import React, { useState } from 'react'
import { submitResearch } from '../lib/api'

export default function BriefForm() {
  const [title, setTitle] = useState('Lagos After Dark')
  const [description, setDescription] = useState("A contemporary Nigerian crime thriller set in Lagos.")
  const [format, setFormat] = useState('Film')
  const [genre, setGenre] = useState('Crime Thriller')
  const [geography, setGeography] = useState('Nigeria')
  const [response, setResponse] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [stage, setStage] = useState(0)
  const stages = [
    'Understanding brief',
    'Creating research plan',
    'Searching the web',
    'Analyzing findings',
    'Building studio brief',
  ]

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setResponse(null)
    setStage(0)
    const brief = {
      title,
      description,
      format,
      genre,
      geography,
      research_questions: [],
    }
    try {
      // Progress simulation: advance stages while awaiting response
      const advance = () => {
        setStage((s) => Math.min(s + 1, stages.length))
      }
      const timer = setInterval(advance, 700)
      const res = await submitResearch(brief)
      clearInterval(timer)
      setResponse(res)
      setStage(stages.length)
    } catch (err) {
      setResponse({ error: String(err) })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card">
      <form onSubmit={handleSubmit}>
        <div className="form-row">
          <label>Project Title</label>
          <input value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <div className="form-row">
          <label>Project Description</label>
          <textarea rows={4} value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
        <div className="form-row">
          <label>Format</label>
          <input value={format} onChange={(e) => setFormat(e.target.value)} />
        </div>
        <div className="form-row">
          <label>Genre</label>
          <input value={genre} onChange={(e) => setGenre(e.target.value)} />
        </div>
        <div className="form-row">
          <label>Geography</label>
          <input value={geography} onChange={(e) => setGeography(e.target.value)} />
        </div>
        <div className="form-row">
          <button className="primary" type="submit" disabled={loading}>
            {loading ? 'Researching…' : 'Start Research →'}
          </button>
        </div>
      </form>
      <div style={{marginTop:12}}>
        {stages.map((s, i) => (
          <div key={s} style={{display:'flex',alignItems:'center',gap:8}}>
            <div style={{width:12,height:12,borderRadius:6,background:i<stage? '#D9A441': i===stage? '#142033':'#E7E5E0'}}></div>
            <div style={{color:i<stage? 'var(--text)':'var(--muted)'}}>{`${String(i+1).padStart(2,'0')} — ${s}`}</div>
          </div>
        ))}
      </div>

      {response && (
        <div className="card" style={{marginTop:16}}>
          <h3>Studio Brief</h3>
          {response.report && response.report.executive_summary && (
            <p>{response.report.executive_summary}</p>
          )}
          {response.report && response.report.sources && (
            <div>
              <h4>Sources</h4>
              <ul>
                {response.report.sources.map((s: any) => (
                  <li key={s.url}><a href={s.url} target="_blank" rel="noreferrer">{s.title || s.url}</a></li>
                ))}
              </ul>
            </div>
          )}
          <pre className="response">{JSON.stringify(response, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}
