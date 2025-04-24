import streamlit as st
from notion_client import Client
from datetime import datetime, timedelta
from utils import format_database_id, get_user_databases, get_database_rows, get_database_columns, extract_text_value, load_database_info
from main import main
import requests
import base64

# OAuth 인증 처리
CLIENT_ID = "1dfd872b-594c-8064-88b2-00370275a0d4"
CLIENT_SECRET = "secret_K7Fz7JikGMDqEmLlw1I4dfRrpj2gAU4izaUuEOmMKHr"
REDIRECT_URI = "https://sql-in-notion.streamlit.app/"

# 인증되지 않은 경우 → 인증 유도
if "access_token" not in st.session_state:
    code = st.query_params.get("code")

    if code is None:
        st.title("🔐 Notion 계정 연결이 필요합니다")
        #auth_url = r"https://api.notion.com/v1/oauth/authorize?client_id=1dcd872b-594c-80b7-9644-0037a0db3ca0&response_type=code&owner=user&redirect_uri=https%3A%2F%2Fnotiondbformula-nve9ydzj3dxkbgswaj392v.streamlit.app%2F"
        auth_url = f"https://api.notion.com/v1/oauth/authorize?client_id={CLIENT_ID}&response_type=code&owner=user&redirect_uri={REDIRECT_URI}"
        st.markdown(f"[👉 Notion 계정 연결하기]({auth_url})")
        st.stop()

    # access_token 요청
    auth_token = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    
    response = requests.post(
        "https://api.notion.com/v1/oauth/token",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_token}"
        },
        json={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI
        }
    )

    if response.status_code != 200:
        st.error("❌ 인증 토큰 요청 실패")
        st.text(response.text)
        st.stop()

    token_data = response.json()
    st.session_state.access_token = token_data["access_token"]

# Notion 클라이언트 생성 (세션에서 토큰 사용)
notion = Client(auth=st.session_state.access_token)

SAMPLE_PRODUCT_DB_ID = "1ddc9e591278815a8c0ac7e88daf78d1"
SAMPLE_ORDER_DB_ID = "1ddc9e59127881eca812cf3238d176bb"

product_db_id = format_database_id(SAMPLE_PRODUCT_DB_ID)
order_db_id = format_database_id(SAMPLE_ORDER_DB_ID)

product_db, product_columns_types = load_database_info(notion, product_db_id)
order_db, order_columns_types = load_database_info(notion, order_db_id)

# 칼럼 타입에 따른 필터 옵션 정의
def get_filter_options(column_type):
    if column_type in ["title", "rich_text"]:
        return ["equals", "contains", "starts_with", "ends_with", "is_empty", "is_not_empty"]
    elif column_type == "number":
        return ["equals", "does_not_equal", "greater_than", "less_than", "greater_than_or_equal_to", "less_than_or_equal_to", "is_empty", "is_not_empty"]
    elif column_type == "select":
        return ["equals", "does_not_equal", "is_empty", "is_not_empty"]
    elif column_type == "multi_select":
        return ["contains", "does_not_contain", "is_empty", "is_not_empty"]
    elif column_type == "date":
        return ["equals", "before", "after", "on_or_before", "on_or_after", "this_week", "past_week", "past_month", "past_year", "is_empty", "is_not_empty"]
    elif column_type == "checkbox":
        return ["equals"]
    else:
        return ["equals", "is_empty", "is_not_empty"]  # 기본 옵션

# 필터 값 UI 렌더링
def render_filter_value_input(column_type, operator, key):
    if column_type in ["title", "rich_text", "url", "email", "phone_number"]:
        return st.text_input("값", key=f"{key}_value", label_visibility="visible")
    elif column_type == "number":
        return st.number_input("값", key=f"{key}_value", step=0.1, label_visibility="visible")
    elif column_type == "select":
        # 실제 구현에서는 해당 select 옵션 목록을 가져와야 함
        options = ["옵션1", "옵션2", "옵션3"]  # 예시
        return st.selectbox("값", options, key=f"{key}_value", label_visibility="visible")
    elif column_type == "multi_select":
        # 실제 구현에서는 해당 multi_select 옵션 목록을 가져와야 함
        options = ["옵션1", "옵션2", "옵션3"]  # 예시
        return st.multiselect("값", options, key=f"{key}_value", label_visibility="visible")
    elif column_type == "date":
        if operator in ["before", "after", "on_or_before", "on_or_after", "equals"]:
            return st.date_input("날짜", key=f"{key}_value", label_visibility="visible")
        else:
            return None  # this_week, past_week 등은 값 입력 불필요
    elif column_type == "checkbox":
        return st.checkbox("참/거짓", key=f"{key}_value")
    else:
        return st.text_input("값", key=f"{key}_value", label_visibility="visible")

# 필터 조건 UI 컴포넌트
def render_filter_condition(db_name, columns_types, index, key_prefix):
    st.markdown(f"##### 조건 {index+1}")
    
    # 한 행을 3개 열로 분할
    col1, col2, col3 = st.columns([3, 2, 3])
    
    # 칼럼 선택 (첫 번째 열)
    with col1:
        column = st.selectbox(
            f"{db_name} 칼럼", 
            options=list(columns_types.keys()), 
            key=f"{key_prefix}_column_{index}"
        )
    
    # 선택된 칼럼의 타입
    column_type = columns_types.get(column, "text")
    
    # 연산자 선택 (두 번째 열)
    with col2:
        operators = get_filter_options(column_type)
        operator = st.selectbox(
            "연산자", 
            options=operators, 
            key=f"{key_prefix}_operator_{index}"
        )
    
    # 필터 값 입력 (세 번째 열)
    with col3:
        if operator not in ["is_empty", "is_not_empty", "this_week", "past_week", "past_month", "past_year"]:
            value = render_filter_value_input(column_type, operator, f"{key_prefix}_{index}")
        else:
            value = None
            st.write("값 입력 불필요")
        
    return {
        "column": column,
        "operator": operator,
        "value": value,
        "type": column_type
    }


### 페이지 설정 ###
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

if "join_condition_count" not in st.session_state:
    st.session_state.join_condition_count = 1

if "left_filter_count" not in st.session_state:
    st.session_state.left_filter_count = 0

if "right_filter_count" not in st.session_state:
    st.session_state.right_filter_count = 0

# SELECT section
st.markdown("# 🔍 SELECT")
with st.form("select_form"):
    # 키 이름을 변경 (_select 접미사 추가)
    left_columns = st.multiselect(f"{left_db_nm} 칼럼", options=product_columns_types.keys(), 
                               default=list(product_columns_types.keys()), key="left_columns_select")
    right_columns = st.multiselect(f"{right_db_nm} 칼럼", options=order_columns_types.keys(), 
                                default=list(order_columns_types.keys()), key="right_columns_select")
    select_submitted = st.form_submit_button("칼럼 선택 저장")
    
    if select_submitted:
        # 다른 키 이름으로 저장 (_selected 접미사 사용)
        st.session_state.left_columns_selected = left_columns
        st.session_state.right_columns_selected = right_columns
        st.success("칼럼 선택이 저장되었습니다.")

st.markdown("---")

# FROM section
st.markdown("# 📚 FROM")
st.markdown(f"### {left_db_nm}")

def add_left_filter():
    st.session_state.left_filter_count += 1

## LEFT WHERE 필터 조건 렌더링
left_filters = []
for i in range(st.session_state.left_filter_count):
    filter_condition = render_filter_condition(left_db_nm, product_columns_types, i, "left_filter")
    left_filters.append(filter_condition)
st.button("➕ 필터 추가", on_click=add_left_filter, key="add_left_filter")
st.markdown("---")

# INNER JOIN section
st.markdown("# 🔗 INNER JOIN")
st.markdown(f"### {right_db_nm}")

def add_right_filter():
    st.session_state.right_filter_count += 1

## RIGHT WHERE 필터 조건 렌더링
right_filters = []
for i in range(st.session_state.right_filter_count):
    filter_condition = render_filter_condition(right_db_nm, order_columns_types, i, "right_filter")
    right_filters.append(filter_condition)

st.button("➕ RIGHT 필터 추가", on_click=add_right_filter, key="add_right_filter")
st.markdown("---")


# ON section
def add_join_condition():
    st.session_state.join_condition_count += 1

st.markdown("## 🧩 ON")
st.markdown(f"🔄 {left_db_nm}과 {right_db_nm} 사이의 키 칼럼")

join_conditions = []
for i in range(st.session_state.join_condition_count):
    col1, col2, col3 = st.columns([4, 1, 4])
    with col1:
        left_col = st.selectbox(f"{left_db_nm}", product_columns_types.keys(), key=f"join_left_{i}")
    with col2:
        st.markdown("#### =")
    with col3:
        right_col = st.selectbox(f"{right_db_nm}", order_columns_types.keys(), key=f"join_right_{i}")
    join_conditions.append((left_col, right_col))

st.button("➕ JOIN 조건 추가", on_click=add_join_condition, key="add_join_condition")
st.markdown("---")


# JOIN 결과를 저장할 Notion 페이지 선택 section
st.markdown("## 📋 결과 저장 설정")

# 사용자 페이지 목록 가져오기
user_pages = notion.search(filter={"property": "object", "value": "page"})["results"]
page_options = []

for i, page in enumerate(user_pages):
    # 페이지 제목 추출 (title 속성이 있는 경우)
    if "properties" in page and "title" in page["properties"] and page["properties"]["title"]["title"]:
        page_title = page["properties"]["title"]["title"][0]["plain_text"]
    else:
        page_title = f"Untitled Page {i+1}"
    
    page_options.append((page_title, page["id"]))

# 페이지 선택 및 결과 DB 이름 입력
if page_options:
    st.session_state.save_page = st.selectbox(
        "결과를 저장할 Notion 페이지", 
        options=page_options, 
        format_func=lambda x: x[0],
        key="save_page_select"
    )
    
    # 기본 이름 설정 - 현재 시간 포함
    default_name = f"{left_db_nm}_{right_db_nm}_JOIN_{datetime.now().strftime('%Y%m%d')}"
    st.session_state.save_db_name = st.text_input(
        "저장할 데이터베이스 이름", 
        value=default_name,
        key="save_db_name_input"
    )
else:
    st.warning("저장 가능한 Notion 페이지가 없습니다.")

st.markdown("---")

# Join
if st.button("🚀 INNER JOIN 실행", key="execute_join"):

    st.write("#### LEFT 필터:")
    for i, filter_condition in enumerate(left_filters):
        st.write(f"{i+1}. {filter_condition['column']} {filter_condition['operator']} {filter_condition['value']}")
    
    st.write("#### RIGHT 필터")
    for i, filter_condition in enumerate(right_filters):
        st.write(f"{i+1}. {filter_condition['column']} {filter_condition['operator']} {filter_condition['value']}")
    
    st.write("#### JOIN:")
    for i, (left_col, right_col) in enumerate(join_conditions):
        st.write(f"{i+1}. {left_db_nm}.{left_col} = {right_db_nm}.{right_col}")
    
    # 세션 상태에 필터 조건 저장
    st.session_state.left_filters = left_filters
    st.session_state.right_filters = right_filters

    main(notion)