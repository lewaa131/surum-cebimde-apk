"""Shared font and green controls, including dropdowns and editing bubbles."""
from kivy.lang import Builder

Builder.load_string('''
<Label>:
    font_name: 'Roboto'
<TextInput>:
    font_name: 'Roboto'
<Spinner>:
    background_normal: ''
    background_down: ''
    background_color: .06, .42, .27, 1
    color: 1, 1, 1, 1
<SpinnerOption>:
    background_normal: ''
    background_down: ''
    background_color: .88, .95, .90, 1
    color: .05, .25, .17, 1
    font_name: 'Roboto'
    font_size: dp(15)
    height: dp(48)
<Bubble>:
    background_color: .06, .42, .27, 1
''')
