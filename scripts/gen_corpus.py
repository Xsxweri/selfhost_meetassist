"""造多场富内容会议，供记忆抽取质量评测。

每场 summary 明确覆盖 decision/action/preference/fact/entity 五类，
写入 meetings 表（指定 owner），随后用 eval_extract.py --ingest 抽取评测。

用法：
    uv run python scripts/gen_corpus.py --owner a@b.com
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.meeting import Meeting
from app.models.user import User

CORPUS = [
    ("Q3市场预算评审会",
     "决议：批准Q3市场预算500万元，由张总负责审批。行动项：财务需在下周一前拨付首笔200万元。"
     "团队偏好保守投放策略，优先选择线上渠道而非线下广告。背景事实：上季度实际花费420万元，超支8%。"
     "关键干系人：张总担任市场VP，主导本次预算分配。"),
    ("产品V2上线排期会",
     "决议：产品V2正式上线时间定为9月30日。行动项：王五负责后端接口开发，须在10月8日前完成压力测试。"
     "团队习惯将例会固定在每周三上午召开。事实：当前自动化测试覆盖率为75%。"
     "负责人：王五是后端组长，统筹接口交付。"),
    ("客户A续约谈判会",
     "决议：客户A合同金额定为120万元，续约期两年。行动项：赵六需在本周五前发出续约合同草案。"
     "客户偏好通过邮件沟通，不接受电话推销。事实：客户A已合作三年，历史付款准时。"
     "关键人物：赵六是客户A的对接销售，负责本次续约。"),
    ("合规风险专项会",
     "决议：全公司须在月底前完成数据合规自查。行动项：李四需在下周五前提交合规报告。"
     "管理层倾向聘请外部律所复核，而非仅内部审查。事实：新政策编号POL-2024-087已于本月生效。"
     "关键实体：合规部由李四牵头，对接外部律所。"),
    ("校园招聘计划会",
     "决议：2025届校招名额定为50人，重点招募算法岗。行动项：HR需在10月前完成20所目标高校的宣讲排期。"
     "团队偏好招收有实习经验的候选人。事实：去年校招录用率为15%。"
     "负责人：HR总监陈七统筹本次校招。"),
    ("技术架构升级评审会",
     "决议：核心系统迁移到Kubernetes容器化部署，Q4完成。行动项：架构组需在两周内产出迁移方案。"
     "团队倾向渐进式迁移，反对一次性重写。事实：现有系统日均请求量2000万次。"
     "关键人物：孙八是首席架构师，主导迁移设计。"),
    ("年度运营复盘会",
     "决议：明年运营重心转向存量用户留存。行动项：运营组需在下月前建立用户分层模型。"
     "团队偏好数据驱动的决策方式，减少主观拍板。事实：今年用户流失率达22%。"
     "关键实体：增长团队由周九负责，主攻留存指标。"),
    ("供应商合作洽谈会",
     "决议：选定云服务商为阿里云，签约三年。行动项：采购需在月底前完成合同谈判。"
     "公司偏好选择国内供应商以符合数据本地化要求。事实：阿里云报价比AWS低18%。"
     "关键人物：采购经理吴十负责供应商对接。"),
    ("数据中台建设启动会",
     "决议：数据中台一期投入300万元，半年内交付。行动项：数据组需先完成元数据盘点。"
     "团队倾向选用开源技术栈，控制授权成本。事实：当前公司有12个孤立业务数据库。"
     "负责人：数据总监郑一统筹中台建设。"),
    ("团队季度绩效会",
     "决议：本季度绩效A档比例控制在20%。行动项：各组长需在下周三前提交组员评分。"
     "管理层偏好OKR与KPI结合的考核方式。事实：上季度团队平均产出提升12%。"
     "关键实体：绩效委员会由HR与各组长组成。"),
]


async def main(email: str):
    async with AsyncSessionLocal() as db:
        u = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if not u:
            raise SystemExit(f"用户不存在: {email}")
        for title, summary in CORPUS:
            db.add(Meeting(owner_id=u.id, title=title, summary=summary))
        await db.commit()
        print(f"已注入 {len(CORPUS)} 场富内容会议到 owner={email}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--owner", default="a@b.com")
    asyncio.run(main(p.parse_args().owner))