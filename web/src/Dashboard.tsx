import { useState, useEffect } from "react";

interface CostData {
  today: {
    today_cost_usd: number;
    budget_usd: number;
    remaining_usd: number;
    budget_used_pct: number;
  };
  session: {
    session_cost_usd: number;
    session_tokens: number;
  };
  weekly_cost_usd: number;
  monthly_cost_usd: number;
}

interface StatusData {
  status: string;
  version: string;
  uptime_seconds: number;
  provider: string;
  model: string;
  channels: string[];
  security: {
    sandbox: boolean;
    policy_engine: boolean;
    canary_tokens: boolean;
    audit_logging: boolean;
  };
}

export default function Dashboard() {
  const [costData, setCostData] = useState<CostData | null>(null);
  const [statusData, setStatusData] = useState<StatusData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  async function fetchData() {
    try {
      const [costRes, statusRes] = await Promise.all([
        fetch("/api/v1/cost/today").then((r) => r.json()).catch(() => null),
        fetch("/api/v1/status").then((r) => r.json()).catch(() => null),
      ]);
      if (costRes) setCostData(costRes);
      if (statusRes) setStatusData(statusRes);
    } catch {
      // Ignore fetch errors
    }
    setLoading(false);
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <header className="px-6 py-3 border-b border-gray-800">
        <h1 className="text-lg font-semibold">Dashboard</h1>
        <p className="text-xs text-gray-500">System status and cost tracking</p>
      </header>

      <div className="p-6 space-y-6">
        {loading ? (
          <div className="text-gray-500">Loading...</div>
        ) : (
          <>
            {/* Status Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card title="Status">
                <div className="flex items-center gap-2">
                  <div className={`w-3 h-3 rounded-full ${statusData?.status === "running" ? "bg-gulama-500" : "bg-red-500"}`} />
                  <span className="capitalize">{statusData?.status || "Unknown"}</span>
                </div>
                {statusData && (
                  <div className="mt-2 text-sm text-gray-400 space-y-1">
                    <p>Provider: {statusData.provider}/{statusData.model}</p>
                    <p>Version: {statusData.version}</p>
                  </div>
                )}
              </Card>

              <Card title="Today's Cost">
                <div className="text-2xl font-bold text-gulama-400">
                  ${costData?.today?.today_cost_usd?.toFixed(4) || "0.0000"}
                </div>
                <div className="text-sm text-gray-400 mt-1">
                  Budget: ${costData?.today?.budget_usd?.toFixed(2) || "10.00"} |
                  Used: {costData?.today?.budget_used_pct?.toFixed(1) || "0.0"}%
                </div>
                {costData?.today && (
                  <div className="mt-2 w-full bg-gray-700 rounded-full h-2">
                    <div
                      className="bg-gulama-500 h-2 rounded-full transition-all"
                      style={{ width: `${Math.min(costData.today.budget_used_pct, 100)}%` }}
                    />
                  </div>
                )}
              </Card>

              <Card title="Period Costs">
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-400">This week</span>
                    <span>${costData?.weekly_cost_usd?.toFixed(4) || "0.0000"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">This month</span>
                    <span>${costData?.monthly_cost_usd?.toFixed(4) || "0.0000"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Session tokens</span>
                    <span>{costData?.session?.session_tokens?.toLocaleString() || "0"}</span>
                  </div>
                </div>
              </Card>
            </div>

            {/* Security Status */}
            {statusData?.security && (
              <Card title="Security Status">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <SecurityBadge name="Sandbox" enabled={statusData.security.sandbox} />
                  <SecurityBadge name="Policy Engine" enabled={statusData.security.policy_engine} />
                  <SecurityBadge name="Canary Tokens" enabled={statusData.security.canary_tokens} />
                  <SecurityBadge name="Audit Logging" enabled={statusData.security.audit_logging} />
                </div>
              </Card>
            )}

            {/* Active Channels */}
            {statusData?.channels && (
              <Card title="Active Channels">
                <div className="flex flex-wrap gap-2">
                  {statusData.channels.map((ch) => (
                    <span
                      key={ch}
                      className="px-3 py-1 bg-gray-800 rounded-full text-sm text-gulama-400"
                    >
                      {ch}
                    </span>
                  ))}
                </div>
              </Card>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <h3 className="text-sm font-medium text-gray-400 mb-3">{title}</h3>
      {children}
    </div>
  );
}

function SecurityBadge({ name, enabled }: { name: string; enabled: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <div className={`w-2 h-2 rounded-full ${enabled ? "bg-gulama-500" : "bg-red-500"}`} />
      <span className="text-sm">{name}</span>
    </div>
  );
}
