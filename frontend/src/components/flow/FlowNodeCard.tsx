import { memo, useState } from "react";
import { Handle, Position, type NodeProps } from "reactflow";

interface FlowNodeData {
  label: string;
  desc: string;
}

function FlowNodeCard({ data }: NodeProps<FlowNodeData>) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      style={{
        background: "#1e2333",
        border: "1px solid #3a3f52",
        borderRadius: 10,
        padding: "10px 14px",
        minWidth: 160,
        cursor: "pointer",
        transition: "border-color 0.2s, box-shadow 0.2s",
        boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
      }}
      onClick={() => setExpanded((v) => !v)}
      onMouseEnter={(e) => {
        const el = e.currentTarget as HTMLElement;
        el.style.borderColor = "#4f7cff";
        el.style.boxShadow = "0 0 12px rgba(79,124,255,0.3)";
      }}
      onMouseLeave={(e) => {
        const el = e.currentTarget as HTMLElement;
        el.style.borderColor = "#3a3f52";
        el.style.boxShadow = "0 2px 8px rgba(0,0,0,0.3)";
      }}
    >
      <Handle type="target" position={Position.Left} style={{ background: "#4f7cff", width: 8, height: 8 }} />
      <p style={{ margin: 0, fontWeight: 600, fontSize: "0.82rem", color: "#e6e8ee" }}>{data.label}</p>
      {expanded && (
        <p style={{ margin: "6px 0 0", fontSize: "0.72rem", color: "#9aa1b1" }}>
          {data.desc}
        </p>
      )}
      <Handle type="source" position={Position.Right} style={{ background: "#4f7cff", width: 8, height: 8 }} />
    </div>
  );
}

export default memo(FlowNodeCard);
