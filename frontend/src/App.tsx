import { Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import PlaceholderPage from "./pages/PlaceholderPage";
import AgentDashboardPage from "./pages/AgentDashboardPage";
import AgentCreatePage from "./pages/AgentCreatePage";
import AgentFlowPage from "./pages/AgentFlowPage";
import ToolsPage from "./pages/ToolsPage";
import SchedulesPage from "./pages/SchedulesPage";

const PLACEHOLDER_ROUTES = [
  { path: "/upload", title: "문서 업로드", desc: "전처리 파이프라인 연동 예정" },
  { path: "/viewer", title: "문서 뷰어 (HITL)", desc: "청크 검수·편집 UI 예정" },
  { path: "/search", title: "RAG 검색", desc: "검색 UI 예정" },
  { path: "/research", title: "리서치 에이전트", desc: "Supervisor Job 실행 UI 예정" },
];

const SIDEBAR_ROUTES = [
  ...PLACEHOLDER_ROUTES,
  { path: "/agents", title: "에이전트 관리" },
  { path: "/agents/create", title: "에이전트 생성" },
  { path: "/agents/flow", title: "흐름도" },
  { path: "/tools", title: "MCP 도구" },
  { path: "/schedules", title: "스케줄" },
];

export default function App() {
  return (
    <div className="layout">
      <Sidebar routes={SIDEBAR_ROUTES} />
      <main className="content">
        <Routes>
          {PLACEHOLDER_ROUTES.map((r) => (
            <Route
              key={r.path}
              path={r.path}
              element={<PlaceholderPage title={r.title} description={r.desc} />}
            />
          ))}
          <Route path="/agents" element={<AgentDashboardPage />} />
          <Route path="/agents/create" element={<AgentCreatePage />} />
          <Route path="/agents/flow" element={<AgentFlowPage />} />
          <Route path="/tools" element={<ToolsPage />} />
          <Route path="/schedules" element={<SchedulesPage />} />
          <Route
            path="/"
            element={<PlaceholderPage title="Synapse" description="좌측 메뉴에서 페이지를 선택하세요." />}
          />
        </Routes>
      </main>
    </div>
  );
}
