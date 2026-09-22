import { apiRequest } from "@/lib/api-client";
import { API_BASE_URL, USE_MOCK_API } from "@/lib/config";
import type { ProgressEvent } from "@/types/processing";
import { mockProgressEvents, mockStore } from "./mock-data";

export async function analyzeIncident(id: string): Promise<void> {
  if (USE_MOCK_API) {
    mockStore.setProcessing(id, "PROCESSING", 0);
    return;
  }
  await apiRequest<void>(`/incidents/${encodeURIComponent(id)}/analyze`, {
    method: "POST",
  });
}

export function subscribeToProgress(
  id: string,
  onEvent: (event: ProgressEvent) => void,
  onError?: (error: Error) => void,
): () => void {
  if (USE_MOCK_API) {
    let index = 0;
    let stopped = false;
    const timer = window.setInterval(() => {
      if (stopped) return;
      const event = mockProgressEvents[index];
      if (!event) {
        window.clearInterval(timer);
        return;
      }
      onEvent(event);
      if (event.stage === "COMPLETED") {
        mockStore.setProcessing(id, "COMPLETED", 100);
        window.clearInterval(timer);
      }
      index += 1;
    }, 700);

    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }

  // NEED_CONFIRMATION: confirm the final SSE path when the FastAPI contract is frozen.
  const eventSource = new EventSource(
    `${API_BASE_URL}/incidents/${encodeURIComponent(id)}/progress`,
  );
  eventSource.onmessage = (message) => {
    try {
      onEvent(JSON.parse(message.data) as ProgressEvent);
    } catch {
      onError?.(new Error("The progress event was invalid."));
    }
  };
  eventSource.onerror = () => onError?.(new Error("The analysis progress stream disconnected."));

  return () => eventSource.close();
}