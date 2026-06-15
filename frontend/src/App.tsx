import { Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import PlaceholderPage from "./pages/PlaceholderPage";

/** 화면 기획 확정 전 — 라우팅 셸만 유지 */
const ROUTES = [
  { path: "/upload", title: "문서 업로드", desc: "전처리 파이프라인 연동 예정" },
  { path: "/viewer", title: "문서 뷰어 (HITL)", desc: "청크 검수·편집 UI 예정" },
  { path: "/search", title: "RAG 검색", desc: "검색 UI 예정" },
  { path: "/research", title: "리서치 에이전트", desc: "Supervisor Job 실행 UI 예정" },
];

export default function App() {
  return (
    <div className="layout">
      <Sidebar routes={ROUTES} />
      <main className="content">
        <Routes>
          {ROUTES.map((r) => (
            <Route
              key={r.path}
              path={r.path}
              element={<PlaceholderPage title={r.title} description={r.desc} />}
            />
          ))}
          <Route
            path="/"
            element={<PlaceholderPage title="Synapse" description="좌측 메뉴에서 페이지를 선택하세요." />}
          />
        </Routes>
      </main>
    </div>
  );
}
