"use client";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import type { Activity, StatsPerson } from "@/lib/types";
const colors = [
  "#7770dd",
  "#39a99c",
  "#e6b463",
  "#ed8797",
  "#6c9fd8",
  "#ad7dc5",
  "#879a64",
  "#d18b64",
];
export function TimeChart({ data }: { data: Activity["daily"] }) {
  return (
    <div className="h-64 mt-6 min-w-0">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={data}
          margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
        >
          <defs>
            <linearGradient id="activityFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#7770dd" stopOpacity={0.23} />
              <stop offset="100%" stopColor="#7770dd" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid
            vertical={false}
            stroke="var(--border)"
            strokeDasharray="3 4"
          />
          <XAxis
            dataKey="date"
            tickLine={false}
            axisLine={false}
            fontSize={10}
            minTickGap={30}
          />
          <YAxis
            tickLine={false}
            axisLine={false}
            fontSize={10}
            allowDecimals={false}
          />
          <Tooltip
            contentStyle={{ borderRadius: 8, border: "1px solid #ddd" }}
          />
          <Area
            isAnimationActive={false}
            type="monotone"
            dataKey="count"
            name="Messages"
            stroke="#7770dd"
            strokeWidth={2}
            fill="url(#activityFill)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
export function ActivityBar({
  data,
}: {
  data: { label: string; count: number }[];
}) {
  return (
    <div className="h-52 mt-5 min-w-0">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ left: -25, right: 0 }}>
          <CartesianGrid
            vertical={false}
            stroke="var(--border)"
            strokeDasharray="3 4"
          />
          <XAxis
            dataKey="label"
            axisLine={false}
            tickLine={false}
            fontSize={10}
          />
          <YAxis
            axisLine={false}
            tickLine={false}
            fontSize={10}
            allowDecimals={false}
          />
          <Tooltip cursor={{ fill: "var(--muted)" }} />
          <Bar
            isAnimationActive={false}
            dataKey="count"
            name="Messages"
            fill="#8c85e5"
            radius={[3, 3, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
export function ShareChart({ people }: { people: StatsPerson[] }) {
  const shown = people
    .slice()
    .sort((a, b) => b.message_count - a.message_count)
    .slice(0, 8);
  return (
    <div className="flex flex-col sm:flex-row items-center gap-5">
      <div className="h-56 w-52 shrink-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              isAnimationActive={false}
              data={shown}
              dataKey="message_count"
              nameKey="name"
              innerRadius={62}
              outerRadius={86}
              paddingAngle={3}
              stroke="none"
            >
              {shown.map((p, i) => (
                <Cell key={p.id} fill={colors[i % colors.length]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="w-full space-y-3">
        {shown.map((p, i) => (
          <div key={p.id} className="flex gap-2 items-center text-xs">
            <span
              className="w-2 h-2 rounded-full shrink-0"
              style={{ background: colors[i % colors.length] }}
            />
            <span className="truncate">{p.name}</span>
            <span className="ml-auto text-secondary">
              {p.percentage.toFixed(1)}%
            </span>
          </div>
        ))}
        {people.length > 8 && (
          <p className="prose-note">Top 8 participants shown.</p>
        )}
      </div>
    </div>
  );
}
