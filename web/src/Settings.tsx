import { useState } from "react";

export default function Settings() {
  const [activeTab, setActiveTab] = useState<"general" | "llm" | "security" | "channels">("general");

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <header className="px-6 py-3 border-b border-gray-800">
        <h1 className="text-lg font-semibold">Settings</h1>
        <p className="text-xs text-gray-500">Configure Gulama</p>
      </header>

      {/* Tab bar */}
      <div className="px-6 py-2 border-b border-gray-800 flex gap-4">
        {(["general", "llm", "security", "channels"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-3 py-1.5 text-sm rounded-lg transition-colors capitalize ${
              activeTab === tab
                ? "bg-gulama-600 text-white"
                : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      <div className="p-6 space-y-6">
        {activeTab === "general" && <GeneralSettings />}
        {activeTab === "llm" && <LLMSettings />}
        {activeTab === "security" && <SecuritySettings />}
        {activeTab === "channels" && <ChannelSettings />}
      </div>
    </div>
  );
}

function GeneralSettings() {
  return (
    <div className="space-y-4">
      <SettingGroup title="Autonomy Level">
        <select className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-full max-w-md">
          <option value="0">0 — Observer (ask before every action)</option>
          <option value="1">1 — Assistant (auto-read, ask before writes)</option>
          <option value="2" selected>2 — Co-pilot (auto safe, ask before shell/network)</option>
          <option value="3">3 — Autopilot-cautious (auto most, ask before destructive)</option>
          <option value="4">4 — Autopilot (auto everything except financial)</option>
        </select>
      </SettingGroup>

      <SettingGroup title="Persona">
        <select className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-full max-w-md">
          <option value="default">Default — Helpful, secure assistant</option>
          <option value="developer">Developer — Technical focus</option>
          <option value="researcher">Researcher — Analytical focus</option>
          <option value="creative">Creative — Writing & ideation</option>
          <option value="minimal">Minimal — Ultra-concise</option>
        </select>
      </SettingGroup>

      <SettingGroup title="Daily Budget">
        <div className="flex items-center gap-2">
          <span className="text-gray-400">$</span>
          <input
            type="number"
            defaultValue="10.00"
            step="0.50"
            min="0"
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-32"
          />
          <span className="text-gray-500 text-sm">USD per day</span>
        </div>
      </SettingGroup>
    </div>
  );
}

function LLMSettings() {
  return (
    <div className="space-y-4">
      <SettingGroup title="Provider">
        <select className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-full max-w-md">
          <option value="anthropic">Anthropic (Claude)</option>
          <option value="openai">OpenAI (GPT)</option>
          <option value="google">Google (Gemini)</option>
          <option value="deepseek">DeepSeek</option>
          <option value="qwen">Qwen (Alibaba)</option>
          <option value="groq">Groq</option>
          <option value="ollama">Ollama (Local)</option>
          <option value="together">Together AI</option>
          <option value="openai_compatible">Custom OpenAI-compatible</option>
        </select>
      </SettingGroup>

      <SettingGroup title="Model">
        <input
          type="text"
          defaultValue="claude-sonnet-4-5-20250929"
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-full max-w-md"
        />
      </SettingGroup>

      <SettingGroup title="API Base URL (optional)">
        <input
          type="text"
          placeholder="https://api.example.com/v1"
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-full max-w-md"
        />
        <p className="text-xs text-gray-500 mt-1">Only needed for self-hosted or custom endpoints</p>
      </SettingGroup>

      <SettingGroup title="Temperature">
        <input
          type="range"
          min="0"
          max="2"
          step="0.1"
          defaultValue="0.7"
          className="w-full max-w-md"
        />
      </SettingGroup>
    </div>
  );
}

function SecuritySettings() {
  return (
    <div className="space-y-4">
      <SettingGroup title="Security Features">
        <div className="space-y-3">
          <Toggle label="Sandbox Enabled" defaultChecked />
          <Toggle label="Policy Engine Enabled" defaultChecked />
          <Toggle label="Canary Token Detection" defaultChecked />
          <Toggle label="Egress Filtering + DLP" defaultChecked />
          <Toggle label="Audit Logging" defaultChecked />
          <Toggle label="Skill Signature Verification" defaultChecked />
        </div>
        <p className="text-xs text-gray-500 mt-3">
          Security features cannot be disabled without the --i-know-what-im-doing flag.
        </p>
      </SettingGroup>
    </div>
  );
}

function ChannelSettings() {
  return (
    <div className="space-y-4">
      <SettingGroup title="Telegram">
        <Toggle label="Enabled" />
        <input
          type="password"
          placeholder="Bot token (stored in encrypted vault)"
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-full max-w-md mt-2"
        />
      </SettingGroup>

      <SettingGroup title="Discord">
        <Toggle label="Enabled" />
        <input
          type="password"
          placeholder="Bot token"
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-full max-w-md mt-2"
        />
      </SettingGroup>

      <SettingGroup title="WhatsApp">
        <Toggle label="Enabled" />
        <p className="text-xs text-gray-500 mt-1">
          Requires WhatsApp Business API access
        </p>
      </SettingGroup>

      <SettingGroup title="Slack">
        <Toggle label="Enabled" />
        <input
          type="password"
          placeholder="Bot token (xoxb-...)"
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-full max-w-md mt-2"
        />
      </SettingGroup>
    </div>
  );
}

function SettingGroup({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <h3 className="text-sm font-medium text-gray-400 mb-3">{title}</h3>
      {children}
    </div>
  );
}

function Toggle({ label, defaultChecked = false }: { label: string; defaultChecked?: boolean }) {
  const [checked, setChecked] = useState(defaultChecked);
  return (
    <label className="flex items-center gap-3 cursor-pointer">
      <div
        onClick={() => setChecked(!checked)}
        className={`w-10 h-5 rounded-full transition-colors relative ${
          checked ? "bg-gulama-600" : "bg-gray-700"
        }`}
      >
        <div
          className={`w-4 h-4 bg-white rounded-full absolute top-0.5 transition-transform ${
            checked ? "translate-x-5" : "translate-x-0.5"
          }`}
        />
      </div>
      <span className="text-sm">{label}</span>
    </label>
  );
}
