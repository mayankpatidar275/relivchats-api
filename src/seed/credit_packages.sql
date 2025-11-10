
-- Insert new packages (Final Plan)
INSERT INTO credit_packages (id, name, coins, price_usd, price_inr, description, is_active, is_popular, sort_order, stripe_price_id) 
VALUES
(
    gen_random_uuid(),
    'Starter',
    400,
    4.99,
    399,
    'Perfect for trying your first romantic analysis',
    true,
    false,
    1,
    NULL
),
(
    gen_random_uuid(),
    'Popular',
    850,
    9.99,
    799,
    'Best value - Unlock 2 romantic insights with extra coins',
    true,
    true,  -- Mark as popular
    2,
    NULL
),
(
    gen_random_uuid(),
    'Pro',
    1600,
    17.99,
    1499,
    'Power user pack - Analyze multiple chats or categories',
    true,
    false,
    3,
    NULL
);