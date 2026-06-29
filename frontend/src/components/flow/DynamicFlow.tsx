import ReactFlow, { Background, Controls, MiniMap } from "reactflow";
import "reactflow/dist/style.css";
import FlowNodeCard from "./FlowNodeCard";
import type { FlowNode, FlowEdge } from "../../types";

const nodeTypes = { flowCard: FlowNodeCard };

interface Props {
  nodes: FlowNode[];
  edges: FlowEdge[];
  height?: number;
}

export default function DynamicFlow({ nodes, edges, height = 400 }: Props) {
  if (!nodes.length) {
    return (
      <div
        style={{
          height,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#9aa1b1",
        }}
      >
        그래프 데이터가 없습니다.
      </div>
    );
  }

  return (
    <div style={{ height }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        proOptions={{ hideAttribution: true }}
        minZoom={0.3}
        maxZoom={2}
      >
        <Background color="#2a2f40" gap={20} />
        <Controls />
        <MiniMap
          nodeColor="#1e2333"
          maskColor="rgba(0,0,0,0.5)"
          style={{ background: "#121520", border: "1px solid #3a3f52", borderRadius: 8 }}
        />
      </ReactFlow>
    </div>
  );
}
