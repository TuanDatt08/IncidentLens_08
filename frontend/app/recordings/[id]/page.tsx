import { RecordingWorkspace } from "@/components/incidents/recording-workspace";

export default function RecordingPage({ params }: { params: { id: string } }) {
  return <RecordingWorkspace id={params.id} />;
}
