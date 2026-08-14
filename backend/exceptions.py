from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class APIError(HTTPException):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(status_code=status_code, detail={"code": code, "message": message})
        self.code = code
        self.message = message


def not_found(message: str = "资源不存在") -> APIError:
    return APIError(404, "NOT_FOUND", message)


def bad_request(message: str) -> APIError:
    return APIError(400, "BAD_REQUEST", message)


def conflict(message: str) -> APIError:
    return APIError(409, "CONFLICT", message)


def unauthorized(message: str = "未授权") -> APIError:
    return APIError(401, "UNAUTHORIZED", message)


async def api_error_handler(_: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message},
    )
