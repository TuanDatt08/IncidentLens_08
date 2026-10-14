import { ReportWorkspaceV2 } from "@/components/review/report-workspace-v2";
import { V2_WORKSPACE_ENABLED } from "@/lib/config";
import { V2WorkspaceUnavailable } from "@/components/auth/v2-workspace-gate";

export default function ReportPage({ params }: { params: { id: string } }) {
  return V2_WORKSPACE_ENABLED ? <ReportWorkspaceV2 key={params.id} id={params.id} /> : <V2WorkspaceUnavailable />;
}
