import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from aiogram import executor
import stripe

# Настройка логирования
logging.basicConfig(level=logging.INFO)


API_TOKEN = '6310209801:AAFEZQqf40lphnViSEdgZhtGdIjtaY3WBLw'

# Замените 'YOUR_STRIPE_SECRET_KEY' на ваш секретный ключ Stripe
STRIPE_SECRET_KEY = 'YOUR_STRIPE_SECRET_KEY'

# Настройка Stripe
stripe.api_key = STRIPE_SECRET_KEY

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Простые данные о продуктах
products = [
    {"id": 1, "name": "Подписка уровень 1", "price": 10.99},
    {"id": 2, "name": "Подписка уровень 2", "price": 19.99},
    {"id": 3, "name": "Подписка уровень 3", "price": 5.99},
]

# Словарь корзин пользователей
user_carts = {}


# Команда для запуска бота
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    user_carts[user_id] = []  # Инициализация пустой корзины для пользователя

    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(
        "Посмотреть товары", callback_data='view_products'))

    await message.reply("Добро пожаловать в Простой магазин Бот! Используйте меню ниже:", reply_markup=keyboard)


# Команда для просмотра доступных товаров
@dp.callback_query_handler(lambda c: c.data == 'view_products')
async def view_products(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    keyboard = InlineKeyboardMarkup()
    for product in products:
        keyboard.add(InlineKeyboardButton(f"{product['name']} - {product['price']} ₽",
                                          callback_data=f'view_product_{product["id"]}'))

    keyboard.add(InlineKeyboardButton(
        "Посмотреть корзину", callback_data='view_cart'))

    await bot.send_message(user_id, "Вот доступные товары:", reply_markup=keyboard)


# Команда для просмотра подробностей о конкретном товаре
@dp.callback_query_handler(lambda c: c.data.startswith('view_product_'))
async def view_product(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    product_id = int(callback_query.data.split('_')[-1])
    product = next((p for p in products if p['id'] == product_id), None)

    if product:
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("Добавить в корзину",
                     callback_data=f'add_to_cart_{product["id"]}'))

        message_text = f"Товар: {product['name']}\nЦена: {product['price']} ₽"
        await bot.send_message(user_id, message_text, reply_markup=keyboard)
    else:
        await bot.send_message(user_id, "Товар не найден.")


# Команда для добавления товара в корзину пользователя
@dp.callback_query_handler(lambda c: c.data.startswith('add_to_cart_'))
async def add_to_cart(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    product_id = int(callback_query.data.split('_')[-1])
    product = next((p for p in products if p['id'] == product_id), None)

    if product:
        user_carts[user_id].append(product)
        await bot.send_message(user_id, f"{product['name']} добавлен в вашу корзину.")
    else:
        await bot.send_message(user_id, "Товар не найден.")


# Команда для просмотра корзины пользователя
@dp.callback_query_handler(lambda c: c.data == 'view_cart')
async def view_cart(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    user_cart = user_carts[user_id]

    if user_cart:
        total_price = sum(product['price'] for product in user_cart)
        cart_contents = "\n".join(
            [f"{product['name']} - {product['price']} ₽" for product in user_cart])
        message_text = f"Ваша корзина:\n{cart_contents}\n\nИтого: {total_price} ₽"
        payment_button = InlineKeyboardButton(
            "Оплатить", callback_data='pay_now')
        keyboard = InlineKeyboardMarkup().add(payment_button)
        await bot.send_message(user_id, message_text, reply_markup=keyboard)
    else:
        message_text = "Ваша корзина пуста."
        await bot.send_message(user_id, message_text)


# Команда для обработки платежа
@dp.callback_query_handler(lambda c: c.data == 'pay_now')
async def pay_now(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    user_cart = user_carts[user_id]

    if user_cart:
        # Конвертация в центы для Stripe
        total_price = int(sum(product['price'] * 100 for product in user_cart))
        description = ", ".join([product['name'] for product in user_cart])

        prices = [LabeledPrice(label=product['name'], amount=int(
            product['price'] * 100)) for product in user_cart]

        await bot.send_invoice(user_id, title='Оплата заказа',
                               description=description,
                               invoice_payload='some-invoice-payload',
                               provider_token='STRIPE_TOKEN',  # Замените на ваш токен Stripe
                               currency='RUB',
                               prices=prices,
                               need_name=True, need_phone_number=True,
                               need_email=True, is_flexible=False)
    else:
        await bot.send_message(user_id, "Ваша корзина пуста.")


# Обработка успешного платежа
@dp.pre_checkout_query_handler(lambda query: True)
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True,
                                        error_message="Произошла ошибка. Попробуйте снова позже.")


@dp.message_handler(content_types=types.ContentType.SUCCESSFUL_PAYMENT)
async def process_successful_payment(message: types.Message):
    user_id = message.from_user.id
    user_cart = user_carts[user_id]

    # Обработка успешного платежа
    # Здесь вы можете обновить свою базу данных или выполнить любые необходимые действия
    await bot.send_message(user_id, "Спасибо за оплату! Ваш заказ будет обработан.")

    # Очистка корзины пользователя
    user_carts[user_id] = []


# Запуск бота
if __name__ == '__main__':
    from aiogram import executor

    executor.start_polling(dp, skip_updates=True)
