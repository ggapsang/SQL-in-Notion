## 1. 데이터 구조
---

- 노션의 데이터베이스는 기본적으로 페이지(page)의 집합이다
- 각 페이지는 `properties` 필드에 여러 속성을 담고 있고, 이 속성들은 **Key-Value** 형태로 되어 있다
- 속성 타입은 다양하다
	- `title`
	- `rich_text`
	- `number`
	- `date`
	- `select`
	- `relation`
	- `checkbox`
	- `multi_select`
- 실제로는 이런 속성 값들을 JSON 형식으로 감싸는 구조

### 📋 Notion 속성 타입 정리

|타입 이름|설명|예시|
|---|---|---|
|`title`|데이터베이스의 주요 제목 필드 (한 개만 존재 가능)|`"홍길동"`|
|`rich_text`|일반 텍스트 필드, 서식 포함 가능|`"메모 내용입니다"`|
|`number`|숫자형 데이터 (합계, 계산 등에 사용 가능)|`123`, `45.6`|
|`select`|단일 선택 옵션 (미리 정의된 값 중 하나 선택)|`"완료됨"`|
|`multi_select`|다중 선택 옵션 (여러 값 선택 가능)|`["디자인", "기획"]`|
|`date`|날짜 및 시간 정보 (범위도 설정 가능)|`2025-04-23`, `2025-04-01 ~ 2025-04-05`|
|`checkbox`|참/거짓을 나타내는 체크박스|`true`, `false`|
|`relation`|다른 데이터베이스의 페이지 참조|`[page_id1, page_id2]`|
|`formula`|수식 기반 계산 필드 (다른 속성을 조합해 계산)|`if(Status == "완료", 1, 0)`|
|`rollup`|Relation 필드를 기반으로 집계 수행|`합계`, `개수`, `최댓값` 등|
|`files`|첨부된 파일이나 이미지|`[file1, file2]`|
|`url`|하이퍼링크 주소|`"https://example.com"`|
|`email`|이메일 주소 필드|`"user@example.com"`|
|`phone_number`|전화번호 필드|`"+82-10-1234-5678"`|
|`people`|노션 사용자(멤버)를 태그|`[사용자1, 사용자2]`|
|`created_time`|해당 페이지 생성 시간|`2025-04-21T12:34:56Z`|
|`last_edited_time`|마지막 수정 시간|`2025-04-22T09:30:00Z`|

```json
{
  "object": "page",
  "id": "...",
  "properties": {
    "이름": {
      "type": "title",
      "title": [{ "text": { "content": "홍길동" } }]
    },
    "나이": {
      "type": "number",
      "number": 30
    },
    ...
  }
}

```
