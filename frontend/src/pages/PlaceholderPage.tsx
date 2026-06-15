interface Props {
  title: string;
  description: string;
}

/** 기획 확정 전 placeholder 페이지 */
export default function PlaceholderPage({ title, description }: Props) {
  return (
    <div>
      <h2>{title}</h2>
      <p className="muted">{description}</p>
      <div className="card">
        <p>이 화면은 아직 구현되지 않았습니다.</p>
        <p className="muted" style={{ fontSize: "0.85rem" }}>
          폴더: <code>frontend/src/pages/</code>
        </p>
      </div>
    </div>
  );
}
