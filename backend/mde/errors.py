class MdeError(Exception):
    code = "mde_error"
    http_status = 500

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class CsvError(MdeError):
    code = "bad_csv"
    http_status = 400


class TargetError(MdeError):
    code = "target_invalid"
    http_status = 422


class SplitError(MdeError):
    code = "split_invalid"
    http_status = 422


class DecisionRequired(MdeError):
    code = "decision_required"
    http_status = 422


class ConfirmationRequired(MdeError):
    code = "confirmation_required"
    http_status = 422


class Busy(MdeError):
    code = "busy"
    http_status = 409


class NotFound(MdeError):
    code = "not_found"
    http_status = 404


class TooLarge(MdeError):
    code = "too_large"
    http_status = 413


class TooManyColumns(MdeError):
    code = "too_many_columns"
    http_status = 422


class BadRequest(MdeError):
    code = "bad_request"
    http_status = 400
