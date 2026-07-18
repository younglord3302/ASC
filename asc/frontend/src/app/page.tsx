"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Play,
  Square,
  Activity,
  Users,
  Database,
  BarChart3,
  Globe,
  ChevronRight,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Loader2,
  MessageSquare,
  GitBranch,
  Shield,
  FileText,
  Code,
  Server,
  Palette,
  BookOpen,
  Zap,
  Search,
  Layers,
} from "lucide-react";

// ─── Types ──────────────────────────────────────────────────────────────────

interface Agent {
  role: string;
  status: string;
  current_task: string | null;
  progress: number;
  uptime: number;
}

interface Workflow {
  id: string;
  project_name: string;
  status: string;
  progress: number;
  current_agent: string | null;
  created_at: string;
  updated_at: string;
}

interface Message {
  from: string;
  type: string;
  content: string;
  timestamp: string;
}

// ─── Agent Config ───────────────────────────────────────────────────────────

const AGENT_META: Record<string, { icon: any; color: string; label: string }> = {
  ceo: { icon: Zap, color: "text-purple-500", label: "CEO" },
  product_manager: { icon: FileText, color: "text-blue-500", label: "Product Manager" },
  researcher: { icon: Search, color: "text-cyan-500", label: "Researcher" },
  architect: { icon: Layers, color: "text-indigo-500", label: "Architect" },
  ui_ux: { icon: Palette, color: "text-pink-500", label: "UI/UX Designer" },
  frontend: { icon: Code, color: "text-orange-500", label: "Frontend Engineer" },
  backend: { icon: Server, color: "text-green-500", label: "Backend Engineer" },
  database: { icon: Database, color: "text-teal-500", label: "Database Engineer" },
  devops: { icon: Globe, color: "text-red-500", label: "DevOps Engineer" },
  security: { icon: Shield, color: "text-yellow-500", label: "Security Engineer" },
  qa: { icon: CheckCircle2, color: "text-emerald-500", label: "QA Engineer" },
  reviewer: { icon: MessageSquare, color: "text-violet-500", label: "Reviewer" },
  documentation: { icon: BookOpen, color: "text-sky-500", label: "Documentation" },
  memory: { icon: Database, color: "text-rose-500", label: "Memory Agent" },
};

// ─── API Client ─────────────────────────────────────────────────────────────

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function apiGet(path: string) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

async function apiPost(path: string, body?: any) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// ─── Components ─────────────────────────────────────────────────────────────

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    idle: "bg-gray-400",
    working: "bg-green-500 agent-working",
    waiting: "bg-yellow-500",
    done: "bg-blue-500",
    failed: "bg-red-500",
  };
  return (
    <span className={`inline-block w-2.5 h-2.5 rounded-full ${colors[status] || "bg-gray-400"}`} />
  );
}

function ProgressBar({ value, className = "" }: { value: number; className?: string }) {
  return (
    <div className={`w-full bg-gray-200 rounded-full h-2 overflow-hidden ${className}`}>
      <div
        className="h-full bg-gradient-to-r from-primary-500 to-primary-600 rounded-full transition-all duration-500 progress-animated"
        style={{ width: `${Math.min(value * 100, 100)}%` }}
      />
    </div>
  );
}

function AgentCard({ agent }: { agent: Agent }) {
  const meta = AGENT_META[agent.role] || { icon: Activity, color: "text-gray-500", label: agent.role };
  const Icon = meta.icon;
  return (
    <div className="bg-white rounded-xl border border-surface-200 p-4 hover:shadow-md transition-shadow">
      <div className="flex items-center gap-3 mb-3">
        <div className={`p-2 rounded-lg bg-surface-50 ${meta.color}`}>
          <Icon className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-sm truncate">{meta.label}</p>
          <p className="text-xs text-surface-500 truncate">{agent.current_task || "Idle"}</p>
        </div>
        <StatusDot status={agent.status} />
      </div>
      <ProgressBar value={agent.progress} />
      <p className="text-xs text-surface-400 mt-2">
        <Clock className="w-3 h-3 inline mr-1" />
        {agent.uptime.toFixed(0)}s
      </p>
    </div>
  );
}

function WorkflowCard({ workflow }: { workflow: Workflow }) {
  const statusColors: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-800",
    running: "bg-blue-100 text-blue-800",
    waiting_approval: "bg-purple-100 text-purple-800",
    completed: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
  };
  const statusIcons: Record<string, any> = {
    pending: Clock,
    running: Loader2,
    waiting_approval: AlertCircle,
    completed: CheckCircle2,
    failed: XCircle,
  };
  const StatusIcon = statusIcons[workflow.status] || Activity;

  return (
    <div className="bg-white rounded-xl border border-surface-200 p-4 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-sm truncate">{workflow.project_name}</h3>
        <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors[workflow.status] || ""}`}>
          <StatusIcon className="w-3 h-3" />
          {workflow.status.replace("_", " ")}
        </span>
      </div>
      <ProgressBar value={workflow.progress} className="mb-2" />
      <div className="flex items-center justify-between text-xs text-surface-500">
        <span>
          <Clock className="w-3 h-3 inline mr-1" />
          {new Date(workflow.created_at).toLocaleTimeString()}
        </span>
        {workflow.current_agent && (
          <span className="text-primary-600 font-medium">
            {AGENT_META[workflow.current_agent]?.label || workflow.current_agent}
          </span>
        )}
      </div>
    </div>
  );
}

// ─── Main Dashboard ─────────────────────────────────────────────────────────

export default function Dashboard() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"agents" | "workflows" | "memory">("agents");
  const [memoryStats, setMemoryStats] = useState<any>(null);
  const [costData, setCostData] = useState<any>(null);

  const fetchData = useCallback(async () => {
    try {
      const [agentsData, workflowsData, costData] = await Promise.all([
        apiGet("/dashboard/agents"),
        apiGet("/dashboard/workflows"),
        apiGet("/dashboard/costs"),
      ]);
      setAgents(agentsData);
      setWorkflows(workflowsData);
      setCostData(costData);
    } catch (err) {
      console.error("Failed to fetch dashboard data:", err);
    }
  }, []);

  const fetchMemoryStats = useCallback(async () => {
    try {
      const stats = await apiGet("/memory/stats");
      setMemoryStats(stats);
    } catch (err) {
      console.error("Failed to fetch memory stats:", err);
    }
  }, []);

  useEffect(() => {
    fetchData();
    fetchMemoryStats();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, [fetchData, fetchMemoryStats]);

  const handleSubmit = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    try {
      await apiPost("/workflows", {
        user_prompt: prompt,
        mode: "approval",
      });
      setPrompt("");
      await fetchData();
    } catch (err) {
      console.error("Failed to start workflow:", err);
    } finally {
      setLoading(false);
    }
  };

  const activeWorkflows = workflows.filter((w) => w.status === "running" || w.status === "waiting_approval");
  const completedWorkflows = workflows.filter((w) => w.status === "completed");

  return (
    <div className="min-h-screen bg-surface-50">
      {/* Header */}
      <header className="bg-white border-b border-surface-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-primary-700 rounded-lg flex items-center justify-center">
                <Zap className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-bold">ASC</h1>
                <p className="text-xs text-surface-500">Autonomous Software Company</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 text-sm text-surface-500">
                <Activity className="w-4 h-4 text-green-500" />
                <span>{activeWorkflows.length} active</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-surface-500">
                <CheckCircle2 className="w-4 h-4 text-blue-500" />
                <span>{completedWorkflows.length} done</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Prompt Input */}
        <div className="bg-white rounded-2xl border border-surface-200 p-6 mb-8 shadow-sm">
          <h2 className="text-lg font-semibold mb-1">What do you want to build?</h2>
          <p className="text-sm text-surface-500 mb-4">
            Describe your software project and ASC will plan, build, test, and deploy it.
          </p>
          <div className="flex gap-3">
            <input
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
              placeholder="e.g., Build a hospital management SaaS with mobile apps, admin dashboard, and AI scheduling..."
              className="flex-1 px-4 py-3 rounded-xl border border-surface-300 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent text-sm"
              disabled={loading}
            />
            <button
              onClick={handleSubmit}
              disabled={loading || !prompt.trim()}
              className="px-6 py-3 bg-primary-600 text-white rounded-xl font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              {loading ? "Starting..." : "Build"}
            </button>
          </div>
        </div>

        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-xl border border-surface-200 p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-purple-50">
                <Users className="w-5 h-5 text-purple-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{agents.length}</p>
                <p className="text-xs text-surface-500">Active Agents</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-surface-200 p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-50">
                <GitBranch className="w-5 h-5 text-blue-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{workflows.length}</p>
                <p className="text-xs text-surface-500">Total Workflows</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-surface-200 p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-green-50">
                <Database className="w-5 h-5 text-green-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{memoryStats?.total || 0}</p>
                <p className="text-xs text-surface-500">Memory Entries</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-surface-200 p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-orange-50">
                <BarChart3 className="w-5 h-5 text-orange-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{costData?.total_tokens?.toLocaleString() || 0}</p>
                <p className="text-xs text-surface-500">
                  Total Tokens
                  {costData?.total_cost ? ` · $${costData.total_cost.toFixed(4)}` : ""}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6 bg-surface-100 rounded-lg p-1 w-fit">
          {[
            { id: "agents", label: "Agent Panel", icon: Users },
            { id: "workflows", label: "Workflows", icon: GitBranch },
            { id: "memory", label: "Memory Explorer", icon: Database },
          ].map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? "bg-white text-surface-900 shadow-sm"
                    : "text-surface-500 hover:text-surface-700"
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Tab Content */}
        {activeTab === "agents" && (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {agents.map((agent) => (
              <AgentCard key={agent.role} agent={agent} />
            ))}
          </div>
        )}

        {activeTab === "workflows" && (
          <div>
            {workflows.length === 0 ? (
              <div className="text-center py-16 text-surface-400">
                <GitBranch className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p className="text-lg font-medium">No workflows yet</p>
                <p className="text-sm">Enter a prompt above to start building</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {workflows.map((wf) => (
                  <WorkflowCard key={wf.id} workflow={wf} />
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === "memory" && (
          <div className="bg-white rounded-xl border border-surface-200 p-6">
            <h3 className="font-semibold mb-4">Memory System</h3>
            {memoryStats ? (
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                {Object.entries(memoryStats).filter(([k]) => k !== "total").map(([tier, count]) => (
                  <div key={tier} className="text-center p-4 rounded-lg bg-surface-50">
                    <p className="text-2xl font-bold text-primary-600">{count as number}</p>
                    <p className="text-xs text-surface-500 capitalize">{tier.replace("_", " ")}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-surface-400 text-sm">Loading memory stats...</p>
            )}
          </div>
        )}
      </main>
    </div>
  );
}