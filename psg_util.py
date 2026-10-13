''' Simple wrapper for PySimpleGUI popups '''

from sys import exit
import PySimpleGUI as psg

def get_float(text: str, default: str = '', min: float | None = None, max: float | None = None, return_no_value: bool = False) -> float | None:
    prompt = text
    if min or max:
        if min and not max:
            prompt += f' (>= {min})'
        elif min and max:
            prompt += f' ({min} - {max})'
        elif max and not min:
            prompt += f' (<= {max})'
    while True:
        value = psg.popup_get_text(prompt, default_text = default)
        if value is None:
            if return_no_value:
                return value
            else:
                exit()
        try:
            value = float(value)
        except ValueError:
            psg.popup_timed('Enter a floating point number', auto_close_duration = 5)
            continue
        if min and value < min:
            psg.popup_timed(f'Value must be greater or equal to {min}', auto_close_duration = 5)
        elif max and value > max:
            psg.popup_timed(f'Value must be less than or equal to {max}', auto_close_duration = 5)
        else:
            return value

def get_float_or_exit(text: str, default: str = '', min: float | None = None, max: float | None = None) -> float:
    value: float | None = get_float(text, default, min, max, return_no_value = True)
    if not value:
        exit()
    else:
        return value

def get_int(text: str, default: str = '', min: int | None = None, max: int | None = None, return_no_value: bool = False) -> int | None:
    prompt = text
    if min or max:
        if min and not max:
            prompt += f' (>= {min})'
        elif min and max:
            prompt += f' ({min} - {max})'
        elif max and not min:
            prompt += f' (<= {max})'
    while True:
        value = psg.popup_get_text(prompt, default_text = default)
        if value is None:
            if return_no_value:
                return
            else:
                exit()
        try:
            value = int(value)
        except ValueError:
            psg.popup_timed('Enter an integer number', auto_close_duration = 5    )
            continue
        if min and value < min:
            psg.popup_timed(f'Value must be greater or equal to {min}', auto_close_duration = 5)
        elif max and value > max:
            psg.popup_timed(f'Value must be less than or equal to {max}', auto_close_duration = 5)
        else:
            return value

def get_int_or_exit(text: str, default: str = '', min: int | None = None, max: int | None = None) -> int:
    value: int | None = get_int(text, default, min, max, return_no_value = True)
    if not value:
        exit()
    else:
        return value