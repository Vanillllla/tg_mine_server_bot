def func(required_arg, *args, **kwargs):
    print(f"Обязательный: {required_arg}")
    print(f"Остальные позиционные: {args}")
    print(f"Именованные: {kwargs}")

func("обязательный", 2, 3, tttttt="value")