from pydantic import BaseModel, Field
from typing import Any, Optional
import uuid


class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: dict[str, Any]
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class JSONRPCError(BaseModel):
    code: int
    message: str
    data: Optional[Any] = None


class JSONRPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[JSONRPCError] = None
    id: str


def make_success_response(result: Any, request_id: str) -> JSONRPCResponse:
    return JSONRPCResponse(result=result, id=request_id)


def make_error_response(code: int, message: str, request_id: str) -> JSONRPCResponse:
    return JSONRPCResponse(error=JSONRPCError(code=code, message=message), id=request_id)
