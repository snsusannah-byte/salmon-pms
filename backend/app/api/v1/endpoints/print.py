from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.print_service import PrintService

router = APIRouter()


@router.get("/{sale_type}/{sale_id}")
async def get_sale_print_data(
    sale_type: str,
    sale_id: int,
    db: AsyncSession = Depends(get_db),
):
    """统一销售单打印数据

    - **sale_type**: whole_fish（进口销售/整鱼销售） | finished_product_v2（以销定采/预包装/海鲜物料）
    - **sale_id**: 销售单 ID
    """
    if sale_type not in {"whole_fish", "finished_product_v2"}:
        raise HTTPException(status_code=400, detail="不支持的打印类型")
    return await PrintService.get_sale_print_data(db, sale_type, sale_id)
