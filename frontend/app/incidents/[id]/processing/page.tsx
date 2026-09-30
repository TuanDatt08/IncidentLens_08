import { ProcessingView } from "@/components/incidents/processing-view";

export default function ProcessingPage({ params }: { params: { id: string } }) {
  return <ProcessingView id={params.id} />;
}