import ReactFlow, { Background, Controls } from "reactflow";
import "reactflow/dist/style.css";
import FlowNodeCard from "./FlowNodeCard";
import { researchNodes, researchEdges } from "./flowConfig";

const nodeTypes = { flowCard: FlowNodeCard };

export default function ResearchFlow() {
  return (
    <div style={{ height: 350 }}>
      <ReactFlow
        nodes={researchNodes}
        edges={researchEdges}
        nodeTypes={nodeTypes}
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#2a2f40" gap={20} />
        <Controls />
      </ReactFlow>
    </div>
  );
}
