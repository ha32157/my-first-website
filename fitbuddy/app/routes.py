from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Form, Header, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_all_users, get_db, get_latest_plan, get_user, save_plan, save_user, update_plan
from .gemini_service import GeminiService
from .schemas import FeedbackRequest, HealthResponse, PlanResponse, UserInput

router = APIRouter()
templates = Jinja2Templates(directory="templates")
settings = get_settings()
ai = GeminiService(settings)


def _context(**kwargs):
    return kwargs


def _admin_authorized(cookie: str | None, header: str | None) -> bool:
    return (cookie and cookie == settings.admin_key) or (header and header == settings.admin_key)


def _plan_response(user, plan, updated: bool = False) -> PlanResponse:
    return PlanResponse(
        user_id=user.user_id,
        name=user.name,
        age=user.age,
        weight_kg=user.weight_kg,
        goal=user.goal,
        intensity=user.intensity,
        workout_plan=plan.updated_plan if updated and plan.updated_plan else plan.original_plan,
        nutrition_tip=plan.nutrition_tip,
        updated=updated and bool(plan.updated_plan),
    )


@router.get("/", response_class=HTMLResponse, name="home")
def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context=_context())


@router.post("/generate-workout", response_class=HTMLResponse)
def generate_workout_form(
    request: Request,
    user_id: str = Form(...),
    name: str = Form(...),
    age: int = Form(...),
    weight_kg: float = Form(...),
    goal: str = Form(...),
    intensity: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        user_input = UserInput(user_id=user_id, name=name, age=age, weight_kg=weight_kg, goal=goal, intensity=intensity)
        user = save_user(db, **user_input.model_dump())
        workout_plan = ai.generate_workout(user_input)
        nutrition_tip = ai.generate_tip(user_input.goal)
        plan = save_plan(db, user=user, original_plan=workout_plan, nutrition_tip=nutrition_tip)
        return templates.TemplateResponse(request=request, name="result.html", context={"user": user, "plan": plan, "ai_demo": ai.demo_mode, "message": None})
    except Exception as exc:
        return templates.TemplateResponse(request=request, name="index.html", status_code=400, context={"error": str(exc)})


@router.post("/submit-feedback", response_class=HTMLResponse)
def submit_feedback_form(
    request: Request,
    user_id: str = Form(...),
    feedback: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_user(db, user_id)
    if user is None:
        return templates.TemplateResponse(request=request, name="index.html", status_code=404, context={"error": "User ID was not found."})
    try:
        feedback_request = FeedbackRequest(feedback=feedback)
        plan = get_latest_plan(db, user)
        if plan is None:
            raise ValueError("No workout plan exists for this user yet.")
        profile = UserInput(user_id=user.user_id, name=user.name, age=user.age, weight_kg=user.weight_kg, goal=user.goal, intensity=user.intensity)
        revised = ai.update_workout(profile, plan.original_plan, feedback_request.feedback)
        tip = ai.generate_tip(user.goal)
        plan = update_plan(db, plan=plan, updated_plan=revised, feedback=feedback_request.feedback, nutrition_tip=tip)
        return templates.TemplateResponse(request=request, name="result.html", context={"user": user, "plan": plan, "ai_demo": ai.demo_mode, "message": "Your plan was updated successfully."})
    except Exception as exc:
        return templates.TemplateResponse(request=request, name="result.html", status_code=400, context={"user": user, "plan": plan if 'plan' in locals() else None, "ai_demo": ai.demo_mode, "message": None, "error": str(exc)})


@router.get("/view-all-users", response_class=HTMLResponse)
def view_all_users(
    request: Request,
    admin_key: str | None = Cookie(default=None),
    x_admin_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    if not _admin_authorized(admin_key, x_admin_key):
        return templates.TemplateResponse(request=request, name="admin_login.html", status_code=401, context={"error": None})
    users = get_all_users(db)
    rows = [{"user": user, "plan": get_latest_plan(db, user)} for user in users]
    return templates.TemplateResponse(request=request, name="all_users.html", context={"rows": rows})


@router.post("/admin/login")
def admin_login(request: Request, key: str = Form(...)):
    if key != settings.admin_key:
        return templates.TemplateResponse(request=request, name="admin_login.html", status_code=401, context={"error": "Invalid admin key."})
    response = RedirectResponse(url="/view-all-users", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie("admin_key", key, httponly=True, samesite="lax", secure=False, max_age=3600)
    return response


@router.post("/admin/logout")
def admin_logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("admin_key")
    return response


@router.get("/api/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)):
    try:
        db.execute(__import__('sqlalchemy').text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    return HealthResponse(status="ok" if db_status == "ok" else "degraded", database=db_status, ai_mode="demo" if ai.demo_mode else "gemini")


@router.post("/api/workouts", response_model=PlanResponse, status_code=201)
def api_generate_workout(payload: UserInput, db: Session = Depends(get_db)):
    user = save_user(db, **payload.model_dump())
    workout_plan = ai.generate_workout(payload)
    nutrition_tip = ai.generate_tip(payload.goal)
    plan = save_plan(db, user=user, original_plan=workout_plan, nutrition_tip=nutrition_tip)
    return _plan_response(user, plan)


@router.post("/api/workouts/{user_id}/feedback", response_model=PlanResponse)
def api_submit_feedback(user_id: str, payload: FeedbackRequest, db: Session = Depends(get_db)):
    user = get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User ID was not found")
    plan = get_latest_plan(db, user)
    if plan is None:
        raise HTTPException(status_code=404, detail="No workout plan exists for this user")
    profile = UserInput(user_id=user.user_id, name=user.name, age=user.age, weight_kg=user.weight_kg, goal=user.goal, intensity=user.intensity)
    revised = ai.update_workout(profile, plan.original_plan, payload.feedback)
    tip = ai.generate_tip(user.goal)
    plan = update_plan(db, plan=plan, updated_plan=revised, feedback=payload.feedback, nutrition_tip=tip)
    return _plan_response(user, plan, updated=True)


@router.get("/api/users/{user_id}", response_model=PlanResponse)
def api_get_user(user_id: str, db: Session = Depends(get_db)):
    user = get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User ID was not found")
    plan = get_latest_plan(db, user)
    if plan is None:
        raise HTTPException(status_code=404, detail="No workout plan exists for this user")
    return _plan_response(user, plan, updated=bool(plan.updated_plan))


@router.get("/api/users")
def api_get_users(x_admin_key: str | None = Header(default=None), db: Session = Depends(get_db)):
    if not _admin_authorized(None, x_admin_key):
        raise HTTPException(status_code=401, detail="Valid X-Admin-Key header required")
    return [
        {
            "user_id": user.user_id,
            "name": user.name,
            "age": user.age,
            "weight_kg": user.weight_kg,
            "goal": user.goal,
            "intensity": user.intensity,
            "latest_plan_id": get_latest_plan(db, user).id if get_latest_plan(db, user) else None,
        }
        for user in get_all_users(db)
    ]
