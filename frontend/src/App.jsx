import { useEffect, useState, useCallback } from 'react'
import './App.css'
import UploadPanel from './components/UploadPanel'
import TrailPanel from './components/TrailPanel'
import Login from './components/Login'
import { listStatements, deleteStatement, getToken, clearToken, setUnauthorizedHandler } from './api'

function App() {
  const [tab, setTab] = useState('upload')
  const [statements, setStatements] = useState([])
  const [authed, setAuthed] = useState(!!getToken())

  useEffect(() => {
    setUnauthorizedHandler(() => setAuthed(false))
  }, [])

  const refreshStatements = useCallback(async () => {
    const res = await listStatements()
    setStatements(res.data)
  }, [])

  useEffect(() => {
    if (authed) refreshStatements()
  }, [authed, refreshStatements])

  const handleDelete = async (id) => {
    if (!confirm('Delete this statement and all its transactions?')) return
    await deleteStatement(id)
    refreshStatements()
  }

  const handleLogout = () => {
    clearToken()
    setAuthed(false)
  }

  if (!authed) {
    return <Login onLoggedIn={() => setAuthed(true)} />
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
          <button onClick={handleLogout}>Log out</button>
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
