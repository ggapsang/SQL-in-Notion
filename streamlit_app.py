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

left_db_label = st.selectbox("🎯 LEFT 데이터베이스 선택", db_options, index=0, key="left_db_label")
right_db_label = st.selectbox("📂 RIGHT 데이터베이스 선택", db_options, index=1, key="right_db_label")

st.write()
st.markdown("---")

st.markdown("# SELECT")
if "condition_count" not in st.session_state:
    st.session_state.condition_count = 1
if st.button("➕ 칼럼 추가"):
    st.session_state.condition_count += 1

with st.form("select_form"):
    st.subheader("🎯 가져올 칼럼 선택")
    


st.markdown("# FROM")
with st.form("select_form"):
    st.subheader("기준(왼쪽) 테이블 선택")

st.markdown("# INNER JOIN")
st.markdown("## ON")
with st.form("select_form"):
    st.subheader("JOIN 조건 설정")

st.markdown("## WHERE")
with st.form("select_form"):
    st.subheader("기준 조건 설정")

submitted = st.form_submit_button("🚀 INNER JOIN 실행")
if submitted:
    go_inner_join()

st.markdown("---")

