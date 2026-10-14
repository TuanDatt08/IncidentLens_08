import { RecordingWorkspace } from "@/components/incidents/recording-workspace";
import { V2_WORKSPACE_ENABLED } from "@/lib/config";
import { V2WorkspaceUnavailable } from "@/components/auth/v2-workspace-gate";

export default function RecordingPage({ params }: { params: { id: string } }) {
  return V2_WORKSPACE_ENABLED ? <RecordingWorkspace id={params.id} /> : <V2WorkspaceUnavailable />;
}
