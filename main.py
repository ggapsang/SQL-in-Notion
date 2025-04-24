import streamlit as st
import pandas as pd
from utils import get_database_rows, load_database_info, notion_to_dataframe, perform_inner_join, create_notion_database, add_rows_to_notion_database
from datetime import datetime

# main.py 수정 부분 - 저장 관련 코드 변경

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
            
            # Notion에 결과 자동 저장
            st.subheader("📋 Notion에 결과 저장")
            
            save_container = st.empty()
            
            try:
                # 세션 상태에서 미리 선택한 페이지와 DB 이름 가져오기
                if "save_page" in st.session_state and "save_db_name" in st.session_state:
                    save_container.info("Notion 데이터베이스에 결과 저장 중...")
                    
                    parent_page_id = st.session_state.save_page[1]  # 튜플의 두 번째 항목은 페이지 ID
                    result_name = st.session_state.save_db_name
                    
                    # 새 데이터베이스 생성
                    new_db_id = create_notion_database(
                        notion, 
                        parent_page_id, 
                        result_name, 
                        result_df.columns,
                        left_columns_types,
                        right_columns_types
                    )
                    
                    if new_db_id:
                        # 행 추가 (왼쪽 데이터베이스 이름을 함께 전달)
                        success_count, total_count = add_rows_to_notion_database(
                            notion, new_db_id, result_df, left_db_name
                        )
                        save_container.success(f"✅ {success_count}/{total_count} 행이 Notion 데이터베이스에 성공적으로 저장되었습니다!")
                        
                        # 생성된 DB로 이동할 수 있는 링크 제공
                        db_url = f"https://notion.so/{new_db_id.replace('-', '')}"
                        st.markdown(f"[새 데이터베이스 보기]({db_url})")
                    else:
                        save_container.error("데이터베이스 생성에 실패했습니다.")
                else:
                    st.error("저장할 페이지와 데이터베이스 이름 설정이 없습니다. JOIN 결과를 저장하려면 먼저 저장 설정을 확인해주세요.")
            except Exception as e:
                save_container.error(f"저장 중 오류 발생: {str(e)}")
                st.exception(e)
        else:
            st.warning("JOIN 결과가 없습니다. 조건을 확인해주세요.")
    
    except Exception as e:
        st.error(f"JOIN 실행 중 오류 발생: {e}")
        st.exception(e)