from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.case import Case
from app.models.lawyer import LawyerProfile
from app.models.user import User


async def seed_demo_data(session: AsyncSession) -> None:
    user_count = await session.scalar(select(func.count()).select_from(User))
    if user_count:
        return

    admin = User(
        username="admin",
        password_hash=hash_password("Admin123!"),
        role="admin",
        display_name="平台管理员",
    )
    lawyer = User(
        username="lawyer",
        password_hash=hash_password("Lawyer123!"),
        role="lawyer",
        display_name="李律师",
    )
    demo = User(
        username="demo",
        password_hash=hash_password("Demo123!"),
        role="user",
        display_name="演示用户",
    )
    session.add_all([admin, lawyer, demo])
    await session.flush()

    session.add(
        LawyerProfile(
            user_id=lawyer.id,
            license_no="DEMO-LAWYER-001",
            specialties="欠薪、违法解除、工伤待遇",
            bio="平台内部演示律师，负责劳动纠纷人工复核。",
        )
    )
    session.add(
        Case(
            owner_id=demo.id,
            title="工地欠薪咨询",
            dispute_type="wage",
            legal_relationship="labor",
            stage="evidence",
            location="上海市",
            facts="在工地工作三个月，没有签书面合同，老板拖欠两个月工资。",
            summary="用户咨询工地欠薪及证据准备。",
            classification={"dispute_type": "wage", "source": "demo_seed"},
        )
    )
    await session.commit()
