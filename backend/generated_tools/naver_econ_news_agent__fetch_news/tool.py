def fetch_news(topic='네이버 경제뉴스', **kwargs):
    try:
        from universal_parser import fetch_news as _fetch
    except Exception as e:
        return {"status": "error", "content": "",
                "message": "universal_parser import 실패: " + str(e)}
    t = kwargs.get("topic") or topic or ""
    return _fetch(topic=t, limit=10)
