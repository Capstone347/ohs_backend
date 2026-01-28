from app.config import settings


class OHSRemoteException(Exception):
    pass


class ValidationError(OHSRemoteException):
    pass


class OrderNotFoundError(OHSRemoteException):
    pass


class DocumentGenerationError(OHSRemoteException):
    pass


class PaymentProcessingError(OHSRemoteException):
    pass


class EmailDeliveryError(OHSRemoteException):
    pass


class FileStorageError(OHSRemoteException):
    pass


class ConfigurationError(OHSRemoteException):
    pass
