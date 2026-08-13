PRAGMA foreign_keys = ON;

ALTER TABLE plant_profiles ADD COLUMN native_range TEXT NOT NULL DEFAULT '[]';
ALTER TABLE plant_profiles ADD COLUMN introduced_range TEXT NOT NULL DEFAULT '[]';
ALTER TABLE plant_profiles ADD COLUMN biomes TEXT NOT NULL DEFAULT '[]';
ALTER TABLE plant_profiles ADD COLUMN ecoregions TEXT NOT NULL DEFAULT '[]';
ALTER TABLE plant_profiles ADD COLUMN climate_associations TEXT NOT NULL DEFAULT '{}';
ALTER TABLE plant_profiles ADD COLUMN crop_origin TEXT NOT NULL DEFAULT '{}';
ALTER TABLE plant_profiles ADD COLUMN crop_use TEXT NOT NULL DEFAULT '{}';
ALTER TABLE plant_profiles ADD COLUMN food_use TEXT NOT NULL DEFAULT '{}';
ALTER TABLE plant_profiles ADD COLUMN forage_use TEXT NOT NULL DEFAULT '{}';
ALTER TABLE plant_profiles ADD COLUMN ornamental_use TEXT NOT NULL DEFAULT '{}';
ALTER TABLE plant_profiles ADD COLUMN soil_associations TEXT NOT NULL DEFAULT '{}';
ALTER TABLE plant_profiles ADD COLUMN water_associations TEXT NOT NULL DEFAULT '{}';
ALTER TABLE plant_profiles ADD COLUMN light_associations TEXT NOT NULL DEFAULT '{}';
ALTER TABLE plant_profiles ADD COLUMN temperature_associations TEXT NOT NULL DEFAULT '{}';
ALTER TABLE plant_profiles ADD COLUMN occurrence_sources TEXT NOT NULL DEFAULT '[]';
ALTER TABLE plant_profiles ADD COLUMN research_sources TEXT NOT NULL DEFAULT '[]';
