import { useEffect, useRef, useState } from 'react'
import { apiBase, getStatement, uploadStatement } from '../api'

const POLL_INTERVAL_MS = 2000

export default function UploadPanel({ statements, onUploaded, onDelete }) {
  const [dragOver, setDragOver] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const [password, setPassword] = useState('')
  const [selectedFile, setSelectedFile] = useState(null)
  const inputRef = useRef(null)
  const pollTimerRef = useRef(null)

  const isCloudHosted = typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1'
  const isLocalApiTarget = apiBase.includes('127.0.0.1') || apiBase.includes('localhost')

  useEffect(() => () => clearTimeout(pollTimerRef.current), [])

  const pollStatement = (id) => {
    clearTimeout(pollTimerRef.current)
    pollTimerRef.current = setTimeout(async () => {
      try {
        const res = await getStatement(id)
        const statement = res.data
        setResult({ statement })
        if (statement.status === 'processing') {
          pollStatement(id)
        } else {
          setBusy(false)
          onUploaded()
        }
      } catch {
        setBusy(false)
      }
    }, POLL_INTERVAL_MS)
  }

  const handleFile = async (file, pdfPassword = password) => {
    if (!file) return
    setSelectedFile(file)
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const res = await uploadStatement(file, pdfPassword)
      setResult(res.data)
      setPassword('')
      onUploaded()
      if (res.data.statement.status === 'processing') {
        pollStatement(res.data.statement.id)
      } else {
        setBusy(false)
      }
    } catch (e) {
      setBusy(false)
      if (e.response?.data?.detail) {
        setError(e.response.data.detail)
      } else if (e.message === 'Network Error' || !e.response) {
        setError('Network / Connection Error. If the live backend service was sleeping (Render Free Tier), please wait 30 seconds for it to wake up and try again.')
      } else {
        setError('Upload failed. Please check the file format and try again.')
      }
    }
  }

  const onDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files?.[0]
    handleFile(file)
  }

  const isPdf = selectedFile?.name?.toLowerCase().endsWith('.pdf')

  return (
    <div className="panel">
      <h2>Upload Bank Statement (PDF / CSV / Excel)</h2>
      <p className="muted">Upload your PDF, CSV, or Excel (.xlsx/.xls) bank statement. Multi-page PDFs, table-less PDFs, and password-protected files are supported.</p>

      {isCloudHosted && isLocalApiTarget && (
        <div className="alert alert-error" style={{ marginBottom: '16px', background: '#fff3cd', color: '#856404', borderColor: '#ffeeba' }}>
          ⚠️ <strong>Deployment Warning:</strong> Live site is configured to target <code>{apiBase}</code>. Please set the <code>VITE_API_URL</code> environment variable in your Vercel/Render frontend settings (pointing to your backend URL e.g. <code>https://bank-statement-backend-xxxx.onrender.com</code>) and redeploy.
        </div>
      )}

      <div
        className={`dropzone ${dragOver ? 'dropzone-active' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.csv,.xlsx,.xls"
          hidden
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
        {busy ? (
          <p>{result?.statement?.status === 'processing' ? 'Processing statement... this can take a while for large PDFs.' : 'Uploading...'}</p>
        ) : (
          <p>Drag &amp; drop a <strong>PDF</strong>, <strong>CSV</strong>, or <strong>Excel</strong> file here, or click to browse</p>
        )}
      </div>

      <div style={{ marginTop: '12px', display: 'flex', gap: '10px', alignItems: 'center' }}>
        <input
          type="password"
          placeholder="PDF Password (if protected)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="form-control"
          style={{ maxWidth: '280px', padding: '8px 12px', borderRadius: '4px', border: '1px solid #ccc' }}
        />
        {selectedFile && isPdf && (
          <button
            className="btn btn-primary"
            onClick={() => handleFile(selectedFile, password)}
            disabled={busy}
          >
            Retry Upload with Password
          </button>
        )}
      </div>

      {error && <div className="alert alert-error" style={{ marginTop: '12px' }}>{error}</div>}

      {result?.statement?.status === 'processing' && (
        <div className="alert" style={{ marginTop: '12px' }}>
          Processing <strong>{result.statement.filename}</strong>... this page will update automatically.
        </div>
      )}

      {result?.statement?.status === 'failed' && (
        <div className="alert alert-error" style={{ marginTop: '12px' }}>
          Failed to process <strong>{result.statement.filename}</strong>: {result.statement.error}
        </div>
      )}

      {result?.statement?.status === 'done' && (
        <div className="alert alert-success" style={{ marginTop: '12px' }}>
          Parsed <strong>{result.statement.transaction_count}</strong> transactions from{' '}
          <strong>{result.statement.filename}</strong>.
          {result.statement.warnings?.length > 0 && (
            <ul>
              {result.statement.warnings.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          )}
        </div>
      )}

      <h3 style={{ marginTop: '24px' }}>Uploaded Statements</h3>
      {statements.length === 0 ? (
        <p className="muted">No statements uploaded yet.</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>File</th>
              <th>Uploaded</th>
              <th>Status</th>
              <th>Transactions</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {statements.map((s) => (
              <tr key={s.id}>
                <td>{s.filename}</td>
                <td>{new Date(s.uploaded_at).toLocaleString()}</td>
                <td>
                  {s.status === 'processing' && <span className="status-badge status-processing">Processing</span>}
                  {s.status === 'done' && <span className="status-badge status-done">Done</span>}
                  {s.status === 'failed' && <span className="status-badge status-failed" title={s.error}>Failed</span>}
                </td>
                <td>{s.transaction_count}</td>
                <td>
                  <button className="btn-link btn-danger" onClick={() => onDelete(s.id)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
