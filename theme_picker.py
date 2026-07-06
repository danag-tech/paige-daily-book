from datetime import date


THEMES = [
    "历史与文明",
    "心理学与自我理解",
    "社会观察",
    "认知升级",
    "商业与经济",
    "科技与未来",
    "文学经典",
    "女性成长",
    "生活方式",
    "传记与人物",
    "哲学入门",
    "沟通与关系",
    "城市与旅行",
    "艺术与审美",
    "工作方法",
]


def get_today_theme() -> str:
    today = date.today()
    index = today.toordinal() % len(THEMES)
    return THEMES[index]
