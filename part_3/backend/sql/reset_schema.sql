-- Explicit full-reload reset for curated MYH application data.
--
-- This file is intentionally destructive and must only be run by explicit
-- loader/refresh workflows. FastAPI startup must never execute this file.
-- Local admin metadata in application_notes is preserved across curated-data
-- reloads.

DROP TABLE IF EXISTS applications CASCADE;
DROP TABLE IF EXISTS providers CASCADE;
DROP TABLE IF EXISTS education_areas CASCADE;
DROP TABLE IF EXISTS locations CASCADE;
DROP TABLE IF EXISTS decisions CASCADE;
DROP TABLE IF EXISTS principal_types CASCADE;
DROP TABLE IF EXISTS study_forms CASCADE;
