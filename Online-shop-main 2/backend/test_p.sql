-- Получение ID категории
DO $$
DECLARE
    category_id INTEGER;
BEGIN
    SELECT id INTO category_id FROM categories WHERE name = 'Электроника' LIMIT 1;

    -- Добавление товаров
    INSERT INTO products (name, price, stock_quantity, category_id, image)
    VALUES
        ('Смартфон Galaxy S23', 59999.99, 50, category_id, 'static/images/galaxy_s23.jpg'),
        ('Ноутбук Lenovo IdeaPad', 79999.99, 30, category_id, 'static/images/lenovo_ideapad.jpg'),
        ('Наушники AirPods Pro', 19999.99, 100, category_id, 'static/images/airpods_pro.jpg'),
        ('Планшет iPad Air', 64999.99, 20, category_id, 'static/images/ipad_air.jpg')
    ON CONFLICT DO NOTHING;
END $$;