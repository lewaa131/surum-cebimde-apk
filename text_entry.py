"""Kivy 2.3.1 seçim menüsünü Türkçe ve dokunmaya uygun gösterir."""
from kivy.lang import Builder
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from date_entry import format_date_entry, complete_date_entry

Builder.load_string('''
#:import Window kivy.core.window.Window
<TextInputCutCopyPaste>:
    width: min(dp(280), max(dp(100), Window.width - dp(24)))
    height: dp(56)
''')


class MobileTextInput(TextInput):
    def __init__(self, **kwargs):
        kwargs.setdefault('use_bubble', True)
        kwargs.setdefault('use_handles', True)
        # ScrollView replays a tap on release. Its later synthetic touch-up
        # must not immediately dismiss the keyboard that tap just opened.
        kwargs.setdefault('unfocus_on_touch', False)
        kwargs.setdefault('background_normal', '')
        kwargs.setdefault('background_active', '')
        kwargs.setdefault('background_color', (1, 1, 1, 1))
        kwargs.setdefault('foreground_color', (.05, .25, .17, 1))
        kwargs.setdefault('cursor_color', (.08, .45, .29, 1))
        kwargs.setdefault('selection_color', (.25, .65, .43, .35))
        super().__init__(**kwargs)

    def _show_cut_copy_paste(self, *args, **kwargs):
        # Preserve Kivy's long-press timer, scroll cancellation, clipboard,
        # selection handles and popup placement; only translate the labels.
        super()._show_cut_copy_paste(*args, **kwargs)
        if self._bubble is not None:
            for name, text in (('but_cut', 'Kes'), ('but_copy', 'Kopyala'),
                               ('but_paste', 'Yapıştır'), ('but_selectall', 'Tümünü seç')):
                getattr(self._bubble, name).text = text


class DateInput(MobileTextInput):
    def __init__(self, **kwargs):
        kwargs.update(multiline=False, input_type='number', keyboard_suggestions=False)
        kwargs.setdefault('hint_text', 'GG.AA.YYYY · 01.09.2026')
        super().__init__(**kwargs)
        self.bind(focus=self._complete)

    def insert_text(self, substring, from_undo=False):
        if from_undo:
            return super().insert_text(substring, from_undo=True)
        if self.selection_text: self.delete_selection()
        index = self.cursor_index()
        at_end = index == len(self.text)
        # A dot is inserted only when the next segment starts, so backspace
        # remains natural. Explicit separators also accept a one-digit day.
        raw = self.text[:index] + substring + self.text[index:]
        if '.' not in substring and index == len(self.text):
            raw = raw.replace('.', '')
        value = format_date_entry(raw)
        self.text = value
        self.cursor = self.get_cursor_from_index(len(value) if at_end else min(index+len(substring),len(value)))

    def _complete(self, widget, focused):
        if not focused: self.text = complete_date_entry(self.text)


class TagNumberInput(MobileTextInput):
    """Only the twelve digits; the immutable TR prefix is a separate label."""
    def __init__(self, **kwargs):
        kwargs.update(multiline=False, input_type='number', keyboard_suggestions=False)
        kwargs['input_filter'] = self._filter_digits
        super().__init__(**kwargs)
        self.bind(text=self._limit_digits)
        self._limit_digits(self, self.text)

    def _filter_digits(self, value, undo):
        # Reject overflow before insertion so existing trailing digits survive.
        # Kivy removes selected text before invoking the paste/typing filter.
        available = max(0,12-len(self.text))
        return ''.join(c for c in value if c in '0123456789')[:available]

    def _limit_digits(self, widget, value):
        digits = ''.join(c for c in value if c in '0123456789')[:12]
        if value != digits:
            cursor = min(self.cursor_index(), len(digits))
            self.text = digits
            Clock.schedule_once(lambda _:setattr(self, 'cursor', self.get_cursor_from_index(cursor)))
