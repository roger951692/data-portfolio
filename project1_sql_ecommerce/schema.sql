-- ============================================================
-- E-Commerce Portfolio Database
-- Schema + Seed Data (PostgreSQL-compatible)
-- ============================================================

-- Drop tables if exist
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

-- ============================================================
-- SCHEMA
-- ============================================================

CREATE TABLE customers (
    customer_id   SERIAL PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    city          VARCHAR(50),
    signup_date   DATE NOT NULL
);

CREATE TABLE products (
    product_id    SERIAL PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    category      VARCHAR(50),
    cost_price    NUMERIC(10,2) NOT NULL
);

CREATE TABLE orders (
    order_id      SERIAL PRIMARY KEY,
    customer_id   INT REFERENCES customers(customer_id),
    order_date    DATE NOT NULL,
    status        VARCHAR(20) DEFAULT 'completed' -- completed, cancelled, refunded
);

CREATE TABLE order_items (
    item_id       SERIAL PRIMARY KEY,
    order_id      INT REFERENCES orders(order_id),
    product_id    INT REFERENCES products(product_id),
    quantity      INT NOT NULL,
    unit_price    NUMERIC(10,2) NOT NULL
);

CREATE TABLE payments (
    payment_id    SERIAL PRIMARY KEY,
    order_id      INT REFERENCES orders(order_id),
    amount        NUMERIC(10,2) NOT NULL,
    payment_date  DATE NOT NULL,
    method        VARCHAR(20) -- card, paypal, transfer
);

-- ============================================================
-- INDEXES (for query optimization demo - Query 10)
-- ============================================================
CREATE INDEX idx_orders_customer    ON orders(customer_id);
CREATE INDEX idx_orders_date        ON orders(order_date);
CREATE INDEX idx_order_items_order  ON order_items(order_id);
CREATE INDEX idx_order_items_product ON order_items(product_id);
CREATE INDEX idx_payments_order     ON payments(order_id);

-- ============================================================
-- SEED DATA
-- ============================================================

INSERT INTO customers (name, city, signup_date) VALUES
('Ana García',       'Barcelona',  '2022-01-15'),
('Marc Puig',        'Madrid',     '2022-02-03'),
('Laura Martínez',   'Valencia',   '2022-02-20'),
('Jordi Roca',       'Barcelona',  '2022-03-10'),
('Marta Soler',      'Sevilla',    '2022-04-05'),
('Pere Valls',       'Barcelona',  '2022-04-22'),
('Carme Ferrer',     'Bilbao',     '2022-05-11'),
('Antoni Mas',       'Madrid',     '2022-06-01'),
('Núria Costa',      'Barcelona',  '2022-06-18'),
('David Llopis',     'Valencia',   '2022-07-07'),
('Silvia Pons',      'Zaragoza',   '2022-07-25'),
('Miquel Nadal',     'Barcelona',  '2022-08-14'),
('Elena Torres',     'Madrid',     '2022-09-02'),
('Francesc Gil',     'Girona',     '2022-09-20'),
('Rosa Camps',       'Barcelona',  '2022-10-09'),
('Albert Font',      'Tarragona',  '2022-11-01'),
('Montse Ibáñez',    'Madrid',     '2022-11-19'),
('Xavier Molina',    'Barcelona',  '2022-12-05'),
('Gemma Coll',       'Valencia',   '2023-01-10'),
('Pau Esteve',       'Barcelona',  '2023-01-28');

INSERT INTO products (name, category, cost_price) VALUES
('Laptop Pro 15"',       'Electronics',   650.00),
('Wireless Mouse',       'Electronics',    18.00),
('Mechanical Keyboard',  'Electronics',    55.00),
('USB-C Hub 7-in-1',     'Electronics',    22.00),
('Monitor 27" 4K',       'Electronics',   280.00),
('Office Chair Ergonomic','Furniture',    195.00),
('Standing Desk',        'Furniture',     320.00),
('Desk Lamp LED',        'Furniture',      28.00),
('Python Programming',   'Books',           9.00),
('SQL for Analysts',     'Books',           8.50),
('Data Science Handbook','Books',          11.00),
('Notebook A5 Pack x5',  'Stationery',      6.00),
('Ballpoint Pens x20',   'Stationery',      3.50),
('Webcam HD 1080p',      'Electronics',    45.00),
('Noise-Cancel Headphones','Electronics',  85.00);

-- Orders: 2022-2023, mix of statuses
INSERT INTO orders (customer_id, order_date, status) VALUES
(1,  '2022-02-10', 'completed'),
(1,  '2022-06-15', 'completed'),
(1,  '2023-01-20', 'completed'),
(2,  '2022-03-05', 'completed'),
(2,  '2022-09-12', 'refunded'),
(3,  '2022-04-18', 'completed'),
(3,  '2022-11-03', 'completed'),
(4,  '2022-05-22', 'completed'),
(5,  '2022-05-30', 'completed'),
(5,  '2022-12-14', 'completed'),
(6,  '2022-06-08', 'completed'),
(7,  '2022-07-01', 'cancelled'),
(7,  '2022-07-15', 'completed'),
(8,  '2022-08-20', 'completed'),
(9,  '2022-08-25', 'completed'),
(9,  '2023-02-11', 'completed'),
(10, '2022-09-10', 'completed'),
(11, '2022-10-05', 'completed'),
(12, '2022-10-22', 'completed'),
(12, '2023-03-08', 'completed'),
(13, '2022-11-11', 'completed'),
(14, '2022-11-28', 'completed'),
(15, '2022-12-02', 'completed'),
(15, '2023-04-15', 'completed'),
(16, '2023-01-05', 'completed'),
(17, '2023-01-25', 'completed'),
(18, '2023-02-14', 'completed'),
(19, '2023-03-01', 'completed'),
(20, '2023-03-20', 'completed'),
(1,  '2023-04-10', 'completed'),
(3,  '2023-04-28', 'completed'),
(6,  '2023-05-05', 'completed'),
(8,  '2023-05-18', 'completed'),
(10, '2023-06-02', 'completed'),
(13, '2023-06-20', 'completed');

INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(1,  1, 1, 1199.00), (1, 2, 1, 35.00),
(2,  5, 1,  549.00),
(3,  15,1,  149.00), (3, 3, 1, 95.00),
(4,  2, 2,   35.00), (4, 4, 1, 49.00),
(5,  6, 1,  349.00),
(6,  9, 2,   18.99), (6, 10, 1, 17.99),
(7,  7, 1,  599.00),
(8,  7, 1,  599.00),
(9,  1, 1, 1199.00),
(10, 3, 1,   95.00), (10, 14, 1, 79.00),
(11, 8, 2,   45.00), (11, 12, 3, 11.99),
(12, 2, 1,   35.00),
(13, 2, 1,   35.00),
(14, 5, 1,  549.00),
(15, 15,1,  149.00),
(16, 1, 1, 1199.00), (16, 4, 2, 49.00),
(17, 6, 1,  349.00),
(18, 9, 1,   18.99), (18, 11, 1, 21.99),
(19, 3, 1,   95.00),
(20, 14,1,   79.00), (20, 2, 1, 35.00),
(21, 1, 1, 1199.00),
(22, 8, 1,   45.00), (22, 13, 2, 7.99),
(23, 5, 1,  549.00),
(24, 15,1,  149.00), (24, 3, 1, 95.00),
(25, 4, 2,   49.00),
(26, 6, 1,  349.00),
(27, 1, 1, 1199.00),
(28, 2, 3,   35.00),
(29, 9, 2,   18.99), (29, 10, 2, 17.99),
(30, 15,1,  149.00),
(31, 5, 1,  549.00),
(32, 3, 1,   95.00), (32, 14, 1, 79.00),
(33, 1, 1, 1199.00),
(34, 8, 1,   45.00),
(35, 6, 1,  349.00);

-- Payments (most orders paid, 2 orders missing payment for data quality demo)
INSERT INTO payments (order_id, amount, payment_date, method) VALUES
(1,  1234.00, '2022-02-10', 'card'),
(2,   549.00, '2022-06-15', 'card'),
(3,   244.00, '2023-01-20', 'paypal'),
(4,   119.00, '2022-03-05', 'card'),
(6,    55.98, '2022-04-18', 'card'),
(8,   599.00, '2022-05-22', 'transfer'),
(9,   349.00, '2022-05-30', 'card'),
(10,  174.00, '2022-12-14', 'paypal'),
(11,  125.97, '2022-06-08', 'card'),
(13,   35.00, '2022-07-15', 'card'),
(14,  549.00, '2022-08-20', 'card'),
(15,  149.00, '2022-08-25', 'paypal'),
(16, 1297.00, '2023-02-11', 'card'),
(17,  349.00, '2022-09-10', 'card'),
(18,  349.00, '2022-10-05', 'card'),
(19,   95.00, '2022-10-22', 'card'),
(20,  114.00, '2023-03-08', 'paypal'),
(21, 1199.00, '2022-11-11', 'card'),
(22,   60.98, '2022-11-28', 'card'),
(23,  549.00, '2022-12-02', 'card'),
(24,  244.00, '2023-04-15', 'card'),
(25,   98.00, '2023-01-05', 'transfer'),
(26,  349.00, '2023-01-25', 'card'),
(27, 1199.00, '2023-02-14', 'card'),
(28,  105.00, '2023-03-01', 'paypal'),
(29,   73.96, '2023-03-20', 'card'),
(30,  149.00, '2023-04-10', 'card'),
(31,  549.00, '2023-04-28', 'card'),
(32,  174.00, '2023-05-05', 'card'),
(33, 1199.00, '2023-05-18', 'card'),
(35,  349.00, '2023-06-20', 'card');
-- Orders 5 (refunded), 7 (cancelled), 34 intentionally have no payment row
