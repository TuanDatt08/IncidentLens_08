import { ReviewWorkspace } from "@/components/review/review-workspace";

export default function IncidentReviewPage({ params }: { params: { id: string } }) {
  return <ReviewWorkspace id={params.id} />;
}