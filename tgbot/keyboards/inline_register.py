from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

CITIES = [
    "Москва",
    "Санкт-Петербург",
    "Новосибирск",
    "Екатеринбург",
    "Казань",
    "Нижний Новгород",
    "Челябинск",
    "Самара",
    "Ростов-на-Дону",
    "Уфа",
]

SPECS = [
    ("finishing", "Отделочные работы"),
    ("tiling", "Плиточные работы"),
    ("floor_screed", "Стяжка пола"),
    ("concrete_floors", "Бетонные полы"),
    ("concrete_works", "Бетонные работы"),
    ("monolithic", "Монолитные работы"),
    ("plaster_walls", "Штукатурка стен"),
    ("putty_walls", "Шпаклевка стен"),
    ("painting", "Малярные работы"),
    ("paint", "Покраска"),
    ("wallpaper", "Обои"),
    ("electrics", "Электрика"),
    ("plumbing", "Сантехника"),
    ("roofing", "Кровельные работы"),
    ("facade", "Фасадные работы"),
    ("foundation", "Фундамент"),
    ("dismantling", "Демонтаж"),
    ("welding", "Сварка"),
    ("windows", "Окна"),
    ("doors_install", "Установка дверей"),
    ("floors", "Полы"),
    ("frame", "Каркас"),
    ("ventilation", "Вентиляция"),
    ("heating", "Отопление"),
    ("landscaping", "Благоустройство"),
    ("engineering", "Проектирование"),
    ("estimate", "Смета"),
    ("insulation", "Утепление"),
    ("partitions", "Перегородки"),
    ("garbage_removal", "Вывоз мусора"),
    ("helper_jobs", "Подсобные работы"),
    ("masonry", "Кладка"),
    ("house_from_scratch", "Дом с нуля"),
    ("design_project", "Дизайн проект"),
    ("decor", "Декор"),
    ("odd_jobs", "Халтура"),
]


def cities_kb(prefix: str = "city") -> InlineKeyboardMarkup:
    rows, row = [], []
    for i, name in enumerate(CITIES, 1):
        row.append(InlineKeyboardButton(text=name, callback_data=f"{prefix}:{name}"))
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def specs_kb(
    selected, prefix: str = "spec", done_id: str = "spec_done"
) -> InlineKeyboardMarkup:
    selected_set = set(selected or [])
    rows, row = [], []
    for i, (slug, title) in enumerate(SPECS, 1):
        mark = "✅" if slug in selected_set else "•"
        row.append(
            InlineKeyboardButton(
                text=f"{mark} {title}", callback_data=f"{prefix}:{slug}"
            )
        )
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="Готово", callback_data=done_id)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def skip_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Пропустить", callback_data="photos_skip")]
        ]
    )
