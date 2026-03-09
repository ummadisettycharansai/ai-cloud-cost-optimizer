/**
 * BudgetGauge — Circular progress ring for budget utilization display.
 * Props:
 *   utilization: number (0–100 percent)
 *   label: string
 *   limit: number (monthly budget limit)
 *   spent: number (current spend)
 */

interface BudgetGaugeProps {
  utilization: number;
  label: string;
  limit: number;
  spent: number;
}

const RADIUS = 36;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

function getSeverityColor(pct: number): string {
  if (pct >= 100) return '#ef4444';   // red-500
  if (pct >= 80)  return '#f97316';   // orange-500
  if (pct >= 60)  return '#eab308';   // yellow-500
  return '#22c55e';                    // green-500
}

export default function BudgetGauge({ utilization, label, limit, spent }: BudgetGaugeProps) {
  const clamped = Math.min(utilization, 100);
  const dashOffset = CIRCUMFERENCE * (1 - clamped / 100);
  const color = getSeverityColor(utilization);

  return (
    <div className="flex flex-col items-center gap-2 p-3">
      <svg width="96" height="96" viewBox="0 0 96 96">
        {/* Background track */}
        <circle
          cx="48" cy="48" r={RADIUS}
          fill="none"
          stroke="#27272a"
          strokeWidth="8"
        />
        {/* Progress arc */}
        <circle
          cx="48" cy="48" r={RADIUS}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
          transform="rotate(-90 48 48)"
          style={{ transition: 'stroke-dashoffset 0.6s ease, stroke 0.3s ease' }}
        />
        {/* Center text */}
        <text x="48" y="44" textAnchor="middle" fill="white" fontSize="14" fontWeight="bold">
          {clamped.toFixed(0)}%
        </text>
        <text x="48" y="60" textAnchor="middle" fill="#a1a1aa" fontSize="9">
          used
        </text>
      </svg>
      <div className="text-center">
        <p className="text-sm font-medium text-zinc-200 truncate max-w-[120px]">{label}</p>
        <p className="text-xs text-zinc-500">
          ${spent.toLocaleString()} / ${limit.toLocaleString()}
        </p>
      </div>
    </div>
  );
}
