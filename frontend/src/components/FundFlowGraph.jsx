import { useMemo } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MarkerType,
} from 'reactflow'
import 'reactflow/dist/style.css'

const fmt = (n) => new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(n)

const MAX_COUNTERPARTY_NODES = 40
const ANIMATE_BELOW_NODE_COUNT = 15

export default function FundFlowGraph({ data }) {
  const { nodes, edges, hiddenCount } = useMemo(() => {
    if (!data || data.nodes.length === 0) return { nodes: [], edges: [], hiddenCount: 0 }

    const account = data.nodes.find((n) => n.kind === 'account')
    const allCounterparties = [...data.nodes.filter((n) => n.kind === 'counterparty')]
      .sort((a, b) => (b.total_in + b.total_out) - (a.total_in + a.total_out))

    const counterparties = allCounterparties.slice(0, MAX_COUNTERPARTY_NODES)
    const overflow = allCounterparties.slice(MAX_COUNTERPARTY_NODES)

    const idRemap = new Map()
    if (overflow.length > 0) {
      const otherId = 'cp:__other__'
      const otherTotals = overflow.reduce(
        (acc, cp) => ({ in: acc.in + cp.total_in, out: acc.out + cp.total_out }),
        { in: 0, out: 0 }
      )
      counterparties.push({
        id: otherId,
        label: `Other (${overflow.length} counterparties)`,
        kind: 'counterparty',
        total_in: otherTotals.in,
        total_out: otherTotals.out,
      })
      overflow.forEach((cp) => idRemap.set(cp.id, otherId))
    }

    const centerX = 450
    const centerY = 320
    const radius = Math.max(260, counterparties.length * 28)

    const rfNodes = []
    if (account) {
      rfNodes.push({
        id: account.id,
        position: { x: centerX, y: centerY },
        data: {
          label: (
            <div>
              <div className="node-title">{account.label}</div>
              <div className="node-sub">In: ₹{fmt(account.total_in)}</div>
              <div className="node-sub">Out: ₹{fmt(account.total_out)}</div>
            </div>
          ),
        },
        style: nodeStyle('#1d4ed8'),
      })
    }

    counterparties.forEach((cp, i) => {
      const angle = (i / counterparties.length) * 2 * Math.PI
      rfNodes.push({
        id: cp.id,
        position: {
          x: centerX + radius * Math.cos(angle),
          y: centerY + radius * Math.sin(angle),
        },
        data: {
          label: (
            <div>
              <div className="node-title">{cp.label}</div>
              {cp.total_in > 0 && <div className="node-sub node-in">Sent: ₹{fmt(cp.total_in)}</div>}
              {cp.total_out > 0 && <div className="node-sub node-out">Received: ₹{fmt(cp.total_out)}</div>}
            </div>
          ),
        },
        style: nodeStyle('#334155'),
      })
    })

    // Remap edges touching an overflowed counterparty onto the aggregate "Other" node,
    // merging any that land on the same remapped source/target/direction.
    const edgeMap = new Map()
    for (const e of data.edges) {
      const source = idRemap.get(e.source) || e.source
      const target = idRemap.get(e.target) || e.target
      const key = `${source}|${target}|${e.direction}`
      const existing = edgeMap.get(key)
      if (existing) {
        existing.amount += e.amount
        existing.count += e.count
      } else {
        edgeMap.set(key, { source, target, direction: e.direction, amount: e.amount, count: e.count })
      }
    }

    const shouldAnimate = rfNodes.length < ANIMATE_BELOW_NODE_COUNT
    const rfEdges = [...edgeMap.values()].map((e, i) => ({
      id: `e${i}`,
      source: e.source,
      target: e.target,
      label: `₹${fmt(e.amount)} (${e.count}x)`,
      animated: shouldAnimate,
      style: { stroke: e.direction === 'in' ? '#16a34a' : '#dc2626', strokeWidth: 2 },
      labelStyle: { fill: '#e2e8f0', fontSize: 11 },
      labelBgStyle: { fill: '#0f172a', fillOpacity: 0.85 },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: e.direction === 'in' ? '#16a34a' : '#dc2626',
      },
    }))

    return { nodes: rfNodes, edges: rfEdges, hiddenCount: overflow.length }
  }, [data])

  if (!data || nodes.length === 0) {
    return <p className="muted">No transactions match this filter yet.</p>
  }

  return (
    <>
      {hiddenCount > 0 && (
        <p className="muted" style={{ marginBottom: 8 }}>
          Showing top {MAX_COUNTERPARTY_NODES} counterparties by volume; {hiddenCount} more grouped into "Other".
        </p>
      )}
      <div style={{ height: 560, background: '#0f172a', borderRadius: 8 }}>
        <ReactFlow nodes={nodes} edges={edges} fitView fitViewOptions={{ padding: 0.25 }}>
          <Background color="#1e293b" gap={16} />
          <Controls />
        </ReactFlow>
      </div>
    </>
  )
}

function nodeStyle(borderColor) {
  return {
    background: '#111827',
    color: '#f1f5f9',
    border: `2px solid ${borderColor}`,
    borderRadius: 8,
    padding: 8,
    fontSize: 12,
    width: 170,
  }
}
