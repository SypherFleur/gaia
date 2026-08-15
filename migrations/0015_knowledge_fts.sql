-- Institutional knowledge retrieval was substring counting over document bodies,
-- which cannot rank, stem, or match phrases. FTS5 gives real ranked retrieval
-- with no new dependency and no model download.
--
-- The index is a contentless-adjacent mirror keyed by document id; tenant and
-- collection scoping stays in the SQL join against knowledge_documents so a
-- query can never reach another organization's rows.

CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_documents_fts USING fts5 (
    document_id UNINDEXED,
    organization_id UNINDEXED,
    collection_id UNINDEXED,
    title,
    body,
    tokenize = 'porter unicode61'
);
