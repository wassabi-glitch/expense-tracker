-- Get your user_id first
SELECT id FROM users WHERE email = 'ahrorabrorov26@email.com';

-- Then insert 50 recurring expenses
INSERT INTO recurring_expenses (user_id, title, amount, category, frequency, start_date, next_due_date, is_active, created_at)
SELECT 
    YOUR_USER_ID,  -- Replace with actual user_id
    'Test Recurring ' || generate_series,
    (random() * 90000 + 10000)::numeric(10,2),
    (ARRAY['FOOD', 'TRANSPORT', 'UTILITIES', 'ENTERTAINMENT'])[floor(random() * 4 + 1)],
    (ARRAY['DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY'])[floor(random() * 4 + 1)],
    '2026-03-01'::date,
    '2026-04-01'::date,
    true,
    NOW()
FROM generate_series(1, 50);