import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import players, categories, leaderboard, comments
from app.websocket.game import router as game_ws_router

load_dotenv()

app = FastAPI(title="ClashQuiz API")

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
if "*" in origins:
    # Un wildcard combiné à allow_credentials=True est explicitement interdit
    # par la spec CORS et neutralise toute la protection : on préfère planter
    # au démarrage plutôt que de tourner silencieusement en prod non protégé.
    raise RuntimeError(
        "CORS_ORIGINS ne doit jamais contenir '*' (incompatible avec allow_credentials). "
        "Indique la liste exacte des domaines autorisés."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(players.router)
app.include_router(categories.router)
app.include_router(leaderboard.router)
app.include_router(comments.router)
app.include_router(game_ws_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
