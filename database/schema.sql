PRAGMA foreign_keys = ON;

-- 1. GEOLOCATION: zip -> city/state/coordinate dimension (removes transitive dep)
CREATE TABLE geolocation (
    zip_code_prefix      TEXT PRIMARY KEY,
    avg_lat              REAL,
    avg_lng              REAL,
    city                 TEXT NOT NULL,
    state                TEXT NOT NULL
);

-- 2. CUSTOMER_PROFILE: natural person (customer_unique_id)
CREATE TABLE customer_profile (
    customer_unique_id   TEXT PRIMARY KEY
);

-- 3. CUSTOMER: per-order customer record (city/state derived via geolocation)
CREATE TABLE customer (
    customer_id          TEXT PRIMARY KEY,
    customer_unique_id   TEXT NOT NULL,
    zip_code_prefix      TEXT NOT NULL,
    FOREIGN KEY (customer_unique_id) REFERENCES customer_profile(customer_unique_id),
    FOREIGN KEY (zip_code_prefix)     REFERENCES geolocation(zip_code_prefix)
);

-- 4. SELLER
CREATE TABLE seller (
    seller_id            TEXT PRIMARY KEY,
    zip_code_prefix      TEXT NOT NULL,
    FOREIGN KEY (zip_code_prefix) REFERENCES geolocation(zip_code_prefix)
);

-- 5. PRODUCT_CATEGORY: PT -> EN translation dimension
CREATE TABLE product_category (
    product_category_name        TEXT PRIMARY KEY,
    product_category_name_english TEXT
);

-- 6. PRODUCT
CREATE TABLE product (
    product_id               TEXT PRIMARY KEY,
    product_category_name    TEXT,
    product_name_length      INTEGER,
    product_description_length INTEGER,
    product_photos_qty       INTEGER,
    product_weight_g         INTEGER,
    product_length_cm        INTEGER,
    product_height_cm        INTEGER,
    product_width_cm         INTEGER,
    FOREIGN KEY (product_category_name) REFERENCES product_category(product_category_name)
);

-- 7. ORDERS
CREATE TABLE orders (
    order_id                    TEXT PRIMARY KEY,
    customer_id                 TEXT NOT NULL,
    order_status                TEXT NOT NULL CHECK (
        order_status IN ('created','approved','invoiced','processing','shipped',
                         'delivered','unavailable','canceled')),
    order_purchase_timestamp          DATETIME,
    order_approved_at                DATETIME,
    order_delivered_carrier_date     DATETIME,
    order_delivered_customer_date    DATETIME,
    order_estimated_delivery_date     DATE,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
);

-- 8. ORDER_ITEM: composite PK; price/freight depend on the whole item key
CREATE TABLE order_item (
    order_id             TEXT NOT NULL,
    order_item_id        INTEGER NOT NULL,
    product_id           TEXT NOT NULL,
    seller_id            TEXT NOT NULL,
    shipping_limit_date  DATETIME,
    price                REAL NOT NULL CHECK (price >= 0),
    freight_value        REAL NOT NULL CHECK (freight_value >= 0),
    PRIMARY KEY (order_id, order_item_id),
    FOREIGN KEY (order_id)   REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES product(product_id),
    FOREIGN KEY (seller_id)  REFERENCES seller(seller_id)
);

-- 9. PAYMENT: one order may split into several payments/installments
CREATE TABLE payment (
    order_id             TEXT NOT NULL,
    payment_sequential   INTEGER NOT NULL,
    payment_type         TEXT CHECK (
        payment_type IN ('credit_card','boleto','voucher','debit_card','not_defined')),
    payment_installments INTEGER CHECK (payment_installments >= 0),
    payment_value        REAL CHECK (payment_value >= 0),
    PRIMARY KEY (order_id, payment_sequential),
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

-- 10. REVIEW: surrogate PK because source review_id repeats (814 duplicates)
CREATE TABLE review (
    review_pk            INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id            TEXT,
    order_id             TEXT NOT NULL,
    review_score         INTEGER CHECK (review_score BETWEEN 1 AND 5),
    review_comment_title    TEXT,
    review_comment_message  TEXT,
    review_creation_date    DATETIME,
    review_answer_timestamp DATETIME,
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

-- Indexes: foreign keys + high-frequency analytical columns
CREATE INDEX idx_orders_customer    ON orders(customer_id);
CREATE INDEX idx_orders_status      ON orders(order_status);
CREATE INDEX idx_orders_purchase_ts ON orders(order_purchase_timestamp);
CREATE INDEX idx_order_item_product ON order_item(product_id);
CREATE INDEX idx_order_item_seller  ON order_item(seller_id);
CREATE INDEX idx_order_item_order    ON order_item(order_id);
CREATE INDEX idx_payment_order       ON payment(order_id);
CREATE INDEX idx_review_order        ON review(order_id);
CREATE INDEX idx_review_score        ON review(review_score);
CREATE INDEX idx_review_review_id    ON review(review_id);
CREATE INDEX idx_customer_profile    ON customer(customer_unique_id);
CREATE INDEX idx_product_category    ON product(product_category_name);
