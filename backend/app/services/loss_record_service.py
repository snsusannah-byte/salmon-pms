"""
损耗处理 Service
"""
from datetime import date
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finished_product_v2 import LossRecord


class LossRecordService:
    """损耗处理服务"""

    @staticmethod
    async def list_records(
        db: AsyncSession,
        loss_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        product_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[LossRecord], int]:
        """损耗记录列表"""
        query = select(LossRecord)
        
        if loss_type:
            query = query.where(LossRecord.loss_type == loss_type)
        if start_date:
            query = query.where(LossRecord.loss_date >= start_date)
        if end_date:
            query = query.where(LossRecord.loss_date <= end_date)
        if product_id:
            query = query.where(LossRecord.product_id == product_id)
        
        query = query.order_by(desc(LossRecord.loss_date))
        
        total_result = await db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = total_result.scalar()
        
        result = await db.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total

    @staticmethod
    async def get_by_id(db: AsyncSession, record_id: int) -> Optional[LossRecord]:
        """按ID获取"""
        result = await db.execute(
            select(LossRecord).where(LossRecord.id == record_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_record(db: AsyncSession, data: dict) -> LossRecord:
        """创建损耗记录"""
        record = LossRecord(
            loss_date=data.get("loss_date", date.today()),
            loss_type=data["loss_type"],
            slaughter_date=data.get("slaughter_date"),
            product_id=data.get("product_id"),
            weight_kg=Decimal(str(data.get("weight_kg", 0))),
            quantity=data.get("quantity", 0) or 0,
            reason=data.get("reason"),
            notes=data.get("notes"),
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        
        # 扣减当日可用肉或库存
        await LossRecordService._deduct_stock(db, record)
        
        return record

    @staticmethod
    async def _deduct_stock(db: AsyncSession, record: LossRecord):
        """损耗登记后扣减库存"""
        # 1. 如果有slaughter_date，扣减当日可用肉
        if record.slaughter_date and record.weight_kg > 0:
            from app.services.daily_slaughter_service import DailySlaughterService
            
            slaughter_record = await DailySlaughterService.get_by_date(db, record.slaughter_date)
            if slaughter_record:
                # 扣减可用肉（损耗不直接扣sold_meat_kg，而是作为独立字段影响可用肉）
                # 这里简化处理：将损耗重量加到loss_weight_kg中，重新计算可用肉
                slaughter_record.loss_weight_kg = (
                    slaughter_record.loss_weight_kg + record.weight_kg
                ).quantize(Decimal("0.001"))
                
                # 重新计算可用肉
                slaughter_record.available_meat_kg = (
                    slaughter_record.meat_weight_kg
                    - slaughter_record.byproduct_trim_weight_kg
                    - slaughter_record.loss_weight_kg
                    - slaughter_record.sold_meat_kg
                ).quantize(Decimal("0.001"))
                
                if slaughter_record.available_meat_kg < 0:
                    slaughter_record.available_meat_kg = Decimal("0")
                
                # 重新计算损耗率
                if slaughter_record.total_weight_kg > 0:
                    slaughter_record.loss_rate = (
                        slaughter_record.loss_weight_kg / slaughter_record.total_weight_kg * 100
                    ).quantize(Decimal("0.01"))
                
                await db.commit()
        
        # 2. 如果有product_id，扣减仓库库存
        if record.product_id and (record.weight_kg > 0 or record.quantity > 0):
            from app.services.warehouse_service import WarehouseService
            
            deduct_qty = record.weight_kg if record.weight_kg > 0 else Decimal(str(record.quantity))
            try:
                await WarehouseService.stock_out(
                    db,
                    product_id=record.product_id,
                    quantity=deduct_qty,
                    reason=f"loss:{record.loss_type}",
                )
            except ValueError:
                # 库存不足时记录但不阻止
                pass

    @staticmethod
    async def update_record(
        db: AsyncSession,
        record: LossRecord,
        data: dict,
    ) -> LossRecord:
        """更新损耗记录"""
        for key in ["loss_date", "loss_type", "slaughter_date", "product_id", "reason", "notes"]:
            if key in data and data[key] is not None:
                setattr(record, key, data[key])
        
        if "weight_kg" in data and data["weight_kg"] is not None:
            record.weight_kg = Decimal(str(data["weight_kg"]))
        if "quantity" in data and data["quantity"] is not None:
            record.quantity = data["quantity"]
        
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def delete_record(db: AsyncSession, record: LossRecord):
        """删除损耗记录"""
        await db.delete(record)
        await db.commit()

    @staticmethod
    async def get_summary(
        db: AsyncSession,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        """损耗汇总统计"""
        query = select(LossRecord)
        if start_date:
            query = query.where(LossRecord.loss_date >= start_date)
        if end_date:
            query = query.where(LossRecord.loss_date <= end_date)
        
        result = await db.execute(query)
        items = result.scalars().all()
        
        total_weight = sum(r.weight_kg for r in items)
        total_quantity = sum(r.quantity for r in items)
        
        by_type = {}
        for item in items:
            lt = item.loss_type
            if lt not in by_type:
                by_type[lt] = {"count": 0, "weight_kg": Decimal("0"), "quantity": 0}
            by_type[lt]["count"] += 1
            by_type[lt]["weight_kg"] += item.weight_kg
            by_type[lt]["quantity"] += item.quantity
        
        # Decimal序列化
        for lt in by_type:
            by_type[lt]["weight_kg"] = float(by_type[lt]["weight_kg"])
        
        return {
            "total_loss_weight_kg": total_weight.quantize(Decimal("0.001")),
            "total_loss_quantity": total_quantity,
            "by_type": by_type,
        }
