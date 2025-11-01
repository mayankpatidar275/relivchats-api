INSERT INTO credit_packages (id, name, coins, price_usd, is_popular, sort_order, description)
        VALUES 
            (gen_random_uuid(), 'Starter', 200, 2.99, false, 1, '4 Friendship/Family or 2 Romantic/Work insights'),
            (gen_random_uuid(), 'Popular', 500, 5.99, true, 2, 'Best value - 10 Friendship/Family or 5 Romantic/Work insights'),
            (gen_random_uuid(), 'Pro', 1500, 14.99, false, 3, 'Maximum savings - 30 Friendship/Family or 15 Romantic/Work insights');
