"""
每日宰杀记录 Service
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finished_product_v2 import (
    DailySlaughterRecord,
    SlaughterType,
    WarehouseStock,
    LossRecord,
)
from app.models import Product, ProductCategory, Company, MovementType


class DailySlaughterService:
    """每日宰杀记录服务"""

    @staticmethod
    async def list_records(
        db: AsyncSession,
        slaughter_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[DailySlaughterRecord], int]:
        """列表查询"""
        query = select(DailySlaughterRecord)
        
        if slaughter_type:
            query = query.where(DailySlaughterRecord.slaughter_type == slaughter_type)
        if start_date:
            query = query.where(DailySlaughterRecord.slaughter_date >= start_date)
        if end_date:
            query = query.where(DailySlaughterRecord.slaughter_date <= end_date)
        
        query = query.order_by(DailySlaughterRecord.slaughter_date.desc())
        
        total_result = await db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = total_result.scalar()
        
        result = await db.execute(query.offset(skip).limit(limit))
        items = result.scalars().all()
        return list(items), total

    @staticmethod
    async def get_by_id(db: AsyncSession, record_id: int) -> Optional[DailySlaughterRecord]:
        """按ID获取"""
        result = await db.execute(
            select(DailySlaughterRecord).where(DailySlaughterRecord.id == record_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_date(db: AsyncSession, slaughter_date: date) -> Optional[DailySlaughterRecord]:
        """按日期获取（每天只能有一条记录）"""
        result = await db.execute(
            select(DailySlaughterRecord)
            .where(DailySlaughterRecord.slaughter_date == slaughter_date)
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_available_slaughter_dates(
        db: AsyncSession,
        min_available_kg: Decimal = Decimal("0"),
    ) -> List[dict]:
        """获取可供销售的宰杀日期列表（关联销售用）"""
        result = await db.execute(
            select(DailySlaughterRecord)
            .where(DailySlaughterRecord.is_locked == True)
            .where(DailySlaughterRecord.available_meat_kg > min_available_kg)
            .order_by(DailySlaughterRecord.slaughter_date.desc())
        )
        items = result.scalars().all()
        return [
            {
                "slaughter_date": item.slaughter_date,
                "available_meat_kg": item.available_meat_kg,
                "cost_price_per_kg": item.cost_price_per_kg,
                "is_locked": item.is_locked,
            }
            for item in items
        ]

    @staticmethod
    def _calculate_rates(data: dict) -> dict:
        """自动计算出肉率、损耗率、成本"""
        total_weight = Decimal(str(data.get("total_weight_kg", 0)))
        meat_weight = Decimal(str(data.get("meat_weight_kg", 0)))
        loss_weight = Decimal(str(data.get("loss_weight_kg", 0)))
        trim_weight = Decimal(str(data.get("byproduct_trim_weight_kg", 0)))
        
        # 出肉率 = 成品肉 / 总重 × 100
        meat_rate = Decimal("0")
        if total_weight > 0:
            meat_rate = (meat_weight / total_weight * 100).quantize(Decimal("0.01"))
        
        # 损耗率 = 损耗 / 总重 × 100
        loss_rate = Decimal("0")
        if total_weight > 0:
            loss_rate = (loss_weight / total_weight * 100).quantize(Decimal("0.01"))
        
        # 重量平衡校验（提醒用，不阻止保存）
        byproduct_weight = (
            Decimal(str(data.get("byproduct_head_count", 0))) * Decimal("0.3") +  # 鱼头约0.3kg
            Decimal(str(data.get("byproduct_tail_count", 0))) * Decimal("0.1") +  # 鱼尾约0.1kg
            Decimal(str(data.get("byproduct_bone_count", 0))) * Decimal("0.2")   # 鱼骨约0.2kg
        )
        expected_total = meat_weight + loss_weight + trim_weight + byproduct_weight
        
        # 成本计算
        cost_price_per_kg = data.get("cost_price_per_kg")
        total_cost = Decimal("0")
        cost_source = "manual"
        
        if cost_price_per_kg is None or cost_price_per_kg == 0:
            # 自动计算：尝试从整鱼采购成本获取
            cost_source = "auto"
            # 如果没有提供成本价，后续可以从关联的采购入库单计算
            # 这里先使用默认值，实际业务中通常由用户输入或从采购单关联
            cost_price_per_kg = Decimal("0")
        
        if cost_price_per_kg and meat_weight > 0:
            total_cost = (cost_price_per_kg * total_weight).quantize(Decimal("0.01"))
        
        # 计算当日可用肉 = 前期累计(略，简化处理) + 当日产出 - 边角料 - 损耗
        # 简化：可用肉 = 成品肉 - 边角料 - 损耗（假设前期为0）
        available_meat = meat_weight - trim_weight - loss_weight
        if available_meat < 0:
            available_meat = Decimal("0")
        
        return {
            "meat_rate": meat_rate,
            "loss_rate": loss_rate,
            "cost_price_per_kg": cost_price_per_kg or Decimal("0"),
            "total_cost": total_cost,
            "cost_source": cost_source,
            "available_meat_kg": available_meat.quantize(Decimal("0.001")),
            "sold_meat_kg": Decimal("0"),
            "weight_balance_ok": abs(total_weight - expected_total) <= Decimal("0.5"),  # 允许0.5kg误差
            "weight_balance_diff": (total_weight - expected_total).quantize(Decimal("0.001")),
        }

    @staticmethod
    async def create_record(db: AsyncSession, data: dict) -> DailySlaughterRecord:
        """创建宰杀记录"""
        slaughter_type = data.get("slaughter_type", "whole_fish")
        
        # 鱼柳类型：fish_count为0，副产品为0
        if slaughter_type == SlaughterType.FILLET.value:
            data["fish_count"] = 0
            data["byproduct_head_count"] = 0
            data["byproduct_tail_count"] = 0
            data["byproduct_bone_count"] = 0
        
        # 自动计算
        calculated = DailySlaughterService._calculate_rates(data)
        
        record_data = {
            "slaughter_date": data["slaughter_date"],
            "slaughter_type": slaughter_type,
            "fish_count": data.get("fish_count", 0) or 0,
            "total_weight_kg": Decimal(str(data["total_weight_kg"])),
            "meat_weight_kg": Decimal(str(data["meat_weight_kg"])),
            "byproduct_head_count": data.get("byproduct_head_count", 0) or 0,
            "byproduct_tail_count": data.get("byproduct_tail_count", 0) or 0,
            "byproduct_bone_count": data.get("byproduct_bone_count", 0) or 0,
            "byproduct_trim_weight_kg": Decimal(str(data.get("byproduct_trim_weight_kg", 0))),
            "loss_weight_kg": Decimal(str(data.get("loss_weight_kg", 0))),
            "loss_rate": calculated["loss_rate"],
            "meat_rate": calculated["meat_rate"],
            "cost_price_per_kg": calculated["cost_price_per_kg"],
            "total_cost": calculated["total_cost"],
            "cost_source": calculated["cost_source"],
            "available_meat_kg": calculated["available_meat_kg"],
            "sold_meat_kg": calculated["sold_meat_kg"],
            "is_locked": False,
            "notes": data.get("notes"),
        }
        
        record = DailySlaughterRecord(**record_data)
        db.add(record)
        await db.commit()
        await db.refresh(record)
        
        # 自动扣减整鱼/鱼柳库存
        await DailySlaughterService._deduct_warehouse_stock(db, record)
        
        return record

    @staticmethod
    async def _deduct_warehouse_stock(db: AsyncSession, record: DailySlaughterRecord):
        """宰杀登记时自动扣减整鱼/鱼柳库存，并将产出入库到成品仓库"""
        from app.services.warehouse_service import WarehouseService
        from app.models import Product
        from sqlalchemy import select

        # 1. 扣减原料库存（整鱼仓库）
        category_filter = (
            ProductCategory.WHOLE_FISH.value
            if record.slaughter_type == SlaughterType.WHOLE_FISH.value
            else ProductCategory.FILLET.value
        )
        result = await db.execute(
            select(Product).where(Product.category == category_filter).limit(1)
        )
        raw_product = result.scalar_one_or_none()

        if raw_product:
            try:
                await WarehouseService.stock_out(
                    db,
                    product_id=raw_product.id,
                    quantity=record.total_weight_kg,
                    reason=f"屠宰消耗 {record.slaughter_date}",
                )
            except ValueError:
                pass

        # 2. 成品肉入库（成品仓库）
        result = await db.execute(
            select(Product).where(Product.category == ProductCategory.FINISHED_PRODUCT.value).limit(1)
        )
        finished_product = result.scalar_one_or_none()

        if finished_product and record.meat_weight_kg > 0:
            await WarehouseService.stock_in(
                db,
                product_id=finished_product.id,
                quantity=record.meat_weight_kg,
                unit_price=record.cost_price_per_kg or Decimal("0"),
                reason=f"屠宰产出 {record.slaughter_date}",
            )

    @staticmethod
    async def update_record(
        db: AsyncSession,
        record: DailySlaughterRecord,
        data: dict,
    ) -> DailySlaughterRecord:
        """更新宰杀记录（仅未锁定时）"""
        if record.is_locked:
            raise ValueError("该记录已锁定，不可修改")
        
        # 合并数据
        current_data = {
            "total_weight_kg": record.total_weight_kg,
            "meat_weight_kg": record.meat_weight_kg,
            "fish_count": record.fish_count,
            "byproduct_head_count": record.byproduct_head_count,
            "byproduct_tail_count": record.byproduct_tail_count,
            "byproduct_bone_count": record.byproduct_bone_count,
            "byproduct_trim_weight_kg": record.byproduct_trim_weight_kg,
            "loss_weight_kg": record.loss_weight_kg,
            "cost_price_per_kg": record.cost_price_per_kg,
        }
        current_data.update({k: v for k, v in data.items() if v is not None})
        
        # 重新计算
        calculated = DailySlaughterService._calculate_rates(current_data)
        
        for key, value in calculated.items():
            if hasattr(record, key):
                setattr(record, key, value)
        
        # 更新用户输入的字段
        for key in ["fish_count", "total_weight_kg", "meat_weight_kg",
                    "byproduct_head_count", "byproduct_tail_count", "byproduct_bone_count",
                    "byproduct_trim_weight_kg", "loss_weight_kg", "notes"]:
            if key in data and data[key] is not None:
                setattr(record, key, Decimal(str(data[key])) if "weight" in key or key in ["total_weight_kg", "meat_weight_kg"] else data[key])
        
        if "cost_price_per_kg" in data and data["cost_price_per_kg"] is not None:
            record.cost_price_per_kg = Decimal(str(data["cost_price_per_kg"]))
            record.cost_source = "manual"
        
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def delete_record(db: AsyncSession, record: DailySlaughterRecord):
        """删除宰杀记录"""
        if record.is_locked:
            raise ValueError("该记录已锁定，不可删除")
        if record.sold_meat_kg > 0:
            raise ValueError("该记录已有关联销售，不可删除")
        
        await db.delete(record)
        await db.commit()

    @staticmethod
    async def lock_record(db: AsyncSession, record: DailySlaughterRecord):
        """锁定宰杀记录（成本确认后锁定）"""
        record.is_locked = True
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def update_sold_weight(
        db: AsyncSession,
        slaughter_date: date,
        sold_weight_kg: Decimal,
    ):
        """更新已售肉重（销售时调用）"""
        result = await db.execute(
            select(DailySlaughterRecord)
            .where(DailySlaughterRecord.slaughter_date == slaughter_date)
        )
        record = result.scalar_one_or_none()
        if record:
            record.sold_meat_kg = (record.sold_meat_kg + sold_weight_kg).quantize(Decimal("0.001"))
            record.available_meat_kg = (record.meat_weight_kg - record.byproduct_trim_weight_kg - 
                                         record.loss_weight_kg - record.sold_meat_kg).quantize(Decimal("0.001"))
            if record.available_meat_kg < 0:
                record.available_meat_kg = Decimal("0")
            await db.commit()
            await db.refresh(record)
        return record

    @staticmethod
    async def get_summary(
        db: AsyncSession,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        """宰杀记录汇总"""
        query = select(DailySlaughterRecord)
        if start_date:
            query = query.where(DailySlaughterRecord.slaughter_date >= start_date)
        if end_date:
            query = query.where(DailySlaughterRecord.slaughter_date <= end_date)
        
        result = await db.execute(query)
        items = result.scalars().all()
        
        total_days = len(items)
        total_fish_count = sum(r.fish_count or 0 for r in items)
        total_meat_kg = sum(r.meat_weight_kg for r in items)
        total_loss_kg = sum(r.loss_weight_kg for r in items)
        
        avg_meat_rate = Decimal("0")
        avg_cost_price = Decimal("0")
        avg_loss_rate = Decimal("0")
        
        if items:
            avg_meat_rate = (sum(r.meat_rate for r in items) / len(items)).quantize(Decimal("0.01"))
            avg_cost_price = (sum(r.cost_price_per_kg for r in items) / len(items)).quantize(Decimal("0.01"))
            avg_loss_rate = (sum(r.loss_rate for r in items) / len(items)).quantize(Decimal("0.01"))
        
        return {
            "total_days": total_days,
            "total_fish_count": total_fish_count,
            "total_meat_kg": total_meat_kg.quantize(Decimal("0.001")),
            "avg_meat_rate": avg_meat_rate,
            "avg_cost_price": avg_cost_price,
            "total_loss_kg": total_loss_kg.quantize(Decimal("0.001")),
            "avg_loss_rate": avg_loss_rate,
        }
