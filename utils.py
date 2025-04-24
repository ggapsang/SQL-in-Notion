import pandas as pd
import streamlit as st
from notion_client import Client
from datetime import datetime
import aiohttp
import asyncio
import time


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

def create_notion_database(notion, parent_page_id, database_name, columns, left_columns_types=None, right_columns_types=None):
    """
    Notion에 새 데이터베이스 생성
    
    Args:
        notion: Notion 클라이언트
        parent_page_id: 부모 페이지 ID
        database_name: 데이터베이스 이름
        columns: 열 이름 목록
        left_columns_types: 왼쪽 테이블 열 타입 정보 (선택적)
        right_columns_types: 오른쪽 테이블 열 타입 정보 (선택적)
    """
    properties = {}
    
    # Name 속성 (필수)
    properties["Name"] = {
        "title": {}
    }
    
    # 나머지 속성 추가 (타입 정보 활용)
    for col in columns:
        if col == "Name":  # Name은 이미 추가됨
            continue
            
        # 열 이름에서 '_right' 접미사 제거
        original_col = col.replace('_right', '')
        
        # 타입 정보 찾기
        col_type = None
        if left_columns_types and original_col in left_columns_types:
            col_type = left_columns_types[original_col]
        elif right_columns_types and original_col in right_columns_types:
            col_type = right_columns_types[original_col]
        
        # 열 타입에 따라 속성 설정
        if col_type == "number":
            properties[col] = {"number": {}}
        elif col_type == "date":
            properties[col] = {"date": {}}
        elif col_type == "select":
            properties[col] = {"select": {}}
        else:
            # 기본값은 일반 텍스트
            properties[col] = {"rich_text": {}}
    
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

def add_rows_to_notion_database(notion, database_id, dataframe, left_db_name=None):
    """DataFrame의 행을 Notion 데이터베이스에 추가"""
    total_rows = len(dataframe)
    success_count = 0
    
    # 데이터베이스 스키마 정보 가져오기
    db_info = notion.databases.retrieve(database_id=database_id)
    db_properties = db_info["properties"]
    
    for idx, row in dataframe.iterrows():
        # 행 데이터로 properties 구성
        properties = {}
        
        # Name 속성 설정 (페이지 이름이 됨)
        name_value = f"{left_db_name or 'Row'} #{idx+1}"
        properties["Name"] = {
            "title": [{"text": {"content": name_value}}]
        }
        
        # 나머지 속성 처리
        for col in dataframe.columns:
            # Name은 제외 (이미 처리함)
            if col == "Name":
                continue
                
            value = row[col]
            
            # 컬럼 속성 타입 확인
            if col in db_properties:
                prop_type = db_properties[col]["type"]
                
                # 타입에 따라 다르게 처리
                if prop_type == "title":
                    properties[col] = {
                        "title": [{"text": {"content": str(value)}}]
                    }
                elif prop_type == "rich_text":
                    properties[col] = {
                        "rich_text": [{"text": {"content": str(value)}}]
                    }
                elif prop_type == "number":
                    # 숫자로 변환 시도
                    try:
                        num_value = float(value) if value is not None else None
                        properties[col] = {"number": num_value}
                    except (ValueError, TypeError):
                        properties[col] = {"number": None}
                elif prop_type == "date":
                    # 날짜 형식으로 변환
                    try:
                        if isinstance(value, pd.Timestamp) or isinstance(value, datetime):
                            date_str = value.isoformat()
                            properties[col] = {"date": {"start": date_str}}
                        else:
                            properties[col] = {"date": None}
                    except Exception:
                        properties[col] = {"date": None}
                elif prop_type == "select":
                    # 선택 옵션
                    if value:
                        properties[col] = {"select": {"name": str(value)}}
                    else:
                        properties[col] = {"select": None}
                elif prop_type == "multi_select":
                    # 다중 선택 (문자열을 쉼표로 분리)
                    if isinstance(value, str) and value:
                        options = [{"name": option.strip()} for option in value.split(',')]
                        properties[col] = {"multi_select": options}
                    else:
                        properties[col] = {"multi_select": []}
                elif prop_type == "checkbox":
                    # 불리언 값
                    bool_value = bool(value) if value is not None else False
                    properties[col] = {"checkbox": bool_value}
                else:
                    # 기타 타입은 텍스트로 변환
                    properties[col] = {
                        "rich_text": [{"text": {"content": str(value)}}]
                    }
        
        try:
            notion.pages.create(
                parent={"database_id": database_id},
                properties=properties
            )
            success_count += 1
        except Exception as e:
            st.error(f"행 {+1} 추가 중 오류: {e}")
    
    return success_count, total_rows

def add_rows_with_progress(notion, database_id, dataframe, left_db_name):
    import asyncio
    # 윈도우 환경에서는 아래 코드 필요
    if asyncio.get_event_loop().is_closed():
        asyncio.set_event_loop(asyncio.new_event_loop())
    
    with st.spinner(f"Notion에 {len(dataframe)}개 행 저장 중..."):
        start_time = time.time()
        loop = asyncio.get_event_loop()
        success, total, failed = loop.run_until_complete(
            add_rows_to_notion_database_async(notion, database_id, dataframe, left_db_name)
        )
        end_time = time.time()
        
        st.success(f"✅ {success}/{total} 행 저장 완료! (소요 시간: {end_time-start_time:.2f}초)")
        if failed:
            st.warning(f"⚠️ {len(failed)}개 행 저장 실패")
    
    return success, total

async def add_rows_to_notion_database_async(notion, database_id, dataframe, left_db_name=None):
    """비동기로 DataFrame의 행을 Notion 데이터베이스에 추가"""
    total_rows = len(dataframe)
    success_count = 0
    failed_rows = []
    
    # 데이터베이스 스키마 정보 가져오기
    db_info = notion.databases.retrieve(database_id=database_id)
    db_properties = db_info["properties"]
    
    # Notion API 토큰
    token = notion.auth
    
    async def add_row(session, index, row):
        # 행 데이터로 properties 구성
        properties = {}
        
        # Name 필드를 의미 있는 값으로 채우기
        name_value = ""
        # 1. 첫 번째 열 값을 기본으로 사용
        if len(dataframe.columns) > 0:
            first_col = dataframe.columns[0]
            if not first_col.endswith('_right'):  # 왼쪽 테이블 값 우선 사용
                name_value = str(row[first_col])
        
        # 2. 행 번호 추가
        name_value = f"{left_db_name or 'Row'} #{index+1}: {name_value}"
        
        # Name 속성 설정
        properties["Name"] = {
            "title": [{"text": {"content": name_value}}]
        }
        
        # 나머지 속성 처리
        for col in dataframe.columns:
            if col == "Name":  # Name은 이미 처리함
                continue
                
            value = row[col]
            
            # 컬럼 속성 타입에 따라 처리
            if col in db_properties:
                prop_type = db_properties[col]["type"]
                
                if prop_type == "title":
                    properties[col] = {
                        "title": [{"text": {"content": str(value)}}]
                    }
                elif prop_type == "rich_text":
                    properties[col] = {
                        "rich_text": [{"text": {"content": str(value)}}]
                    }
                elif prop_type == "number":
                    # 숫자로 변환 시도
                    try:
                        num_value = float(value) if value is not None and value != "" else None
                        properties[col] = {"number": num_value}
                    except (ValueError, TypeError):
                        properties[col] = {"number": None}
                elif prop_type == "date":
                    # 날짜 형식으로 변환
                    try:
                        if pd and isinstance(value, pd.Timestamp):
                            date_str = value.isoformat()
                            properties[col] = {"date": {"start": date_str}}
                        elif isinstance(value, datetime):
                            date_str = value.isoformat()
                            properties[col] = {"date": {"start": date_str}}
                        elif isinstance(value, str) and value:
                            # 문자열에서 날짜 파싱 시도
                            try:
                                date_obj = datetime.fromisoformat(value.replace('Z', '+00:00'))
                                properties[col] = {"date": {"start": date_obj.isoformat()}}
                            except:
                                properties[col] = {"date": None}
                        else:
                            properties[col] = {"date": None}
                    except Exception:
                        properties[col] = {"date": None}
                elif prop_type == "select":
                    # 선택 옵션
                    if value:
                        properties[col] = {"select": {"name": str(value)}}
                    else:
                        properties[col] = {"select": None}
                elif prop_type == "multi_select":
                    # 다중 선택 (문자열을 쉼표로 분리)
                    if isinstance(value, str) and value:
                        options = [{"name": option.strip()} for option in value.split(',')]
                        properties[col] = {"multi_select": options}
                    else:
                        properties[col] = {"multi_select": []}
                elif prop_type == "checkbox":
                    # 불리언 값
                    bool_value = bool(value) if value is not None else False
                    properties[col] = {"checkbox": bool_value}
                else:
                    # 기타 타입은 텍스트로 변환
                    properties[col] = {
                        "rich_text": [{"text": {"content": str(value) if value is not None else ""}}]
                    }
        
        try:
            async with session.post(
                "https://api.notion.com/v1/pages",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Notion-Version": "2022-06-28"  # 최신 버전으로 업데이트 필요할 수 있음
                },
                json={
                    "parent": {"database_id": database_id},
                    "properties": properties
                }
            ) as response:
                if response.status == 200:
                    nonlocal success_count
                    success_count += 1
                else:
                    nonlocal failed_rows
                    failed_rows.append(index)
                    resp_text = await response.text()
                    print(f"오류 (행 {index}): {resp_text}")
        except Exception as e:
            failed_rows.append(index)
            print(f"예외 발생 (행 {index}): {str(e)}")
    
    # 동시 요청 수 제한 (Notion API 제한 고려)
    semaphore = asyncio.Semaphore(5)  # 최대 5개 동시 요청
    
    async def bounded_add_row(session, index, row):
        async with semaphore:
            await add_row(session, index, row)
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for idx, row in dataframe.iterrows():
            task = asyncio.ensure_future(bounded_add_row(session, idx, row))
            tasks.append(task)
        
        # 진행 상황 표시
        for f in asyncio.as_completed(tasks):
            await f
    
    return success_count, total_rows, failed_rows