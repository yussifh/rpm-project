import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { User } from "@/types/auth";

const ROLE_COLORS: Record<string, string> = {
  admin: "#14555A",
  patient: "#E2A63B",
};

interface UsersByRoleChartProps {
  users: User[];
}

export function UsersByRoleChart({ users }: UsersByRoleChartProps) {
  const counts: Record<string, number> = { admin: 0, patient: 0 };
  for (const user of users) counts[user.role] += 1;

  const data = Object.entries(counts)
    .filter(([, count]) => count > 0)
    .map(([role, count]) => ({ name: role, value: count }));

  if (data.length === 0) {
    return <p className="text-sm text-ink-soft">No users to display.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie data={data} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80} paddingAngle={2}>
          {data.map((entry) => (
            <Cell key={entry.name} fill={ROLE_COLORS[entry.name]} />
          ))}
        </Pie>
        <Tooltip />
      </PieChart>
    </ResponsiveContainer>
  );
}
