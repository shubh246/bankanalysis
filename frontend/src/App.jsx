import { useEffect, useState, useCallback } from 'react'
import './App.css'
import UploadPanel from './components/UploadPanel'
import TrailPanel from './components/TrailPanel'
import { listStatements, deleteStatement } from './api'

function App() {
  const [tab, setTab] = useState('upload')
  const [statements, setStatements] = useState([])

  const refreshStatements = useCallback(async () => {
    const res = await listStatements()
    setStatements(res.data)
  }, [])

  useEffect(() => {
    refreshStatements()
  }, [refreshStatements])

  const handleDelete = async (id) => {
    if (!confirm('Delete this statement and all its transactions?')) return
    await deleteStatement(id)
    refreshStatements()
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Bank Statement Analysis</h1>
        <nav className="tabs">
          <button className={tab === 'upload' ? 'active' : ''} onClick={() => setTab('upload')}>
            Upload
          </button>
          <button className={tab === 'trail' ? 'active' : ''} onClick={() => setTab('trail')}>
            Trail &amp; Fund Flow
          </button>
        </nav>
      </header>

      <main>
        {tab === 'upload' && (
          <UploadPanel statements={statements} onUploaded={refreshStatements} onDelete={handleDelete} />
        )}
        {tab === 'trail' && <TrailPanel statements={statements} />}
      </main>
    </div>
  )
}

export default App
