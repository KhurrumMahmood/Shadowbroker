/** Artifact registry types — shared between frontend and backend (via API). */

export interface ArtifactVersion {
  version: number;
  note: string;
  created_at: string;
}

export interface ArtifactMeta {
  name: string;
  title: string;
  tags: string[];
  data_signature: string;
  versions: ArtifactVersion[];
  current_version: number;
  created_by_admin: boolean;
  accepts_data: Record<string, string>;
}

export interface RegistryEntry {
  name: string;
  title: string;
  description: string;
  tags: string[];
  data_signature: string;
  current_version: number;
  type: "react" | "html";
  created_by_admin: boolean;
  created_at: string;
  updated_at: string;
}

export interface ArtifactRegistry {
  artifacts: RegistryEntry[];
}

export interface ArtifactSearchResult {
  entry: RegistryEntry;
  score: number;
}
