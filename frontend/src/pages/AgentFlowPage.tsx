import { useState } from "react";
import PipelineFlow from "../components/flow/PipelineFlow";
import SupervisorFlow from "../components/flow/SupervisorFlow";
import OrchestratorFlow from "../components/flow/OrchestratorFlow";
import ResearchFlow from "../components/flow/ResearchFlow";

type Tab = "orchestrator" | "pipeline" | "supervisor" | "research";

const TABS: { key: Tab; label: string }[] = [
  { key: "orchestrator", label: "오케스트레이터" },
  { key: "pipeline", label: "생성 파이프라인" },
  { key: "supervisor", label: "Dual Supervisor" },
  { key: "research", label: "리서치 워크플로우" },
];

const DESCRIPTIONS: Record<Tab, string> = {
  orchestrator: "Registry 조회 → Solo / Dual 분기를 거쳐 에이전트를 생성하거나 재사용합니다.",
  pipeline: "Requirements → Tool Retriever → Provisioner → Evaluator 4단계 파이프라인으로 에이전트를 자동 생성합니다.",
  supervisor: "Builder와 Critic이 서로의 결과를 평가하며 반복적으로 개선합니다.",
  research: "Supervisor가 5개 워커 에이전트를 오케스트레이션하여 리서치를 수행합니다.",
};

export default function AgentFlowPage() {
  const [tab, setTab] = useState<Tab>("orchestrator");

  return (
    <div>
      <h2>에이전트 흐름도</h2>
      <p className="muted" style={{ marginBottom: 20 }}>
        노드를 클릭하면 설명이 표시됩니다. 마우스 휠로 확대/축소할 수 있습니다.
      </p>

      <div className="row" style={{ gap: 6, marginBottom: 16 }}>
        {TABS.map((t) => (
          <button
            key={t.key}
            className={tab === t.key ? "" : "secondary"}
            onClick={() => setTab(t.key)}
            style={{ fontSize: "0.82rem" }}
          >
            {t.label}
          </button>
        ))}
      </div>

      <p className="muted" style={{ fontSize: "0.82rem", marginBottom: 12 }}>
        {DESCRIPTIONS[tab]}
      </p>

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        {tab === "orchestrator" && <OrchestratorFlow />}
        {tab === "pipeline" && <PipelineFlow />}
        {tab === "supervisor" && <SupervisorFlow />}
        {tab === "research" && <ResearchFlow />}
      </div>
    </div>
  );
}
