import { ReportWorkspaceV2 } from "@/components/review/report-workspace-v2";

export default function ReportPage({ params }: { params: { id: string } }) {
  return <ReportWorkspaceV2 id={params.id} />;
}
