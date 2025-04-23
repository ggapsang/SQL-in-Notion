import pandas as pd
import streamlit as st
from notion_client import Client
from datetime import datetime


def format_database_id(raw_id: str) -> str:
    """하이픈 없는 Notion 데이터베이스 ID를 하이픈 포함된 형식으로 변환"""
    return f"{raw_id[:8]}-{raw_id[8:12]}-{raw_id[12:16]}-{raw_id[16:20]}-{raw_id[20:]}"

def get_user_databases(notion):
    """현재 사용자가 접근 가능한 Notion 데이터베이스 목록을 가져오기"""
    dbs = notion.search(filter={"property": "object", "value": "database"})["results"]
    return [(db["title"][0]["plain_text"] if db["title"] else "[제목 없음]", db["id"]) for db in dbs]


def get_database_rows(notion, database_id):
    """지정한 Notion 데이터베이스의 모든 row를 반환"""
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

def get_database_columns(notion, database_id):
    """Notion 데이터베이스의 컬럼(속성) 이름 목록을 가져옴"""
    response = notion.databases.retrieve(database_id=database_id)
    return list(response.get("properties", {}).keys())

def extract_text_value(prop):
    """Notion 속성(property) 객체에서 사람이 읽을 수 있는 텍스트 값을 추출"""
    try:
        typ = prop["type"]
        if typ == "title":
            return prop["title"][0]["plain_text"] if prop["title"] else ""
        elif typ == "rich_text":
            return prop["rich_text"][0]["plain_text"] if prop["rich_text"] else ""
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
    """날짜 속성에서 시작일과 종료일을 추출"""
    try:
        if prop["type"] != "date":
            return None, None
        date_info = prop["date"]
        return date_info.get("start"), date_info.get("end", date_info.get("start"))
    except:
        return None, None

def load_database_info(notion, database_id):
    """
    Notion 데이터베이스의 정보와 칼럼 타입 정보를 반환
    Args:
        notion (Client): 인증된 Notion API 클라이언트
        database_id (str): 데이터베이스 ID
    Returns:
        tuple: (database_obj, column_types_dict)
    """
    db = notion.databases.retrieve(database_id=database_id)
    columns_types = {}
    
    for prop_name, prop_info in db.get("properties", {}).items():
        prop_type = prop_info.get("type")
        columns_types[prop_name] = prop_type
    
    return db, columns_types
    
    
def notion_to_dataframe(db_columns, db_rows):
    """Notion 데이터베이스 행들을 pandas DataFrame으로 변환"""
    data = []
    for row in db_rows:
        row_dict = {}
        for col in db_columns:
            if col in row["properties"]:
                prop = row["properties"][col]
                row_dict[col] = extract_text_value(prop)
            else:
                row_dict[col] = None
        data.append(row_dict)
    return pd.DataFrame(data)

def perform_inner_join(left_df, right_df, join_conditions):
    """두 DataFrame간 inner join 수행"""
    if not join_conditions:
        st.error("조인 조건이 설정되지 않았습니다!")
        return None
    
    # join_conditions를 pandas merge에 맞는 형식으로 변환
    left_on = []
    right_on = []
    
    for left_col, right_col in join_conditions:
        left_on.append(left_col)
        right_on.append(right_col)
    
    # suffixes 설정
    left_suffix = '_left'
    right_suffix = '_right'
    
    # 조인 수행
    try:
        result_df = pd.merge(
            left_df, right_df, 
            left_on=left_on, right_on=right_on, 
            how='inner',
            suffixes=(left_suffix, right_suffix)
        )
        return result_df
    except Exception as e:
        st.error(f"조인 수행 중 오류 발생: {e}")
        return None

def create_notion_database(notion, parent_page_id, database_name, columns):
    """Notion에 새 데이터베이스 생성"""
    properties = {}
    
    # Name 속성 (필수)
    properties["Name"] = {
        "title": {}
    }
    
    # 나머지 속성 추가
    for col in columns:
        if col != "Name":  # Name은 이미 추가됨
            properties[col] = {
                "rich_text": {}
            }
    
    try:
        response = notion.databases.create(
            parent={"page_id": parent_page_id},
            title=[{
                "type": "text",
                "text": {"content": database_name}
            }],
            properties=properties
        )
        return response["id"]
    except Exception as e:
        st.error(f"데이터베이스 생성 중 오류 발생: {e}")
        return None

def add_rows_to_notion_database(notion, database_id, df):
    """DataFrame의 데이터를 Notion 데이터베이스에 행으로 추가"""
    success_count = 0
    total_count = len(df)
    
    with st.spinner(f'Notion에 {total_count}개 행 추가 중...'):
        for i, row in df.iterrows():
            try:
                properties = {}
                
                # 첫 번째 열을 title로 사용
                first_col = df.columns[0]
                properties["Name"] = {
                    "title": [{"text": {"content": str(row[first_col])}}]
                }
                
                # 나머지 열을 rich_text로 추가
                for col in df.columns:
                    if col != first_col:
                        properties[col] = {
                            "rich_text": [{"text": {"content": str(row[col])}}]
                        }
                
                notion.pages.create(
                    parent={"database_id": database_id},
                    properties=properties
                )
                success_count += 1
            except Exception as e:
                st.error(f"행 {i+1} 추가 중 오류: {e}")
        
        return success_count, total_count
