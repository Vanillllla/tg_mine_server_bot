from manim import *
import numpy as np


class PlottingStats(Scene):
    def construct(self):
        # 1. Настраиваем оси
        # x_range=[min, max, step]
        axes = Axes(
            x_range=[-4, 4, 1],
            y_range=[-1.5, 1.5, 0.5],
            x_length=8,
            y_length=5,
            axis_config={"color": GREY},
            tips=False  # Убрать стрелочки на концах осей
        ).add_coordinates()

        # 2. Строим график
        # axes.plot принимает лямбда-функцию
        sin_curve = axes.plot(lambda x: np.sin(x), color=BLUE)

        sin_label = MathTex("y = \\sin(x)").next_to(sin_curve, UP + RIGHT)

        # 3. Магия ValueTracker
        # Создаем "хранилище" значения X. Стартуем с -3
        t = ValueTracker(-3)

        # 4. Создаем точку, которая зависит от t
        # always_redraw пересоздает объект каждый кадр
        dot = always_redraw(lambda: Dot(
            # c2p берет (x, y) и возвращает координаты на экране
            point=axes.c2p(t.get_value(), np.sin(t.get_value())),
            color=RED
        ))

        # 5. Динамический текст (показания Y)
        # ИСПРАВЛЕНИЕ: Используем параметр number (или позиционный аргумент),
        # параметра num в DecimalNumber нет.
        number_label = always_redraw(lambda: DecimalNumber(
            number=np.sin(t.get_value()),
            num_decimal_places=2,
            color=RED
        ).next_to(dot, UP))

        self.play(Create(axes), Create(sin_curve), Write(sin_label))
        self.add(dot, number_label)

        # 6. Запуск анимации
        # Мы анимируем ТОЛЬКО ValueTracker.
        # Точка и цифра обновятся сами благодаря always_redraw.
        self.play(
            t.animate.set_value(3),
            run_time=4,
            rate_func=linear
        )

        self.wait()