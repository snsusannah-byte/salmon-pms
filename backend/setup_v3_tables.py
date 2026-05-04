from sqlalchemy import create_engine, text
from app.core.config import settings

url = settings.DATABASE_URL.replace('+asyncpg', '')
engine = create_engine(url)

with engine.connect() as conn:
    conn = conn.execution_options(isolation_level="AUTOCOMMIT")

    print("=== Step 1: 检查并添加 Products 缺失字段 ===")
    result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='products'"))
    cols = [r[0] for r in result]
    print(f"现有字段: {', '.join(cols)}")

    new_cols = [
        ("lead_time_days", "INTEGER", "0"),
        ("avg_daily_consumption", "NUMERIC(12,4)", "0"),
        ("safety_buffer", "INTEGER", "0"),
        ("cost_price", "NUMERIC(15,2)", None),
        ("suggested_retail_price", "NUMERIC(15,2)", None),
        ("wholesale_price", "NUMERIC(15,2)", None),
        ("min_price", "NUMERIC(15,2)", None),
        ("stock_weight_kg", "NUMERIC(12,3)", "0"),
        ("stock_quantity", "INTEGER", "0"),
        ("safety_stock", "INTEGER", "0"),
    ]
    for col, dtype, default in new_cols:
        if col not in cols:
            sql = f"ALTER TABLE products ADD COLUMN {col} {dtype}"
            if default:
                sql += f" DEFAULT {default}"
            sql += " NULL"
            conn.execute(text(sql))
            print(f"  + 添加字段: {col}")
        else:
            print(f"  = 字段已存在: {col}")

    print("\n=== Step 2: 检查并添加 finished_product_sales 缺失字段 ===")
    result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='finished_product_sales'"))
    cols = [r[0] for r in result]
    print(f"现有字段: {', '.join(cols)}")

    fps_cols = [
        ("slaughter_date", "DATE", None),
        ("total_weight_kg", "NUMERIC(12,3)", "0"),
    ]
    for col, dtype, default in fps_cols:
        if col not in cols:
            sql = f"ALTER TABLE finished_product_sales ADD COLUMN {col} {dtype}"
            if default:
                sql += f" DEFAULT {default}"
            sql += " NULL"
            conn.execute(text(sql))
            print(f"  + 添加字段: {col}")
        else:
            print(f"  = 字段已存在: {col}")

    print("\n=== Step 3: 创建 daily_slaughter_records 表 ===")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS daily_slaughter_records (
            id SERIAL PRIMARY KEY,
            slaughter_date DATE NOT NULL,
            slaughter_type VARCHAR(20) NOT NULL DEFAULT 'whole_fish',
            fish_count INTEGER DEFAULT 0,
            total_weight_kg NUMERIC(12,3) NOT NULL,
            meat_weight_kg NUMERIC(12,3) NOT NULL,
            byproduct_head_count INTEGER DEFAULT 0,
            byproduct_tail_count INTEGER DEFAULT 0,
            byproduct_bone_count INTEGER DEFAULT 0,
            byproduct_trim_weight_kg NUMERIC(12,3) DEFAULT 0,
            loss_weight_kg NUMERIC(12,3) DEFAULT 0,
            loss_rate NUMERIC(5,2) DEFAULT 0,
            meat_rate NUMERIC(5,2) DEFAULT 0,
            cost_price_per_kg NUMERIC(12,4) DEFAULT 0,
            total_cost NUMERIC(15,2) DEFAULT 0,
            cost_source VARCHAR(50) DEFAULT 'auto',
            available_meat_kg NUMERIC(12,3) DEFAULT 0,
            sold_meat_kg NUMERIC(12,3) DEFAULT 0,
            is_locked BOOLEAN DEFAULT FALSE,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_slaughter_date ON daily_slaughter_records(slaughter_date)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_slaughter_type ON daily_slaughter_records(slaughter_type)"))
    print("  + 表创建完成")

    print("\n=== Step 4: 创建 warehouse_purchase_orders 表 ===")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS warehouse_purchase_orders (
            id SERIAL PRIMARY KEY,
            order_date DATE NOT NULL,
            product_id INTEGER NOT NULL REFERENCES products(id),
            supplier_id INTEGER REFERENCES companies(id),
            batch_no VARCHAR(100),
            quantity NUMERIC(12,3) NOT NULL,
            unit VARCHAR(20) DEFAULT 'kg',
            unit_price NUMERIC(12,4) NOT NULL,
            total_amount NUMERIC(15,2) NOT NULL,
            lead_time_days INTEGER DEFAULT 0,
            warehouse_location VARCHAR(100),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_wpo_order_date ON warehouse_purchase_orders(order_date)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_wpo_product_id ON warehouse_purchase_orders(product_id)"))
    print("  + 表创建完成")

    print("\n=== Step 5: 创建 warehouse_stocks 表 ===")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS warehouse_stocks (
            id SERIAL PRIMARY KEY,
            product_id INTEGER NOT NULL UNIQUE REFERENCES products(id),
            current_quantity NUMERIC(12,3) DEFAULT 0,
            reserved_quantity NUMERIC(12,3) DEFAULT 0,
            available_quantity NUMERIC(12,3) DEFAULT 0,
            unit_cost NUMERIC(12,4),
            warehouse_location VARCHAR(100),
            last_in_date DATE,
            last_out_date DATE,
            warning_threshold INTEGER DEFAULT 0,
            is_below_warning BOOLEAN DEFAULT FALSE,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    print("  + 表创建完成")

    print("\n=== Step 6: 创建 finished_product_sale_items 表 ===")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS finished_product_sale_items (
            id SERIAL PRIMARY KEY,
            sale_id INTEGER NOT NULL REFERENCES finished_product_sales(id),
            item_type VARCHAR(20) NOT NULL,
            product_id INTEGER NOT NULL REFERENCES products(id),
            weight_kg NUMERIC(12,3),
            quantity INTEGER,
            unit_price NUMERIC(12,4),
            amount NUMERIC(15,2) DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_fps_item_sale_id ON finished_product_sale_items(sale_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_fps_item_product_id ON finished_product_sale_items(product_id)"))
    print("  + 表创建完成")

    print("\n=== Step 7: 创建 loss_records 表 ===")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS loss_records (
            id SERIAL PRIMARY KEY,
            loss_date DATE NOT NULL,
            loss_type VARCHAR(20) NOT NULL,
            slaughter_date DATE,
            product_id INTEGER REFERENCES products(id),
            weight_kg NUMERIC(12,3) DEFAULT 0,
            quantity INTEGER DEFAULT 0,
            reason TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_loss_date ON loss_records(loss_date)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_loss_type ON loss_records(loss_type)"))
    print("  + 表创建完成")

    print("\n=== Step 8: 修复 alembic_version 表 ===")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS alembic_version (
            version_num VARCHAR(32) NOT NULL PRIMARY KEY
        )
    """))
    conn.execute(text("DELETE FROM alembic_version"))
    conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('v3_complete')"))
    print("  + alembic_version 已设置为 v3_complete")

    print("\n=== 全部完成！ ===")
