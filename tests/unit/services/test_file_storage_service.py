import pytest
from pathlib import Path
import tempfile
import shutil
from datetime import datetime, timezone

from app.services.file_storage_service import FileStorageService
from app.services.exceptions import (
    DirectoryCreationException,
    FileSaveException,
    FileNotFoundServiceException,
)


@pytest.fixture
def temp_dir():
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def file_storage_service(temp_dir):
    return FileStorageService(base_data_dir=temp_dir)


class TestFileStorageService:
    def test_initialization_creates_directories(self, file_storage_service):
        assert file_storage_service.uploads_dir.exists()
        assert file_storage_service.logos_dir.exists()
        assert file_storage_service.documents_dir.exists()
        assert file_storage_service.generated_documents_dir.exists()
        assert file_storage_service.preview_documents_dir.exists()

    def test_save_logo(self, file_storage_service):
        file_content = b"fake logo content"
        order_id = 123
        filename = "test_logo.png"
        
        logo_path = file_storage_service.save_logo(file_content, order_id, filename)
        
        assert logo_path.exists()
        assert logo_path.parent == file_storage_service.logos_dir
        assert logo_path.read_bytes() == file_content
        assert f"order_{order_id}" in logo_path.name

    def test_save_logo_empty_content_fails(self, file_storage_service):
        with pytest.raises(FileSaveException, match="cannot be empty"):
            file_storage_service.save_logo(b"", 123, "logo.png")

    def test_save_logo_no_order_id_fails(self, file_storage_service):
        with pytest.raises(FileSaveException, match="order_id is required"):
            file_storage_service.save_logo(b"content", None, "logo.png")

    def test_save_logo_no_filename_fails(self, file_storage_service):
        with pytest.raises(FileSaveException, match="filename is required"):
            file_storage_service.save_logo(b"content", 123, "")

    def test_save_logo_no_extension_fails(self, file_storage_service):
        with pytest.raises(FileSaveException, match="must have an extension"):
            file_storage_service.save_logo(b"content", 123, "logo")

    def test_get_logo_path(self, file_storage_service):
        file_content = b"logo content"
        order_id = 456
        filename = "test.png"
        
        saved_path = file_storage_service.save_logo(file_content, order_id, filename)
        saved_filename = saved_path.name
        
        retrieved_path = file_storage_service.get_logo_path(order_id, saved_filename)
        
        assert retrieved_path == saved_path
        assert retrieved_path.exists()

    def test_get_logo_path_not_found_fails(self, file_storage_service):
        with pytest.raises(FileNotFoundServiceException, match="not found"):
            file_storage_service.get_logo_path(123, "nonexistent.png")

    def test_save_generated_document(self, file_storage_service):
        file_content = b"document content"
        order_id = 789
        
        doc_path = file_storage_service.save_generated_document(file_content, order_id)
        
        assert doc_path.exists()
        assert doc_path.parent == file_storage_service.generated_documents_dir
        assert doc_path.read_bytes() == file_content
        assert f"manual_order_{order_id}" in doc_path.name
        assert doc_path.suffix == ".docx"

    def test_save_generated_document_custom_extension(self, file_storage_service):
        file_content = b"pdf content"
        order_id = 111
        
        doc_path = file_storage_service.save_generated_document(file_content, order_id, extension=".pdf")
        
        assert doc_path.exists()
        assert doc_path.suffix == ".pdf"

    def test_save_generated_document_empty_content_fails(self, file_storage_service):
        with pytest.raises(FileSaveException, match="cannot be empty"):
            file_storage_service.save_generated_document(b"", 123)

    def test_save_preview_document(self, file_storage_service):
        file_content = b"preview content"
        order_id = 222
        
        preview_path = file_storage_service.save_preview_document(file_content, order_id)
        
        assert preview_path.exists()
        assert preview_path.parent == file_storage_service.preview_documents_dir
        assert preview_path.read_bytes() == file_content
        assert f"preview_order_{order_id}" in preview_path.name
        assert preview_path.suffix == ".pdf"

    def test_save_preview_document_custom_extension(self, file_storage_service):
        file_content = b"preview content"
        order_id = 333
        
        preview_path = file_storage_service.save_preview_document(file_content, order_id, extension=".docx")
        
        assert preview_path.exists()
        assert preview_path.suffix == ".docx"

    def test_get_document_path_generated(self, file_storage_service):
        file_content = b"document content"
        order_id = 444
        
        saved_path = file_storage_service.save_generated_document(file_content, order_id)
        saved_filename = saved_path.name
        
        retrieved_path = file_storage_service.get_document_path(saved_filename, "generated")
        
        assert retrieved_path == saved_path
        assert retrieved_path.exists()

    def test_get_document_path_preview(self, file_storage_service):
        file_content = b"preview content"
        order_id = 555
        
        saved_path = file_storage_service.save_preview_document(file_content, order_id)
        saved_filename = saved_path.name
        
        retrieved_path = file_storage_service.get_document_path(saved_filename, "preview")
        
        assert retrieved_path == saved_path
        assert retrieved_path.exists()

    def test_get_document_path_invalid_type_fails(self, file_storage_service):
        with pytest.raises(ValueError, match="Invalid document_type"):
            file_storage_service.get_document_path("test.pdf", "invalid")

    def test_get_document_path_not_found_fails(self, file_storage_service):
        with pytest.raises(FileNotFoundServiceException, match="not found"):
            file_storage_service.get_document_path("nonexistent.pdf", "generated")

    def test_delete_logo(self, file_storage_service):
        file_content = b"logo to delete"
        order_id = 666
        
        logo_path = file_storage_service.save_logo(file_content, order_id, "delete.png")
        
        assert logo_path.exists()
        
        file_storage_service.delete_logo(logo_path)
        
        assert not logo_path.exists()

    def test_delete_logo_not_found_fails(self, file_storage_service):
        nonexistent_path = file_storage_service.logos_dir / "nonexistent.png"
        
        with pytest.raises(FileNotFoundServiceException, match="not found"):
            file_storage_service.delete_logo(nonexistent_path)

    def test_delete_document(self, file_storage_service):
        file_content = b"document to delete"
        order_id = 777
        
        doc_path = file_storage_service.save_generated_document(file_content, order_id)
        
        assert doc_path.exists()
        
        file_storage_service.delete_document(doc_path)
        
        assert not doc_path.exists()

    def test_get_logos_for_order(self, file_storage_service):
        import time
        order_id = 888
        
        logo1 = file_storage_service.save_logo(b"logo1", order_id, "logo1.png")
        time.sleep(1.1)
        logo2 = file_storage_service.save_logo(b"logo2", order_id, "logo2.png")
        other_logo = file_storage_service.save_logo(b"other", 999, "other.png")
        
        logos = file_storage_service.get_logos_for_order(order_id)
        
        assert len(logos) >= 2
        logo_names = [logo.name for logo in logos]
        assert any(logo1.name == name for name in logo_names)
        assert any(logo2.name == name for name in logo_names)
        assert other_logo not in logos

    def test_get_logos_for_order_no_results(self, file_storage_service):
        logos = file_storage_service.get_logos_for_order(999)
        
        assert len(logos) == 0

    def test_cleanup_old_previews(self, file_storage_service):
        
        old_preview = file_storage_service.save_preview_document(b"old preview", 101)
        
        old_time = (datetime.now(timezone.utc).timestamp() - (10 * 24 * 3600))
        old_preview.touch()
        import os
        os.utime(old_preview, (old_time, old_time))
        
        new_preview = file_storage_service.save_preview_document(b"new preview", 102)
        
        deleted_count = file_storage_service.cleanup_old_previews(days_old=7)
        
        assert deleted_count == 1
        assert not old_preview.exists()
        assert new_preview.exists()

    def test_cleanup_old_previews_invalid_days_fails(self, file_storage_service):
        with pytest.raises(ValueError, match="must be at least 1"):
            file_storage_service.cleanup_old_previews(days_old=0)

    def test_get_storage_info(self, file_storage_service):
        file_storage_service.save_logo(b"x" * 1000, 1, "logo.png")
        file_storage_service.save_generated_document(b"y" * 2000, 2)
        file_storage_service.save_preview_document(b"z" * 3000, 3)
        
        storage_info = file_storage_service.get_storage_info()
        
        assert "logos_size_bytes" in storage_info
        assert "generated_docs_size_bytes" in storage_info
        assert "preview_docs_size_bytes" in storage_info
        assert "total_size_bytes" in storage_info
        
        assert storage_info["logos_size_bytes"] >= 1000
        assert storage_info["generated_docs_size_bytes"] >= 2000
        assert storage_info["preview_docs_size_bytes"] >= 3000
        assert storage_info["total_size_bytes"] > 0
