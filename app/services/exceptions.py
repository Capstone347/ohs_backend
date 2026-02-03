from app.core.exceptions import OHSRemoteException


class ServiceException(OHSRemoteException):
    pass


class OrderServiceException(ServiceException):
    pass


class OrderNotCreatedException(OrderServiceException):
    pass


class OrderStatusUpdateException(OrderServiceException):
    pass


class InvalidOrderStateException(OrderServiceException):
    pass


class ValidationServiceException(ServiceException):
    pass


class InvalidNAICSCodeException(ValidationServiceException):
    pass


class InvalidEmailException(ValidationServiceException):
    pass


class InvalidProvinceException(ValidationServiceException):
    pass


class InvalidFileException(ValidationServiceException):
    pass


class FileSizeLimitExceededException(ValidationServiceException):
    pass


class UnsupportedFileTypeException(ValidationServiceException):
    pass


class FileStorageServiceException(ServiceException):
    pass


class DirectoryCreationException(FileStorageServiceException):
    pass


class FileSaveException(FileStorageServiceException):
    pass


class FileNotFoundServiceException(FileStorageServiceException):
    pass


class DocumentGenerationServiceException(ServiceException):
    pass
