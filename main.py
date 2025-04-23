import streamlit as st
import pandas as pd
from utils import get_database_rows, load_database_info, notion_to_dataframe, perform_inner_join, create_notion_database, add_rows_to_notion_database
from datetime import datetime

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
        if hasattr(st.session_state, 'left_columns_selected') and hasattr(st.session_state, 'right_columns_selected'):
            selected_left_cols = st.session_state.left_columns_selected
            selected_right_cols = st.session_state.right_columns_selected
        
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