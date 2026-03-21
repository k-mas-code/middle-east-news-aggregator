/**
 * Bias Chart Component
 *
 * Displays bias score comparison chart using Recharts.
 * Validates: Requirement 5.3
 */

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import type { Comparison } from '../types/api';

interface BiasChartProps {
  comparison: Comparison;
}

export function BiasChart({ comparison }: BiasChartProps) {
  const data = Object.entries(comparison.media_bias_scores).map(([media, sentiment]) => ({
    name: media,
    polarity: sentiment.polarity,
    subjectivity: sentiment.subjectivity,
    label: sentiment.label,
  }));

  return (
    <div className="bias-chart">
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" />
          <YAxis domain={[-1, 1]} />
          <Tooltip />
          <Legend />
          <Bar dataKey="polarity" fill="#2196f3" name="極性" />
          <Bar dataKey="subjectivity" fill="#ff9800" name="主観性" />
        </BarChart>
      </ResponsiveContainer>

      <div className="bias-labels">
        {data.map((item) => (
          <div key={item.name} className="bias-label">
            <strong>{item.name}:</strong> {item.label}
          </div>
        ))}
      </div>
    </div>
  );
}
