#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🍰 ربات تلگرام شیرینی‌فروشی
Sweet Shop Telegram Bot - Full Version
"""

import os
import json
import logging
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ─── تنظیمات ───────────────────────────────────────────────────
BOT_TOKEN = "8713274144:AAG83-hloD0w7qP7TNfSTJDo73h7Io1GhbI"   # توکن ربات از BotFather
ADMIN_IDS = [75294567]              # آیدی عددی ادمین‌ها

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── دیتابیس ساده (فایل JSON) ──────────────────────────────────
DATA_FILE = "shop_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "products": {
            "cakes": [
                {"id": 1, "name": "کیک شکلاتی", "price": 85000, "desc": "کیک شکلاتی خامه‌ای مخصوص", "emoji": "🍫", "available": True},
                {"id": 2, "name": "کیک وانیلی", "price": 75000, "desc": "کیک وانیلی با تزئین توت‌فرنگی", "emoji": "🍓", "available": True},
                {"id": 3, "name": "کیک تولد سفارشی", "price": 150000, "desc": "کیک تولد با طرح دلخواه", "emoji": "🎂", "available": True},
            ],
            "sweets": [
                {"id": 4, "name": "باقلوا", "price": 45000, "desc": "باقلوای تازه با مغز گردو", "emoji": "🥜", "available": True},
                {"id": 5, "name": "زولبیا", "price": 35000, "desc": "زولبیا تازه خانگی", "emoji": "🍯", "available": True},
                {"id": 6, "name": "شیرینی نان برنجی", "price": 55000, "desc": "نان برنجی اصیل ایرانی", "emoji": "🌾", "available": True},
            ],
            "desserts": [
                {"id": 7, "name": "پاناکوتا", "price": 40000, "desc": "پاناکوتای ایتالیایی با سس توت‌فرنگی", "emoji": "🍮", "available": True},
                {"id": 8, "name": "تیرامیسو", "price": 55000, "desc": "تیرامیسوی اصیل با قهوه اسپرسو", "emoji": "☕", "available": True},
                {"id": 9, "name": "چیز کیک", "price": 65000, "desc": "چیز کیک نیویورکی با سس بلوبری", "emoji": "🫐", "available": True},
            ]
        },
        "discount_codes": {
            "SWEET10": {"percent": 10, "active": True, "min_order": 100000},
            "VIP20": {"percent": 20, "active": True, "min_order": 200000},
            "WELCOME": {"percent": 15, "active": True, "min_order": 0},
        },
        "events": [
            {
                "id": 1,
                "title": "🎊 جشنواره شیرینی عید",
                "desc": "تخفیف ویژه ۳۰٪ روی تمام محصولات در ایام عید",
                "date": "۱۴۰۳/۱/۱ تا ۱۴۰۳/۱/۱۳",
                "active": True
            },
            {
                "id": 2,
                "title": "🎂 کارگاه تزئین کیک",
                "desc": "آموزش تزئین کیک با استاد حرفه‌ای - ظرفیت محدود",
                "date": "شنبه ۱۵ فروردین - ساعت ۱۵:۰۰",
                "active": True
            }
        ],
        "orders": [],
        "users": {}
    }

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ─── متغیرهای مکالمه ───────────────────────────────────────────
WAITING_DISCOUNT = 1
WAITING_PHONE = 2
WAITING_ADDRESS = 3
WAITING_PAYMENT = 4

# ─── منوی اصلی ─────────────────────────────────────────────────
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🍰 منوی محصولات", callback_data="menu_products")],
        [InlineKeyboardButton("🛒 سبد خرید", callback_data="menu_cart"),
         InlineKeyboardButton("📦 سفارشات من", callback_data="my_orders")],
        [InlineKeyboardButton("🎫 کد تخفیف", callback_data="menu_discount"),
         InlineKeyboardButton("🎉 ایونت‌ها", callback_data="menu_events")],
        [InlineKeyboardButton("📞 ارتباط با ما", callback_data="contact")]
    ])

def category_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎂 کیک‌ها", callback_data="cat_cakes")],
        [InlineKeyboardButton("🍬 شیرینی‌ها", callback_data="cat_sweets")],
        [InlineKeyboardButton("🍮 دسرها", callback_data="cat_desserts")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]
    ])

# ─── هندلر شروع ────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = load_data()
    
    # ثبت کاربر
    uid = str(user.id)
    if uid not in data["users"]:
        data["users"][uid] = {
            "name": user.full_name,
            "username": user.username,
            "joined": datetime.now().isoformat(),
            "cart": [],
            "discount_code": None
        }
        save_data(data)
    
    welcome_text = (
        f"🍰 *خوش آمدید {user.first_name} عزیز!*\n\n"
        "به شیرینی‌فروشی ما خوش آمدید 🌸\n"
        "بهترین کیک‌ها، شیرینی‌ها و دسرهای خانگی\n\n"
        "از منوی زیر انتخاب کنید:"
    )
    
    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )

# ─── هندلر دکمه‌ها ──────────────────────────────────────────────
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = load_data()
    uid = str(query.from_user.id)
    
    # ─ منوی اصلی ─
    if query.data == "back_main":
        await query.edit_message_text(
            "🏠 *منوی اصلی*\nاز گزینه‌های زیر انتخاب کنید:",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
    
    # ─ محصولات ─
    elif query.data == "menu_products":
        await query.edit_message_text(
            "🛍 *دسته‌بندی محصولات*\nچه چیزی می‌خواید؟",
            parse_mode="Markdown",
            reply_markup=category_keyboard()
        )
    
    elif query.data.startswith("cat_"):
        category = query.data.replace("cat_", "")
        cat_names = {"cakes": "🎂 کیک‌ها", "sweets": "🍬 شیرینی‌ها", "desserts": "🍮 دسرها"}
        products = data["products"].get(category, [])
        
        buttons = []
        for p in products:
            if p["available"]:
                btn_text = f"{p['emoji']} {p['name']} - {p['price']:,} تومان"
                buttons.append([InlineKeyboardButton(btn_text, callback_data=f"product_{p['id']}")])
        buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="menu_products")])
        
        await query.edit_message_text(
            f"*{cat_names.get(category, 'محصولات')}*\nیک محصول انتخاب کنید:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    
    elif query.data.startswith("product_"):
        pid = int(query.data.replace("product_", ""))
        product = find_product(data, pid)
        
        if product:
            text = (
                f"{product['emoji']} *{product['name']}*\n\n"
                f"📝 {product['desc']}\n\n"
                f"💰 قیمت: *{product['price']:,} تومان*"
            )
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 افزودن به سبد", callback_data=f"add_{pid}")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="menu_products")]
            ])
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
    
    elif query.data.startswith("add_"):
        pid = int(query.data.replace("add_", ""))
        product = find_product(data, pid)
        
        if product:
            cart = data["users"][uid]["cart"]
            # بررسی اگر قبلاً در سبد هست
            found = False
            for item in cart:
                if item["id"] == pid:
                    item["qty"] += 1
                    found = True
                    break
            if not found:
                cart.append({"id": pid, "name": product["name"], 
                           "price": product["price"], "qty": 1, "emoji": product["emoji"]})
            save_data(data)
            
            await query.answer(f"✅ {product['name']} به سبد اضافه شد!", show_alert=True)
    
    # ─ سبد خرید ─
    elif query.data == "menu_cart":
        cart = data["users"][uid]["cart"]
        if not cart:
            await query.edit_message_text(
                "🛒 سبد خرید شما خالی است!\n\nاز منوی محصولات خرید کنید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🍰 مشاهده محصولات", callback_data="menu_products")],
                    [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]
                ])
            )
        else:
            total = sum(i["price"] * i["qty"] for i in cart)
            discount_code = data["users"][uid].get("discount_code")
            discount_amount = 0
            
            if discount_code and discount_code in data["discount_codes"]:
                dc = data["discount_codes"][discount_code]
                if dc["active"] and total >= dc.get("min_order", 0):
                    discount_amount = int(total * dc["percent"] / 100)
            
            final_total = total - discount_amount
            
            text = "🛒 *سبد خرید شما:*\n\n"
            for item in cart:
                text += f"{item['emoji']} {item['name']} × {item['qty']} = {item['price']*item['qty']:,} تومان\n"
            text += f"\n💰 جمع: {total:,} تومان"
            if discount_amount:
                text += f"\n🎫 تخفیف: -{discount_amount:,} تومان"
                text += f"\n✅ مبلغ نهایی: *{final_total:,} تومان*"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ ثبت سفارش", callback_data="checkout")],
                [InlineKeyboardButton("🗑 پاک کردن سبد", callback_data="clear_cart")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]
            ])
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
    
    elif query.data == "clear_cart":
        data["users"][uid]["cart"] = []
        data["users"][uid]["discount_code"] = None
        save_data(data)
        await query.answer("🗑 سبد خرید پاک شد", show_alert=True)
        await query.edit_message_text("سبد خرید پاک شد.", reply_markup=main_menu_keyboard())
    
    # ─ ثبت سفارش ─
    elif query.data == "checkout":
        context.user_data["state"] = WAITING_PHONE
        await query.edit_message_text(
            "📱 *ثبت سفارش*\n\nلطفاً شماره موبایل خود را وارد کنید:\n(مثال: 09123456789)",
            parse_mode="Markdown"
        )
    
    # ─ کد تخفیف ─
    elif query.data == "menu_discount":
        context.user_data["state"] = WAITING_DISCOUNT
        await query.edit_message_text(
            "🎫 *کد تخفیف*\n\nکد تخفیف خود را وارد کنید:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]
            ])
        )
    
    # ─ ایونت‌ها ─
    elif query.data == "menu_events":
        events = [e for e in data["events"] if e["active"]]
        if not events:
            text = "🎉 در حال حاضر ایونت فعالی وجود ندارد."
        else:
            text = "🎉 *ایونت‌های فعال:*\n\n"
            for e in events:
                text += f"*{e['title']}*\n"
                text += f"📅 {e['date']}\n"
                text += f"📝 {e['desc']}\n\n"
        
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔔 عضویت در کانال", url="https://t.me/your_channel")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]
            ])
        )
    
    # ─ ارتباط ─
    elif query.data == "contact":
        await query.edit_message_text(
            "📞 *ارتباط با ما:*\n\n"
            "📱 تلفن: ۰۹۱۲۰۰۰۰۰۰۰\n"
            "📍 آدرس: تهران، ...\n"
            "⏰ ساعت کار: ۸ صبح تا ۱۰ شب\n\n"
            "💬 پیام مستقیم به ادمین: @admin_username",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]
            ])
        )
    
    # ─ سفارشات ─
    elif query.data == "my_orders":
        user_orders = [o for o in data["orders"] if o["user_id"] == uid]
        if not user_orders:
            text = "📦 شما هنوز سفارشی ثبت نکرده‌اید."
        else:
            text = "📦 *سفارشات شما:*\n\n"
            for o in user_orders[-5:]:  # آخرین ۵ سفارش
                text += f"🔸 سفارش #{o['id']} - {o['date'][:10]}\n"
                text += f"   💰 {o['total']:,} تومان | وضعیت: {o['status']}\n\n"
        
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]
            ])
        )
    
    # ─ تأیید پرداخت (ادمین) ─
    elif query.data.startswith("confirm_"):
        if query.from_user.id in ADMIN_IDS:
            order_id = query.data.replace("confirm_", "")
            for o in data["orders"]:
                if str(o["id"]) == order_id:
                    o["status"] = "✅ تأیید شد"
                    save_data(data)
                    # اطلاع به مشتری
                    await context.bot.send_message(
                        chat_id=o["user_id"],
                        text=f"🎉 سفارش #{order_id} شما تأیید شد!\nبه زودی آماده می‌شود."
                    )
                    await query.answer("✅ سفارش تأیید شد!")
                    break
    
    elif query.data.startswith("reject_"):
        if query.from_user.id in ADMIN_IDS:
            order_id = query.data.replace("reject_", "")
            for o in data["orders"]:
                if str(o["id"]) == order_id:
                    o["status"] = "❌ رد شد"
                    save_data(data)
                    await context.bot.send_message(
                        chat_id=o["user_id"],
                        text=f"❌ متأسفانه سفارش #{order_id} شما تأیید نشد.\nبرای اطلاعات بیشتر با ما تماس بگیرید."
                    )
                    await query.answer("❌ سفارش رد شد!")
                    break

# ─── هندلر پیام‌های متنی ───────────────────────────────────────
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")
    text = update.message.text
    uid = str(update.effective_user.id)
    data = load_data()
    
    # ─ کد تخفیف ─
    if state == WAITING_DISCOUNT:
        code = text.strip().upper()
        context.user_data["state"] = None
        
        if code in data["discount_codes"]:
            dc = data["discount_codes"][code]
            if dc["active"]:
                data["users"][uid]["discount_code"] = code
                save_data(data)
                await update.message.reply_text(
                    f"🎉 *کد تخفیف اعمال شد!*\n\n"
                    f"✅ کد: `{code}`\n"
                    f"🎫 تخفیف: {dc['percent']}٪\n"
                    f"💰 حداقل سفارش: {dc.get('min_order', 0):,} تومان",
                    parse_mode="Markdown",
                    reply_markup=main_menu_keyboard()
                )
            else:
                await update.message.reply_text("❌ این کد تخفیف منقضی شده.", reply_markup=main_menu_keyboard())
        else:
            await update.message.reply_text("❌ کد تخفیف نامعتبر است.", reply_markup=main_menu_keyboard())
    
    # ─ شماره تلفن برای سفارش ─
    elif state == WAITING_PHONE:
        context.user_data["phone"] = text
        context.user_data["state"] = WAITING_ADDRESS
        await update.message.reply_text(
            "📍 آدرس تحویل را وارد کنید:",
            parse_mode="Markdown"
        )
    
    # ─ آدرس ─
    elif state == WAITING_ADDRESS:
        context.user_data["address"] = text
        context.user_data["state"] = WAITING_PAYMENT
        
        cart = data["users"][uid]["cart"]
        total = sum(i["price"] * i["qty"] for i in cart)
        discount_code = data["users"][uid].get("discount_code")
        discount_amount = 0
        
        if discount_code and discount_code in data["discount_codes"]:
            dc = data["discount_codes"][discount_code]
            if dc["active"] and total >= dc.get("min_order", 0):
                discount_amount = int(total * dc["percent"] / 100)
        
        final_total = total - discount_amount
        context.user_data["final_total"] = final_total
        context.user_data["discount_amount"] = discount_amount
        
        summary = "📋 *خلاصه سفارش:*\n\n"
        for item in cart:
            summary += f"{item['emoji']} {item['name']} × {item['qty']}\n"
        summary += f"\n💰 مبلغ کل: {total:,} تومان"
        if discount_amount:
            summary += f"\n🎫 تخفیف: -{discount_amount:,} تومان"
        summary += f"\n✅ *مبلغ نهایی: {final_total:,} تومان*\n\n"
        summary += "💳 *روش پرداخت:*\n"
        summary += "۱- پرداخت آنلاین\n"
        summary += "۲- پرداخت در محل\n\n"
        summary += "عدد ۱ یا ۲ را وارد کنید:"
        
        await update.message.reply_text(summary, parse_mode="Markdown")
    
    # ─ انتخاب روش پرداخت ─
    elif state == WAITING_PAYMENT:
        context.user_data["state"] = None
        
        if text in ["1", "۱"]:
            payment_method = "آنلاین"
            payment_text = f"💳 *پرداخت آنلاین*\n\nمبلغ {context.user_data['final_total']:,} تومان\n\nبه شماره کارت زیر واریز کنید:\n`6037-XXXX-XXXX-XXXX`\nبه نام: صاحب فروشگاه\n\nپس از پرداخت، تصویر رسید را ارسال کنید."
        elif text in ["2", "۲"]:
            payment_method = "در محل"
            payment_text = "✅ سفارش ثبت شد! پرداخت هنگام تحویل انجام می‌شود."
        else:
            await update.message.reply_text("⚠️ لطفاً ۱ یا ۲ وارد کنید.")
            return
        
        # ثبت سفارش
        cart = data["users"][uid]["cart"]
        order_id = len(data["orders"]) + 1
        order = {
            "id": order_id,
            "user_id": uid,
            "user_name": update.effective_user.full_name,
            "phone": context.user_data.get("phone", ""),
            "address": context.user_data.get("address", ""),
            "items": cart.copy(),
            "total": context.user_data["final_total"],
            "discount": context.user_data.get("discount_amount", 0),
            "payment": payment_method,
            "status": "⏳ در انتظار تأیید",
            "date": datetime.now().isoformat()
        }
        data["orders"].append(order)
        data["users"][uid]["cart"] = []
        data["users"][uid]["discount_code"] = None
        save_data(data)
        
        await update.message.reply_text(
            f"🎉 *سفارش #{order_id} ثبت شد!*\n\n{payment_text}\n\n"
            "به زودی با شما تماس می‌گیریم.",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
        
        # ارسال به ادمین
        for admin_id in ADMIN_IDS:
            admin_text = (
                f"🔔 *سفارش جدید #{order_id}*\n\n"
                f"👤 {update.effective_user.full_name}\n"
                f"📱 {order['phone']}\n"
                f"📍 {order['address']}\n"
                f"💰 {order['total']:,} تومان\n"
                f"💳 {payment_method}\n\n"
            )
            for item in cart:
                admin_text += f"• {item['emoji']} {item['name']} × {item['qty']}\n"
            
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=admin_text,
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("✅ تأیید", callback_data=f"confirm_{order_id}"),
                         InlineKeyboardButton("❌ رد", callback_data=f"reject_{order_id}")]
                    ])
                )
            except Exception as e:
                logger.error(f"Cannot send to admin: {e}")
    
    # ─ دستورات ادمین ─
    elif update.effective_user.id in ADMIN_IDS:
        if text.startswith("/broadcast "):
            msg = text.replace("/broadcast ", "")
            count = 0
            for user_id in data["users"]:
                try:
                    await context.bot.send_message(chat_id=user_id, text=f"📢 *اطلاعیه:*\n\n{msg}", parse_mode="Markdown")
                    count += 1
                except:
                    pass
            await update.message.reply_text(f"✅ پیام به {count} کاربر ارسال شد.")

# ─── دستور broadcast ───────────────────────────────────────────
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if not context.args:
        await update.message.reply_text(
            "⚠️ استفاده:\n/broadcast پیام شما اینجا"
        )
        return
    
    msg = " ".join(context.args)
    data = load_data()
    count = 0
    for user_id in data["users"]:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📢 *اطلاعیه فروشگاه:*\n\n{msg}",
                parse_mode="Markdown"
            )
            count += 1
        except:
            pass
    await update.message.reply_text(f"✅ پیام به {count} کاربر ارسال شد.")

# ─── دستور stats ────────────────────────────────────────────────
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    data = load_data()
    total_orders = len(data["orders"])
    total_revenue = sum(o["total"] for o in data["orders"] if o["status"] != "❌ رد شد")
    total_users = len(data["users"])
    
    await update.message.reply_text(
        f"📊 *آمار فروشگاه:*\n\n"
        f"👥 کاربران: {total_users}\n"
        f"📦 سفارشات: {total_orders}\n"
        f"💰 درآمد کل: {total_revenue:,} تومان",
        parse_mode="Markdown"
    )

# ─── ابزار کمکی ────────────────────────────────────────────────
def find_product(data, pid):
    for category in data["products"].values():
        for p in category:
            if p["id"] == pid:
                return p
    return None

# ─── اجرای ربات ────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    
    print("🍰 ربات شیرینی‌فروشی در حال اجراست...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
