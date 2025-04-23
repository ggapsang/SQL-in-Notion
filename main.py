import streamlit as st
from notion_client import Client
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from utils import format_database_id, get_user_databases, get_database_rows, get_database_columns, extract_text_value, load_database_info

### 테스트 코드 ###
notion = Client(auth="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")  # 테스트용 토큰

SAMPLE_PRODUCT_DB_ID = "1ddc9e591278815a8c0ac7e88daf78d1"
SAMPLE_ORDER_DB_ID = "1ddc9e59127881eca812cf3238d176bb"

product_db_id = format_database_id(SAMPLE_PRODUCT_DB_ID)
order_db_id = format_database_id(SAMPLE_ORDER_DB_ID)

product_db, product_columns_types = load_database_info(notion, product_db_id)
order_db, order_columns_types = load_database_info(notion, order_db_id)

product_db_rows = get_database_rows(notion, product_db_id)
order_db_rows = get_database_rows(notion, order_db_id)

product_db_columns = get_database_columns(notion, product_db_id)
order_db_columns = get_database_columns(notion, order_db_id)
###------###

def get_dict_from_row(row, db_columns):
    """Notion 데이터베이스의 row에서 각 속성의 값을 추출하여 딕셔너리로 반환"""
    result = {}
    for col in db_columns:
        prop = row["properties"][col]
        result[col] = extract_text_value(prop)
    return result

def notion_to_dataframe(db_columns, db_rows):
    """Notion 데이터베이스 행들을 pandas DataFrame으로 변환"""
    data = [get_dict_from_row(row, db_columns) for row in db_rows]
    return pd.DataFrame(data)

def go_inner_join(df1, df2, on):
    """두 DataFrame을 inner join"""
    return pd.merge(df1, df2, on=on, how="inner")

st.write(df.head())
