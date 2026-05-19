import os
import httpx
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime

from database import users_collection, bots_collection
from auth import hash_password, verify_password, create_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


# ─── REQUEST MODELS ───────────────────────────────────────────

class SignupRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class GoogleAuthRequest(BaseModel):
    token: str


# ─── SIGNUP ───────────────────────────────────────────────────

@router.post("/signup")
def signup(req: SignupRequest):
    existing = users_collection.find_one({'email': req.email.lower()})
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email already registered."
        )

    if len(req.password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 6 characters."
        )

    user = {
        'name': req.name,
        'email': req.email.lower(),
        'password': hash_password(req.password),
        'auth_provider': 'email',
        'plan': 'free',
        'created_at': datetime.utcnow()
    }

    result = users_collection.insert_one(user)
    user_id = str(result.inserted_id)
    token = create_token(user_id, req.email.lower())

    return {
        'token': token,
        'user': {
            'id': user_id,
            'name': req.name,
            'email': req.email.lower(),
            'plan': 'free'
        }
    }


# ─── LOGIN ────────────────────────────────────────────────────

@router.post("/login")
def login(req: LoginRequest):
    user = users_collection.find_one({'email': req.email.lower()})

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password."
        )

    if user.get('auth_provider') == 'google':
        raise HTTPException(
            status_code=400,
            detail="This account uses Google login. Please sign in with Google."
        )

    if not verify_password(req.password, user['password']):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password."
        )

    user_id = str(user['_id'])
    token = create_token(user_id, user['email'])

    return {
        'token': token,
        'user': {
            'id': user_id,
            'name': user['name'],
            'email': user['email'],
            'plan': user.get('plan', 'free')
        }
    }


# ─── GOOGLE OAUTH ─────────────────────────────────────────────

@router.post("/google")
async def google_auth(req: GoogleAuthRequest):
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={req.token}"
        )

    if res.status_code != 200:
        raise HTTPException(
            status_code=401,
            detail="Invalid Google token."
        )

    google_data = res.json()
    email = google_data.get('email')
    name  = google_data.get('name', email)

    if not email:
        raise HTTPException(
            status_code=400,
            detail="Could not get email from Google."
        )

    user = users_collection.find_one({'email': email.lower()})

    if not user:
        new_user = {
            'name': name,
            'email': email.lower(),
            'password': None,
            'auth_provider': 'google',
            'plan': 'free',
            'created_at': datetime.utcnow()
        }
        result = users_collection.insert_one(new_user)
        user_id = str(result.inserted_id)
    else:
        user_id = str(user['_id'])

    token = create_token(user_id, email.lower())

    return {
        'token': token,
        'user': {
            'id': user_id,
            'name': name,
            'email': email.lower(),
            'plan': user.get('plan', 'free') if user else 'free'
        }
    }


# ─── GET CURRENT USER ─────────────────────────────────────────

@router.get("/me")
def get_me(current_user=Depends(get_current_user)):
    user = users_collection.find_one(
        {'_id': ObjectId(current_user['sub'])}
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    return {
        'id': str(user['_id']),
        'name': user['name'],
        'email': user['email'],
        'plan': user.get('plan', 'free'),
        'created_at': str(user['created_at'])
    }


# ─── LOGOUT ───────────────────────────────────────────────────

@router.post("/logout")
def logout():
    return {'message': 'Logged out successfully.'}