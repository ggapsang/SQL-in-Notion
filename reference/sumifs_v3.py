import streamlit as st
from notion_client import Client
from datetime import datetime

# Notion 설정
notion = Client(auth="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")  # 테스트용 토큰

# Notion 유틸
def format_database_id(raw_id: str) -> str:
    return f"{raw_id[:8]}-{raw_id[8:12]}-{raw_id[12:16]}-{raw_id[16:20]}-{raw_id[20:]}"

def get_user_databases():
    dbs = notion.search(filter={"property": "object", "value": "database"})["results"]
    return [(db["title"][0]["plain_text"] if db["title"] else "[제목 없음]", db["id"]) for db in dbs]

def get_database_rows(database_id):
    results = []
    next_cursor = None
    while True:
        response = notion.databases.query(
            **({"database_id": database_id, "start_cursor": next_cursor} if next_cursor else {"database_id": database_id})
        )
        results.extend(response["results"])
        next_cursor = response.get("next_cursor")
        if not response.get("has_more"):
            break
    return results

def get_database_columns(database_id):
    response = notion.databases.retrieve(database_id=database_id)
    return list(response.get("properties", {}).keys())

def extract_text_value(prop):
    try:
        typ = prop["type"]
        if typ == "title":
            return prop["title"][0]["plain_text"] if prop["title"] else ""
        elif typ == "rich_text":
            return prop["rich_text"][0]["text"]["plain_text"] if prop["rich_text"] else ""
        elif typ == "select":
            return prop["select"]["name"] if prop["select"] else ""
        elif typ == "number":
            return prop["number"] if prop["number"] else 0
        elif typ == "date":
            return prop["date"]["start"] if prop["date"] else ""
        else:
            return f"[지원 안함: {typ}]"
    except Exception as e:
        return f"[에러: {e}]"

def extract_date_range(prop):
    try:
        if prop["type"] != "date":
            return None, None
        date_info = prop["date"]
        return date_info.get("start"), date_info.get("end", date_info.get("start"))
    except:
        return None, None

# 페이지 시작
st.title("📊 SUMIFS in Notion")

# 콜아웃 추가
st.markdown("""
💡 **사용 가이드**

- 👉 **조건은 최소 1개부터 시작**하며, 필요한 만큼 `➕ 조건 추가` 버튼으로 늘릴 수 있습니다.
- 🎯 **결과가 입력될 칼럼은 반드시 숫자(Number) 타입**이어야 하며, 그렇지 않으면 오류가 발생합니다.
- 🚫 **다중 선택(multi_select)** 속성은 현재 조건 비교 및 합계 계산에 **지원하지 않습니다**.
- 📅 날짜 조건을 사용하려면 **'날짜'로 설정된 칼럼**을 사용하고, 비교 대상에는 **시작일~종료일 범위가 있는 필드**를 선택하세요.
- ✅ 지원되는 조건 비교 타입: `텍스트(title, rich_text)`, `선택(select)`, `날짜(date)`, `숫자(number)`

---
""")

# 사용자에게 접근 가능한 DB 리스트 보여주기
db_options = get_user_databases()
if not db_options:
    st.warning("⚠️ 접근 가능한 데이터베이스가 없습니다.")
    st.stop()

target_label = st.selectbox("🎯 대상 (Target) 데이터베이스 선택", db_options, index=0, key="target_db")
source_label = st.selectbox("📂 참조 (Source) 데이터베이스 선택", db_options, index=1, key="source_db")

# 선택된 ID를 기존 고정값 대신 할당 (format 유지)
target_database_id = target_label[1]
src_database_id = source_label[1]
target_cols = get_database_columns(target_database_id)
src_cols = get_database_columns(src_database_id)

# 조건 상태 세션에 보관
if "condition_count" not in st.session_state:
    st.session_state.condition_count = 1
if st.button("➕ 조건 추가"):
    st.session_state.condition_count += 1

# 폼 내부
with st.form("sumifs_form"):
    st.subheader("🎯 설정값 입력")

    target_column = st.selectbox("📥 결과 입력 칼럼", target_cols)
    sum_range_column = st.selectbox("💰 합계 대상 칼럼 (Source)", src_cols)

    st.markdown("### ✅ 조건 설정")
    dynamic_conditions = []
    for i in range(st.session_state.condition_count):
        st.markdown(f"🔹 조건 {i+1}")
        col1, col2, col3 = st.columns([4, 4, 2])
        with col1:
            src_col = st.selectbox(f"Source 칼럼 {i+1}", src_cols, key=f"src_{i}")
        with col2:
            tgt_col = st.selectbox(f"Target 칼럼 {i+1}", target_cols, key=f"tgt_{i}")
        with col3:
            is_range = st.checkbox("📅 날짜", key=f"range_{i}")
        dynamic_conditions.append({
            "src_col": src_col,
            "tgt_col": tgt_col,
            "is_range": is_range
        })

    submitted = st.form_submit_button("🚀 SUMIFS 실행")

if submitted:
    target_rows = get_database_rows(target_database_id)
    src_rows = get_database_rows(src_database_id)

    src_data = []
    for row in src_rows:
        props = row["properties"]
        row_dict = {}
        for cond in dynamic_conditions:
            row_dict[cond["src_col"]] = extract_text_value(props[cond["src_col"]]).strip()
        row_dict["value"] = props[sum_range_column]["number"]
        src_data.append(row_dict)

    updated_count = 0
    for row in target_rows:
        props = row["properties"]
        page_id = row["id"]

        target_criteria = {
            cond["tgt_col"]: extract_text_value(props[cond["tgt_col"]]).strip()
            for cond in dynamic_conditions
        }

        matched_vals = []
        for src_row in src_data:
            is_match = True
            for cond in dynamic_conditions:
                src_val = src_row[cond["src_col"]]
                tgt_val = target_criteria[cond["tgt_col"]]

                if cond["is_range"]:
                    try:
                        src_date = datetime.fromisoformat(src_val)
                        tgt_start, tgt_end = extract_date_range(props[cond["tgt_col"]])
                        if not (tgt_start and tgt_end):
                            is_match = False
                            break
                        start = datetime.fromisoformat(tgt_start)
                        end = datetime.fromisoformat(tgt_end)
                        if not (start <= src_date <= end):
                            is_match = False
                            break
                    except:
                        is_match = False
                        break
                else:
                    if src_val != tgt_val:
                        is_match = False
                        break

            if is_match:
                matched_vals.append(src_row["value"])

        total = sum(matched_vals)
        #st.write(f"📌 조건: {target_criteria}, 합계: {total}")

        notion.pages.update(
            page_id=page_id,
            properties={target_column: {"number": total}}
        )
        updated_count += 1

    st.success(f"✅ {updated_count} rows updated successfully!")
