from dataclasses import dataclass

@dataclass(frozen=True)
class LevelInfo:
    number: int
    name: str
    min_xp: int
    max_xp: int | None
    check_limit: str
    deposit_percent: int
    task_percent: int


LEVELS = [
    LevelInfo(1, "Новичок", 0, 499, "чеки недоступны или сильно ограничены", 10, 3),
    LevelInfo(2, "Активист", 500, 1499, "до 200 000 {currency_name} в день", 10, 3),
    LevelInfo(3, "Мастер заданий", 1500, 4999, "до 500 000 {currency_name} в день", 10, 5),
    LevelInfo(4, "Гуру подписок", 5000, 9999, "до 2 500 000 {currency_name} в день", 10, 7),
]


def get_level_info(xp: int) -> LevelInfo:
    current = LEVELS[0]
    for level in LEVELS:
        if xp >= level.min_xp and (level.max_xp is None or xp <= level.max_xp):
            return level
        if xp >= level.min_xp:
            current = level
    return current


def xp_to_next_level(xp: int) -> int:
    for level in LEVELS:
        if level.min_xp > xp:
            return level.min_xp - xp
    return 0


def levels_table(currency_name: str) -> str:
    lines = []
    for level in LEVELS:
        xp_range = f"{level.min_xp}+ XP" if level.max_xp is None else f"{level.min_xp}-{level.max_xp} XP"
        check_limit = level.check_limit.format(currency_name=currency_name)
        check_text = check_limit if check_limit.startswith("чеки") else f"чеки {check_limit}"
        lines.append(
            f"<b>{level.number}. {level.name}</b>\n"
            f"{xp_range}; {check_text}; {level.deposit_percent}% с пополнений, "
            f"{level.task_percent}% с заданий рефералов."
        )
    return "\n\n".join(lines)
