from fastapi import APIRouter, UploadFile, File, Request, status, HTTPException
from app.schemas.resumes import ResumeUploadResponse, ResumeGetResponse
from app.api.deps import CurrentUser
from app.service.resumes import upload_resume_service, ResumeFileInvalidError, get_resumes_list_service


router = APIRouter(prefix="/api/v1/resumes",tags=["resumes"])

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="上传简历",
    description="上传新简历",
)
async def upload_resume(
    current_user:CurrentUser,
    request:Request,
    file:UploadFile=File(...),
)->ResumeUploadResponse:
    async with request.app.state.mysql_session_factory() as session:
        try:
            resume = await upload_resume_service(file,current_user.id,session,request.app.state.llm_client,)
            return ResumeUploadResponse.model_validate(resume)
        except ResumeFileInvalidError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=str(e))


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="获取当前用户简历",
    description="获取当前用户简历列表",
)
async def get_resume(current_user:CurrentUser,request:Request)->list[ResumeGetResponse]:
    async with request.app.state.mysql_session_factory() as session:
        resumes = await get_resumes_list_service(current_user.id,session)
        return [ResumeGetResponse.model_validate(resume) for resume in resumes]




