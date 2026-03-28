-- local-file-processor DuckDB schema

-- Documents: one row per ingested file
CREATE SEQUENCE IF NOT EXISTS documents_id_seq;
CREATE TABLE IF NOT EXISTS documents (
  id          BIGINT PRIMARY KEY DEFAULT nextval('documents_id_seq'),
  title       TEXT NOT NULL,
  file_path   TEXT,
  file_type   TEXT,
  content     TEXT,
  metadata    JSON DEFAULT '{}',
  summary     TEXT,
  tags        JSON DEFAULT '[]',
  source      TEXT,
  author      TEXT,
  created_at  TIMESTAMP DEFAULT now(),
  updated_at  TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_documents_file_path  ON documents (file_path);
CREATE INDEX IF NOT EXISTS idx_documents_file_type  ON documents (file_type);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents (created_at);

-- Chunks: one row per ~500-token text chunk
CREATE SEQUENCE IF NOT EXISTS chunks_id_seq;
CREATE TABLE IF NOT EXISTS file_chunks (
  id          BIGINT PRIMARY KEY DEFAULT nextval('chunks_id_seq'),
  document_id BIGINT,
  chunk_index INTEGER NOT NULL,
  text        TEXT NOT NULL,
  token_count INTEGER DEFAULT 0,
  metadata    JSON DEFAULT '{}',
  created_at  TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON file_chunks (document_id);

-- Embeddings: one row per chunk vector
CREATE SEQUENCE IF NOT EXISTS embeddings_id_seq;
CREATE TABLE IF NOT EXISTS embeddings (
  id          BIGINT PRIMARY KEY DEFAULT nextval('embeddings_id_seq'),
  chunk_id    BIGINT,
  document_id BIGINT,
  model       TEXT NOT NULL DEFAULT 'moonshot-v1-embedding',
  vector      FLOAT[1536],
  created_at  TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_embeddings_chunk_id    ON embeddings (chunk_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_document_id ON embeddings (document_id);

-- Events: pipeline audit log
CREATE SEQUENCE IF NOT EXISTS events_id_seq;
CREATE TABLE IF NOT EXISTS events (
  id          BIGINT PRIMARY KEY DEFAULT nextval('events_id_seq'),
  document_id BIGINT,
  type        TEXT NOT NULL,
  payload     JSON DEFAULT '{}',
  occurred_at TIMESTAMP DEFAULT now(),
  created_at  TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_events_document_id ON events (document_id);
CREATE INDEX IF NOT EXISTS idx_events_type        ON events (type);
