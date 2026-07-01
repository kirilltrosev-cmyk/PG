from app.custom_emojis import ce


def make_texts(p: dict[str, str]) -> dict[str, str]:
    return {
        "welcome": (
            f"{p['hello']}, {{name}}!\n\n"
            f"{{project_name}} {p['welcome']} {{currency_name}}.\n\n"
            f"├ {ce('earn')} {p['earn']}\n"
            f"├ {ce('ads')} {p['advertise']}\n"
            f"├ {ce('checks')} {p['checks']}\n"
            f"├ {ce('profile')} {p['profile']}\n"
            f"└ {ce('subscription_check')} {p['subscription_check']}"
        ),
        "earn": (
            f"{ce('earn')} {p['earning_categories']}:\n\n"
            f"├ {ce('channel')} {p['channels']}: {{channel}}\n"
            f"├ {ce('group')} {p['groups']}: {{group}}\n"
            f"├ {ce('post')} {p['posts']}: {{post}}\n"
            f"├ {ce('bot')} {p['bots']}: {{bot}}\n"
            f"├ {ce('reactions')} {p['reactions']}: {{reaction}}\n"
            f"└ {ce('boost')} Boost: {{boost}}\n\n"
            f"{p['choose_task']}."
        ),
        "profile": (
            f"{ce('profile')} {p['profile']}\n\n"
            f"{{display_name}}\n"
            f"├ {ce('id')} ID: {{telegram_id}}\n"
            f"├ {ce('balance')} {p['balance']}: {{balance}} {{currency_name}}\n"
            f"├ {ce('levels')} {p['level']}: {{level_name}}\n"
            f"├ {ce('xp')} XP: {{xp}}, {p['next_level']} {{xp_left}}\n"
            f"├ {ce('referrals')} {p['referrals']}: {{referrals_count}}\n"
            f"└ {ce('notifications_on')} {p['notifications']}: {{notifications}}"
        ),
        "topup": f"{ce('payment')} {p['topup']}\n\n{p['current_balance']}: {{balance}} {{currency_name}}\n\n{p['choose_package']}.",
        "topup_confirm": f"{ce('payment')} {p['confirm_purchase']}\n\n• {p['amount']}: {{amount}} {{currency_name}}\n• {p['price']}: {{stars}} {ce('stars')}\n\n{p['balance_after_payment']}.",
        "topup_custom": f"{p['enter_stars']}.",
        "topup_done": f"{ce('success')} {p['balance_topped']}: +{{amount}} {{currency_name}}.",
        "refs": f"{ce('referrals')} {p['referrals']}\n\n{p['your_link']}:\n{{referral_link}}\n\n• {p['invited']}: {{referrals_count}}\n• {p['earned']}: {{referral_earned}} {{currency_name}}",
        "refs_stats": f"{ce('statistics')} {p['referral_stats']}\n├ {p['regular']}: +{{regular}}\n├ Premium: +{{premium}}\n├ OP: +{{op}}\n├ {p['deposits']}: {{deposit_percent}}%\n└ {p['tasks']}: {{task_percent}}%",
        "levels": f"{ce('levels')} {p['levels']}\n\n• {p['current']}: {{level_name}}\n• XP: {{xp}}\n• {p['next_in']}: {{xp_left}}\n\n{{levels_table}}",
        "xp_help": (
            f"{ce('xp')} {p['xp_title']}\n\n"
            f"{p['xp_body']}\n\n"
            f"{p['xp_formula']}"
        ),
        "notifications_on": f"{p['notifications_on']}.",
        "notifications_off": f"{p['notifications_off']}.",
        "advertise": f"{ce('ads')} {p['ad_cabinet']} {{project_name}}\n\n{ce('balance')} {p['balance']}: {{balance}} {{currency_name}}\n\n{p['choose_promotion']}.",
        "ad_channel_intro": f"{p['choose_subscription']}:\n\n1. {p['all_users']}.\n{p['minimum_price']}: 750 {{currency_name}}\n\n2. Telegram Premium.\n{p['minimum_price']}: 1 400 {{currency_name}}",
        "ad_group_intro": f"{p['choose_subscription']}:\n\n1. {p['all_users']}.\n{p['minimum_price']}: 1 000 {{currency_name}}\n\n2. Telegram Premium.\n{p['minimum_price']}: 1 500 {{currency_name}}",
        "ad_post_intro": p["ad_post_intro"],
        "ad_bot_intro": p["ad_bot_intro"],
        "ad_reaction_intro": p["ad_reaction_intro"],
        "ad_boost_intro": f"⚡ {p['choose_boost']}:\n\n7 {p['days']} — 21 000 {{currency_name}}\n30 {p['days']} — 90 000 {{currency_name}}",
        "ad_boost_amount": f"{p['fee_note']}.\n\n{p['one_boost']} {{days}} {p['days']}: {{price}} {{currency_name}}\n{p['your_balance']}: {{balance}} {{currency_name}}\n\n{p['enter_boost_count']}.\n\n{p['max_for_balance']}: {{max_amount}}",
        "ad_manual_filters": f"{p['describe_filters']}.",
        "ad_send_url": f"{p['send_target_link']}.",
        "ad_send_reward": f"{p['enter_reward']} {{currency_name}}. {p['example']}: 750 {p['or']} 1400{{min_line}}",
        "ad_bad_reward": f"{p['enter_valid_amount']}. {p['example']}: 5 {p['or']} 7.5",
        "ad_reward_too_low": f"{p['below_minimum']}. {p['minimum_price']}: {{min_reward}} {{currency_name}}.",
        "ad_send_limit": f"{p['reward_per_completion']}: {{reward}} {{currency_name}}\n\n{p['how_many_completions']}?",
        "ad_bad_url": f"{p['send_valid_url']}.",
        "ad_preview": (
            f"{ce('ads')} {p['review']}\n\n"
            f"├ {p['type']}: {{task_type}}\n"
            f"├ {p['title']}: {{title}}\n"
            f"├ {p['audience']}: {{audience}}\n"
            f"├ {p['price']}: {{reward}} {{currency_name}}\n"
            f"├ {p['limit']}: {{limit}}\n"
            f"└ {p['total']}: {{total}} {{currency_name}}\n\n"
            f"⚠️ {p['proof_note']}.\n\n"
            f"{p['launch']}?"
        ),
        "ad_created": f"{ce('success')} {p['task']} #{{task_id}} {p['created']}. {p['charged']} {{total}} {{currency_name}}.",
        "ad_auto": f"{ce('auto_tasks')} {p['auto_tasks']}\n\n{p['no_channels_auto']}.",
        "ad_auto_add": f"{p['ad_auto_add']}.",
        "ad_mine": (
            f"{ce('my_tasks')} <b>{p['my_tasks']}</b>\n\n"
            f"<b>{p['summary']}:</b>\n"
            f"├ {p['active']}: {{active}}\n"
            f"├ {p['moderation']}: {{moderation}}\n"
            f"├ {p['archived']}: {{completed}}\n"
            f"├ {p['paused']}: {{paused}}\n"
            f"└ {p['waiting_review']}: {{pending}}\n\n"
            f"<b>{p['recent_tasks']}:</b>\n{{items}}\n\n"
            f"{p['choose_task_or_review']}."
        ),
        "ad_mine_empty": f"{p['ad_mine_empty']}.",
        "links": f"{ce('links')} <b>{p['useful_links']}</b>\n\n{p['agreement']}.\n\n{p['choose_section']}.",
        "guide": p["guide"],
        "rules": f"{ce('warning')} <b>{p['service_rules']}</b>\n\n{p['rules_body']}",
        "privacy_policy": f"{ce('shield')} <b>{p['privacy_policy']}</b>\n\n{p['privacy_body']}",
        "op": f"{ce('subscription_check')} {p['subscription_check']}\n\n{p['op_intro']}.",
        "op_groups_empty": f"{p['op_groups_empty']}.",
        "op_groups": f"{ce('group')} {p['connected_groups']}\n\n{{items}}",
        "op_group_card": f"├ {p['group']}: {{title}}\n├ {p['status']}: {{enabled}}\n├ {p['required_channels']}: {{channels_count}}\n└ {p['action']}: {{action}}\n\n{{warning_text}}",
        "op_channels": f"{ce('channel')} {p['required_channels']}\n\n{{items}}",
        "op_channel_ask": f"{p['op_channel_ask']}.",
        "op_channel_bad": f"{p['op_channel_bad']}.",
        "op_warning": f"{p['current_warning']}:\n\n{{warning_text}}",
        "op_warning_ask": f"{p['op_warning_ask']}.",
        "op_actions": f"{p['op_actions']}.",
        "op_whitelist": f"{ce('shield')} Whitelist\n\n{{items}}",
        "op_whitelist_ask": f"{p['op_whitelist_ask']}.",
        "op_stats": f"{ce('statistics')} {p['stats']}\n├ {p['events']}: {{checks_total}}\n├ OK: {{checks_ok}}\n├ {p['failed']}: {{checks_failed}}\n├ {p['deleted']}: {{messages_deleted}}\n├ {p['restricted']}: {{restricted}}\n└ {p['required']}: {{channels_count}}",
        "op_commands": p["op_commands"],
        "op_add_bot": p["op_add_bot"],
        "op_guide": f"{ce('instruction')} {p['op_guide']}",
        "stats": f"{ce('statistics')} {p['stats']}\n├ {p['users']}: {{users}}\n├ {p['active_tasks']}: {{active_tasks}}\n├ {p['completions']}: {{completed}}\n├ {p['payments']}: {{payments}}\n└ {p['complaints']}: {{complaints}}",
        "no_tasks": f"{p['no_tasks']}.",
        "task_list": f"{p['task_list']}\n\n{p['available']}: {{total}}\n{p['page']}: {{page}}/{{pages}}",
        "task_card": f"{p['task']} #{{id}}\n{{title}}\n{{task_details}}",
        "sandbox_topup_done": f"{ce('success')} {p['sandbox_topup']}: +{{amount}} {{currency_name}}.",
        "language": p["language"],
        "language_set": p["language_set"],
        "checks": f"{ce('checks')} {p['checks_text']}",
        "check_created": f"{p['check_created']}:\nhttps://t.me/{{bot_username}}?start=check_{{token}}",
        "check_activated": f"{p['check_activated']}.",
        "check_bad": f"{p['check_bad']}.",
        "admin": f"{ce('admin')} {p['admin_panel']}.",
        "pending_empty": f"{p['pending_empty']}.",
    }


ENGLISH_BASE = {
    "hello": "Hello", "welcome": "helps Telegram projects grow and lets users earn", "earn": "Earn", "advertise": "Advertise", "checks": "Checks", "profile": "Profile", "subscription_check": "Subscription check",
    "earning_categories": "Available earning categories", "channels": "Channels", "groups": "Groups", "posts": "Posts", "bots": "Bots", "reactions": "Reactions", "choose_task": "Choose a task type",
    "balance": "Balance", "level": "Level", "next_level": "next level in", "referrals": "Referrals", "notifications": "Notifications", "topup": "Top up", "current_balance": "Current balance", "choose_package": "Choose a package or enter Telegram Stars amount",
    "confirm_purchase": "Confirm purchase", "amount": "Amount", "price": "Price", "balance_after_payment": "The balance will update after successful Telegram Stars payment", "enter_stars": "Enter Telegram Stars amount", "balance_topped": "Balance topped up",
    "your_link": "Your link", "invited": "Invited", "earned": "Earned", "referral_stats": "Referral stats", "regular": "Regular", "deposits": "Deposits", "tasks": "Tasks", "levels": "Levels", "current": "Current", "next_in": "Next in",
    "xp_title": "How to get XP", "xp_body": "XP is earned from tasks, referrals and balance top-ups.", "xp_formula": "For each completed task, XP matches the reward: 750 GRAM gives 750 XP, 1 400 GRAM gives 1 400 XP.",
    "notifications_on": "Notifications enabled", "notifications_off": "Notifications disabled", "ad_cabinet": "Ad cabinet", "choose_promotion": "Choose what to promote. I will show the price and ask for confirmation before launch",
    "choose_subscription": "Choose subscription type", "all_users": "All users — broad audience", "minimum_price": "Minimum price", "ad_post_intro": "Post promotion. Choose views or reactions.", "ad_bot_intro": "Bot promotion. Choose simple start or extra conditions.",
    "ad_reaction_intro": "Rules for reaction tasks:\n\n1. Do not create reaction tasks for Telegram Stars.\n\n2. Screenshots must be possible in the channel.\n\n⚠️ Rule violations may lead to task removal or account limits.\n\nNow configure the task audience.",
    "choose_boost": "Choose boost period", "days": "days", "fee_note": "A 15% fee applies when paying with internal currency", "one_boost": "One Boost for", "your_balance": "Your balance", "enter_boost_count": "Enter the number of Boost charges", "max_for_balance": "Maximum for your balance",
    "describe_filters": "Describe audience filters in one message", "send_target_link": "Send the target link. You may add chat_id after it", "enter_reward": "Enter reward per completion in", "example": "Example", "or": "or", "enter_valid_amount": "Enter a valid amount greater than zero", "below_minimum": "The price is below the minimum for this category", "reward_per_completion": "Reward per completion", "how_many_completions": "How many completions do you need", "send_valid_url": "Send a valid URL or @username",
    "review": "Review", "type": "Type", "title": "Title", "audience": "Audience", "limit": "Limit", "total": "Total", "proof_note": "Proof screenshots must be reviewed in My tasks", "launch": "Launch", "task": "Task", "created": "created", "charged": "Charged", "auto_tasks": "Auto tasks", "no_channels_auto": "No channels connected yet. Add a channel to configure automatic promotion for new posts", "ad_auto_add": "Add the bot as channel admin, then connect the channel in setup",
    "my_tasks": "My tasks", "summary": "Summary", "active": "Active", "moderation": "Moderation", "archived": "Archived", "paused": "Paused", "waiting_review": "Waiting for review", "recent_tasks": "Recent tasks", "choose_task_or_review": "Choose a task or open requests waiting for your decision", "ad_mine_empty": "You have no created tasks yet",
    "useful_links": "Useful links", "agreement": "By using the bot, you agree to the service rules and privacy policy", "choose_section": "Choose a section below", "guide": "Guide: earn, create ads, top up balance, share checks and invite referrals.", "service_rules": "Service rules", "rules_body": "1. By using the bot, you accept these rules.\n\n2. Fraud, spam, illegal content and fake activity are forbidden.\n\n3. Administration may remove tasks and restrict access for violations.", "privacy_policy": "Privacy policy", "privacy_body": "1. The bot processes public Telegram data required for the service.\n\n2. Data is used for rewards, verification, fraud prevention and communication.\n\n3. Data is not shared with third parties except where required by law.",
    "op_intro": "Add the bot as group admin, then configure required channels and actions", "op_groups_empty": "No connected groups yet. Add the bot as group admin and come back", "connected_groups": "Connected groups", "group": "Group", "status": "Status", "required_channels": "Required channels", "action": "Action", "op_channel_ask": "Add our bot as channel admin, then send the channel link, username or ID", "op_channel_bad": "I cannot check this channel. Add the bot as channel admin or check the link/ID", "current_warning": "Current warning", "op_warning_ask": "Send new warning text", "op_actions": "Choose violation action", "op_whitelist_ask": "Send user ID or username", "stats": "Stats", "events": "Events", "failed": "Failed", "deleted": "Deleted", "restricted": "Restricted", "required": "Required", "op_commands": "Group commands.", "op_add_bot": "Send the API token of the bot you want to connect. The token is used only for checks and is stored protected.", "op_guide": "Guide: add bot, grant admin rights, add required channels, choose action and enable checking.",
    "users": "Users", "active_tasks": "Active tasks", "completions": "Completions", "payments": "Payments", "complaints": "Complaints", "no_tasks": "No tasks in this category right now", "task_list": "Choose a task from the list.\n\nOpen its card, follow the link and complete the action. Then return and press Check or send proof.\n\nDo not unsubscribe or block the bot for 7 days, otherwise the reward may be cancelled.", "available": "Available", "page": "Page", "sandbox_topup": "Sandbox top-up completed", "language": "Choose interface language.", "language_set": "Language saved.", "checks_text": "Checks let you transfer internal balance to other users.", "check_created": "Check created", "check_activated": "Check activated", "check_bad": "Check is unavailable or already used", "admin_panel": "Admin panel: stats, manual reviews, complaints and balances", "pending_empty": "No pending reviews",
}


def pack(**items: str) -> dict[str, str]:
    data = ENGLISH_BASE.copy()
    data.update(items)
    return data


LANGUAGE_PHRASES = {
    "uk": pack(hello="Привіт", welcome="допомагає просувати Telegram-проєкти й заробляти", earn="Заробити", advertise="Рекламувати", checks="Чеки", profile="Профіль", subscription_check="Перевірка підписки", language="Оберіть мову інтерфейсу.", language_set="Мову збережено.", earning_categories="Доступні напрями заробітку", channels="Канали", groups="Групи", posts="Пости", bots="Боти", reactions="Реакції", choose_task="Виберіть тип завдання", balance="Баланс", level="Рівень", referrals="Реферали", notifications="Сповіщення", topup="Поповнення", current_balance="Поточний баланс", check_created="Чек створено", check_activated="Чек активовано", check_bad="Чек недоступний або вже використаний"),
    "de": pack(hello="Hallo", welcome="hilft Telegram-Projekten zu wachsen und lässt Nutzer verdienen", earn="Verdienen", advertise="Werben", checks="Schecks", profile="Profil", subscription_check="Abo-Prüfung", language="Wählen Sie die Sprache der Oberfläche.", language_set="Sprache gespeichert.", earning_categories="Verfügbare Verdienstkategorien", channels="Kanäle", groups="Gruppen", posts="Beiträge", bots="Bots", reactions="Reaktionen", choose_task="Wählen Sie einen Aufgabentyp", balance="Guthaben", level="Level", referrals="Empfehlungen", notifications="Benachrichtigungen", topup="Aufladen", current_balance="Aktuelles Guthaben", check_created="Scheck erstellt", check_activated="Scheck aktiviert", check_bad="Scheck ist nicht verfügbar oder bereits benutzt"),
    "zh": pack(hello="你好", welcome="帮助 Telegram 项目增长，并让用户赚取", earn="赚取", advertise="推广", checks="支票", profile="资料", subscription_check="订阅检查", language="请选择界面语言。", language_set="语言已保存。", earning_categories="可赚取的类别", channels="频道", groups="群组", posts="帖子", bots="机器人", reactions="反应", choose_task="选择任务类型", balance="余额", level="等级", referrals="邀请", notifications="通知", topup="充值", current_balance="当前余额", check_created="支票已创建", check_activated="支票已激活", check_bad="支票不可用或已被使用"),
    "ar": pack(hello="مرحباً", welcome="يساعد مشاريع Telegram على النمو ويتيح للمستخدمين كسب", earn="اكسب", advertise="إعلان", checks="الشيكات", profile="الملف الشخصي", subscription_check="فحص الاشتراك", language="اختر لغة الواجهة.", language_set="تم حفظ اللغة.", earning_categories="فئات الربح المتاحة", channels="القنوات", groups="المجموعات", posts="المنشورات", bots="البوتات", reactions="التفاعلات", choose_task="اختر نوع المهمة", balance="الرصيد", level="المستوى", referrals="الإحالات", notifications="الإشعارات", topup="شحن الرصيد", current_balance="الرصيد الحالي", check_created="تم إنشاء الشيك", check_activated="تم تفعيل الشيك", check_bad="الشيك غير متاح أو مستخدم مسبقاً"),
    "fa": pack(hello="سلام", welcome="به رشد پروژه‌های Telegram کمک می‌کند و به کاربران امکان کسب", earn="کسب درآمد", advertise="تبلیغ", checks="چک‌ها", profile="پروفایل", subscription_check="بررسی عضویت", language="زبان رابط را انتخاب کنید.", language_set="زبان ذخیره شد.", earning_categories="دسته‌های درآمد", channels="کانال‌ها", groups="گروه‌ها", posts="پست‌ها", bots="ربات‌ها", reactions="واکنش‌ها", choose_task="نوع وظیفه را انتخاب کنید", balance="موجودی", level="سطح", referrals="معرفی‌ها", notifications="اعلان‌ها", topup="شارژ", current_balance="موجودی فعلی", check_created="چک ایجاد شد", check_activated="چک فعال شد", check_bad="چک در دسترس نیست یا قبلاً استفاده شده است"),
    "es": pack(hello="Hola", welcome="ayuda a crecer proyectos de Telegram y permite a los usuarios ganar", earn="Ganar", advertise="Anunciar", checks="Cheques", profile="Perfil", subscription_check="Comprobación de suscripción", language="Seleccione el idioma de la interfaz.", language_set="Idioma guardado.", earning_categories="Categorías disponibles para ganar", channels="Canales", groups="Grupos", posts="Publicaciones", bots="Bots", reactions="Reacciones", choose_task="Elija un tipo de tarea", balance="Saldo", level="Nivel", referrals="Referidos", notifications="Notificaciones", topup="Recargar", current_balance="Saldo actual", check_created="Cheque creado", check_activated="Cheque activado", check_bad="El cheque no está disponible o ya fue usado"),
    "id": pack(hello="Halo", welcome="membantu proyek Telegram berkembang dan memungkinkan pengguna memperoleh", earn="Dapatkan", advertise="Iklankan", checks="Cek", profile="Profil", subscription_check="Pemeriksaan langganan", language="Pilih bahasa antarmuka.", language_set="Bahasa disimpan.", earning_categories="Kategori penghasilan tersedia", channels="Channel", groups="Grup", posts="Postingan", bots="Bot", reactions="Reaksi", choose_task="Pilih jenis tugas", balance="Saldo", level="Level", referrals="Referral", notifications="Notifikasi", topup="Isi saldo", current_balance="Saldo saat ini", check_created="Cek dibuat", check_activated="Cek diaktifkan", check_bad="Cek tidak tersedia atau sudah digunakan"),
    "pt": pack(hello="Olá", welcome="ajuda projetos do Telegram a crescer e permite que usuários ganhem", earn="Ganhar", advertise="Anunciar", checks="Cheques", profile="Perfil", subscription_check="Verificação de assinatura", language="Escolha o idioma da interface.", language_set="Idioma salvo.", earning_categories="Categorias disponíveis para ganhar", channels="Canais", groups="Grupos", posts="Postagens", bots="Bots", reactions="Reações", choose_task="Escolha um tipo de tarefa", balance="Saldo", level="Nível", referrals="Indicações", notifications="Notificações", topup="Recarregar", current_balance="Saldo atual", check_created="Cheque criado", check_activated="Cheque ativado", check_bad="Cheque indisponível ou já usado"),
    "hi": pack(hello="नमस्ते", welcome="Telegram परियोजनाओं को बढ़ाने में मदद करता है और उपयोगकर्ताओं को कमाने देता है", earn="कमाएँ", advertise="विज्ञापन", checks="चेक", profile="प्रोफ़ाइल", subscription_check="सदस्यता जाँच", language="इंटरफ़ेस भाषा चुनें।", language_set="भाषा सहेज दी गई।", earning_categories="उपलब्ध कमाई श्रेणियाँ", channels="चैनल", groups="समूह", posts="पोस्ट", bots="बॉट", reactions="प्रतिक्रियाएँ", choose_task="कार्य प्रकार चुनें", balance="बैलेंस", level="स्तर", referrals="रेफ़रल", notifications="सूचनाएँ", topup="टॉप अप", current_balance="वर्तमान बैलेंस", check_created="चेक बनाया गया", check_activated="चेक सक्रिय हुआ", check_bad="चेक उपलब्ध नहीं है या पहले ही उपयोग हो चुका है"),
    "bn": pack(hello="নমস্কার", welcome="Telegram প্রকল্প বাড়াতে সাহায্য করে এবং ব্যবহারকারীদের উপার্জন করতে দেয়", earn="আয় করুন", advertise="বিজ্ঞাপন", checks="চেক", profile="প্রোফাইল", subscription_check="সাবস্ক্রিপশন পরীক্ষা", language="ইন্টারফেসের ভাষা নির্বাচন করুন।", language_set="ভাষা সংরক্ষণ করা হয়েছে।", earning_categories="উপার্জনের উপলব্ধ বিভাগ", channels="চ্যানেল", groups="গ্রুপ", posts="পোস্ট", bots="বট", reactions="প্রতিক্রিয়া", choose_task="টাস্কের ধরন বেছে নিন", balance="ব্যালেন্স", level="লেভেল", referrals="রেফারেল", notifications="নোটিফিকেশন", topup="টপ আপ", current_balance="বর্তমান ব্যালেন্স", check_created="চেক তৈরি হয়েছে", check_activated="চেক সক্রিয় হয়েছে", check_bad="চেক উপলব্ধ নয় বা ইতিমধ্যে ব্যবহৃত"),
    "uz": pack(hello="Salom", welcome="Telegram loyihalarini rivojlantirishga yordam beradi va foydalanuvchilarga ishlash imkonini beradi", earn="Ishlash", advertise="Reklama", checks="Cheklar", profile="Profil", subscription_check="Obunani tekshirish", language="Interfeys tilini tanlang.", language_set="Til saqlandi.", earning_categories="Mavjud daromad yo‘nalishlari", channels="Kanallar", groups="Guruhlar", posts="Postlar", bots="Botlar", reactions="Reaksiyalar", choose_task="Vazifa turini tanlang", balance="Balans", level="Daraja", referrals="Referallar", notifications="Bildirishnomalar", topup="To‘ldirish", current_balance="Joriy balans", check_created="Chek yaratildi", check_activated="Chek faollashtirildi", check_bad="Chek mavjud emas yoki ishlatilgan"),
    "tr": pack(hello="Merhaba", welcome="Telegram projelerinin büyümesine yardımcı olur ve kullanıcıların kazanmasını sağlar", earn="Kazan", advertise="Reklam ver", checks="Çekler", profile="Profil", subscription_check="Abonelik kontrolü", language="Arayüz dilini seçin.", language_set="Dil kaydedildi.", earning_categories="Mevcut kazanç kategorileri", channels="Kanallar", groups="Gruplar", posts="Gönderiler", bots="Botlar", reactions="Tepkiler", choose_task="Görev türü seçin", balance="Bakiye", level="Seviye", referrals="Referanslar", notifications="Bildirimler", topup="Yükle", current_balance="Güncel bakiye", check_created="Çek oluşturuldu", check_activated="Çek etkinleştirildi", check_bad="Çek kullanılamıyor veya zaten kullanıldı"),
    "kk": pack(hello="Сәлем", welcome="Telegram жобаларын өсіруге көмектеседі және пайдаланушыларға табыс табуға мүмкіндік береді", earn="Табыс табу", advertise="Жарнамалау", checks="Чектер", profile="Профиль", subscription_check="Жазылымды тексеру", language="Интерфейс тілін таңдаңыз.", language_set="Тіл сақталды.", earning_categories="Қолжетімді табыс санаттары", channels="Арналар", groups="Топтар", posts="Посттар", bots="Боттар", reactions="Реакциялар", choose_task="Тапсырма түрін таңдаңыз", balance="Баланс", level="Деңгей", referrals="Рефералдар", notifications="Хабарламалар", topup="Толтыру", current_balance="Ағымдағы баланс", check_created="Чек жасалды", check_activated="Чек белсендірілді", check_bad="Чек қолжетімсіз немесе бұрын қолданылған"),
    "fr": pack(hello="Bonjour", welcome="aide les projets Telegram à grandir et permet aux utilisateurs de gagner", earn="Gagner", advertise="Promouvoir", checks="Chèques", profile="Profil", subscription_check="Vérification d’abonnement", language="Choisissez la langue de l’interface.", language_set="Langue enregistrée.", earning_categories="Catégories de gain disponibles", channels="Canaux", groups="Groupes", posts="Publications", bots="Bots", reactions="Réactions", choose_task="Choisissez un type de tâche", balance="Solde", level="Niveau", referrals="Parrainages", notifications="Notifications", topup="Recharger", current_balance="Solde actuel", check_created="Chèque créé", check_activated="Chèque activé", check_bad="Chèque indisponible ou déjà utilisé"),
}


LANGUAGE_OVERRIDES = {language: make_texts(phrases) for language, phrases in LANGUAGE_PHRASES.items()}
