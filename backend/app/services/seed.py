import hashlib

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.case import Case
from app.models.collaboration import HelpResource, RuleConfig, UserProfile
from app.models.lawyer import LawyerProfile
from app.models.rule_package import RulePackage
from app.models.user import User
from app.services.rule_packages import (
    load_default_workflow_package,
    rule_package_checksum,
)


async def seed_demo_data(session: AsyncSession) -> None:
    user_count = await session.scalar(select(func.count()).select_from(User))
    if not user_count:
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

    demo_user = await session.scalar(select(User).where(User.username == "demo"))
    if demo_user is not None:
        demo_profile = await session.scalar(
            select(UserProfile).where(UserProfile.user_id == demo_user.id)
        )
        if demo_profile is None:
            session.add(
                UserProfile(
                    user_id=demo_user.id,
                    real_name="演示用户",
                    phone="13800000000",
                    id_number_masked="110***********1234",
                    id_number_hash=hashlib.sha256(b"demo-profile").hexdigest(),
                    verification_status="verified",
                )
            )

    await seed_reference_data(session)
    await seed_rule_content(session)
    await session.commit()


async def seed_reference_data(session: AsyncSession) -> None:
    help_count = await session.scalar(select(func.count()).select_from(HelpResource))
    if not help_count:
        session.add_all(
            [
                HelpResource(
                    resource_type="arbitration",
                    name="全国人社政务服务平台",
                    region="全国",
                    website="https://www.12333.gov.cn/",
                    phone="12333",
                    description="劳动保障政策和公共服务入口，具体仲裁机构以当地官方发布为准。",
                ),
                HelpResource(
                    resource_type="court",
                    name="人民法院在线服务",
                    region="全国",
                    website="https://zxfw.court.gov.cn/",
                    description="人民法院在线诉讼服务入口，具体立案要求以受理法院为准。",
                ),
                HelpResource(
                    resource_type="legal_aid",
                    name="中国法律服务网",
                    region="全国",
                    website="https://12348.gov.cn/",
                    phone="12348",
                    description="公共法律服务和法律援助咨询入口。",
                ),
            ]
        )


async def seed_rule_content(session: AsyncSession) -> None:
    package_count = await session.scalar(
        select(func.count()).select_from(RulePackage)
    )
    if package_count:
        return
    package = load_default_workflow_package()
    content = package.model_dump(mode="json")
    content["review_status"] = "pending_review"
    admin = await session.scalar(select(User).where(User.username == "admin"))
    session.add(
        RulePackage(
            package_type="workflow",
            package_id=package.package_id,
            version=package.version,
            status="pending_review",
            content=content,
            checksum=rule_package_checksum(content),
            created_by_id=admin.id if admin is not None else None,
        )
    )

    rule_count = await session.scalar(select(func.count()).select_from(RuleConfig))
    if not rule_count:
        categories = {
            "wage": ["payroll", "chat", "contract"],
            "termination": ["contract", "chat", "payroll"],
            "contract": ["contract", "chat", "attendance"],
            "overtime": ["attendance", "chat", "payroll"],
            "injury": ["medical", "chat", "contract"],
            "service_pay": ["settlement", "chat", "payroll"],
        }
        labels = {
            "wage": "欠薪",
            "termination": "违法解除",
            "contract": "未签劳动合同",
            "overtime": "加班费",
            "injury": "工伤待遇",
            "service_pay": "劳务报酬",
        }
        session.add_all(
            [
                RuleConfig(
                    dispute_type=dispute_type,
                    name=f"{labels[dispute_type]}演示证据规则",
                    evidence_requirements=requirements,
                    next_steps=["整理材料清单", "核对事实和金额", "申请人工复核"],
                    source_note="本地演示规则，待法律内容负责人复核。",
                    review_status="pending_review",
                )
                for dispute_type, requirements in categories.items()
            ]
        )
