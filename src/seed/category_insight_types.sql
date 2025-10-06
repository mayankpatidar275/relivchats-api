-- 1. Link Conflict Analysis (1st in display order)
INSERT INTO category_insight_types (id, category_id, insight_type_id, display_order)
VALUES (
    gen_random_uuid(), -- FIX: Explicitly generate the UUID for the primary key
    (SELECT id FROM analysis_categories WHERE name = 'romantic'),
    (SELECT id FROM insight_types WHERE name = 'conflict_analysis'),
    1
);

-- 2. Link Communication Patterns (2nd in display order)
INSERT INTO category_insight_types (id, category_id, insight_type_id, display_order)
VALUES (
    gen_random_uuid(), -- FIX: Explicitly generate the UUID for the primary key
    (SELECT id FROM analysis_categories WHERE name = 'romantic'),
    (SELECT id FROM insight_types WHERE name = 'communication_patterns'),
    2
);

-- 3. Link Relationship Indicators (3rd in display order)
INSERT INTO category_insight_types (id, category_id, insight_type_id, display_order)
VALUES (
    gen_random_uuid(), -- FIX: Explicitly generate the UUID for the primary key
    (SELECT id FROM analysis_categories WHERE name = 'romantic'),
    (SELECT id FROM insight_types WHERE name = 'relationship_indicators'),
    3
);