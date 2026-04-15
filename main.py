'''
 TODO: Create a prototype of subscribing and email sending
 TODO: Uporządkować kod wg PEP8
'''

import json
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pydantic import BaseModel


def open_json_file(filename):
    with open(filename, "r", encoding="utf-8") as f:
        dictionary = json.load(f)
        return dictionary


def update_json_file(filename, dictionary):
    with open(filename, "w", encoding="utf-8") as f:
        f.seek(0)
        json.dump(dictionary, f)


SECRET_KEY = "fa14c35d837087c1fa4a6fd29867fdaed3831166049cff7f1ab5a09a952dcb5c"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
USERS_DB = open_json_file("users.json")
ARTICLES_DB = open_json_file("articles.json")
password_hash = PasswordHash.recommended()
DUMMY_HASH = password_hash.hash("dummypassword")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    username: str
    email: str


class UserInDB(User):
    password: str


class Article(BaseModel):
    title: str
    contents: str


app = FastAPI()


def verify_password(plain_password, hashed_password):
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password):
    return password_hash.hash(password)


def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)
    return None


def authenticate_user(db, username: str, password: str):
    user = get_user(db, username)
    if not user:
        # Even though the user is not in the database,
        # still run the verification to prevent timing attacks.
        verify_password(password, DUMMY_HASH)
        return None
    if not verify_password(password, user.password):
        return None
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate your credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
        user = get_user(USERS_DB, username=token_data.username)
        if user is None:
            raise credentials_exception
        return user
    except InvalidTokenError:
        raise credentials_exception


@app.get("/users/")
def user_list():
    users = USERS_DB
    return {"Users": list(users.keys())}


@app.post("/users/")
def sign_up(user: UserInDB):
    try:
        if user.username in USERS_DB:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="This username is already taken")
        new_user = {"username": user.username, "email": user.email,
                    "password": get_password_hash(user.password)}
        USERS_DB.update({user.username: new_user})
        update_json_file("users.json", USERS_DB)
        return {"Success": f"Added {user.username} as a new user."}
    except HTTPException as err:
        raise err
    except Exception as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=err.__str__())


@app.post("/token")
async def login_for_access_token(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    try:
        user = authenticate_user(
            USERS_DB, form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        return Token(access_token=access_token, token_type="bearer")
    except HTTPException as err:
        raise err
    except Exception as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=err.__str__())


@app.get("/users/me")
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    return {current_user.username: current_user.email}


@app.get("/articles/")
def list_articles():
    titles = set(ARTICLES_DB.keys())
    js = {}
    for title in titles:
        js.update({title: ARTICLES_DB[title]["author"]})
    return js


@app.get("/articles/{title}/")
def read_article(title: str):
    return {"Contents": ARTICLES_DB[title]["contents"]}


@app.post("/articles/")
def add_or_update_article(current_user: Annotated[User, Depends(get_current_user)],
                          article: Article, ):
    try:
        new_article = {"title": article.title,
                       "author": current_user.username, "contents": article.contents}
        ARTICLES_DB.update({article.title: new_article})
        update_json_file("articles.json", ARTICLES_DB)
        # send email to the interested person
        return {"msg": "Succesfully updated your articles!"}
    except Exception as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=err.__str__())


@app.delete("/users/{username}")
def delete_user(current_user: Annotated[User, Depends(get_current_user)], username: str):
    try:
        if current_user.username != username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="You do not have permission to "
                                   "delete this user!")
        USERS_DB.pop(username)
        update_json_file("users.json", USERS_DB)
        return {"msg": "Bye bye!"}
    except HTTPException as err:
        raise err
    except Exception as err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=err.__str__())


@app.delete("/articles/{title}")
def delete_article(current_user: Annotated[User, Depends(get_current_user)], title: str):
    try:
        if current_user.username != ARTICLES_DB[title]["author"]:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="You must be logged in as an author"
                                       " of the article in order to delete it",
                                headers={"WWW-Authenticate": "Bearer"}, )
        if ARTICLES_DB.pop(title, None):
            update_json_file("articles.json", ARTICLES_DB)
            return {"msg": f"Removed \"{title}\" from the available articles!"}
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="You are trying to delete an article that does not exist!" )
    except HTTPException as err:
        raise err
    except Exception as err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=err.__str__())

