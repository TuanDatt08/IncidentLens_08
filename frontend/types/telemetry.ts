export type TelemetrySignal = { key: string; label: string; unit: string | null; samples: { time_s: number; value: number | null }[] };
export type TelemetryChart = {
  state: "available" | "unavailable";
  time_basis: "video_seconds" | "log_seconds";
  alignment: "VERIFIED" | "UNKNOWN";
  duration_s: number | null;
  row_count: number;
  downsampled: boolean;
  signals: TelemetrySignal[];
  message: string | null;
};
