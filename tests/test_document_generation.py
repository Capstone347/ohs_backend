import pytest
from pathlib import Path
from datetime import datetime, timedelta
from PIL import Image
import io

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.company import Company
from app.models.plan import Plan, PlanSlug, PlanName
from app.models.order import Order
from app.models.company_logo import CompanyLogo
from app.repositories.order_repository import OrderRepository
from app.repositories.document_repository import DocumentRepository
from app.services.file_storage_service import FileStorageService
from app.services.document_generation_service import DocumentGenerationService
from app.services.preview_service import PreviewService


@pytest.fixture
def test_data_dir(tmp_path):
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def file_storage_service(test_data_dir):
    return FileStorageService(base_data_dir=test_data_dir)


@pytest.fixture
def test_logo(file_storage_service):
    img = Image.new('RGB', (300, 200), color='blue')
    
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_bytes = img_byte_arr.getvalue()
    
    logo_path = file_storage_service.save_logo(img_bytes, 999, "test_logo.png")
    
    return logo_path


@pytest.fixture
def sample_user(db_session: Session):
    user = User(
        email="test@example.com",
        password_hash="test_hash",
        full_name="John Doe",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_company(db_session: Session):
    company = Company(
        name="Test Safety Corp",
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


@pytest.fixture
def basic_plan(db_session: Session):
    plan = Plan(
        slug=PlanSlug.BASIC,
        name=PlanName.BASIC,
        description="Basic OHS Manual",
        base_price=299.00,
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    return plan


@pytest.fixture
def comprehensive_plan(db_session: Session):
    plan = Plan(
        slug=PlanSlug.COMPREHENSIVE,
        name=PlanName.COMPREHENSIVE,
        description="Comprehensive OHS Manual",
        base_price=599.00,
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    return plan


@pytest.fixture
def sample_order_with_logo(
    db_session: Session,
    sample_user,
    sample_company,
    basic_plan,
    test_logo,
):
    order = Order(
        user_id=sample_user.id,
        company_id=sample_company.id,
        plan_id=basic_plan.id,
        jurisdiction="BC",
        total_amount=299.00,
        created_at=datetime.utcnow(),
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    
    company_logo = CompanyLogo(
        order_id=order.id,
        file_path=str(test_logo),
        uploaded_at=datetime.utcnow(),
    )
    db_session.add(company_logo)
    db_session.commit()
    
    return order


@pytest.fixture
def sample_order_no_logo(
    db_session: Session,
    sample_user,
    sample_company,
    comprehensive_plan,
):
    order = Order(
        user_id=sample_user.id,
        company_id=sample_company.id,
        plan_id=comprehensive_plan.id,
        jurisdiction="ON",
        total_amount=599.00,
        created_at=datetime.utcnow(),
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    return order


@pytest.fixture
def document_generation_service(
    db_session: Session,
    file_storage_service,
):
    order_repo = OrderRepository(db_session)
    document_repo = DocumentRepository(db_session)
    
    return DocumentGenerationService(
        order_repository=order_repo,
        document_repository=document_repo,
        file_storage_service=file_storage_service,
    )


@pytest.fixture
def preview_service(
    db_session: Session,
    file_storage_service,
):
    document_repo = DocumentRepository(db_session)
    
    return PreviewService(
        document_repository=document_repo,
        file_storage_service=file_storage_service,
    )


class TestDocumentGeneration:
    def test_generate_basic_manual_with_logo(
        self,
        document_generation_service,
        sample_order_with_logo,
    ):
        result = document_generation_service.generate_manual(sample_order_with_logo.id)
        
        assert result is not None
        assert result.order_id == sample_order_with_logo.id
        assert result.file_path is not None
        assert result.file_format.value == "docx"
        assert result.access_token is not None
        assert len(result.access_token) == 64
        
        file_path = Path(result.file_path)
        assert file_path.exists()
        assert file_path.suffix == ".docx"
        assert file_path.stat().st_size > 0
        
        print(f"\n✓ Generated document: {file_path}")
        print(f"  File size: {file_path.stat().st_size} bytes")
        print(f"  Access token: {result.access_token[:16]}...")
    
    def test_generate_comprehensive_manual_without_logo(
        self,
        document_generation_service,
        sample_order_no_logo,
    ):
        result = document_generation_service.generate_manual(sample_order_no_logo.id)
        
        assert result is not None
        assert result.order_id == sample_order_no_logo.id
        assert result.file_path is not None
        
        file_path = Path(result.file_path)
        assert file_path.exists()
        assert file_path.suffix == ".docx"
        assert file_path.stat().st_size > 0
        
        print(f"\n✓ Generated comprehensive document: {file_path}")
        print(f"  File size: {file_path.stat().st_size} bytes")
    
    def test_generate_manual_with_order_id_zero_raises_error(
        self,
        document_generation_service,
    ):
        with pytest.raises(ValueError, match="order_id is required"):
            document_generation_service.generate_manual(0)
    
    def test_generate_manual_with_nonexistent_order_raises_error(
        self,
        document_generation_service,
    ):
        with pytest.raises(Exception, match="Order 99999 not found"):
            document_generation_service.generate_manual(99999)
    
    def test_document_record_created_in_database(
        self,
        document_generation_service,
        sample_order_with_logo,
        db_session,
    ):
        result = document_generation_service.generate_manual(sample_order_with_logo.id)
        
        db_session.refresh(result)
        
        assert result.document_id is not None
        assert result.order_id == sample_order_with_logo.id
        assert result.generated_at is not None
        assert result.token_expires_at > datetime.utcnow()
        assert result.downloaded_count == 0
        assert result.last_downloaded_at is None
    
    def test_generated_document_contains_company_data(
        self,
        document_generation_service,
        sample_order_with_logo,
    ):
        from docx import Document
        
        result = document_generation_service.generate_manual(sample_order_with_logo.id)
        
        doc = Document(result.file_path)
        
        full_text = "\n".join([para.text for para in doc.paragraphs])
        
        assert "Test Safety Corp" in full_text
        assert str(sample_order_with_logo.id) in full_text
        assert str(datetime.now().year) in full_text


class TestPreviewGeneration:
    def test_generate_preview_from_document(
        self,
        document_generation_service,
        preview_service,
        sample_order_with_logo,
    ):
        document = document_generation_service.generate_manual(sample_order_with_logo.id)
        
        preview_path = preview_service.generate_preview(document.document_id)
        
        assert preview_path.exists()
        assert preview_path.suffix == ".pdf"
        assert preview_path.stat().st_size > 0
        assert "preview" in str(preview_path)
        
        print(f"\n✓ Generated preview: {preview_path}")
        print(f"  File size: {preview_path.stat().st_size} bytes")
        print(f"  Format: PDF (secure preview)")
    
    def test_preview_generation_with_invalid_document_id_raises_error(
        self,
        preview_service,
    ):
        with pytest.raises(Exception, match="Document 99999 not found"):
            preview_service.generate_preview(99999)
    
    def test_preview_is_pdf_not_docx(
        self,
        document_generation_service,
        preview_service,
        sample_order_with_logo,
    ):
        document = document_generation_service.generate_manual(sample_order_with_logo.id)
        preview_path = preview_service.generate_preview(document.document_id)
        
        assert preview_path.suffix == ".pdf"
        assert preview_path.exists()
        
        from pypdf import PdfReader
        reader = PdfReader(str(preview_path))
        assert len(reader.pages) > 0


class TestCompleteWorkflow:
    def test_full_document_generation_workflow(
        self,
        document_generation_service,
        preview_service,
        sample_order_with_logo,
        test_data_dir,
    ):
        print(f"\n{'='*60}")
        print("FULL DOCUMENT GENERATION WORKFLOW TEST")
        print(f"{'='*60}")
        
        print(f"\n1. Order Details:")
        print(f"   Order ID: {sample_order_with_logo.id}")
        print(f"   Company: {sample_order_with_logo.company.name}")
        print(f"   Plan: {sample_order_with_logo.plan.name.value}")
        print(f"   Jurisdiction: {sample_order_with_logo.jurisdiction}")
        
        print(f"\n2. Generating document...")
        document = document_generation_service.generate_manual(sample_order_with_logo.id)
        
        print(f"   ✓ Document generated successfully!")
        print(f"   Document ID: {document.document_id}")
        print(f"   File Path: {document.file_path}")
        print(f"   File Size: {Path(document.file_path).stat().st_size} bytes")
        print(f"   Access Token: {document.access_token[:16]}...")
        print(f"   Expires: {document.token_expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        assert Path(document.file_path).exists()
        
        print(f"\n3. Generating preview...")
        preview_path = preview_service.generate_preview(document.document_id)
        
        print(f"   ✓ Preview generated successfully!")
        print(f"   Preview Path: {preview_path}")
        print(f"   Preview Size: {preview_path.stat().st_size} bytes")
        print(f"   Preview Format: PDF (Secure - Limited Content)")
        
        assert preview_path.exists()
        assert preview_path.suffix == ".pdf"
        
        print(f"\n4. Verifying file structure...")
        generated_dir = test_data_dir / "documents" / "generated"
        preview_dir = test_data_dir / "documents" / "previews"
        
        print(f"   Generated documents directory: {generated_dir}")
        print(f"   Files: {list(generated_dir.glob('*.docx'))}")
        print(f"   Preview documents directory: {preview_dir}")
        print(f"   Files: {list(preview_dir.glob('*.pdf'))}")
        
        assert generated_dir.exists()
        assert preview_dir.exists()
        assert len(list(generated_dir.glob('*.docx'))) > 0
        assert len(list(preview_dir.glob('*.pdf'))) > 0
        
        print(f"\n{'='*60}")
        print("✓ WORKFLOW COMPLETED SUCCESSFULLY!")
        print(f"{'='*60}\n")
    
    def test_generate_both_plan_types(
        self,
        db_session,
        sample_user,
        sample_company,
        basic_plan,
        comprehensive_plan,
        file_storage_service,
        test_logo,
    ):
        print(f"\n{'='*60}")
        print("TESTING BOTH PLAN TYPES")
        print(f"{'='*60}")
        
        order_repo = OrderRepository(db_session)
        document_repo = DocumentRepository(db_session)
        service = DocumentGenerationService(
            order_repository=order_repo,
            document_repository=document_repo,
            file_storage_service=file_storage_service,
        )
        
        basic_order = Order(
            user_id=sample_user.id,
            company_id=sample_company.id,
            plan_id=basic_plan.id,
            jurisdiction="BC",
            total_amount=299.00,
        )
        db_session.add(basic_order)
        db_session.commit()
        db_session.refresh(basic_order)
        
        logo = CompanyLogo(
            order_id=basic_order.id,
            file_path=str(test_logo),
            uploaded_at=datetime.utcnow(),
        )
        db_session.add(logo)
        db_session.commit()
        
        print(f"\n1. Generating BASIC manual...")
        basic_doc = service.generate_manual(basic_order.id)
        print(f"   ✓ Basic manual: {basic_doc.file_path}")
        print(f"   Size: {Path(basic_doc.file_path).stat().st_size} bytes")
        
        comprehensive_order = Order(
            user_id=sample_user.id,
            company_id=sample_company.id,
            plan_id=comprehensive_plan.id,
            jurisdiction="ON",
            total_amount=599.00,
        )
        db_session.add(comprehensive_order)
        db_session.commit()
        db_session.refresh(comprehensive_order)
        
        logo2 = CompanyLogo(
            order_id=comprehensive_order.id,
            file_path=str(test_logo),
            uploaded_at=datetime.utcnow(),
        )
        db_session.add(logo2)
        db_session.commit()
        
        print(f"\n2. Generating COMPREHENSIVE manual...")
        comprehensive_doc = service.generate_manual(comprehensive_order.id)
        print(f"   ✓ Comprehensive manual: {comprehensive_doc.file_path}")
        print(f"   Size: {Path(comprehensive_doc.file_path).stat().st_size} bytes")
        
        assert Path(basic_doc.file_path).exists()
        assert Path(comprehensive_doc.file_path).exists()
        
        basic_size = Path(basic_doc.file_path).stat().st_size
        comprehensive_size = Path(comprehensive_doc.file_path).stat().st_size
        
        assert comprehensive_size > basic_size, "Comprehensive manual should be larger"
        
        print(f"\n✓ Size comparison: Comprehensive ({comprehensive_size}) > Basic ({basic_size})")
        print(f"\n{'='*60}")
        print("✓ BOTH PLAN TYPES GENERATED SUCCESSFULLY!")
        print(f"{'='*60}\n")
