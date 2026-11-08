"""Fill the user guide template (docs/template/user_guide_template.docx).

Keeps the template's page setup, headings and bullet lists, replaces the
placeholders with PyRainCloud content and inserts the screens rendered by
docs/make_screens.py.

Run:  uv run python docs/make_screens.py && uv run python docs/build_user_guide.py
"""

from __future__ import annotations

import copy
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from docx.table import Table
from docx.text.paragraph import Paragraph

DOCS = Path(__file__).resolve().parent
TEMPLATE = DOCS / "template" / "user_guide_template.docx"
SCREENS = DOCS / "screens"
IMAGES = DOCS / "images"
OUTPUT = DOCS / "Инструкция_пользователя_PyRainCloud.docx"

REPO_URL = "https://github.com/noki1928/pyraincloud"
BODY_FONT = "Calibri"
CODE_FONT = "Consolas"

# A segment is (text, kind): kind is "b" (bold), "n" (normal) or "c" (inline code).
Seg = tuple[str, str]


class Guide:
    def __init__(self, template: Path):
        self.doc = Document(str(template))
        self.body = self.doc._body
        self.paras = list(self.doc.paragraphs)
        self.figure_no = 0

    # --- low-level helpers -------------------------------------------------

    @staticmethod
    def _clear(p: Paragraph) -> None:
        for r in list(p._p):
            if r.tag != qn("w:pPr"):
                p._p.remove(r)

    @staticmethod
    def _write(p: Paragraph, segs: list[Seg], size: float | None = None) -> None:
        for text, kind in segs:
            run = p.add_run(text)
            run.bold = kind == "b"
            font = CODE_FONT if kind == "c" else BODY_FONT
            run.font.name = font
            run._r.get_or_add_rPr().get_or_add_rFonts().set(qn("w:cs"), font)
            if size:
                run.font.size = Pt(size)

    def set(self, idx: int, segs: list[Seg]) -> Paragraph:
        """Replace the text of template paragraph ``idx`` keeping its list formatting."""
        p = self.paras[idx]
        self._clear(p)
        self._write(p, segs)
        return p

    def remove(self, idx: int) -> None:
        el = self.paras[idx]._p
        el.getparent().remove(el)

    def _new_after(self, anchor) -> Paragraph:
        el = OxmlElement("w:p")
        anchor_el = anchor._p if isinstance(anchor, Paragraph) else anchor._tbl
        anchor_el.addnext(el)
        return Paragraph(el, self.body)

    def item_after(self, anchor, like: int, segs: list[Seg]) -> Paragraph:
        """New list item formatted like template paragraph ``like``."""
        el = copy.deepcopy(self.paras[like]._p)
        anchor_el = anchor._p if isinstance(anchor, Paragraph) else anchor._tbl
        anchor_el.addnext(el)
        p = Paragraph(el, self.body)
        self._clear(p)
        self._write(p, segs)
        return p

    def text_after(self, anchor, segs: list[Seg], indent_cm: float = 0.0) -> Paragraph:
        p = self._new_after(anchor)
        p.paragraph_format.space_after = Pt(4)
        if indent_cm:
            p.paragraph_format.left_indent = Cm(indent_cm)
        self._write(p, segs)
        return p

    def code_after(self, anchor, code: str) -> Paragraph:
        """Monospace block on a light grey background, one paragraph per line."""
        p = anchor
        lines = code.strip("\n").splitlines()
        for i, line in enumerate(lines):
            p = self._new_after(p)
            # shading first: python-docx then inserts spacing/indent in schema order around it
            shd = OxmlElement("w:shd")
            shd.set(qn("w:val"), "clear")
            shd.set(qn("w:color"), "auto")
            shd.set(qn("w:fill"), "F2F2F2")
            p._p.get_or_add_pPr().append(shd)
            fmt = p.paragraph_format
            fmt.left_indent = Cm(0.6)
            fmt.space_before = Pt(4 if i == 0 else 0)
            fmt.space_after = Pt(6 if i == len(lines) - 1 else 0)
            fmt.line_spacing = 1.0
            fmt.keep_with_next = i < len(lines) - 1
            run = p.add_run(line if line else " ")
            run.font.name = CODE_FONT
            run._r.get_or_add_rPr().get_or_add_rFonts().set(qn("w:cs"), CODE_FONT)
            run.font.size = Pt(9)
        return p

    def figure_after(self, anchor, image: Path, caption: str, width_cm: float = 15.0) -> Paragraph:
        self.figure_no += 1
        pic = self._new_after(anchor)
        pic.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pic.paragraph_format.space_before = Pt(6)
        pic.paragraph_format.keep_with_next = True
        pic.add_run().add_picture(str(image), width=Cm(width_cm))
        cap = self._new_after(pic)
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.paragraph_format.space_after = Pt(10)
        run = cap.add_run(f"Рисунок {self.figure_no} — {caption}")
        run.italic = True
        run.font.size = Pt(9.5)
        run.font.name = BODY_FONT
        run.font.color.rgb = RGBColor(0x40, 0x40, 0x40)
        return cap

    def table_after(
        self,
        anchor,
        header: list[str],
        rows: list[list[str]],
        widths_cm: list[float],
        code_cols: tuple[int, ...] = (),
    ) -> Table:
        table = self.doc.add_table(rows=1 + len(rows), cols=len(header))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        borders = OxmlElement("w:tblBorders")
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
            b = OxmlElement(f"w:{edge}")
            b.set(qn("w:val"), "single")
            b.set(qn("w:sz"), "4")
            b.set(qn("w:color"), "A6A6A6")
            borders.append(b)
        tbl_pr = table._tbl.tblPr
        successor = next(
            (
                el
                for el in tbl_pr
                if el.tag in {qn(f"w:{t}") for t in ("shd", "tblLayout", "tblCellMar", "tblLook")}
            ),
            None,
        )
        if successor is None:
            tbl_pr.append(borders)
        else:
            successor.addprevious(borders)
        for r_i, values in enumerate([header, *rows]):
            for c_i, value in enumerate(values):
                cell = table.cell(r_i, c_i)
                cell.width = Cm(widths_cm[c_i])
                p = cell.paragraphs[0]
                p.paragraph_format.space_after = Pt(0)
                if r_i == 0:
                    shd = OxmlElement("w:shd")
                    shd.set(qn("w:val"), "clear")
                    shd.set(qn("w:fill"), "E7EEF7")
                    cell._tc.get_or_add_tcPr().append(shd)
                    self._write(p, [(value, "b")], size=10)
                else:
                    kind = "c" if c_i in code_cols else "n"
                    for j, line in enumerate(value.split("\n")):
                        if j:
                            p = cell.add_paragraph()
                            p.paragraph_format.space_after = Pt(0)
                        self._write(p, [(line, kind)], size=9 if kind == "c" else 10)
        anchor_el = anchor._p if isinstance(anchor, Paragraph) else anchor._tbl
        anchor_el.addnext(table._tbl)
        return table

    def save(self, path: Path) -> None:
        self.doc.core_properties.title = "PyRainCloud — инструкция пользователя"
        self.doc.core_properties.author = "PyRainCloud"
        self.doc.save(str(path))


def build() -> Path:
    g = Guide(TEMPLATE)
    S, IMG = SCREENS, IMAGES

    # Header
    g.set(1, [("Проект: ", "b"), ("PyRainCloud 0.1.0 — Python-библиотека rain cloud plots", "n")])

    # --- 0. Введение ---------------------------------------------------------
    g.set(
        4,
        [
            ("Название проекта: ", "b"),
            (
                "PyRainCloud — библиотека для построения rain cloud plots из pandas DataFrame "
                "одной командой (версия 0.1.0, лицензия MIT).",
                "n",
            ),
        ],
    )
    g.set(
        5,
        [
            ("Ссылка на работающий MVP: ", "b"),
            (f"репозиторий {REPO_URL}", "c"),
            (" — исходный код, README, пример-ноутбук ", "n"),
            ("examples/quickstart.ipynb", "c"),
            (
                ". Пакет собран (wheel + sdist) и готов к публикации на PyPI; после публикации "
                "ставится командой ",
                "n",
            ),
            ("pip install pyraincloud", "c"),
            (".", "n"),
        ],
    )
    g.set(
        6,
        [
            ("Для кого этот продукт: ", "b"),
            (
                "для аспирантов, исследователей и аналитиков данных (психология, нейробиология, "
                "медицина, биология, A/B-тесты), которые работают в Python + pandas + matplotlib и "
                "сравнивают 2–10 групп по непрерывному показателю: время реакции, баллы, "
                "концентрации.",
                "n",
            ),
        ],
    )
    g.set(
        7,
        [
            ("Что он делает: ", "b"),
            (
                "строит rain cloud plot публикационного качества — облако плотности, box plot и "
                "сами наблюдения на одном графике — одной строкой кода прямо из DataFrame.",
                "n",
            ),
        ],
    )
    p = g.set(
        8,
        [
            ("Сколько времени займёт знакомство: ", "b"),
            (
                "около 5 минут до первого графика: 1–2 минуты на установку, минута на данные, "
                "сам график — одна строка кода и меньше секунды на построение.",
                "n",
            ),
        ],
    )
    p = g.text_after(
        p,
        [
            ("Что нужно заранее: ", "b"),
            (
                "Python 3.9 или новее и любое привычное окружение — uv, pip + venv, "
                "conda, Poetry, Pipenv, Jupyter или Google Colab. Знание matplotlib "
                "не требуется.",
                "n",
            ),
        ],
    )
    p = g.text_after(
        p,
        [
            ("Как выглядит результат. ", "b"),
            (
                "Каждая группа — это «облако» (оценка плотности распределения, "
                "слева), «ящик» (медиана и квартили, по центру) и «дождь» (каждое "
                "отдельное наблюдение, справа):",
                "n",
            ),
        ],
    )
    g.figure_after(
        p,
        IMG / "01_basic.png",
        'Rain cloud plot, построенный командой rc.raincloud(data=df, x="group", y="reaction_time")',
        width_cm=12,
    )

    # --- 1. Первый вход ------------------------------------------------------
    g.remove(10)
    g.set(11, [("Как попасть в продукт:", "b")])
    p = g.set(
        12,
        [
            (
                "PyRainCloud — это Python-библиотека, а не сайт или приложение: её "
                "устанавливают одной командой в своё окружение и импортируют в Jupyter "
                "Notebook, скрипте или IDE (VS Code, PyCharm). Команда установки для "
                "вашего окружения:",
                "n",
            )
        ],
    )
    p = g.table_after(
        p,
        ["Окружение", "Команда установки"],
        [
            [
                "uv",
                "uv add pyraincloud\n# или для одного скрипта:\nuv run --with pyraincloud python my_plot.py",
            ],
            [
                "pip + venv\n(Linux / macOS)",
                "python3 -m venv .venv\nsource .venv/bin/activate\npip install pyraincloud",
            ],
            [
                "pip + venv\n(Windows)",
                "py -m venv .venv\n.venv\\Scripts\\Activate.ps1\npip install pyraincloud",
            ],
            [
                "conda / mamba",
                "conda create -n raincloud -c conda-forge python=3.11 \\\n    numpy pandas scipy matplotlib\nconda activate raincloud\npip install pyraincloud",
            ],
            ["Poetry", "poetry add pyraincloud"],
            ["Pipenv", "pipenv install pyraincloud"],
            ["Jupyter / Colab", "%pip install pyraincloud   # в ячейке ноутбука"],
        ],
        widths_cm=[3.5, 12.5],
        code_cols=(1,),
    )
    p = g.text_after(
        p,
        [
            ("До публикации на PyPI замените ", "n"),
            ("pyraincloud", "c"),
            (" в команде на ", "n"),
            (f'"pyraincloud @ git+{REPO_URL}.git"', "c"),
            (" (установка из репозитория) или на путь к собранному файлу ", "n"),
            ("dist/pyraincloud-0.1.0-py3-none-any.whl", "c"),
            (".", "n"),
        ],
        indent_cm=1.27,
    )
    g.set(13, [("Что нужно сделать на старте:", "b")])
    g.set(
        14,
        [
            (
                "Регистрация, вход и ключи не нужны: библиотека работает полностью локально, "
                "без интернета — данные никуда не отправляются.",
                "n",
            )
        ],
    )
    p = g.set(
        15,
        [
            ("Сразу вводить ничего не нужно. Проверьте установку командой ", "n"),
            ('python -c "import pyraincloud as rc; print(rc.__version__)"', "c"),
            (" — она должна вывести ", "n"),
            ("0.1.0", "c"),
            (".", "n"),
        ],
    )
    g.set(16, [("Что пользователь увидит первым:", "b")])
    g.set(
        17,
        [
            ("После ", "n"),
            ("import pyraincloud as rc", "c"),
            (" доступна одна функция — ", "n"),
            ("rc.raincloud(...)", "c"),
            (". Её описание показывают ", "n"),
            ("help(rc.raincloud)", "c"),
            (" или ", "n"),
            ("rc.raincloud?", "c"),
            (
                " в Jupyter. Главный «экран» продукта — ячейка с вызовом функции и график под ней.",
                "n",
            ),
        ],
    )
    p = g.set(18, [("Скриншоты стартового экрана:", "b")])
    p = g.figure_after(
        p,
        S / "00_install_check.png",
        "Проверка установки в терминале: библиотека импортируется, версия 0.1.0",
    )
    g.figure_after(
        p,
        S / "01_import.png",
        "Первая ячейка Jupyter: импорт библиотеки и описание функции raincloud",
    )

    # --- 2. Core-функция -----------------------------------------------------
    g.remove(20)
    g.set(
        21,
        [
            ("Название функции: ", "b"),
            ("«Rain cloud plot одной командой» — ", "n"),
            ("rc.raincloud(data, x, y)", "c"),
            (" рисует облако плотности, box plot и точки для каждой группы.", "n"),
        ],
    )
    g.set(
        22,
        [
            ("Зачем она нужна пользователю: ", "b"),
            (
                "вручную такой график занимает 50+ строк кода на matplotlib и 2–3 часа на "
                "первую диаграмму. Здесь — одна строка и пара секунд, а на графике сразу видно "
                "распределение, медиану с квартилями и каждое наблюдение.",
                "n",
            ),
        ],
    )
    g.set(23, [("Пошаговая инструкция:", "b")])
    g.set(
        24,
        [
            (
                "Подготовьте данные в pandas DataFrame в «длинном» формате: одна строка — одно "
                "наблюдение, колонка с названием группы и колонка с числом. Данные можно "
                "загрузить из файла: ",
                "n",
            ),
            ('df = pd.read_csv("data.csv")', "c"),
            (".", "n"),
        ],
    )
    g.set(
        25,
        [
            ("Вызовите ", "n"),
            ('fig, ax = rc.raincloud(data=df, x="group", y="reaction_time")', "c"),
            (", подставив имена своих колонок, и запустите ячейку (Shift+Enter) или скрипт.", "n"),
        ],
    )
    g.set(
        26,
        [
            (
                "Библиотека проверяет данные, группирует их, оценивает плотность и рисует три "
                "слоя. Обычно это занимает меньше секунды; 10 групп по 5 000 точек — не "
                "дольше 2 секунд (проверяется автотестом).",
                "n",
            )
        ],
    )
    g.set(
        27,
        [
            ("График появляется под ячейкой (в обычном скрипте добавьте ", "n"),
            ("plt.show()", "c"),
            ("), а в переменных ", "n"),
            ("fig", "c"),
            (" и ", "n"),
            ("ax", "c"),
            (" лежат стандартные объекты matplotlib для дальнейшей работы.", "n"),
        ],
    )
    p = g.set(
        28,
        [
            ("Пример входных данных: ", "b"),
            (
                "эксперимент с тремя группами по 30 испытуемых, у каждого измерено время "
                "реакции в миллисекундах.",
                "n",
            ),
        ],
    )
    p = g.code_after(
        p,
        """\
import numpy as np
import pandas as pd
import pyraincloud as rc

rng = np.random.default_rng(42)
df = pd.DataFrame({
    "group": ["Control"] * 30 + ["Treatment A"] * 30 + ["Treatment B"] * 30,
    "reaction_time": np.concatenate([rng.normal(500, 50, 30),
                                     rng.normal(450, 60, 30),
                                     rng.normal(480, 55, 30)]),
})

fig, ax = rc.raincloud(data=df, x="group", y="reaction_time")""",
    )
    g.set(
        29,
        [
            ("Пример результата: ", "b"),
            (
                "график из трёх групп в порядке их появления в данных. У каждой группы "
                "облако слева, ящик по центру и точки справа; подписи осей взяты из имён "
                "колонок. Пропуски (NaN) отбрасываются с предупреждением.",
                "n",
            ),
        ],
    )
    p = g.set(30, [("Скриншоты каждого шага:", "b")])
    p = g.figure_after(
        p, S / "02_data.png", "Шаг 1 — данные в DataFrame: колонка группы и числовая колонка"
    )
    g.figure_after(
        p, S / "03_basic.png", "Шаги 2–4 — вызов rc.raincloud и готовый график под ячейкой"
    )

    # --- 3. Функция №2 -------------------------------------------------------
    g.remove(32)
    g.set(
        33,
        [
            ("Название функции: ", "b"),
            (
                "настройка внешнего вида — цвета, ориентация, прозрачность и размеры слоёв, "
                "включение и отключение ящиков и точек.",
                "n",
            ),
        ],
    )
    g.set(
        34,
        [
            ("Зачем она нужна: ", "b"),
            (
                "чтобы оформить серию графиков в едином стиле под требования журнала, "
                "развернуть график горизонтально при длинных названиях групп и получать "
                "одинаковую картинку при каждом запуске.",
                "n",
            ),
        ],
    )
    g.set(35, [("Пошаговая инструкция:", "b")])
    g.set(
        36,
        [
            ("Выберите цвета групп: список HEX-кодов или названий (", "n"),
            ('["#66c2a5", "#fc8d62", "#8da0cb"]', "c"),
            ("), цветов должно быть не меньше, чем групп.", "n"),
        ],
    )
    g.set(
        37,
        [
            ("Добавьте в тот же вызов ", "n"),
            ("rc.raincloud", "c"),
            (" нужные параметры из таблицы ниже, например ", "n"),
            ('orient="h", cloud_alpha=0.6, point_size=4', "c"),
            (".", "n"),
        ],
    )
    p = g.set(
        38,
        [
            (
                "Запустите ячейку — график перерисуется с новым оформлением. При неверном "
                "значении (например, ",
                "n",
            ),
            ("cloud_alpha=1.5", "c"),
            (") библиотека сразу сообщит, какой параметр исправить.", "n"),
        ],
    )
    g.item_after(
        p,
        38,
        [
            (
                "Для серии графиков сохраните настройки в словарь и передавайте его "
                "в каждый вызов: ",
                "n",
            ),
            ("style = dict(palette=palette, cloud_alpha=0.6, point_size=4)", "c"),
            (", затем ", "n"),
            ("rc.raincloud(data=df, x=..., y=..., **style)", "c"),
            (".", "n"),
        ],
    )
    p = g.set(
        39,
        [
            ("Пример входных и выходных данных: ", "b"),
            ("те же данные, горизонтальная ориентация и своя палитра:", "n"),
        ],
    )
    p = g.code_after(
        p,
        """\
palette = ["#66c2a5", "#fc8d62", "#8da0cb"]
fig, ax = rc.raincloud(
    data=df, x="group", y="reaction_time",
    orient="h", palette=palette,
    cloud_alpha=0.6, cloud_width=0.9,
    point_size=4, point_alpha=0.8, box_width=0.2,
    random_state=0,          # одинаковое расположение точек при каждом запуске
)""",
    )
    p = g.text_after(p, [("Все параметры настройки:", "b")])
    p = g.table_after(
        p,
        ["Параметр", "Что меняет", "По умолчанию"],
        [
            ["orient", "'v' — группы по горизонтали, 'h' — по вертикали", "'v'"],
            ["palette", "список цветов, по одному на группу", "цвета matplotlib"],
            ["cloud_alpha", "прозрачность облака, от 0 до 1", "0.5"],
            ["cloud_width", "максимальная ширина облака", "0.8"],
            ["point_size", "размер точек", "3.0"],
            ["point_alpha", "прозрачность точек, от 0 до 1", "0.6"],
            ["box_width", "ширина ящика", "0.15"],
            ["add_boxes", "рисовать ли ящик (True/False)", "True"],
            ["add_points", "рисовать ли точки (True/False)", "True"],
            ["random_state", "число для одинакового разброса точек", "None"],
            ["ax", "готовые оси matplotlib, на которых рисовать", "None (новый график)"],
        ],
        widths_cm=[3.2, 9.0, 3.8],
        code_cols=(0,),
    )
    p = g.set(40, [("Скриншоты процесса:", "b")])
    p = g.figure_after(
        p, S / "04_custom_h.png", "Горизонтальная ориентация, своя палитра, увеличенные точки"
    )
    g.figure_after(p, S / "05_no_boxes.png", "Тот же график без ящиков: add_boxes=False")

    # --- 4. Функция №3 -------------------------------------------------------
    g.remove(42)
    g.set(
        43,
        [
            ("Название функции: ", "b"),
            ("донастройка и экспорт результата — функция возвращает стандартные ", "n"),
            ("fig, ax", "c"),
            (
                " matplotlib: на график можно добавить заголовок, подписи и отметки "
                "значимости, а потом сохранить его в PNG или PDF.",
                "n",
            ),
        ],
    )
    g.set(
        44,
        [
            ("Зачем она нужна: ", "b"),
            (
                "замыкает путь от данных до готовой иллюстрации в статье: никакого нового "
                "API — всё, что пользователь умеет в matplotlib, работает и здесь. Несколько "
                "графиков можно собрать на одной фигуре через параметр ",
                "n",
            ),
            ("ax=", "c"),
            (".", "n"),
        ],
    )
    g.set(45, [("Пошаговая инструкция:", "b")])
    g.set(
        46,
        [
            ("Сохраните результат вызова: ", "n"),
            ('fig, ax = rc.raincloud(data=df, x="group", y="reaction_time")', "c"),
            (".", "n"),
        ],
    )
    g.set(
        47,
        [
            ("Оформите график методами matplotlib: ", "n"),
            ("ax.set_title(...)", "c"),
            (", ", "n"),
            ("ax.set_ylabel(...)", "c"),
            (", отметка значимости — ", "n"),
            ("ax.annotate(...)", "c"),
            (".", "n"),
        ],
    )
    p = g.set(
        48,
        [
            ("Сохраните файл: ", "n"),
            ('fig.savefig("raincloud_plot.pdf", dpi=300, bbox_inches="tight")', "c"),
            (
                " — файл появится в текущей папке. Формат определяется расширением: "
                ".pdf, .png, .svg, .tiff.",
                "n",
            ),
        ],
    )
    g.item_after(
        p,
        48,
        [
            (
                "Чтобы разместить несколько графиков рядом, создайте оси заранее и передайте их: ",
                "n",
            ),
            ("fig, (ax1, ax2) = plt.subplots(1, 2)", "c"),
            (", затем ", "n"),
            ("rc.raincloud(..., ax=ax1)", "c"),
            (".", "n"),
        ],
    )
    p = g.set(
        49,
        [
            ("Пример результата: ", "b"),
            (
                "подписанный график с отметкой «p < 0.05» и файлы PDF/PNG 300 dpi, "
                "готовые к вставке в статью.",
                "n",
            ),
        ],
    )
    p = g.code_after(
        p,
        """\
fig, ax = rc.raincloud(data=df, x="group", y="reaction_time",
                       palette=palette, random_state=0)
ax.set_title("Reaction Time by Treatment Group", fontsize=14, fontweight="bold")
ax.set_xlabel("Treatment Group")
ax.set_ylabel("Reaction Time (ms)")
ax.plot([0, 0, 1, 1], [612, 620, 620, 612], color="black", linewidth=1)
ax.annotate("p < 0.05", xy=(0.5, 622), ha="center", va="bottom")
fig.savefig("raincloud_plot.pdf", dpi=300, bbox_inches="tight")""",
    )
    p = g.set(50, [("Скриншоты:", "b")])
    p = g.figure_after(
        p, S / "06_annotate.png", "Заголовок, подписи осей и отметка значимости поверх графика"
    )
    g.figure_after(p, S / "07_savefig.png", "Сохранение в PDF и PNG: файлы созданы в текущей папке")

    # --- 5. Ошибки -----------------------------------------------------------
    g.remove(52)
    p = g.set(
        53,
        [
            ("Ошибка №1: ", "b"),
            ("ValueError: Column 'condition' not found in data", "c"),
            (" → Что делать: ", "b"),
            (
                "имя колонки в x или y написано не так, как в таблице. Посмотрите точные "
                "имена командой ",
                "n",
            ),
            ("print(df.columns)", "c"),
            (" — важны регистр и пробелы.", "n"),
        ],
    )
    p = g.figure_after(p, S / "08_err_column.png", "Сообщение об ошибке в имени колонки")
    p2 = g.set(
        54,
        [
            ("Ошибка №2: ", "b"),
            ("ValueError: palette has 2 colour(s) but data has 3 group(s)", "c"),
            (" → Что делать: ", "b"),
            ("в палитре меньше цветов, чем групп. Добавьте цвета или уберите ", "n"),
            ("palette", "c"),
            (" — тогда цвета подберутся автоматически.", "n"),
        ],
    )
    p2 = g.figure_after(p2, S / "09_err_palette.png", "Сообщение о слишком короткой палитре")
    p3 = g.set(
        55,
        [
            ("Ошибка №3: ", "b"),
            ("TypeError: Column 'reaction_time' must be numeric", "c"),
            (" → Что делать: ", "b"),
            (
                "в числовой колонке есть текст — «n/a», прочерки или запятая вместо "
                "точки. Читайте файл с ",
                "n",
            ),
            ('pd.read_csv(..., decimal=",")', "c"),
            (" или очистите колонку: ", "n"),
            ('df["reaction_time"] = pd.to_numeric(df["reaction_time"], errors="coerce")', "c"),
            (".", "n"),
        ],
    )
    p3 = g.item_after(
        p3,
        55,
        [
            ("Предупреждение RaincloudWarning: dropped N NaN value(s) ", "b"),
            ("→ Что делать: ", "b"),
            (
                "это не ошибка — график построен, пустые значения просто "
                "исключены. Если пропусков быть не должно, проверьте исходные "
                "данные.",
                "n",
            ),
        ],
    )
    p3 = g.figure_after(
        p3, S / "10_warn_nan.png", "Предупреждения о пропусках: график всё равно построен"
    )
    p3 = g.item_after(
        p3,
        55,
        [
            ("ModuleNotFoundError: No module named 'pyraincloud' ", "b"),
            ("→ Что делать: ", "b"),
            ("библиотека установлена в другое окружение. В Jupyter выполните ", "n"),
            ("%pip install pyraincloud", "c"),
            (
                " прямо в ячейке или выберите ядро нужного окружения; с uv запускайте код через ",
                "n",
            ),
            ("uv run", "c"),
            (".", "n"),
        ],
    )
    p3 = g.item_after(
        p3,
        55,
        [
            ("График не появляется при запуске скрипта ", "b"),
            ("→ Что делать: ", "b"),
            ("библиотека намеренно не открывает окно сама. Добавьте ", "n"),
            ("plt.show()", "c"),
            (" в конце скрипта или сохраните файл через ", "n"),
            ("fig.savefig(...)", "c"),
            (".", "n"),
        ],
    )
    g.item_after(
        p3,
        55,
        [
            ("У одной группы нет «облака» ", "b"),
            ("→ Что делать: ", "b"),
            (
                "в группе одно значение или все значения одинаковы — плотность для "
                "неё посчитать нельзя. Библиотека предупреждает об этом и рисует "
                "только ящик и точки; добавьте наблюдений, если нужно облако.",
                "n",
            ),
        ],
    )

    # --- 6. FAQ --------------------------------------------------------------
    g.remove(57)
    g.set(
        58,
        [
            ("Нужен ли интернет или аккаунт? ", "b"),
            (
                "→ Нет. Библиотека работает полностью на вашем компьютере, ничего не "
                "отправляет и не сохраняет без вашей команды.",
                "n",
            ),
        ],
    )
    g.set(
        59,
        [
            ("Почему точки немного сдвигаются при каждом запуске и как это убрать? ", "b"),
            (
                "→ Точки специально разносятся случайным образом, чтобы не перекрываться. "
                "Передайте ",
                "n",
            ),
            ("random_state=0", "c"),
            (" (или любое число) — расположение станет одинаковым.", "n"),
        ],
    )
    p = g.set(
        60,
        [
            ("Как задать свой порядок групп? ", "b"),
            ("→ Сделайте колонку категориальной: ", "n"),
            (
                'df["group"] = pd.Categorical(df["group"], categories=["Treatment B", '
                '"Control", "Treatment A"])',
                "c",
            ),
            (". По умолчанию группы идут в порядке появления в данных.", "n"),
        ],
    )
    p = g.item_after(
        p,
        60,
        [
            ("Можно ли автоматически посчитать p-value? ", "b"),
            ("→ В версии 0.1.0 нет: посчитайте статистику в SciPy (например, ", "n"),
            ("scipy.stats.ttest_ind", "c"),
            (") и нанесите результат через ", "n"),
            ("ax.annotate", "c"),
            (", как в разделе 4.", "n"),
        ],
    )
    p = g.item_after(
        p,
        60,
        [
            ("Мои данные «широкие» — каждая группа в своей колонке. Что делать? ", "b"),
            ("→ Переведите их в длинный формат одной строкой: ", "n"),
            ('long = df.melt(var_name="group", value_name="value")', "c"),
            (", затем ", "n"),
            ('rc.raincloud(data=long, x="group", y="value")', "c"),
            (".", "n"),
        ],
    )
    g.item_after(
        p,
        60,
        [
            ("Какие версии Python и библиотек поддерживаются? ", "b"),
            (
                "→ Python 3.9 и новее, pandas ≥ 1.5, matplotlib ≥ 3.5, numpy, scipy. "
                "Тесты пройдены на Python 3.9 с минимальными версиями зависимостей и "
                "на Python 3.10–3.13 с актуальными.",
                "n",
            ),
        ],
    )

    g.save(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    print(f"Saved {build()}")
