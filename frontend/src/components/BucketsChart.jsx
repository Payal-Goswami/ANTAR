import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

const BUCKETS = [
  { key: 'both_right', label: 'Both correct', color: '#548d73' },
  { key: 'both_wrong', label: 'Both wrong', color: '#c7ced7' },
  { key: 'only_a', label: 'Only A correct', color: '#3e79b8' },
  { key: 'only_b', label: 'Only B correct', color: '#d49a4e' },
]

export default function BucketsChart({ buckets }) {
  const data = [{ name: 'Test rows', ...buckets }]
  return (
    <div className="bucket-chart" role="img" aria-label="Stacked count of pairwise correctness buckets">
      <ResponsiveContainer width="100%" height={118}>
        <BarChart data={data} layout="vertical" margin={{ top: 12, right: 12, bottom: 4, left: 12 }}>
          <CartesianGrid stroke="#edf0f3" strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" hide />
          <YAxis type="category" dataKey="name" hide />
          <Tooltip formatter={(value, name) => [value, BUCKETS.find((item) => item.key === name)?.label ?? name]} />
          {BUCKETS.map((bucket) => (
            <Bar
              key={bucket.key}
              dataKey={bucket.key}
              stackId="rows"
              fill={bucket.color}
              name={bucket.key}
              radius={bucket.key === 'both_right' ? [5, 0, 0, 5] : bucket.key === 'only_b' ? [0, 5, 5, 0] : 0}
              isAnimationActive={false}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
      <div className="bucket-legend">
        {BUCKETS.map((bucket) => (
          <span key={bucket.key}><i style={{ background: bucket.color }} />{bucket.label}</span>
        ))}
      </div>
    </div>
  )
}
