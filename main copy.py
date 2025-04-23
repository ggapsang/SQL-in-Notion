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

def apply_filter(df, filters, columns_types):
    """필터 조건에 따라 DataFrame 필터링"""
    if not filters:
        return df
    
    filtered_df = df.copy()
    for filter_condition in filters:
        column = filter_condition["column"]
        operator = filter_condition["operator"]
        value = filter_condition["value"]
        col_type = filter_condition["type"]
        
        # 필터 조건이 비어있거나 해당하지 않으면 건너뛰기
        if operator in ["is_empty", "is_not_empty", "this_week", "past_week", "past_month", "past_year"] and value is None:
            continue
            
        # 텍스트 관련 연산자
        if operator == "equals":
            filtered_df = filtered_df[filtered_df[column] == value]
        elif operator == "does_not_equal":
            filtered_df = filtered_df[filtered_df[column] != value]
        elif operator == "contains":
            filtered_df = filtered_df[filtered_df[column].str.contains(value, na=False)]
        elif operator == "starts_with":
            filtered_df = filtered_df[filtered_df[column].str.startswith(value, na=False)]
        elif operator == "ends_with":
            filtered_df = filtered_df[filtered_df[column].str.endswith(value, na=False)]
        
        # 숫자 관련 연산자
        elif operator == "greater_than":
            filtered_df = filtered_df[filtered_df[column] > value]
        elif operator == "less_than":
            filtered_df = filtered_df[filtered_df[column] < value]
        elif operator == "greater_than_or_equal_to":
            filtered_df = filtered_df[filtered_df[column] >= value]
        elif operator == "less_than_or_equal_to":
            filtered_df = filtered_df[filtered_df[column] <= value]
        
        # 빈값 관련 연산자
        elif operator == "is_empty":
            filtered_df = filtered_df[filtered_df[column].isna() | (filtered_df[column] == "")]
        elif operator == "is_not_empty":
            filtered_df = filtered_df[~filtered_df[column].isna() & (filtered_df[column] != "")]
            
        # 날짜 관련 연산자
        elif col_type == "date":
            if operator == "before":
                filtered_df = filtered_df[pd.to_datetime(filtered_df[column]) < pd.to_datetime(value)]
            elif operator == "after":
                filtered_df = filtered_df[pd.to_datetime(filtered_df[column]) > pd.to_datetime(value)]
            elif operator == "on_or_before":
                filtered_df = filtered_df[pd.to_datetime(filtered_df[column]) <= pd.to_datetime(value)]
            elif operator == "on_or_after":
                filtered_df = filtered_df[pd.to_datetime(filtered_df[column]) >= pd.to_datetime(value)]
            # 추가 날짜 필터는 필요시 구현
    
    return filtered_df


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




def main():
    return "dummy main function" 
