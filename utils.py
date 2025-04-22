def format_database_id(raw_id: str) -> str:
    """
    하이픈 없는 Notion 데이터베이스 ID를 하이픈 포함된 형식으로 변환
    Args:
        raw_id (str): 하이픈이 없는 원시 ID 문자열
    Returns:
        str: 하이픈이 삽입된 정규화된 ID
    """
    return f"{raw_id[:8]}-{raw_id[8:12]}-{raw_id[12:16]}-{raw_id[16:20]}-{raw_id[20:]}"

def get_user_databases(notion):
    """
    현재 사용자가 접근 가능한 Notion 데이터베이스 목록을 가져오기
    Args:
        notion (Client): 인증된 Notion API 클라이언트 객체
    Returns:
        list of tuple: (데이터베이스 이름, 데이터베이스 ID) 리스트
    """
    dbs = notion.search(filter={"property": "object", "value": "database"})["results"]
    return [(db["title"][0]["plain_text"] if db["title"] else "[제목 없음]", db["id"]) for db in dbs]


def get_database_rows(notion, database_id):
    """
    지정한 Notion 데이터베이스의 모든 row를 반환
    Args:
        notion (Client): 인증된 Notion API 클라이언트
        database_id (str): 데이터베이스 ID
    Returns:
        list: row 객체들의 리스트
    """
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
    """
    Notion 데이터베이스의 컬럼(속성) 이름 목록을 가져옴
    Args:
        notion (Client): 인증된 Notion API 클라이언트
        database_id (str): 대상 데이터베이스 ID
    Returns:
        list: 속성 이름들 (문자열 리스트)
    """
    response = notion.databases.retrieve(database_id=database_id)
    return list(response.get("properties", {}).keys())


def extract_text_value(prop):
    """
    Notion 속성(property) 객체에서 사람이 읽을 수 있는 텍스트 값을 추출
    Args:
        prop (dict): Notion 속성 객체
    Returns:
        str or int: 속성의 텍스트 값 또는 숫자 값. 지원되지 않는 타입일 경우 안내 메시지 반환
    """
    try:
        typ = prop["type"]
        if typ == "title":
            return prop["title"][0]["plain_text"] if prop["title"] else ""
        elif typ == "rich_text":
            return prop["rich_text"][0]["text"]["plain_text"] if prop["rich_text"] else ""
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
    """
    날짜 속성에서 시작일과 종료일을 추출
    Args:
        prop (dict): 날짜 타입의 Notion 속성 객체
    Returns:
        tuple: (시작일, 종료일). 종료일이 없으면 시작일을 반환함.
    """
    try:
        if prop["type"] != "date":
            return None, None
        date_info = prop["date"]
        return date_info.get("start"), date_info.get("end", date_info.get("start"))
    except:
        return None, None
