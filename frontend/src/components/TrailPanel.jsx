import { useMemo, useState } from 'react'
import * as XLSX from 'xlsx'
import { searchTransactions, getFundFlow } from '../api'
import FundFlowGraph from './FundFlowGraph'

const COLUMNS = [
  { key: 'date', label: 'Date' },
  { key: 'counterparty', label: 'Name' },
  { key: 'channel', label: 'Channel' },
  { key: 'description', label: 'Description' },
  { key: 'debit', label: 'Debit' },
  { key: 'credit', label: 'Credit' },
  { key: 'balance', label: 'Balance' },
]

const fmt = (n) => (n == null ? '-' : new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(n))

export default function TrailPanel({ statements }) {
  const [filters, setFilters] = useState({
    amount: '',
    amount_tolerance: '0',
    counterparty: '',
    direction: '',
    statement_ids: [],
    date_from: '',
    date_to: '',
  })
  const [transactions, setTransactions] = useState(null)
  const [flow, setFlow] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [searched, setSearched] = useState(false)
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' })

  const sortedTransactions = useMemo(() => {
    if (!transactions) return transactions
    if (!sortConfig.key) return transactions
    const { key, direction } = sortConfig
    const dir = direction === 'asc' ? 1 : -1
    return [...transactions].sort((a, b) => {
      let va = a[key]
      let vb = b[key]
      if (va == null && vb == null) return 0
      if (va == null) return 1
      if (vb == null) return -1
      if (typeof va === 'string') va = va.toLowerCase()
      if (typeof vb === 'string') vb = vb.toLowerCase()
      if (va < vb) return -1 * dir
      if (va > vb) return 1 * dir
      return 0
    })
  }, [transactions, sortConfig])

  const handleSort = (key) => {
    setSortConfig((prev) =>
      prev.key === key
        ? { key, direction: prev.direction === 'asc' ? 'desc' : 'asc' }
        : { key, direction: 'asc' }
    )
  }

  const exportToExcel = () => {
    if (!sortedTransactions || sortedTransactions.length === 0) return
    const data = sortedTransactions.map((t) => ({
      Date: t.date ?? '',
      Name: t.counterparty ?? '',
      Channel: t.channel ?? '',
      Description: t.description ?? '',
      Debit: t.debit ?? '',
      Credit: t.credit ?? '',
      Balance: t.balance ?? '',
    }))
    const ws = XLSX.utils.json_to_sheet(data)
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, 'Transactions')
    XLSX.writeFile(wb, `transactions_${new Date().toISOString().slice(0, 10)}.xlsx`)
  }

  const update = (key) => (e) => setFilters((f) => ({ ...f, [key]: e.target.value }))

  const toggleStatement = (id) => {
    setFilters((f) => {
      const idStr = String(id)
      const has = f.statement_ids.includes(idStr)
      return {
        ...f,
        statement_ids: has
          ? f.statement_ids.filter((x) => x !== idStr)
          : [...f.statement_ids, idStr],
      }
    })
  }

  const buildParams = () => {
    const p = {}
    if (filters.amount !== '') p.amount = Number(filters.amount)
    if (filters.amount_tolerance !== '') p.amount_tolerance = Number(filters.amount_tolerance)
    if (filters.counterparty) p.counterparty = filters.counterparty
    if (filters.direction) p.direction = filters.direction
    if (filters.statement_ids.length > 0) p.statement_ids = filters.statement_ids.join(',')
    if (filters.date_from) p.date_from = filters.date_from
    if (filters.date_to) p.date_to = filters.date_to
    return p
  }

  const hasAnyFilter = () =>
    filters.amount !== '' ||
    filters.counterparty.trim() !== '' ||
    filters.direction !== '' ||
    filters.statement_ids.length > 0 ||
    filters.date_from !== '' ||
    filters.date_to !== ''

  const runSearch = async (e) => {
    e.preventDefault()
    if (!hasAnyFilter()) {
      setError('Enter at least one filter (amount, name, direction, statement, or date) before searching.')
      setSearched(false)
      return
    }
    setBusy(true)
    setError(null)
    try {
      const params = buildParams()
      const [txRes, flowRes] = await Promise.all([
        searchTransactions(params),
        getFundFlow(params),
      ])
      setTransactions(txRes.data)
      setFlow(flowRes.data)
      setSearched(true)
    } catch (e) {
      setError(e.response?.data?.detail || 'Search failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="panel">
      <h2>Trail by Amount &amp; Fund Flow</h2>
      <p className="muted">
        Search for a specific amount to trail every matching transaction, and see the fund flow
        with counterparty names.
      </p>

      <form className="filter-form" onSubmit={runSearch}>
        <div className="field">
          <label>Amount</label>
          <input type="number" step="0.01" placeholder="e.g. 5000" value={filters.amount} onChange={update('amount')} />
        </div>
        <div className="field">
          <label>Tolerance (+/-)</label>
          <input type="number" step="0.01" value={filters.amount_tolerance} onChange={update('amount_tolerance')} />
        </div>
        <div className="field">
          <label>Name contains</label>
          <input type="text" placeholder="e.g. John" value={filters.counterparty} onChange={update('counterparty')} />
        </div>
        <div className="field">
          <label>Direction</label>
          <select value={filters.direction} onChange={update('direction')}>
            <option value="">Any</option>
            <option value="credit">Credit (money in)</option>
            <option value="debit">Debit (money out)</option>
          </select>
        </div>
        <div className="field field-statements">
          <label>Statements ({filters.statement_ids.length === 0 ? 'all' : filters.statement_ids.length} selected)</label>
          <div className="checkbox-group">
            {statements.length === 0 && <span className="muted">No statements uploaded yet.</span>}
            {statements.map((s) => (
              <label key={s.id} className="checkbox-item">
                <input
                  type="checkbox"
                  checked={filters.statement_ids.includes(String(s.id))}
                  onChange={() => toggleStatement(s.id)}
                />
                {s.filename}
              </label>
            ))}
          </div>
        </div>
        <div className="field">
          <label>From date</label>
          <input type="date" value={filters.date_from} onChange={update('date_from')} />
        </div>
        <div className="field">
          <label>To date</label>
          <input type="date" value={filters.date_to} onChange={update('date_to')} />
        </div>
        <div className="field field-submit">
          <button type="submit" disabled={busy}>{busy ? 'Searching...' : 'Search'}</button>
        </div>
      </form>

      {error && <div className="alert alert-error">{error}</div>}

      {searched && (
        <>
          <div className="section-header">
            <h3>Matching Transactions ({transactions?.length ?? 0})</h3>
            {transactions && transactions.length > 0 && (
              <button type="button" className="btn-export" onClick={exportToExcel}>
                Export to Excel
              </button>
            )}
          </div>
          {transactions && transactions.length > 0 ? (
            <div className="table-scroll">
              <table className="table">
                <thead>
                  <tr>
                    {COLUMNS.map((col) => (
                      <th
                        key={col.key}
                        className="sortable"
                        onClick={() => handleSort(col.key)}
                      >
                        {col.label}
                        {sortConfig.key === col.key ? (sortConfig.direction === 'asc' ? ' ▲' : ' ▼') : ''}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {sortedTransactions.map((t) => (
                    <tr key={t.id}>
                      <td>{t.date ?? '-'}</td>
                      <td>{t.counterparty}</td>
                      <td>{t.channel}</td>
                      <td className="desc-cell">{t.description}</td>
                      <td className="num debit">{t.debit ? fmt(t.debit) : ''}</td>
                      <td className="num credit">{t.credit ? fmt(t.credit) : ''}</td>
                      <td className="num">{fmt(t.balance)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="muted">No transactions matched.</p>
          )}

          <h3>Fund Flow</h3>
          <FundFlowGraph data={flow} />
        </>
      )}
    </div>
  )
}
