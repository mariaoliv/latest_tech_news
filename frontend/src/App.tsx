import { useState, useEffect } from 'react'
import { getNewsSummary } from './api'

import './App.css'

const NewsDashboard: React.FC = () => {
  const [summary, setSummary] = useState<string>('')
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchNews = async () => {
      try {
        setLoading(true)
        const data = await getNewsSummary()
        setSummary(data)
      } catch (err) {
        setError("Failed to load tech news summary.")
      } finally {
        setLoading(false)
      }
    };

    fetchNews()
  }, [])

  if (loading) return <div>Generating latest tech summary...</div>
  if (error) return <div style={{ color: 'red' }}>{error}</div>

  return (
    <div className="summary-container">
      <h1>Latest Tech News</h1>
      <p style={{ whiteSpace: 'pre-wrap' }}>{summary}</p>
    </div>
  )
}

export default NewsDashboard
