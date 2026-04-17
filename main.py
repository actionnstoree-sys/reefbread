from flask import Flask, request
import requests
import os
import sqlite3
from twilio.rest import Client
import random
app = Flask(__name__)

# ===== Load tokens =====


TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM")

PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WHOLESALE_TELEGRAM_BOT_TOKEN = os.getenv("WHOLESALE_TELEGRAM_BOT_TOKEN")
WHOLESALE_TELEGRAM_CHAT_ID = os.getenv("WHOLESALE_TELEGRAM_CHAT_ID")
TRACKING_BOT_TOKEN = os.getenv("TRACKING_BOT_TOKEN")
TRACKING_CHAT_ID = os.getenv("TRACKING_CHAT_ID")



DB_FILE = "orders.db"  # اسم ملف قاعدة البيانات

BUTTON_REMINDER_MESSAGES = [
    "👇 من فضلك اختر من الأزرار الموجودة تحت للمتابعة.",
    "⚠️ الرسائل المكتوبة لن تعمل هنا، استخدم أحد الأزرار.",
    "😊 لنكمل معًا، اضغط على الاختيار المناسب من الأسفل.",
    "⬇️ اضغط على أحد الأزرار أدناه لإكمال الخطوات.",
    "❗ من فضلك استخدم الأزرار الموجودة أسفل الرسالة.",
    "✨ خطوة سهلة! اختر من الأزرار لتستمر.",
    "🚀 لننطلق! اضغط على أحد الأزرار الموجودة أدناه.",
    "💡 تلميح: الأزرار هي طريقك لإتمام العملية.",
    "🙌 اختر الخيار المناسب من الأزرار أدناه للمتابعة.",
    "🛠️ استخدم أحد الأزرار لإكمال المهمة بنجاح.",
    "🎯 اضغط على أحد الأزرار لتصل مباشرة للمرحلة التالية.",
    "📌 لا يمكننا متابعة الرسائل النصية هنا، استخدم الأزرار.",
    "💚 خطوة بسيطة: اضغط على الاختيار المناسب من الأزرار.",
    "📝 لا يمكن الكتابة هنا، الرجاء اختيار زر.",
    "⚡ اختر بسرعة من الأزرار أدناه لنستمر بدون تأخير.",
    "🎉 كل شيء جاهز! اختر أحد الأزرار للمتابعة.",
    "🚦 لا يمكن إدخال نص الآن، استخدم الاختيارات أسفل الرسالة.",
    "👍 اضغط على أحد الأزرار لإكمال الخطوة التالية.",
    "💫 سهّل على نفسك: استخدم الأزرار لتحديد اختياراتك.",
    "🔔 تذكير ودي: الأزرار هي الطريق الأسرع للمتابعة.",
    "🛎️ اضغط على زر لتتقدم للمرحلة القادمة.",
    "🎁 الأزرار أدناه ستوفر لك تجربة أسهل وأسرع!",
    "🌟 خطوة صغيرة، اضغط على أحد الأزرار لتكمل.",
    "📣 لا يمكن إدخال نص هنا، اختر زر من الأسفل.",
    "💡 نصيحة: الأزرار تجعل العملية أسرع وأسهل!"
]

def send_button_reminder(sender_id):
    msg = random.choice(BUTTON_REMINDER_MESSAGES)
    send_message(sender_id, msg)

def init_db():
    if not os.path.exists(DB_FILE):
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                province TEXT,
                area TEXT,
                street TEXT,
                building TEXT,
                apartment TEXT,
                phone TEXT,
                alt_phone TEXT,
                order_text TEXT,
                total_price TEXT,
                delivery TEXT,
                gift TEXT
            )
            """)
            # جدول الطلبات الجملة
            cursor.execute("""
            CREATE TABLE wholesale_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                province TEXT,
                area TEXT,
                online_shop TEXT,
                phone TEXT,
                activity TEXT,
                quantity TEXT
            )
            """)
            conn.commit()
        print(f"✅ قاعدة البيانات {DB_FILE} جاهزة")
init_db()

# ===== Products =====
PRODUCTS = {
    "خبز الشعير": 53,
    "خبز الكتان": 54,
    "خبز الشوفان": 62,
    "خبز الشيا": 62,
    "الخبز الاسمر": 54,
    "عالي الألياف": 56,
    "عالي البروتين": 69
}

# ===== Users =====
USER_ORDERS = {}

def save_order_to_db(order_data):
    """
    order_data: dict with keys: name, province, area, street, building, apartment, phone, alt_phone, order_text, total_price, delivery, gift
    """
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO orders 
            (name, province, area, street, building, apartment, phone, alt_phone, order_text, total_price, delivery, gift)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_data["name"], order_data["province"], order_data["area"],
            order_data["street"], order_data["building"], order_data["apartment"],
            order_data["phone"], order_data.get("alt_phone", ""),
            order_data["order_text"], order_data["total_price"],
            order_data["delivery"], order_data.get("gift", "")
        ))
        conn.commit()
        print(f"✅ تم حفظ الطلب في قاعدة البيانات")

# استدعاء الدالة عند تشغيل البوت
# ===== Bread Ingredients =====
BREAD_INGREDIENTS = {
    "خبز الشعير": "🟦 خبز الشعير → 53 سعر حراري\nدقيق الشعير\nدقيق القمح حبة كاملة\nخميرة طبيعية\nأملاح البحر بنسبة قليلة\nكل أنواع الخبز خالية من السكر والدهون واللبن والمواد الحافظة",
    "خبز الشوفان": "🟦 خبز الشوفان → 74 سعر حراري\nدقيق الشوفان\nدقيق القمح حبة كاملة\nخميرة طبيعية\nأملاح البحر بنسبة قليلة\nكل أنواع الخبز خالية من السكر والدهون واللبن والمواد الحافظة",
    "خبز الشيا": "🟦 خبز الشيا → 74 سعر حراري\nدقيق بذور الشيا\nدقيق القمح حبة كاملة\nخميرة طبيعية\nأملاح البحر بنسبة قليلة\nكل أنواع الخبز خالية من السكر والدهون واللبن والمواد الحافظة",
    "خبز الكتان": "🟪 خبز بذور الكتان → 77 سعر حراري\nدقيق بذور الكتان\nدقيق القمح حبة كاملة\nخميرة طبيعية\nأملاح البحر بنسبة قليلة\nكل أنواع الخبز خالية من السكر والدهون واللبن والمواد الحافظة",
    "الخبز الاسمر": "🟩 خبز أسمر → 70 سعر حراري\nدقيق القمح حبة كاملة\nنخالة القمح\nقليل من أملاح البحر والخميرة\nكل أنواع الخبز خالية من السكر والدهون واللبن والمواد الحافظة",
    "خبز عالي الألياف": "🟥 خبز عالي الألياف → 61 سعر حراري\nدقيق القمح حبة كاملة\nنخالة القمح\nقليل من أملاح البحر والخميرة\nكل أنواع الخبز خالية من السكر والدهون واللبن والمواد الحافظة",
    "خبز عالي البروتين": "🟧 خبز عالي البروتين → 58 سعر حراري\nبذور الكينوا\nدقيق جوز الهند\nدقيق اللوز\nدقيق القمح حبة كاملة\nقليل من أملاح البحر والخميرة\nكل أنواع الخبز خالية من السكر والدهون واللبن والمواد الحافظة"
}

def send_choose_button_message(sender_id):
    message = (
        "⚠️ من فضلك اختار من الأزرار الموجودة تحت 👇\n"
        "الرسائل المكتوبة مش هتشتغل هنا."
    )

    send_message(sender_id, message)

STAGE_INPUT_TYPE = {
    "welcome": "button",
    "choosing_products": "button",
    "ordering": "button",
    "adding_to_existing": "button",
    "order_found_options": "button",
    "confirm_existing_data": "button",
    "confirm_order": "button",

    "collecting_data": "text",
    "search_distributor": "text",
    "wholesale": "text",
    "track_ask_phone": "text"
}

def send_main_menu(sender_id):
    quick_replies = [
        {"content_type": "text", "title": "ℹ️ استفسار عن منتج", "payload": "INQUIRY_MENU"},
        {"content_type": "text", "title": "🛒 طلب أوردر", "payload": "START_ORDER"},
        {"content_type": "text", "title": "📦 متابعة/تعديل طلبك", "payload": "TRACK_ORDER_MENU"},
        {"content_type": "text", "title": "📍 أماكن توافرنا", "payload": "FIND_DISTRIBUTORS"}, # الزر الجديد
        {"content_type": "text", "title": "🏢 طلبات الجملة", "payload": "INQ_WHOLESALE"}
    ]
    send_quick_replies(sender_id, "مرحباً بك في خبز ريف 💚\nاختر أحد الخيارات:", quick_replies)

def resend_stage_options(sender_id, stage):

    if stage in ["ordering", "adding_to_existing", "choosing_products"]:
        send_products(sender_id)

    elif stage == "order_found_options":
        show_order_options(sender_id)

    elif stage == "confirm_existing_data":
        show_confirm_data_buttons(sender_id)

    elif stage == "confirm_order":
        confirm_order(sender_id)

    elif stage == "welcome":
        send_main_menu(sender_id)


def enforce_button_choice(sender_id, user, text):
    if not text:
        return False

    stage = user.get("stage")

    restricted_stages = [
        "ordering",
        "adding_to_existing",
        "choosing_products",
        "order_found_options",
        "confirm_existing_data",
        "confirm_order"
    ]

    if stage in restricted_stages:

        send_button_reminder(sender_id)

        resend_stage_options(sender_id, stage)

        return True

    return False


def send_telegram_notification(message, bot_token=None, chat_id=None):
    # استخدام المتغيرات اللي أنت عرفتها في أول الكود كقيم افتراضية
    FINAL_TOKEN = bot_token if bot_token else TELEGRAM_BOT_TOKEN
    FINAL_CHAT_ID = chat_id if chat_id else TELEGRAM_CHAT_ID
    
    url = f"https://api.telegram.org/bot{FINAL_TOKEN}/sendMessage"
    payload = {
        "chat_id": FINAL_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        import requests
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        print(f"❌ فشل إرسال إشعار تليجرام: {e}")
def get_user_data_by_phone(phone_number):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name, province, area, street, building, apartment, phone, alt_phone, order_text, total_price, delivery, gift
            FROM orders
            WHERE phone = ?
            ORDER BY id DESC
            LIMIT 1
        """, (phone_number,))
        row = cursor.fetchone()

    if row:
        return {
            "الاسم ثلاثي": row[0],
            "اسم المحافظة": row[1],
            "اسم المنطقة": row[2],
            "اسم الشارع + علامة مميزة": row[3],
            "رقم العمارة": row[4],
            "رقم الشقة": row[5],
            "رقم هاتف ويفضل يكون عليه واتساب": row[6],
            "رقم هاتف اخر (ان وجد)": row[7],
            "الطلب": row[8],
            "الإجمالي بشحن": row[9],
            "التوصيل": row[10],
            "هدية": row[11]
        }
    return None
def update_order_by_phone(phone_number, order_text=None, total_price=None, delivery=None, gift=None):
    fields = []
    values = []
    if order_text is not None:
        fields.append("order_text = ?")
        values.append(order_text)
    if total_price is not None:
        fields.append("total_price = ?")
        values.append(total_price)
    if delivery is not None:
        fields.append("delivery = ?")
        values.append(delivery)
    if gift is not None:
        fields.append("gift = ?")
        values.append(gift)

    if fields:
        values.append(phone_number)
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE orders SET {', '.join(fields)}
                WHERE phone = ?
            """, values)
            conn.commit()
    


def find_order_row_by_phone(phone_number):
    conn = sqlite3.connect("orders.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id FROM orders
        WHERE phone = ?
        ORDER BY id DESC
        LIMIT 1
    """, (phone_number,))

    result = cursor.fetchone()
    conn.close()

    if result:
        return result[0]  # يرجع ID الأوردر
    return None



def save_order(customer_data, order_text, total_price, delivery_text, gift_text):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO orders 
            (name, province, area, street, building, apartment, phone, alt_phone, order_text, total_price, delivery, gift)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            customer_data.get("الاسم ثلاثي", ""),
            customer_data.get("اسم المحافظة", ""),
            customer_data.get("اسم المنطقة", ""),
            customer_data.get("اسم الشارع + علامة مميزة", ""),
            customer_data.get("رقم العمارة", ""),
            customer_data.get("رقم الشقة", ""),
            customer_data.get("رقم هاتف ويفضل يكون عليه واتساب", ""),
            customer_data.get("رقم هاتف اخر (ان وجد)", ""),
            order_text,
            total_price,
            delivery_text,
            gift_text
        ))
        conn.commit()
    print("✅ تم الحفظ في SQLite")
# --- دوال التعامل مع الإكسيل ---




def delete_order_by_phone(phone_number):
    """
    تحذف آخر طلب للعميل بناءً على رقم الهاتف.
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM orders
                WHERE id = (
                    SELECT id FROM orders
                    WHERE phone = ?
                    ORDER BY id DESC
                    LIMIT 1
                )
            """, (phone_number,))
            conn.commit()
        return True
    except Exception as e:
        print(f"❌ فشل حذف الطلب: {e}")
        return False
    
def delete_order_from_excel(order_id):
    try:
        with sqlite3.connect("orders.db") as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM orders WHERE id = ?", (order_id,))
            conn.commit()
        return True
    except Exception as e:
        print("Delete order error:", e)
        return False

def send_wholesale_telegram_notification(text):
    url = f"https://api.telegram.org/bot{WHOLESALE_TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": WHOLESALE_TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"❌ فشل إرسال إشعار الجملة: {e}")


def save_wholesale_to_db(data):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO wholesale_orders 
            (name, province, area, online_shop, phone, activity, quantity)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("الاسم"),
            data.get("المحافظة"),
            data.get("المنطقة"),
            data.get("محل أم أون لاين"),
            data.get("رقم التليفون"),
            data.get("نوع النشاط"),
            data.get("الكمية المطلوبة تقريبا")
        ))
        conn.commit()
    
    # إرسال الإشعار فوراً لبوت الجملة
    admin_msg = (
        "🏢 **طلب انضمام لعملاء الجملة**\n\n"
        f"👤 الاسم: {data.get('الاسم')}\n"
        f"📞 الهاتف: {data.get('رقم التليفون')}\n"
        f"💼 النشاط: {data.get('نوع النشاط')}\n"
        f"📦 الكمية: {data.get('الكمية المطلوبة تقريبا')}"
    )
    send_wholesale_telegram_notification(admin_msg)


####################################
def send_tracking_telegram_notification(text):
    print("--- محاولة إرسال إشعار للمتابعة ---")
    url = f"https://api.telegram.org/bot{TRACKING_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TRACKING_CHAT_ID, 
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        print(f"نتيجة تليجرام: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ خطأ تقني في الاتصال: {e}")
####################################
def normalize_text(text):
    if not text: return ""
    text = text.strip().replace(" ", "") # حذف المسافات
    replacements = {
        "أ": "ا", "إ": "ا", "آ": "ا",
        "ة": "ه", "ى": "ي",
        "ال": "" # حذف ال التعريف للبحث المرن
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

def get_distributors(city_input):
    city = normalize_text(city_input)
    
    # --- الفئة الأولى: محافظات التوصيل المباشر (بدون موزعين) ---
    if any(x in city for x in ["قاهره", "جيزه", "اكتوبر", "تجمع", "شروق"]):
        return "DIRECT_DELIVERY_ONLY" # علامة عشان نرد عليه برد التوصيل المباشر

    # --- الفئة الثانية: المحافظات اللي ليها موزعين (الداتا اللي بعتها) ---
    # المنصورة
    if any(x in city for x in ["منصوره", "دقهليه"]):
        return ("📍 المنصورة (الماركت - العنوان):\n"
                "🏪 قناة السويس - برج الميرلاند\n🏪 المختلط - ش فريدة حسان\n🏪 هايبر مارت - ش سعد زغلول\n🏪 الامام محمد عبده - امام بلاتوه\n🏪 المشاية السفلية - امام جزيرة الورد\n"
                "🏪 الترعة - ش الخلفاء الراشدين\n🏪 طلخا (1،2،3) - ش صلاح سالم والبحر الأعظم\n🏪 أجا - ش بورسعيد\n🏪 بلقاس - خلف بنك مصر\n🏪 شربين - بجوار المركز\n🏪 السنبلاوين - (برايم مارت، نص مشكل)")

    elif "دمياط" in city:
        if "جديده" in city:
            return ("📍 دمياط الجديدة:\n🏪 أسواق القوس (الدولي، المركزية، محبوب)\n🏪 أسواق الحياة - المركزية\n🏪 العمدة - 17\n🏪 أبو عمار - ش أبو الخير\n🏪 البوادي - الأولى\n🏪 السنبايطي - ش باب الحارة")
        else:
            return ("📍 دمياط القديمة:\n🏪 جوهرة هايبر - الشرباصي\n🏪 السيسي/تاج سحل - ش وزير\n🏪 أبو العينين - خلف المحطة\n🏪 الجيار - الشعبية\n🏪 الكانتو/فودة - ش نافع\n🏪 الزيدي - السنانية")

    elif any(x in city for x in ["اسكندريه", "عجمي", "بيطاش", "هانوفيل"]):
        # الإسكندرية فيها الحالتين، هنعرض الموزعين ونقوله متاح توصيل برضه
        return ("📍 الإسكندرية (الموزعين المعتمدين بالطلبات الخارجية):\n1️⃣ هيلثي العجمي\n2️⃣ بيت الجملة (الحديد والصلب)\n3️⃣ زهران (البيطاش)\n4️⃣ فتح الله (ستار، الهانوفيل، أبو يوسف)\n5️⃣ أبو الفضل (عين شمس، السماليهي)\n6️⃣ كارفور العروبة\n\n💡 علماً بأن خدمة التوصيل للمنازل متاحة أيضاً في الإسكندرية.")

    elif "اسماعيليه" in city:
        return "📍 الإسماعيلية:\n🏪 (العمدة، أهل الصفقة، نقاوة، بيتي وان، التعارف، ستار، سلمى، زياد، خديجة، عيد، الحياة، رينا، الحجاز، الفلسطيني، باندا، الغنيمي، العائلة، الدنيا بخير، الوفاء)"

    elif any(x in city for x in ["قليوبيه", "بنها", "طوخ", "قناطر", "منوفيه", "شبين", "سادات", "اشمون"]):
        return "📍 القليوبية والمنوفية:\n📞 للتواصل مع الموزع المعتمد: 01090468901"

    elif "محله" in city: return "📍 المحلة: هيبي سايد"
    elif "دسوق" in city or "كفر الشيخ" in city: return "📍 كفر الشيخ:\n🏪 دسوق (هيبي فود)\n🏪 كفر الشيخ (هيبي ميك)\n📞 خدمة التوصيل: 01113398933"
    elif "اسيوط" in city: return "📍 أسيوط: هيبي لايف / ثلاجة الحرمين"
    elif "بني سويف" in city: return "📍 بني سويف: بن سليمان"
    elif "بورسعيد" in city: return "📍 بورسعيد: أون سبورت"
    elif "ميت غمر" in city: return "📍 ميت غمر: الكانت"
    elif "شرم" in city: return "📍 شرم الشيخ: All In One Market"
    elif "سيناء" in city or "عريش" in city: return "📍 شمال سيناء:\n🏪 منفذ العريش (بجوار مسجد النصر)\n📞 التواصل: 01098949491 / 01221346226"
    elif "قنا" in city: return "📍 قنا:\n📞 أرقام خدمة التوصيل: 01553344300 / 01015401540"
    elif "بحيره" in city: return "📍 البحيرة:\n📞 رقم الموزع: 01558830006"

    # --- الفئة الثالثة: خارج النطاق ---
    return "OUT_OF_SCOPE"


def send_message(recipient_id, text):
    url = f"https://graph.facebook.com/v16.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    try:
        response = requests.post(url, json=payload)
        print(f"Facebook Messenger status: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ فشل إرسال رسالة فيسبوك: {e}")

def send_quick_replies(recipient_id, text, quick_replies):
    url = f"https://graph.facebook.com/v16.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text, "quick_replies": quick_replies}}
    try:
        response = requests.post(url, json=payload)
        print(f"Facebook Messenger status: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ فشل إرسال Quick Replies فيسبوك: {e}")




def send_welcome(sender_id):
    text = (
        "شكراً لتواصلك مع خبز ريف 💚\n\n"
        "🎉 عرض رمضان:\n"
        "عند طلب 5 أكياس ➜ التوصيل مجاني 🚚\n"
        "عند طلب 8 أكياس ➜ التوصيل مجاني + كيس هدية 🎁"
    )
    quick_replies = [
        {"content_type": "text", "title": "ℹ️ استفسار عن منتج", "payload": "INQUIRY_MENU"},
        {"content_type": "text", "title": "🛒 طلب أوردر", "payload": "START_ORDER"},
        {"content_type": "text", "title": "📦 متابعة/تعديل طلبك", "payload": "TRACK_ORDER_MENU"},
        {"content_type": "text", "title": "📍 أماكن توافرنا", "payload": "FIND_DISTRIBUTORS"}, # الزر الجديد
        {"content_type": "text", "title": "🏢 طلبات الجملة", "payload": "INQ_WHOLESALE"}
    ]
    send_quick_replies(sender_id, text, quick_replies)



def handle_message(sender_id, message):


    user = USER_ORDERS.get(sender_id)
    if not user:
        # المستخدم جديد، انشئ بيانات له وأرسل الترحيب
        USER_ORDERS[sender_id] = {"stage": "welcome"}
        send_welcome(sender_id)
        return
    user = USER_ORDERS.get(sender_id)  # حدث user بعد الإنشاء
    text = message.get("text", "").strip()
    if not text:
        return

    current_stage = user.get("stage", "welcome")

    # لو المرحلة هي "welcome" (أول رسالة) أرسل الترحيب مباشرة وتوقف هنا
    if current_stage == "welcome":
        send_welcome(sender_id)
        return

    # هنا تستمر باقي منطق التعامل مع الرسائل، مثل التأكد من نوع الإدخال (زر أو نص)
    # ...
    allowed_input = STAGE_INPUT_TYPE.get(current_stage, "text")
    # ===== تحقق Button Lock =====
    if allowed_input == "button":
        send_message(sender_id, "🚫 الرجاء استخدام الأزرار المتاحة فقط.")
        send_button_reminder(sender_id)

        # إعادة عرض الخيارات حسب المرحلة
        if current_stage in ["ordering", "adding_to_existing", "choosing_products"]:
            send_products(sender_id)
        elif current_stage == "order_found_options":
            show_order_options(sender_id)
        elif current_stage == "confirm_existing_data":
            show_confirm_data_buttons(sender_id)
        elif current_stage == "confirm_order":
            confirm_order(sender_id)
        return  # منع استمرار تنفيذ الدالة

    # ===============================
    # 1️⃣ جمع بيانات الأوردر العادي
    # ===============================
    if current_stage == "collecting_data":
        field = user["data_fields"][user["current_question"]]

        # فحص رقم الهاتف
        if field == "رقم هاتف ويفضل يكون عليه واتساب":
            if not (text.isdigit() and len(text) == 11):
                send_message(sender_id, "🚫 رقم غير صحيح! ارسل رقم صحيح مكون من 11 رقم.")
                return

            existing_data = get_user_data_by_phone(text)
            if existing_data:
                user["customer_data"] = existing_data
                user["stage"] = "confirm_existing_data"

                summary = (
                    f"👋 أهلاً بك من جديد يا {existing_data.get('الاسم ثلاثي', 'عميلنا العزيز')}!\n"
                    f"📍 العنوان المسجل: {existing_data.get('اسم المحافظة')} - {existing_data.get('اسم المنطقة')}\n"
                    "هل تريد استخدام نفس البيانات السابقة؟"
                )

                quick_replies = [
                    {"content_type": "text", "title": "✅ نعم، استخدمها", "payload": "USE_OLD_DATA"},
                    {"content_type": "text", "title": "✏️ لا، بيانات جديدة", "payload": "RE-ENTER_DATA"}
                ]

                send_quick_replies(sender_id, summary, quick_replies)
                return

        # فحص المحافظات، المناطق، وحفظ البيانات كما في الكود الأصلي
        # ... (استمر بالكود الحالي لبقية الأسئلة)

        # فحص المحافظة
        if field == "اسم المحافظة":
            allowed = [
                "القاهرة","قاهره","قاهرة","القاهره",
                "الجيزة","الجيزه",
                "الاسكندرية","الاسكندريه","الإسكندرية","إسكندرية",
                "القليوبية","قليوبية","قليوبيه","القليوبيه"
            ]

            if text not in allowed:
                send_message(sender_id, "❌ نأسف 🙏 المحافظة خارج نطاق التوصيل المباشر حالياً.")
                user["stage"] = "FIND_DISTRIBUTORS"
                send_message(sender_id, "📍 يمكنك الاطلاع على أماكن موزعينا المتاحة من خلال الضغط على خيار 'أماكن توافرنا' بالأسفل 👇")
                send_main_menu(sender_id)
                return

        # فحص خاص بالقليوبية
        if field == "اسم المنطقة":
            gov = user["customer_data"].get("اسم المحافظة", "")
            allowed_qalyubia = ["العبور", "شبرا الخيمة", "شبرا الخيمه", "الخصوص"]

            if "قليوبية" in gov or "القليوبية" in gov:
                if text not in allowed_qalyubia:
                    msg = (
                        f"عذراً، منطقة '{text}' في القليوبية متاح لها موزعين فقط حالياً. 😔\n\n"
                        "المناطق المتاحة للتوصيل المباشر: (العبور - شبرا الخيمة - الخصوص).\n"
                        "يمكنك البحث عن أقرب موزع لك من القائمة الرئيسية."
                    )
                    send_message(sender_id, "❌ نأسف 🙏 المحافظة خارج نطاق التوصيل المباشر حالياً.")
                    user["stage"] = "FIND_DISTRIBUTORS"
                    send_message(sender_id, "📍 يمكنك الاطلاع على أماكن موزعينا المتاحة من خلال الضغط على خيار 'أماكن توافرنا' بالأسفل 👇")
                    send_main_menu(sender_id)
                    return

        # حفظ البيانات والانتقال للسؤال التالي
        user["customer_data"][field] = text
        user["current_question"] += 1

        if user["current_question"] < len(user["data_fields"]):
            ask_next_question(sender_id)
        else:
            user["stage"] = "choosing_products"
            send_products(sender_id)
        return

    # ===============================
    # 2️⃣ البحث عن الموزعين
    # ===============================
    elif user["stage"] == "search_distributor":
        result = get_distributors(text)

        if result == "DIRECT_DELIVERY_ONLY":
            send_message(sender_id, "📍 هذه المنطقة متاح بها توصيل للمنازل فقط.\nاضغط '🛒 طلب أوردر' للبدء.")
        elif result == "OUT_OF_SCOPE":
            send_message(sender_id, "بعتذر لحضرتك ولكن منطقة حضرتك خارج حيز التوصيل حالياً. 😔")
        else:
            send_message(sender_id, result)

        user["stage"] = "welcome"
        send_main_menu(sender_id)
        return

    # ===============================
    # 3️⃣ بيانات الجملة (Wholesale)
    # ===============================
    elif user["stage"] == "wholesale":
        fields = user.get("wholesale_fields", [])
        current_idx = user.get("current_wholesale_question", 0)

        if current_idx < len(fields):
            user["wholesale_data"][fields[current_idx]] = text
            user["current_wholesale_question"] += 1

            if user["current_wholesale_question"] < len(fields):
                next_q = fields[user["current_wholesale_question"]]
                send_message(sender_id, f"من فضلك اكتب {next_q}:")
            else:
                # ✅ الحفظ في SQLite بدل Excel
                save_wholesale_to_db(user["wholesale_data"])

                send_message(sender_id, "✅ تم تسجيل بياناتك بنجاح. سيتواصل معك قسم الجملة قريباً. 💚")

                user["stage"] = "welcome"
                user["current_wholesale_question"] = 0
                user["wholesale_data"] = {}

                send_main_menu(sender_id)
        else:
            user["stage"] = "welcome"
            user["current_wholesale_question"] = 0
            send_main_menu(sender_id)

        return

    # ===============================
    # 4️⃣ تتبع / تعديل طلب
    # ===============================
    elif user["stage"] == "track_ask_phone":

        if not (text.isdigit() and len(text) == 11):
            send_message(sender_id, "🚫 رقم غير صحيح! ارسل رقم صحيح مكون من 11 رقم.")
            return

        existing_data = get_user_data_by_phone(text)

        if existing_data:
            last_order_details = existing_data.get('الطلب', 'لا يوجد طلبات سابقة')

            user["customer_data"] = existing_data
            user["temp_phone"] = text
            user["stage"] = "order_found_options"

            summary = (
                f"✅ تم العثور على بياناتك يا {existing_data.get('الاسم ثلاثي', 'فندم')}!\n"
                f"📍 العنوان: {existing_data.get('اسم المحافظة')} - {existing_data.get('اسم المنطقة')}\n"
                f"📦 أخر أوردر ليك كان: ({last_order_details})\n\n"
                "كيف يمكننا مساعدتك اليوم؟"
            )

            quick_replies = [
                {"content_type": "text", "title": "🔍 استفسار عن الحالة", "payload": "TRACK_INQUIRY"},
                {"content_type": "text", "title": "➕ إضافة أصناف", "payload": "MODIFY_ORDER_MENU"},
                {"content_type": "text", "title": "❌ إلغاء الطلب", "payload": "CANCEL_EXISTING_ORDER"},
                {"content_type": "text", "title": "🏠 القائمة الرئيسية", "payload": "MAIN_MENU"}
            ]

            send_quick_replies(sender_id, summary, quick_replies)

        else:
            msg = (
                "لم نجد أي طلبات مسجلة بهذا الرقم حالياً 🧐\n\n"
                "ربما تم كتابة الرقم بشكل خاطئ؟ أو ربما لم تجرب طعم 'خبز ريف' حتى الآن! 💚✨\n"
                "يسعدنا جداً أن تنضم إلينا وتطلب أوردرك الأول الآن."
            )

            quick_replies = [
                {"content_type": "text", "title": "🛒 اطلب أوردر جديد", "payload": "START_ORDER"},
                {"content_type": "text", "title": "🔢 تجربة رقم آخر", "payload": "TRACK_ORDER_MENU"},
                {"content_type": "text", "title": "🏠 العودة للرئيسية", "payload": "MAIN_MENU"}
            ]

            send_quick_replies(sender_id, msg, quick_replies)

        return

    # ===============================
    # 5️⃣ الرجوع للرئيسية
    # ===============================
    if user["stage"] == "welcome" or text.lower() in ["menu", "القائمة", "الرئيسية"]:
        send_welcome(sender_id)


def send_inquiry_options(sender_id):
    quick_replies = [
        {"content_type": "text", "title": "1️⃣ الأسعار", "payload": "INQ_PRICES"},
        {"content_type": "text", "title": "2️⃣ العروض المتاحة", "payload": "INQ_OFFERS"},
        {"content_type": "text", "title": "3️⃣ مكونات الخبز", "payload": "INQ_INGREDIENTS"},
        {"content_type": "text", "title": "4️⃣ كيفية حفظ المنتج", "payload": "INQ_STORAGE"},
        {"content_type": "text", "title": "5️⃣ الجلوتين", "payload": "INQ_GLUTEN"},
        {"content_type": "text", "title": "🏠 العودة للقائمة الرئيسية", "payload": "MAIN_MENU"}
    ]

    send_quick_replies(sender_id, "اختر نوع الاستفسار:", quick_replies)

def handle_inquiry(sender_id, payload):

    user = USER_ORDERS.get(sender_id)
    if not user:
        return

    # =============================
    # 💰 الأسعار
    # =============================
    if payload == "INQ_PRICES":
        text = (
            "💰 أسعار الخبز:\n"
            "خبز الشعير: 53 جنيه\n"
            "خبز الشوفان: 62 جنيه\n"
            "خبز الشيا: 62 جنيه\n"
            "خبز الكتان: 54 جنيه\n"
            "خبز أسمر: 54 جنيه\n"
            "خبز عالي الألياف: 56 جنيه\n"
            "خبز عالي البروتين: 69 جنيه"
        )
        send_message(sender_id, text)

    # =============================
    # 🎉 العروض
    # =============================
    elif payload == "INQ_OFFERS":
        text = (
            "🎉 عروض رمضان المبارك:\n"
            "✅ التوصيل مجاني عند طلب 5 أكياس\n"
            "✅ كيس هدية + توصيل مجاني عند طلب 8 أكياس"
        )
        send_message(sender_id, text)

    # =============================
    # 🥖 مكونات الخبز
    # =============================
    elif payload == "INQ_INGREDIENTS":

        quick_replies = []

        for bread_name in BREAD_INGREDIENTS.keys():
            quick_replies.append({
                "content_type": "text",
                "title": bread_name,
                "payload": f"ING_{bread_name}"
            })

        quick_replies.append({
            "content_type": "text",
            "title": "🏠 القائمة الرئيسية",
            "payload": "MAIN_MENU"
        })

        send_quick_replies(sender_id, "اختر نوع الخبز لعرض المكونات 👇", quick_replies)
        return

    # =============================
    # 📦 التخزين
    # =============================
    elif payload == "INQ_STORAGE":
        text = (
            "📦 كيفية حفظ المنتج:\n"
            "❄️ في الفريزر: حتى 6 أشهر\n"
            "🧊 في الثلاجة: حتى شهر\n"
            "🌡️ خارج الثلاجة: حتى 10 أيام\n"
            "⏳ بعد الخروج من الفريزر/الثلاجة يُترك دقائق بدون تسخين"
        )
        send_message(sender_id, text)

    # =============================
    # 🌾 الجلوتين
    # =============================
    elif payload == "INQ_GLUTEN":
        text = (
            "أهم المعلومات الصحية عن خبز ريف 🌱\n"
            "- جميع الأنواع خالية تمامًا من الدقيق الأبيض\n"
            "- تحتوي الأنواع على نسبة دقيق أسمر لا تتعدّى 15% للباكيت\n"
            "- نسبة الجلوتين منخفضة جدًا (لا تتعدّى 15%)\n\n"
            "خبز ريف اختيار صحي ومتوازن ومناسب لأنظمة غذائية مختلفة 💚"
        )
        send_message(sender_id, text)

    # =============================
    # 🏢 الجملة
    # =============================
    elif payload == "INQ_WHOLESALE":

        user["stage"] = "wholesale"
        user["wholesale_data"] = {}
        user["wholesale_fields"] = [
            "الاسم",
            "المحافظة",
            "المنطقة",
            "رقم التليفون"
        ]
        user["current_wholesale_question"] = 0

        send_message(sender_id, "من فضلك اكتب الاسم:")
        return

    # =============================
    # 🏠 القائمة الرئيسية
    # =============================
    elif payload == "MAIN_MENU":
        send_main_menu(sender_id)
        return

    # =============================
    # 🔘 أزرار المتابعة بعد أي استفسار
    # =============================
    quick_replies = [
        {"content_type": "text", "title": "🛒 طلب أوردر", "payload": "START_ORDER"},
        {"content_type": "text", "title": "🔙 القائمة السابقة", "payload": "INQUIRY_MENU"},
        {"content_type": "text", "title": "🏠 القائمة الرئيسية", "payload": "MAIN_MENU"}
    ]

    send_quick_replies(sender_id, "اختر أحد الخيارات:", quick_replies)


def process_order_action(sender_id, action_type):
    user = USER_ORDERS.get(sender_id)
    if not user:
        return

    data = user.get("customer_data", {})

    # تحديد الإيموجي حسب نوع الإجراء
    header_emoji = "⚠️" if action_type == "إلغاء" else "❓"

    admin_msg = (
        f"{header_emoji} طلب {action_type} أوردر قائم!\n\n"
        "👤 بيانات العميل:\n"
        f"الاسم ثلاثي: {data.get('الاسم ثلاثي', '')}\n"
        f"المحافظة: {data.get('اسم المحافظة', '')}\n"
        f"المنطقة: {data.get('اسم المنطقة', '')}\n"
        f"الشارع + علامة مميزة: {data.get('اسم الشارع + علامة مميزة', '')}\n"
        f"رقم العمارة: {data.get('رقم العمارة', '')}\n"
        f"رقم الشقة: {data.get('رقم الشقة', '')}\n"
        f"رقم الهاتف الأساسي: {data.get('رقم هاتف ويفضل يكون عليه واتساب', '')}\n"
        f"رقم هاتف آخر: {data.get('رقم هاتف اخر (ان وجد)', '')}\n\n"
        "📦 تفاصيل آخر أوردر:\n"
        f"{data.get('الطلب', 'غير متوفر')}\n"
        "-----------------\n"
        f"🛠️ نوع الإجراء المطلوب: {action_type}"
    )

    # إرسال لجروب المتابعة
    try:
        send_telegram_notification(
            admin_msg,
            TRACKING_BOT_TOKEN,
            TRACKING_CHAT_ID
        )
    except Exception as e:
        print("Telegram Error:", e)

    # الرد على العميل
    if action_type == "إلغاء":
        response_text = "✅ تم إرسال طلب الإلغاء للإدارة وسيتم التأكيد معك قريباً. 💚"
    else:
        response_text = "✅ تم إرسال استفسارك لقسم المتابعة وسيتم الرد عليك فوراً. 💚"

    send_message(sender_id, response_text)

    # إعادة تعيين الحالة
    user["stage"] = "welcome"
    send_main_menu(sender_id)


def handle_postback(sender_id, postback):

    payload = postback.get("payload")
    if not payload:
        return

    # تأمين وجود المستخدم
    if sender_id not in USER_ORDERS:
        USER_ORDERS[sender_id] = {}

    user = USER_ORDERS[sender_id]

    # =============================
    # 🛒 بدء أوردر جديد
    # =============================
    if payload == "START_ORDER":

        USER_ORDERS[sender_id] = {
            "items": {},
            "data_fields": [
                "رقم هاتف ويفضل يكون عليه واتساب",
                "الاسم ثلاثي",
                "اسم المحافظة",
                "اسم المنطقة",
                "اسم الشارع + علامة مميزة",
                "رقم العمارة",
                "رقم الشقة",
                "رقم هاتف اخر (ان وجد)"
            ],
            "current_question": 0,
            "customer_data": {},
            "stage": "collecting_data"
        }

        ask_next_question(sender_id)

    # =============================
    # ♻️ استخدام بيانات قديمة
    # =============================
    elif payload == "USE_OLD_DATA":
        user["stage"] = "ordering"
        user.setdefault("items", {})
        send_products(sender_id)

    elif payload == "RE-ENTER_DATA":
        user["customer_data"] = {}
        user["current_question"] = 1
        user["stage"] = "collecting_data"
        ask_next_question(sender_id)

    # =============================
    # 📦 متابعة طلب
    # =============================
    elif payload == "TRACK_ORDER_MENU":
        user["stage"] = "track_ask_phone"
        send_message(sender_id, "من فضلك أدخل رقم الهاتف الذي قمت بعمل الطلب به (11 رقم):")

    elif payload == "TRACK_INQUIRY":
        process_order_action(sender_id, "استفسار")

    elif payload == "CANCEL_EXISTING_ORDER":
        process_order_action(sender_id, "إلغاء")

    # =============================
    # ✏️ تعديل طلب
    # =============================
    elif payload == "MODIFY_ORDER_MENU":
        quick_replies = [
            {"content_type": "text", "title": "➕ إضافة منتج", "payload": "ADD_TO_EXISTING"},
            {"content_type": "text", "title": "🔄 تغيير الأوردر بالكامل", "payload": "CHANGE_ENTIRE_ORDER"}
        ]
        send_quick_replies(sender_id, "هل تود إضافة منتج جديد أم تغيير الأصناف الحالية؟", quick_replies)

    elif payload == "ADD_TO_EXISTING":
        user["stage"] = "adding_to_existing"
        user["items"] = {}
        send_products(sender_id)

    elif payload == "CHANGE_ENTIRE_ORDER":
        user["stage"] = "ordering"
        user["items"] = {}
        send_products(sender_id)

    # =============================
    # ℹ️ الاستفسارات
    # =============================
    elif payload == "INQUIRY_MENU":
        send_inquiry_options(sender_id)

    elif payload.startswith("INQ_"):
        handle_inquiry(sender_id, payload)

    elif payload.startswith("ING_"):
        bread_name = payload.replace("ING_", "")

        if bread_name in BREAD_INGREDIENTS:
            send_message(sender_id, BREAD_INGREDIENTS[bread_name])

            quick_replies = [
                {"content_type": "text", "title": "🛒 طلب أوردر", "payload": "START_ORDER"},
                {"content_type": "text", "title": "🔙 القائمة السابقة", "payload": "INQUIRY_MENU"},
                {"content_type": "text", "title": "🏠 القائمة الرئيسية", "payload": "MAIN_MENU"}
            ]
            send_quick_replies(sender_id, "اختر أحد الخيارات:", quick_replies)

    # =============================
    # 🥖 اختيار المنتجات
    # =============================
    elif payload.startswith("PRODUCT_"):
        product = payload.replace("PRODUCT_", "")
        user["selected_product"] = product
        send_quantity_menu(sender_id, product)

    elif payload.startswith("QTY_"):
        if "selected_product" not in user:
            return

        try:
            qty = int(payload.split("_")[1])
        except:
            return

        product = user["selected_product"]
        user.setdefault("items", {})
        user["items"][product] = user["items"].get(product, 0) + qty

        send_after_product_menu(sender_id)

    # =============================
    # ✅ إنهاء وتأكيد
    # =============================
    elif payload == "ADD_MORE":
        send_products(sender_id)

    elif payload == "FINISH_ORDER":
        show_final_summary(sender_id)

    elif payload == "CONFIRM_ORDER":
        confirm_order(sender_id)

    elif payload == "CANCEL_ORDER":
        cancel_order(sender_id)

    # =============================
    # 📍 البحث عن موزعين
    # =============================
    elif payload == "FIND_DISTRIBUTORS":
        user["stage"] = "search_distributor"
        send_message(sender_id, "من فضلك اكتب اسم المحافظة للبحث عن أقرب موزع لك:")

    # =============================
    # 🏠 القائمة الرئيسية
    # =============================
    elif payload == "MAIN_MENU":
        user["stage"] = "welcome"
        send_main_menu(sender_id)


def ask_next_question(sender_id):

    user = USER_ORDERS.get(sender_id)
    if not user:
        return

    index = user.get("current_question", 0)
    fields = user.get("data_fields", [])

    if index < len(fields):
        field = fields[index]
        send_message(sender_id, f"من فضلك اكتب {field}:")
    else:
        user["stage"] = "ordering"
        send_products(sender_id)


def send_products(sender_id, enforce_buttons=False):
    if not PRODUCTS:
        send_message(sender_id, "لا توجد منتجات متاحة حالياً.")
        return

    quick_replies = []

    for name, price in list(PRODUCTS.items())[:13]:  # حد أقصى 13 زر
        title = f"{name} - {price}ج"
        if len(title) > 20:
            title = title[:17] + "..."
        quick_replies.append({
            "content_type": "text",
            "title": title,
            "payload": f"PRODUCT_{name}"
        })

    msg = "اختر المنتج:"
    if enforce_buttons:
        msg = random.choice(BUTTON_REMINDER_MESSAGES)  # اختيار رسالة عشوائية من القائمة

    send_quick_replies(sender_id, msg, quick_replies)


def send_quantity_menu(sender_id, product):

    # تأمين وجود المنتج
    if product not in PRODUCTS:
        send_message(sender_id, "حدث خطأ في اختيار المنتج، حاول مرة أخرى.")
        send_products(sender_id)
        return

    quick_replies = []

    # 1 إلى 10 أكياس
    for i in range(1, 11):
        quick_replies.append({
            "content_type": "text",
            "title": str(i),
            "payload": f"QTY_{i}"
        })

    send_quick_replies(
        sender_id,
        f"كم عدد أكياس {product}؟",
        quick_replies
    )


def send_after_product_menu(sender_id):

    user = USER_ORDERS.get(sender_id)
    if not user:
        return

    items = user.get("items", {})

    if not items:
        send_message(sender_id, "لا يوجد منتجات في السلة حالياً.")
        send_products(sender_id)
        return

    # عمل ملخص سريع
    summary_lines = []
    total_items = 0

    for product, qty in items.items():
        summary_lines.append(f"{product} × {qty}")
        total_items += qty

    summary_text = "🛒 سلتك الحالية:\n" + "\n".join(summary_lines)

    quick_replies = [
        {"content_type": "text", "title": "➕ طلب منتج اخر", "payload": "ADD_MORE"},
        {"content_type": "text", "title": "✅ إنهاء الأوردر", "payload": "FINISH_ORDER"},
        {"content_type": "text", "title": "❌ إلغاء الأوردر", "payload": "CANCEL_ORDER"}
    ]

    send_quick_replies(
        sender_id,
        f"تم إضافة المنتج 👌\n\n{summary_text}",
        quick_replies
    )


import re

def extract_total_qty_from_text(order_text):

    if not order_text:
        return 0

    # يلتقط:
    # x2
    # X2
    # x 2
    # X 10
    quantities = re.findall(r'[xX]\s*(\d+)', order_text)

    return sum(int(q) for q in quantities)


def show_final_summary(sender_id):
    user = USER_ORDERS.get(sender_id)
    if not user:
        return
    
    order = user.get("items", {})
    if not order:
        send_message(sender_id, "لم يتم اختيار أي منتجات بعد.")
        return

    # --- 1. حسابات الأصناف الجديدة ---
    new_items_qty = sum(order.values())
    new_items_price = sum(PRODUCTS[name] * qty for name, qty in order.items())
    details = "\n".join([f"✨ {name} x{qty} = {PRODUCTS[name]*qty}ج" for name, qty in order.items()])

    # --- 2. متغيرات افتراضية للأوردر القديم ---
    old_products_price = 0
    old_order_text = ""
    total_combined_qty = new_items_qty
    delivery_status = ""

    # --- 3. حالة إضافة على طلب قائم ---
    if user.get("stage") == "adding_to_existing":
        data = user.get("customer_data", {})
        old_order_text = str(data.get('الطلب') or data.get('الأوردر') or '')
        
        # استخراج الكمية القديمة بطريقة مرنة
        old_qty_list = re.findall(r'[xX]\s*(\d+)', old_order_text)
        old_qty = sum(int(q) for q in old_qty_list)

        # استخراج السعر القديم
        raw_old_total = "0"
        for key, value in data.items():
            if "الإجمالي" in str(key):
                raw_old_total = str(value)
                break
        clean_old_total = re.sub(r'[^\d.]', '', raw_old_total)
        try:
            old_total_val = float(clean_old_total) if clean_old_total else 0.0
        except ValueError:
            old_total_val = 0.0

        old_delivery = 30 if (old_qty > 0 and old_qty < 5) else 0
        old_products_price = old_total_val - old_delivery

        # الحسابات الكلية
        total_combined_qty = old_qty + new_items_qty
        total_products_price = old_products_price + new_items_price
        new_delivery = 0 if total_combined_qty >= 5 else 30
        final_grand_total = total_products_price + new_delivery

        # رسالة حالة الشحن
        if old_delivery == 30 and new_delivery == 0:
            delivery_status = "🚚 التوصيل: **مجاني** (بدلاً من 30ج) 🎉"
        elif new_delivery == 0:
            delivery_status = "🚚 التوصيل: **مجاني** ✨"
        else:
            delivery_status = f"🚚 التوصيل: {new_delivery}ج"

        summary = (
            "🧾 **ملخص تحديث الطلب:**\n\n"
            "📦 **الطلب السابق:**\n"
            f"{old_order_text}\n"
            f"💰 قيمة المنتجات السابقة: {old_products_price}ج\n"
            "-----------------\n"
            "➕ **الإضافات الجديدة:**\n"
            f"{details}\n"
            f"💵 قيمة الإضافات: {new_items_price}ج\n"
            "-----------------\n"
            f"📊 إجمالي الكمية: {total_combined_qty} أكياس\n"
            f"{delivery_status}\n"
            f"✅ **الإجمالي النهائي الجديد: {final_grand_total}ج**\n\n"
            "💡 تم دمج طلباتك وتحديث مصاريف الشحن تلقائياً."
        )
    
    # --- 4. حالة أوردر جديد تماماً ---
    else:
        delivery = 0 if new_items_qty >= 5 else 30
        total_price = new_items_price + delivery
        delivery_text = "مجاني" if delivery == 0 else f"{delivery}ج"
        
        summary = (
            "🧾 **ملخص طلبك:**\n\n"
            f"{details}\n"
            "-----------------\n"
            f"المجموع: {new_items_price}ج\n"
            f"التوصيل: {delivery_text}\n"
            f"الإجمالي: {total_price}ج"
        )

    # --- 5. أزرار تأكيد أو إلغاء ---
    quick_replies = [
        {"content_type": "text", "title": "✅ تأكيد وإرسال", "payload": "CONFIRM_ORDER"},
        {"content_type": "text", "title": "❌ إلغاء", "payload": "CANCEL_ORDER"}
    ]
    send_quick_replies(sender_id, summary, quick_replies)


def update_existing_order_with_new_items(sender_id):
    user = USER_ORDERS[sender_id]
    data = user.get("customer_data", {})
    
    # 1️⃣ سحب نص الطلب القديم
    old_order_text = data.get('الطلب', '')

    # 2️⃣ حساب السعر القديم للمنتجات بدون شحن
    try:
        raw_total = str(data.get('الإجمالي بشحن', '0')).replace('ج', '').strip()
        old_total_with_shipping = float(raw_total)
        old_delivery = 0 if "مجاني" in str(data.get('التوصيل', '')) else 30
        old_products_price = old_total_with_shipping - old_delivery
    except:
        old_products_price = 0.0

    # 3️⃣ حساب الإضافات الجديدة
    new_items = user.get("items", {})
    new_qty = sum(new_items.values())
    new_price = sum(PRODUCTS[name] * qty for name, qty in new_items.items())
    new_text = " | ".join([f"{name} x{qty}" for name, qty in new_items.items()])

    # 4️⃣ حساب المجموع النهائي (القديم + الجديد)
    old_qty = user.get("old_total_qty", 0)
    final_qty = old_qty + new_qty
    final_products_price = old_products_price + new_price

    # 5️⃣ حساب الشحن النهائي
    final_delivery = 0 if final_qty >= 5 else 30
    final_total_with_shipping = final_products_price + final_delivery

    # 6️⃣ تجميع نص الأوردر
    combined_text = f"{old_order_text} + [إضافة: {new_text}]"

    # 7️⃣ تحديث الإكسيل
    row_index = find_order_row_by_phone(user.get("temp_phone"))
    if row_index:
        delete_order_from_excel(row_index)
        delivery_status = "مجاني" if final_delivery == 0 else f"{final_delivery}ج"
        gift = "🎁 كيس هدية" if final_qty >= 8 else "لا يوجد"

        # استخدم دالتك الحالية لحفظ الأوردر (تأكد من اسمها)
        save_order(
            data, 
            combined_text, 
            final_total_with_shipping, 
            delivery_status, 
            gift
        )

    # 8️⃣ إعادة القيم لاستخدامها لاحقاً
    return combined_text, final_total_with_shipping, final_delivery, final_products_price


from twilio.rest import Client

def send_whatsapp_confirmation(phone, order_details, total_price, delivery_text, customer_data, delivery_time):
    """
    إرسال رسالة واتساب للعميل تحتوي على تفاصيل الطلب والعنوان ووقت التوصيل.
    """

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        # تحويل الرقم للشكل الدولي لو العميل كتب 010...
        if phone.startswith("0"):
            phone = "+2" + phone

        message_body = f"""
🎉 تم تأكيد طلبك بنجاح من خبز ريف 💚

📦 تفاصيل الطلب:
{order_details}

💰 الإجمالي: {total_price} جنيه
🚚 التوصيل: {delivery_text}

🏠 عنوان التوصيل:
{customer_data.get('اسم المحافظة','')} - {customer_data.get('اسم المنطقة','')}
{customer_data.get('اسم الشارع + علامة مميزة','')}, عمارة: {customer_data.get('رقم العمارة','')}, شقة: {customer_data.get('رقم الشقة','')}

⏰ {delivery_time}

📞 هاتف للتواصل: {customer_data.get('رقم هاتف ويفضل يكون عليه واتساب','')}

شكراً لاختيارك خبز ريف 🌾
"""

        client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            body=message_body,
            to=f"whatsapp:{phone}"
        )

        print("✅ تم إرسال رسالة واتساب للعميل")

    except Exception as e:
        print(f"❌ فشل إرسال واتساب: {e}")




def confirm_order(sender_id):
    user = USER_ORDERS.get(sender_id)
    if not user:
        return

    # --- طلب جديد ---
    order = user.get("items", {})
    total_qty = sum(order.values())
    items_price = sum(PRODUCTS[name]*qty for name, qty in order.items())
    delivery_cost = 0 if total_qty >= 5 else 30
    total_price = items_price + delivery_cost
    delivery_text = "مجاني" if delivery_cost == 0 else f"{delivery_cost}ج"
    gift = "🎁 كيس هدية" if total_qty >= 8 else "لا يوجد"

    excel_order_details = " | ".join([f"{name} x{qty}" for name, qty in order.items()])
    save_order(user["customer_data"], excel_order_details, total_price, delivery_text, gift)

    # إشعار التليجرام
    telegram_text = (
        f"🛒 **طلب جديد!**\n\n"
        "👤 **بيانات العميل:**\n"
        f"الاسم ثلاثي: {user['customer_data'].get('الاسم ثلاثي','')}\n"
        f"اسم المحافظة: {user['customer_data'].get('اسم المحافظة','')}\n"
        f"اسم المنطقة: {user['customer_data'].get('اسم المنطقة','')}\n"
        f"اسم الشارع + علامة مميزة: {user['customer_data'].get('اسم الشارع + علامة مميزة','')}\n"
        f"رقم العمارة: {user['customer_data'].get('رقم العمارة','')}\n"
        f"رقم الشقة: {user['customer_data'].get('رقم الشقة','')}\n"
        f"رقم هاتف: {user['customer_data'].get('رقم هاتف ويفضل يكون عليه واتساب','')}\n\n"
        "📦 **تفاصيل الطلب:**\n"
        f"{excel_order_details}\n\n"
        f"💰 **الإجمالي:** {total_price}ج\n"
        f"🚚 **التوصيل:** {delivery_text}"
    )
    send_telegram_notification(telegram_text)

    # تحديد وقت التوصيل
    special_area = user["customer_data"].get("اسم المنطقة","")
    if special_area in ["حلوان","15 مايو"]:
        delivery_time = "طلبك هيوصل يوم الثلاثاء القادم 🚚"
    else:
        delivery_time = "طلبك هيوصل في خلال 48 ساعة 🚚"

    # رسالة فيسبوك
    text = f"🎉 تم تأكيد طلب حضرتك بنجاح!\n{delivery_time} 💚"
    send_message(sender_id, text)

    # رسالة واتساب
    phone = user["customer_data"].get("رقم هاتف ويفضل يكون عليه واتساب","")
    send_whatsapp_confirmation(phone, excel_order_details, total_price, delivery_text, user["customer_data"], delivery_time)

    

    # --- تصفير الحالة والعودة للقائمة الرئيسية ---
    USER_ORDERS[sender_id] = {
        "items": {},
        "data_fields": user.get("data_fields", []),
        "current_question": 0,
        "customer_data": {},
        "stage": "welcome"
    }
    send_main_menu(sender_id)


def cancel_order(sender_id):
    # إرسال رسالة تأكيد للعميل
    send_message(sender_id, "❌ تم إلغاء الطلب بنجاح!")
    
    # تصفير بيانات الطلب الحالي
    if sender_id in USER_ORDERS:
        USER_ORDERS[sender_id]["items"] = {}
        USER_ORDERS[sender_id]["stage"] = "welcome"
        USER_ORDERS[sender_id]["customer_data"] = {}
        USER_ORDERS[sender_id]["current_question"] = 0
    
    # إعادة العميل للقائمة الرئيسية أو رسالة الترحيب
    send_welcome(sender_id)

# ===== Verify webhook =====
@app.route('/webhook', methods=['GET'])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Verification failed", 403

# ===== Webhook POST (تحديث لضمان وجود كل الحقول) =====
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    for entry in data.get("entry", []):
        for event in entry.get("messaging", []):
            sender_id = event["sender"]["id"]

            # ===== SQL-ready: نتحقق إذا المستخدم موجود في DB بدل USER_ORDERS =====
            if sender_id not in USER_ORDERS:
                # مؤقتًا: الاحتفاظ بالsession في الذاكرة
                USER_ORDERS[sender_id] = {
                    "items": {},
                    "data_fields": [
                        "الاسم ثلاثي", "اسم المحافظة", "اسم المنطقة", 
                        "اسم الشارع + علامة مميزة", "رقم العمارة", "رقم الشقة", 
                        "رقم هاتف ويفضل يكون عليه واتساب", "رقم هاتف اخر (ان وجد)"
                    ],
                    "wholesale_fields": ["الاسم", "المحافظة", "المنطقة", "محل أم أون لاين", "رقم التليفون"],
                    "current_question": 0,
                    "current_wholesale_question": 0,
                    "customer_data": {},  # لاحقًا: SQL fetch
                    "wholesale_data": {},  # لاحقًا: SQL fetch
                    "stage": "welcome"
                }

            # ===== التعامل مع الرسائل والـ postbacks =====
            if "message" in event and not event["message"].get("is_echo", False):
                if "quick_reply" in event["message"]:
                    payload = event["message"]["quick_reply"]["payload"]
                    handle_postback(sender_id, {"payload": payload})
                else:
                    handle_message(sender_id, event["message"])
            elif "postback" in event:
                handle_postback(sender_id, event["postback"])

    return "ok", 200



# ===== Run Flask =====
if __name__ == "__main__":
    app.run()
