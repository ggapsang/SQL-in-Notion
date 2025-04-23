import streamlit as st
import pandas as pd
from utils import get_database_rows, extract_text_value, get_dict_from_row, load_database_info
from datetime import datetime

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

def main(notion):
    """메인 실행 함수: 프론트엔드에서 설정된 값으로 JOIN 수행"""
    try:
        # 세션 상태에서 필요한 값들 가져오기
        left_db_id = st.session_state.left_db_label[1]
        right_db_id = st.session_state.right_db_label[1]
        left_db_name = st.session_state.left_db_label[0]
        right_db_name = st.session_state.right_db_label[0]
        
        # 데이터베이스 정보 로드
        left_db, left_columns_types = load_database_info(notion, left_db_id)
        right_db, right_columns_types = load_database_info(notion, right_db_id)
        
        # 데이터베이스 행 가져오기
        left_db_rows = get_database_rows(notion, left_db_id)
        right_db_rows = get_database_rows(notion, right_db_id)
        
        # DataFrame 변환
        left_columns = list(left_columns_types.keys())
        right_columns = list(right_columns_types.keys())
        
        left_df = notion_to_dataframe(left_columns, left_db_rows)
        right_df = notion_to_dataframe(right_columns, right_db_rows)
        
        # 필터 적용
        if hasattr(st.session_state, 'left_filters'):
            left_df = apply_filter(left_df, st.session_state.left_filters, left_columns_types)
        
        if hasattr(st.session_state, 'right_filters'):
            right_df = apply_filter(right_df, st.session_state.right_filters, right_columns_types)
        
        # 조인 조건 가져오기
        join_conditions = []
        for i in range(st.session_state.join_condition_count):
            left_col = st.session_state[f"join_left_{i}"]
            right_col = st.session_state[f"join_right_{i}"]
            join_conditions.append((left_col, right_col))
        
        # INNER JOIN 수행
        result_df = perform_inner_join(left_df, right_df, join_conditions)
        
        if result_df is not None:
            # 결과 표시
            st.subheader("📊 INNER JOIN 결과")
            st.dataframe(result_df)
            st.success(f"총 {len(result_df)}개의 행이 조인되었습니다.")
            
            # 선택된 열만 보여주기
            if hasattr(st.session_state, 'left_columns') and hasattr(st.session_state, 'right_columns'):
                selected_left_cols = st.session_state.left_columns
                selected_right_cols = st.session_state.right_columns
                
                # 중복 열 이름 처리
                columns_to_show = []
                for col in selected_left_cols:
                    if col in result_df.columns:
                        columns_to_show.append(col)
                
                for col in selected_right_cols:
                    # JOIN에서 생성된 접미사 처리
                    if col + '_right' in result_df.columns:
                        columns_to_show.append(col + '_right')
                    elif col in result_df.columns and col not in selected_left_cols:
                        columns_to_show.append(col)
                
                if columns_to_show:
                    st.subheader("🔎 선택한 열만 표시")
                    st.dataframe(result_df[columns_to_show])
            
            # Notion에 결과 저장 옵션
            if st.button("📋 Notion에 결과 저장"):
                result_name = f"{left_db_name}_{right_db_name}_JOIN_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # 여기서는 단순화를 위해 현재 사용자의 첫 번째 페이지 ID를 사용
                # 실제 구현에서는 사용자가 저장할 페이지를 선택할 수 있게 해야 함
                user_pages = notion.search(filter={"property": "object", "value": "page"})["results"]
                if user_pages:
                    parent_page_id = user_pages[0]["id"]
                    
                    # 결과를 저장할 새 데이터베이스 생성
                    new_db_id = create_notion_database(notion, parent_page_id, result_name, result_df.columns)
                    
                    if new_db_id:
                        # 행 추가
                        success_count, total_count = add_rows_to_notion_database(notion, new_db_id, result_df)
                        st.success(f"{success_count}/{total_count} 행이 성공적으로 저장되었습니다!")
                else:
                    st.error("접근 가능한 페이지가 없습니다.")
        else:
            st.warning("JOIN 결과가 없습니다. 조건을 확인해주세요.")
    
    except Exception as e:
        st.error(f"JOIN 실행 중 오류 발생: {e}")
        st.exception(e)