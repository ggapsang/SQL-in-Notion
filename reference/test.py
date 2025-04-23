import streamlit as st
from notion_client import Client
from datetime import datetime, timedelta
from utils import format_database_id, get_user_databases, get_database_rows, get_database_columns, extract_text_value, load_database_info

# Notion 설정
notion = Client(auth="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")  # 테스트용 토큰

SAMPLE_PRODUCT_DB_ID = "1ddc9e591278815a8c0ac7e88daf78d1"
SAMPLE_ORDER_DB_ID = "1ddc9e59127881eca812cf3238d176bb"

product_db_id = format_database_id(SAMPLE_PRODUCT_DB_ID)
order_db_id = format_database_id(SAMPLE_ORDER_DB_ID)

product_db, product_columns_types = load_database_info(notion, product_db_id)
order_db, order_columns_types = load_database_info(notion, order_db_id)

st.write("Notion 데이터베이스 정보")
st.write(product_db)

# 데이터베이스 값 상위 10개 로드
product_db_rows = get_database_rows(notion, product_db_id)[:10]
st.write("상위 10개 데이터")
st.write(product_db_rows)