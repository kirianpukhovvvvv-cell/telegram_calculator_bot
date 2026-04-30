import logging
import sqlite3
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from sympy import sympify, N, pi, sin, cos, tan, cot, sqrt, solve, Matrix
import matplotlib.pyplot as plt
from io import BytesIO
import re

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Токен бота
TOKEN = "8763281008:AAGRl6cZWpK0QEDYV2EmeglGMb1R9AjeXuI"

# Инициализация БД для истории
class HistoryDB:
    def __init__(self, db_path="calculator_history.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                expression TEXT,
                result TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def add_record(self, user_id, expression, result):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO history (user_id, expression, result) VALUES (?, ?, ?)",
            (user_id, expression, str(result))
        )
        conn.commit()
        conn.close()

    def get_history(self, user_id, limit=10):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT expression, result FROM history WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
            (user_id, limit)
        )
        records = cursor.fetchall()
        conn.close()
        return records

history_db = HistoryDB()

# Клавиатуры
MAIN_KEYBOARD = ReplyKeyboardMarkup([
    ['7', '8', '9', '/', 'C'],
    ['4', '5', '6', '*', '('],
    ['1', '2', '3', '-', ')'],
    ['0', '.', '+', 'sqrt', 'pi'],
    ['sin', 'cos', 'tan', 'cot', 'e'],
    ['(', ')', '^', '**', '%'],
    ['=', 'History', 'Plot', 'Solve', 'Matrix']
], resize_keyboard=True)

MATRIX_KEYBOARD = ReplyKeyboardMarkup([
    ['[[1,0],[0,1]]', '[[0,1],[1,0]]'],
    ['+', '-', '*'],
    ['Back to main']
], resize_keyboard=True)

PLOT_KEYBOARD = ReplyKeyboardMarkup([
    ['x**2', 'sin(x)', 'cos(x)'],
    ['exp(x)', 'log(x)', 'sqrt(x)'],
    ['Back to main']
], resize_keyboard=True)

def safe_append_expression(current_expr, new_part):
    """Безопасно добавляет часть выражения, избегая дублирования операторов"""
    if current_expr and current_expr[-1] in '+-*/' and new_part in '+-*/':
        # Заменяем последний оператор на новый
        return current_expr[:-1] + new_part
    return current_expr + new_part

def validate_matrix_input(matrix_str):
    """Проверяет корректность ввода матрицы"""
    try:
        matrix = eval(matrix_str)
        if not isinstance(matrix, list):
            return False
        for row in matrix:
            if not isinstance(row, list):
                return False
            if len(row) != len(matrix[0]):  # Все строки одинаковой длины
                return False
        return True
    except:
        return False

def validate_equation_input(equation_str):
    """Проверяет корректность уравнения"""
    if '=' not in equation_str:
        return False, "Уравнение должно содержать знак ="

    left, right = equation_str.split('=', 1)
    try:
        sympify(left)
        sympify(right)
        return True, ""
    except Exception as e:
        return False, f"Ошибка в выражении: {e}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Добро пожаловать в расширенный калькулятор!\n"
        "Используйте кнопки или вводите выражения вручную.\n\n"
        "**Команды:**\n"
        "/history — история вычислений\n"
        "/plot x**2 — построить график\n"
        "/solve x**2-4=0 — решить уравнение\n"
        "/matrix [[1,2],[3,4]]+[[5,6],[7,8]] — матричные операции\n"
        "/deg on/off — переключение между градусами и радианами",
        reply_markup=MAIN_KEYBOARD,
        parse_mode='Markdown'
    )

async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    records = history_db.get_history(user_id)

    if not records:
        await update.message.reply_text("История вычислений пуста.")
        return

    history_text = "\n".join([f"{expr} = {res}" for expr, res in records])
    await update.message.reply_text(f"История вычислений:\n{history_text}")


async def plot_function(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        func_str = update.message.text.replace('/plot ', '')
        x = sympify('x')
        func = sympify(func_str)

        x_vals = [i/10 for i in range(-50, 51)]  # от -5 до 5 с шагом 0.1
        y_vals = [func.subs(x, val).evalf() for val in x_vals]

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

        # Отправляем файл для скачивания
        buf_download = BytesIO(buf.getvalue())
        buf_download.name = f"graph_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        await update.message.reply_photo(photo=buf, caption=f"График функции {func_str}")
        await update.message.reply_document(document=buf_download, filename=buf_download.name)
    except Exception as e:
        await update.message.reply_text(f"Ошибка построения графика: {e}")

async def solve_equation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        eq_str = update.message.text.replace('/solve ', '')
        is_valid, error_msg = validate_equation_input(eq_str)
        if not is_valid:
            await update.message.reply_text(error_msg)
            return

        x = sympify('x')
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

        # Валидация матриц
        if not validate_matrix_input(matrices[0].strip()):
            await update.message.reply_text("Некорректный формат первой матрицы")
            return
        if not validate_matrix_input(matrices[1].strip()):
            await update.message.reply_text("Некорректный формат второй матрицы")
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

async def set_angle_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = update.message.text.replace('/deg ', '').lower()
    if mode == 'on':
        context.user_data['angle_mode'] = 'degrees'
        await update.message.reply_text("Режим углов: градусы", reply_markup=MAIN_KEYBOARD)
    elif mode == 'off':
        context.user_data['angle_mode'] = 'radians'
        await update.message.reply_text("Режим углов: радианы", reply_markup=MAIN_KEYBOARD)
    else:
        await update.message.reply_text("Используйте: /deg on или /deg off")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    current_mode = context.user_data.get('mode', 'main')

    # Обработка режимов клавиатуры
    if current_mode == 'matrix' and user_input == 'Back to main':
        context.user_data['mode'] = 'main'
        await update.message.reply_text("Возвращаемся в основной режим калькулятора.", reply_markup=MAIN_KEYBOARD)
        return
    elif current_mode == 'plot' and user_input == 'Back to main':
        context.user_data['mode'] = 'main'
        await update.message.reply_text("Возвращаемся в основной режим калькулятора.", reply_markup=MAIN_KEYBOARD)
        return

    if user_input == 'C':
        context.user_data['expression'] = ''
        await update.message.reply_text("Очищено.", reply_markup=MAIN_KEYBOARD)
        return

    elif user_input == 'History':
        await show_history(update, context)
        return

    elif user_input == 'Plot':
        context.user_data['mode'] = 'plot'
        await update.message.reply_text(
            "Режим построения графиков. Выберите функцию или введите свою.",
            reply_markup=PLOT_KEYBOARD
        )
        return

    elif user_input == 'Solve':
        await update.message.reply_text("Введите уравнение для решения в формате: /solve x**2 - 4 = 0")
        return

    elif user_input == 'Matrix':
        context.user_data['mode'] = 'matrix'
        await update.message.reply_text(
            "Режим матричных операций. Используйте кнопки для быстрого ввода.",
            reply_markup=MATRIX_KEYBOARD
        )
        return

    elif user_input in ['sin', 'cos', 'tan', 'cot', 'sqrt']:
        # Добавляем открывающую скобку после функции
        current_expr = context.user_data.get('expression', '')
        context.user_data['expression'] = current_expr + user_input + '('
        await update.message.reply_text(
            f"Вы ввели: {context.user_data['expression']}",
            reply_markup=MAIN_KEYBOARD if current_mode == 'main' else (MATRIX_KEYBOARD if current_mode == 'matrix' else PLOT_KEYBOARD)
        )
        return

    elif user_input == '=':
        # Если пользователь нажал '='
        expression = context.user_data.get('expression', '')
        if not expression:
            await update.message.reply_text("Нет выражения для вычисления.", reply_markup=MAIN_KEYBOARD)
            return

        try:
            # Обработка углов в градусах
            angle_mode = context.user_data.get('angle_mode', 'radians')
            if angle_mode == 'degrees':
                # Преобразуем все углы в радианы
                expression = re.sub(r'(sin|cos|tan|cot)\(([^)]+)\)',
                               lambda m: f"{m.group(1)}({m.group(2)}*pi/180)", expression)

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

            # Сохраняем в базу данных
            user_id = update.effective_user.id
            history_db.add_record(user_id, expression, exact_result)

            response = (
                f"Выражение: `{expression}`\n\n"
                f"**Точное значение:** `{exact_result}`\n"
                f"**В виде дроби:** `{fraction_str}`\n"
                f"**Десятичное:** `{decimal_formatted}`"
            )

        except Exception as e:
            response = f"Ошибка в выражении: `{e}`"

        await update.message.reply_text(response, reply_markup=MAIN_KEYBOARD, parse_mode='Markdown')

    else:
        # Для обычных символов
        current_expr = context.user_data.get('expression', '')
        new_expr = safe_append_expression(current_expr, user_input)
        context.user_data['expression'] = new_expr
        await update.message.reply_text(
            f"Вы ввели: {new_expr}",
            reply_markup=MAIN_KEYBOARD if current_mode == 'main' else (MATRIX_KEYBOARD if current_mode == 'matrix' else PLOT_KEYBOARD)
        )

def main():
    application = Application.builder().token(TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("history", show_history))
    application.add_handler(CommandHandler("deg", set_angle_mode))
    application.add_handler(MessageHandler(filters.Regex(r'^/plot'), plot_function))
    application.add_handler(MessageHandler(filters.Regex(r'^/solve'), solve_equation))
    application.add_handler(MessageHandler(filters.Regex(r'^/matrix'), matrix_operation))
    # Обработчик для всех текстовых сообщений, не являющихся командами
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запускаем бота
    print("Бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    main()
