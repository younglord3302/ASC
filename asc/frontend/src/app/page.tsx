"use client";

import { useState, useEffect, useCallback } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";
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
  LogOut,
} from "lucide-react";

import {
  apiGet,
  apiPost,
  isAuthenticated,
  clearToken,
  fetchMe,
  type CurrentUser,
} from "@/lib/auth";
import { useLiveWorkflow } from "@/lib/useLiveWorkflow";
import LoginForm from "@/components/LoginForm";

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
  error?: string | null;
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

function WorkflowCard({
  workflow,
  selected = false,
  onSelect,
}: {
  workflow: Workflow;
  selected?: boolean;
  onSelect?: () => void;
}) {
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
    <button
      type="button"
      onClick={onSelect}
      className={`text-left bg-white rounded-xl border p-4 hover:shadow-md transition-shadow ${
        selected ? "border-primary-400 ring-2 ring-primary-200" : "border-surface-200"
      }`}
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-sm truncate">{workflow.project_name}</h3>
        <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors[workflow.status] || ""}`}>
          <StatusIcon className="w-3 h-3" />
          {workflow.status.replace("_", " ")}
        </span>
      </div>
      <ProgressBar value={workflow.progress} className="mb-2" />
      {workflow.status === "failed" && workflow.error && (
        <p className="text-[11px] text-red-600 mb-2 line-clamp-2">{workflow.error}</p>
      )}
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
    </button>
  );
}

// ─── Main Dashboard ─────────────────────────────────────────────────────────

export default function Dashboard() {
  const [authed, setAuthed] = useState(false);
  const [authChecked, setAuthChecked] = useState(false);
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"agents" | "workflows" | "memory" | "costs" | "deployment">("agents");
  const [memoryStats, setMemoryStats] = useState<any>(null);
  const [costData, setCostData] = useState<any>(null);
  const [deploymentData, setDeploymentData] = useState<any>(null);
  const [selectedWfForDeploy, setSelectedWfForDeploy] = useState<string | null>(null);
  const [deployLoading, setDeployLoading] = useState(false);
  const [deployMsg, setDeployMsg] = useState<string | null>(null);

  // Memory Explorer: semantic/keyword search + knowledge-graph traversal.
  const [memQuery, setMemQuery] = useState("");
  const [memSemantic, setMemSemantic] = useState(true);
  const [memResults, setMemResults] = useState<any[]>([]);
  const [memLoading, setMemLoading] = useState(false);
  const [memError, setMemError] = useState<string | null>(null);
  const [relSource, setRelSource] = useState<{ id: string; content: string } | null>(null);
  const [relResults, setRelResults] = useState<any[] | null>(null);
  const [relLoading, setRelLoading] = useState(false);

  // Workflow transcript: expand a card to view its live agent conversation.
  const [selectedWf, setSelectedWf] = useState<string | null>(null);
  const [wfMessages, setWfMessages] = useState<any[]>([]);
  const [wfMsgLoading, setWfMsgLoading] = useState(false);

  // Validate any stored token on mount, and react to auth loss (401).
  useEffect(() => {
    let cancelled = false;
    async function check() {
      if (!isAuthenticated()) {
        if (!cancelled) {
          setAuthed(false);
          setAuthChecked(true);
        }
        return;
      }
      try {
        const me = await fetchMe();
        if (!cancelled) {
          setUser(me);
          setAuthed(true);
        }
      } catch {
        if (!cancelled) setAuthed(false);
      } finally {
        if (!cancelled) setAuthChecked(true);
      }
    }
    check();

    const onUnauthorized = () => {
      setAuthed(false);
      setUser(null);
    };
    window.addEventListener("asc:unauthorized", onUnauthorized);
    return () => {
      cancelled = true;
      window.removeEventListener("asc:unauthorized", onUnauthorized);
    };
  }, []);

  const handleLoginSuccess = useCallback(async () => {
    setAuthed(true);
    try {
      setUser(await fetchMe());
    } catch {
      /* ignore */
    }
  }, []);

  const handleLogout = useCallback(() => {
    clearToken();
    setAuthed(false);
    setUser(null);
  }, []);

  const fetchData = useCallback(async () => {
    try {
      const [agentsData, workflowsData, costData, deploymentData] = await Promise.all([
        apiGet("/dashboard/agents"),
        apiGet("/dashboard/workflows"),
        apiGet("/dashboard/costs"),
        apiGet("/dashboard/deployment"),
      ]);
      setAgents(agentsData);
      setWorkflows(workflowsData);
      setCostData(costData);
      setDeploymentData(deploymentData);
    } catch (err) {
      console.error("Failed to fetch dashboard data:", err);
    }
  }, []);

  const fetchDeployment = useCallback(async () => {
    try {
      setDeploymentData(await apiGet("/dashboard/deployment"));
    } catch (err) {
      console.error("Failed to fetch deployment:", err);
    }
  }, []);

  const deploy = useCallback(async (workflowId: string) => {
    setDeployLoading(true);
    setDeployMsg(null);
    try {
      const data = await apiPost(`/workflows/${workflowId}/deploy`);
      setDeployMsg(`Deployed to ${data.deployments?.[0]?.url ?? "production"}`);
      await fetchDeployment();
    } catch (err: any) {
      setDeployMsg(err?.message || "Deploy failed");
    } finally {
      setDeployLoading(false);
      setSelectedWfForDeploy(null);
    }
  }, [fetchDeployment]);

  const fetchMemoryStats = useCallback(async () => {
    try {
      const stats = await apiGet("/memory/stats");
      setMemoryStats(stats);
    } catch (err) {
      console.error("Failed to fetch memory stats:", err);
    }
  }, []);

  const runMemSearch = useCallback(async () => {
    const q = memQuery.trim();
    if (!q) return;
    setMemLoading(true);
    setMemError(null);
    setRelSource(null);
    setRelResults(null);
    try {
      const data = await apiPost("/memory/search", {
        query: q,
        semantic: memSemantic,
      });
      setMemResults(data.results || []);
    } catch (err: any) {
      setMemError(err?.message || "Search failed");
      setMemResults([]);
    } finally {
      setMemLoading(false);
    }
  }, [memQuery, memSemantic]);

  const fetchMessages = useCallback(async (workflowId: string) => {
    setWfMsgLoading(true);
    setWfMessages([]);
    try {
      const data = await apiGet(`/workflows/${workflowId}/messages`);
      setWfMessages(data.messages || []);
    } catch (err) {
      console.error("Failed to fetch workflow messages:", err);
    } finally {
      setWfMsgLoading(false);
    }
  }, []);

  const toggleWorkflow = useCallback((workflowId: string) => {
    setSelectedWf((cur) => {
      const next = cur === workflowId ? null : workflowId;
      if (next) fetchMessages(next);
      else setWfMessages([]);
      return next;
    });
  }, [fetchMessages]);

  // Merge a live WebSocket frame into local state for the selected workflow.
  const mergeLive = useCallback((update: any) => {
    if (update.progress != null) {
      setWorkflows((prev) =>
        prev.map((w) =>
          w.id === selectedWf ? { ...w, progress: update.progress, current_agent: update.current_agent ?? w.current_agent } : w,
        ),
      );
    }
    if (Array.isArray(update.messages) && update.messages.length > 0) {
      setWfMessages(update.messages);
    }
  }, [selectedWf]);

  useLiveWorkflow(selectedWf, mergeLive);

  const fetchRelated = useCallback(async (id: string, content: string) => {
    setRelSource({ id, content });
    setRelLoading(true);
    setRelResults(null);
    try {
      const data = await apiGet(`/memory/related/${id}`);
      setRelResults(data.related || []);
    } catch (err) {
      console.error("Failed to fetch related memories:", err);
      setRelResults([]);
    } finally {
      setRelLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!authed) return;
    fetchData();
    fetchMemoryStats();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, [authed, fetchData, fetchMemoryStats]);

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

  // Auth gate: show nothing until we've checked, then login screen if needed.
  if (!authChecked) {
    return (
      <div className="min-h-screen bg-surface-50 flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-primary-500" />
      </div>
    );
  }
  if (!authed) {
    return <LoginForm onSuccess={handleLoginSuccess} />;
  }

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
              {user && (
                <span className="hidden sm:inline text-sm text-surface-500 max-w-[180px] truncate">
                  {user.email}
                </span>
              )}
              <button
                onClick={handleLogout}
                title="Sign out"
                className="flex items-center gap-1.5 text-sm text-surface-500 hover:text-surface-800 transition-colors"
              >
                <LogOut className="w-4 h-4" />
                <span className="hidden sm:inline">Sign out</span>
              </button>
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
            { id: "costs", label: "Cost Dashboard", icon: BarChart3 },
            { id: "deployment", label: "Deployment", icon: Globe },
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
                  <WorkflowCard
                    key={wf.id}
                    workflow={wf}
                    selected={selectedWf === wf.id}
                    onSelect={() => toggleWorkflow(wf.id)}
                  />
                ))}
              </div>
            )}

            {selectedWf && (
              <div className="mt-6 bg-white rounded-xl border border-surface-200 p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold">Agent Conversation</h3>
                  <button
                    onClick={() => toggleWorkflow(selectedWf)}
                    className="text-sm text-surface-500 hover:text-surface-800"
                  >
                    Close
                  </button>
                </div>
                {wfMsgLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin text-primary-500" />
                ) : wfMessages.length === 0 ? (
                  <p className="text-sm text-surface-400">No messages yet.</p>
                ) : (
                  <ul className="space-y-3 max-h-[28rem] overflow-auto pr-1">
                    {wfMessages.map((m, i) => {
                      const role = m.from as keyof typeof AGENT_META;
                      const meta = AGENT_META[role];
                      return (
                        <li key={m.id || i} className="flex gap-3">
                          <span className={`mt-1 w-2 h-2 rounded-full shrink-0 ${meta?.color || "text-surface-400"}`} />
                          <div className="min-w-0">
                            <p className="text-xs font-medium text-surface-600">
                              {meta?.label || m.from || "System"}
                              {m.type ? <span className="ml-1 text-surface-400">· {m.type}</span> : null}
                            </p>
                            <p className="text-sm text-surface-700 whitespace-pre-wrap break-words">
                              {m.content}
                            </p>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === "memory" && (
          <div className="space-y-6">
            {/* Tier breakdown */}
            <div className="bg-white rounded-xl border border-surface-200 p-6">
              <h3 className="font-semibold mb-4">Memory System</h3>
              {memoryStats ? (
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                  {Object.entries(memoryStats).filter(([k]) => k !== "total" && k !== "backend").map(([tier, count]) => (
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

            {/* Semantic Search + Knowledge Graph */}
            <div className="bg-white rounded-xl border border-surface-200 p-6">
              <h3 className="font-semibold mb-1">Search & Knowledge Graph</h3>
              <p className="text-sm text-surface-500 mb-4">
                Recall memories by meaning (semantic) or exact text, then expand a node to
                traverse its relationships in the knowledge graph.
              </p>

              <div className="flex flex-wrap gap-3 items-center mb-4">
                <input
                  type="text"
                  value={memQuery}
                  onChange={(e) => setMemQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && runMemSearch()}
                  placeholder="Search memory (e.g. database schema design)..."
                  className="flex-1 min-w-[240px] px-4 py-2.5 rounded-lg border border-surface-300 focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
                  disabled={memLoading}
                />
                <button
                  onClick={() => setMemSemantic((v) => !v)}
                  className={`px-3 py-2.5 rounded-lg text-sm font-medium border transition-colors ${
                    memSemantic
                      ? "bg-primary-50 border-primary-300 text-primary-700"
                      : "bg-white border-surface-300 text-surface-600 hover:bg-surface-50"
                  }`}
                  title="Toggle semantic (vector) vs keyword search"
                >
                  {memSemantic ? "Semantic" : "Keyword"}
                </button>
                <button
                  onClick={runMemSearch}
                  disabled={memLoading || !memQuery.trim()}
                  className="px-4 py-2.5 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-50 flex items-center gap-2"
                >
                  {memLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                  Search
                </button>
              </div>

              {memError && (
                <p className="text-sm text-red-600 mb-3">{memError}</p>
              )}

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* Results list */}
                <div>
                  <p className="text-xs font-semibold text-surface-500 uppercase tracking-wide mb-2">
                    {memResults.length > 0 ? `${memResults.length} results` : "Results"}
                  </p>
                  {memResults.length === 0 ? (
                    <p className="text-sm text-surface-400">
                      {memQuery.trim() ? "No matching memories." : "Run a search to recall memories."}
                    </p>
                  ) : (
                    <ul className="space-y-2 max-h-96 overflow-auto pr-1">
                      {memResults.map((m) => (
                        <li key={m.id}>
                          <button
                            onClick={() => fetchRelated(m.id, m.content)}
                            className={`w-full text-left p-3 rounded-lg border transition-colors ${
                              relSource?.id === m.id
                                ? "border-primary-300 bg-primary-50"
                                : "border-surface-200 hover:border-primary-200 hover:bg-surface-50"
                            }`}
                          >
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-[10px] font-medium uppercase px-1.5 py-0.5 rounded bg-surface-100 text-surface-600">
                                {m.type}
                              </span>
                              <span className="text-[10px] text-surface-400">
                                importance {typeof m.importance === "number" ? m.importance.toFixed(2) : m.importance}
                              </span>
                            </div>
                            <p className="text-sm text-surface-700 line-clamp-3">{m.content}</p>
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                {/* Related graph panel */}
                <div>
                  <p className="text-xs font-semibold text-surface-500 uppercase tracking-wide mb-2">
                    Knowledge Graph
                  </p>
                  {!relSource ? (
                    <p className="text-sm text-surface-400">
                      Select a memory on the left to view its relationships.
                    </p>
                  ) : (
                    <div className="rounded-lg border border-surface-200 p-4">
                      <p className="text-xs text-surface-500 mb-1">Selected node</p>
                      <p className="text-sm text-surface-800 mb-3 line-clamp-3">{relSource.content}</p>
                      {relLoading ? (
                        <Loader2 className="w-4 h-4 animate-spin text-primary-500" />
                      ) : relResults && relResults.length > 0 ? (
                        <ul className="space-y-2">
                          {relResults.map((r) => (
                            <li key={r.id} className="flex items-start gap-2 text-sm">
                              <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-primary-400 shrink-0" />
                              <div>
                                <span className="text-[10px] font-medium uppercase px-1.5 py-0.5 rounded bg-surface-100 text-surface-600 mr-1">
                                  {r.type}
                                </span>
                                <span className="text-surface-700">{r.content}</span>
                              </div>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-sm text-surface-400">No related memories (isolated node).</p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === "costs" && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-white rounded-xl border border-surface-200 p-4">
                <p className="text-2xl font-bold">{costData?.total_tokens?.toLocaleString() || 0}</p>
                <p className="text-xs text-surface-500">Total Tokens</p>
              </div>
              <div className="bg-white rounded-xl border border-surface-200 p-4">
                <p className="text-2xl font-bold">{costData?.total_cost ? `$${costData.total_cost.toFixed(4)}` : "$0.0000"}</p>
                <p className="text-xs text-surface-500">Estimated Cost</p>
              </div>
              <div className="bg-white rounded-xl border border-surface-200 p-4">
                <p className="text-2xl font-bold">{costData?.api_calls || 0}</p>
                <p className="text-xs text-surface-500">API Calls</p>
              </div>
              <div className="bg-white rounded-xl border border-surface-200 p-4">
                <p className="text-2xl font-bold">{costData?.workflow_count || 0}</p>
                <p className="text-xs text-surface-500">Workflows</p>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-surface-200 p-6">
              <h3 className="font-semibold mb-1">Token Usage by Agent</h3>
              <p className="text-sm text-surface-500 mb-4">Where the LLM spend goes across the agent society.</p>
              {costData?.by_agent && Object.keys(costData.by_agent).length > 0 ? (
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={Object.entries(costData.by_agent).map(([role, s]: [string, any]) => ({
                      role: (AGENT_META[role]?.label || role).replace(/\s+/g, "\n"),
                      tokens: s.tokens,
                      cost: Number(s.cost.toFixed(4)),
                    }))}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                      <XAxis dataKey="role" tick={{ fontSize: 10 }} interval={0} />
                      <YAxis tick={{ fontSize: 10 }} />
                      <Tooltip />
                      <Bar dataKey="tokens" fill="#6366f1" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <p className="text-sm text-surface-400">No usage yet — run a workflow to see agent token costs.</p>
              )}
            </div>
          </div>
        )}

        {activeTab === "deployment" && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl border border-surface-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold">Deployment Status</h3>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  deploymentData?.build_status === "deployed"
                    ? "bg-green-100 text-green-800"
                    : "bg-surface-100 text-surface-600"
                }`}>
                  {deploymentData?.build_status === "deployed" ? "Deployed" : "Idle"}
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <p className="text-xs text-surface-500 mb-1">Production</p>
                  {deploymentData?.production_url ? (
                    <a href={deploymentData.production_url} target="_blank" rel="noreferrer"
                       className="text-sm text-primary-600 hover:underline break-all">
                      {deploymentData.production_url}
                    </a>
                  ) : <p className="text-sm text-surface-400">—</p>}
                </div>
                <div>
                  <p className="text-xs text-surface-500 mb-1">Staging (rollback)</p>
                  {deploymentData?.staging_url ? (
                    <a href={deploymentData.staging_url} target="_blank" rel="noreferrer"
                       className="text-sm text-primary-600 hover:underline break-all">
                      {deploymentData.staging_url}
                    </a>
                  ) : <p className="text-sm text-surface-400">—</p>}
                </div>
                <div>
                  <p className="text-xs text-surface-500 mb-1">Health</p>
                  <p className="text-sm text-surface-700 capitalize">{deploymentData?.health || "unknown"}</p>
                </div>
              </div>
              {deployMsg && (
                <p className="text-sm text-green-600 mt-4">{deployMsg}</p>
              )}
            </div>

            <div className="bg-white rounded-xl border border-surface-200 p-6">
              <h3 className="font-semibold mb-1">Deploy a Completed Workflow</h3>
              <p className="text-sm text-surface-500 mb-4">
                Select a completed project to deploy (simulated push to production).
              </p>
              {workflows.filter((w) => w.status === "completed").length === 0 ? (
                <p className="text-sm text-surface-400">No completed workflows to deploy yet.</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {workflows.filter((w) => w.status === "completed").map((w) => (
                    <button
                      key={w.id}
                      onClick={() => deploy(w.id)}
                      disabled={deployLoading}
                      className="px-3 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-50"
                    >
                      {deployLoading && selectedWfForDeploy === w.id ? (
                        <Loader2 className="w-4 h-4 inline animate-spin mr-1" />
                      ) : <Globe className="w-4 h-4 inline mr-1" />}
                      {w.project_name}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

      </main>
    </div>
  );
}