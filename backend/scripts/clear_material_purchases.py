"""
清空辅料采购模块所有数据
"""
import asyncio
from sqlalchemy import select, delete, text
from app.core.database import get_db
from app.models import (
    MaterialPurchaseOrder,
    MaterialPurchaseItem,
    MaterialBatch,
    StockInbound,
    StockMovement,
    PurchaseOrderV2,
    PurchaseOrderProductV2,
    TransactionRecord,
)

async def clear_all():
    db_gen = get_db()
    db = await db_gen.__anext__()
    try:
        # 1. 查出所有物料采购单
        result = await db.execute(select(MaterialPurchaseOrder))
        orders = result.scalars().all()
        print(f"找到 {len(orders)} 条采购单")

        order_ids = [o.id for o in orders]
        order_nos = [o.order_no for o in orders]

        if not order_ids:
            print("没有数据需要清理")
            return

        # 2. 查出所有关联的采购明细
        items_result = await db.execute(
            select(MaterialPurchaseItem).where(
                MaterialPurchaseItem.purchase_order_id.in_(order_ids)
            )
        )
        items = items_result.scalars().all()
        item_ids = [i.id for i in items]
        print(f"关联明细 {len(item_ids)} 条")

        # 3. 删除物料批次（按明细 ID）
        if item_ids:
            batch_del = await db.execute(
                delete(MaterialBatch).where(
                    MaterialBatch.purchase_order_item_id.in_(item_ids)
                )
            )
            print(f"删除批次 {batch_del.rowcount} 条")

        # 4. 删除入库记录 -> 先删对应的 stock_movement
        inbound_result = await db.execute(
            select(StockInbound.id).where(
                StockInbound.source_type == "material_purchase",
                StockInbound.source_id.in_(order_ids),
            )
        )
        inbound_ids = [r[0] for r in inbound_result.all()]
        if inbound_ids:
            sm_del = await db.execute(
                delete(StockMovement).where(
                    StockMovement.ref_id.in_(inbound_ids),
                    StockMovement.ref_type == "StockInbound",
                )
            )
            print(f"删除入库关联的库存变动 {sm_del.rowcount} 条")

            si_del = await db.execute(
                delete(StockInbound).where(StockInbound.id.in_(inbound_ids))
            )
            print(f"删除入库记录 {si_del.rowcount} 条")

        # 5. 删除 ref_type='material_purchase' 的 stock_movement
        sm_del2 = await db.execute(
            text("DELETE FROM stock_movements WHERE ref_type = 'material_purchase' AND ref_id = ANY(:ids)"),
            {"ids": order_ids},
        )
        print(f"删除物料采购库存变动 {sm_del2.rowcount} 条")

        # 6. 删除应付记录（先子表后父表）
        for order_no in order_nos:
            po_result = await db.execute(
                select(PurchaseOrderV2.id).where(
                    PurchaseOrderV2.purchase_no == f"CGCL-{order_no}"
                )
            )
            po_v2_id = po_result.scalar_one_or_none()
            if po_v2_id:
                await db.execute(
                    delete(PurchaseOrderProductV2).where(
                        PurchaseOrderProductV2.purchase_order_id == po_v2_id
                    )
                )
                await db.execute(
                    delete(PurchaseOrderV2).where(PurchaseOrderV2.id == po_v2_id)
                )
                print(f"删除应付记录 CGCL-{order_no}")

        # 7. 删除交易流水
        for order_no in order_nos:
            tr_del = await db.execute(
                delete(TransactionRecord).where(
                    TransactionRecord.reference_no == order_no
                )
            )
            if tr_del.rowcount > 0:
                print(f"删除交易流水 {order_no}: {tr_del.rowcount} 条")

        # 8. 删除采购明细（cascade 理论上会自动删，但手动确保）
        if item_ids:
            await db.execute(
                delete(MaterialPurchaseItem).where(
                    MaterialPurchaseItem.id.in_(item_ids)
                )
            )
            print(f"删除采购明细")

        # 9. 删除采购单
        order_del = await db.execute(
            delete(MaterialPurchaseOrder).where(
                MaterialPurchaseOrder.id.in_(order_ids)
            )
        )
        print(f"删除采购单 {order_del.rowcount} 条")

        await db.commit()
        print("✅ 全部清理完成")

    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        print(f"❌ 清理失败: {e}")
    finally:
        try:
            await db_gen.__anext__()
        except StopAsyncIteration:
            pass

if __name__ == "__main__":
    asyncio.run(clear_all())
