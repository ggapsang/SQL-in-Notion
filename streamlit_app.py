import streamlit as st
from notion_client import Client
from datetime import datetime
from utils import format_database_id, get_user_databases, get_database_rows, get_database_columns, extract_text_value

# Notion 설정
notion = Client(auth="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")  # 테스트용 토큰

SAMPLE_PRODUCT_DB_ID = "1ddc9e591278815a8c0ac7e88daf78d1"
SAMPLE_ORDER_DB_ID = "1ddc9e59127881eca812cf3238d176bb"

product_db_id = format_database_id(SAMPLE_PRODUCT_DB_ID)
order_db_id = format_database_id(SAMPLE_ORDER_DB_ID)

product_db = notion.databases.retrieve(database_id=product_db_id)
order_db = notion.databases.retrieve(database_id=order_db_id)


def go_inner_join():
    return "INNER JOIN 결과"

# 페이지 설정
st.title("SQL IN NOTION PROJECT")
st.subheader("INNER JOIN")

db_options = get_user_databases(notion)
if not db_options:
    st.warning("⚠️ 접근 가능한 데이터베이스가 없습니다.")
    st.stop()

left_db_label = st.selectbox("📂 LEFT 데이터베이스 선택", db_options, index=0, key="left_db_label")
right_db_label = st.selectbox("📂 RIGHT 데이터베이스 선택", db_options, index=1, key="right_db_label")

left_db_nm = left_db_label[0]
right_db_nm = right_db_label[0]

st.write()
st.markdown("---")

# form init
if "join_condition_count" not in st.session_state:
    st.session_state.join_condition_count = 1


# SELECT section
st.markdown("# 🔍 SELECT")
st.markdown("📋 가져올 칼럼 선택")
with st.form("select_form"):
    left_columns = st.multiselect(f"{left_db_nm} 칼럼", options=product_db["properties"].keys(), 
                               default=list(product_db["properties"].keys()), key="left_columns")
    right_columns = st.multiselect(f"{right_db_nm} 칼럼", options=order_db["properties"].keys(), 
                                default=list(order_db["properties"].keys()), key="right_columns")
    select_submitted = st.form_submit_button("칼럼 선택 저장")
    
    if select_submitted:
        st.session_state.left_columns = left_columns
        st.session_state.right_columns = right_columns
        st.success("칼럼 선택이 저장되었습니다.")

st.markdown("---")

st.markdown("# 📚 FROM") # FROM
st.markdown(f"### {left_db_nm}")
st.markdown("# 🔗 INNER JOIN") # INNERJOIN
st.markdown(f"### {right_db_nm}")

st.markdown("---")

# ON section
if "join_condition_count" not in st.session_state:
    st.session_state.join_condition_count = 1

def add_join_condition():
    st.session_state.join_condition_count += 1

st.markdown("## 🧩 ON")
st.markdown(f"🔄 {left_db_nm}과 {right_db_nm}사이의 키 칼럼")

st.button("➕ JOIN 조건 추가", on_click=add_join_condition)

join_conditions = []
for i in range(st.session_state.join_condition_count):
    col1, col2, col3 = st.columns([4, 1, 4])
    with col1:
        left_col = st.selectbox(f"LEFT 칼럼 {i+1}", product_db["properties"].keys(), key=f"join_left_{i}")
    with col2:
        st.markdown("#### =")
    with col3:
        right_col = st.selectbox(f"RIGHT 칼럼 {i+1}", order_db["properties"].keys(), key=f"join_right_{i}")
    join_conditions.append((left_col, right_col))

st.markdown("---")

# WHERE section
st.markdown("## 🚦 WHERE")
st.markdown("🔍 JOIN 결과에서 추가 필터링이 필요할 경우")
with st.form("where_form"):
    where_condition = st.text_input("WHERE 조건 (SQL 구문)", key="where_condition")
    where_submitted = st.form_submit_button("필터 조건 저장")
    
    if where_submitted:
        st.session_state.where_condition = where_condition
        st.success("필터 조건이 저장되었습니다.")

st.markdown("---")

# 최종 실행 버튼
if st.button("🚀 INNER JOIN 실행"):
    if hasattr(st.session_state, 'left_columns') and hasattr(st.session_state, 'right_columns'):
        go_inner_join()
    else:
        st.warning("SELECT 칼럼을 먼저 저장해주세요.")