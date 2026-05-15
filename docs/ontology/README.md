# LG HelloDoctor 도메인 온톨로지

`backend/main.py` 의 6개 코드 사전을 정식 OWL/SKOS 온톨로지로 격상한 결과물.
한국어 시니어 음성 의료 AI의 의료 지식을 W3C 표준 시맨틱 웹 형식으로 표현한다.

---

## 파일

| 파일 | 내용 |
|------|------|
| `hellodoctor.ttl` | Turtle 직렬화 OWL/SKOS 온톨로지 (단일 파일) |
| `README.md` | 본 문서 — 구조·통계·SPARQL 예시 |

---

## 통계 (v0.1.0, 2026-05-15)

| 항목 | 개수 |
|------|-----:|
| `owl:Class` (스키마) | 16 |
| `owl:ObjectProperty` | 6 |
| `owl:DatatypeProperty` | 5 |
| 개체(Individual) — 진료과 | 14 |
| 개체 — 신체부위 | 10 |
| 개체 — 일반 증상 | 10 |
| 개체 — 응급 증상 | 7 |
| 개체 — 질병 | 8 |
| 개체 — 약물 | 8 |
| 개체 — 검사 | 6 |
| 개체 — 의도 | 5 |
| 개체 — 금지어 | 10 |
| 개체 — 호출어 | 1 |
| **총 개체** | **79** |
| 외부 표준 매핑 (`skos:closeMatch`) | SNOMED CT 30+ |

---

## 코드 사전 → 온톨로지 매핑

| `backend/main.py` 사전 | 형식화 결과 |
|---|---|
| `MEDICAL_CORRECTIONS` (38 항목) | `skos:altLabel` 로 모든 진료과·증상·약물·검사·질병에 부착 |
| `EMERGENCY_KEYWORDS` (9 항목) | 7개 `hd:Symptom` 개체 (`hd:RespiratoryArrest` 등) + `skos:hiddenLabel` |
| `EMERGENCY_SCORES` (10 항목) | `hd:emergencyScore` 데이터 속성 + `hd:EmergencyLevel` 임계값 |
| `SYMPTOM_DEPT_MAP` (12 항목) | `hd:treatedBy` 관계 + `hd:kakaoCategoryCode` |
| `QUERY_REWRITE_MAP` (8 항목) | `hd:rewriteQuery` 데이터 속성 |
| `FOLLOWUP_QUESTIONS` (6 항목) | `hd:followupQuestion` 데이터 속성 |
| `FORBIDDEN_WORDS` (10 항목) | `hd:ForbiddenTerm` 개체 10종 + 의료법 조문 주석 |
| `WAKE_WORDS` (4 항목) | `hd:Hellobi` 단일 개체 + 4개 `skos:altLabel` |

---

## 클래스 계층

```
hd:MedicalConcept
├── hd:Symptom         (감각·증상)
├── hd:BodyPart        (해부 부위)
│   ├── hd:Head
│   ├── hd:Torso
│   ├── hd:UpperLimb
│   ├── hd:LowerLimb
│   └── hd:Integument
├── hd:MedicalDepartment (진료과)
├── hd:Drug
├── hd:Disease
└── hd:DiagnosticTest

hd:Intent           (B팀 분류 라벨 5종)
hd:EmergencyLevel   (응급도 임계값)
hd:ForbiddenTerm    (의료법 금지어)
hd:WakeWord         (호출어)
```

---

## 핵심 관계 (Object Properties)

| 속성 | 도메인 → 레인지 | 의미 |
|------|------------|------|
| `hd:partOf` (`owl:TransitiveProperty`) | `BodyPart → BodyPart` | 무릎 → 하지 → 신체부위 (추이 추론) |
| `hd:affectsBodyPart` | `Symptom → BodyPart` | 증상-부위 연결 |
| `hd:treatedBy` | `Symptom → Department` | 증상-진료과 매칭 |
| `hd:requiresDepartment` | `Disease → Department` | 질병-진료과 매칭 |
| `hd:triggersEmergency` | `Symptom → EmergencyLevel` | 응급 분기 |

---

## SPARQL 예시 — 정식 온톨로지가 가져오는 가치

### Q1. 응급 점수 80 이상인 모든 증상

```sparql
PREFIX hd: <http://lghellodoctor.ai/ontology#>

SELECT ?symptom ?label ?score
WHERE {
  ?symptom a hd:Symptom ;
           hd:emergencyScore ?score ;
           rdfs:label ?label .
  FILTER (?score >= 80 && lang(?label) = "ko")
}
ORDER BY DESC(?score)
```

### Q2. "허리"에 관련된 모든 증상과 진료과 (역방향 탐색)

```sparql
SELECT ?symptom ?dept
WHERE {
  ?symptom hd:affectsBodyPart hd:LowerBack ;
           hd:treatedBy ?dept .
}
```

### Q3. **추이적 추론 활용** — 하지(`LowerLimb`) 부위 증상 전부

`hd:partOf` 가 `owl:TransitiveProperty` 라서 추론기(Pellet/HermiT/Apache Jena Reasoner)를 통과시키면 무릎 증상도 자동 포함된다.

```sparql
SELECT ?symptom ?part
WHERE {
  ?symptom hd:affectsBodyPart ?part .
  ?part hd:partOf* hd:LowerLimb .
}
```

→ **코드 사전(dict)으로는 불가능한 질의**. 형식 온톨로지의 핵심 가치.

### Q4. Kakao 카테고리 코드로 그룹화

```sparql
SELECT ?code (GROUP_CONCAT(?label; SEPARATOR=", ") AS ?depts)
WHERE {
  ?d a hd:MedicalDepartment ;
     hd:kakaoCategoryCode ?code ;
     rdfs:label ?label .
  FILTER (lang(?label) = "ko")
}
GROUP BY ?code
```

### Q5. STT 오인식 → 표준어 역추적

```sparql
SELECT ?concept ?wrong ?correct
WHERE {
  ?concept skos:altLabel ?wrong ;
           rdfs:label ?correct .
  FILTER (lang(?correct) = "ko")
}
```

---

## 로드 방법 (Python — rdflib)

```python
from rdflib import Graph, Namespace

g = Graph()
g.parse("docs/ontology/hellodoctor.ttl", format="turtle")

HD = Namespace("http://lghellodoctor.ai/ontology#")

# 응급 점수 ≥ 80 인 증상 전부
q = """
PREFIX hd: <http://lghellodoctor.ai/ontology#>
SELECT ?label ?score WHERE {
  ?s hd:emergencyScore ?score ; rdfs:label ?label .
  FILTER (?score >= 80 && lang(?label) = "ko")
}
"""
for row in g.query(q):
    print(row.label, row.score)
```

---

## 외부 표준 매핑

본 온톨로지는 다음 의료 표준과 `skos:closeMatch` 관계로 연결되어 있다.

- **SNOMED CT** — 국제 임상 용어 표준 (`http://snomed.info/id/{code}`)
- **KCD-8** — 한국표준질병사인분류 (URI 예약, 매핑 추후)

⚠️ **임상 검증 주의**: 현재 SNOMED 매핑은 기술적 참조 매핑이며, 실제 임상 사용 전에는 의사(응급의학·일반의) 검수가 필요하다. HITL 1차 책임자는 **의사** ([CLAUDE.md](../../CLAUDE.md) §HITL 매트릭스 참고).

---

## 시맨틱 웹 도구로 검증

```bash
# 1) ROBOT (OBO 표준 검증 도구)
robot validate-profile --profile OWL2DL --input hellodoctor.ttl

# 2) Apache Jena (RDF 문법 + SPARQL)
riot --validate hellodoctor.ttl

# 3) Protégé GUI 로 시각화
#    File → Open → hellodoctor.ttl
```

---

## 향후 작업 (Future Work)

1. **KCD-8 매핑 추가** — 한국 표준 질병분류 코드 직접 부착
2. **UMLS Metathesaurus 연결** — Concept Unique Identifier(CUI) 매핑
3. **추론 규칙 추가** — SWRL 또는 SHACL Rules 로 "응급 증상은 자동으로 emergency intent" 규칙 형식화
4. **SHACL 제약 추가** — 모든 `hd:Symptom` 은 반드시 `hd:affectsBodyPart` 또는 `hd:triggersEmergency` 를 가져야 함 등
5. **CI 자동 동기화** — `backend/main.py` 의 6개 dict 변경 시 TTL 자동 재생성 + 회귀 검증
