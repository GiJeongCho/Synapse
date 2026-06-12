"""ResearchMind — Streamlit HITL interface.

Features:
- Document upload with automatic preprocessing
- Color-intensity chunk viewer (darker = higher quality/importance)
- Inline chunk editing / deletion → re-embedding
- RAG search with reranked results
"""

import json
import requests
import streamlit as st

API_BASE = "http://localhost:8000/api"

st.set_page_config(page_title="ResearchMind", layout="wide")


def _color_for_intensity(intensity: float) -> str:
    """Map 0–1 intensity to an rgba color (blue tones, darker = higher)."""
    alpha = max(0.08, intensity)
    r = int(30 + (1 - intensity) * 180)
    g = int(60 + (1 - intensity) * 160)
    b = int(200 - (1 - intensity) * 40)
    return f"rgba({r}, {g}, {b}, {alpha:.2f})"


def _label_badge(label: str) -> str:
    colors = {
        "core": "#e74c3c",
        "support": "#f39c12",
        "context": "#3498db",
        "noise": "#95a5a6",
    }
    bg = colors.get(label, "#95a5a6")
    return (
        f'<span style="background:{bg};color:white;padding:2px 8px;'
        f'border-radius:4px;font-size:0.8em;">{label.upper()}</span>'
    )


# ---- Sidebar ----
st.sidebar.title("ResearchMind")
page = st.sidebar.radio("메뉴", ["문서 업로드", "문서 뷰어", "RAG 검색"])

# ========================================================================
# Page: 문서 업로드
# ========================================================================
if page == "문서 업로드":
    st.header("문서 업로드")
    st.markdown("PDF / TXT / MD 파일을 업로드하면 자동으로 Adaptive Chunking + 중요도 스코어링이 실행됩니다.")

    uploaded = st.file_uploader("파일 선택", type=["pdf", "txt", "md"])
    if uploaded and st.button("전처리 실행"):
        with st.spinner("전처리 중... (문서 분류 → 청킹 → 5지표 채점 → 중요도 스코어링 → 임베딩 → 저장)"):
            files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
            try:
                resp = requests.post(f"{API_BASE}/documents/upload", files=files, timeout=300)
                if resp.status_code == 200:
                    data = resp.json()
                    st.success(f"완료! 청크 {data['num_chunks']}개 저장됨")
                    st.json(data)
                else:
                    st.error(f"오류: {resp.text}")
            except requests.ConnectionError:
                st.error("백엔드 서버에 연결할 수 없습니다. `uvicorn app.main:app --reload` 로 서버를 시작하세요.")

# ========================================================================
# Page: 문서 뷰어 (HITL)
# ========================================================================
elif page == "문서 뷰어":
    st.header("문서 뷰어 — 색 농도 기반 청크 검수")
    st.markdown("진한 색 = 높은 품질/중요도, 연한 색 = 낮은 품질 → 수정 또는 삭제 가능")

    try:
        docs = requests.get(f"{API_BASE}/documents/list", timeout=10).json()
    except requests.ConnectionError:
        st.error("백엔드 서버에 연결할 수 없습니다.")
        docs = []

    if not docs:
        st.info("저장된 문서가 없습니다. '문서 업로드' 탭에서 먼저 문서를 올려주세요.")
    else:
        source_options = [d["source"] for d in docs]
        selected_source = st.selectbox("문서 선택", source_options)

        if selected_source:
            try:
                chunks = requests.get(
                    f"{API_BASE}/documents/chunks/{selected_source}", timeout=30
                ).json()
            except requests.ConnectionError:
                chunks = []
                st.error("백엔드 서버에 연결할 수 없습니다.")

            if chunks:
                # Summary stats
                col1, col2, col3, col4 = st.columns(4)
                labels = [c.get("importance", "unknown") for c in chunks]
                col1.metric("총 청크", len(chunks))
                col2.metric("Core", labels.count("core"))
                col3.metric("Support", labels.count("support"))
                col4.metric("Context / Noise", labels.count("context") + labels.count("noise"))

                st.markdown("---")

                # Chunk display
                for i, chunk in enumerate(chunks):
                    intensity = chunk.get("color_intensity", 0.5)
                    bg = _color_for_intensity(intensity)
                    label = chunk.get("importance", "unknown")
                    score = chunk.get("importance_score", 0)
                    cid = chunk.get("id", f"chunk_{i}")
                    text = chunk.get("text", "")
                    adjusted = chunk.get("user_adjusted", False)

                    header = f"{_label_badge(label)} 중요도: {score:.2f} | 색 농도: {intensity:.2f}"
                    if adjusted:
                        header += ' <span style="color:green;">✓ 수정됨</span>'

                    st.markdown(
                        f'<div style="background:{bg};padding:12px;border-radius:8px;'
                        f'margin-bottom:8px;border-left:4px solid {bg};">'
                        f'<div style="margin-bottom:6px;">{header}</div>'
                        f'<div style="font-size:0.9em;white-space:pre-wrap;">{text[:500]}'
                        f'{"..." if len(text) > 500 else ""}</div>'
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                    with st.expander(f"편집 / 삭제 — {cid}"):
                        new_text = st.text_area(
                            "청크 텍스트 수정",
                            value=text,
                            key=f"edit_{cid}",
                            height=150,
                        )
                        c1, c2 = st.columns(2)
                        if c1.button("수정 후 재임베딩", key=f"save_{cid}"):
                            with st.spinner("재임베딩 중..."):
                                doc_type = chunk.get("doc_type", "paper")
                                payload = {
                                    "chunk_id": cid,
                                    "new_text": new_text,
                                    "source": selected_source,
                                    "doc_type": doc_type,
                                }
                                resp = requests.post(
                                    f"{API_BASE}/documents/chunks/edit",
                                    json=payload,
                                    timeout=60,
                                )
                                if resp.status_code == 200:
                                    st.success("재임베딩 완료!")
                                    st.rerun()
                                else:
                                    st.error(f"오류: {resp.text}")

                        if c2.button("삭제", key=f"del_{cid}"):
                            resp = requests.post(
                                f"{API_BASE}/documents/chunks/delete",
                                json={"chunk_ids": [cid]},
                                timeout=30,
                            )
                            if resp.status_code == 200:
                                st.success("삭제 완료!")
                                st.rerun()
                            else:
                                st.error(f"오류: {resp.text}")

# ========================================================================
# Page: RAG 검색
# ========================================================================
elif page == "RAG 검색":
    st.header("RAG 검색")
    st.markdown("자연어 질의 → Milvus 시맨틱 검색 → 리랭킹 → 결과 표시")

    query = st.text_input("검색 질의")
    col1, col2 = st.columns(2)
    top_k = col1.slider("결과 수", 1, 20, 5)
    doc_filter = col2.selectbox("문서 타입 필터", ["전체", "paper", "news", "law"])

    if st.button("검색") and query:
        with st.spinner("검색 중..."):
            payload = {
                "query": query,
                "top_k": top_k,
                "doc_type_filter": None if doc_filter == "전체" else doc_filter,
            }
            try:
                resp = requests.post(f"{API_BASE}/search/query", json=payload, timeout=60)
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("results", [])

                    if not results:
                        st.info("검색 결과가 없습니다.")
                    else:
                        st.markdown(f"**{len(results)}개 결과**")
                        for j, r in enumerate(results):
                            intensity = r.get("color_intensity", 0.5)
                            bg = _color_for_intensity(intensity)
                            label = r.get("importance", "unknown")
                            final = r.get("final_score", r.get("score", 0))
                            source = r.get("source", "")

                            st.markdown(
                                f'<div style="background:{bg};padding:12px;border-radius:8px;'
                                f'margin-bottom:8px;">'
                                f'{_label_badge(label)} '
                                f'<b>Score: {final:.4f}</b> | 출처: {source}<br/>'
                                f'<div style="margin-top:6px;font-size:0.9em;white-space:pre-wrap;">'
                                f'{r.get("text", "")[:600]}</div>'
                                f"</div>",
                                unsafe_allow_html=True,
                            )
                else:
                    st.error(f"오류: {resp.text}")
            except requests.ConnectionError:
                st.error("백엔드 서버에 연결할 수 없습니다.")
