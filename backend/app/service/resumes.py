from pathlib import Path
from io import BytesIO

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from pypdf import PdfReader
from docx import Document

from app.core.config import settings
from app.core.logging import get_logger
from app.models.resumes import Resume
from sqlalchemy import select
from openai import AsyncOpenAI
from app.schemas.resumes import ResumeProfile

logger = get_logger()
MAX_FILE_BYTES=10*1024*1024
MAX_TEXT_CHARS=20_000

ALLOWED = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

EXTRACT_PROFILE_PROMPT="""
你是一个专业的简历分析专家.
你从简历原文中提取结构化信息,只能返回json格式。
只使用原文中出现的内容，不要编造经历、公司、时间或技能。
原文没有的字段用 null 或空数组。
"""

class ResumeFileInvalidError(Exception):
    pass

def extract_text(content:bytes,shuffix:str)->str:
    if shuffix == ".pdf":
        reader = PdfReader(BytesIO(content))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    elif shuffix == ".docx":
        doc = Document(BytesIO(content))
        return "\n".join(paragraph.text for paragraph in doc.paragraphs)
    else:
        raise ResumeFileInvalidError(f"Unsupported file type: {shuffix}")


async def upload_resume_service(
    file:UploadFile,
    user_id:int,
    session:AsyncSession,
    llm_client:AsyncOpenAI,
)->Resume:
    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED:
        raise ResumeFileInvalidError(f"Unsupported file type: {suffix}")
    
    content = await file.read()
    if len(content) > MAX_FILE_BYTES:
        raise ResumeFileInvalidError(f"文件过大: {filename}")
    if not content:
        raise ResumeFileInvalidError(f"文件为空: {filename}")
    
    resume= Resume(
        original_filename=filename[:255],
        media_type=ALLOWED[suffix],
        status="failed",
        raw_text=None,
        error_detail=None,
        storage_path="pending",
        profile=None,
        user_id=user_id
    )
    session.add(resume)
    await session.flush()

    relative = f"{user_id}/{resume.id}{suffix}"
    dest = Path(settings.resume_upload_dir) / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)
    resume.storage_path = relative.replace("\\", "/")

    try:
        text = extract_text(content,suffix).strip()
    except Exception:
        logger.exception("resume extract failed resume_id=%s", resume.id)
        resume.status = "failed"
        resume.error_detail = "无法解析该文件"
        await session.commit()
        return resume
    
    if not text:
        resume.status = "failed"
        resume.error_detail = "无法提取文本"
        await session.commit()
        return resume
    
    if len(text) > MAX_TEXT_CHARS:
        resume.status = "failed"
        resume.error_detail = "文本过长"
        await session.commit()
        return resume
    
    resume.raw_text = text
    resume.status = "ready"
    try:
        profile = await extract_profile_service(text,llm_client,settings.llm_model_light)
    except Exception:
        logger.exception("resume profile failed resume_id=%s", resume.id)
        resume.error_detail = "结构化失败"
        await session.commit()
        return resume
    resume.profile = profile.model_dump()
    resume.error_detail = None
    await session.commit()
    return resume

async def get_resumes_list_service(
    user_id:int,
    session:AsyncSession
)->list[Resume]:
    result=await session.execute(
        select(Resume).where(Resume.user_id == user_id).order_by(Resume.created_at.desc())
    )
    return list(result.scalars().all())

# 结构化解析简历
async def extract_profile_service(
    raw_text:str,
    llm_client:AsyncOpenAI,
    model:str,
)->ResumeProfile:
    completion = await llm_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": EXTRACT_PROFILE_PROMPT},
            {"role": "user", "content": raw_text},
        ],
        response_format={"type": "json_object"},
    )
    parsed = completion.choices[0].message.content
    if not parsed:
        raise ValueError("empty profile")
    return ResumeProfile.model_validate_json(parsed)

