from sqlalchemy import create_engine, text
from app.core.config import settings

url = settings.DATABASE_URL.replace('+asyncpg', '')
engine = create_engine(url)

with engine.connect() as conn:
    try:
        result = conn.execute(text('SELECT version_num FROM alembic_version'))
        version = result.scalar()
        print('Current alembic version:', version)
    except Exception as e:
        print('Alembic version error:', e)

    key_tables = [
        'daily_slaughter_records',
        'warehouse_purchase_orders',
        'warehouse_stocks',
        'finished_product_sale_items',
        'loss_records',
        'finished_product_receipts',
        'finished_product_aftersales',
    ]

    print('--- Key Tables ---')
    for t in key_tables:
        try:
            conn.execute(text(f"SELECT 1 FROM {t} LIMIT 1"))
            print(f"  {t}: EXISTS")
        except:
            print(f"  {t}: MISSING")

    print('--- Products Columns ---')
    result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='products'"))
    cols = [r[0] for r in result]
    for c in ['lead_time_days', 'avg_daily_consumption', 'safety_buffer', 'cost_price', 'stock_quantity', 'safety_stock']:
        print(f"  {c}: {'EXISTS' if c in cols else 'MISSING'}")

    print('--- FPS Columns ---')
    result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='finished_product_sales'"))
    cols = [r[0] for r in result]
    for c in ['slaughter_date', 'total_weight_kg']:
        print(f"  {c}: {'EXISTS' if c in cols else 'MISSING'}")
