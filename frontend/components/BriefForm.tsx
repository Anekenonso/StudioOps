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

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setResponse(null)
    const brief = {
      title,
      description,
      format,
      genre,
      geography,
      research_questions: [],
    }
    try {
      const res = await submitResearch(brief)
      setResponse(res)
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
      {response && <pre className="response">{JSON.stringify(response, null, 2)}</pre>}
    </div>
  )
}
