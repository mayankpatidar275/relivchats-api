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