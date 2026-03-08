from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import random

from database import get_balance, change_balance, get_setting, set_setting

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SYMBOLS = ["cherry", "lemon", "bell", "diamond", "star", "seven", "coin"]

WEIGHTS = {
    "cherry": 24,
    "lemon": 22,
    "bell": 17,
    "coin": 12,
    "diamond": 9,
    "star": 8,
    "seven": 4,
}

PAYTABLE = {
    "cherry": {3: 2, 4: 4, 5: 8},
    "lemon": {3: 2, 4: 5, 5: 10},
    "bell": {3: 3, 4: 8, 5: 15},
    "coin": {3: 8, 4: 20, 5: 40},
    "diamond": {3: 5, 4: 15, 5: 30},
    "seven": {3: 10, 4: 30, 5: 60},
}

LINES = [
    [0, 0, 0, 0, 0],
    [1, 1, 1, 1, 1],
    [2, 2, 2, 2, 2],
    [0, 1, 2, 1, 0],
    [2, 1, 0, 1, 2],
    [0, 0, 1, 0, 0],
    [2, 2, 1, 2, 2],
    [1, 0, 0, 0, 1],
    [1, 2, 2, 2, 1],
    [0, 1, 1, 1, 0],
    [2, 1, 1, 1, 2],
    [1, 1, 0, 1, 1],
    [1, 1, 2, 1, 1],
    [0, 1, 0, 1, 0],
    [2, 1, 2, 1, 2],
    [0, 0, 2, 0, 0],
    [2, 2, 0, 2, 2],
    [1, 0, 1, 0, 1],
    [1, 2, 1, 2, 1],
    [0, 2, 1, 2, 0],
]


class BootstrapIn(BaseModel):
    user_id: int


class SpinIn(BaseModel):
    user_id: int
    bet: float
    turbo: bool = False


def get_rtp():
    value = get_setting("rtp")
    if value is None:
        set_setting("rtp", "96")
        return 96.0
    return float(value)


def get_jackpot():
    value = get_setting("jackpot")
    if value is None:
        set_setting("jackpot", "0")
        return 0.0
    return float(value)


def set_jackpot(value: float):
    set_setting("jackpot", str(round(value, 2)))


def get_free_spins(user_id: int):
    value = get_setting(f"fs_{user_id}")
    if value is None:
        set_setting(f"fs_{user_id}", "0")
        return 0
    return int(value)


def set_free_spins(user_id: int, value: int):
    set_setting(f"fs_{user_id}", str(max(0, int(value))))


def weighted_symbol():
    pool = []
    for sym, w in WEIGHTS.items():
        pool.extend([sym] * w)
    return random.choice(pool)


def build_reels():
    return [[weighted_symbol() for _ in range(3)] for _ in range(5)]


def get_line_symbols(reels, line):
    return [reels[col][line[col]] for col in range(5)]


def get_line_hits(line, count):
    return [[col, line[col]] for col in range(count)]


def calc_line_win(symbols, bet_per_line):
    if symbols.count("star") >= 3:
        return 0.0, 0, False, None

    base = None
    count = 0

    for symbol in symbols:
        if symbol == "star":
            break

        if base is None:
            if symbol == "diamond":
                count += 1
                continue
            base = symbol
            count += 1
            continue

        if symbol == base or symbol == "diamond":
            count += 1
        else:
            break

    if base is None:
        return 0.0, 0, False, None

    multiplier = PAYTABLE.get(base, {}).get(count, 0)
    line_win = round(multiplier * bet_per_line, 2)
    jackpot_hit = base == "seven" and count == 5
    return line_win, count, jackpot_hit, base


def calc_scatter_bonus(reels, bet):
    flat = [sym for col in reels for sym in col]

    scatter_count = flat.count("star")
    bonus_count = flat.count("coin")

    scatter_win = 0.0
    fs_awarded = 0

    if scatter_count >= 5:
        scatter_win = round(bet * 10, 2)
        fs_awarded = 12
    elif scatter_count == 4:
        scatter_win = round(bet * 5, 2)
        fs_awarded = 8
    elif scatter_count == 3:
        scatter_win = round(bet * 2, 2)
        fs_awarded = 5

    bonus_triggered = False
    bonus_win = 0.0
    bonus_label = ""

    if bonus_count >= 3:
        bonus_triggered = True
        pick = random.choice([2, 3, 5, 8])
        bonus_win = round(bet * pick, 2)
        bonus_label = f"Bonus x{pick}"

    return scatter_win, fs_awarded, bonus_triggered, bonus_win, bonus_label


@app.get("/")
def root():
    return {"ok": True, "message": "Diamond Slot API working"}


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/bootstrap")
def bootstrap(data: BootstrapIn):
    balance = get_balance(data.user_id)
    free_spins = get_free_spins(data.user_id)

    return {
        "ok": True,
        "balance": round(balance, 2),
        "free_spins": free_spins,
        "rtp": get_rtp(),
        "jackpot": round(get_jackpot(), 2),
        "lines": len(LINES),
    }


@app.post("/spin")
def spin(data: SpinIn):
    user_id = data.user_id
    bet = round(float(data.bet), 2)

    if bet < 0.25:
        return {"ok": False, "error": "Минимальная ставка 0.25"}

    if bet > 100:
        return {"ok": False, "error": "Максимальная ставка 100"}

    free_spins = get_free_spins(user_id)
    use_fs = free_spins > 0

    balance = get_balance(user_id)
    if not use_fs and balance < bet:
        return {"ok": False, "error": "Недостаточно баланса"}

    if use_fs:
        set_free_spins(user_id, free_spins - 1)
    else:
        balance = change_balance(user_id, -bet)

    jackpot = get_jackpot()
    if not use_fs:
        jackpot += round(bet * 0.02, 2)
        set_jackpot(jackpot)

    reels = build_reels()
    bet_per_line = round(bet / len(LINES), 4)

    total_win = 0.0
    hit_cells = []
    winning_lines = []
    jackpot_hit = False

    for i, line in enumerate(LINES):
        line_symbols = get_line_symbols(reels, line)
        line_win, count, is_jp, base = calc_line_win(line_symbols, bet_per_line)

        if line_win > 0:
            total_win += line_win
            hit_cells.extend(get_line_hits(line, count))
            winning_lines.append({
                "index": i,
                "symbol": base,
                "count": count,
                "win": round(line_win, 2),
            })

        if is_jp:
            jackpot_hit = True

    scatter_win, fs_awarded, bonus_triggered, bonus_win, bonus_label = calc_scatter_bonus(reels, bet)
    total_win = round(total_win + scatter_win + bonus_win, 2)

    if fs_awarded > 0:
        set_free_spins(user_id, get_free_spins(user_id) + fs_awarded)

    jackpot_paid = 0.0
    if jackpot_hit:
        jackpot_paid = round(get_jackpot(), 2)
        set_jackpot(0.0)
        total_win = round(total_win + jackpot_paid, 2)

    rtp = get_rtp()
    total_win = round(total_win * (rtp / 100.0), 2)

    splash = ""
    if total_win >= bet * 20:
        splash = "mega"
    elif total_win >= bet * 10:
        splash = "big"

    if total_win > 0:
        balance = change_balance(user_id, total_win)
    else:
        balance = get_balance(user_id)

    message = "Мимо"
    if jackpot_hit:
        message = "Jackpot"
    elif bonus_triggered:
        message = bonus_label
    elif total_win > 0 and splash == "mega":
        message = "Mega Win"
    elif total_win > 0 and splash == "big":
        message = "Big Win"
    elif total_win > 0:
        message = "Победа"

    return {
        "ok": True,
        "balance": round(balance, 2),
        "reels": reels,
        "bet": bet,
        "win": round(total_win, 2),
        "message": message,
        "rtp": rtp,
        "jackpot": round(get_jackpot(), 2),
        "jackpot_hit": jackpot_hit,
        "jackpot_paid": round(jackpot_paid, 2),
        "free_spins": get_free_spins(user_id),
        "fs_awarded": fs_awarded,
        "bonus_triggered": bonus_triggered,
        "bonus_win": round(bonus_win, 2),
        "splash": splash,
        "hit_cells": hit_cells,
        "winning_lines": winning_lines,
        "used_free_spin": use_fs,
        "turbo": data.turbo,
    }
