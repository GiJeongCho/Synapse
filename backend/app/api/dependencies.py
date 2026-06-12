"""라우터 공통 의존성(§15.1).

실행 라우터는 S2S 인증(JWT/헤더 검증)을 의존성으로 강제한다.
현재는 스캐폴드 스텁이며, 운영 전환 시 실제 JWT 검증을 채운다.
"""

from __future__ import annotations

from fastapi import Header
from typing import Optional


async def verify_jwt_and_headers(
    authorization: Optional[str] = Header(default=None),
    x_request_id: Optional[str] = Header(default=None),
) -> dict:
    """S2S 인증 검증(스텁).

    TODO: JWT 서명/만료 검증 및 필수 헤더 검증을 구현한다(§15.1).
    """
    return {"request_id": x_request_id, "authorization": authorization}
