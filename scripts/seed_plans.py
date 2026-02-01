import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

def seed_plans():
    try:
        from sqlalchemy.orm import Session
        from app.database import SessionLocal
        from app.models.plan import Plan, PlanSlug, PlanName
    except ImportError as e:
        print(f"Import error: {e}")
        return
    
    db = SessionLocal()
    try:
        plans = [
            Plan(
                slug=PlanSlug.BASIC,
                name=PlanName.BASIC,
                description="Basic OHS manual with essential workplace safety procedures",
                base_price=99.99
            ),
            Plan(
                slug=PlanSlug.COMPREHENSIVE,
                name=PlanName.COMPREHENSIVE,
                description="Comprehensive OHS manual with advanced safety protocols, industry-specific content, and legal compliance documentation",
                base_price=199.99
            )
        ]
        
        existing_plans = db.query(Plan).all()
        if len(existing_plans) >= 2:
            print(f"Plans already exist ({len(existing_plans)} found). Skipping.")
            return
        
        for plan in plans:
            db.add(plan)
        
        db.commit()
        
        print("Successfully seeded plans:")
        for plan in db.query(Plan).all():
            print(f"{plan.name} (${plan.base_price}): {plan.description}")
            
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_plans()