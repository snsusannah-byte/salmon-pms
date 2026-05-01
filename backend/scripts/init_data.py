"""初始化数据脚本：创建默认管理员用户"""
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import get_password_hash
from app.models import User

async def init_db():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # 检查是否已有 admin 用户
        result = await session.execute(select(User).where(User.username == "admin"))
        existing = result.scalar_one_or_none()
        
        if existing:
            print("Admin user already exists")
            return
        
        admin = User(
            username="admin",
            email="admin@salmon.com",
            hashed_password=get_password_hash("admin123"),
            full_name="Administrator",
            role="admin",
            is_active=True,
        )
        session.add(admin)
        await session.commit()
        print("Default admin user created: admin / admin123")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_db())
