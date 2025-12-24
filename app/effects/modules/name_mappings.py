ATTRIBUTES_MAP = {
    "storeys_count": "Количество этажей",
    "population": "Население (чел)",
    "demand": "Спрос (чел)",
    "demand_left": "Неудовлетворённый спрос (чел)",
    "distance": "Расстояние (м)",
    "avg_dist": "Средняя доступность до сервиса (м)",
    "capacity": "Вместимость (чел)",
    "capacity_left": "Профицит мест (чел)",
    "living_area": "Жилая площадь (кв.м)",
    "service_load": "Нагрузка на сервис",
    "min_dist": "Минмиальное расстояне до сервиса (м)",
    "building_index": "ID здания",
    "service_index": "ID сервиса",
    "supplyed_demands_within": "Удовлетворённый спрос в нормативной доступности (чел)",
    "supplyed_demands_without": "Удовлетворённый спрос вне нормативной доступности (чел)",
    "carried_capacity_within": "Обеспечено в радиусе нормативной доступности (чел)",
    "carried_capacity_without": "Обеспечено вне радиуса нормативной доступности (чел)",
    "provison_value": "Оценка обеспеченности",
    "supplyed_demands_within_before": "Удовлетворённый спрос в нормативной доступности (до) (чел)",
    "us_demands_within_before": "Неудовлетворённый спрос в нормативной доступности (до) (чел)",
    "supplyed_demands_without_before": "Удовлетворённый спрос вне нормативной доступности (до) (чел)",
    "us_demands_without_before": "Неудовлетворённый спрос вне нормативной доступности (до) (чел)",
    "supplyed_demands_within_after": "Удовлетворённый спрос в нормативной доступности (после) (чел)",
    "us_demands_within_after": "Неудовлетворённый спрос в нормативной доступности (после) (чел)",
    "supplyed_demands_without_after": "Удовлетворённый спрос вне нормативной доступности (после) (чел)",
    "us_demands_without_after": "Неудовлетворённый спрос вне нормативной доступности (после) (чел)",
}

EFFECTS_MAP = {
    "absolute_total": "Абсолютный эффект (чел)",
    "index_total": "Индексный эффект",
    "absolute_scenario_project": "Абсолютный эффект на территории проекта",
    "index_scenario_project": "Индексный эффект на территории проекта",
    "absolute_within": "Абсолютный эффект в нормативной доступности",
    "demand": "Спрос (чел)",
    "is_project": "Проектный объект",
}

SERVICE_DROP_COLUMNS = ["is_scenario_object", "is_locked"]
BUILDINGS_DROP_COLUMNS = SERVICE_DROP_COLUMNS + ["is_project"]
