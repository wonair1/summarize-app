import os
import json
import requests
import streamlit as st
import streamlit.components.v1 as components


API_URL = os.getenv(
    "API_URL",
    "http://localhost:8000/summarize"
)

SUMMARIES_URL = API_URL.replace(
    "/summarize",
    "/summaries"
)

SEARCH_URL = API_URL.replace(
    "/summarize",
    "/summaries/search"
)


st.set_page_config(
    page_title="Hugging Face Summarizer"
)

st.title("Hugging Face 모델 기반 텍스트 요약")


# =========================================================
# 복사 버튼
# =========================================================

def copy_button(text, key):

    # JavaScript 문자열로 안전하게 변환
    safe_text = json.dumps(text)

    components.html(
        f"""
        <div style="
            width: 100%;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0;
            padding: 0;
        ">

            <button
                id="copy-btn-{key}"
                style="
                    width: 100%;
                    height: 32px;
                    padding: 0;
                    margin: 0;
                    border: 1px solid rgb(49, 51, 63);
                    border-radius: 6px;
                    background-color: white;
                    color: rgb(49, 51, 63);
                    cursor: pointer;
                    font-size: 14px;
                    font-weight: 400;
                    transition: 0.15s;
                "
            >
                📋
            </button>

        </div>

        <script>

        const button = document.getElementById(
            "copy-btn-{key}"
        );

        const text = {safe_text};


        button.addEventListener("click", async function() {{

            let copied = false;


            // -------------------------------------------------
            // 1. Clipboard API 시도
            // -------------------------------------------------

            try {{

                if (
                    navigator.clipboard &&
                    window.isSecureContext
                ) {{

                    await navigator.clipboard.writeText(text);

                    copied = true;

                }}

            }} catch (error) {{

                copied = false;

            }}


            // -------------------------------------------------
            // 2. Clipboard API가 막혀 있으면 fallback
            // -------------------------------------------------

            if (!copied) {{

                try {{

                    const textarea =
                        document.createElement("textarea");

                    textarea.value = text;

                    textarea.style.position = "fixed";
                    textarea.style.left = "-9999px";
                    textarea.style.top = "0";
                    textarea.style.opacity = "0";

                    document.body.appendChild(textarea);

                    textarea.focus();
                    textarea.select();

                    copied = document.execCommand("copy");

                    textarea.remove();

                }} catch (error) {{

                    copied = false;

                }}

            }}


            // -------------------------------------------------
            // 3. 버튼에 결과 표시
            // -------------------------------------------------

            if (copied) {{

                button.innerText = "✅";

                button.style.backgroundColor =
                    "rgb(240, 253, 244)";

                button.style.borderColor =
                    "rgb(34, 197, 94)";

                button.style.color =
                    "rgb(22, 101, 52)";


                setTimeout(function() {{

                    button.innerText = "📋";

                    button.style.backgroundColor = "white";

                    button.style.borderColor =
                        "rgb(49, 51, 63)";

                    button.style.color =
                        "rgb(49, 51, 63)";

                }}, 1200);


            }} else {{

                button.innerText = "❌";

                button.style.backgroundColor =
                    "rgb(254, 242, 242)";

                button.style.borderColor =
                    "rgb(239, 68, 68)";

                button.style.color =
                    "rgb(153, 27, 27)";


                setTimeout(function() {{

                    button.innerText = "📋";

                    button.style.backgroundColor = "white";

                    button.style.borderColor =
                        "rgb(49, 51, 63)";

                    button.style.color =
                        "rgb(49, 51, 63)";

                }}, 1200);

            }}

        }});

        </script>
        """,
        height=40,
    )


# =========================================================
# 삭제 확인 팝업
# =========================================================

@st.dialog("삭제 확인")
def confirm_delete(summary_id):

    st.write("이 요약 기록을 삭제하시겠습니까?")

    st.caption(
        f"기록 번호: #{summary_id}"
    )

    col1, col2 = st.columns(2)


    with col1:

        if st.button(
            "취소",
            use_container_width=True
        ):

            st.rerun()


    with col2:

        if st.button(
            "삭제",
            type="primary",
            use_container_width=True
        ):

            try:

                response = requests.delete(
                    f"{SUMMARIES_URL}/{summary_id}",
                    timeout=10
                )

                response.raise_for_status()

                st.rerun()

            except requests.exceptions.RequestException as e:

                st.error(
                    f"삭제 중 오류가 발생했습니다: {e}"
                )


# =========================================================
# 탭
# =========================================================

tab1, tab2 = st.tabs(
    [
        "📝 텍스트 요약",
        "🗄️ DB 기록"
    ]
)


# =========================================================
# 텍스트 요약
# =========================================================

with tab1:

    st.subheader("기사 URL 요약")


    url = st.text_input(
        "기사 URL",
        placeholder="https://..."
    )


    max_length = st.slider(
        "최대 길이",
        50,
        300,
        150
    )


    min_length = st.slider(
        "최소 길이",
        20,
        100,
        40
    )


    if st.button("요약하기"):

        if not url:

            st.warning("URL을 입력하세요.")

        else:

            with st.spinner("요약 중입니다..."):

                try:

                    response = requests.post(
                        API_URL,
                        json={
                            "url": url,
                            "max_length": max_length,
                            "min_length": min_length
                        },
                        timeout=120
                    )

                    response.raise_for_status()

                    result = response.json()

                    if result.get("cached"):
                        st.info("♻️ 이미 요약된 URL입니다. 기존 DB 기록을 사용했습니다.")
                    else:
                        st.success("요약 완료")

                    st.markdown("### 사용 모델")

                    st.write(
                        result["model"]
                    )


                    st.markdown("### 요약 결과")

                    st.write(
                        result["summary"]
                    )


                    copy_button(
                        result["summary"],
                        key="copy_summary"
                    )


                except requests.exceptions.RequestException as e:

                    st.error(
                        f"Backend 서버에 연결할 수 없습니다: {e}"
                    )


                except Exception as e:

                    st.error(
                        f"오류가 발생했습니다: {e}"
                    )


# =========================================================
# DB 기록
# =========================================================

with tab2:

    st.subheader("요약 기록")


    col1, col2 = st.columns(
        [4, 1]
    )


    with col1:

        search_query = st.text_input(
            "검색",
            placeholder="URL, 원문 또는 요약 내용 검색",
            label_visibility="collapsed"
        )


    with col2:

        search_button = st.button(
            "검색",
            use_container_width=True
        )


    try:

        # -----------------------------------------------------
        # 검색
        # -----------------------------------------------------

        if (
            search_button
            and search_query.strip()
        ):

            response = requests.get(
                SEARCH_URL,
                params={
                    "q": search_query.strip()
                },
                timeout=10
            )


        # -----------------------------------------------------
        # 전체 목록
        # -----------------------------------------------------

        else:

            response = requests.get(
                SUMMARIES_URL,
                timeout=10
            )


        response.raise_for_status()

        summaries = response.json()


        # -----------------------------------------------------
        # 검색 결과 개수
        # -----------------------------------------------------

        if (
            search_button
            and search_query.strip()
        ):

            st.caption(
                f"'{search_query.strip()}' "
                f"검색 결과: {len(summaries)}개"
            )


        # -----------------------------------------------------
        # 결과 없음
        # -----------------------------------------------------

        if not summaries:

            st.info(
                "저장된 요약 기록이 없습니다."
            )


        # -----------------------------------------------------
        # 기록 출력
        # -----------------------------------------------------

        else:

            for item in summaries:

                # =================================================
                # 기록 / 복사 / 삭제
                # =================================================

                col_record, col_copy, col_delete = st.columns(
                    [8, 1, 1],
                    gap="small"
                )


                # -------------------------------------------------
                # Expander
                # -------------------------------------------------

                with col_record:

                    with st.expander(
                        f"#{item['id']} | "
                        f"{item['model']} | "
                        f"{item['created_at']}"
                    ):

                        st.markdown("**URL**")

                        st.write(
                            item["url"]
                        )


                        st.markdown("**모델**")

                        st.write(
                            item["model"]
                        )


                        st.markdown("**생성 시간**")

                        st.write(
                            item["created_at"]
                        )


                        st.markdown("**원문**")


                        if item.get("original_text"):

                            st.text_area(
                                "원문",
                                item["original_text"],
                                height=300,
                                disabled=True,
                                label_visibility="collapsed"
                            )

                        else:

                            st.caption(
                                "이 기록에는 저장된 원문이 없습니다."
                            )


                        st.markdown("**요약**")

                        st.write(
                            item["summary"]
                        )


                # -------------------------------------------------
                # 복사 버튼
                # -------------------------------------------------

                with col_copy:

                    copy_button(
                        item["summary"],
                        key=f"copy_{item['id']}"
                    )


                # -------------------------------------------------
                # 삭제 버튼
                # -------------------------------------------------

                with col_delete:

                    if st.button(
                        "🗑️",
                        key=f"delete_{item['id']}",
                        help="이 기록 삭제",
                        use_container_width=True
                    ):

                        confirm_delete(
                            item["id"]
                        )


                st.divider()


    except requests.exceptions.RequestException as e:

        st.error(
            f"Backend 서버에 연결할 수 없습니다: {e}"
        )


    except Exception as e:

        st.error(
            f"오류가 발생했습니다: {e}"
        )


    # ---------------------------------------------------------
    # 새로고침
    # ---------------------------------------------------------

    if st.button("새로고침"):

        st.rerun()
