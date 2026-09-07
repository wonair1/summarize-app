from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from bs4 import BeautifulSoup
from transformers import pipeline
import requests
import os
import psycopg2


app = FastAPI()

MODEL_PATH = "/models/t5-small"


class SummarizeRequest(BaseModel):
    url: str
    max_length: int = 150
    min_length: int = 40


summarizer = pipeline(
    task="summarization",
    model=MODEL_PATH,
    tokenizer=MODEL_PATH,
    framework="pt",
)


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "db"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "summarize"),
        user=os.getenv("DB_USER", "summarize"),
        password=os.getenv("DB_PASSWORD", "summarize_password"),
    )


def init_db():
    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS summaries (
                id SERIAL PRIMARY KEY,
                url TEXT NOT NULL,
                original_text TEXT,
                summary TEXT NOT NULL,
                model VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            ALTER TABLE summaries
            ADD COLUMN IF NOT EXISTS original_text TEXT
            """
        )

        connection.commit()
        cursor.close()

    finally:
        connection.close()


def extract_url(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=20,
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    paragraphs = [
        p.get_text(" ", strip=True)
        for p in soup.find_all("p")
    ]

    return "\n".join(paragraphs)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model": "t5-small",
    }


@app.post("/summarize")
def summarize(req: SummarizeRequest):
    try:

        # =====================================================
        # 기존 URL 확인
        # =====================================================

        connection = get_db_connection()

        try:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    id,
                    summary,
                    model,
                    created_at
                FROM summaries
                WHERE url = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (req.url,),
            )

            existing = cursor.fetchone()

            cursor.close()

        finally:
            connection.close()


        # =====================================================
        # 이미 존재하는 URL이면 기존 결과 반환
        # =====================================================

        if existing:

            return {
                "model": existing[2],
                "summary": existing[1],
                "cached": True,
                "summary_id": existing[0],
                "created_at": existing[3].isoformat(),
            }


        # =====================================================
        # 신규 URL → 원문 추출
        # =====================================================

        original_text = extract_url(req.url)

        if not original_text.strip():
            raise HTTPException(
                status_code=400,
                detail="본문을 추출할 수 없습니다.",
            )


        # =====================================================
        # T5 요약
        # =====================================================

        text = "summarize: " + original_text

        result = summarizer(
            text,
            max_length=req.max_length,
            min_length=req.min_length,
            truncation=True,
        )

        summary = result[0]["summary_text"]


        # =====================================================
        # DB 저장
        # =====================================================

        connection = get_db_connection()

        try:
            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO summaries
                    (url, original_text, summary, model)
                VALUES
                    (%s, %s, %s, %s)
                """,
                (
                    req.url,
                    original_text,
                    summary,
                    "t5-small",
                ),
            )

            connection.commit()
            cursor.close()

        finally:
            connection.close()


        # =====================================================
        # 신규 요약 결과
        # =====================================================

        return {
            "model": "t5-small",
            "summary": summary,
            "cached": False,
        }


    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@app.get("/summaries")
def get_summaries():

    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                url,
                original_text,
                summary,
                model,
                created_at
            FROM summaries
            ORDER BY id DESC
            """
        )

        rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "url": row[1],
                "original_text": row[2],
                "summary": row[3],
                "model": row[4],
                "created_at": row[5].isoformat(),
            }
            for row in rows
        ]

    finally:
        cursor.close()
        connection.close()


@app.get("/summaries/search")
def search_summaries(q: str):

    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                url,
                original_text,
                summary,
                model,
                created_at
            FROM summaries
            WHERE url ILIKE %s
               OR original_text ILIKE %s
               OR summary ILIKE %s
            ORDER BY id DESC
            """,
            (
                f"%{q}%",
                f"%{q}%",
                f"%{q}%",
            ),
        )

        rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "url": row[1],
                "original_text": row[2],
                "summary": row[3],
                "model": row[4],
                "created_at": row[5].isoformat(),
            }
            for row in rows
        ]

    finally:
        cursor.close()
        connection.close()


@app.delete("/summaries/{summary_id}")
def delete_summary(summary_id: int):

    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM summaries
            WHERE id = %s
            RETURNING id
            """,
            (summary_id,),
        )

        deleted = cursor.fetchone()

        if deleted is None:
            raise HTTPException(
                status_code=404,
                detail="해당 기록을 찾을 수 없습니다.",
            )

        connection.commit()

        return {
            "message": "삭제되었습니다.",
            "id": deleted[0],
        }

    finally:
        cursor.close()
        connection.close()
