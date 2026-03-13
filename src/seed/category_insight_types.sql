-- -- 1. Link Conflict Analysis (1st in display order)
-- INSERT INTO category_insight_types (id, category_id, insight_type_id, display_order)
-- VALUES (
--     gen_random_uuid(), -- FIX: Explicitly generate the UUID for the primary key
--     (SELECT id FROM analysis_categories WHERE name = 'romantic'),
--     (SELECT id FROM insight_types WHERE name = 'conflict_analysis'),
--     1
-- );

-- -- 2. Link Communication Patterns (2nd in display order)
-- INSERT INTO category_insight_types (id, category_id, insight_type_id, display_order)
-- VALUES (
--     gen_random_uuid(), -- FIX: Explicitly generate the UUID for the primary key
--     (SELECT id FROM analysis_categories WHERE name = 'romantic'),
--     (SELECT id FROM insight_types WHERE name = 'communication_patterns'),
--     2
-- );

-- -- 3. Link Relationship Indicators (3rd in display order)
-- INSERT INTO category_insight_types (id, category_id, insight_type_id, display_order)
-- VALUES (
--     gen_random_uuid(), -- FIX: Explicitly generate the UUID for the primary key
--     (SELECT id FROM analysis_categories WHERE name = 'romantic'),
--     (SELECT id FROM insight_types WHERE name = 'relationship_indicators'),
--     3
-- );

-- INSERT INTO category_insight_types (id, category_id, insight_type_id, display_order)
-- VALUES (
--     gen_random_uuid(), -- FIX: Explicitly generate the UUID for the primary key
--     (SELECT id FROM analysis_categories WHERE name = 'romantic'),
--     (SELECT id FROM insight_types WHERE name = 'emotional_intimacy'),
--     1
-- );

-- INSERT INTO category_insight_types (id, category_id, insight_type_id, display_order)
-- VALUES (
--     gen_random_uuid(), -- FIX: Explicitly generate the UUID for the primary key
--     (SELECT id FROM analysis_categories WHERE name = 'romantic'),
--     (SELECT id FROM insight_types WHERE name = 'love_language'),
--     1
-- );

-- Romantic
INSERT INTO category_insight_types (id, category_id, insight_type_id, display_order)
VALUES (
    gen_random_uuid(),
    (SELECT id FROM analysis_categories WHERE name = 'romantic'),
    (SELECT id FROM insight_types WHERE name = 'conflict_resolution'),
    1
);

INSERT INTO category_insight_types (id, category_id, insight_type_id, display_order)
VALUES (
    gen_random_uuid(),
    (SELECT id FROM analysis_categories WHERE name = 'romantic'),
    (SELECT id FROM insight_types WHERE name = 'future_planning'),
    2
);

INSERT INTO category_insight_types (id, category_id, insight_type_id, display_order)
VALUES (
    gen_random_uuid(),
    (SELECT id FROM analysis_categories WHERE name = 'romantic'),
    (SELECT id FROM insight_types WHERE name = 'playfulness_romance'),
    3
);

-- Friendship
INSERT INTO category_insight_types (id, category_id, insight_type_id, display_order)
VALUES (
    gen_random_uuid(),
    (SELECT id FROM analysis_categories WHERE name = 'friendship'),
    (SELECT id FROM insight_types WHERE name = 'friendship_trust_loyalty'),
    1
);

INSERT INTO category_insight_types (id, category_id, insight_type_id, display_order)
VALUES (
    gen_random_uuid(),
    (SELECT id FROM analysis_categories WHERE name = 'friendship'),
    (SELECT id FROM insight_types WHERE name = 'friendship_support_dynamics'),
    2
);

INSERT INTO category_insight_types (id, category_id, insight_type_id, display_order)
VALUES (
    gen_random_uuid(),
    (SELECT id FROM analysis_categories WHERE name = 'friendship'),
    (SELECT id FROM insight_types WHERE name = 'friendship_vitality'),
    3
);

-- Family
INSERT INTO category_insight_types (id, category_id, insight_type_id, display_order)
VALUES (
    gen_random_uuid(),
    (SELECT id FROM analysis_categories WHERE name = 'family'),
    (SELECT id FROM insight_types WHERE name = 'family_dynamics'),
    1
);

INSERT INTO category_insight_types (id, category_id, insight_type_id, display_order)
VALUES (
    gen_random_uuid(),
    (SELECT id FROM analysis_categories WHERE name = 'family'),
    (SELECT id FROM insight_types WHERE name = 'family_emotional_climate'),
    2
);

INSERT INTO category_insight_types (id, category_id, insight_type_id, display_order)
VALUES (
    gen_random_uuid(),
    (SELECT id FROM analysis_categories WHERE name = 'family'),
    (SELECT id FROM insight_types WHERE name = 'family_conflict_patterns'),
    3
);

-- Workplace
INSERT INTO category_insight_types (id, category_id, insight_type_id, display_order)
VALUES (
    gen_random_uuid(),
    (SELECT id FROM analysis_categories WHERE name = 'workplace'),
    (SELECT id FROM insight_types WHERE name = 'workplace_communication'),
    1
);

INSERT INTO category_insight_types (id, category_id, insight_type_id, display_order)
VALUES (
    gen_random_uuid(),
    (SELECT id FROM analysis_categories WHERE name = 'workplace'),
    (SELECT id FROM insight_types WHERE name = 'workplace_collaboration'),
    2
);

INSERT INTO category_insight_types (id, category_id, insight_type_id, display_order)
VALUES (
    gen_random_uuid(),
    (SELECT id FROM analysis_categories WHERE name = 'workplace'),
    (SELECT id FROM insight_types WHERE name = 'workplace_relationship_health'),
    3
);

