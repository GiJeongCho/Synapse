[x] 벡터 DB 연결 (실제 문서 들어가는지) — Milvus 연동 완료
[x] api들 제대로 연결 — 문서/검색/meta-agent/tools/schedules/workflows 라우터 연결 완료
[x] rerank 모델 교체 — 외부 API(`RERANK_API_URL`) 연동 완료 (폴백 가중합 병행)
[x] 프론트엔드 React 전환 — Streamlit → React(Vite+TS) 완료

나중에 (현재 미해결 — 상세는 docs/구현_현황.md §8 참고)
1. 논문에 구현된 수식(RC/BI/ICC/DCC/SC)이랑 실제 metrics.py 맞는지 재검증
2. 스케줄 자동 등록 (요청문의 "매일 9시" 등을 파싱해 cron 자동 등록)
3. GraphStore search() 구현 → graph_agent를 실제 그래프 기반으로 전환
4. 하이브리드 검색 Graph fusion(RRF)
5. Job Store PostgreSQL 전환, JWT 인증 실구현