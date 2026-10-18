import type { Metadata } from "next";
import { LandingPage } from "@/components/landing/landing-page";
import "./landing.css";
import "./galaxy.css";
import "./landing-orbit.css";
import "./landing-polish.css";
import "./landing-refinement.css";

export const metadata: Metadata = {
  title: "IncidentLens — Từ dữ liệu đến bằng chứng",
  description: "Phân tích video sự cố, đối chiếu telemetry khi có và tập hợp bằng chứng để kỹ sư kiểm tra, chỉnh sửa báo cáo và review.",
};

export default function HomePage() {
  return <LandingPage />;
}
