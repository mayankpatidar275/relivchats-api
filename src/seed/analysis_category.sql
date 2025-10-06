INSERT INTO analysis_categories (id, name, display_name, description, icon, is_active)
VALUES (
    gen_random_uuid(), -- PostgreSQL function to generate a new UUID
    'romantic',
    'Romantic Relationship',
    'Analysis of communication patterns and dynamics within romantic partnerships.',
    '❤️', -- Example icon
    TRUE
);