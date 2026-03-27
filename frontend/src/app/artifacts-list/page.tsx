import type { Metadata } from "next";
import ArtifactsListPage from "@/components/artifacts-list/ArtifactsListPage";

export const metadata: Metadata = {
  title: "ARTIFACTS // SHOWCASE",
  description: "Browse and preview ShadowBroker artifacts with sample data",
};

export default function ArtifactsListRoute() {
  return <ArtifactsListPage />;
}
