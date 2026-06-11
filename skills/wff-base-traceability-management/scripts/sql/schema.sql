CREATE TABLE IF NOT EXISTS registry_meta (
  project_key TEXT NOT NULL,
  project_root TEXT NOT NULL,
  project_label TEXT,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS id_counters (
  project_scope TEXT NOT NULL,
  artifact_type TEXT NOT NULL,
  next_value INTEGER NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (project_scope, artifact_type)
);

CREATE TABLE IF NOT EXISTS artifacts (
  project_scope TEXT NOT NULL,
  artifact_id TEXT NOT NULL,
  artifact_type TEXT NOT NULL,
  stage_or_lane TEXT,
  status TEXT,
  source_path TEXT NOT NULL,
  source_anchor TEXT,
  language_role TEXT,
  canonical_of TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (project_scope, artifact_id)
);

CREATE TABLE IF NOT EXISTS links (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_scope TEXT NOT NULL,
  from_artifact_id TEXT NOT NULL,
  to_artifact_id TEXT NOT NULL,
  link_type TEXT NOT NULL,
  source_path TEXT,
  evidence_anchor TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS claim_evidence_refs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_scope TEXT NOT NULL,
  artifact_id TEXT NOT NULL,
  block_id TEXT NOT NULL,
  view_id TEXT,
  rendered_claim_refs_json TEXT NOT NULL,
  source_claim_refs_json TEXT NOT NULL,
  proposed_claim_refs_json TEXT NOT NULL,
  audit_status TEXT NOT NULL,
  artifact_version TEXT,
  artifact_hash TEXT,
  claim_surface_version TEXT,
  claim_surface_hash TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (project_scope, artifact_id, block_id, view_id)
);

CREATE INDEX IF NOT EXISTS idx_artifacts_source_path ON artifacts (project_scope, source_path);
CREATE INDEX IF NOT EXISTS idx_links_from ON links (project_scope, from_artifact_id);
CREATE INDEX IF NOT EXISTS idx_links_to ON links (project_scope, to_artifact_id);
CREATE INDEX IF NOT EXISTS idx_claim_evidence_artifact ON claim_evidence_refs (project_scope, artifact_id);
