import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from sympy import sympify, N, pi, E, sin, cos, tan, cot, sqrt, solve, Matrix
import matplotlib.pyplot as plt
from io import BytesIO

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Токен бота
TOKEN = "8763281008:AAGRl6cZWpK0QEDYV2EmeglGMb1R9AjeXuI"

# Клавиатура калькулятора
calculator_keyboard = [
    ['7', '8', '9', '/', 'C'],
    ['4', '5', '6', '*', '('],
    ['1', '2', '3', '-', ')'],
    ['0', '.', '+', 'sqrt', 'pi'],
    ['sin', 'cos', 'tan', 'cot', 'e'],
    ['(', ')', '^', '**', '%'],
    ['=', 'History', 'Plot', 'Solve', 'Matrix']
]

reply_markup = ReplyKeyboardMarkup(calculator_keyboard, resize_keyboard=True)

def safe_append_expression(current_expr, new_part):
    """Безопасно добавляет часть выражения, избегая дублирования операторов"""
    if current_expr and current_expr[-1] in '+-*/' and new_part in '+-*/':
        # Заменяем последний оператор на новый
        return current_expr[:-1] + new_part
    return current_expr + new_part

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Добро пожаловать в расширенный калькулятор!\n"
        "Используйте кнопки или вводите выражения вручную.\n\n"
        "**Команды:**\n"
        "/history — история вычислений\n"
        "/plot x**2 — построить график\n"
        "/solve x**2-4=0 — решить уравнение\n"
        "/matrix [[1,2],[3,4]]+[[5,6],[7,8]] — матричные операции",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    history = context.user_data.get('history', [])
    if not history:
        await update.message.reply_text("История вычислений пуста.")
        return

    history_text = "\n".join(history)
    await update.message.reply_text(f"История вычислений:\n{history_text}")

async def plot_function(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Получаем функцию от пользователя
        func_str = update.message.text.replace('/plot ', '')
        x = sympify('x')
        func = sympify(func_str)

        # Создаём массив значений x
        x_vals = [i/10 for i in range(-50, 51)]  # от -5 до 5 с шагом 0.1
        y_vals = [func.subs(x, val).evalf() for val in x_vals]

        # Строим график
        plt.figure(figsize=(10, 6))
        plt.plot(x_vals, y_vals)
        plt.title(f'График функции: {func_str}')
        plt.grid(True)
        plt.axhline(0, color='black', linewidth=0.5)
        plt.axvline(0, color='black', linewidth=0.5)

        # Сохраняем в буфер
        buf = BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()

        await update.message.reply_photo(photo=buf, caption=f"График функции {func_str}")
    except Exception as e:
        await update.message.reply_text(f"Ошибка построения графика: {e}")

async def solve_equation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Получаем уравнение от пользователя
        eq_str = update.message.text.replace('/solve ', '')
        x = sympify('x')
        # Преобразуем строку в уравнение вида f(x) = 0
        equation = sympify(eq_str.replace('=', '-(') + ')')

        solutions = solve(equation, x)
        result = f"Решения уравнения {eq_str}:\n" + "\n".join([str(sol) for sol in solutions])
        await update.message.reply_text(result)
    except Exception as e:
        await update.message.reply_text(f"Ошибка решения уравнения: {e}")

async def matrix_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Пример ввода: /matrix [[1,2],[3,4]] + [[5,6],[7,8]]
        command = update.message.text.replace('/matrix ', '')
        # Разбираем команду на матрицы и операцию
        if '+' in command:
            matrices = command.split('+')
            op = 'add'
        elif '-' in command:
            matrices = command.split('-')
            op = 'sub'
        elif '*' in command:
            matrices = command.split('*')
            op = 'mul'
        else:
            await update.message.reply_text("Поддерживаются операции: +, -, *")
            return

        # Парсим матрицы
        matrix1 = Matrix(eval(matrices[0].strip()))
        matrix2 = Matrix(eval(matrices[1].strip()))

        # Выполняем операцию
        if op == 'add':
            result = matrix1 + matrix2
        elif op == 'sub':
            result = matrix1 - matrix2
        elif op == 'mul':
            result = matrix1 * matrix2

        await update.message.reply_text(f"Результат:\n{result}")
    except Exception as e:
        await update.message.reply_text(f"Ошибка матричной операции: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text

    if user_input == 'C':
        context.user_data['expression'] = ''
        await update.message.reply_text("Очищено.", reply_markup=reply_markup)
        return

    elif user_input == 'History':
        await show_history(update, context)
        return

    elif user_input == 'Plot':
        await update.message.reply_text("Введите функцию для построения графика в формате: /plot x**2")
        return

    elif user_input == 'Solve':
        await update.message.reply_text("Введите уравнение для решения в формате: /solve x**2 - 4 = 0")
        return

    elif user_input == 'Matrix':
        await update.message.reply_text("Введите матричную операцию в формате: /matrix [[1,2],[3,4]] + [[5,6],[7,8]]")
        return

    elif user_input in ['sin', 'cos', 'tan', 'cot', 'sqrt']:
        # Добавляем открывающую скобку после функции
        current_expr = context.user_data.get('expression', '')
        context.user_data['expression'] = current_expr + user_input + '('
        await update.message.reply_text(f"Вы ввели: {context.user_data['expression']}", reply_markup=reply_markup)
        return

    elif user_input == '=':
        # Если пользователь нажал '='
        expression = context.user_data.get('expression', '')
        if not expression:
            await update.message.reply_text("Нет выражения для вычисления.", reply_markup=reply_markup)
            return

        try:
            # Парсим и вычисляем выражение с помощью SymPy
            sympy_expr = sympify(expression)

            # Точное значение (в виде дроби или символьного выражения)
            exact_result = sympy_expr

            # Десятичное значение
            decimal_result = N(sympy_expr)

            # Представление в виде дроби (если возможно)
            try:
                          fraction_result = exact_result.as_numer_denom()
            if fraction_result[1] != 1:
                fraction_str = f"{fraction_result[0]}/{fraction_result[1]}"
            else:
                fraction_str = str(fraction_result[0])
        except:
            fraction_str = "Не представимо в виде простой дроби"

        # Форматируем вывод больших чисел
        def format_large_number(num):
            try:
                num_float = float(num)
                if abs(num_float) > 1e10 or (abs(num_float) < 1e-5 and num_float != 0):
                    return f"{num_float:.2e}"  # Научная нотация
                else:
                    return str(num_float)
            except:
                return str(num)

        decimal_formatted = format_large_number(decimal_result)

        # Сохраняем в историю
        if 'history' not in context.user_data:
            context.user_data['history'] = []

        context.user_data['history'].append(f"{expression} = {exact_result}")
        # Ограничим историю последними 10 вычислениями
        context.user_data['history'] = context.user_data['history'][-10:]

        response = (
            f"Выражение: `{expression}`\n\n"
            f"**Точное значение:** `{exact_result}`\n"
            f"**В виде дроби:** `{fraction_str}`\n"
            f"**Десятичное:** `{decimal_formatted}`"
        )

    except Exception as e:
        response = f"Ошибка в выражении: `{e}`"

    await update.message.reply_text(response, reply_markup=reply_markup, parse_mode='Markdown')

    else:
        # Для обычных символов
        current_expr = context.user_data.get('expression', '')
        new_expr = safe_append_expression(current_expr, user_input)
        context.user_data['expression'] = new_expr
        await update.message.reply_text(f"Вы ввели: {new_expr}", reply_markup=reply_markup)

def main():
    application = Application.builder().token(TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("history", show_history))
    application.add_handler(MessageHandler(filters.Regex(r'^/plot'), plot_function))
    application.add_handler(MessageHandler(filters.Regex(r'^/solve'), solve_equation))
    application.add_handler(MessageHandler(filters.Regex(r'^/matrix'), matrix_operation))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == '__main__':
    main()
