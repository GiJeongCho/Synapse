import { Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import PlaceholderPage from "./pages/PlaceholderPage";
import UploadPage from "./pages/UploadPage";
import ViewerPage from "./pages/ViewerPage";
import SearchPage from "./pages/SearchPage";
import AgentDashboardPage from "./pages/AgentDashboardPage";
import AgentCreatePage from "./pages/AgentCreatePage";
import AgentFlowPage from "./pages/AgentFlowPage";
import ToolsPage from "./pages/ToolsPage";
import SchedulesPage from "./pages/SchedulesPage";

const SIDEBAR_ROUTES = [
  { path: "/upload", title: "문서 업로드" },
  { path: "/viewer", title: "문서 뷰어 (HITL)" },
  { path: "/search", title: "RAG 검색" },
  { path: "/research", title: "리서치 에이전트" },
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
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/viewer" element={<ViewerPage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/research" element={<PlaceholderPage title="리서치 에이전트" description="Supervisor Job 실행 UI 예정" />} />
          <Route path="/agents" element={<AgentDashboardPage />} />
          <Route path="/agents/create" element={<AgentCreatePage />} />
          <Route path="/agents/flow" element={<AgentFlowPage />} />
          <Route path="/tools" element={<ToolsPage />} />
          <Route path="/schedules" element={<SchedulesPage />} />
          <Route path="/" element={<PlaceholderPage title="Synapse" description="좌측 메뉴에서 페이지를 선택하세요." />} />
        </Routes>
      </main>
    </div>
  );
}
