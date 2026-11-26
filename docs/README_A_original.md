# Historical reference — original Member A README

Paths below describe the original flat project, not the current layout. Use root README.md for commands.

## 1. 文件摆放

olist_A_windows
├── olist_customers_dataset.csv
├── olist_geolocation_dataset.csv
├── olist_order_items_dataset.csv
├── olist_order_payments_dataset.csv
├── olist_order_reviews_dataset.csv
├── olist_orders_dataset.csv
├── olist_products_dataset.csv
├── olist_sellers_dataset.csv
├── product_category_name_translation.csv
├── schema.sql                
├── load_to_sqlite.py         
├── seller_module.sql         
├── seller_analysis.py       
└── charts/                   

## 2. 文件说明

| 文件 | 作用 | 对应 A 的任务 |
|---|---|---|
| `schema.sql` | 10 张 3NF 表的 DDL，含主外键、CHECK 约束、索引 | Schema、3NF |
| `load_to_sqlite.py` | 清洗源数据并按 3NF 入库，自动校验外键孤儿为 0 | Database Design |
| `seller_module.sql` | 卖家性能视图 + 排行 / 分州 / 分层 / 低分高量 / 趋势 / 集中度查询 | Seller Module |
| `seller_analysis.py` | 复现卖家指标并生成图表 | 卖家统计分析 |

## 3. 成员字段参考

| 模块 | 读取表 | 连接键 |
|---|---|---|
| B Customer | `customer`, `customer_profile`, `orders` | `customer_id`, `customer_unique_id` |
| C Product | `product`, `product_category` | `product_id`, `product_category_name` |
| D Order | `orders`, `order_item` | `order_id`, `customer_id`, `order_status` |
| E Payment/Review | `payment`, `review` | `order_id`, `payment_type`, `review_score` |

