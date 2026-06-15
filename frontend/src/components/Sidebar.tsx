import { NavLink } from "react-router-dom";

interface RouteItem {
  path: string;
  title: string;
}

interface Props {
  routes: RouteItem[];
}

export default function Sidebar({ routes }: Props) {
  return (
    <aside className="sidebar">
      <h1>Synapse</h1>
      <p className="tagline">Multi-Agent 리서치 — UI 기획 전</p>
      <nav>
        {routes.map((r) => (
          <NavLink
            key={r.path}
            to={r.path}
            className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
          >
            {r.title}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
