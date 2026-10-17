-- ==============================================================================
-- Supabase Row-Level Security Policies for Rosetta
-- ==============================================================================
-- Run this in the Supabase SQL Editor after creating the tables via Alembic.
-- These policies ensure users can only access their own data.
-- ==============================================================================

-- Enable RLS on tables
ALTER TABLE translations ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_records ENABLE ROW LEVEL SECURITY;

-- ==============================================================================
-- Translations Policies
-- ==============================================================================

-- Users can read their own translations
CREATE POLICY "Users can read own translations"
  ON translations
  FOR SELECT
  USING (auth.uid() = user_id);

-- Users can insert their own translations
CREATE POLICY "Users can insert own translations"
  ON translations
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Users can delete their own translations
CREATE POLICY "Users can delete own translations"
  ON translations
  FOR DELETE
  USING (auth.uid() = user_id);

-- Service role can bypass RLS (for backend operations)
-- This is automatic with the service_role key in Supabase.

-- ==============================================================================
-- Usage Records Policies
-- ==============================================================================

-- Users can read their own usage records
CREATE POLICY "Users can read own usage"
  ON usage_records
  FOR SELECT
  USING (auth.uid() = user_id);

-- Users can insert their own usage records
CREATE POLICY "Users can insert own usage"
  ON usage_records
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Users can update their own usage records
CREATE POLICY "Users can update own usage"
  ON usage_records
  FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- ==============================================================================
-- Analyzer RLS Policies
-- ==============================================================================

ALTER TABLE analysis_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE source_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE phase_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE code_blocks ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph_edges ENABLE ROW LEVEL SECURITY;
ALTER TABLE conditions ENABLE ROW LEVEL SECURITY;
ALTER TABLE block_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE findings ENABLE ROW LEVEL SECURITY;

-- Analysis Runs
CREATE POLICY "Users can read own analysis runs"
  ON analysis_runs FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own analysis runs"
  ON analysis_runs FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own analysis runs"
  ON analysis_runs FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own analysis runs"
  ON analysis_runs FOR DELETE USING (auth.uid() = user_id);

-- Source Files
CREATE POLICY "Users can access own source files"
  ON source_files FOR ALL
  USING (EXISTS (SELECT 1 FROM analysis_runs WHERE analysis_runs.id = source_files.run_id AND analysis_runs.user_id = auth.uid()));

-- Phase Runs
CREATE POLICY "Users can access own phase runs"
  ON phase_runs FOR ALL
  USING (EXISTS (SELECT 1 FROM analysis_runs WHERE analysis_runs.id = phase_runs.run_id AND analysis_runs.user_id = auth.uid()));

-- Code Blocks
CREATE POLICY "Users can access own code blocks"
  ON code_blocks FOR ALL
  USING (EXISTS (SELECT 1 FROM analysis_runs WHERE analysis_runs.id = code_blocks.run_id AND analysis_runs.user_id = auth.uid()));

-- Graph Nodes
CREATE POLICY "Users can access own graph nodes"
  ON graph_nodes FOR ALL
  USING (EXISTS (SELECT 1 FROM analysis_runs WHERE analysis_runs.id = graph_nodes.run_id AND analysis_runs.user_id = auth.uid()));

-- Graph Edges
CREATE POLICY "Users can access own graph edges"
  ON graph_edges FOR ALL
  USING (EXISTS (SELECT 1 FROM analysis_runs WHERE analysis_runs.id = graph_edges.run_id AND analysis_runs.user_id = auth.uid()));

-- Conditions
CREATE POLICY "Users can access own conditions"
  ON conditions FOR ALL
  USING (EXISTS (
    SELECT 1 FROM code_blocks
    JOIN analysis_runs ON analysis_runs.id = code_blocks.run_id
    WHERE code_blocks.id = conditions.block_id AND analysis_runs.user_id = auth.uid()
  ));

-- Block Analyses
CREATE POLICY "Users can access own block analyses"
  ON block_analyses FOR ALL
  USING (EXISTS (
    SELECT 1 FROM code_blocks
    JOIN analysis_runs ON analysis_runs.id = code_blocks.run_id
    WHERE code_blocks.id = block_analyses.block_id AND analysis_runs.user_id = auth.uid()
  ));

-- Findings
CREATE POLICY "Users can access own findings"
  ON findings FOR ALL
  USING (EXISTS (SELECT 1 FROM analysis_runs WHERE analysis_runs.id = findings.run_id AND analysis_runs.user_id = auth.uid()));
