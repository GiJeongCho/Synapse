"""하위 호환용 재노출 모듈.

설정의 정식 위치는 ``app/core/config.py`` 다(§2.1, §21). 기존 ``from app.config import settings``
임포트를 깨지 않기 위해 여기서 재노출한다. 신규 코드는 ``app.core.config`` 를 직접 임포트한다.
"""

from app.core.config import Settings, settings

__all__ = ["Settings", "settings"]
