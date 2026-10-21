import os
import random

from kivy.core.clipboard import Clipboard
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import (
    AliasProperty,
    BooleanProperty,
    ColorProperty,
    DictProperty,
    NumericProperty,
    StringProperty,
)
from kivy.storage.jsonstore import JsonStore
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.utils import platform
from kivymd.app import MDApp
from kivymd.toast import toast
from kivymd.uix.button import MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.menu import MDDropdownMenu

from engine import CalcError, evaluate, format_result, to_fraction

# AdMob banner support (Android build only; requires KivMob in Buildozer).
try:
    from kivmob import KivMob
except ImportError:
    KivMob = None


# ---------------------------------------------------------------------------
# Button look
# ---------------------------------------------------------------------------
# style -> (background colour, text colour)
_DARK_KEYS = {
    "num": ((0.17, 0.19, 0.27, 1), (1.00, 1.00, 1.00, 1)),
    "fn":  ((0.10, 0.13, 0.22, 1), (0.80, 0.87, 1.00, 1)),
    "op":  ((0.12, 0.42, 0.95, 1), (1.00, 1.00, 1.00, 1)),
    "eq":  ((0.20, 0.52, 1.00, 1), (1.00, 1.00, 1.00, 1)),
    "ac":  ((0.10, 0.13, 0.22, 1), (1.00, 0.45, 0.45, 1)),
    "del": ((0.10, 0.13, 0.22, 1), (1.00, 0.75, 0.30, 1)),
}
_LIGHT_KEYS = {
    "num": ((1.00, 1.00, 1.00, 1), (0.08, 0.10, 0.18, 1)),
    "fn":  ((0.84, 0.88, 0.97, 1), (0.12, 0.20, 0.40, 1)),
    "op":  ((0.12, 0.42, 0.95, 1), (1.00, 1.00, 1.00, 1)),
    "eq":  ((0.20, 0.52, 1.00, 1), (1.00, 1.00, 1.00, 1)),
    "ac":  ((0.84, 0.88, 0.97, 1), (0.85, 0.20, 0.20, 1)),
    "del": ((0.84, 0.88, 0.97, 1), (0.75, 0.45, 0.00, 1)),
}
ACTIVE_STYLE = ((0.98, 0.69, 0.20, 1), (0.10, 0.10, 0.10, 1))

# Screen colours for each theme (main.kv reads them as app.c_xxx)
THEMES = {
    "dark": {
        "bg": (0.04, 0.06, 0.12, 1), "bar": (0.07, 0.10, 0.20, 1),
        "display": (0.07, 0.10, 0.20, 1), "text": (1, 1, 1, 1),
        "expr": (0.85, 0.90, 1.00, 1), "result": (1, 1, 1, 1),
        "status": (0.45, 0.65, 1.00, 1), "error": (1.00, 0.45, 0.45, 1),
        "keys": _DARK_KEYS,
    },
    "light": {
        "bg": (0.92, 0.94, 0.98, 1), "bar": (1, 1, 1, 1),
        "display": (1, 1, 1, 1), "text": (0.08, 0.10, 0.18, 1),
        "expr": (0.30, 0.35, 0.48, 1), "result": (0.05, 0.08, 0.16, 1),
        "status": (0.12, 0.42, 0.95, 1), "error": (0.85, 0.15, 0.15, 1),
        "keys": _LIGHT_KEYS,
    },
}


def current_theme():
    app = MDApp.get_running_app()
    return THEMES.get(getattr(app, "theme_name", "dark"), THEMES["dark"])


class CalcButton(ButtonBehavior, Label):
    """A rounded calculator key. Its look is drawn in main.kv (<CalcButton>)."""

    bg = ColorProperty([0.17, 0.19, 0.27, 1])
    key = StringProperty("")
    style = StringProperty("num")

    def _get_bg_down(self):
        r, g, b, a = self.bg
        d = -0.12 if (r + g + b) > 2.0 else 0.15      # light keys darken when pressed
        return [min(max(r + d, 0), 1), min(max(g + d, 0), 1), min(max(b + d, 0), 1), a]

    bg_down = AliasProperty(_get_bg_down, None, bind=["bg"])

    def apply_style(self, active=False):
        bg, fg = ACTIVE_STYLE if active else current_theme()["keys"][self.style]
        self.bg = bg
        self.color = fg


# ---------------------------------------------------------------------------
# Keypad layouts:  (row height weight, [(label, key, style, width weight), ...])
# Labels may use Kivy markup: [sup]..[/sup] = superscript.
# ---------------------------------------------------------------------------
BASIC_PAD = [
    (1, [("AC", "ac", "ac"), ("DEL", "del", "del"), ("%", "pct", "fn"), ("÷", "÷", "op")]),
    (1, [("7", "7", "num"), ("8", "8", "num"), ("9", "9", "num"), ("×", "×", "op")]),
    (1, [("4", "4", "num"), ("5", "5", "num"), ("6", "6", "num"), ("-", "-", "op")]),
    (1, [("1", "1", "num"), ("2", "2", "num"), ("3", "3", "num"), ("+", "+", "op")]),
    (1, [("0", "0", "num"), (".", ".", "num"), ("=", "eq", "eq", 2)]),
]

SCI_PAD = [
    # --- function keys (same order as a Casio fx-991ES PLUS) ---
    (0.9, [("2nd", "shift", "fn"), ("hyp", "hyp", "fn"), ("DEG", "drg", "fn"),
           ("S<>D", "sfd", "fn"), ("ENG", "eng", "fn")]),
    (1.0, [("sin", "sin", "fn"), ("cos", "cos", "fn"), ("tan", "tan", "fn"),
           ("log", "log", "fn"), ("ln", "ln", "fn")]),
    (1.0, [("√", "sqrt", "fn"), ("x[sup]2[/sup]", "sq", "fn"), ("x[sup]n[/sup]", "pow", "fn"),
           ("x[sup]-1[/sup]", "inv", "fn"), ("n!", "fact", "fn")]),
    (1.0, [("π", "pi", "fn"), ("e", "e", "fn"), ("(", "(", "fn"),
           (")", ")", "fn"), ("Ran#", "ran", "fn")]),
    (1.0, [("nPr", "nPr", "fn"), ("nCr", "nCr", "fn"), ("%", "pct", "fn"),
           ("MR", "mr", "fn"), ("M+", "m+", "fn")]),
    # --- number pad ---
    (1.25, [("7", "7", "num"), ("8", "8", "num"), ("9", "9", "num"),
            ("DEL", "del", "del"), ("AC", "ac", "ac")]),
    (1.25, [("4", "4", "num"), ("5", "5", "num"), ("6", "6", "num"),
            ("×", "×", "op"), ("÷", "÷", "op")]),
    (1.25, [("1", "1", "num"), ("2", "2", "num"), ("3", "3", "num"),
            ("+", "+", "op"), ("-", "-", "op")]),
    (1.25, [("0", "0", "num"), (".", ".", "num"), ("×10[sup]x[/sup]", "x10", "fn"),
            ("Ans", "ans", "fn"), ("=", "eq", "eq")]),
]


def make_labels(shift, hyp, angle):
    """Labels of the keys whose text changes with 2nd / hyp / DEG-RAD-GRAD."""
    sup = lambda t: f"[sup]{t}[/sup]"
    h = "h" if hyp else ""
    inv = sup("-1") if shift else ""
    return {
        "sin": f"sin{h}{inv}",
        "cos": f"cos{h}{inv}",
        "tan": f"tan{h}{inv}",
        "log": "10" + sup("x") if shift else "log",
        "ln": "e" + sup("x") if shift else "ln",
        "sqrt": sup("3") + "√" if shift else "√",
        "sq": "x" + sup("3" if shift else "2"),
        "pow": sup("x") + "√" if shift else "x" + sup("n"),
        "hyp": "Abs" if shift else "hyp",
        "mr": "MC" if shift else "MR",
        "m+": "M-" if shift else "M+",
        "shift": "2nd",
        "drg": angle,
    }


# key -> (normal text, shifted text, kind)
#   kind "value": starts something new     (a number, "(", a function ...)
#   kind "op"   : continues a calculation  (after "=" it continues from Ans)
INSERT = {
    "+": ("+", "+", "op"), "-": ("-", "-", "op"),
    "×": ("×", "×", "op"), "÷": ("÷", "÷", "op"),
    "(": ("(", "(", "value"), ")": (")", ")", "value"),
    "pi": ("π", "π", "value"), "e": ("e", "e", "value"), "ans": ("Ans", "Ans", "value"),
    "log": ("log(", "10^(", "value"), "ln": ("ln(", "e^(", "value"),
    "sqrt": ("√(", "cbrt(", "value"),
    "sq": ("^2", "^3", "op"), "pow": ("^", "root", "op"),
    "inv": ("^(-1)", "^(-1)", "op"), "fact": ("!", "!", "op"), "pct": ("%", "%", "op"),
    "nPr": ("P", "P", "op"), "nCr": ("C", "C", "op"),
    "x10": ("×10^", "×10^", "op"),
    "abs": ("abs(", "abs(", "value"),
}

# Things DEL removes in one go (longest first)
DEL_TOKENS = sorted(
    ["asinh(", "acosh(", "atanh(", "sinh(", "cosh(", "tanh(", "asin(", "acos(",
     "atan(", "sin(", "cos(", "tan(", "log(", "ln(", "abs(", "cbrt(", "√(",
     "10^(", "e^(", "×10^", "^(-1)", "root", "Ans"],
    key=len, reverse=True,
)

ANGLE_CYCLE = {"DEG": "RAD", "RAD": "GRAD", "GRAD": "DEG"}


# ---------------------------------------------------------------------------
# The calculator panel (display + keypads)
# ---------------------------------------------------------------------------
class CalcPanel(BoxLayout):
    mode = StringProperty("basic")          # "basic" or "scientific"
    expr = StringProperty("")
    result = StringProperty("")
    status = StringProperty("DEG")
    labels = DictProperty({})

    shift = BooleanProperty(False)
    hyp = BooleanProperty(False)
    eng = BooleanProperty(False)
    angle = StringProperty("DEG")
    memory = NumericProperty(0)
    places = NumericProperty(-1)            # -1 = automatic, otherwise fixed decimals

    def on_kv_post(self, base_widget):
        # runs once main.kv has built the display and the screens
        self.ans = 0.0
        self.last_value = None
        self.just_evaluated = False
        self.showing_fraction = False
        self.buttons = {}

        self.ids.basic_screen.add_widget(self._build_pad(BASIC_PAD, big_text=True))
        self.ids.sci_screen.add_widget(self._build_pad(SCI_PAD))

        self.bind(shift=self._refresh, hyp=self._refresh, eng=self._refresh,
                  angle=self._refresh, memory=self._refresh)
        self._refresh()

    # ----- building the keypads ------------------------------------------
    def _build_pad(self, pad, big_text=False):
        grid = BoxLayout(orientation="vertical", spacing=dp(6))
        for height, row_cells in pad:
            row = BoxLayout(spacing=dp(6), size_hint_y=height)
            for cell in row_cells:
                label, key, style = cell[:3]
                width = cell[3] if len(cell) > 3 else 1
                btn = CalcButton(text=label, key=key, style=style, size_hint_x=width)
                btn.apply_style()
                if big_text:
                    btn.font_size = "22sp"
                btn.bind(on_press=lambda b: self.press(b.key))
                # a key can exist on both pads (AC, DEL, digits...) -> keep a list
                self.buttons.setdefault(key, []).append(btn)
                row.add_widget(btn)
            grid.add_widget(row)
        return grid

    def _fmt(self, value):
        return format_result(value, self.eng, None if self.places < 0 else int(self.places))

    def restyle(self):
        """Re-colour every key (after a theme change)."""
        self._refresh()
        for btns in self.buttons.values():
            for btn in btns:
                if btn.key not in ("shift", "hyp", "eng"):
                    btn.apply_style()

    def set_places(self, places):
        self.places = places
        if self.last_value is not None and self.just_evaluated:
            self.result = self._fmt(self.last_value)
            self.showing_fraction = False

    # ----- mode ------------------------------------------------------------
    def set_mode(self, mode):
        self.mode = mode
        self.ids.sm.current = mode
        self.shift = False
        self.hyp = False

    # ----- keeping labels / status in sync ----------------------------------
    def _refresh(self, *args):
        self.labels = make_labels(self.shift, self.hyp, self.angle)
        for key, text in self.labels.items():
            for btn in self.buttons.get(key, []):
                btn.text = text
        for key, on in (("shift", self.shift), ("hyp", self.hyp and not self.shift),
                        ("eng", self.eng)):
            for btn in self.buttons.get(key, []):
                btn.apply_style(active=on)

        parts = []
        if self.shift:
            parts.append("2nd")
        if self.hyp:
            parts.append("HYP")
        parts.append(self.angle)
        if self.eng:
            parts.append("ENG")
        if self.memory != 0:
            parts.append("M")
        self.status = "   ".join(parts)

    # ----- key dispatch ------------------------------------------------------
    def press(self, key):
        controls = {
            "shift": self._toggle_shift, "hyp": self._hyp, "drg": self._cycle_angle,
            "sfd": self._sfd, "eng": self._toggle_eng,
            "ac": self._clear, "del": self._delete, "eq": self._equals,
            "mr": self._memory_recall, "m+": self._memory_add,
        }
        if key in controls:
            controls[key]()
            return
        self._insert_key(key)

    def _insert_key(self, key):
        if key.isdigit() or key == ".":
            text, kind = key, "value"
        elif key == "ran":
            text, kind = f"{random.randint(0, 999) / 1000:.3f}", "value"
        elif key in ("sin", "cos", "tan"):
            text = ("a" if self.shift else "") + key + ("h" if self.hyp else "") + "("
            kind = "value"
        else:
            normal, shifted, kind = INSERT[key]
            text = shifted if self.shift else normal
        self._insert(text, kind)
        self.shift = False
        self.hyp = False

    def _insert(self, text, kind):
        if self.just_evaluated:
            self.expr = "Ans" if kind == "op" else ""
            self.just_evaluated = False
        self.result = ""
        self.last_value = None
        self.showing_fraction = False
        # typing + x / ÷ straight after another + x / ÷ just swaps the operator
        if text in ("+", "×", "÷") and self.expr and self.expr[-1] in "+×÷":
            self.expr = self.expr[:-1]
        self.expr += text

    # ----- toggles ---------------------------------------------------------
    def _toggle_shift(self):
        self.shift = not self.shift

    def _hyp(self):
        if self.shift:                       # 2nd + hyp = Abs
            self._insert("abs(", "value")
            self.shift = False
        else:
            self.hyp = not self.hyp

    def _cycle_angle(self):
        self.angle = ANGLE_CYCLE[self.angle]

    def _toggle_eng(self):
        self.eng = not self.eng
        if self.last_value is not None and self.just_evaluated:
            self.result = self._fmt(self.last_value)
            self.showing_fraction = False

    # ----- editing ---------------------------------------------------------
    def _clear(self):
        self.expr = ""
        self.result = ""
        self.last_value = None
        self.just_evaluated = False
        self.showing_fraction = False
        self.shift = False
        self.hyp = False

    def _delete(self):
        self.just_evaluated = False
        self.result = ""
        self.last_value = None
        for token in DEL_TOKENS:
            if self.expr.endswith(token):
                self.expr = self.expr[: -len(token)]
                return
        self.expr = self.expr[:-1]

    # ----- calculating -------------------------------------------------------
    def _evaluate_current(self):
        """Value of the expression (or Ans if the line is empty). None on error."""
        try:
            if not self.expr:
                return self.ans
            return evaluate(self.expr, self.angle, self.ans, self.memory)
        except CalcError as err:
            self.result = str(err)
            self.last_value = None
            return None

    def _equals(self):
        if not self.expr or self.just_evaluated:
            return
        value = self._evaluate_current()
        if value is None:
            return
        self.ans = value
        self.last_value = value
        self.showing_fraction = False
        self.result = self._fmt(value)
        self.just_evaluated = True

        app = MDApp.get_running_app()
        if app is not None and hasattr(app.root, "add_to_history"):
            app.root.add_to_history(self.expr, self.result)

    def _sfd(self):
        """S<>D : switch the last answer between decimal and fraction."""
        if self.last_value is None or not self.just_evaluated:
            return
        if self.showing_fraction:
            self.result = self._fmt(self.last_value)
            self.showing_fraction = False
        else:
            frac = to_fraction(self.last_value)
            if frac:
                self.result = frac
                self.showing_fraction = True

    # ----- memory ------------------------------------------------------------
    def _memory_recall(self):
        if self.shift:                       # 2nd + MR = MC (clear memory)
            self.memory = 0
            self.shift = False
        else:
            self._insert("M", "value")

    def _memory_add(self):
        sign = -1 if self.shift else 1       # 2nd + M+ = M-
        value = self._evaluate_current()
        self.shift = False
        if value is None:
            return
        self.memory += sign * value
        self.ans = value
        self.last_value = value
        self.result = self._fmt(value)
        self.just_evaluated = True


# ---------------------------------------------------------------------------
# Top-level layout: toolbar, menu, history, dialogs
# ---------------------------------------------------------------------------
DECIMAL_CYCLE = [-1, 2, 4, 6, 8]            # -1 = Auto

HELP_TEXT = """
2nd  - press first, then a key:
   sin/cos/tan -> inverse (sin-1 ...)
   log -> 10^x     ln -> e^x
   sqrt -> cube root     x^2 -> x^3
   x^n -> x-th root (type 3, 2nd, x^n, 27)
   MR -> MC (clear memory)     M+ -> M-
   hyp -> Abs

hyp  - sin/cos/tan become sinh/cosh/tanh
DEG  - switch DEG / RAD / GRAD
S<>D - answer as fraction or decimal
ENG  - engineering notation (x10^3, x10^6)
M+   - add result to memory,  MR recalls it
Ans  - last answer (press an operator after = to continue)
nPr / nCr - type 5, nPr, 2
Ran# - random number 0.000 - 0.999
"""


class MainLayout(BoxLayout):

    history = []

    def _app(self):
        return MDApp.get_running_app()

    def add_to_history(self, expression, result):
        self.history.append(f"{expression} = {result}")
        del self.history[:-200]                         # keep the last 200
        self._app().save_state()

    def show_history(self, *args):
        # newest first, last 50 entries
        text = "\n".join(reversed(self.history[-50:]))

        dialog = MDDialog(
            title="History",
            text=text if text else "No calculations yet.",
            buttons=[
                MDFlatButton(
                    text="CLOSE",
                    on_release=lambda x: dialog.dismiss()
                )
            ]
        )

        dialog.open()

    def clear_history(self):
        self.history.clear()
        self._app().save_state()
        if hasattr(self, "menu"):
            self.menu.dismiss()

            dialog = MDDialog(
                title="Success",
                text="History cleared successfully!",
                buttons=[
                    MDFlatButton(
                        text="OK",
                        on_release=lambda x: dialog.dismiss()
                    )
                ]
            )

            dialog.open()

    # ----- the menu ---------------------------------------------------------
    def show_menu(self, caller):
        panel = self.ids.panel
        app = self._app()
        scientific = panel.mode == "scientific"
        decimals = "Auto" if panel.places < 0 else str(int(panel.places))

        menu_items = [
            {"text": "Basic Mode" if scientific else "Scientific Mode",
             "on_release": lambda: self.toggle_mode()},
            {"text": "Light Theme" if app.theme_name == "dark" else "Dark Theme",
             "on_release": lambda: self.toggle_theme()},
            {"text": f"Angle: {panel.angle}",
             "on_release": lambda: self.cycle_angle()},
            {"text": f"Decimals: {decimals}",
             "on_release": lambda: self.cycle_decimals()},
            {"text": "Copy Result",
             "on_release": lambda: self.copy_result()},
            {"text": "Copy History",
             "on_release": lambda: self.copy_history()},
            {"text": "Clear History",
             "on_release": lambda: self.clear_history()},
            {"text": "Help",
             "on_release": lambda: self.help()},
            {"text": "About",
             "on_release": lambda: self.about()},
        ]

        self.menu = MDDropdownMenu(
            caller=caller,
            items=menu_items,
            width_mult=4
        )

        self.menu.open()

    def _close_menu(self):
        if hasattr(self, "menu"):
            self.menu.dismiss()

    def toggle_mode(self):
        """Menu -> Scientific Mode / Basic Mode"""
        self._close_menu()
        panel = self.ids.panel
        panel.set_mode("scientific" if panel.mode == "basic" else "basic")
        self.update_title()
        self._app().save_state()

    def update_title(self):
        self.ids.toolbar.title = (
            "Scientific" if self.ids.panel.mode == "scientific" else "Calculator")

    def toggle_theme(self):
        self._close_menu()
        app = self._app()
        app.apply_theme("light" if app.theme_name == "dark" else "dark")
        app.save_state()

    def cycle_angle(self):
        self._close_menu()
        self.ids.panel._cycle_angle()
        toast(f"Angle unit: {self.ids.panel.angle}")
        self._app().save_state()

    def cycle_decimals(self):
        self._close_menu()
        panel = self.ids.panel
        nxt = DECIMAL_CYCLE[(DECIMAL_CYCLE.index(int(panel.places)) + 1) % len(DECIMAL_CYCLE)]
        panel.set_places(nxt)
        toast("Decimals: Auto" if nxt < 0 else f"Decimals: {nxt}")
        self._app().save_state()

    def copy_result(self):
        self._close_menu()
        text = self.ids.panel.result
        if not text or "ERROR" in text:
            toast("Nothing to copy - press = first")
            return
        Clipboard.copy(text)
        toast(f"Copied {text}")

    def copy_history(self):
        self._close_menu()
        if not self.history:
            toast("History is empty")
            return
        Clipboard.copy("\n".join(reversed(self.history)))
        toast("History copied")

    def help(self):
        self._close_menu()
        dialog = MDDialog(
            title="Scientific keys",
            text=HELP_TEXT,
            buttons=[
                MDFlatButton(
                    text="CLOSE",
                    on_release=lambda x: dialog.dismiss()
                )
            ]
        )
        dialog.open()

    def about(self):
        self._close_menu()
        dialog = MDDialog(
            title="About",
            text="""
        Calculator v1.1

        Developer: Aryan Rai

        Features:
        • Basic Calculator
        • Scientific Calculator
        • History
        • Light / Dark theme
        • Angle unit & decimal places
        • Material Design UI

        Built with:
        Python
        Kivy
        KivyMD
        """,
            buttons=[
                MDFlatButton(
                    text="Close",
                    on_release=lambda x: dialog.dismiss()
                )
            ]
        )

        dialog.open()


# AdMob IDs supplied for Pro Calculator.
ADMOB_APP_ID = "ca-app-pub-1251262394546713~8890574302"
ADMOB_BANNER_ID = "ca-app-pub-1251262394546713/1768044018"


class Calculator(MDApp):
    # colours used by main.kv (changed by apply_theme)
    theme_name = StringProperty("dark")
    c_bg = ColorProperty(THEMES["dark"]["bg"])
    c_bar = ColorProperty(THEMES["dark"]["bar"])
    c_display = ColorProperty(THEMES["dark"]["display"])
    c_text = ColorProperty(THEMES["dark"]["text"])
    c_expr = ColorProperty(THEMES["dark"]["expr"])
    c_result = ColorProperty(THEMES["dark"]["result"])
    c_status = ColorProperty(THEMES["dark"]["status"])
    c_error = ColorProperty(THEMES["dark"]["error"])

    def apply_theme(self, name):
        t = THEMES[name]
        self.theme_name = name
        for key in ("bg", "bar", "display", "text", "expr", "result", "status", "error"):
            setattr(self, "c_" + key, t[key])
        self.theme_cls.theme_style = "Dark" if name == "dark" else "Light"
        if self.root is not None:
            self.root.ids.panel.restyle()

    # ----- saved settings & history (survive closing the app) ---------------
    def _store(self):
        return JsonStore(os.path.join(self.user_data_dir, "procalc.json"))

    def load_state(self):
        try:
            store = self._store()
            return store.get("state") if store.exists("state") else {}
        except Exception:
            return {}

    def save_state(self):
        if self.root is None:
            return
        panel = self.root.ids.panel
        try:
            self._store().put(
                "state",
                theme=self.theme_name,
                mode=panel.mode,
                angle=panel.angle,
                places=int(panel.places),
                history=self.root.history[-200:],
            )
        except Exception:
            pass                                        # never crash on a save problem

    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self._saved = self.load_state()
        theme = self._saved.get("theme", "dark")
        self.apply_theme(theme if theme in THEMES else "dark")
        if platform not in ("android", "ios"):
            # phone-shaped window when testing on a PC
            from kivy.core.window import Window
            Window.size = (390, 800)
        return Builder.load_file("main.kv")

    def on_start(self):
        # KivMob displays a native AdMob banner on Android. It is deliberately
        # skipped on desktop so local development remains usable.
        self._admob = None
        if platform == "android" and KivMob is not None:
            try:
                self._admob = KivMob(ADMOB_APP_ID)
                self._admob.new_banner(ADMOB_BANNER_ID, top_pos=False)
                self._admob.request_banner()
                self._admob.show_banner()
            except Exception as exc:
                # Ads must never prevent the calculator from opening.
                print("AdMob banner could not be initialized:", exc)

        saved, panel = self._saved, self.root.ids.panel
        if saved.get("angle") in ("DEG", "RAD", "GRAD"):
            panel.angle = saved["angle"]
        if saved.get("places") in DECIMAL_CYCLE:
            panel.places = saved["places"]
        if saved.get("mode") == "scientific":
            panel.set_mode("scientific")
            self.root.update_title()
        self.root.history[:] = [str(h) for h in saved.get("history", [])]
        panel.restyle()

    def on_pause(self):
        self.save_state()
        return True                                     # allow Android to pause the app

    def on_stop(self):
        self.save_state()


if __name__ == "__main__":
    Calculator().run()
