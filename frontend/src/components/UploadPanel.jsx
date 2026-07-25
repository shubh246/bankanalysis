import { useRef, useState } from 'react'
import { uploadStatement } from '../api'

export default function UploadPanel({ statements, onUploaded, onDelete }) {
  const [dragOver, setDragOver] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const [password, setPassword] = useState('')
  const [selectedFile, setSelectedFile] = useState(null)
  const inputRef = useRef(null)

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
    } catch (e) {
      setError(e.response?.data?.detail || 'Upload failed. Please check the file and try again.')
    } finally {
      setBusy(false)
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
      <h2>Upload Bank Statement (PDF / CSV)</h2>
      <p className="muted">Upload your PDF or CSV bank statement. Multi-page PDFs, table-less PDFs, and password-protected files are supported.</p>

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
          accept=".pdf,.csv"
          hidden
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
        {busy ? (
          <p>Parsing PDF statement...</p>
        ) : (
          <p>Drag &amp; drop a <strong>PDF</strong> or <strong>CSV</strong> here, or click to browse</p>
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

      {result && (
        <div className="alert alert-success" style={{ marginTop: '12px' }}>
          Parsed <strong>{result.transactions.length}</strong> transactions from{' '}
          <strong>{result.statement.filename}</strong>.
          {result.warnings.length > 0 && (
            <ul>
              {result.warnings.map((w, i) => <li key={i}>{w}</li>)}
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
              <th>Transactions</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {statements.map((s) => (
              <tr key={s.id}>
                <td>{s.filename}</td>
                <td>{new Date(s.uploaded_at).toLocaleString()}</td>
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

