INSERT INTO public.analysis_categories
(id, "name", display_name, description, icon, is_active, created_at, credit_cost)
VALUES(    gen_random_uuid(), -- PostgreSQL function to generate a new UUID
 'romantic',
 'Romantic Relationship',
 'Analysis of communication patterns and dynamics within romantic partnerships.',
 '❤️',
 true,
 '2025-11-10 22:59:32.531',
 400
);

INSERT INTO public.analysis_categories
(id, "name", display_name, description, icon, is_active, created_at, credit_cost)
VALUES(
 gen_random_uuid(),
 'friendship',
 'Friendship',
 'Deep analysis of trust, support, and connection quality in your friendship.',
 '🤝',
 true,
 NOW(),
 400
);

INSERT INTO public.analysis_categories
(id, "name", display_name, description, icon, is_active, created_at, credit_cost)
VALUES(
 gen_random_uuid(),
 'family',
 'Family',
 'Understand the dynamics, emotional climate, and communication patterns in your family.',
 '🏡',
 true,
 NOW(),
 400
);

INSERT INTO public.analysis_categories
(id, "name", display_name, description, icon, is_active, created_at, credit_cost)
VALUES(
 gen_random_uuid(),
 'workplace',
 'Workplace',
 'Analyze communication effectiveness, collaboration, and relationship health at work.',
 '💼',
 true,
 NOW(),
 400
);