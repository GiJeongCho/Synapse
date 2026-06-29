import ReactFlow, { Background, Controls } from "reactflow";
import "reactflow/dist/style.css";
import FlowNodeCard from "./FlowNodeCard";
import { supervisorNodes, supervisorEdges } from "./flowConfig";

const nodeTypes = { flowCard: FlowNodeCard };

export default function SupervisorFlow() {
  return (
    <div style={{ height: 350 }}>
      <ReactFlow
        nodes={supervisorNodes}
        edges={supervisorEdges}
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
