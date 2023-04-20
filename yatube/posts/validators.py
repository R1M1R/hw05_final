from django import forms


def validate_not_empty(value):
    if value == "":
        raise forms.ValidationError(
            "Пожалуйста заполните поле текста.",
            params={"value": value},
        )
