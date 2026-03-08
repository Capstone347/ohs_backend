from sqlalchemy.orm import Session, joinedload

from app.models.industry_naics_code import IndustryNAICSCode
from app.models.industry_profile import IndustryProfile


class IndustryProfileRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_company_id_with_codes(self, company_id: int) -> IndustryProfile | None:
        if not company_id:
            raise ValueError("company_id is required")

        return (
            self.db.query(IndustryProfile)
            .options(joinedload(IndustryProfile.naics_codes))
            .filter(IndustryProfile.company_id == company_id)
            .first()
        )

    def upsert_profile_and_codes(
        self,
        company_id: int,
        province: str,
        naics_codes: list[str],
        business_description: str | None = None,
    ) -> IndustryProfile:
        if not company_id:
            raise ValueError("company_id is required")

        if not province:
            raise ValueError("province is required")

        if not naics_codes:
            raise ValueError("naics_codes is required")

        industry_profile = self.get_by_company_id_with_codes(company_id)
        if not industry_profile:
            industry_profile = IndustryProfile(company_id=company_id)
            self.db.add(industry_profile)
            self.db.flush()

        industry_profile.province = province
        industry_profile.business_description = business_description

        (
            self.db.query(IndustryNAICSCode)
            .filter(IndustryNAICSCode.industry_profile_id == industry_profile.id)
            .delete(synchronize_session=False)
        )

        for position, code in enumerate(naics_codes, start=1):
            self.db.add(
                IndustryNAICSCode(
                    industry_profile_id=industry_profile.id,
                    code=code,
                    position=position,
                )
            )

        self.db.commit()
        self.db.refresh(industry_profile)
        refreshed_profile = self.get_by_company_id_with_codes(company_id)
        if not refreshed_profile:
            raise ValueError("Failed to load industry profile after update")
        return refreshed_profile