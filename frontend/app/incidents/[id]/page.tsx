import { ReviewWorkspace } from "@/components/review/review-workspace";

export default function IncidentReviewPage({ params }: { params: { id: string } }) {
  return <ReviewWorkspace key={params.id} id={params.id} />;
}