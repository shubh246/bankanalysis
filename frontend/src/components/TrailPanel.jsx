import { useState } from 'react'
import { searchTransactions, getFundFlow } from '../api'
import FundFlowGraph from './FundFlowGraph'

const fmt = (n) => (n == null ? '-' : new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(n))

export default function TrailPanel({ statements }) {
  const [filters, setFilters] = useState({
    amount: '',
    amount_tolerance: '0',
    counterparty: '',
    direction: '',
    statement_id: '',
    date_from: '',
    date_to: '',
  })
  const [transactions, setTransactions] = useState(null)
  const [flow, setFlow] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [searched, setSearched] = useState(false)

  const update = (key) => (e) => setFilters((f) => ({ ...f, [key]: e.target.value }))

  const buildParams = () => {
    const p = {}
    if (filters.amount !== '') p.amount = Number(filters.amount)
    if (filters.amount_tolerance !== '') p.amount_tolerance = Number(filters.amount_tolerance)
    if (filters.counterparty) p.counterparty = filters.counterparty
    if (filters.direction) p.direction = filters.direction
    if (filters.statement_id) p.statement_id = Number(filters.statement_id)
    if (filters.date_from) p.date_from = filters.date_from
    if (filters.date_to) p.date_to = filters.date_to
    return p
  }

  const runSearch = async (e) => {
    e.preventDefault()
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
        <div className="field">
          <label>Statement</label>
          <select value={filters.statement_id} onChange={update('statement_id')}>
            <option value="">All</option>
            {statements.map((s) => (
              <option key={s.id} value={s.id}>{s.filename}</option>
            ))}
          </select>
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
          <h3>Matching Transactions ({transactions?.length ?? 0})</h3>
          {transactions && transactions.length > 0 ? (
            <div className="table-scroll">
              <table className="table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Name</th>
                    <th>Channel</th>
                    <th>Description</th>
                    <th>Debit</th>
                    <th>Credit</th>
                    <th>Balance</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((t) => (
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
