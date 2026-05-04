import asyncio
from logging.config import fileConfig

from sqlalchemy import pool, create_engine
from sqlalchemy.engine import Connection

from alembic import context

# Import app models for autogenerate
import sys
sys.path.append(".")
from app.models.base import Base
from app.models import (
    Company, BankAccount, User,
    ImportInvoice, Product, ProductBOM, InvoiceProduct,
    Shipment, Batch, BatchInvoice,
    ExchangeRecord, ImportTax, ClearanceCost,
    WholeFishSale, SalesReceipt, AftersalesRecord,
    TransactionRecord, Inventory, InventoryMovement,
    AuditTrail, Notification, SystemConfig,
)
from app.core.config import settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def get_url():
    return settings.DATABASE_URL.replace("+asyncpg", "")

def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """同步方式运行迁移（修复async驱动问题）"""
    url = get_url()
    connectable = create_engine(url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        do_run_migrations(connection)

    connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
