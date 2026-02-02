from pathlib import Path
from datetime import datetime
import shutil

from app.config import settings
from app.services.exceptions import (
    FileStorageServiceException,
    DirectoryCreationException,
    FileSaveException,
    FileNotFoundServiceException,
)


class FileStorageService:
    def __init__(self, base_data_dir: Path | None = None):
        self.base_data_dir = base_data_dir or settings.data_dir
        self.uploads_dir = self.base_data_dir / "uploads"
        self.logos_dir = self.uploads_dir / "logos"
        self.documents_dir = self.base_data_dir / "documents"
        self.generated_documents_dir = self.documents_dir / "generated"
        self.preview_documents_dir = self.documents_dir / "previews"
        
        self._ensure_directories_exist()

    def _ensure_directories_exist(self) -> None:
        directories = [
            self.uploads_dir,
            self.logos_dir,
            self.documents_dir,
            self.generated_documents_dir,
            self.preview_documents_dir,
        ]
        
        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise DirectoryCreationException(f"Failed to create directory {directory}: {str(e)}")

    def save_logo(self, file_content: bytes, order_id: int, filename: str) -> Path:
        if not file_content:
            raise FileSaveException("File content cannot be empty")
        
        if not order_id:
            raise FileSaveException("order_id is required")
        
        if not filename:
            raise FileSaveException("filename is required")
        
        extension = Path(filename).suffix.lower()
        if not extension:
            raise FileSaveException("File must have an extension")
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"order_{order_id}_{timestamp}{extension}"
        logo_path = self.logos_dir / safe_filename
        
        try:
            logo_path.write_bytes(file_content)
            return logo_path
        except Exception as e:
            raise FileSaveException(f"Failed to save logo file: {str(e)}")

    def get_logo_path(self, order_id: int, filename: str) -> Path:
        if not order_id:
            raise ValueError("order_id is required")
        
        if not filename:
            raise ValueError("filename is required")
        
        logo_path = self.logos_dir / filename
        
        if not logo_path.exists():
            raise FileNotFoundServiceException(f"Logo file not found: {filename}")
        
        return logo_path

    def save_generated_document(self, file_content: bytes, order_id: int, extension: str = ".docx") -> Path:
        if not file_content:
            raise FileSaveException("File content cannot be empty")
        
        if not order_id:
            raise FileSaveException("order_id is required")
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"manual_order_{order_id}_{timestamp}{extension}"
        document_path = self.generated_documents_dir / filename
        
        try:
            document_path.write_bytes(file_content)
            return document_path
        except Exception as e:
            raise FileSaveException(f"Failed to save generated document: {str(e)}")

    def save_preview_document(self, file_content: bytes, order_id: int, extension: str = ".pdf") -> Path:
        if not file_content:
            raise FileSaveException("File content cannot be empty")
        
        if not order_id:
            raise FileSaveException("order_id is required")
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"preview_order_{order_id}_{timestamp}{extension}"
        preview_path = self.preview_documents_dir / filename
        
        try:
            preview_path.write_bytes(file_content)
            return preview_path
        except Exception as e:
            raise FileSaveException(f"Failed to save preview document: {str(e)}")

    def get_document_path(self, filename: str, document_type: str = "generated") -> Path:
        if not filename:
            raise ValueError("filename is required")
        
        if document_type == "generated":
            document_path = self.generated_documents_dir / filename
        elif document_type == "preview":
            document_path = self.preview_documents_dir / filename
        else:
            raise ValueError(f"Invalid document_type: {document_type}. Must be 'generated' or 'preview'")
        
        if not document_path.exists():
            raise FileNotFoundServiceException(f"Document file not found: {filename}")
        
        return document_path

    def delete_logo(self, logo_path: Path) -> None:
        if not logo_path:
            raise ValueError("logo_path is required")
        
        if not logo_path.exists():
            raise FileNotFoundServiceException(f"Logo file not found: {logo_path}")
        
        try:
            logo_path.unlink()
        except Exception as e:
            raise FileSaveException(f"Failed to delete logo file: {str(e)}")

    def delete_document(self, document_path: Path) -> None:
        if not document_path:
            raise ValueError("document_path is required")
        
        if not document_path.exists():
            raise FileNotFoundServiceException(f"Document file not found: {document_path}")
        
        try:
            document_path.unlink()
        except Exception as e:
            raise FileSaveException(f"Failed to delete document file: {str(e)}")

    def get_logos_for_order(self, order_id: int) -> list[Path]:
        if not order_id:
            raise ValueError("order_id is required")
        
        pattern = f"order_{order_id}_*"
        return sorted(self.logos_dir.glob(pattern))

    def cleanup_old_previews(self, days_old: int = 7) -> int:
        if days_old < 1:
            raise ValueError("days_old must be at least 1")
        
        cutoff_time = datetime.utcnow().timestamp() - (days_old * 24 * 3600)
        deleted_count = 0
        
        for preview_file in self.preview_documents_dir.glob("preview_order_*"):
            if preview_file.stat().st_mtime < cutoff_time:
                try:
                    preview_file.unlink()
                    deleted_count += 1
                except Exception:
                    continue
        
        return deleted_count

    def get_storage_info(self) -> dict[str, int]:
        def get_dir_size(directory: Path) -> int:
            total_size = 0
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return total_size
        
        return {
            "logos_size_bytes": get_dir_size(self.logos_dir),
            "generated_docs_size_bytes": get_dir_size(self.generated_documents_dir),
            "preview_docs_size_bytes": get_dir_size(self.preview_documents_dir),
            "total_size_bytes": get_dir_size(self.base_data_dir),
        }
