import ReactFlow, { Background, Controls } from "reactflow";
import "reactflow/dist/style.css";
import FlowNodeCard from "./FlowNodeCard";
import { orchestratorNodes, orchestratorEdges } from "./flowConfig";

const nodeTypes = { flowCard: FlowNodeCard };

export default function OrchestratorFlow() {
  return (
    <div style={{ height: 300 }}>
      <ReactFlow
        nodes={orchestratorNodes}
        edges={orchestratorEdges}
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
