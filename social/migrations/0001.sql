CREATE TABLE IF NOT EXISTS editorial_candidates (
  id TEXT PRIMARY KEY,
  source_name TEXT NOT NULL,
  category TEXT NOT NULL,
  title TEXT NOT NULL,
  url TEXT NOT NULL,
  source_summary TEXT NOT NULL,
  fact_summary TEXT NOT NULL,
  question_one TEXT NOT NULL,
  question_two TEXT NOT NULL,
  state TEXT NOT NULL,
  user_reaction TEXT NOT NULL DEFAULT '',
  followup_count INTEGER NOT NULL DEFAULT 0,
  threads_draft TEXT NOT NULL DEFAULT '',
  linkedin_draft TEXT NOT NULL DEFAULT '',
  decision_reason TEXT NOT NULL DEFAULT '',
  created TEXT NOT NULL,
  updated TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS processed_updates (
  update_id INTEGER PRIMARY KEY,
  processed TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS publications (
  candidate_id TEXT NOT NULL REFERENCES editorial_candidates(id),
  platform TEXT NOT NULL,
  status TEXT NOT NULL,
  remote_id TEXT NOT NULL DEFAULT '',
  error_code TEXT NOT NULL DEFAULT '',
  updated TEXT NOT NULL,
  PRIMARY KEY (candidate_id, platform)
);

CREATE INDEX IF NOT EXISTS editorial_candidates_state
  ON editorial_candidates(state, updated DESC);
