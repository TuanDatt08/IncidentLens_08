from __future__ import annotations

from fastapi import UploadFile

from backend.config import Settings, get_settings
from backend.models.incident import IncidentPackage, IngestionStatus, ProcessingStatus
from backend.services.errors import IncidentIngestionError
from backend.services.logs import LogService
from backend.services.package_repository import IncidentPackageRepository
from backend.services.storage import LocalStorage
from backend.services.video import VideoService


class IncidentIngestionService:
    """Orchestrates upload validation and metadata preparation."""

    def __init__(
        self,
        storage: LocalStorage,
        repository: IncidentPackageRepository,
        video_service: VideoService,
        log_service: LogService,
        *,
        max_video_size_bytes: int,
        max_log_size_bytes: int,
    ) -> None:
        self.storage = storage
        self.repository = repository
        self.video_service = video_service
        self.log_service = log_service
        self.max_video_size_bytes = max_video_size_bytes
        self.max_log_size_bytes = max_log_size_bytes

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> IncidentIngestionService:
        settings = settings or get_settings()
        storage = LocalStorage(settings.incident_storage_dir)
        return cls(
            storage=storage,
            repository=IncidentPackageRepository(settings.incident_storage_dir),
            video_service=VideoService(settings.ffprobe_bin, settings.ffmpeg_bin),
            log_service=LogService(),
            max_video_size_bytes=settings.max_video_size_mb * 1024 * 1024,
            max_log_size_bytes=settings.max_log_size_mb * 1024 * 1024,
        )

    def ingest(self, video: UploadFile, log: UploadFile | None = None) -> IncidentPackage:
        package_id = self.repository.new_package_id()
        package = IncidentPackage(
            package_id=package_id,
            status=IngestionStatus.VALIDATING,
            video_path="",
            processing_status=ProcessingStatus.UPLOADED,
            video_filename=video.filename,
        )

        try:
            self.repository.save(package)
            self.video_service.validate_upload(video.filename, video.content_type)
            if log is not None:
                self.log_service.validate_upload(log.filename, log.content_type)

            video_file = self.storage.save_stream(
                video.file,
                package_id=package_id,
                relative_name="source/video.mp4",
                max_bytes=self.max_video_size_bytes,
            )
            package.video_path = video_file.relative_path
            self.repository.save(package)

            video_path = video_file.path
            probe = self.video_service.probe(video_path)
            package.video_metadata = probe.as_dict()
            self.repository.save(package)

            if log is not None:
                log_file = self.storage.save_stream(
                    log.file,
                    package_id=package_id,
                    relative_name="source/telemetry.csv",
                    max_bytes=self.max_log_size_bytes,
                )
                package.log_path = log_file.relative_path
                normalized = self.log_service.normalize(log_file.path)
                normalized_file = self.storage.write_bytes(
                    package_id,
                    "processed/telemetry_normalized.csv",
                    normalized.content,
                )
                package.normalized_log_path = normalized_file.relative_path
                package.log_metadata = normalized.metadata()

            package.status = IngestionStatus.READY
            package.processing_status = ProcessingStatus.READY
            self.repository.save(package)
            return package
        except IncidentIngestionError as exc:
            self._mark_failed(package, exc.code, exc.message)
            raise exc.with_package_id(package_id) from exc
        except OSError as exc:
            message = "Incident data could not be persisted to storage."
            self._mark_failed(package, "storage_error", message)
            raise IncidentIngestionError(
                "storage_error",
                message,
                status_code=500,
                package_id=package_id,
            ) from exc
        except Exception as exc:
            message = "Incident ingestion failed unexpectedly."
            self._mark_failed(package, "ingestion_failed", message)
            raise IncidentIngestionError(
                "ingestion_failed",
                message,
                status_code=500,
                package_id=package_id,
            ) from exc

    def _mark_failed(self, package: IncidentPackage, code: str, message: str) -> None:
        package.status = IngestionStatus.FAILED
        package.processing_status = ProcessingStatus.FAILED
        package.error_code = code
        package.error_message = message
        try:
            self.repository.save(package)
        except Exception:
            # Preserve the original structured ingestion/storage error when
            # the failure manifest itself cannot be persisted.
            pass


_service: IncidentIngestionService | None = None


def get_ingestion_service() -> IncidentIngestionService:
    global _service
    if _service is None:
        _service = IncidentIngestionService.from_settings()
    return _service
