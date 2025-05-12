import telebot
from telebot import types
import time
import os
import google.generativeai as genai
import requests # Оставим, может пригодиться для чего-то другого в будущем
import json

# --- Настройка ---
BOT_TOKEN = "7578503522:AAGFv9xDSz6GzlyPcn7L2dUu2H6R3s55YVM" # Ваш токен
GEMINI_API_KEY = "AIzaSyBbG1xlWQyz8VTv3wV7_7Od3YzatnwRWmA" # Ваш Gemini ключ
# Yandex API ключ больше не используется
# YANDEX_API_KEY = "YOUR_YANDEX_ROUTING_API_KEY"

# Конфигурируем Google AI SDK
gemini_configured = False
if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
    print("!!! ВНИМАНИЕ: Не указан Google AI (Gemini) API ключ...")
else:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        print("Google AI (Gemini) SDK успешно сконфигурирован.")
        gemini_configured = True
    except Exception as e:
        print(f"Ошибка конфигурации Google AI (Gemini) SDK: {e}")

bot = telebot.TeleBot(BOT_TOKEN)

# --- УДАЛЕНИЕ WEBHOOK ---
print("Пытаюсь удалить вебхук...")
try:
    webhook_removed = bot.remove_webhook()
    if webhook_removed: print("Вебхук успешно удален.")
    else: print("Вебхук не был установлен или уже удален.")
    time.sleep(0.5)
except Exception as e:
    print(f"Ошибка при удалении вебхука: {e}")

# --- Управление состоянием пользователя ---
user_states = {}
user_data = {}
def set_user_state(chat_id, state): user_states[chat_id] = state; print(f"State for {chat_id} set: {state}")
def get_user_state(chat_id): return user_states.get(chat_id)
def clear_user_state(chat_id):
    user_states.pop(chat_id, None); user_data.pop(chat_id, None)
    print(f"State/data for {chat_id} cleared.")

# --- Тексты сообщений (С ИСПРАВЛЕННЫМИ И ПОЛНЫМИ ТЕКСТАМИ) ---
texts = {
    "welcome": "Привет. Я могу ответить на твои вопросы, либо с помощью ИИ помочь тебе с логистикой! Что выберешь?",
    "questions_menu": "Какой вопрос тебя интересует?", # <--- Убедились, что текст есть
    "logistics_help_start": "Чтобы помочь с логистикой, мне нужны две точки на карте.",
    "ask_ai_prompt": "Задайте свой вопрос для AI (Gemini):",
    "ask_ai_processing": "⏳ Обрабатываю ваш вопрос с помощью AI (Gemini)...",
    "ask_ai_error": "😕 К сожалению, произошла ошибка при обращении к AI (Gemini). Попробуйте позже.",
    "ask_location_1": "📍 Пожалуйста, отправьте первую точку (начальную), используя вложение 'Геопозиция'.",
    "ask_location_2": "📍 Отлично! Теперь отправьте вторую точку (конечную), используя вложение 'Геопозиция'.",
    "ask_logistics_preferences": "Есть ли у вас особые пожелания к перевозке (например, тип груза, приоритет скорости/стоимости, конкретный транспорт)? Напишите их или нажмите 'Пропустить'.",
    "logistics_processing": "⏳ Анализирую логистику с помощью AI (Gemini)... Пожалуйста, подождите.",
    "logistics_error": "😕 Не удалось проанализировать логистику с помощью AI. Возможно, сервис временно недоступен или произошла ошибка.",
    "location_unexpected": "Пожалуйста, используйте кнопку 'Помощь с логистикой' и отправьте геоточку через вложения.",
    "ai_unexpected": "Пожалуйста, используйте кнопку 'Спросить у AI', чтобы задать вопрос.",
    "advantages": "*Какие основные преимущества внедрения AI и IoT в логистику?*\n\nAI и IoT помогают оптимизировать маршруты, снижать операционные расходы, улучшить отслеживание в реальном времени и управлять запасами, что приводит к более быстрым и эффективным поставкам.",
    "integration_steps": "*Какие шаги нужно предпринять для интеграции AI и IoT в существующие логистические процессы?*\n\nДля успешной интеграции AI и IoT необходимо провести аудит текущих процессов, выбрать подходящие технологии, обучить персонал и начать с пилотных проектов. Важно выбрать поставщиков, которые могут обеспечить масштабируемость и совместимость с уже существующими системами.",
    "supply_chain": "*Как AI и IoT помогают в управлении цепочками поставок?*\n\nAI и IoT позволяют отслеживать товары в реальном времени, предсказывать возможные задержки и оптимизировать процессы закупок и доставки, обеспечивая более эффективное управление запасами и минимизацию излишков.",
    "roi": "*Какова типичная окупаемость инвестиций (ROI) при внедрении AI и IoT в логистике?*\n\nROI может быть значительным, благодаря экономии на оптимизации маршрутов, сокращению расхода топлива, снижению операционных сбоев и более эффективному распределению ресурсов. Время на возврат инвестиций будет зависеть от масштаба внедрения."
}

# --- Функции для создания клавиатур ---
def create_main_menu_keyboard(): keyboard = types.InlineKeyboardMarkup(row_width=1); btn_questions = types.InlineKeyboardButton("Помощь с вопросами", callback_data="show_questions"); btn_logistics = types.InlineKeyboardButton("Помощь с логистикой", callback_data="start_logistics"); keyboard.add(btn_questions, btn_logistics); return keyboard
def create_questions_menu_keyboard(): keyboard = types.InlineKeyboardMarkup(row_width=2); btn_advantages = types.InlineKeyboardButton("Преимущества AI", callback_data="show_advantages"); btn_supply_chain = types.InlineKeyboardButton("AI в цепочках поставок", callback_data="show_supply_chain"); btn_integration = types.InlineKeyboardButton("Шаги интеграции", callback_data="show_integration_steps"); btn_roi = types.InlineKeyboardButton("Окупаемость", callback_data="show_roi"); btn_ask_ai = types.InlineKeyboardButton("🤖 Спросить у AI", callback_data="ask_ai"); btn_back_main = types.InlineKeyboardButton("⬅️ Вернуться", callback_data="back_to_main"); keyboard.add(btn_advantages, btn_supply_chain, btn_integration, btn_roi); keyboard.add(btn_ask_ai); keyboard.add(btn_back_main); return keyboard
def create_cancel_keyboard(cancel_callback="back_to_main"): keyboard = types.InlineKeyboardMarkup(row_width=1); btn_cancel = types.InlineKeyboardButton("❌ Отмена", callback_data=cancel_callback); keyboard.add(btn_cancel); return keyboard
def create_back_to_questions_keyboard(): keyboard = types.InlineKeyboardMarkup(row_width=1); btn_back = types.InlineKeyboardButton("⬅️ Назад к вопросам", callback_data="back_to_questions"); keyboard.add(btn_back); return keyboard
def create_back_to_main_menu_keyboard(): keyboard = types.InlineKeyboardMarkup(row_width=1); btn_back = types.InlineKeyboardButton("⬅️ В главное меню", callback_data="back_to_main"); keyboard.add(btn_back); return keyboard
def create_skip_preferences_keyboard(): keyboard = types.InlineKeyboardMarkup(row_width=1); btn_skip = types.InlineKeyboardButton("➡️ Пропустить пожелания", callback_data="skip_logistics_preferences"); btn_cancel = types.InlineKeyboardButton("❌ Отмена (в главное меню)", callback_data="back_to_main"); keyboard.add(btn_skip, btn_cancel); return keyboard

# --- Функция для анализа логистики (ТОЛЬКО AI) ---
def analyze_logistics_with_ai(chat_id, loc1, loc2, preferences=None):
    processing_msg = bot.send_message(chat_id, texts["logistics_processing"])

    if not gemini_configured:
        bot.edit_message_text(chat_id=chat_id, message_id=processing_msg.message_id, text="Извините, сервис AI для анализа логистики сейчас недоступен.", reply_markup=create_back_to_main_menu_keyboard())
        return

    user_preferences_text = f"\n*Пожелания пользователя:* {preferences}" if preferences else "\n*Пожелания пользователя:* Не указаны."

    if preferences:
        prompt = f"""
        Проанализируй логистический маршрут и дай рекомендации, УЧИТЫВАЯ ПОЖЕЛАНИЯ ПОЛЬЗОВАТЕЛЯ.
        Используй свои общие знания о примерных ценах на логистические услуги. Все ценовые оценки должны быть помечены как *(ориентировочно)*.
        Оцени примерное расстояние между точками самостоятельно, если это необходимо для расчетов.

        *Исходные данные:*
        - Точка отправления (широта, долгота): {loc1.latitude}, {loc1.longitude}
        - Точка назначения (широта, долгота): {loc2.latitude}, {loc2.longitude}
        {user_preferences_text}

        *Задачи:*
        1. На основе пожеланий пользователя и общих данных, определи наиболее подходящий вид наземного транспорта.
        2. Оцени примерную ОБЩУЮ стоимость перевозки этим транспортом *(ориентировочно)*. Постарайся разбить оценку на компоненты: расход топлива (исходя из твоего оценочного расстояния и среднего расхода для транспорта), стоимость найма водителя/амортизация/аренда, возможные платные дороги (если предполагаешь их наличие).
        3. Опиши рекомендуемый маршрут в общих чертах (основные трассы, ключевые города, если можешь предположить).
        4. Представь ответ в виде простого текста. Используй базовое Markdown-форматирование для читаемости (например, *жирный текст* для заголовков, - или * для списков). Не используй HTML-теги.
        """
    else: # Если пользователь НЕ указал пожелания
        prompt = f"""
        Проанализируй логистический маршрут и дай РАЗНОСТОРОННИЕ рекомендации, так как пользователь не указал конкретных пожеланий.
        Используй свои общие знания о примерных ценах на логистические услуги. Все ценовые оценки должны быть помечены как *(ориентировочно)*.
        Оцени примерное расстояние между точками самостоятельно, если это необходимо для расчетов.

        *Исходные данные:*
        - Точка отправления (широта, долгота): {loc1.latitude}, {loc1.longitude}
        - Точка назначения (широта, долгота): {loc2.latitude}, {loc2.longitude}

        *Задачи:*
        1. Предложи НЕСКОЛЬКО вариантов наземного транспорта (например, 2-3 варианта), подходящих для перевозки среднестатистического груза (например, 1 тонна, не хрупкий), с разными приоритетами:
           а) Наиболее ДЕШЕВЫЙ вариант.
           б) Наиболее БЫСТРЫЙ вариант (если отличается от дешевого).
           в) Оптимальный БАЛАНС (если есть).
        2. Для КАЖДОГО предложенного варианта транспорта оцени примерную ОБЩУЮ стоимость перевозки *(ориентировочно)*. Постарайся разбить оценку на компоненты: топливо (исходя из твоего оценочного расстояния), водитель/аренда, возможные платные дороги.
        3. Для КАЖДОГО варианта кратко опиши рекомендуемый маршрут (основные трассы, города), если можешь предположить.
        4. Представь ответ в виде простого текста. Используй базовое Markdown-форматирование для читаемости (например, *жирный текст* для заголовков, - или * для списков). Не используй HTML-теги.
        """

    final_response_text = ""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        safety_settings=[ {"category": c, "threshold": "BLOCK_MEDIUM_AND_ABOVE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
        response = model.generate_content(prompt, safety_settings=safety_settings)

        if response.parts:
            final_response_text = response.text
        else:
            block_reason = response.prompt_feedback.block_reason if response.prompt_feedback else "неизвестна"
            final_response_text = texts["logistics_error"] + f"\n(Причина: Ответ AI был заблокирован [{block_reason}] или пуст)"
    except Exception as e:
        print(f"Google AI (Gemini) API Error during logistics analysis: {e}")
        final_response_text = texts["logistics_error"]

    try:
        bot.edit_message_text(chat_id=chat_id, message_id=processing_msg.message_id,
                              text=final_response_text,
                              reply_markup=create_back_to_main_menu_keyboard(),
                              parse_mode="Markdown") # Используем Markdown
    except telebot.apihelper.ApiTelegramException as e:
        print(f"Ошибка парсинга Markdown ответа Gemini (logistics): {e}. Отправляю без форматирования.")
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=processing_msg.message_id,
                                  text=final_response_text,
                                  reply_markup=create_back_to_main_menu_keyboard(),
                                  parse_mode=None)
        except Exception as fallback_e:
            print(f"Не удалось отправить сообщение даже без форматирования: {fallback_e}")
            bot.edit_message_text(chat_id=chat_id, message_id=processing_msg.message_id,text=texts["logistics_error"],reply_markup=create_back_to_main_menu_keyboard())

# --- Обработчики ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    print(f"User {message.from_user.first_name} ({message.chat.id}) started the bot.")
    clear_user_state(message.chat.id); keyboard = create_main_menu_keyboard(); bot.send_message(message.chat.id, texts["welcome"], reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    chat_id = call.message.chat.id; message_id = call.message.message_id; user_name = call.from_user.first_name; callback_data = call.data
    print(f"User {user_name} ({chat_id}) pressed button: {callback_data}"); bot.answer_callback_query(call.id)
    try:
        if callback_data == "ask_ai":
            if not gemini_configured: bot.answer_callback_query(call.id, "Сервис AI недоступен.", show_alert=True); return
            set_user_state(chat_id, 'awaiting_ai_question'); keyboard = create_cancel_keyboard("back_to_questions"); bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=texts["ask_ai_prompt"], reply_markup=keyboard)

        elif callback_data == "show_questions": # <-- ПРОВЕРКА ЭТОГО БЛОКА
            clear_user_state(chat_id)
            keyboard = create_questions_menu_keyboard()
            # Убедимся, что используем правильный ключ и parse_mode не нужен, если в тексте нет разметки
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=texts["questions_menu"], reply_markup=keyboard, parse_mode=None) # Убрали parse_mode для простого текста

        elif callback_data == "start_logistics":
            clear_user_state(chat_id); set_user_state(chat_id, 'awaiting_location_1'); user_data[chat_id] = {}; keyboard = create_cancel_keyboard("back_to_main"); bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=texts["ask_location_1"], reply_markup=keyboard)

        elif callback_data == "skip_logistics_preferences":
            if chat_id in user_data and 'loc1' in user_data[chat_id] and 'loc2' in user_data[chat_id]:
                loc1 = user_data[chat_id]['loc1']; loc2 = user_data[chat_id]['loc2']
                try: bot.delete_message(chat_id, message_id)
                except Exception as e: print(f"Не удалось удалить сообщение skip_prefs: {e}")
                analyze_logistics_with_ai(chat_id, loc1, loc2, preferences=None)
                clear_user_state(chat_id) # Очищаем состояние здесь, т.к. analyze_logistics_with_ai больше не должна этого делать
            else: bot.send_message(chat_id, "Данные о геоточках потеряны...", reply_markup=create_main_menu_keyboard()); clear_user_state(chat_id)

        # --- ОБРАБОТЧИКИ FAQ С MARKDOWN ---
        elif callback_data == "show_advantages": clear_user_state(chat_id); keyboard = create_back_to_questions_keyboard(); bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=texts["advantages"], reply_markup=keyboard, parse_mode="Markdown")
        elif callback_data == "show_integration_steps": clear_user_state(chat_id); keyboard = create_back_to_questions_keyboard(); bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=texts["integration_steps"], reply_markup=keyboard, parse_mode="Markdown")
        elif callback_data == "show_supply_chain": clear_user_state(chat_id); keyboard = create_back_to_questions_keyboard(); bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=texts["supply_chain"], reply_markup=keyboard, parse_mode="Markdown")
        elif callback_data == "show_roi": clear_user_state(chat_id); keyboard = create_back_to_questions_keyboard(); bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=texts["roi"], reply_markup=keyboard, parse_mode="Markdown")
        # ------------------------------------

        elif callback_data == "back_to_questions": clear_user_state(chat_id); keyboard = create_questions_menu_keyboard(); bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=texts["questions_menu"], reply_markup=keyboard, parse_mode=None) # Убрали parse_mode
        elif callback_data == "back_to_main":
            clear_user_state(chat_id); keyboard = create_main_menu_keyboard()
            try: bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=texts["welcome"], reply_markup=keyboard)
            except telebot.apihelper.ApiTelegramException as e:
                 if "message can't be edited" in str(e) or "message to edit not found" in str(e): bot.send_message(chat_id, texts["welcome"], reply_markup=keyboard)
                 else: print(f"Ошибка API при возврате в главное меню (edit): {e}"); bot.send_message(chat_id, texts["welcome"], reply_markup=keyboard)
    except telebot.apihelper.ApiTelegramException as e: print(f"Ошибка API callback: {e}"); bot.answer_callback_query(call.id, text="Ошибка API.")
    except Exception as e: print(f"Непредвиденная ошибка callback: {e}"); bot.answer_callback_query(call.id, text="Внутренняя ошибка.")


@bot.message_handler(content_types=['location'])
def handle_location(message):
    chat_id = message.chat.id; user_name = message.from_user.first_name; current_state = get_user_state(chat_id); location = message.location
    print(f"User {user_name} ({chat_id}) sent location: {location}. Current state: {current_state}")
    if current_state == 'awaiting_location_1':
        user_data[chat_id] = {'loc1': location}; set_user_state(chat_id, 'awaiting_location_2'); keyboard = create_cancel_keyboard("back_to_main")
        try:
             if message.reply_to_message: bot.delete_message(chat_id, message.reply_to_message.message_id)
        except Exception as del_err: print(f"Не удалось удалить сообщ.(1): {del_err}")
        bot.send_message(chat_id, texts["ask_location_2"], reply_markup=keyboard)
    elif current_state == 'awaiting_location_2':
        if chat_id in user_data and 'loc1' in user_data[chat_id]:
            user_data[chat_id]['loc2'] = location; print(f"Received loc2 for {chat_id}: {location}")
            set_user_state(chat_id, 'awaiting_logistics_preferences'); keyboard = create_skip_preferences_keyboard()
            try:
                if message.reply_to_message: bot.delete_message(chat_id, message.reply_to_message.message_id)
            except Exception as del_err: print(f"Не удалось удалить сообщ.(2): {del_err}")
            bot.send_message(chat_id, texts["ask_logistics_preferences"], reply_markup=keyboard)
        else: print(f"Error: State awaiting_location_2, but no loc1 found for chat {chat_id}"); bot.send_message(chat_id, "Произошла ошибка, данные о первой точке потеряны...", reply_markup=create_main_menu_keyboard()); clear_user_state(chat_id); keyboard = create_main_menu_keyboard(); bot.send_message(message.chat.id, texts["welcome"], reply_markup=keyboard)
    else: bot.send_message(chat_id, texts["location_unexpected"])

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id; user_name = message.from_user.first_name; text = message.text; current_state = get_user_state(chat_id)
    print(f"User {user_name} ({chat_id}) sent text: '{text}'. Current state: {current_state}")
    if current_state == 'awaiting_ai_question':
        if not gemini_configured: bot.reply_to(message, "Извините, сервис AI (Gemini) сейчас недоступен."); clear_user_state(chat_id); keyboard = create_questions_menu_keyboard(); bot.send_message(chat_id, texts["questions_menu"], reply_markup=keyboard); return
        processing_msg = bot.reply_to(message, texts["ask_ai_processing"])
        try:
            model = genai.GenerativeModel('gemini-1.5-flash-latest');
            prompt = f"Ответь на вопрос: {text}\n\nИспользуй Markdown для форматирования, если нужно (например, *жирный*, _курсив_, списки с - или *)."
            safety_settings=[ {"category": c, "threshold": "BLOCK_MEDIUM_AND_ABOVE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
            response = model.generate_content(prompt, safety_settings=safety_settings)
            if response.parts: ai_response = response.text
            else: block_reason = response.prompt_feedback.block_reason if response.prompt_feedback else "неизвестна"; ai_response = texts["ask_ai_error"] + f"\n(AI: [{block_reason}])"
            try: bot.edit_message_text(chat_id=chat_id, message_id=processing_msg.message_id, text=ai_response, reply_markup=create_back_to_questions_keyboard(), parse_mode="Markdown")
            except telebot.apihelper.ApiTelegramException as e_tg:
                 if "can't parse entities" in str(e_tg): print(f"Parse Markdown error (text_q): {e_tg}"); bot.edit_message_text(chat_id=chat_id, message_id=processing_msg.message_id, text=ai_response, reply_markup=create_back_to_questions_keyboard(), parse_mode=None)
                 else: print(f"TG API error (text_q): {e_tg}"); bot.edit_message_text(chat_id=chat_id, message_id=processing_msg.message_id, text=texts["ask_ai_error"], reply_markup=create_back_to_questions_keyboard())
        except Exception as e: print(f"Gemini API Error (text q): {e}"); bot.edit_message_text(chat_id=chat_id, message_id=processing_msg.message_id, text=texts["ask_ai_error"], reply_markup=create_back_to_questions_keyboard())
        finally: clear_user_state(chat_id)
    elif current_state == 'awaiting_logistics_preferences':
        if chat_id in user_data and 'loc1' in user_data[chat_id] and 'loc2' in user_data[chat_id]:
            loc1 = user_data[chat_id]['loc1']; loc2 = user_data[chat_id]['loc2']; user_preferences = text.strip()
            user_data[chat_id]['preferences'] = user_preferences
            try:
                 if message.reply_to_message: bot.delete_message(chat_id, message.reply_to_message.message_id)
            except Exception as e: print(f"Не удалось удалить сообщение ask_prefs: {e}")
            analyze_logistics_with_ai(chat_id, loc1, loc2, preferences=user_preferences)
            clear_user_state(chat_id) # Очищаем состояние здесь
        else: bot.send_message(chat_id, "Данные о геоточках потеряны...", reply_markup=create_main_menu_keyboard()); clear_user_state(chat_id)
    elif current_state in ['awaiting_location_1', 'awaiting_location_2']: bot.reply_to(message, "Пожалуйста, отправьте геолокацию...")
    else: pass

# --- Запуск бота ---
if __name__ == '__main__':
    print("Бот запускается в режиме polling...")
    while True:
        try: bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except telebot.apihelper.ApiTelegramException as e: print(f"TG API Error poll: {e}"); time.sleep(15)
        except requests.exceptions.RequestException as e: print(f"Network Error poll: {e}"); time.sleep(30)
        except Exception as e: print(f"Critical Error poll: {e}"); time.sleep(15)
        else: print("Polling stopped."); break
    print("Бот остановлен.")
